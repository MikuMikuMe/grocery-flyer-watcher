"""Checkpoint resume safety; all examples are synthetic and never send email."""
import copy
from datetime import datetime, timedelta, timezone
import json
import unittest

from grocery_flyer_watch import continuation as c


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.data = c.blank(["metro", "rexall", "staples"])

    def test_seed_is_not_a_retailer_baseline_or_send_authority(self):
        p = c.plan(self.data)
        self.assertEqual(p["status"], "checkpoint_only_not_delivery_authorization")
        self.assertTrue(all(x["action"] == "triage_matching_registry_baseline"
                            for x in p["next"]))
        self.assertTrue(all(x["last_completed"] == "not_started"
                            for x in self.data["profiles"]))

    def test_private_prompt_roundtrip_replaces_without_duplication(self):
        original = "Do source validation; do not resend handled editions."
        prompt = c.embed(original, self.data)
        self.assertEqual(c.extract(prompt), self.data)
        self.assertEqual(c.embed(prompt, self.data).count(c.BEGIN), 1)
        self.assertEqual(c.embed(prompt, self.data).count(c.END), 1)

    def test_publication_before_send_write_ahead_blocks_automatic_retry(self):
        p = self.data["profiles"][1]
        p["publication"] = {"commit": "a" * 40, "directory": "reports/reviewed/rexall/hash",
                            "assessment_path": "state/assessments/id.json"}
        p["last_completed"] = "preflight"
        p["next_stage"] = "authorization"
        p["recipients"] = {"slot-a": "not_attempted", "slot-b": "not_attempted"}
        self.data = c.validate(self.data)
        c.before_send(self.data, "rexall", "slot-a", "actual-auth-result")
        self.assertEqual(p["recipients"]["slot-a"], "uncertain")
        self.assertEqual(p["recipients"]["slot-b"], "not_attempted")
        self.assertEqual(c.plan(self.data)["next"][0]["action"],
                         "reconcile_actual_gmail_sent_before_retry")
        with self.assertRaises(c.CheckpointError):
            c.before_send(self.data, "rexall", "slot-a", "auth-again")

    def test_source_cursor_kept_but_stale_proofs_require_refresh(self):
        p = self.data["profiles"][1]
        p["last_completed"] = "source_inventory"
        p["next_stage"] = "candidate_review"
        p["status"] = "incomplete"
        p["observed_at"] = "2026-11-07T16:00:00Z"
        p["source_cursor"] = {"source": "weekly-flyer",
                              "completed_units": ["page-1", "page-2"], "next_unit": "page-3"}
        r = c.plan(self.data, now=datetime(2026, 11, 8, 1, tzinfo=timezone.utc))
        rexall = next(x for x in r["next"] if x["profile"] == "rexall")
        self.assertEqual(rexall["action"],
                         "refresh_expired_source_evidence_then_resume_cursor")
        self.assertEqual(rexall["cursor"], "page-3")

    def test_missing_publication_cannot_claim_send_stage(self):
        p = self.data["profiles"][1]
        p["last_completed"] = "preflight"
        p["next_stage"] = "authorization"
        with self.assertRaises(c.CheckpointError):
            c.validate(self.data)

    def test_private_checkpoint_rejects_raw_contact_or_new_fields(self):
        p = self.data["profiles"][1]
        p["reason"] = "email someone@example.com"
        with self.assertRaises(c.CheckpointError):
            c.validate(self.data)
        p["reason"] = ""
        p["recipient_email"] = "someone@example.com"
        with self.assertRaises(c.CheckpointError):
            c.validate(self.data)

    def test_fake_send_accepted_is_never_inferred(self):
        p = self.data["profiles"][1]
        p["recipients"] = {"slot-a": "uncertain", "slot-b": "not_attempted"}
        r = c.plan(self.data)
        self.assertEqual(r["next"][0]["action"], "reconcile_actual_gmail_sent_before_retry")
        self.assertIn("slot-b", p["recipients"])


    def test_verified_sent_transition_stays_recipient_specific(self):
        p = self.data["profiles"][1]
        p["publication"] = {"commit": "b" * 40, "directory": "reports/reviewed/r/hash",
                            "assessment_path": "state/assessments/x.json"}
        p["last_completed"] = "preflight"
        p["next_stage"] = "authorization"
        p["recipients"] = {"slot-a": "not_attempted", "slot-b": "not_attempted"}
        c.before_send(self.data, "rexall", "slot-a", "auth-step-result")
        c.after_sent_verification(self.data, "rexall", "slot-a", "actual-Gmail-Sent-match")
        self.assertEqual(p["recipients"]["slot-a"], "accepted_verified_in_sent")
        self.assertEqual(p["recipients"]["slot-b"], "not_attempted")
        self.assertEqual(p["status"], "incomplete")
        c.before_send(self.data, "rexall", "slot-b", "auth-step-result-2")
        c.after_preacceptance_failure(self.data, "rexall", "slot-b",
                                      "actual-provider-preacceptance-denial")
        self.assertEqual(p["recipients"]["slot-b"], "definitely_failed_before_acceptance")
        self.assertEqual(p["status"], "incomplete")

    def test_private_save_rejects_public_checkout(self):
        from pathlib import Path
        with self.assertRaises(c.CheckpointError):
            c.private_save(Path("tests/fake-private-checkpoint.json"), "{}")

    def test_second_reviewer_not_inferred_by_checkpoint(self):
        c.update(self.data, "rexall", last_completed="source_inventory",
                 next_stage="candidate_review", evidence_ref="actual-archive-index",
                 reason="source research only")
        self.assertEqual(self.data["profiles"][1]["next_stage"], "candidate_review")
        self.assertNotIn("authorized", json.dumps(self.data))


if __name__ == "__main__":
    unittest.main()

