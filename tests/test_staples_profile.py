"""Staples profile regressions: synthetic fixtures, no network or real deliveries."""
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


class StaplesProfileTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "config/profiles.toml").open("rb") as stream:
            self.entries = tomllib.load(stream)["profiles"]
        self.by_id = {entry["id"]: entry for entry in self.entries}
        self.configs = {key: load_config(ROOT / entry["config"])
                        for key, entry in self.by_id.items()}
        self.staples = self.configs["staples"]
        today = datetime.now(ZoneInfo(self.staples["timezone"])).date()
        self.sample = {
            "flyer": {"id": "synthetic-only", "retailer": "Staples",
                      "market": self.staples["market"], "starts_on": today.isoformat(),
                      "ends_on": (today + timedelta(days=6)).isoformat(),
                      "url": "https://www.staples.ca/a/content/flyers"},
            "offers": [{"name": "Synthetic monitor MODEL-A", "price_cad": "99.99",
                        "pricing": "each", "priority": 4,
                        "why": "Synthetic test data, not a real advertised offer."}]
        }

    def test_all_existing_profiles_remain_and_policy_is_readable(self):
        self.assertTrue({"metro", "shoppers-drug-mart", "rexall", "staples"} <= set(self.by_id))
        self.assertEqual(len(self.entries), len(self.by_id))
        self.assertEqual(self.staples["retailer"], "Staples")
        self.assertEqual(self.by_id["staples"]["policy"], "docs/STAPLES.md")
        self.assertTrue((ROOT / self.by_id["staples"]["policy"]).is_file())

    def test_destinations_and_state_are_independent(self):
        for field in ("baseline", "report_dir"):
            values = [entry[field] for entry in self.entries]
            self.assertEqual(len(values), len(set(values)))
            self.assertTrue(all((ROOT / value).resolve().is_relative_to(ROOT.resolve())
                                for value in values))
        states = [c["state_file"] for c in self.configs.values()]
        self.assertEqual(len(states), len(set(states)))
        self.assertEqual(self.by_id["staples"]["baseline"], "data/staples/latest.json")
        self.assertFalse(self.staples["state_file"].is_relative_to(self.staples["output_dir"]))

    def test_safe_defaults_and_multiple_source_families(self):
        self.assertEqual(self.staples["collector"], [])
        self.assertEqual(self.staples["notification"], "none")
        self.assertEqual(self.staples["publication"], "local")
        hosts = {urlsplit(source).hostname for source in self.staples["sources"]}
        self.assertTrue({"www.staples.ca", "stores.staples.ca", "flyers.smartcanucks.ca",
                         "www.flyers-on-line.com"} <= hosts)
        for source in self.staples["sources"]:
            parsed = urlsplit(source)
            self.assertEqual(parsed.scheme, "https")
            self.assertFalse(parsed.query or parsed.fragment or parsed.username or parsed.password)
            self.assertNotEqual(parsed.hostname, "www.staples.com")

    def test_staples_scope_rejects_cross_retailer_data(self):
        check_scope(self.staples, self.sample)
        for key, config in self.configs.items():
            if key != "staples":
                with self.subTest(profile=key), self.assertRaises(ValueError):
                    check_scope(config, self.sample)

    def test_exact_model_and_retailer_change_identity(self):
        keys = set()
        for config in self.configs.values():
            other = copy.deepcopy(self.sample)
            other["flyer"]["retailer"] = config["retailer"]
            keys.add(event_key(other))
        self.assertEqual(len(keys), len(self.configs))
        other = copy.deepcopy(self.sample)
        other["offers"][0]["name"] = "Synthetic monitor MODEL-B"
        self.assertNotEqual(event_key(other), event_key(self.sample))

    def test_coupon_terms_material_editorial_wording_not_material(self):
        other = copy.deepcopy(self.sample)
        other["offers"][0]["why"] = "Updated explanation of the same synthetic offer."
        self.assertEqual(event_key(other), event_key(self.sample))
        other["offers"][0]["restrictions"] = "Synthetic coupon required; limit 1; pickup only"
        self.assertNotEqual(event_key(other), event_key(self.sample))
        self.assertEqual(other["offers"][0]["price_cad"], "99.99")

    def test_explicit_silent_seed_does_not_publish_or_deliver(self):
        # Orchestrators must seed initial verified baselines; run alone is not the gate.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            c = dict(self.staples, state_file=root / "private" / "state.json",
                     output_dir=root / "public", notification="smtp")
            input_path = root / "verified-synthetic.json"
            input_path.write_text(json.dumps(self.sample), encoding="utf-8")
            publisher, notifier = Mock(), Mock()
            seed(c, self.sample)
            self.assertEqual(run(c, input_path, publisher=publisher, notifier=notifier), [])
            publisher.assert_not_called()
            notifier.assert_not_called()
            self.assertFalse(c["output_dir"].exists())

    def test_dry_run_has_no_delivery_or_state_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            c = dict(self.staples, state_file=root / "private" / "state.json",
                     output_dir=root / "public", notification="smtp")
            input_path = root / "verified-synthetic.json"
            input_path.write_text(json.dumps(self.sample), encoding="utf-8")
            publisher, notifier = Mock(), Mock()
            self.assertEqual(len(run(c, input_path, dry_run=True,
                                     publisher=publisher, notifier=notifier)), 1)
            publisher.assert_not_called()
            notifier.assert_not_called()
            self.assertFalse(c["state_file"].exists())
            self.assertFalse(c["output_dir"].exists())


if __name__ == "__main__":
    unittest.main()
