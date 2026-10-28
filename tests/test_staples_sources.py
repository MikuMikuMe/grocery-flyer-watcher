"""Offline regression checks for all-category Staples collection discovery."""
from pathlib import Path
import sys
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from grocery_flyer_watch.core import validate_snapshot
from grocery_flyer_watch.runner import load_config

DEALS = "https://www.staples.ca/collections/staples-deals-centre"
CLEARANCE = "https://www.staples.ca/collections/staples-clearance-centre-7922"


class StaplesSourceTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT / "config/staples.toml")

    def test_flyer_and_both_collections_are_configured(self):
        required = {"https://www.staples.ca/a/content/flyers", DEALS, CLEARANCE}
        self.assertTrue(required <= set(self.config["sources"]))
        self.assertEqual(len(self.config["sources"]), len(set(self.config["sources"])))

    def test_collection_urls_have_no_category_or_tracking_filters(self):
        for source in (DEALS, CLEARANCE):
            with self.subTest(source=source):
                parsed = urlsplit(source)
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parsed.hostname, "www.staples.ca")
                self.assertFalse(parsed.query or parsed.fragment or parsed.username or parsed.password)

    def test_public_config_keeps_safe_runtime_defaults(self):
        self.assertEqual(self.config["collector"], [])
        self.assertEqual(self.config["notification"], "none")
        self.assertEqual(self.config["publication"], "local")
        self.assertFalse(self.config["state_file"].is_relative_to(self.config["output_dir"]))
        self.assertNotIn("home_store", self.config)
        self.assertNotIn("category_allowlist", self.config)

    def test_shared_offer_schema_does_not_filter_departments(self):
        # Synthetic dated fixtures only. This does not simulate a live collection check.
        names = ["Synthetic chair", "Synthetic cleaning supply", "Synthetic candy",
                 "Synthetic snack", "Synthetic drink", "Synthetic kitchen item",
                 "Synthetic seasonal decoration", "Synthetic laptop",
                 "Synthetic product from another department"]
        for name in names:
            with self.subTest(name=name):
                snapshot = {"flyer": {"id": "synthetic-dated-test", "retailer": "Staples",
                    "market": "Kingston, Ontario", "starts_on": "2026-10-23",
                    "ends_on": "2026-10-29", "url": "https://www.staples.ca/a/content/flyers"},
                    "offers": [{"name": name, "price_cad": "1.00", "pricing": "each",
                                "priority": 1, "why": "Synthetic fixture, not an advertised offer."}]}
                self.assertIs(validate_snapshot(snapshot), snapshot)

    def test_undated_items_are_not_forced_into_the_flyer_schema(self):
        # An undated collection requires the separately documented observation contract.
        snapshot = {"flyer": {"id": "synthetic", "retailer": "Staples",
            "market": "Kingston, Ontario", "url": CLEARANCE},
            "offers": [{"name": "Synthetic candy", "price_cad": "1.00", "pricing": "each",
                        "priority": 1, "why": "Synthetic fixture only."}]}
        with self.assertRaises(ValueError):
            validate_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
