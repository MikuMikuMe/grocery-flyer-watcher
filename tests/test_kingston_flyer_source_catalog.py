"""Static contract for the fixed Kingston flyer-source catalog, no network required."""
import json
import pathlib
import tomllib
import unittest
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = {
    "metro": "config/watch.toml",
    "food-basics": "config/food-basics.toml",
    "walmart": "config/walmart.toml",
    "loblaws": "config/loblaws.toml",
    "shoppers-drug-mart": "config/shoppers.toml",
    "rexall": "config/rexall.toml",
    "staples": "config/staples.toml",
    "costco": "config/costco.toml",
}

class KingstonFlyerCatalogTests(unittest.TestCase):
    def test_catalog_covers_enabled_registry_with_stable_links(self):
        registry = tomllib.loads((ROOT / "config/profiles.toml").read_text())
        catalog = json.loads((ROOT / "config/kingston_flyer_sources.json").read_text())
        self.assertEqual(catalog["market"], "Kingston, Ontario, Canada")
        indexed = {r["id"]: r for r in catalog["retailers"]}
        self.assertEqual(set(indexed), {r["id"] for r in registry["profiles"]})
        self.assertEqual(set(indexed), set(FILES))
        for rid, row in indexed.items():
            with self.subTest(retailer=rid):
                self.assertTrue(row["store_anchors"])
                self.assertTrue(row["sources"])
                self.assertTrue(row["sources"][0]["role"].startswith("official"))
                links = [x["url"] for x in row["sources"]]
                self.assertEqual(len(links), len(set(links)))
                self.assertTrue(any("archive" in x["role"] for x in row["sources"]) or rid == "costco")
                for item in row["sources"] + row["store_anchors"]:
                    url = item["url"]
                    parsed = urlparse(url)
                    self.assertEqual(parsed.scheme, "https")
                    self.assertNotIn(" ", url)
                    self.assertNotIn("?", url)
                path = ROOT / FILES[rid]
                profile = tomllib.loads(path.read_text())
                for url in links + [x["url"] for x in row["store_anchors"]]:
                    self.assertIn(url, profile["sources"])
        rexall = indexed["rexall"]["sources"]
        self.assertIn("https://flyers.smartcanucks.ca/rexall--canada", [x["url"] for x in rexall])
        self.assertNotIn("https://flyers.smartcanucks.ca/rexall-canada", [x["url"] for x in rexall])

if __name__ == "__main__":
    unittest.main()
