"""Synthetic regressions: a retailer-owned host is not a delivery prerequisite.

These records test validation semantics only. They are never real advertising evidence,
store-scope proof, independent source inspections, or authorization to send live email.
"""
from copy import deepcopy
from urllib.parse import urlsplit
import unittest

from grocery_flyer_watch import review
from grocery_flyer_watch.quality_gate import check
from quality_fixture import fixture, seal, sync_proof


RETAILERS = ('Metro', 'Shoppers Drug Mart', 'Rexall', 'Staples',
             'Food Basics', 'Walmart', 'Costco')


def archive_fixture(retailer='Metro'):
    bundle, profile, now = fixture()
    plan, audit = bundle['plan'], bundle['audit']
    plan['retailer'] = profile['retailer'] = audit['baseline']['retailer'] = retailer
    plan['change']['evidence_refs'] = ['https://archive.example.org/edition']
    plan['coverage']['inventory_url'] = 'https://archive.example.org/edition'
    for unit in plan['coverage']['units']:
        unit['url'] = f"https://archive.example.org/edition/{unit['id']}.jpg"
    for candidate in plan['candidates']:
        candidate['source_url'] = f"https://archive.example.org/edition/{candidate['unit_id']}.jpg"
    for cid, proof in audit['fact_proofs'].items():
        candidate = next(c for c in plan['candidates'] if c['id'] == cid)
        proof['source_url'] = candidate['source_url']
        proof['channel_excerpt'] = (
            'Synthetic regional in-store advertisement covers Example City; '
            'this is not an item-stock or checkout observation.'
        )
    seal(bundle)
    return bundle, profile, now


class AlternativeFlyerSourceTests(unittest.TestCase):
    def test_all_retailers_accept_reviewed_archive_advertising_evidence(self):
        for retailer in RETAILERS:
            with self.subTest(retailer=retailer):
                bundle, profile, now = archive_fixture(retailer)
                approved = check(bundle, profile, now=now)
                self.assertEqual(len(approved.selection['items']), 9)
                self.assertTrue(all(urlsplit(i['source_url']).hostname == 'archive.example.org'
                                    for i in approved.selection['items']))

    def test_regional_in_store_eligibility_does_not_require_shelf_stock(self):
        bundle, profile, now = archive_fixture()
        for proof in bundle['audit']['fact_proofs'].values():
            self.assertTrue(proof['local_scope_verified'])
            self.assertIn('not an item-stock', proof['channel_excerpt'])
        self.assertEqual(check(bundle, profile, now=now).kind, 'new_edition')

    def test_reviewed_mirror_replaces_unavailable_host_not_advertising_identity(self):
        bundle, profile, now = archive_fixture()
        first = check(bundle, profile, now=now)
        alternative = deepcopy(bundle)
        plan, audit = alternative['plan'], alternative['audit']
        def replacement(url):
            return url.replace('archive.example.org', 'mirror.example.org')
        plan['change']['evidence_refs'] = [replacement(x) for x in plan['change']['evidence_refs']]
        plan['coverage']['inventory_url'] = replacement(plan['coverage']['inventory_url'])
        for unit in plan['coverage']['units']:
            unit['url'] = replacement(unit['url'])
        for candidate in plan['candidates']:
            candidate['source_url'] = replacement(candidate['source_url'])
        for proof in audit['fact_proofs'].values():
            proof['source_url'] = replacement(proof['source_url'])
        seal(alternative)
        second = check(alternative, profile, now=now)
        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual(first.edition_id, second.edition_id)

    def test_shared_printed_edition_terms_need_not_be_unique_product_pages(self):
        bundle, profile, now = archive_fixture()
        proofs = list(bundle['audit']['fact_proofs'].values())
        self.assertEqual(len({p['validity_excerpt'] for p in proofs}), 1)
        self.assertEqual(len({p['terms_excerpt'] for p in proofs}), 1)
        self.assertLess(len({p['source_url'] for p in proofs}), len(proofs))
        check(bundle, profile, now=now)

    def test_archive_label_does_not_excuse_unverified_market_scope(self):
        bundle, profile, now = archive_fixture()
        bundle['audit']['fact_proofs']['p1']['local_scope_verified'] = False
        seal(bundle)
        with self.assertRaisesRegex(review.ReviewError, '^local_purchase_claim_not_verified$'):
            check(bundle, profile, now=now)

    def test_one_item_scope_gap_can_be_excluded_without_blocking_verified_items(self):
        bundle, profile, now = archive_fixture()
        candidate = bundle['plan']['candidates'][0]
        candidate.update(channel='unverified', decision='exclude',
                         reason='Synthetic regional variant is unresolved; other items are verified.')
        bundle['plan']['selected_ids'].remove('p1')
        del bundle['audit']['fact_proofs']['p1']
        bundle['plan']['second_pass']['omission_notes']['p1'] = candidate['reason']
        seal(bundle)
        self.assertEqual(len(check(bundle, profile, now=now).selection['items']), 8)

    def test_archive_price_still_must_match_the_actual_excerpt(self):
        bundle, profile, now = archive_fixture()
        bundle['plan']['candidates'][0]['price_cad'] = '3.00'
        sync_proof(bundle)
        seal(bundle)
        with self.assertRaisesRegex(review.ReviewError, '^cash_price_not_in_evidence$'):
            check(bundle, profile, now=now)

    def test_accessible_archive_does_not_replace_the_omission_review(self):
        bundle, profile, now = archive_fixture()
        bundle['plan']['second_pass']['unresolved'] = ['Synthetic unresolved front-page candidate']
        seal(bundle)
        with self.assertRaisesRegex(review.ReviewError, '^unresolved_audit_findings$'):
            check(bundle, profile, now=now)


if __name__ == '__main__':
    unittest.main()
