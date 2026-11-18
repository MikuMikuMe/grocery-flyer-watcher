"""Public advertising facts are source-verification inputs, NOT mail authorization."""
import copy
import json
import unittest

from grocery_flyer_watch import advertised_facts as facts


class AdvertisedFactsTests(unittest.TestCase):
    def sample(self):
        return {
            "format": "advertised-facts-v1",
            "retailer_id": "walmart",
            "retailer": "Walmart",
            "market": "Kingston, Ontario",
            "edition": {
                "starts_on": "2026-11-12",
                "ends_on": "2026-11-18",
                "source_url": "https://www.weeklyflyer.com/walmart/ontario-weekly",
            },
            "offers": [
                {
                    "name": "Silver Elephant jasmine rice",
                    "pack": "7 kg",
                    "price_cad": "14.98",
                    "pricing": "package",
                    "source_url": "https://www.weeklyflyer.com/walmart/ontario-weekly",
                    "source_quote": "Silver Elephant jasmine rice 7 kg $14.98",
                    "channel": "in_store",
                    "terms": [],
                },
                {
                    "name": "Coca-Cola bottles",
                    "pack": "6 x 710 mL",
                    "price_cad": "3.98",
                    "pricing": "package",
                    "source_url": "https://www.weeklyflyer.com/walmart/ontario-weekly",
                    "source_quote": "Coca-Cola bottles 6 x 710 mL $3.98 Selected flavours",
                    "channel": "in_store",
                    "terms": ["Selected flavours"],
                },
            ],
        }

    def test_build_is_deterministic_and_only_public_advertising_facts(self):
        a = facts.build(self.sample(), expected_market="Kingston, Ontario", expected_retailer_id="walmart")
        b = facts.build(copy.deepcopy(self.sample()), expected_market="Kingston, Ontario", expected_retailer_id="walmart")
        self.assertEqual(a, b)
        self.assertEqual(a["format"], "verified-public-advertising-snapshot-v1")
        self.assertTrue(a["path"].startswith(
            "data/advertisements/walmart/2026-11-12_2026-11-18/"))
        self.assertTrue(a["path"].endswith(".json"))
        self.assertEqual(len(a["sha256"]), 64)
        out = json.loads(a["content"])
        self.assertEqual(out, self.sample())
        self.assertNotIn("recipient", a["content"])
        self.assertNotIn("source_cursor", a["content"])
        self.assertNotIn("authorization", a["content"])
        self.assertFalse(a["quality_authorized"])
        self.assertFalse(a["publication_authorized"])
        self.assertFalse(a["gmail_authorized"])

    def test_contact_private_field_and_webhook_are_rejected(self):
        for variation in (
            lambda x: x.update({"recipient": "secret@example.com"}),
            lambda x: x["offers"][0].update({"evidence_ref": "web:private"}),
            lambda x: x["offers"][0].update({"name": "mail person@example.com"}),
            lambda x: x["offers"][0].update({"terms": ["/api/webhooks/secret"]}),
            lambda x: x["offers"][0].update({"source_url": "https://example.com/?token=123"}),
        ):
            d = self.sample()
            variation(d)
            with self.subTest(input=variation):
                with self.assertRaises(facts.FactsError):
                    facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")

    def test_cash_not_derived_from_savings_amount(self):
        d = self.sample()
        d["offers"][0]["source_quote"] = "Silver Elephant jasmine rice 7 kg SAVE $14.98"
        with self.assertRaises(facts.FactsError):
            facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")

    def test_exact_name_pack_cash_and_quote_are_mandatory(self):
        variants = [
            ("name", "Wrong brand"),
            ("pack", "18 kg"),
            ("price_cad", "14.99"),
            ("price_cad", "0"),
            ("price_cad", "not-a-number"),
            ("pricing", "shipping"),
            ("source_quote", ""),
        ]
        for field, val in variants:
            d = self.sample()
            d["offers"][0][field] = val
            with self.subTest(field=field, val=val):
                with self.assertRaises(facts.FactsError):
                    facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")

    def test_reject_other_market_or_unknown_channel(self):
        d = self.sample()
        d["market"] = "Toronto, Ontario"
        with self.assertRaises(facts.FactsError):
            facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")
        d = self.sample()
        d["offers"][0]["channel"] = "shipping_only"
        with self.assertRaises(facts.FactsError):
            facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")

    def test_reject_invalid_edition_or_empty_offers(self):
        d = self.sample()
        d["edition"]["ends_on"] = "2026-11-11"
        with self.assertRaises(facts.FactsError):
            facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")
        d = self.sample()
        d["offers"] = []
        with self.assertRaises(facts.FactsError):
            facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")

    def test_duplicate_offers_are_rejected(self):
        d = self.sample()
        d["offers"].append(copy.deepcopy(d["offers"][0]))
        with self.assertRaises(facts.FactsError):
            facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")

    def test_unsupported_terms_without_a_quote_are_rejected(self):
        d = self.sample()
        d["offers"][0]["terms"] = ["Members only"]
        with self.assertRaises(facts.FactsError):
            facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart")

    def test_wrong_profile_rejected(self):
        d = self.sample()
        with self.assertRaises(facts.FactsError):
            facts.build(d, expected_market="Kingston, Ontario", expected_retailer_id="loblaws")

    def test_build_cannot_send_or_write_anything(self):
        d = self.sample()
        self.assertNotIn("gmail", vars(facts))
        self.assertNotIn("send", vars(facts))
        self.assertNotIn("publish", vars(facts))
        self.assertIsNone(facts.validate_snapshot(d, expected_market="Kingston, Ontario", expected_retailer_id="walmart"))


if __name__ == "__main__":
    unittest.main()
