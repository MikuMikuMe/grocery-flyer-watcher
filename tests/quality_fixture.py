"""Synthetic source evidence only. Never use this fixture to authorize real mail."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from grocery_flyer_watch.quality_gate import FACTS, material, review_binding


def fixture(now=None):
    now = now or datetime.now(timezone.utc)
    # Use UTC for the synthetic market so midnight cannot split fixture and assertion clocks.
    today = now.date()
    end = (today + timedelta(days=4)).isoformat()
    start = today.isoformat()
    candidates = []
    for i in range(1, 12):
        name = f'Synthetic product {i}'
        candidates.append(dict(id=f'p{i}', promotion_id=f'promo{i}', unit_id='front' if i <= 3 else 'back',
            department='household', source_url='https://example.org/flyer/image',
            source_quote=f'{name} 500 g $4.00 Limit 2', source_name=name,
            price_cad='4.00', price_kind='cash', pricing='package', pack='500 g',
            starts_on=start, ends_on=end, verified_on=start,
            channel='in_store', terms=['Limit 2'], priority=5 if i <= 3 else (3 if i <= 7 else 2),
            prominent=i <= 3, decision='include' if i <= 9 else 'exclude',
            reason='Synthetic private assessment, not a real recommendation.',
            section='Best buys' if i <= 3 else ('Worth buying' if i <= 7 else 'Not worth treating as headline bargains'),
            assessment='Useful everyday purchase.', comparison=None))
    plan = dict(version=1, retailer='Example retailer', market='Example City, Ontario', timezone='UTC',
        campaign_key='synthetic-edition', period_label=f'{start} to {end}',
        change=dict(kind='new_edition', baseline_ref='private-previous-edition', evidence_refs=['https://example.org/editions']),
        coverage=dict(inventory_url='https://example.org/editions', inventory_complete=True,
            expected_unit_ids=['front', 'back'], partial_note='', units=[
                dict(id='front', url='https://example.org/flyer/front', status='reviewed', evidence_ref='synthetic-read-1',candidate_ids=['p1','p2','p3'],note=''),
                dict(id='back',url='https://example.org/flyer/back',status='reviewed',evidence_ref='synthetic-read-2',candidate_ids=[f'p{i}' for i in range(4,12)],note='')]),
        candidates=candidates,selected_ids=[f'p{i}' for i in range(1,10)],
        second_pass=dict(source_unit_ids=['front','back'],candidate_ids=[f'p{i}' for i in range(1,12)],
            prominent_ids=['p1','p2','p3'],omission_notes={},unresolved=[]),shortfall=dict(reason='',reviewed=False))
    audit = dict(source_scope='weekly-flyer',source_kind='flyer',edition=dict(starts_on=start,ends_on=end),
        baseline=dict(retailer=plan['retailer'],market=plan['market'],source_scope='weekly-flyer',
            starts_on=(today-timedelta(days=7)).isoformat(),ends_on=(today-timedelta(days=1)).isoformat(),
            source_sha256='a'*64,inventory_complete=True,offers=[],reference='private-previous-edition'),
        trigger_ids=[],source_sha256='b'*64,page_proofs=[],fact_proofs={},partial_exception=None,
        privacy_reviewed=True,forbidden_phrases=['PRIVATE_INTERNAL_MARKER'],reviewed_bundle_sha256='')
    for i, u in enumerate(plan['coverage']['units']):
        audit['page_proofs'].append(dict(unit_id=u['id'],role=u['id'],departments=['household'],
            lead_ids=['p1','p2','p3'] if i==0 else [],content_sha256=str(i+1)*64,observed_at=now.isoformat(),
            first_read_ref=f'synthetic-first-{i}',second_read_ref=f'synthetic-second-{i}'))
    for c in candidates[:9]:
        audit['fact_proofs'][c['id']] = dict(facts={k:deepcopy(c[k]) for k in FACTS},source_url=c['source_url'],
            read_ref=f"synthetic-label-{c['id']}",observed_at=now.isoformat(),price_excerpt='$4.00',
            terms_excerpt='Limit 2',validity_excerpt=f'Printed synthetic validity {start} to {end}',
            channel_excerpt='Synthetic regional in-store advertisement',local_scope_verified=True,
            comparison_window=None)
    bundle = {'format':'quality-bundle-v1','plan':plan,'audit':audit}
    seal(bundle)
    profile = {k:plan[k] for k in ('retailer','market','timezone')}
    return bundle, profile, now


def seal(bundle):
    """TEST ONLY: stand in for an actual second source-review binding."""
    bundle['audit']['reviewed_bundle_sha256'] = review_binding(bundle)


def sync_proof(bundle, cid='p1'):
    c = next(c for c in bundle['plan']['candidates'] if c['id']==cid)
    bundle['audit']['fact_proofs'][cid]['facts'] = {k:deepcopy(c[k]) for k in FACTS}


def make_material(bundle, *, collection=False, new_item=False, complete=True):
    p,a=bundle['plan'],bundle['audit']
    p['change']['kind']='material_offer_change'
    if collection:
        a['source_scope']='deals-centre'
        a['source_kind']='collection'
        a['edition']={'starts_on':None,'ends_on':None}
        p['period_label']='Verified collection offers'
        for c in p['candidates']:
            c['starts_on']=c['ends_on']=None
        for cid in p['selected_ids']:
            sync_proof(bundle,cid)
    a['baseline'].update(source_scope=a['source_scope'],**a['edition'],inventory_complete=complete)
    old=material(p['candidates'][0])
    old['price_cad']='6'
    a['baseline']['offers']=[] if new_item else [old]
    a['trigger_ids']=['p1']
    seal(bundle)
