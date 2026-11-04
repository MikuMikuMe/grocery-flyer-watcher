"""Synthetic regression cases only; no real receipt, email or customer data."""
import copy
from datetime import datetime, timedelta
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grocery_flyer_watch.review import ReviewError, check_body, main, project, render, validate

REPORT = 'https://example.org/reports/synthetic'


def fixture():
    today = datetime.now(ZoneInfo('America/Toronto')).date()
    end = (today + timedelta(days=4)).isoformat()
    candidates = []
    for i in range(1, 12):
        name = f'Synthetic product {i}'
        # Source-native names; no inferred claims or real advertised prices.
        candidates.append(dict(id=f'p{i}', promotion_id=f'promo{i}', unit_id='front' if i <= 3 else 'inside',
            department='household', source_url='https://example.org/flyer/image',
            source_quote=f'{name} 500 g $4.00 Limit 2', source_name=name,
            price_cad='4.00', price_kind='cash', pricing='package', pack='500 g',
            starts_on=today.isoformat(), ends_on=end, verified_on=today.isoformat(),
            channel='in_store', terms=['Limit 2'], priority=5 if i <= 3 else (3 if i <= 7 else 2),
            prominent=i <= 3, decision='include' if i <= 9 else 'exclude',
            reason='Synthetic assessment for tests; not a real value claim.',
            section='Best buys' if i <= 3 else ('Worth buying' if i <= 7 else 'Not worth treating as headline bargains'),
            assessment='Synthetic assessment.', comparison=None))
    return dict(version=1, retailer='Example retailer', market='Example City, Ontario',
        timezone='America/Toronto', campaign_key='synthetic-edition', period_label=f'{today.isoformat()} to {end}',
        change=dict(kind='new_edition', baseline_ref='private-previous-edition', evidence_refs=['https://example.org/editions']),
        coverage=dict(inventory_url='https://example.org/editions', inventory_complete=True,
            expected_unit_ids=['front', 'inside'], partial_note='', units=[
                dict(id='front', url='https://example.org/flyer/front', status='reviewed', evidence_ref='synthetic-read-1', candidate_ids=['p1','p2','p3'], note=''),
                dict(id='inside', url='https://example.org/flyer/inside', status='reviewed', evidence_ref='synthetic-read-2', candidate_ids=[f'p{i}' for i in range(4,12)], note='')]),
        candidates=candidates, selected_ids=[f'p{i}' for i in range(1,10)],
        second_pass=dict(source_unit_ids=['front','inside'], candidate_ids=[f'p{i}' for i in range(1,12)],
            prominent_ids=['p1','p2','p3'], omission_notes={}, unresolved=[]),
        shortfall=dict(reason='', reviewed=False))


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()

    def rejects(self, code):
        with self.assertRaisesRegex(ReviewError, code):
            validate(self.p)

    def test_valid_nine_items_render_from_one_selection(self):
        s = project(self.p)
        body = render(s, REPORT)
        check_body(self.p, body, REPORT)
        self.assertEqual(len(s['items']), 9)
        self.assertEqual(body.count('- **'), 9)
        self.assertIn('Not worth treating as headline bargains', body)
        self.assertNotIn('Prices CAD.', body)

    def test_all_seven_retailers_share_gate(self):
        for retailer in ('Metro','Shoppers Drug Mart','Rexall','Staples','Food Basics','Walmart','Costco'):
            with self.subTest(retailer=retailer):
                self.p['retailer'] = retailer
                validate(self.p)

    def test_no_receipt_or_private_rationale_export(self):
        self.p['candidates'][0]['reason'] = 'PRIVATE_INTERNAL_MARKER'
        public = json.dumps(project(self.p))
        self.assertNotIn('PRIVATE_INTERNAL_MARKER', public)
        self.assertNotIn('baseline_ref', public)
        self.assertNotIn('source_quote', public)
        self.assertNotIn('evidence_ref', public)

    def test_missing_butcher_page_blocked(self):
        self.p['coverage']['expected_unit_ids'].append('butcher')
        self.rejects('source_pages_missing')

    def test_page_left_unreviewed_blocked(self):
        self.p['coverage']['units'][1]['status'] = 'unreviewed'
        self.rejects('unreviewed_source_unit')

    def test_blocked_page_requires_real_partial_disclosure(self):
        self.p['coverage']['expected_unit_ids'].append('unavailable-page')
        self.p['coverage']['units'].append(dict(id='unavailable-page',url='https://example.org/blocked',status='blocked',evidence_ref='synthetic-failed-read',candidate_ids=[],note='Access unavailable'))
        self.rejects('partial_coverage_must_be_disclosed')
        self.p['coverage']['partial_note'] = 'Coverage: one advertised page could not be read; the listed offers were verified on accessible pages.'
        self.assertIn('Coverage:', render(project(self.p), REPORT))

    def test_unknown_collection_total_cannot_claim_full_coverage(self):
        self.p['coverage']['inventory_complete'] = False
        self.rejects('partial_coverage_must_be_disclosed')

    def test_forgotten_inventory_candidate_blocked(self):
        self.p['coverage']['units'][1]['candidate_ids'].append('missed-wings')
        self.rejects('page_candidate_inventory_mismatch')

    def test_prominent_beef_wings_or_pork_cannot_be_silently_excluded(self):
        for name in ('beef', 'wings', 'pork'):
            with self.subTest(offer=name):
                self.p = fixture()
                c = self.p['candidates'][9]
                c['source_name'] = f'Synthetic {name}'
                c['source_quote'] = f'Synthetic {name} 500 g $4.00'
                c['prominent'] = True
                c['priority'] = 5
                self.p['second_pass']['prominent_ids'].append('p10')
                self.rejects('prominent_or_strong_offer_omitted_without_audit')

    def test_reasoned_omission_allowed_no_forced_category_quota(self):
        c = self.p['candidates'][9]
        c['prominent'] = True
        self.p['second_pass']['prominent_ids'].append('p10')
        self.p['second_pass']['omission_notes']['p10'] = 'Reviewed against source; same-use candidate with less favourable terms.'
        validate(self.p)

    def test_second_pass_must_revisit_pages(self):
        self.p['second_pass']['source_unit_ids'] = ['front']
        self.rejects('second_pass_coverage_gap')

    def test_unresolved_audit_blocks_send(self):
        self.p['second_pass']['unresolved'] = ['check ambiguous cut']
        self.rejects('unresolved_audit_findings')

    def test_skinless_cannot_be_renamed_boneless(self):
        c = self.p['candidates'][0]
        c['source_quote'] = 'Fresh skinless chicken breast 500 g $4.00'
        c['source_name'] = 'Fresh boneless skinless chicken breast'
        self.rejects('product_description_not_in_evidence')

    def test_unit_not_in_source_blocks(self):
        self.p['candidates'][0]['pricing'] = 'per_lb'
        self.rejects('price_unit_not_in_evidence')

    def test_integer_currency_price_is_supported(self):
        self.p['candidates'][0]['source_quote'] = 'Synthetic product 1 500 g $4 Limit 2'
        validate(self.p)

    def test_wrong_cash_price_blocks(self):
        self.p['candidates'][0]['price_cad'] = '7.00'
        self.rejects('cash_price_not_in_evidence')

    def test_wrong_pack_blocks(self):
        self.p['candidates'][0]['pack'] = '1 kg'
        self.rejects('pack_not_in_evidence')

    def test_costco_savings_are_not_cash(self):
        self.p['candidates'][0]['price_kind'] = 'saving_only'
        self.rejects('saving_amount_is_not_cash_price')

    def test_even_mislabelled_save_amount_is_not_cash(self):
        self.p['candidates'][0]['source_quote'] = 'Synthetic product 1 500 g SAVE $4.00'
        self.rejects('cash_price_not_in_evidence')

    def test_expired_weekend_offer_blocks_even_when_weekly_flyer_active(self):
        c = self.p['candidates'][0]
        c['starts_on'] = '2020-01-01'
        c['ends_on'] = '2020-01-02'
        self.rejects('expired_item_promotion')

    def test_undated_collection_not_given_invented_dates(self):
        for c in self.p['candidates']:
            c['starts_on'] = c['ends_on'] = None
        self.p['period_label'] = 'Verified collection offers'
        self.assertIn('No advertised end date.', render(project(self.p), REPORT))

    def test_stale_selected_evidence_blocks(self):
        self.p['candidates'][0]['verified_on'] = '2020-01-01'
        self.rejects('selected_offer_not_rechecked_today')

    def test_shipping_only_not_actionable(self):
        self.p['candidates'][0]['channel'] = 'shipping_only'
        self.rejects('ineligible_purchase_channel')

    def test_unknown_local_stock_cannot_be_best_buy(self):
        self.p['candidates'][0]['channel'] = 'unverified'
        self.rejects('unknown_local_eligibility_cannot_be_best_buy')

    def test_duplicate_promotion_variants_do_not_pad_count(self):
        self.p['candidates'][1]['promotion_id'] = 'promo1'
        self.rejects('same_offer_counted_twice')

    def test_mostly_weak_roundup_blocks(self):
        for c in self.p['candidates']:
            c['section'] = 'Not worth treating as headline bargains'
        self.rejects('roundup_mostly_weak_or_unverified')

    def test_under_eight_requires_explained_shortfall(self):
        self.p['selected_ids'].pop()
        self.p['candidates'][8]['decision'] = 'exclude'
        self.p['selected_ids'].pop()
        self.p['candidates'][7]['decision'] = 'exclude'
        self.rejects('shortfall_unexplained')
        self.p['shortfall'] = dict(reason='Only seven distinct verifiable useful or meaningfully comparable offers were supported by accessible evidence.',reviewed=True)
        validate(self.p)

    def test_initialization_editorial_and_unchanged_are_not_email_triggers(self):
        for kind in ('initialization', 'editorial', 'unchanged'):
            self.p['change']['kind'] = kind
            self.rejects('no_qualifying_change')

    def test_product_order_or_review_notes_not_new_campaign(self):
        first = project(self.p)
        self.p['candidates'][0]['reason'] = 'A different private assessment.'
        second = project(self.p)
        self.assertEqual(first, second)
        self.p['selected_ids'].reverse()
        self.assertEqual(first['campaign_key'], project(self.p)['campaign_key'])

    def test_email_and_report_drift_blocked(self):
        body = render(project(self.p), REPORT)
        with self.assertRaisesRegex(ReviewError, 'body_differs_from_reviewed_selection'):
            check_body(self.p, body.replace('$4.00', '$3.00', 1), REPORT)

    def test_purchase_conditions_preserved_in_render(self):
        self.p['candidates'][0]['terms'] = ['Members only; limit 2.']
        self.assertIn('Members only; limit 2.', render(project(self.p), REPORT))

    def test_private_contact_not_projected(self):
        self.p['candidates'][0]['assessment'] = 'private' + chr(64) + 'example.invalid'
        self.rejects('private_data_in_public_field')

    def test_meat_comparison_needs_bone_evidence(self):
        c = self.p['candidates'][0]
        c.update(source_name='Fresh skinless chicken breast',source_quote='Fresh skinless chicken breast 500 g $4.00',department='meat')
        c['comparison'] = dict(retailer='Other retailer',source_url='https://example.org/comparison',source_quote='Fresh boneless chicken breast 500 g $6.00',price_cad='6.00',pricing='package',kind='meat',ours=dict(species='chicken',cut='breast',bone='boneless',state='fresh'),theirs=dict(species='chicken',cut='breast',bone='boneless',state='fresh'))
        self.rejects('comparison_attribute_not_in_evidence')

    def test_explicit_matching_comparison_allowed(self):
        c = self.p['candidates'][0]
        c.update(source_name='Fresh boneless chicken breast',source_quote='Fresh boneless chicken breast 500 g $4.00',department='meat')
        facts = dict(species='chicken',cut='breast',bone='boneless',state='fresh')
        c['comparison'] = dict(retailer='Other retailer',source_url='https://example.org/comparison',source_quote='Fresh boneless chicken breast 500 g $6.00',price_cad='6.00',pricing='package',kind='meat',ours=facts,theirs=dict(facts))
        self.assertIn('Other retailer', render(project(self.p), REPORT))

    def test_different_package_cannot_be_compared_as_same_cost(self):
        self.test_explicit_matching_comparison_allowed()
        self.p['candidates'][0]['comparison']['source_quote'] = 'Fresh boneless chicken breast 900 g $6.00'
        self.rejects('comparison_pack_mismatch')

    def test_skin_attribute_must_match_in_meat_comparison(self):
        self.test_explicit_matching_comparison_allowed()
        self.p['candidates'][0]['comparison']['source_quote'] = 'Fresh boneless skinless chicken breast 500 g $6.00'
        self.rejects('comparison_additional_attribute_mismatch')

    def test_model_item_does_not_need_invented_pack_size(self):
        c = self.p['candidates'][0]
        c.update(source_name='Example chair MODEL-Z', source_quote='Example chair MODEL-Z $4.00',
                 pack='', pricing='each', department='furniture')
        validate(self.p)

    def test_cli_outputs_only_public_artifacts_no_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root/'private.json'
            plan.write_text(json.dumps(self.p),encoding='utf-8')
            with patch('sys.stdout',new_callable=io.StringIO):
                self.assertEqual(main([str(plan),'--report-url',REPORT,'--out',str(root/'public')]),0)
                self.assertEqual(main([str(plan),'--report-url',REPORT,'--check-body',str(root/'public/digest.md')]),0)
            self.assertEqual({p.name for p in (root/'public').iterdir()}, {'digest.md','selection.json'})
            self.assertNotIn('reason', (root/'public/selection.json').read_text())

    def test_cli_error_is_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'private.json'
            path.write_text('{broken JSON',encoding='utf-8')
            with patch('sys.stderr',new_callable=io.StringIO) as error:
                self.assertEqual(main([str(path),'--report-url',REPORT]),2)
            self.assertNotIn('broken JSON', error.getvalue())


if __name__ == '__main__':
    unittest.main()
