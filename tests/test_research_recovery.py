"""Offline failover/coverage/rotation regressions; no live offers or mail."""
import copy
import json
from pathlib import Path
import unittest

from grocery_flyer_watch import continuation as c


ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "config/kingston_flyer_sources.json").read_text())


class ResearchRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state = c.blank(["metro", "walmart", "loblaws", "rexall"])
        self.walmart = self.state["profiles"][1]
        self.walmart["source_cursor"]["source"] = (
            "https://www.weeklyflyer.com/walmart/walmart-ontario-flyer-2026-11-12")
        self.walmart["source_cursor"]["completed_units"] = [
            "weekly-original-image-first-read-page-1",
            "weekly-original-image-first-read-page-2",
            "2026-11-17 inventory grid page1 actual first-read",
        ]
        c.validate(self.state)

    def test_broken_grid_reuses_actual_original_scans_without_approving_inventory(self):
        got = c.source_failover(
            self.state, CATALOG, "walmart",
            failed_url="https://www.example.ca/walmart/grid?page=3",
            attempts=1,
            reviewed_original_url=self.walmart["source_cursor"]["source"],
            missing_units=["grid-page-3", "grid-page-4", "grid-page-5"])
        self.assertEqual(got["action"], "extract_missing_inventory_from_original_scans")
        self.assertEqual(got["unresolved_units"], ["grid-page-3", "grid-page-4", "grid-page-5"])
        self.assertFalse(got["coverage_complete"])
        self.assertFalse(got["quality_authorized"])
        self.assertEqual(self.walmart["last_completed"], "not_started")

    def test_catalog_host_and_path_boundaries_prevent_arbitrary_source_reuse(self):
        got = c.source_failover(
            self.state, CATALOG, "walmart",
            failed_url="https://bad.example.org/walmart/grid?page=3", attempts=2,
            reviewed_original_url="https://www.weeklyflyer.com/walmart-fake")
        self.assertEqual(got["action"], "switch_to_next_fixed_source")
        self.assertEqual(got["source_url"], "https://www.walmart.ca/en/store/3043-kingston-on")
        self.assertFalse(got["coverage_complete"])

    def test_failed_registered_sources_are_skipped_and_then_rotate(self):
        sources = next(x["sources"] for x in CATALOG["retailers"] if x["id"] == "walmart")
        urls = [x["url"] for x in sources]
        got = c.source_failover(
            self.state, CATALOG, "walmart", attempts=2,
            failed_url=urls[0], attempted_urls=urls[1:],
            missing_units=["unreadable-original-page-10"])
        self.assertEqual(got["action"], "source_blocked_rotate_retailer")
        self.assertIsNone(got["source_url"])
        self.assertEqual(got["unresolved_units"], ["unreadable-original-page-10"])

    def test_no_original_visual_read_does_not_assume_complete_inventory(self):
        self.walmart["source_cursor"]["completed_units"] = ["weekly-grid-page1"]
        got = c.source_failover(
            self.state, CATALOG, "walmart", attempts=1,
            failed_url="https://www.example.ca/grid",
            reviewed_original_url=self.walmart["source_cursor"]["source"],
            missing_units=["grid-page-3"])
        self.assertEqual(got["action"], "switch_to_next_fixed_source")
        self.assertFalse(got["coverage_complete"])

    def proof(self):
        return {
            "expected_unit_ids": ["logical-page-1", "logical-page-2"],
            "inventory_reads": {"logical-page-1": "real-read-1",
                                "logical-page-2": "real-read-2"},
            "omission_reads": {"logical-page-1": "independent-revisit-1",
                               "logical-page-2": "independent-revisit-2"},
            "blocked_unit_ids": [],
            "edition_verified": True, "market_verified": True,
            "allow_partial": False, "partial_note": "",
        }

    def test_complete_logical_coverage_can_advance_despite_broken_redundant_mirror(self):
        decision = c.coverage_decision(self.proof())
        self.assertEqual(decision["action"], "prepare_baseline_value_and_quality")
        self.assertTrue(decision["coverage_complete"])
        self.assertTrue(decision["ready_for_baseline_value"])
        self.assertFalse(decision["quality_authorized"])

    def test_missing_first_read_prevents_advance(self):
        p = self.proof()
        p["inventory_reads"].pop("logical-page-2")
        p["omission_reads"].pop("logical-page-2")
        decision = c.coverage_decision(p)
        self.assertEqual(decision["action"], "inventory_missing_units_from_original_or_alternate")
        self.assertEqual(decision["missing_units"], ["logical-page-2"])
        self.assertFalse(decision["ready_for_baseline_value"])

    def test_second_pass_is_mandatory_and_distinct(self):
        p = self.proof()
        p["omission_reads"].pop("logical-page-2")
        self.assertEqual(c.coverage_decision(p)["action"], "finish_distinct_omission_pass")
        p = self.proof()
        p["omission_reads"]["logical-page-2"] = "real-read-2"
        with self.assertRaises(c.CheckpointError):
            c.coverage_decision(p)

    def test_blocked_logical_units_need_strict_partial_exception(self):
        p = self.proof()
        p["inventory_reads"].pop("logical-page-2")
        p["omission_reads"].pop("logical-page-2")
        p["blocked_unit_ids"] = ["logical-page-2"]
        self.assertEqual(
            c.coverage_decision(p)["action"],
            "blocked_units_require_fallback_or_rotation")
        p["allow_partial"] = True
        p["partial_note"] = "Original page 2 inaccessible after matching alternatives"
        d = c.coverage_decision(p)
        self.assertEqual(d["action"], "prepare_disclosed_partial_bundle_for_quality")
        self.assertFalse(d["coverage_complete"])
        self.assertFalse(d["quality_authorized"])

    def test_unverified_market_does_not_advance(self):
        p = self.proof()
        p["market_verified"] = False
        self.assertEqual(c.coverage_decision(p)["action"], "resolve_market_and_edition")

    def test_rotation_chooses_oldest_currently_viable_other_retailer(self):
        self.state["profiles"][0]["observed_at"] = "2026-11-13T00:00:00Z"
        self.state["profiles"][2]["observed_at"] = "2026-11-14T00:00:00Z"
        d = c.rotate_retailer(self.state, "walmart", ["loblaws", "metro"])
        self.assertEqual(d["secondary"], "metro")
        self.assertEqual(d["deep_retailer_cap"], 2)
        self.assertFalse(d["quality_authorized"])
        self.assertEqual(c.rotate_retailer(self.state, "walmart", [])["action"],
                         "no_verified_viable_secondary")

    def test_rotation_excludes_handled_and_uncertain_recipients(self):
        self.state["profiles"][0]["status"] = "done"
        self.state["profiles"][2]["recipients"] = {"slot-a": "uncertain"}
        d = c.rotate_retailer(self.state, "walmart", ["metro", "loblaws", "rexall"])
        self.assertEqual(d["secondary"], "rexall")

    def test_checkpoint_increments_are_not_completed_assessments(self):
        self.state["sequence"] = 900
        d = c.outcome_metrics(self.state)
        self.assertEqual(d["publication_claims"], 0)
        self.assertEqual(d["completed_qualified_delivery_claims"], 0)
        self.assertTrue(d["checkpoint_sequence_is_not_completion"])
        p = self.state["profiles"][2]
        p["publication"] = {"commit": "a" * 40, "directory": "reports/reviewed/l/h",
                            "assessment_path": "state/assessments/id.json"}
        p["last_completed"] = "sent_verified"
        p["next_stage"] = "sent_verified"
        p["recipients"] = {"slot-a": "accepted_verified_in_sent"}
        p["status"] = "done"
        d = c.outcome_metrics(self.state)
        self.assertEqual(d["publication_claims"], 1)
        self.assertEqual(d["completed_qualified_delivery_claims"], 1)
        self.assertIn("require_external_verification", d["status"])

    def test_schema_rejects_missing_coverage_evidence(self):
        p = self.proof()
        p["inventory_reads"]["logical-page-2"] = ""
        with self.assertRaises(c.CheckpointError):
            c.coverage_decision(p)


if __name__ == "__main__":
    unittest.main()
