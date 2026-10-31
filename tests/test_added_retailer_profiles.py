"""Offline tests for independently configurable Food Basics, Walmart and Costco watches."""
import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import Mock
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from grocery_flyer_watch.runner import check_scope, event_key, load_config, run, seed

NEW = {"food-basics": "Food Basics", "walmart": "Walmart", "costco": "Costco"}
EXISTING = {"metro", "shoppers-drug-mart", "rexall", "staples"}


class AddedRetailerProfileTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "config/profiles.toml").open("rb") as stream:
            entries = tomllib.load(stream)["profiles"]
        self.entries = {e["id"]: e for e in entries}
        self.assertEqual(len(entries), len(self.entries))
        self.configs = {key: load_config(ROOT / e["config"])
                        for key, e in self.entries.items()}

    def sample(self, key):
        c = self.configs[key]
        today = datetime.now(ZoneInfo(c["timezone"])).date()
        return {"flyer": {"id": "synthetic-not-advertised", "retailer": c["retailer"],
            "market": c["market"], "starts_on": today.isoformat(),
            "ends_on": (today + timedelta(days=6)).isoformat(), "url": c["sources"][0]},
            "offers": [{"name": "Synthetic household pack", "price_cad": "9.99",
                "pricing": "package", "count": 4, "priority": 4,
                "why": "Regression fixture only; not a real price or recommendation."}]}

    def test_all_prior_profiles_preserved_and_new_profiles_registered(self):
        self.assertTrue(EXISTING | set(NEW) <= set(self.entries))
        for key, retailer in NEW.items():
            self.assertEqual(self.configs[key]["retailer"], retailer)
            self.assertEqual(self.configs[key]["market"], "Kingston, Ontario")
            self.assertTrue((ROOT / self.entries[key]["policy"]).is_file())

    def test_separate_public_and_private_destinations(self):
        for field in ("baseline", "report_dir"):
            values = [e[field] for e in self.entries.values()]
            self.assertEqual(len(values), len(set(values)))
            for value in values:
                self.assertTrue((ROOT / value).resolve().is_relative_to(ROOT.resolve()))
        states = [c["state_file"] for c in self.configs.values()]
        self.assertEqual(len(states), len(set(states)))
        for key in NEW:
            self.assertEqual(self.entries[key]["baseline"], f"data/{key}/latest.json")
            self.assertFalse(self.configs[key]["state_file"].is_relative_to(self.configs[key]["output_dir"]))

    def test_safe_defaults_and_clean_multiple_source_hosts(self):
        for key in NEW:
            with self.subTest(profile=key):
                c = self.configs[key]
                self.assertEqual(c["collector"], [])
                self.assertEqual(c["notification"], "none")
                self.assertEqual(c["publication"], "local")
                hosts = set()
                for source in c["sources"]:
                    u = urlsplit(source)
                    self.assertEqual(u.scheme, "https")
                    self.assertFalse(u.query or u.fragment or u.username or u.password)
                    hosts.add(u.hostname)
                self.assertGreaterEqual(len(hosts), 2)

    def test_retailer_scoped_event_keys_and_cross_profile_rejection(self):
        keys = set()
        for key in self.configs:
            data = self.sample(key)
            check_scope(self.configs[key], data)
            keys.add(event_key(data))
            for other in self.configs:
                if key != other:
                    with self.subTest(source=key, other=other), self.assertRaises(ValueError):
                        check_scope(self.configs[other], data)
        self.assertEqual(len(keys), len(self.configs))

    def test_eligibility_changes_are_material_not_commentary(self):
        original = self.sample("costco")
        revised = copy.deepcopy(original)
        revised["offers"][0]["why"] = "Reworded explanation, same synthetic offer."
        self.assertEqual(event_key(original), event_key(revised))
        revised["offers"][0]["restrictions"] = "Synthetic member-only purchase; limit 2"
        self.assertNotEqual(event_key(original), event_key(revised))

    def test_initial_explicit_seed_is_silent_for_each_new_retailer(self):
        # The orchestrator must explicitly seed initial history; run alone is not a value gate.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for key in NEW:
                with self.subTest(profile=key):
                    c = dict(self.configs[key], state_file=root / "private" / (key + ".json"),
                             output_dir=root / "public", notification="smtp")
                    data = self.sample(key)
                    path = root / (key + ".json")
                    path.write_text(json.dumps(data), encoding="utf-8")
                    pub, mail = Mock(), Mock()
                    seed(c, data)
                    self.assertEqual(run(c, path, publisher=pub, notifier=mail), [])
                    pub.assert_not_called()
                    mail.assert_not_called()
            self.assertFalse((root / "public").exists())

    def test_dry_runs_have_no_delivery_or_state_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for key in NEW:
                c = dict(self.configs[key], state_file=root / "private" / (key + ".json"),
                         output_dir=root / "public", notification="smtp")
                path = root / (key + ".json")
                path.write_text(json.dumps(self.sample(key)), encoding="utf-8")
                pub, mail = Mock(), Mock()
                self.assertEqual(len(run(c, path, dry_run=True, publisher=pub, notifier=mail)), 1)
                pub.assert_not_called()
                mail.assert_not_called()
                self.assertFalse(c["state_file"].exists())
            self.assertFalse((root / "public").exists())


if __name__ == "__main__":
    unittest.main()
