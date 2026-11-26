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
GRID = 'https://www.weeklyflyer.com/food-basics'
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
    if p.scheme != 'https' or p.netloc not in {'flyers.smartcanucks.ca', 'backflipp.wishabi.com', 'www.weeklyflyer.com'} or p.fragment:
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


def collect_syndicated(today, get=fetch, evidence=None):
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



class FeaturedGrid(HTMLParser):
    """Collect the visible featured h2/h3 sections, not hidden scripts or nav."""
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.heading = None
        self.parts = []
        self.title = ''
        self.active = False
        self.current = None
        self.rows = []
        self.hidden = 0
        self.feed(raw.decode('utf-8', errors='replace'))
        self.close_row()

    def close_row(self):
        if self.current:
            self.rows.append(self.current)
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if self.hidden:
            return
        if tag in ('h2', 'h3'):
            self.heading = tag
            self.parts = []

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.hidden:
            self.hidden -= 1
            return
        if self.hidden:
            return
        if tag == self.heading:
            value = ' '.join(' '.join(self.parts).split())
            if tag == 'h2':
                self.close_row()
                self.active = bool(re.match(r'Top 20 Food Basics .+\(', value, re.I))
                if self.active:
                    self.title = value
            elif self.active:
                self.close_row()
                self.current = {'name':value, 'text':[]}
            self.heading = None

    def handle_data(self, value):
        if self.hidden:
            return
        if self.heading:
            self.parts.append(value)
        elif self.current:
            self.current['text'].append(value)


def grid_candidates(raw, starts, ends):
    parser = FeaturedGrid(raw)
    # Validate exact visible weekly heading dates against independently fetched archive.
    def short(d):
        dt = date.fromisoformat(d)
        return dt.strftime('%b') + ' ' + str(dt.day)
    if not re.search(r'\(' + re.escape(short(starts)) + r'\s*[-–—]\s*' + re.escape(short(ends)) + r'\)', parser.title):
        raise CollectorError('grid_edition_mismatch')
    rows = {}
    for r in parser.rows:
        name = safe_text(r['name'])
        if not name:
            continue
        # DOM text order: first displayed standalone absolute price after its own h3.
        # Do not interpret multibuys, discounts, member terms, competing values or
        # post-price text; ambiguous records are excluded, not repaired.
        text = ' '.join(' '.join(r['text']).split())
        hits = list(re.finditer(r'(?<![\w/$])\$([0-9]+\.[0-9]{2})\s*(each|/\s*(?:lb|kg))\b', text, re.I))
        if len(hits) != 1 or not price(hits[0].group(1)) or re.search(r'\b(?:member|loyalty|points|when you buy|with card)\b',text,re.I):
            continue
        h=hits[0]
        description=safe_text(text[:h.start()].strip(),240)
        # Keep the source's printed price string (not a unit-price calculation).
        row={'name':name,'price_field_cad':price(h.group(1)),'price_text':h.group(0),
             'description':description,'valid_from':None,'valid_to':None}
        key=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
        rows[key]=row
    if not rows or len(rows)>20:
        raise CollectorError('grid_empty_or_unexpected_count')
    return [rows[k] for k in sorted(rows)]


def collect(today, get=fetch, evidence=None):
    evidence = evidence if evidence is not None else acquire_archive(today, get)
    try:
        return collect_syndicated(today,get,evidence)
    except (CollectorError, OSError, ValueError, TypeError) as exc:
        # Do not repeatedly retry the same source; one fixed fallback. HTTP code
        # only, no response body, credentials, or arbitrary URL logging.
        code = f'HTTP_{exc.code}' if isinstance(exc,urllib.error.HTTPError) else str(exc) if isinstance(exc,CollectorError) else type(exc).__name__
        print(json.dumps({'status':'syndicated_blocked','code':code,'fallback':'weeklyflyer_featured_grid'}),flush=True)
    raw=get(GRID)
    starts,ends=evidence['edition']['starts_on'],evidence['edition']['ends_on']
    offers=grid_candidates(raw,starts,ends)
    return {'format':'external-candidate-batch-v1','retailer_id':PILOT,'market_lookup':MARKET,
            'edition':evidence['edition'],'archive':evidence['archive'],
            'grid':{'url':GRID,'sha256':digest(raw),'scope':'featured_only_region_unverified'},'offers':offers,
            'market_verified':False,'coverage_complete':False,'quality_authorized':False,'publication_authorized':False,'gmail_authorized':False}

