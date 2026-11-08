"""Offline recovery regression tests: no real provider mutation or personal records."""
from __future__ import annotations
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('runtime_bootstrap',ROOT/'automation/runtime_bootstrap.py')
bootstrap=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
from grocery_flyer_watch.runtime_preflight import (
    PreflightError, TABLES, capabilities, diagnose, journal_health)
NOW=datetime.now(timezone.utc)


def observations(send=False):
    entries=[
        {'provider':'Gmail','complete':True,'evidence_ref':'synthetic-schema-read',
         'actions':['Gmail.get_profile','Gmail.search_emails','Gmail.read_email']},
        {'provider':'GitHub','complete':True,'evidence_ref':'synthetic-schema-read',
         'actions':['GitHub.fetch_file','GitHub.get_repo']},
        {'provider':'GitHub_Auto_Project_Connector','complete':True,'evidence_ref':'synthetic-schema-read',
         'actions':['GitHub_Auto_Project_Connector.read_repository_file']},
        {'provider':'Automations','complete':True,'evidence_ref':'synthetic-schema-read',
         'actions':['Automations.peek']},
    ]
    if send:
        entries[0]['actions'].append('Gmail.send_email')
        entries[2]['actions'].append('GitHub_Auto_Project_Connector.commit_repository_files')
    return {'format':'callable-actions-v1','observed_at':NOW.isoformat(),'discovery':entries}


