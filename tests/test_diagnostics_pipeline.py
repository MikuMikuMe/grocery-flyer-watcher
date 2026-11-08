"""Offline diagnostic assertions at actual pipeline boundaries, never real mail."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grocery_flyer_watch.runner import collect, check_scope, load_config, run
from grocery_flyer_watch.quality_gate import check, artifacts, write_artifacts, verify_artifacts
from grocery_flyer_watch.review import ReviewError
from grocery_flyer_watch.reviewed_delivery import run_profiles, _smtp_transport, KnownDeliveryFailure, AmbiguousDelivery
from grocery_flyer_watch.quality_cli import main
from quality_fixture import fixture, seal
from test_portability import snapshot


class PipelineDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.sink = io.StringIO()
        self.env = patch.dict(os.environ, {'FLYER_DIAGNOSTICS': '1'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.output = patch('sys.stderr', self.sink)
        self.output.start(); self.addCleanup(self.output.stop)

    def events(self):
        return [json.loads(s) for s in self.sink.getvalue().splitlines()
                if json.loads(s).get('schema') == 'flyer-diagnostic-v1']

    def failed(self, stage, code):
        self.assertTrue(any(e['stage'] == stage and e.get('code') == code
                            and e['outcome'] in {'failed', 'blocked'} for e in self.events()), self.sink.getvalue())

    def test_missing_collector_has_specific_cause(self):
        with self.assertRaises(ValueError):
            collect({})
        self.failed('collector.read', 'collector_not_configured')

    def test_collector_timeout_does_not_print_argv_or_output(self):
        with patch('grocery_flyer_watch.runner.subprocess.run', side_effect=subprocess.TimeoutExpired(['PRIVATE_TOKEN'], 1, output='PRIVATE_BODY')):
            with self.assertRaises(subprocess.TimeoutExpired):
                collect(dict(collector=['PRIVATE_TOKEN'], market='x', retailer='x', timezone='UTC', sources=[]))
        self.failed('collector.read', 'subprocess_timeout')
        self.assertNotIn('PRIVATE_', self.sink.getvalue())

    def test_malformed_collector_json_does_not_echo_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'private.json';p.write_text('PRIVATE_EMAIL@example.invalid')
            with self.assertRaises(json.JSONDecodeError):
                collect({}, p)
        self.failed('collector.read', 'invalid_json')
        self.assertNotIn('PRIVATE_EMAIL', self.sink.getvalue())

    def test_scope_rejection_not_source_outage(self):
        with self.assertRaises(ValueError):
            check_scope(dict(retailer='Another retailer',market='Another city'), snapshot())
        self.failed('snapshot.scope', 'snapshot_scope_mismatch')

    def test_real_quality_gate_retains_rule_code(self):
        bundle, profile, now = fixture()
        bundle['audit']['fact_proofs']['p1']['local_scope_verified'] = False
        seal(bundle)
        with self.assertRaises(ReviewError):
            check(bundle, profile, now=now)
        self.failed('quality.check', 'local_purchase_claim_not_verified')

    def test_artifact_build_verify_and_drift_are_separate(self):
        bundle, profile, now = fixture()
        approved = check(bundle, profile, now=now)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'generated'
            write_artifacts(approved, out)
            verify_artifacts(approved, out)
            (out/'report.md').write_text('PRIVATE_DRIFT')
            with self.assertRaises(ReviewError):verify_artifacts(approved, out)
        self.failed('artifacts.verify', 'public_artifact_differs_from_reviewed_selection')
        self.assertNotIn('PRIVATE_DRIFT', self.sink.getvalue())
        self.assertIn('artifacts.write', {e['stage'] for e in self.events()})

    def test_profile_failure_is_visible_and_next_profile_runs(self):
        worker = Mock(side_effect=[RuntimeError('PRIVATE_SOURCE_BODY'), 'unchanged'])
        self.assertEqual(run_profiles([{'id':'first'},{'id':'second'}], worker),
                         {'first':'insufficient_evidence','second':'unchanged'})
        self.failed('profile', 'unexpected_error')
        self.assertEqual(worker.call_count, 2)
        self.assertNotIn('PRIVATE_SOURCE_BODY', self.sink.getvalue())

    def test_cli_failure_is_correlated_and_preserves_exit_code(self):
        with patch('sys.stdout',new_callable=io.StringIO), patch('grocery_flyer_watch.quality_cli.read_json', side_effect=FileNotFoundError('/PRIVATE_PATH')):
            self.assertEqual(main(['binding','/PRIVATE_PATH']),2)
        self.failed('quality.cli', 'input_or_executable_missing')
        self.assertEqual(len({e['run_id'] for e in self.events()}),1)
        self.assertNotIn('PRIVATE_PATH',self.sink.getvalue())

    def test_smtp_before_acceptance_differs_from_ambiguous_send(self):
        env={'FLYER_SMTP_HOST':'example.invalid','FLYER_MAIL_FROM':'sender@example.invalid'}
        with patch('grocery_flyer_watch.reviewed_delivery.smtplib.SMTP_SSL',side_effect=OSError('PRIVATE_AUTH')):
            with self.assertRaises(KnownDeliveryFailure):
                _smtp_transport('target@example.invalid','subject','body','event',env)
        self.failed('delivery.transport','smtp_not_started')
        with patch('grocery_flyer_watch.reviewed_delivery.smtplib.SMTP_SSL') as client:
            client.return_value.send_message.side_effect=OSError('PRIVATE_REPLY')
            with self.assertRaises(AmbiguousDelivery):
                _smtp_transport('target@example.invalid','subject','body','event',env)
        self.failed('delivery.transport','smtp_acceptance_unknown')
        for value in ['PRIVATE_AUTH','PRIVATE_REPLY','target@example.invalid','sender@example.invalid']:
            self.assertNotIn(value,self.sink.getvalue())

if __name__ == '__main__':unittest.main()