def canonical(batch):
    return (json.dumps(batch,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def load_record(path):
    raw=path.read_bytes()
    if digest(raw) != path.stem:
        raise CollectorError('immutable_digest_mismatch')
    return json.loads(raw)


def stable_content(batch):
    # Ignore volatile HTML response hashes ONLY for semantic deduplication;
    # preserve the exact first observed hashed evidence bytes on disk. An image,
    # source URL, date, product or terms change creates a new immutable record.
    out=json.loads(canonical(batch))
    for k in ('archive','syndicated','grid'):
        if k in out:
            out[k].pop('sha256',None)
    return out


def persist(batch, root):
    raw = canonical(batch)
    e = batch['edition']
    kind = {'external-candidate-batch-v1':'external-candidates', 'external-source-evidence-v1':'external-source-evidence','external-review-packet-v1':'external-review'}[batch['format']]
    directory = root/'data'/kind/PILOT/(e['starts_on']+'_'+e['ends_on'])
    path = directory/(digest(raw)+'.json')
    directory.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=raw:
            raise CollectorError('immutable_conflict')
        return path, False
    if kind != 'external-review':
        for previous in sorted(directory.glob('*.json')):
            if stable_content(load_record(previous)) == stable_content(batch):
                return previous, False
    with path.open('xb') as f:
        f.write(raw)
    return path, True


def comparable_key(row):
    # A candidate-level comparison, not a verified price drop. Exclude offers
    # with ambiguous units, missing each-pack size or visibly conditional terms.
    display=row.get('price_text') or ''
    m=re.fullmatch(r'\$?(\d+\.\d{2})\s*(each|/\s*(?:lb|kg))',display,re.I)
    if not m or not row.get('description') or not row.get('name') or price(row.get('price_field_cad')) is None:
        return None
    if price(m.group(1)) != price(row.get('price_field_cad')):
        return None
    unit=re.sub(r'\s+','',m.group(2)).lower()
    desc=row['description']
    if unit=='each' and not re.search(r'\b\d+(?:\.\d+)?\s*(?:g|kg|ml|l|lb|pack|ct)\b',desc,re.I):
        return None
    if re.search(r'\b(?:or|member|loyalty|points|when|limit)\b',row['name']+' '+desc,re.I) or any(row.get(k) for k in ('pre_price_text','post_price_text','sale_story')):
        return None
    return (row['name'].casefold(),desc.casefold(),(row.get('brand') or '').casefold(),unit)


def unique_comparables(rows):
    result={}; conflicts=set()
    for row in rows:
        key=comparable_key(row)
        if key is None:
            continue
        amount=Decimal(row['price_field_cad'])
        if key in result and result[key]!=amount:
            conflicts.add(key)
        result[key]=amount
    return {k:v for k,v in result.items() if k not in conflicts}


def source_identity(batch):
    return (batch.get('grid') or batch.get('syndicated') or {}).get('url','').split('?')[0].rsplit('/flipp/flyers/',1)[0]


def build_packet(root, candidate_path):
    current=load_record(candidate_path)
    if current.get('format')!='external-candidate-batch-v1' or current.get('retailer_id')!=PILOT:
        raise CollectorError('wrong_candidate_record')
    starts=current['edition']['starts_on']
    previous=[]
    for p in sorted((root/'data'/'external-candidates'/PILOT).glob('*/*.json')):
        b=load_record(p)
        if b['edition']['ends_on']<starts and b.get('format')==current['format'] and source_identity(b)==source_identity(current):
            previous.append((b['edition']['ends_on'],p,b))
    recent=[]
    if previous:
        recent=[(p,b) for end,p,b in previous if end==max(x[0] for x in previous)]
    now=unique_comparables(current['offers'])
    changes=[]; matched=0; baseline=None; status='initial_candidate_baseline'
    if len(recent)==1:
        p,b=recent[0]; baseline=str(p.relative_to(root)); old=unique_comparables(b['offers']); status='candidate_comparison_only'
        for key in sorted(now.keys() & old.keys()):
            matched+=1
            if now[key]!=old[key]:
                changes.append({'name':key[0],'description':key[1],'unit':key[3],'previous_price_cad':format(old[key],'.2f'),'current_price_cad':format(now[key],'.2f')})
    elif recent:
        status='ambiguous_previous_candidate_edition'
    return {'format':'external-review-packet-v1','retailer_id':PILOT,'edition':current['edition'],
            'candidate_path':str(candidate_path.relative_to(root)),'candidate_sha256':candidate_path.stem,
            'candidate_rows':len(current['offers']),'comparable_rows':len(now),'prior_candidate_path':baseline,
            'comparison_status':status,'matched_rows':matched,'candidate_price_changes':changes,
            'market_verified':False,'coverage_complete':False,'quality_authorized':False,'publication_authorized':False,'gmail_authorized':False}


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
        print(json.dumps({'status':'candidate_ready','path':str(path),'new':new,'offers':len(batch['offers']),'gmail_authorized':False}),flush=True)
        packet=build_packet(a.root,path)
        pp,pn=persist(packet,a.root)
        print(json.dumps({'status':'review_packet_ready','path':str(pp),'new':pn,'comparison_status':packet['comparison_status'],'matched_rows':packet['matched_rows'],'gmail_authorized':False}),flush=True)
    except (CollectorError, OSError, ValueError, TypeError) as exc:
        # No source body, URL query from arbitrary data, or secret in logs.
        print(json.dumps({'status':'blocked','code':f'HTTP_{exc.code}' if isinstance(exc,urllib.error.HTTPError) else str(exc) if isinstance(exc,CollectorError) else type(exc).__name__,'gmail_authorized':False}))
        return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())
