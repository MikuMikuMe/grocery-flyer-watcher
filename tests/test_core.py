"""Offline snapshot and privacy tests."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from metro_flyer_watch.core import changed, fingerprint, read_snapshot, render_report, unit_price, validate_snapshot

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "latest.json"


class FlyerTests(unittest.TestCase):
    def setUp(self):
        self.snap = read_snapshot(FIXTURE)

    def test_fixture(self):
        self.assertEqual(self.snap["flyer"]["id"], "8192488")

    def test_reorder_and_comment_do_not_change_offers(self):
        other = copy.deepcopy(self.snap)
        other["offers"].reverse()
        other["offers"][0]["priority"] = 1
        other["offers"][0]["why"] = "Edited public commentary."
        self.assertEqual(fingerprint(self.snap), fingerprint(other))

    def test_price_change(self):
        other = copy.deepcopy(self.snap)
        other["offers"][0]["price_cad"] = "0.99"
        self.assertTrue(changed(self.snap, other))

    def test_new_flyer(self):
        other = copy.deepcopy(self.snap)
        other["flyer"]["id"] = "8192490"
        self.assertTrue(changed(self.snap, other))

    def test_mass_unit(self):
        rice = next(o for o in self.snap["offers"] if "basmati" in o["name"].lower())
        self.assertEqual(unit_price(rice), "$2.20/kg")

    def test_pound_unit(self):
        pork = next(o for o in self.snap["offers"] if "ground pork" in o["name"].lower())
        self.assertEqual(unit_price(pork), "$4.39/kg ($1.99/lb)")

    def test_email_rejected(self):
        other = copy.deepcopy(self.snap)
        other["offers"][0]["why"] = "Write to name" + chr(64) + "example.org"
        with self.assertRaises(ValueError):
            validate_snapshot(other)

    def test_secret_rejected(self):
        other = copy.deepcopy(self.snap)
        other["offers"][0]["why"] = "token=abc123"
        with self.assertRaises(ValueError):
            validate_snapshot(other)

    def test_extra_field_rejected(self):
        other = copy.deepcopy(self.snap)
        other["private_contact"] = "hidden"
        with self.assertRaises(ValueError):
            validate_snapshot(other)

    def test_tracking_query_rejected(self):
        other = copy.deepcopy(self.snap)
        other["flyer"]["url"] += "?postal_code=not_public"
        with self.assertRaises(ValueError):
            validate_snapshot(other)

    def test_duplicate_names_rejected(self):
        other = copy.deepcopy(self.snap)
        other["offers"].append(copy.deepcopy(other["offers"][0]))
        with self.assertRaises(ValueError):
            validate_snapshot(other)

    def test_report(self):
        report = render_report(self.snap)
        self.assertIn("Flyer ID: 8192488", report)
        self.assertIn("ground pork", report)
        self.assertNotIn(chr(64), report)


if __name__ == "__main__":
    unittest.main()
