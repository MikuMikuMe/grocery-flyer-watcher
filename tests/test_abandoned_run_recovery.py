import unittest
from grocery_flyer_watch.runtime_controller import SCHEMA, transition, parse, render


class AbandonedRunTests(unittest.TestCase):
    def setUp(self):
        self.s = dict(schema=SCHEMA, revision=1, status='RUN_STARTED', run_key='old', native_run_id='old', scheduled_for='2020-01-01T10:00:00Z', checkpoint_sequence=4, operation=None, result=None)
        self.event = dict(action='recover_abandoned', expected_revision=1, checkpoint_sequence=4, verified_checkpoint=True, verified_no_unresolved_delivery=True, verified_no_other_writer=True, latest_run=dict(id='later', recorded_status='completed', scheduled_for='2020-01-01T11:00:00Z', completed_at='2020-01-01T11:01:00Z'))

    def test_superseded_empty_run(self):
        n = transition(self.s, self.event)
        self.assertEqual((n['status'], n['revision'], n['checkpoint_sequence']), ('RUN_FINISHED', 2, 4))
        self.assertEqual(n['recovery']['basis'], 'superseded')
        self.assertEqual(n['recovery']['historical_outcome'], 'unknown')
        self.assertEqual(parse(render(n)), n)

    def test_matching_terminal(self):
        self.event['latest_run'].update(id='old', scheduled_for=self.s['scheduled_for'])
        self.assertEqual(transition(self.s, self.event)['recovery']['basis'], 'terminal')

    def test_reject_missing_or_unsafe_evidence(self):
        for change in ({'verified_checkpoint':False}, {'verified_no_unresolved_delivery':False}, {'verified_no_other_writer':False}, {'checkpoint_sequence':5}, {'expected_revision':0}, {'latest_run':None}, {'latest_run':dict(self.event['latest_run'],recorded_status='in_progress')}, {'latest_run':dict(self.event['latest_run'],scheduled_for=self.s['scheduled_for'])}, {'latest_run':dict(self.event['latest_run'],completed_at=None)}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                transition(self.s, dict(self.event, **change))

    def test_reject_pending_and_saved_results(self):
        s = transition(self.s, dict(action='pending', expected_revision=1, checkpoint_sequence=4, identity=dict(retailer='example', edition='2020-01-01', stage='inventory', unit='page', source='example.invalid', kind='read_only')))
        for state in [s, transition(s, dict(action='result', expected_revision=2, checkpoint_sequence=4, result=dict(disposition='advance', evidence='synthetic', units=['page'])) )]:
            with self.assertRaises(ValueError):
                transition(state, dict(self.event, expected_revision=state['revision']))

    def test_consecutive_recovery_and_start(self):
        ev = dict(self.event, action='recover_start', run_key='new', native_run_id='new', scheduled_for='2020-01-01T12:00:00Z')
        n = transition(self.s, ev)
        self.assertEqual((n['status'], n['run_key'], n['revision']), ('RUN_STARTED', 'new', 2))
        self.assertEqual(n['checkpoint_sequence'], 4)
        self.assertEqual(n['recovery']['run_key'], 'old')
        next_ev = dict(ev, expected_revision=2, run_key='next', native_run_id='next', scheduled_for='2020-01-01T14:00:00Z', latest_run=dict(self.event['latest_run'],id='later2', scheduled_for='2020-01-01T13:00:00Z', completed_at='2020-01-01T13:01:00Z'))
        m = transition(n, next_ev)
        self.assertEqual((m['run_key'],m['revision'],m['checkpoint_sequence']), ('next',3,4))
        self.assertEqual(m['recovery']['run_key'],'new')

    def test_local_run_key_without_native_id(self):
        self.s.update(native_run_id=None, scheduled_for=None, observed_started_at='2020-01-01T10:00:00Z')
        self.event['latest_run']['started_at'] = '2020-01-01T11:00:00Z'
        n = transition(self.s, self.event)
        self.assertEqual(n['recovery']['basis'], 'superseded')
        self.event['latest_run']['started_at'] = '2020-01-01T09:00:00Z'
        with self.assertRaises(ValueError): transition(self.s, self.event)

    def test_early_matching_terminal(self):
        self.event['latest_run'].update(id='old', scheduled_for=self.s['scheduled_for'], completed_at='2020-01-01T09:59:00Z')
        self.assertEqual(transition(self.s, self.event)['recovery']['basis'], 'terminal')

    def test_new_local_run_must_have_timestamp(self):
        ev = dict(self.event, action='recover_start', run_key='local', native_run_id=None, scheduled_for=None)
        with self.assertRaises(ValueError): transition(self.s, ev)
        ev['observed_started_at'] = '2020-01-01T12:00:00Z'
        self.assertEqual(transition(self.s, ev)['observed_started_at'], ev['observed_started_at'])

    def test_fresh_start_bundle(self):
        from grocery_flyer_watch.runtime_controller import recovery_bundle
        closed = transition(self.s, self.event)
        ev = dict(self.event, action='start', expected_revision=2, run_key='fresh', native_run_id='fresh', scheduled_for='2020-01-01T12:00:00Z')
        j, h, handoff = recovery_bundle(closed, ev, b'old history')
        self.assertEqual(parse(j)['status'], 'RUN_STARTED')
        self.assertEqual(parse(j)['revision'], 3)
        self.assertIn(b'fresh', h)
        self.assertIn(b'fresh', handoff)
        self.assertEqual(recovery_bundle(closed, ev, h), (j,h,handoff))

    def test_bundle_idempotent_history_and_handoff(self):
        from grocery_flyer_watch.runtime_controller import recovery_bundle
        ev = dict(self.event, action='recover_start', run_key='new', native_run_id='new', scheduled_for='2020-01-01T12:00:00Z')
        journal, history, handoff = recovery_bundle(self.s, ev, b'original\r\n')
        self.assertTrue(history.startswith(b'original\r\n'))
        self.assertIn(b'old', history)
        self.assertIn(b'new', handoff)
        self.assertEqual(recovery_bundle(self.s, ev, history), (journal,history,handoff))
        self.assertEqual(parse(journal)['revision'], 2)

if __name__ == '__main__':
    unittest.main()
