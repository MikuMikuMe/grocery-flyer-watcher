"""Finite native-run tickets. Synthetic viability is NOT permission to publish/send."""
from datetime import datetime, timezone
import unittest

from grocery_flyer_watch import continuation as c
from grocery_flyer_watch import work_ticket as w


class WorkTicketTests(unittest.TestCase):
    def setUp(self):
        self.state = c.blank(["walmart", "metro", "costco"])
        for p in self.state["profiles"]:
            p["next_stage"] = "source_inventory"
            p["last_completed"] = "triage"
            p["observed_at"] = "2026-11-17T15:00:00Z"
        self.state["profiles"][0]["period"] = "2026-11-12/2026-11-18"
        self.state["profiles"][1]["period"] = "2026-11-12/2026-11-18"
        self.state["profiles"][2]["period"] = "2026-11-09/2026-11-22"
        self.now = datetime(2026, 11, 18, 3, tzinfo=timezone.utc)
        self.availability = {
            "walmart": self.record("2026-11-12", "2026-11-18"),
            "metro": self.record("2026-11-12", "2026-11-18"),
            "costco": self.record("2026-11-09", "2026-11-22"),
        }

    def record(self, start, end):
        return {"verified_market_edition": True, "source_readable": True,
                "edition_start": start, "edition_end": end, "undated_collection": False,
                "evidence_ref": "actual-tool-source-read"}

    def test_expiring_eligible_retailer_beats_later_offer(self):
        self.state["profiles"][1]["observed_at"] = "2026-11-17T16:00:00Z"
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["primary"], "walmart")
        self.assertEqual(result["action"], "resume_source_inventory")
        self.assertEqual(result["next_deliverable"], "source_verified_public_facts_chunk")
        self.assertEqual(result["max_deep_retailers"], 2)
        self.assertFalse(result["gmail_authorized"])

    def test_second_retailer_after_genuine_previous_no_progress(self):
        result = w.choose(self.state, self.availability, now=self.now,
                          previous_primary="walmart", previous_substantive=False)
        self.assertEqual(result["primary"], "metro")
        self.assertEqual(result["rotated_from"], "walmart")
        self.assertEqual(result["action"], "resume_source_inventory")

    def test_if_alternative_unverified_do_not_invent_rotation(self):
        self.availability["metro"]["verified_market_edition"] = False
        self.availability["costco"]["source_readable"] = False
        result = w.choose(self.state, self.availability, now=self.now,
                          previous_primary="walmart", previous_substantive=False)
        self.assertEqual(result["action"], "no_verified_viable_secondary")
        self.assertIsNone(result["primary"])

    def test_a_report_never_counts_as_finished_without_publication(self):
        self.state["sequence"] = 500
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(result["last_completed"], "triage")

    def test_pending_recipient_uncertainty_always_gets_reconciliation_first(self):
        p = self.state["profiles"][1]
        p["publication"] = {
            "commit": "a" * 40, "directory": "reports/reviewed/metro/hash",
            "assessment_path": "state/assessments/metro-event.json",
        }
        p["next_stage"] = "sent_verified"
        p["last_completed"] = "send_started"
        p["recipients"] = {"slot-a": "uncertain", "slot-b": "not_attempted"}
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["action"], "reconcile_sent_uncertainty")
        self.assertEqual(result["primary"], "metro")
        self.assertFalse(result["gmail_authorized"])

    def test_published_assessment_overrides_source_inventories(self):
        p = self.state["profiles"][2]
        p["publication"] = {
            "commit": "b" * 40, "directory": "reports/reviewed/costco/hash",
            "assessment_path": "state/assessments/costco-event.json",
        }
        p["next_stage"] = "authorization"
        p["last_completed"] = "preflight"
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["action"], "verify_pinned_assessment_and_authorize")
        self.assertEqual(result["primary"], "costco")

    def test_quality_work_beats_discovery(self):
        p = self.state["profiles"][2]
        p["last_completed"] = "omission_review"
        p["next_stage"] = "quality_check"
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["action"], "resume_quality_check")
        self.assertEqual(result["next_deliverable"], "actual_executable_quality_result")

    def test_old_evidence_needs_refresh_without_cursor_reset(self):
        p = self.state["profiles"][0]
        p["source_cursor"]["completed_units"] = ["page-1-original-first-read"]
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertTrue(result["refresh_selected_source_evidence"])
        self.assertEqual(result["cursor"], p["source_cursor"]["next_unit"])
        self.assertEqual(p["source_cursor"]["completed_units"], ["page-1-original-first-read"])

    def test_unverified_and_expired_sources_not_actionable(self):
        self.availability["walmart"]["edition_end"] = "2026-11-15"
        self.availability["metro"]["verified_market_edition"] = False
        self.availability["costco"]["source_readable"] = False
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["action"], "no_verified_viable_source")
        self.assertIsNone(result["primary"])


    def test_unknown_dated_retailer_does_not_block_verified_retailer(self):
        # Full-registry triage may have unreadable/undiscovered current editions.
        self.state["profiles"].append(c.blank(["rexall"])["profiles"][0])
        self.availability["rexall"] = {
            "verified_market_edition": False, "source_readable": False,
            "edition_start": None, "edition_end": None,
            "undated_collection": False, "evidence_ref": None,
        }
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["primary"], "walmart")
        self.assertEqual(result["next_deliverable"], "source_verified_public_facts_chunk")

    def test_all_unknown_sources_are_not_eligible(self):
        for ident in self.availability:
            self.availability[ident] = {
                "verified_market_edition": False, "source_readable": False,
                "edition_start": None, "edition_end": None,
                "undated_collection": False, "evidence_ref": None,
            }
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["action"], "no_verified_viable_source")
        self.assertIsNone(result["primary"])

    def test_unknown_dates_cannot_claim_verified_market_edition(self):
        self.availability["metro"] = {
            "verified_market_edition": True, "source_readable": True,
            "edition_start": None, "edition_end": None,
            "undated_collection": False, "evidence_ref": "actual-read",
        }
        with self.assertRaises(w.TicketError):
            w.choose(self.state, self.availability, now=self.now)

    def test_readable_source_without_verified_edition_remains_candidate_only(self):
        self.availability["metro"] = {
            "verified_market_edition": False, "source_readable": True,
            "edition_start": None, "edition_end": None,
            "undated_collection": False, "evidence_ref": "actual-page-read",
        }
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["primary"], "walmart")

    def test_only_staples_undated_collections_are_eligible(self):
        self.availability["walmart"] = {
            "verified_market_edition": True, "source_readable": True,
            "edition_start": None, "edition_end": None,
            "undated_collection": True, "evidence_ref": "source-read",
        }
        with self.assertRaises(w.TicketError):
            w.choose(self.state, self.availability, now=self.now)

    def test_preview_edition_may_be_researched_but_not_authorized(self):
        self.availability["walmart"] = self.record("2026-11-19", "2026-11-25")
        self.availability["metro"]["source_readable"] = False
        self.availability["costco"]["source_readable"] = False
        result = w.choose(self.state, self.availability, now=self.now)
        self.assertEqual(result["primary"], "walmart")
        self.assertEqual(result["action"], "resume_source_inventory")
        self.assertFalse(result["gmail_authorized"])

    def test_input_validation_fails_closed(self):
        del self.availability["costco"]
        with self.assertRaises(w.TicketError):
            w.choose(self.state, self.availability, now=self.now)

    def test_input_availability_cannot_claim_proof_without_ref(self):
        self.availability["walmart"]["evidence_ref"] = None
        with self.assertRaises(w.TicketError):
            w.choose(self.state, self.availability, now=self.now)


if __name__ == "__main__":
    unittest.main()
