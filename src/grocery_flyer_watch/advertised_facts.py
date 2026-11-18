"""Build create-only PUBLIC advertising-fact chunks from inspected sources.

This is an offline, source-agnostic consistency gate. A verified source read
and independent local/edition applicability check must happen BEFORE calling it.
A valid chunk does not prove complete inventory, review quality, new value,
publication, Gmail authorization or any delivery outcome.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys

from . import review

FORMAT = "advertised-facts-v1"
OUTPUT_FORMAT = "verified-public-advertising-snapshot-v1"
TOP_FIELDS = {"format", "retailer_id", "retailer", "market", "edition", "offers"}
EDITION_FIELDS = {"starts_on", "ends_on", "source_url"}
OFFER_FIELDS = {"name", "pack", "price_cad", "pricing", "source_url",
                "source_quote", "channel", "terms"}
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
CASH_RE = re.compile(r"(?:0|[1-9]\d{0,5})\.\d{2}\Z")
PRICING = {"package", "each", "per_lb", "per_kg"}
CHANNELS = {"in_store", "pickup", "unverified"}


class FactsError(ValueError):
    """Error codes only; never put untrusted advertisement data in exceptions."""


def check(condition: bool, code: str) -> None:
    if not condition:
        raise FactsError(code)


def _text(value: object, code: str) -> str:
    try:
        return review.text(value, code)
    except review.ReviewError:
        raise FactsError(code) from None


def _url(value: object, code: str) -> str:
    try:
        return review.url(value)
    except review.ReviewError:
        raise FactsError(code) from None


def _iso(value: object, code: str) -> date:
    try:
        return review.iso(value)
    except review.ReviewError:
        raise FactsError(code) from None


def validate_snapshot(snapshot: dict, *, expected_market: str,
                      expected_retailer_id: str) -> None:
    """Check public-only facts; assert NO source-reading or delivery authority."""
    check(isinstance(snapshot, dict) and set(snapshot) == TOP_FIELDS, "facts_schema")
    check(snapshot["format"] == FORMAT, "facts_version")
    ident = snapshot["retailer_id"]
    check(isinstance(ident, str) and ID_RE.fullmatch(ident) is not None
          and ident == expected_retailer_id, "facts_retailer_scope")
    check(_text(snapshot["retailer"], "facts_retailer") is not None, "facts_retailer")
    check(_text(snapshot["market"], "facts_market") == expected_market and
          _text(expected_market, "facts_market") is not None, "facts_market_scope")
    edition = snapshot["edition"]
    check(isinstance(edition, dict) and set(edition) == EDITION_FIELDS,
          "facts_edition_schema")
    start, end = (_iso(edition["starts_on"], "facts_edition_date"),
                  _iso(edition["ends_on"], "facts_edition_date"))
    check(start <= end and (end - start).days <= 70, "facts_edition_window")
    _url(edition["source_url"], "facts_edition_url")
    offers = snapshot["offers"]
    check(isinstance(offers, list) and 1 <= len(offers) <= 150, "facts_offer_count")
    seen = set()
    for item in offers:
        check(isinstance(item, dict) and set(item) == OFFER_FIELDS,
              "facts_offer_schema")
        name = _text(item["name"], "facts_name")
        quote = _text(item["source_quote"], "facts_source_quote")
        _url(item["source_url"], "facts_source_url")
        check(review.norm(name) in review.norm(quote),
              "facts_name_not_in_advertisement")
        price = item["price_cad"]
        check(isinstance(price, str) and CASH_RE.fullmatch(price) is not None,
              "facts_cash_price_format")
        try:
            cash = review.money(price)
        except review.ReviewError:
            raise FactsError("facts_cash_price") from None
        check(review.contains_amount(quote, cash), "facts_cash_not_in_advertisement")
        pricing = item["pricing"]
        check(pricing in PRICING, "facts_pricing")
        pack = item["pack"]
        if pricing == "package":
            pack = _text(pack, "facts_pack")
            check(review.norm(pack) in review.norm(quote),
                  "facts_pack_not_in_advertisement")
        else:
            check(pack == "" or isinstance(pack, str) and review.norm(pack) in review.norm(quote),
                  "facts_pack_not_in_advertisement")
        if pricing in {"per_lb", "per_kg"}:
            unit = "lb" if pricing == "per_lb" else "kg"
            check(re.search(r"(?:/|per\s+)" + unit + r"\b", quote, re.I) is not None,
                  "facts_unit_not_in_advertisement")
        check(item["channel"] in CHANNELS, "facts_channel")
        terms = item["terms"]
        check(isinstance(terms, list) and len(terms) <= 20,
              "facts_terms_schema")
        for term in terms:
            content = _text(term, "facts_terms")
            check(review.norm(content) in review.norm(quote),
                  "facts_terms_not_in_advertisement")
        key = (review.norm(name), review.norm(pack), pricing, item["price_cad"],
               item["source_url"])
        check(key not in seen, "facts_duplicate_offer")
        seen.add(key)


def build(snapshot: dict, *, expected_market: str,
          expected_retailer_id: str) -> dict:
    """Render canonical public facts; caller must privacy-review/create in GitHub."""
    validate_snapshot(snapshot, expected_market=expected_market,
                      expected_retailer_id=expected_retailer_id)
    content = json.dumps(snapshot, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    dates = snapshot["edition"]
    path = (f"data/advertisements/{expected_retailer_id}/"
            f"{dates['starts_on']}_{dates['ends_on']}/{digest}.json")
    return {
        "format": OUTPUT_FORMAT, "path": path, "sha256": digest,
        "content": content, "quality_authorized": False,
        "publication_authorized": False, "gmail_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--market", required=True)
    parser.add_argument("--retailer-id", required=True)
    args = parser.parse_args(argv)
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        result = build(snapshot, expected_market=args.market,
                       expected_retailer_id=args.retailer_id)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (FactsError, ValueError, OSError) as exc:
        code = str(exc) if isinstance(exc, FactsError) else "facts_read_or_format_error"
        print(json.dumps({"status": "facts_blocked", "code": code,
                          "gmail_authorized": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
