"""Retailer isolation tests using synthetic data; no network, real mail or Git writes."""
import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import Mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from grocery_flyer_watch.core import render_report
from grocery_flyer_watch.runner import check_scope, event_key, load_config, read_state, run


def fixture(retailer, url):
    today = datetime.now(ZoneInfo("America/Toronto")).date()
    return {"flyer": {"id": "synthetic-edition", "retailer": retailer,
        "market": "Kingston, Ontario", "starts_on": today.isoformat(),
        "ends_on": (today + timedelta(days=6)).isoformat(), "url": url},
        "offers": [{"name": "Synthetic paper product", "price_cad": "4.99",
            "pricing": "package", "count": 6, "priority": 3,
            "why": "Test data, not a real advertised deal."}]}


class MultiProfileTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "config/profiles.toml").open("rb") as stream:
            self.registry = tomllib.load(stream)
        self.entries = {p["id"]: p for p in self.registry["profiles"]}
        self.metro = load_config(ROOT / self.entries["metro"]["config"])
        self.shoppers = load_config(ROOT / self.entries["shoppers-drug-mart"]["config"])

    def test_registry_keeps_both_profiles_with_distinct_destinations(self):
        self.assertEqual(self.registry["version"], 1)
        self.assertEqual(len(self.entries), len(self.registry["profiles"]))
        self.assertEqual(self.metro["retailer"], "Metro")
        self.assertEqual(self.shoppers["retailer"], "Shoppers Drug Mart")
        self.assertNotEqual(self.entries["metro"]["baseline"], self.entries["shoppers-drug-mart"]["baseline"])
        for entry in self.registry["profiles"]:
            for key in ("config", "baseline", "report_dir"):
                self.assertTrue((ROOT / entry[key]).resolve().is_relative_to(ROOT.resolve()))
            self.assertTrue((ROOT / entry["config"]).is_file())
            if "policy" in entry:
                self.assertTrue((ROOT / entry["policy"]).is_file())

    def test_state_is_isolated_and_defaults_have_no_external_side_effects(self):
        self.assertNotEqual(self.metro["state_file"], self.shoppers["state_file"])
        for c in (self.metro, self.shoppers):
            self.assertEqual(c["notification"], "none")
            self.assertEqual(c["publication"], "local")
            self.assertEqual(c["collector"], [])
            self.assertFalse(c["state_file"].is_relative_to(c["output_dir"]))

    def test_same_dates_and_prices_are_different_events_by_retailer(self):
        metro = fixture("Metro", "https://www.metro.ca/en/flyer")
        shoppers = fixture("Shoppers Drug Mart", "https://www.shoppersdrugmart.ca/flyer")
        self.assertNotEqual(event_key(metro), event_key(shoppers))

    def test_shoppers_snapshot_is_rejected_by_metro_profile(self):
        shoppers = fixture("Shoppers Drug Mart", "https://www.shoppersdrugmart.ca/flyer")
        check_scope(self.shoppers, shoppers)
        with self.assertRaises(ValueError):
            check_scope(self.metro, shoppers)

    def test_promotion_conditions_are_material_and_visible(self):
        first = fixture("Shoppers Drug Mart", "https://www.shoppersdrugmart.ca/flyer")
        revised = copy.deepcopy(first)
        revised["offers"][0]["restrictions"] = "Weekend only; limit 2; PC Optimum eligibility required"
        self.assertNotEqual(event_key(first), event_key(revised))
        self.assertIn("Weekend only", render_report(revised))
        self.assertEqual(revised["offers"][0]["price_cad"], "4.99")

    def test_each_profile_delivers_once_and_repeat_is_silent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pub, mail = Mock(), Mock()
            profiles = []
            for slug, original in (("metro", self.metro), ("shoppers", self.shoppers)):
                c = dict(original, state_file=root / slug / "state.json", output_dir=root / "public", notification="smtp")
                data = fixture(c["retailer"], c["sources"][0])
                path = root / (slug + ".json")
                path.write_text(json.dumps(data), encoding="utf-8")
                profiles.append((c, path))
                self.assertEqual(len(run(c, path, publisher=pub, notifier=mail)), 1)
            self.assertEqual(pub.call_count, 2)
            self.assertEqual(mail.call_count, 2)
            for c, path in profiles:
                self.assertEqual(run(c, path, publisher=pub, notifier=mail), [])
                self.assertEqual(len(read_state(c["state_file"])["events"]), 1)
            self.assertEqual(mail.call_count, 2)

    def test_one_profile_failure_does_not_change_the_other_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = root / "unavailable.json"
            bad.write_text(json.dumps({"status": "unavailable", "snapshots": []}), encoding="utf-8")
            metro = dict(self.metro, state_file=root / "metro-state.json")
            with self.assertRaises(ValueError):
                run(metro, bad, publisher=Mock(), notifier=Mock())
            good = root / "shoppers.json"
            good.write_text(json.dumps(fixture("Shoppers Drug Mart", self.shoppers["sources"][0])), encoding="utf-8")
            shoppers = dict(self.shoppers, state_file=root / "shoppers-state.json", notification="smtp")
            mail = Mock()
            self.assertEqual(len(run(shoppers, good, publisher=Mock(), notifier=mail)), 1)
            mail.assert_called_once()
            self.assertEqual(len(read_state(metro["state_file"])["events"]), 0)


if __name__ == "__main__":
    unittest.main()
