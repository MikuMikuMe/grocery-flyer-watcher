"""Bounded public acquisition pilot. Candidates are NEVER verified facts or mail authority."""
from __future__ import annotations
import argparse
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ARCHIVE = 'https://flyers.smartcanucks.ca'
FLIPP = 'https://backflipp.wishabi.com'
MARKET = 'Kingston, Ontario, Canada'
# Public store-region lookup, not a personal address or postal code.
QUERY = '?locale=en-ca&postal_code=K7L'
MAX_BYTES = 12_000_000
PILOT = 'food-basics'
SHA = re.compile(r'[a-f0-9]{64}\Z')
PAGE = re.compile(r'/uploads/pages/[0-9]+/[a-zA-Z0-9_-]+-([1-9][0-9]?)\.jpg\Z')
DATES = re.compile(r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), ([A-Z][a-z]{2} \d{1,2}, \d{4})\s*[-–]\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), ([A-Z][a-z]{2} \d{1,2}, \d{4})')

class CollectorError(ValueError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise CollectorError('redirect_refused')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.netloc not in {'flyers.smartcanucks.ca', 'backflipp.wishabi.com'} or p.fragment:
        raise CollectorError('source_not_allowlisted')
    req = urllib.request.Request(url, headers={'User-Agent': 'GroceryFlyerWatcher/1.0 public flyer research', 'Accept': 'application/json,text/html,image/jpeg'})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:
        raw = response.read(MAX_BYTES + 1)
        if not raw or len(raw) > MAX_BYTES:
            raise CollectorError('invalid_response_size')
        return raw


class Links(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.parts = []
        self.feed(raw.decode('utf-8', errors='replace'))

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in {'href', 'src', 'data-src', 'data-original'} and v:
                self.links.append(urllib.parse.urljoin(ARCHIVE, v))

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return ' '.join(' '.join(self.parts).split())


def discover(raw):
    return list(dict.fromkeys(u for u in Links(raw).links if re.fullmatch(r'https://flyers\.smartcanucks\.ca/canada/food-basics-flyer-[a-z0-9-]+', u)))[:4]


def edition(raw, today):
    m = DATES.search(Links(raw).text)
    if not m:
        raise CollectorError('missing_printed_archive_dates')
    a, b = [datetime.strptime(x, '%b %d, %Y').date() for x in m.groups()]
    if not a <= today <= b or (b-a).days > 8:
        raise CollectorError('not_current_weekly_edition')
    return a.isoformat(), b.isoformat()


def page_urls(raw):
    result = {}
    for u in Links(raw).links:
        p = urllib.parse.urlsplit(u)
        m = PAGE.fullmatch(p.path)
        if p.scheme == 'https' and p.netloc == 'flyers.smartcanucks.ca' and not p.query and not p.fragment and m:
            n = int(m.group(1))
            if n <= 64:
                if n in result and result[n] != u:
                    raise CollectorError('conflicting_page_urls')
                result[n] = u
    return result


def datepart(v):
    if not isinstance(v, str):
        raise CollectorError('missing_date')
    try:
        if 'T' in v:
            d = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if d.tzinfo:
                return d.astimezone(ZoneInfo('America/Toronto')).date().isoformat()
        return date.fromisoformat(v[:10]).isoformat()
    except ValueError as e:
        raise CollectorError('invalid_date') from e


def records(obj, key):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get(key), list):
        return obj[key]
    raise CollectorError('unexpected_json_shape')


def safe_text(v, limit=160):
    if not isinstance(v, str) or len(v) > limit or re.search(r'[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}|https?://|[\x00-\x1f]', v):
        return None
    return v.strip() or None


def price(v):
    if isinstance(v, bool) or not isinstance(v, (int, float, str, Decimal)):
        return None
    try:
        n = Decimal(str(v))
        if not n.is_finite() or not 0 < n < 100000 or n != n.quantize(Decimal('0.01')):
            return None
        return format(n, '.2f')
    except InvalidOperation:
        return None


def extract_candidates(raw, starts, ends):
    out = {}
    for item in records(json.loads(raw), 'items'):
        if not isinstance(item, dict):
            continue
        ident = item.get('id', item.get('item_id'))
        name = safe_text(item.get('name'))
        cash = price(item.get('current_price', item.get('price')))
        if type(ident) is not int or ident <= 0 or not name or not cash:
            continue
        a, b = item.get('valid_from'), item.get('valid_to')
        try:
            a, b = datepart(a) if a else None, datepart(b) if b else None
        except CollectorError:
            continue
        if (a and not starts <= a <= ends) or (b and not starts <= b <= ends) or (a and b and a > b):
            continue
        row = {'item_id': ident, 'name': name, 'price_field_cad': cash, 'valid_from': a, 'valid_to': b}
        for k in ('brand','price_text','pre_price_text','post_price_text','sale_story','description'):
            row[k] = safe_text(item.get(k))
        # This field is not a cash/pack/terms interpretation. Discount-only and
        # multibuy text remains visible for independent review; never auto-authorize.
        if ident in out and out[ident] != row:
            raise CollectorError('conflicting_item_id')
        out[ident] = row
    if not out or len(out) > 2500:
        raise CollectorError('empty_or_excessive_candidates')
    return [out[k] for k in sorted(out)]


def acquire_archive(today, get=fetch):
    index_url = ARCHIVE+'/food-basics-canada'
    index = get(index_url)
    chosen = None
    for url in discover(index):
        raw = get(url)
        try:
            starts, ends = edition(raw, today)
        except CollectorError:
            continue
        chosen = (url, raw, starts, ends)
        break
    if not chosen:
        raise CollectorError('no_current_archive_edition')
    url, raw, starts, ends = chosen
    pages = page_urls(raw)
    # The original archive is independent evidence, not proof of exact local variant.
    if 1 not in pages:
        raise CollectorError('missing_original_page_one')
    image = get(pages[1])
    if not image.startswith(b'\xff\xd8\xff'):
        raise CollectorError('non_jpeg_original')
    return {'format':'external-source-evidence-v1','retailer_id':PILOT,
            'edition':{'starts_on':starts,'ends_on':ends},
            'archive':{'url':url,'sha256':digest(raw),'page_one_url':pages[1],'page_one_sha256':digest(image)},
            'market_verified':False,'coverage_complete':False,'gmail_authorized':False}


def collect(today, get=fetch, evidence=None):
    evidence = evidence if evidence is not None else acquire_archive(today, get)
    starts, ends = evidence['edition']['starts_on'], evidence['edition']['ends_on']
    listing_url = FLIPP+'/flipp/flyers'+QUERY
    listing = get(listing_url)
    matches = []
    for f in records(json.loads(listing), 'flyers'):
        if not isinstance(f, dict) or str(f.get('merchant','')).casefold().strip() != 'food basics':
            continue
        try:
            if (datepart(f.get('valid_from')),datepart(f.get('valid_to'))) != (starts,ends):
                continue
        except CollectorError:
            continue
        fid = f.get('id', f.get('flyer_id'))
        if type(fid) is int and fid > 0:
            matches.append(fid)
    matches = sorted(set(matches))
    if len(matches) != 1:
        raise CollectorError('missing_or_ambiguous_syndicated_edition')
    source_url = FLIPP+'/flipp/flyers/'+str(matches[0])+QUERY
    source = get(source_url)
    offers = extract_candidates(source, starts, ends)
    return {'format':'external-candidate-batch-v1','retailer_id':PILOT,'market_lookup':MARKET,
            'edition':{'starts_on':starts,'ends_on':ends},'archive':evidence['archive'],
            'syndicated':{'url':source_url,'sha256':digest(source),'flyer_id':matches[0]},'offers':offers,
            'market_verified':False,'coverage_complete':False,'quality_authorized':False,'publication_authorized':False,'gmail_authorized':False}


def persist(batch, root):
    raw = (json.dumps(batch,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    e = batch['edition']
    kind = {'external-candidate-batch-v1':'external-candidates', 'external-source-evidence-v1':'external-source-evidence'}[batch['format']]
    path = root/'data'/kind/PILOT/(e['starts_on']+'_'+e['ends_on'])/(digest(raw)+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=raw:
            raise CollectorError('immutable_conflict')
        return path, False
    with path.open('xb') as f:
        f.write(raw)
    return path, True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'))
    a=p.parse_args()
    try:
        today=datetime.now(ZoneInfo('America/Toronto')).date()
        evidence=acquire_archive(today)
        ep,en=persist(evidence,a.root)
        print(json.dumps({'status':'source_evidence_ready','path':str(ep),'new':en,'coverage_complete':False,'gmail_authorized':False}),flush=True)
        batch=collect(today,evidence=evidence)
        path,new=persist(batch,a.root)
        print(json.dumps({'status':'candidate_ready','path':str(path),'new':new,'offers':len(batch['offers']),'gmail_authorized':False}))
    except (CollectorError, OSError, ValueError, TypeError) as exc:
        # No source body, URL query from arbitrary data, or secret in logs.
        print(json.dumps({'status':'blocked','code':str(exc) if isinstance(exc,CollectorError) else type(exc).__name__,'gmail_authorized':False}))
        return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())