def make_db(path,seed=True):
    db=sqlite3.connect(path)
    for table,columns in TABLES.items():
        db.execute('CREATE TABLE '+table+' ('+','.join(x+' TEXT' for x in columns)+')')
    if seed:
        db.execute("INSERT INTO scopes (id) VALUES ('synthetic-scope')")
    db.commit();db.close()

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.cache=self.root/'cache'
        blobs={}
        for rel in bootstrap.MODULES:
            p=self.cache/rel;p.parent.mkdir(parents=True,exist_ok=True)
            raw=b'# Synthetic fixture, not production code\n';p.write_bytes(raw)
            blobs[rel]=bootstrap.blob_id(raw)
        self.manifest={'repository_id':1,'commit':'a'*40,'git_blobs':blobs}

    def test_missing_runtime_repairs_from_verified_cache(self):
        dest=self.root/'runtime'
        self.assertEqual(bootstrap.prepare(dest,self.manifest,self.cache)['restored_modules'],len(bootstrap.MODULES))
        self.assertTrue(all((dest/x).is_file() for x in bootstrap.MODULES))

    def test_repeat_recovery_is_idempotent(self):
        dest=self.root/'runtime';bootstrap.prepare(dest,self.manifest,self.cache)
        self.assertEqual(bootstrap.prepare(dest,self.manifest,self.cache)['restored_modules'],0)

    def test_recovery_never_authorizes_mail(self):
        self.assertIs(bootstrap.prepare(self.root/'runtime',self.manifest,self.cache)['delivery_authorized'],False)

    def test_missing_cache_does_not_create_fake_runtime(self):
        dest=self.root/'runtime'
        with self.assertRaisesRegex(bootstrap.RecoveryError,'runtime_module_missing'):
            bootstrap.prepare(dest,self.manifest)
        self.assertFalse(dest.exists())

    def test_cache_tampering_blocks_all_writes(self):
        (self.cache/next(iter(bootstrap.MODULES))).write_text('changed')
        dest=self.root/'runtime'
        with self.assertRaisesRegex(bootstrap.RecoveryError,'cache_integrity_mismatch'):
            bootstrap.prepare(dest,self.manifest,self.cache)
        self.assertFalse(dest.exists())

    def test_existing_edit_is_not_overwritten(self):
        dest=self.root/'runtime';bootstrap.prepare(dest,self.manifest,self.cache)
        p=dest/next(iter(bootstrap.MODULES));p.write_text('local edit')
        with self.assertRaisesRegex(bootstrap.RecoveryError,'runtime_integrity_mismatch'):
            bootstrap.prepare(dest,self.manifest,self.cache)
        self.assertEqual(p.read_text(),'local edit')

    def test_incomplete_manifest_rejected(self):
        self.manifest['git_blobs'].pop(next(iter(bootstrap.MODULES)))
        with self.assertRaisesRegex(bootstrap.RecoveryError,'incomplete_runtime_manifest'):
            bootstrap.prepare(self.root/'runtime',self.manifest,self.cache)

    def test_branch_name_is_not_pinned_commit(self):
        self.manifest['commit']='main'
        with self.assertRaisesRegex(bootstrap.RecoveryError,'pinned_commit_required'):
            bootstrap.prepare(self.root/'runtime',self.manifest,self.cache)

    def test_symlink_runtime_rejected(self):
        dest=self.root/'runtime';dest.symlink_to(self.cache,target_is_directory=True)
        with self.assertRaisesRegex(bootstrap.RecoveryError,'runtime_symlink'):
            bootstrap.prepare(dest,self.manifest,self.cache)

    def test_read_actions_do_not_imply_writes(self):
        r=capabilities(observations(),now=NOW)
        self.assertEqual(r['gmail_send']['status'],'not_exposed')
        self.assertEqual(r['github_publish']['status'],'not_exposed')
        self.assertEqual(r['task_update']['status'],'not_exposed')

    def test_exposed_action_is_not_successful_execution(self):
        r=diagnose(observations(True),now=NOW)
        self.assertEqual(r['operations']['gmail_send']['status'],'exposed_not_execution_tested')
        self.assertEqual(r['provider_mutation_result'],'not_attempted')
        self.assertFalse(r['delivery_authorized'])

    def test_incomplete_discovery_is_unknown_not_denied(self):
        d=observations();d['discovery'][0]['complete']=False
        r=diagnose(d,now=NOW)
        self.assertEqual(r['operations']['gmail_send']['status'],'unknown')
        self.assertIn('action_discovery_incomplete:gmail_send',r['blockers'])
        self.assertNotIn('action_not_exposed:gmail_send',r['blockers'])

    def test_old_action_discovery_requires_refresh(self):
        d=observations();d['observed_at']=(NOW-timedelta(minutes=16)).isoformat()
        with self.assertRaisesRegex(PreflightError,'rediscover'):
            capabilities(d,now=NOW)

    def test_future_action_discovery_rejected(self):
        d=observations();d['observed_at']=(NOW+timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(PreflightError,'rediscover'):
            capabilities(d,now=NOW)

    def test_permission_setting_cannot_substitute_for_actions(self):
        d=observations();d['discovery'][0]['app_permission']='Allow all actions'
        with self.assertRaisesRegex(PreflightError,'discovery_schema'):
            capabilities(d,now=NOW)

    def test_plugin_description_not_accepted_as_action(self):
        d=observations();d['discovery'][0]['actions']=['Reads and sends email']
        with self.assertRaisesRegex(PreflightError,'action_schema'):
            capabilities(d,now=NOW)

    def test_draft_only_is_not_a_send_route(self):
        d=observations();d['discovery'][0]['actions'].append('Gmail.create_draft')
        self.assertEqual(capabilities(d,now=NOW)['gmail_send']['status'],'not_exposed')
        d['discovery'][0]['actions'].append('Gmail.send_draft')
        self.assertEqual(capabilities(d,now=NOW)['gmail_send']['status'],'exposed_not_execution_tested')

    def test_native_writer_recognized_when_exposed(self):
        d=observations();d['discovery'][1]['actions'].append('GitHub.create_file')
        self.assertEqual(capabilities(d,now=NOW)['github_publish']['status'],'exposed_not_execution_tested')

    def test_no_automatic_reauthentication_claim(self):
        r=diagnose(observations(),now=NOW)
        self.assertEqual(r['provider_authentication'],'not_inferred')
        self.assertNotIn('oauth',json.dumps(r).lower())
        self.assertTrue(r['continue_independent_source_checks'])

    def test_no_journal_path_is_separate_failure(self):
        self.assertEqual(journal_health(None)['status'],'journal_not_configured')

    def test_missing_journal_is_not_created(self):
        p=self.root/'private'/'journal.sqlite'
        self.assertEqual(journal_health(p)['status'],'journal_not_restored')
        self.assertFalse(p.parent.exists())

    def test_existing_journal_does_not_prove_durability(self):
        p=self.root/'journal.sqlite';make_db(p)
        before=p.read_bytes()
        self.assertEqual(journal_health(p)['status'],'durability_unverified')
        self.assertEqual(p.read_bytes(),before)

    def test_uninitialized_journal_cannot_backfill(self):
        p=self.root/'journal.sqlite';make_db(p,False)
        self.assertEqual(journal_health(p)['status'],'history_not_initialized')

    def test_corrupt_journal_not_reset(self):
        p=self.root/'journal.sqlite';p.write_bytes(b'corrupt synthetic bytes')
        self.assertEqual(journal_health(p)['status'],'journal_unreadable_or_incompatible')
        self.assertEqual(p.read_bytes(),b'corrupt synthetic bytes')

    def test_journal_inside_checkout_rejected(self):
        (self.root/'.git').mkdir()
        p=self.root/'journal.sqlite';make_db(p)
        self.assertEqual(journal_health(p)['status'],'unsafe_journal_location')

    def test_journal_symlink_rejected(self):
        p=self.root/'real.sqlite';make_db(p)
        q=self.root/'link.sqlite';q.symlink_to(p)
        self.assertEqual(journal_health(q)['status'],'unsafe_journal_location')

    def test_durability_requires_both_restore_and_checkpoint(self):
        p=self.root/'journal.sqlite';make_db(p)
        for proof in ({'kind':'durable_mount','restore_ref':'synthetic','checkpoint_ref':''},None):
            self.assertEqual(journal_health(p,persistence=proof)['status'],'durability_unverified')

    def test_all_prerequisites_still_not_email_authorization(self):
        p=self.root/'journal.sqlite';make_db(p)
        r=diagnose(observations(True),p,{'kind':'durable_mount','restore_ref':'synthetic restore',
                                      'checkpoint_ref':'synthetic checkpoint'},now=NOW)
        self.assertEqual(r['status'],'operational_prerequisites_present')
        self.assertFalse(r['delivery_authorized'])
        self.assertEqual(r['operations']['task_update']['status'],'not_exposed')

if __name__=='__main__':
    unittest.main()
