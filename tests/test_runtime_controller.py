import unittest
from grocery_flyer_watch.runtime_controller import SCHEMA, append_entry, inspect, parse, render, transition


class RuntimeControllerTests(unittest.TestCase):
    def setUp(self):
        self.state = {'schema': SCHEMA, 'revision': 0, 'status': 'IDLE', 'run_key': None, 'checkpoint_sequence': 4, 'operation': None, 'result': None}

    def step(self, action, seq=4, **kw):
        self.state = transition(self.state, dict(action=action, checkpoint_sequence=seq, expected_revision=self.state['revision'], **kw))
        self.assertEqual(parse(render(self.state)), self.state)
        return self.state

    def pending(self, kind='read_only'):
        self.step('start', run_key='synthetic-run')
        self.step('pending', identity=dict(retailer='example', edition='2020-01-01/2020-01-07', stage='inventory', unit='page 6', source='https://example.invalid/flyer', kind=kind))

    def test_interrupt_after_intent(self):
        self.pending()
        self.assertEqual(inspect(self.state, 4)['action'], 'verify_then_retry_read_only')
        with self.assertRaises(ValueError): self.step('start', run_key='another')
        with self.assertRaises(ValueError): self.step('commit', seq=5, verified_checkpoint=True, verified_secondary_records=True)

    def test_result_before_and_after_checkpoint(self):
        self.pending()
        self.step('result', result={'disposition':'advance','evidence':'synthetic evidence','units':['page 6']})
        self.assertEqual(inspect(self.state, 4)['action'], 'verify_result_and_missing_delta')
        self.assertEqual(inspect(self.state, 5)['action'], 'verify_advanced_checkpoint_repair_secondary')
        with self.assertRaises(ValueError): self.step('commit', seq=5, verified_checkpoint=True)
        with self.assertRaises(ValueError): self.step('commit', verified_checkpoint=True, verified_secondary_records=True)
        self.step('commit', seq=5, verified_checkpoint=True, verified_secondary_records=True)
        self.assertEqual(inspect(self.state, 5)['action'], 'verify_secondary_records_then_continue')
        self.step('finish', seq=5, verified_secondary_records=True)
        self.assertEqual(inspect(self.state, 5)['action'], 'start_run')

    def test_external_effects(self):
        self.pending('immutable_write')
        self.assertEqual(inspect(self.state, 4)['action'], 'reconcile_immutable_artifact')
        with self.assertRaises(ValueError): self.step('result', result={'disposition':'advance','evidence':'test','artifact':'file'})
        self.step('begin')
        self.step('result', result={'disposition':'uncertain','evidence':'unknown outcome'})
        self.assertEqual(inspect(self.state, 4)['action'], 'reconcile_uncertainty')
        with self.assertRaises(ValueError): self.step('commit', verified_checkpoint=True, verified_secondary_records=True)
        self.step('reconcile', result={'disposition':'no_progress','evidence':'definite failure'})
        self.step('commit', verified_checkpoint=True, verified_secondary_records=True)

    def test_delivery_never_authorized(self):
        self.pending('delivery_reconcile')
        self.assertEqual(inspect(self.state, 4)['action'], 'reconcile_native_uncertainty_and_sent')
        self.assertFalse(inspect(self.state, 4)['delivery_authorized'])

    def test_stale_revision_and_regression(self):
        with self.assertRaises(ValueError): transition(self.state, {'expected_revision':9,'action':'start','checkpoint_sequence':4,'run_key':'x'})
        self.pending()
        self.assertEqual(inspect(self.state, 3)['action'], 'checkpoint_conflict')
        self.assertEqual(inspect(self.state, 5)['action'], 'checkpoint_conflict')

    def test_append_preserves_bytes_and_deduplicates(self):
        raw = b'original\r\n'
        new = append_entry(raw, 'run-1:START', 'started')
        self.assertTrue(new.startswith(raw))
        self.assertEqual(append_entry(new, 'run-1:START', 'started'), new)
        with self.assertRaises(ValueError): append_entry(new, 'run-1:START', 'different')
        self.assertTrue(append_entry(new, 'run-1:END', 'done').startswith(new))

    def test_stale_handoff(self):
        self.assertTrue(inspect(self.state, 4, 'new-run', 'old-run')['handoff_stale'])

    def test_no_progress_does_not_advance(self):
        self.pending()
        self.step('result', result={'disposition':'no_progress','evidence':'blocked'})
        with self.assertRaises(ValueError): self.step('commit', seq=5, verified_checkpoint=True, verified_secondary_records=True)
        self.step('commit', verified_checkpoint=True, verified_secondary_records=True)


if __name__ == '__main__':
    unittest.main()
