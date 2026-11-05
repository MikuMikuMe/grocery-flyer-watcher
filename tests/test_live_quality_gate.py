"""Failure-driven regression tests; fixtures are synthetic, transport is never real."""
import copy
from datetime import timedelta
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grocery_flyer_watch import review
from grocery_flyer_watch.quality_gate import (FACTS, artifacts, check, material, read_json,
    review_binding, shopping_body, verify_artifacts, write_artifacts)
from grocery_flyer_watch.reviewed_delivery import (AmbiguousDelivery, Journal, KnownDeliveryFailure,
    _smtp_transport, authorize_external, preflight, publication_urls, run_profiles, send)
from quality_fixture import fixture, make_material, seal, sync_proof


class GateTests(unittest.TestCase):
    def setUp(self):
        self.b,self.profile,self.now=fixture()

    def rejects(self, code):
        seal(self.b)
        with self.assertRaisesRegex(review.ReviewError,code):
            check(self.b,self.profile,now=self.now)

    def test_valid_nine_item_bundle(self):
        a=check(self.b,self.profile,now=self.now)
        self.assertEqual(len(a.selection['items']),9)
        self.assertEqual(shopping_body(a.selection).count('- **'),9)
        self.assertNotIn('Prices CAD.',shopping_body(a.selection))

    def test_every_retailer_uses_same_gate(self):
        for ret in ('Metro','Shoppers Drug Mart','Rexall','Staples','Food Basics','Walmart','Costco'):
            self.b['plan']['retailer']=self.profile['retailer']=ret
            self.b['audit']['baseline']['retailer']=ret
            seal(self.b)
            self.assertEqual(check(self.b,self.profile,now=self.now).selection['retailer'],ret)

    def test_profile_mismatch(self):
        self.profile['market']='Other city'
        self.rejects('profile_scope_mismatch')

    def test_missing_butcher_page(self):
        self.b['plan']['coverage']['expected_unit_ids'].append('butcher')
        self.rejects('source_pages_missing')

    def test_missing_page_proof(self):
        self.b['audit']['page_proofs'].pop()
        self.rejects('source_page_proof_missing')

    def test_front_or_back_not_claimed_by_generic_content(self):
        for p in self.b['audit']['page_proofs']: p['role']='content'
        self.rejects('front_or_back_not_accounted_for')

    def test_empty_second_source_read(self):
        self.b['audit']['page_proofs'][0]['second_read_ref']=''
        self.rejects('second_source_read_missing')

    def test_same_read_is_not_two_passes(self):
        p=self.b['audit']['page_proofs'][0];p['second_read_ref']=p['first_read_ref']
        self.rejects('second_pass_reused_first_read')

    def test_department_lead_not_silently_missing(self):
        self.b['audit']['page_proofs'][1]['lead_ids']=['omitted-pork']
        self.rejects('unassessed_department_lead')

    def test_candidate_department_requires_coverage(self):
        self.b['plan']['candidates'][0]['department']='poultry'
        self.rejects('department_not_accounted_for')

    def test_stale_page_read_blocked(self):
        self.b['audit']['page_proofs'][0]['observed_at']=(self.now-timedelta(hours=7)).isoformat()
        self.rejects('stale_source_evidence')

    def test_unknown_collection_extent_requires_exception(self):
        self.b['plan']['coverage']['inventory_complete']=False
        self.b['plan']['coverage']['partial_note']='Collection pagination stopped at the first page.'
        self.rejects('partial_exception_missing')

    def test_partial_exception_retries_and_disclosure_required(self):
        self.b['plan']['coverage']['inventory_complete']=False
        self.b['plan']['coverage']['partial_note']='Collection pagination stopped at the first page.'
        self.b['audit']['partial_exception']={'alternate_sources':['https://example.org/retry'],'reason':'Failed'}
        self.rejects('retry_alternate_sources_before_partial')
        self.b['audit']['partial_exception']['alternate_sources'].append('https://another.example/retry')
        seal(self.b)
        a=check(self.b,self.profile,now=self.now)
        self.assertIn('pagination',a.selection['coverage_note'])

    def test_skinless_never_promoted_to_boneless(self):
        c=self.b['plan']['candidates'][0]
        c['source_quote']='Skinless chicken breast 500 g $4.00'
        c['source_name']='Boneless skinless chicken breast'
        self.rejects('product_description_not_in_evidence')

    def test_unsupported_fact_disguised_in_assessment(self):
        self.b['plan']['candidates'][0]['assessment']='Boneless chicken at a great price.'
        self.rejects('factual_claim_in_unbound_assessment')

    def test_numeric_savings_not_hidden_in_assessment(self):
        self.b['plan']['candidates'][0]['assessment']='Fifty percent cheaper.'
        self.rejects('factual_claim_in_unbound_assessment')

    def test_wrong_selected_price(self):
        self.b['plan']['candidates'][0]['price_cad']='8.00'
        self.rejects('cash_price_not_in_evidence')

    def test_matching_amount_wrong_unit_proximity(self):
        c=self.b['plan']['candidates'][0]
        c.update(source_quote='Synthetic product 1 500 g $4.00/kg or another $9.00/lb Limit 2',pricing='per_lb',pack='')
        sync_proof(self.b)
        self.b['audit']['fact_proofs']['p1']['price_excerpt']='$4.00/kg or another $9.00/lb'
        self.rejects('price_and_unit_not_bound_together')

    def test_regular_price_not_mistaken_for_checkout(self):
        c=self.b['plan']['candidates'][0]
        c['source_quote']='Synthetic product 1 500 g Was $4.00 now $3.00 Limit 2'
        self.b['audit']['fact_proofs']['p1']['price_excerpt']='Was $4.00'
        self.rejects('regular_or_saving_price_not_checkout')

    def test_costco_save_amount_is_not_price(self):
        self.b['plan']['candidates'][0]['source_quote']='Synthetic product 1 500 g SAVE $4.00 Limit 2'
        self.rejects('cash_price_not_in_evidence')

    def test_changed_terms_vs_evidence_blocked(self):
        self.b['plan']['candidates'][0]['terms']=[]
        self.rejects('claim_differs_from_source_facts')

    def test_condition_must_appear_in_evidence(self):
        self.b['plan']['candidates'][0]['terms']=['Members only']
        sync_proof(self.b)
        self.rejects('condition_not_in_evidence')

    def test_expired_short_offer_in_active_week(self):
        c=self.b['plan']['candidates'][0]
        c['starts_on']=(self.now.date()-timedelta(days=3)).isoformat()
        c['ends_on']=(self.now.date()-timedelta(days=1)).isoformat()
        self.rejects('expired_item_promotion')

    def test_null_dates_cannot_hide_weekend_expiry(self):
        c=self.b['plan']['candidates'][0];c['starts_on']=c['ends_on']=None
        sync_proof(self.b)
        self.rejects('dated_flyer_item_dates_required')

    def test_header_cannot_claim_wrong_period(self):
        self.b['plan']['period_label']='Next month'
        self.rejects('header_dates_do_not_match_edition')

    def test_local_claim_needs_local_scope_evidence(self):
        self.b['audit']['fact_proofs']['p1']['local_scope_verified']=False
        self.rejects('local_purchase_claim_not_verified')

    def test_shipping_only_rejected(self):
        self.b['plan']['candidates'][0]['channel']='shipping_only'
        self.rejects('ineligible_purchase_channel')

    def test_terms_and_dates_plan_are_bound_to_final_review(self):
        self.b['plan']['candidates'][0]['assessment']='Different harmless verdict.'
        with self.assertRaisesRegex(review.ReviewError,'bundle_changed_after_second_review'):
            check(self.b,self.profile,now=self.now)

    def test_selected_facts_cannot_be_subset_of_digest(self):
        del self.b['audit']['fact_proofs']['p9']
        self.rejects('selected_fact_evidence_missing')

    def test_evidence_freshness_at_send_time(self):
        with self.assertRaises(review.ReviewError):
            check(self.b,self.profile,now=self.now+timedelta(hours=7))

    def test_no_source_change_blocks_editorial_relabel(self):
        self.b['audit']['source_sha256']='a'*64
        self.rejects('no_source_content_change')

    def test_wrong_baseline_retailer(self):
        self.b['audit']['baseline']['retailer']='Different'
        self.rejects('baseline_wrong_market_or_retailer')

    def test_same_edition_not_new_by_renaming_campaign(self):
        self.b['audit']['baseline'].update(self.b['audit']['edition'])
        self.rejects('edition_not_newer_than_baseline')

    def test_order_or_ranking_never_changes_event_key(self):
        a=check(self.b,self.profile,now=self.now)
        self.b['plan']['selected_ids'].reverse()
        self.b['plan']['campaign_key']='another-editorial-label'
        seal(self.b)
        b=check(self.b,self.profile,now=self.now)
        self.assertEqual(a.event_id,b.event_id)
        self.assertNotEqual(a.selection['selection_sha256'],b.selection['selection_sha256'])

    def test_collection_reorder_is_not_change(self):
        make_material(self.b,collection=True)
        self.b['audit']['baseline']['offers']=[material(self.b['plan']['candidates'][0])]
        self.rejects('reorder_restock_or_editorial_not_material')

    def test_new_item_in_partial_collection_not_new_deal(self):
        make_material(self.b,collection=True,new_item=True,complete=False)
        self.rejects('new_to_partial_coverage_is_not_new_offer')

    def test_known_price_change_in_partial_collection_allowed(self):
        make_material(self.b,collection=True,complete=False)
        a=check(self.b,self.profile,now=self.now)
        self.assertEqual(a.kind,'material_offer_change')
        self.assertTrue(a.trigger_fingerprints)
        self.assertEqual(a.selection['items'][0]['ends_on'],None)

    def test_private_rationale_not_exported(self):
        self.b['plan']['candidates'][0]['reason']='PRIVATE_INTERNAL_MARKER'
        seal(self.b)
        data=artifacts(check(self.b,self.profile,now=self.now))
        self.assertNotIn(b'PRIVATE_INTERNAL_MARKER',b''.join(data.values()))
        self.assertNotIn(b'baseline_ref',b''.join(data.values()))

    def test_private_phrase_in_public_prose_blocked(self):
        self.b['plan']['candidates'][0]['assessment']='PRIVATE_INTERNAL_MARKER'
        self.rejects('private_phrase_in_public_output')

    def test_build_and_reconcile_artifacts(self):
        a=check(self.b,self.profile,now=self.now)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'public'
            write_artifacts(a,out)
            verify_artifacts(a,out)
            p=out/'selection.json'
            data=json.loads(p.read_text());data['items']=data['items'][:1]
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(review.ReviewError,'public_artifact_differs'):
                verify_artifacts(a,out)

    def test_public_output_directory_is_never_overwritten(self):
        a=check(self.b,self.profile,now=self.now)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):write_artifacts(a,tmp)

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'plan.json';path.write_text('{"format":1,"format":2}')
            with self.assertRaisesRegex(review.ReviewError,'duplicate_json_key'):read_json(path)

    def test_nonfinite_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'plan.json';path.write_text('{"price":NaN}')
            with self.assertRaisesRegex(review.ReviewError,'nonfinite_json'):read_json(path)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.b,self.p,self.now=fixture()
        self.a=check(self.b,self.p,now=self.now)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.j=Journal(self.root/'private'/'journal.sqlite');self.addCleanup(self.j.close)
        self.j.seed(self.p['retailer'],self.p['market'],'weekly-flyer',
                    self.b['audit']['baseline']['starts_on'],self.b['audit']['baseline']['ends_on'])
        self.pub={'repository':'example/project','commit':'a'*40,
                  'directory':'reports/reviewed/'+self.a.selection['selection_sha256']}
        self.fetch=lambda u:artifacts(self.a)[u.rsplit('/',1)[-1]]
        self.recipients=['first@example.invalid','second@example.invalid']
        self.j.configure_recipients(self.recipients)

    def send(self,transport=None,**kw):
        return send(self.b,self.p,self.pub,self.j,self.recipients,now=self.now,
                    fetcher=self.fetch,transport=transport or Mock(return_value='synthetic-accepted'),**kw)

    def test_publication_matches_before_delivery(self):
        a,body,url=preflight(self.b,self.p,self.pub,now=self.now,fetcher=self.fetch)
        self.assertIn('/'+'a'*40+'/',url)
        self.assertEqual(body.count('- **'),9)
        self.assertTrue(body.startswith(shopping_body(a.selection)))

    def test_publication_mismatch_blocks(self):
        with self.assertRaisesRegex(review.ReviewError,'published_artifact_mismatch'):
            preflight(self.b,self.p,self.pub,now=self.now,fetcher=lambda u:b'wrong')

    def test_branch_link_not_publication_proof(self):
        self.pub['commit']='main'
        with self.assertRaisesRegex(review.ReviewError,'requires_commit'):
            preflight(self.b,self.p,self.pub,now=self.now,fetcher=self.fetch)

    def test_non_versioned_path_rejected(self):
        self.pub['directory']='reports/latest'
        with self.assertRaisesRegex(review.ReviewError,'content_addressed'):
            preflight(self.b,self.p,self.pub,now=self.now,fetcher=self.fetch)

    def test_no_live_call_after_failed_gate(self):
        self.b['plan']['candidates'][0]['source_name']='Invented name'
        transport=Mock()
        self.assertEqual(self.send(transport),['blocked','blocked'])
        transport.assert_not_called()

    def test_bad_publication_calls_no_transport(self):
        self.fetch=lambda _:b'wrong';transport=Mock()
        self.assertEqual(self.send(transport),['blocked','blocked'])
        transport.assert_not_called()

    def test_recipients_receive_separate_messages_only_once(self):
        transport=Mock(return_value='synthetic-accepted')
        self.assertEqual(self.send(transport),['sent','sent'])
        self.assertEqual(self.send(transport),['already_handled','already_handled'])
        self.assertEqual(transport.call_count,2)
        for call in transport.call_args_list:
            recipient,_,body,_,_=call.args
            self.assertNotIn(recipient,body)
            self.assertNotIn('other@example.invalid',body)

    def test_new_recipient_does_not_get_old_event_backfill(self):
        self.assertEqual(self.send(),['sent','sent'])
        self.recipients.append('new@example.invalid')
        transport=Mock()
        self.assertEqual(self.send(transport),['already_handled','already_handled','already_handled'])
        transport.assert_not_called()

    def test_one_recipient_failure_retries_only_failed(self):
        transport=Mock(side_effect=[KnownDeliveryFailure('offline fixture'),'accepted','accepted'])
        self.assertEqual(self.send(transport),['failed','sent'])
        self.assertEqual(self.send(transport),['sent','already_handled'])
        self.assertEqual([c.args[0] for c in transport.call_args_list],
                         [self.recipients[0],self.recipients[1],self.recipients[0]])

    def test_ambiguous_failure_does_not_auto_resend(self):
        transport=Mock(side_effect=[AmbiguousDelivery('unknown'),'accepted'])
        self.assertEqual(self.send(transport),['uncertain','sent'])
        self.assertEqual(self.send(transport),['blocked','already_handled'])
        self.assertEqual(transport.call_count,2)

    def test_uncertainty_resolved_by_explicit_sent_evidence(self):
        transport=Mock(side_effect=[AmbiguousDelivery('unknown'),'accepted','accepted'])
        self.send(transport)
        self.j.reconcile(self.a.event_id,self.recipients[0],sent=False,evidence_ref='actual-lookup-fixture',
                         checked_at=self.now.isoformat(),now=self.now)
        self.assertEqual(self.send(transport),['sent','already_handled'])

    def test_empty_journal_does_not_backfill(self):
        with Journal(self.root/'new.sqlite') as j:
            transport=Mock()
            result=send(self.b,self.p,self.pub,j,self.recipients,now=self.now,fetcher=self.fetch,transport=transport)
            self.assertEqual(result,['blocked','blocked']);transport.assert_not_called()

    def test_seed_current_edition_suppresses_editorial_backfill(self):
        self.j.seed(self.p['retailer'],self.p['market'],'weekly-flyer',**self.b['audit']['edition'])
        transport=Mock()
        self.assertEqual(self.send(transport),['already_handled','already_handled'])
        transport.assert_not_called()

    def test_changed_shortlist_not_new_email(self):
        self.send()
        self.b['plan']['selected_ids'].reverse();seal(self.b)
        changed=check(self.b,self.p,now=self.now)
        self.a=changed
        self.pub['directory']='reports/reviewed/'+changed.selection['selection_sha256']
        transport=Mock()
        self.assertEqual(self.send(transport),['already_handled','already_handled'])
        transport.assert_not_called()

    def test_expired_items_block_before_transport(self):
        c=self.b['plan']['candidates'][0]
        c['ends_on']=(self.now.date()-timedelta(days=1)).isoformat()
        transport=Mock()
        self.assertEqual(self.send(transport),['blocked','blocked']);transport.assert_not_called()

    def test_same_material_offer_not_emailed_from_two_collections(self):
        make_material(self.b,collection=True)
        self.j.seed(self.p['retailer'],self.p['market'],'deals-centre',None,None)
        self.a=check(self.b,self.p,now=self.now)
        self.pub['directory']='reports/reviewed/'+self.a.selection['selection_sha256']
        self.assertEqual(self.send(),['sent','sent'])
        self.b['audit']['source_scope']=self.b['audit']['baseline']['source_scope']='clearance-centre'
        self.j.seed(self.p['retailer'],self.p['market'],'clearance-centre',None,None)
        seal(self.b)
        self.a=check(self.b,self.p,now=self.now)
        self.pub['directory']='reports/reviewed/'+self.a.selection['selection_sha256']
        transport=Mock()
        self.assertEqual(self.send(transport),['already_handled','already_handled']);transport.assert_not_called()

    def test_body_tamper_blocks_external_gmail_authorization(self):
        _,body,_=preflight(self.b,self.p,self.pub,now=self.now,fetcher=self.fetch)
        lookup=dict(recipient=self.recipients[0],event_id=self.a.event_id,checked_at=self.now.isoformat(),
                    already_sent=False,evidence_ref='synthetic-sent-search')
        with self.assertRaisesRegex(review.ReviewError,'outgoing_body_differs'):
            authorize_external(self.b,self.p,self.pub,self.j,self.recipients[0],lookup,
                               body.replace('$4.00','$2.00',1),now=self.now,fetcher=self.fetch)

    def test_external_authorization_is_recipient_specific(self):
        _,body,_=preflight(self.b,self.p,self.pub,now=self.now,fetcher=self.fetch)
        lookup=dict(recipient=self.recipients[0],event_id=self.a.event_id,checked_at=self.now.isoformat(),
                    already_sent=False,evidence_ref='synthetic-sent-search')
        auth=authorize_external(self.b,self.p,self.pub,self.j,self.recipients[0],lookup,body,
                                now=self.now,fetcher=self.fetch)
        self.assertEqual(auth['status'],'authorized')
        self.j.finish(auth['event_id'],auth['recipient'],auth['ticket'],'sent','synthetic-message-id')
        again=authorize_external(self.b,self.p,self.pub,self.j,self.recipients[0],lookup,body,
                                 now=self.now,fetcher=self.fetch)
        self.assertEqual(again['status'],'already_handled')
        with self.assertRaisesRegex(review.ReviewError,'sent_lookup_scope_mismatch'):
            authorize_external(self.b,self.p,self.pub,self.j,self.recipients[1],lookup,body,
                               now=self.now,fetcher=self.fetch)

    def test_external_lookup_must_be_fresh(self):
        _,body,_=preflight(self.b,self.p,self.pub,now=self.now,fetcher=self.fetch)
        lookup=dict(recipient=self.recipients[0],event_id=self.a.event_id,
            checked_at=(self.now-timedelta(minutes=20)).isoformat(),already_sent=False,evidence_ref='old')
        with self.assertRaisesRegex(review.ReviewError,'sent_lookup_stale'):
            authorize_external(self.b,self.p,self.pub,self.j,self.recipients[0],lookup,body,
                               now=self.now,fetcher=self.fetch)

    def test_journal_cannot_be_inside_checkout(self):
        repo=self.root/'repo';repo.mkdir();(repo/'.git').mkdir()
        with self.assertRaisesRegex(review.ReviewError,'outside_checkout'):
            Journal(repo/'private'/'state.sqlite')

    def test_sequential_profiles_continue_after_failure(self):
        names=['metro','shoppers','rexall','staples','food-basics','walmart','costco']
        seen=[]
        def worker(p):
            seen.append(p['id'])
            if p['id']=='metro':raise RuntimeError('synthetic')
            return 'unchanged'
        result=run_profiles([{'id':n} for n in names],worker)
        self.assertEqual(seen,names)
        self.assertEqual(result['metro'],'insufficient_evidence')
        self.assertEqual(result['costco'],'unchanged')

    def test_acknowledgement_failure_does_not_duplicate_or_skip_other_recipient(self):
        actual_finish = self.j.finish
        def fail_first_ack(event, recipient, ticket, status, receipt=''):
            if recipient == self.recipients[0] and status == 'sent':
                raise OSError('synthetic journal failure after acceptance')
            return actual_finish(event, recipient, ticket, status, receipt)
        transport = Mock(return_value='synthetic accepted')
        with patch.object(self.j, 'finish', side_effect=fail_first_ack):
            self.assertEqual(self.send(transport), ['uncertain', 'sent'])
        self.assertEqual(self.send(transport), ['blocked', 'already_handled'])
        self.assertEqual(transport.call_count, 2)

    def test_failed_send_state_write_failure_does_not_skip_other_recipient(self):
        actual_finish = self.j.finish
        def fail_first_record(event, recipient, ticket, status, receipt=''):
            if recipient == self.recipients[0]:
                raise OSError('synthetic journal write failure')
            return actual_finish(event, recipient, ticket, status, receipt)
        transport = Mock(side_effect=[KnownDeliveryFailure('synthetic refusal'), 'accepted'])
        with patch.object(self.j, 'finish', side_effect=fail_first_record):
            self.assertEqual(self.send(transport), ['uncertain', 'sent'])
        self.assertEqual(transport.call_count, 2)

    def test_forged_acknowledgement_ticket_rejected(self):
        _, body, report_url = preflight(self.b, self.p, self.pub, now=self.now, fetcher=self.fetch)
        self.j.reserve(self.a, self.recipients[0], body, report_url, self.now)
        with self.assertRaisesRegex(review.ReviewError, 'invalid_delivery_ticket'):
            self.j.finish(self.a.event_id, self.recipients[0], 'wrong-ticket', 'sent', 'fictional')

    def test_reconcile_sent_marks_only_that_recipient_handled(self):
        transport = Mock(side_effect=[AmbiguousDelivery('unknown'), 'accepted'])
        self.send(transport)
        self.j.reconcile(self.a.event_id, self.recipients[0], sent=True,
                         evidence_ref='synthetic-provider-confirmation',
                         checked_at=self.now.isoformat(), now=self.now)
        self.assertEqual(self.send(transport), ['already_handled', 'already_handled'])
        self.assertEqual(transport.call_count, 2)

    def test_smtp_enforces_tls_and_one_recipient(self):
        env={'FLYER_MAIL_FROM':'sender@example.invalid','FLYER_SMTP_HOST':'smtp.example.invalid',
             'FLYER_SMTP_MODE':'ssl'}
        with patch('grocery_flyer_watch.reviewed_delivery.smtplib.SMTP_SSL') as server:
            server.return_value.send_message.return_value={}
            receipt=_smtp_transport(self.recipients[0],'Synthetic subject','Synthetic body','e'*64,env)
            message=server.return_value.send_message.call_args.args[0]
            self.assertEqual(message['To'],self.recipients[0])
            self.assertIsNone(message['Cc']);self.assertIsNone(message['Bcc'])
            self.assertNotIn(self.recipients[1],str(message))
            self.assertIsNotNone(server.call_args.kwargs['context'])
            self.assertTrue(receipt.startswith('<flyer-'))

    def test_smtp_connection_failure_known_no_acceptance(self):
        env={'FLYER_MAIL_FROM':'sender@example.invalid','FLYER_SMTP_HOST':'smtp.example.invalid'}
        with patch('grocery_flyer_watch.reviewed_delivery.smtplib.SMTP_SSL',side_effect=OSError('private detail')):
            with self.assertRaisesRegex(KnownDeliveryFailure,'smtp_not_started'):
                _smtp_transport(self.recipients[0],'s','b','e'*64,env)

    def test_disconnect_during_data_is_ambiguous(self):
        env={'FLYER_MAIL_FROM':'sender@example.invalid','FLYER_SMTP_HOST':'smtp.example.invalid'}
        with patch('grocery_flyer_watch.reviewed_delivery.smtplib.SMTP_SSL') as server:
            server.return_value.send_message.side_effect=OSError('lost acknowledgement')
            with self.assertRaises(AmbiguousDelivery):_smtp_transport(self.recipients[0],'s','b','e'*64,env)

    def test_close_failure_after_acceptance_not_retried(self):
        env={'FLYER_MAIL_FROM':'sender@example.invalid','FLYER_SMTP_HOST':'smtp.example.invalid'}
        with patch('grocery_flyer_watch.reviewed_delivery.smtplib.SMTP_SSL') as server:
            server.return_value.send_message.return_value={}
            server.return_value.close.side_effect=OSError('disconnect')
            self.assertTrue(_smtp_transport(self.recipients[0],'s','b','e'*64,env))


if __name__=='__main__':unittest.main()
