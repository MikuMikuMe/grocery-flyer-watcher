"""Rexall configuration and isolation checks. No network, mail or repository writes."""
import copy
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tomllib
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from grocery_flyer_watch.runner import check_scope, event_key, load_config


class RexallProfileTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "config/profiles.toml").open("rb") as stream:
            self.entries = tomllib.load(stream)["profiles"]
        self.by_id = {entry["id"]: entry for entry in self.entries}
        self.configs = {key: load_config(ROOT / entry["config"])
                        for key, entry in self.by_id.items()}
        self.rexall = self.configs["rexall"]
        today = datetime.now(ZoneInfo(self.rexall["timezone"])).date()
        self.sample = {
            "flyer": {"id": "synthetic-only", "retailer": self.rexall["retailer"],
                      "market": self.rexall["market"], "starts_on": today.isoformat(),
                      "ends_on": (today + timedelta(days=6)).isoformat(),
                      "url": "https://www.rexall.ca/eflyer"},
            "offers": [{"name": "Synthetic household item", "price_cad": "4.99",
                        "pricing": "package", "count": 2, "priority": 4,
                        "why": "Synthetic regression fixture, not a real advertised deal."}]
        }

    def test_all_existing_retailers_remain_enabled(self):
        self.assertTrue({"metro", "shoppers-drug-mart", "rexall"} <= set(self.by_id))
        self.assertEqual(len(self.by_id), len(self.entries))
        self.assertEqual(self.rexall["retailer"], "Rexall")
        self.assertEqual(self.by_id["rexall"]["policy"], "docs/REXALL.md")
        self.assertTrue((ROOT / self.by_id["rexall"]["policy"]).is_file())

    def test_baseline_report_and_state_destinations_are_distinct(self):
        for field in ("baseline", "report_dir"):
            values = [entry[field] for entry in self.entries]
            self.assertEqual(len(set(values)), len(values))
        states = [c["state_file"] for c in self.configs.values()]
        self.assertEqual(len(set(states)), len(states))
        self.assertEqual(self.by_id["rexall"]["baseline"], "data/rexall/latest.json")
        self.assertFalse(self.rexall["state_file"].is_relative_to(self.rexall["output_dir"]))

    def test_rexall_safe_defaults_and_official_sources(self):
        self.assertEqual(self.rexall["collector"], [])
        self.assertEqual(self.rexall["notification"], "none")
        self.assertEqual(self.rexall["publication"], "local")
        self.assertIn("https://www.rexall.ca/eflyer", self.rexall["sources"])
        self.assertIn("https://www.rexall.ca/storelocator/store/1529", self.rexall["sources"])

    def test_rexall_snapshot_does_not_match_other_retailers(self):
        check_scope(self.rexall, self.sample)
        for key in ("metro", "shoppers-drug-mart"):
            with self.subTest(profile=key), self.assertRaises(ValueError):
                check_scope(self.configs[key], self.sample)

    def test_same_prices_have_retailer_scoped_event_keys(self):
        keys = set()
        for key in ("metro", "shoppers-drug-mart", "rexall"):
            other = copy.deepcopy(self.sample)
            other["flyer"]["retailer"] = self.configs[key]["retailer"]
            keys.add(event_key(other))
        self.assertEqual(len(keys), 3)

    def test_restrictions_affect_identity_but_editorial_copy_does_not(self):
        other = copy.deepcopy(self.sample)
        other["offers"][0]["why"] = "Different editorial explanation, same advertised offer."
        self.assertEqual(event_key(other), event_key(self.sample))
        other["offers"][0]["restrictions"] = "Synthetic member-only offer; limit 2"
        self.assertNotEqual(event_key(other), event_key(self.sample))


if __name__ == "__main__":
    unittest.main()
