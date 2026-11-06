"""Offline GitHub/Gmail adapter tests. No real accounts, sources, writes or sends."""
import copy
from datetime import timedelta
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from quality_fixture import fixture, seal
from grocery_flyer_watch.quality_gate import artifacts, check
from grocery_flyer_watch.review import ReviewError
from grocery_flyer_watch.reviewed_delivery import preflight, publication_urls
from grocery_flyer_watch.repository_delivery import assessment, assessment_bytes, authorize, main
from grocery_flyer_watch.runtime_preflight import diagnose
from test_runtime_recovery import observations, NOW


class RepositoryDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.b, self.p, self.now = fixture()
        self.recipient = 'one' + chr(64) + 'example.invalid'
        self.other = 'two' + chr(64) + 'example.invalid'
        self.approved = check(self.b, self.p, now=self.now)
        self.record = assessment(self.b, self.p, now=self.now)
        self.publication = {'repository':'example/project', 'commit':'a'*40,
                            'directory':'reports/reviewed/'+self.record['selection_sha256']}
        _, urls = publication_urls(self.publication,self.approved)
        self.files = {urls[k]:v for k,v in artifacts(self.approved).items()}
        self.fetch = lambda u:self.files[u]
        _, self.body, _ = preflight(self.b,self.p,self.publication,now=self.now,fetcher=self.fetch)
        self.proof = {'repository':'example/project','commit':'a'*40,
            'path':'state/assessments/'+self.approved.event_id+'.json',
            'checked_at':self.now.isoformat(),'evidence_ref':'synthetic-github-read',
            'sha256':hashlib.sha256(assessment_bytes(self.record)).hexdigest()}
        self.lookup = {'recipient':self.recipient, 'event_id':self.approved.event_id,
            'checked_at':self.now.isoformat(),'already_sent':False,'evidence_ref':'synthetic-sent-search',
            'older_editions_checked':True,'equivalent_offers_checked':True}
        self.context = {'recipient':self.recipient,'authorized_recipients':[self.recipient,self.other],
            'eligible_since':(self.now-timedelta(days=1)).isoformat(),
            'eligibility_ref':'synthetic-private-roster','history_ref':'synthetic-original-campaign-review',
            'history_checked_at':self.now.isoformat(),'serial_execution':True,
            'prior_attempt':'not_attempted','attempt_ref':'synthetic-private-execution-history'}

    def auth(self):
        return authorize(self.b,self.p,self.publication,self.record,self.proof,self.lookup,
                         self.context,self.body,now=self.now,fetcher=self.fetch)

    def test_valid_without_database_or_journal(self):
        with patch('sqlite3.connect',side_effect=AssertionError('database forbidden')):
            result=self.auth()
        self.assertEqual(result['status'],'authorized')
        self.assertEqual(result['recipient'],self.recipient)
        self.assertNotIn(self.recipient,result['subject'])
        self.assertEqual(result['body_sha256'],hashlib.sha256(self.body.encode()).hexdigest())

    def test_public_record_allowlist_contains_no_private_history(self):
        text=assessment_bytes(self.record).decode()
        for word in ('recipient','receipt','sent','authorization','baseline_ref','history_ref',self.recipient):
            self.assertNotIn(word,text)
        self.assertEqual(self.record['decision'],'qualified')

    def test_same_record_schema_all_seven_retailers(self):
        for name in ('Metro','Shoppers Drug Mart','Rexall','Staples','Food Basics','Walmart','Costco'):
            b,p,now=fixture()
            b['plan']['retailer']=p['retailer']=b['audit']['baseline']['retailer']=name
            seal(b)
            self.assertEqual(assessment(b,p,now=now)['retailer'],name)

    def test_sent_recipient_skipped(self):
        self.lookup['already_sent']=True
        self.assertEqual(self.auth()['status'],'already_handled')

    def test_other_recipient_requires_own_search(self):
        self.lookup['recipient']=self.other
        with self.assertRaisesRegex(ReviewError,'sent_lookup_scope_mismatch'):self.auth()

    def test_recipient_added_after_qualification_no_backfill(self):
        self.context['eligible_since']=(self.now+timedelta(seconds=1)).isoformat()
        self.assertEqual(self.auth()['status'],'not_eligible_no_backfill')

    def test_uncertain_or_missing_history_is_not_authorized_by_empty_sent(self):
        for status in ('uncertain','unknown'):
            self.context['prior_attempt']=status
            with self.assertRaisesRegex(ReviewError,'uncertain_attempt'):self.auth()

    def test_actual_sent_evidence_resolves_duplicate_even_with_uncertain_history(self):
        self.context['prior_attempt']='uncertain';self.lookup['already_sent']=True
        self.assertEqual(self.auth()['status'],'already_handled')

    def test_definite_failure_can_retry_after_fresh_check(self):
        self.context['prior_attempt']='definitely_failed'
        self.assertEqual(self.auth()['status'],'authorized')

    def test_missing_original_history_blocks(self):
        self.context['history_ref']=''
        with self.assertRaisesRegex(ReviewError,'actual_campaign_history'):self.auth()

    def test_old_cross_source_search_required(self):
        for key in ('older_editions_checked','equivalent_offers_checked'):
            self.lookup[key]=False
            with self.assertRaisesRegex(ReviewError,'complete_sent_lookup'):self.auth()
            self.lookup[key]=True

    def test_parallel_worker_not_supported(self):
        self.context['serial_execution']=False
        with self.assertRaisesRegex(ReviewError,'overlapping_workers'):self.auth()

    def test_wrong_or_mutated_record_blocked(self):
        self.record['selection_sha256']='c'*64
        with self.assertRaisesRegex(ReviewError,'assessment_mismatch'):self.auth()

    def test_public_record_cannot_include_contact_fields(self):
        self.record['recipient']=self.recipient
        with self.assertRaisesRegex(ReviewError,'assessment_mismatch'):self.auth()

    def test_baseline_or_weak_record_is_not_delivery_qualification(self):
        for value in ('baseline','no_useful_value'):
            self.record['decision']=value
            with self.assertRaisesRegex(ReviewError,'assessment_mismatch'):self.auth()

    def test_record_must_be_read_from_same_actual_commit(self):
        self.proof['commit']='b'*40
        with self.assertRaisesRegex(ReviewError,'assessment_publication_scope'):self.auth()

    def test_record_read_and_sent_lookup_must_be_fresh(self):
        for obj in (self.proof,self.lookup):
            obj['checked_at']=(self.now-timedelta(minutes=11)).isoformat()
            with self.assertRaisesRegex(ReviewError,'stale'):self.auth()
            obj['checked_at']=self.now.isoformat()

    def test_record_exact_bytes_checked(self):
        self.proof['sha256']='f'*64
        with self.assertRaisesRegex(ReviewError,'assessment_read_hash'):self.auth()

    def test_old_quality_and_body_checks_still_run(self):
        self.body=self.body.replace('$4.00','$3.00',1)
        with self.assertRaisesRegex(ReviewError,'outgoing_body_differs'):self.auth()

    def test_missing_butcher_page_still_blocks(self):
        self.b['plan']['coverage']['expected_unit_ids'].append('butcher');seal(self.b)
        with self.assertRaisesRegex(ReviewError,'source_pages_missing'):self.auth()

    def test_no_database_is_not_a_github_gmail_startup_blocker(self):
        result=diagnose(observations(True),now=NOW,state_backend='github-gmail')
        self.assertEqual(result['blockers'],[])
        self.assertFalse(result['delivery_authorized'])
        self.assertNotIn('durability_unverified',json.dumps(result))

    def test_sqlite_adapter_still_checks_journal(self):
        result=diagnose(observations(True),now=NOW)
        self.assertIn('journal_not_configured',result['blockers'])

    def test_discovery_still_checks_gmail_in_repo_mode(self):
        result=diagnose(observations(False),now=NOW,state_backend='github-gmail')
        self.assertIn('action_not_exposed:gmail_send',result['blockers'])

    def test_optional_adapter_module_can_be_bootstrapped(self):
        spec=importlib.util.spec_from_file_location('repo_bootstrap',ROOT/'automation/runtime_bootstrap.py')
        boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cache=root/'cache';cache.mkdir()
            manifest={'repository_id':1,'commit':'a'*40,'git_blobs':{}}
            for rel in boot.MODULES|boot.OPTIONAL_MODULES:
                f=cache/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b'# synthetic\n')
                manifest['git_blobs'][rel]=boot.blob_id(f.read_bytes())
            result=boot.prepare(root/'runtime',manifest,cache)
            self.assertEqual(result['verified_modules'],10)

    def test_cli_build_does_not_send_and_will_not_overwrite_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'bundle.json';bundle.write_text(json.dumps(self.b))
            config=root/'profile.toml';config.write_text('retailer="Example retailer"\nmarket="Example City, Ontario"\ntimezone="UTC"\nsources=["https://example.org/flyer","https://example.net/flyer"]\nstate_file="private/state.json"\noutput_dir="public"\n')
            out=root/'event.json';args=['assessment',str(bundle),'--config',str(config),'--out',str(out)]
            with patch('sys.stdout',new_callable=io.StringIO),patch('sys.stderr',new_callable=io.StringIO):
                self.assertEqual(main(args),0)
                self.assertEqual(main(args),2)
            self.assertFalse((root/'private').exists())


if __name__=='__main__':unittest.main()
