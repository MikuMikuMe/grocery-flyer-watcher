"""Offline, retailer-neutral pre-send review and canonical digest renderer.

This validates supplied evidence and consistency; it cannot prove a page was read or
that an advertisement is true. It performs no browsing, Git writes, or email delivery.
Keep the review plan private. Only the projected selection and report are public.
"""
from __future__ import annotations

from .diagnostics import traced, emit, safe_code

import argparse
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

SECTIONS = ("Best buys", "Worth buying", "Not worth treating as headline bargains")
CONTACT = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
SECRET = re.compile(r"github_pat_|ghp_|/api/webhooks/|(?:password|token|secret)\s*[:=]", re.I)
REQUIRED = {"version", "retailer", "market", "timezone", "campaign_key", "period_label",
            "change", "coverage", "candidates", "selected_ids", "second_pass", "shortfall"}
CANDIDATE = {"id", "promotion_id", "unit_id", "department", "source_url", "source_quote",
             "source_name", "price_cad", "price_kind", "pricing", "pack", "starts_on",
             "ends_on", "verified_on", "channel", "terms", "priority", "prominent",
             "decision", "reason", "section", "assessment", "comparison"}


class ReviewError(ValueError):
    """Safe diagnostic codes only: never echo private plan values in logs."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReviewError(code)


def keys(value: object, required: set[str], code: str) -> None:
    require(isinstance(value, dict) and set(value) == required, code)


def text(value: object, code: str, *, empty: bool = False) -> str:
    require(isinstance(value, str), code)
    require((empty or bool(value.strip())) and len(value) <= 3000, code)
    require(not any(ord(c) < 32 for c in value), code)
    require(not CONTACT.search(value) and not SECRET.search(value), "private_data_in_public_field")
    return value


def url(value: object) -> str:
    value = text(value, "source_url")
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and bool(parsed.hostname) and "." in parsed.hostname
            and not parsed.username and not parsed.password and not parsed.query
            and not parsed.fragment, "unclean_source_url")
    return value


def norm(value: str) -> str:
    return " ".join(value.casefold().split())


def money(value: object) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ReviewError("invalid_cash_price") from None
    require(number.is_finite() and number > 0, "invalid_cash_price")
    return number


def iso(value: object) -> date:
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None,
            "invalid_date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ReviewError("invalid_date") from None


def contains_amount(quote: str, amount: Decimal) -> bool:
    pattern = r"(?<![\w.])(?P<currency>\$\s*)?(?P<number>\d+(?:,\d{3})*(?:\.\d{1,2})?)(?![\w.])"
    for match in re.finditer(pattern, quote):
        raw = match.group("number")
        if not match.group("currency") and "." not in raw:
            continue
        if Decimal(raw.replace(",", "")) != amount:
            continue
        prefix = quote[max(0, match.start() - 20):match.start()]
        suffix = quote[match.end():match.end() + 5]
        if not re.search(r"(?:save|saving|savings|off)\s*$", prefix, re.I) and not re.match(r"\s*off\b", suffix, re.I):
            return True
    return False


def price_label(candidate: dict) -> str:
    suffix = {"per_lb": "/lb", "per_kg": "/kg", "package": "/pack", "each": " each"}
    return f"${money(candidate['price_cad']):.2f}{suffix[candidate['pricing']]}"


def comparison_text(candidate: dict) -> str:
    """Render only structured comparisons with explicit, equal, evidenced attributes."""
    comp = candidate["comparison"]
    if comp is None:
        return ""
    keys(comp, {"retailer", "source_url", "source_quote", "price_cad", "pricing",
                "kind", "ours", "theirs"}, "comparison_schema")
    text(comp["retailer"], "comparison_retailer")
    quote = text(comp["source_quote"], "comparison_quote")
    url(comp["source_url"])
    dimensions = {
        "meat": {"species", "cut", "bone", "state"},
        "model": {"model", "condition"},
        "pack": {"brand", "product", "pack"},
    }
    require(comp["kind"] in dimensions, "comparison_kind")
    if norm(candidate["department"]) in {"meat", "butcher", "beef", "pork", "poultry", "seafood"}:
        require(comp["kind"] == "meat", "meat_comparison_needs_cut_and_bone")
    for side in ("ours", "theirs"):
        keys(comp[side], dimensions[comp["kind"]], "comparison_dimensions_missing")
    for attribute in dimensions[comp["kind"]]:
        left, right = comp["ours"][attribute], comp["theirs"][attribute]
        text(left, "comparison_attribute")
        text(right, "comparison_attribute")
        require(norm(left) not in {"unknown", "unspecified", "n/a", "none"},
                "unknown_comparison_attribute")
        require(norm(left) == norm(right), "non_equivalent_comparison")
        require(norm(left) in norm(candidate["source_quote"]) and norm(right) in norm(quote),
                "comparison_attribute_not_in_evidence")
    require(comp["pricing"] == candidate["pricing"], "comparison_unit_mismatch")
    if candidate["pack"]:
        require(norm(candidate["pack"]) in norm(quote), "comparison_pack_mismatch")
    if candidate["pricing"] in {"per_lb", "per_kg"}:
        unit = "lb" if candidate["pricing"] == "per_lb" else "kg"
        require(re.search(r"(?:/|per\s+)" + unit + r"\b", quote, re.I) is not None,
                "comparison_unit_not_in_evidence")
    if comp["kind"] == "meat":
        for attribute in ("skinless", "skin-on", "organic", "angus", "aaa"):
            require((attribute in norm(candidate["source_quote"])) == (attribute in norm(quote)),
                    "comparison_additional_attribute_mismatch")
    other_price = money(comp["price_cad"])
    require(contains_amount(quote, other_price), "comparison_price_not_in_evidence")
    return f"Compared with {comp['retailer']} at {price_label(comp)}."


@traced('review.validate')
def validate(plan: dict, today: date | None = None) -> None:
    keys(plan, REQUIRED, "review_schema")
    require(type(plan["version"]) is int and plan["version"] == 1, "review_version")
    for field in ("retailer", "market", "timezone", "campaign_key", "period_label"):
        text(plan[field], "missing_header")
    today = today or datetime.now(ZoneInfo(plan["timezone"])).date()
    change = plan["change"]
    keys(change, {"kind", "baseline_ref", "evidence_refs"}, "change_schema")
    require(change["kind"] in {"new_edition", "material_offer_change"}, "no_qualifying_change")
    require(isinstance(change["baseline_ref"], str) and bool(change["baseline_ref"].strip()),
            "baseline_missing")
    require(isinstance(change["evidence_refs"], list) and bool(change["evidence_refs"]),
            "change_evidence_missing")
    for ref in change["evidence_refs"]:
        url(ref)

    coverage = plan["coverage"]
    keys(coverage, {"inventory_url", "inventory_complete", "expected_unit_ids", "units",
                    "partial_note"}, "coverage_schema")
    url(coverage["inventory_url"])
    require(type(coverage["inventory_complete"]) is bool, "coverage_completeness_missing")
    expected = coverage["expected_unit_ids"]
    require(isinstance(expected, list) and bool(expected)
            and all(isinstance(x, str) and x for x in expected)
            and len(expected) == len(set(expected)), "source_inventory_missing")
    require(isinstance(coverage["units"], list), "source_inventory_missing")
    units = {}
    for unit in coverage["units"]:
        keys(unit, {"id", "url", "status", "evidence_ref", "candidate_ids", "note"},
             "coverage_unit_schema")
        require(isinstance(unit["id"], str) and unit["id"] not in units, "duplicate_source_unit")
        url(unit["url"])
        require(unit["status"] in {"reviewed", "blocked"}, "unreviewed_source_unit")
        require(isinstance(unit["candidate_ids"], list)
                and all(isinstance(x, str) and x for x in unit["candidate_ids"])
                and len(set(unit["candidate_ids"])) == len(unit["candidate_ids"]), "unit_candidates")
        require(isinstance(unit["evidence_ref"], str) and unit["evidence_ref"].strip(),
                "page_evidence_missing")
        if unit["status"] == "blocked":
            require(not unit["candidate_ids"] and bool(unit["note"].strip()), "blocked_unit_not_explained")
        units[unit["id"]] = unit
    require(set(expected) == set(units), "source_pages_missing")
    partial = not coverage["inventory_complete"] or any(u["status"] == "blocked" for u in units.values())
    text(coverage["partial_note"], "partial_coverage_must_be_disclosed", empty=not partial)
    require(partial or not coverage["partial_note"], "spurious_partial_note")

    require(isinstance(plan["candidates"], list) and bool(plan["candidates"]), "no_candidates")
    candidates = {}
    for candidate in plan["candidates"]:
        keys(candidate, CANDIDATE, "candidate_schema")
        cid = text(candidate["id"], "candidate_id")
        require(cid not in candidates, "duplicate_candidate")
        text(candidate["promotion_id"], "promotion_identity_missing")
        text(candidate["department"], "department_missing")
        unit = units.get(candidate["unit_id"])
        require(unit is not None and unit["status"] == "reviewed", "candidate_source_unreviewed")
        require(cid in unit["candidate_ids"], "candidate_not_in_page_inventory")
        require(candidate["decision"] in {"include", "exclude"}, "unresolved_candidate")
        require(type(candidate["priority"]) is int and 1 <= candidate["priority"] <= 5,
                "candidate_priority")
        require(type(candidate["prominent"]) is bool, "prominence_not_assessed")
        require(isinstance(candidate["reason"], str) and bool(candidate["reason"].strip()),
                "selection_reason_missing")
        url(candidate["source_url"])
        quote = text(candidate["source_quote"], "source_quote_missing")
        name = text(candidate["source_name"], "source_product_missing")
        require(norm(name) in norm(quote), "product_description_not_in_evidence")
        candidates[cid] = candidate
    declared = [cid for u in units.values() for cid in u["candidate_ids"]]
    require(len(declared) == len(set(declared)) and set(declared) == set(candidates),
            "page_candidate_inventory_mismatch")

    selected = plan["selected_ids"]
    require(isinstance(selected, list) and all(isinstance(x, str) for x in selected)
            and len(selected) == len(set(selected)), "duplicate_selection")
    require(set(selected) == {cid for cid, c in candidates.items() if c["decision"] == "include"},
            "selection_decisions_mismatch")
    require(1 <= len(selected) <= 10, "selection_size")
    shortfall = plan["shortfall"]
    keys(shortfall, {"reason", "reviewed"}, "shortfall_schema")
    if len(selected) < 8:
        text(shortfall["reason"], "shortfall_unexplained")
        require(shortfall["reviewed"] is True, "shortfall_not_reviewed")
        require(not any(c["decision"] == "exclude" and c["priority"] >= 3
                        and c["promotion_id"] not in {candidates[x]["promotion_id"] for x in selected}
                        for c in candidates.values()), "useful_candidates_excluded_from_short_digest")
    else:
        require(shortfall["reason"] == "" and shortfall["reviewed"] is False,
                "unexpected_shortfall_override")
    promotion_ids = [candidates[cid]["promotion_id"] for cid in selected]
    require(len(promotion_ids) == len(set(promotion_ids)), "same_offer_counted_twice")

    useful = 0
    for cid in selected:
        c = candidates[cid]
        require(c["price_kind"] == "cash", "saving_amount_is_not_cash_price")
        cash = money(c["price_cad"])
        require(contains_amount(c["source_quote"], cash), "cash_price_not_in_evidence")
        require(c["pricing"] in {"per_lb", "per_kg", "package", "each"}, "pricing_unit")
        if c["pricing"] in {"per_lb", "per_kg"}:
            unit = "lb" if c["pricing"] == "per_lb" else "kg"
            require(re.search(r"(?:/|per\s+)" + unit + r"\b", c["source_quote"], re.I) is not None,
                    "price_unit_not_in_evidence")
        pack = text(c["pack"], "exact_pack_missing", empty=c["pricing"] in {"per_lb", "per_kg", "each"})
        if pack:
            require(norm(pack) in norm(c["source_quote"]), "pack_not_in_evidence")
        require(iso(c["verified_on"]) == today, "selected_offer_not_rechecked_today")
        start = iso(c["starts_on"]) if c["starts_on"] is not None else None
        end = iso(c["ends_on"]) if c["ends_on"] is not None else None
        require(end is None or end >= today, "expired_item_promotion")
        require(start is None or end is None or start <= end, "invalid_item_window")
        require(c["section"] in SECTIONS, "selection_section")
        require(c["channel"] in {"in_store", "pickup", "unverified", "shipping_only"}, "purchase_channel")
        require(c["channel"] != "shipping_only", "ineligible_purchase_channel")
        text(c["assessment"], "public_assessment_missing")
        require(isinstance(c["terms"], list), "terms_schema")
        for term in c["terms"]:
            text(term, "purchase_condition")
        if c["channel"] == "unverified":
            require(c["section"] == SECTIONS[2] and bool(c["terms"]),
                    "unknown_local_eligibility_cannot_be_best_buy")
        if c["section"] != SECTIONS[2] and c["priority"] >= 3 and c["channel"] in {"in_store", "pickup"}:
            useful += 1
        comparison_text(c)
    require(useful > len(selected) // 2, "roundup_mostly_weak_or_unverified")

    audit = plan["second_pass"]
    keys(audit, {"source_unit_ids", "candidate_ids", "prominent_ids", "omission_notes",
                 "unresolved"}, "second_pass_missing")
    for field, expected_set in (
        ("source_unit_ids", {uid for uid, u in units.items() if u["status"] == "reviewed"}),
        ("candidate_ids", set(candidates)),
        ("prominent_ids", {cid for cid, c in candidates.items() if c["prominent"]}),
    ):
        values = audit[field]
        require(isinstance(values, list) and len(values) == len(set(values))
                and set(values) == expected_set, "second_pass_coverage_gap")
    require(audit["unresolved"] == [], "unresolved_audit_findings")
    omitted = {cid for cid, c in candidates.items() if c["decision"] == "exclude"
               and (c["prominent"] or c["priority"] >= 4)}
    require(isinstance(audit["omission_notes"], dict) and set(audit["omission_notes"]) == omitted,
            "prominent_or_strong_offer_omitted_without_audit")
    require(all(isinstance(v, str) and bool(v.strip()) for v in audit["omission_notes"].values()),
            "empty_omission_audit")


@traced('review.project')
def project(plan: dict, today: date | None = None) -> dict:
    """Single public selection; never export coverage logs, reasons or private history."""
    validate(plan, today)
    by_id = {c["id"]: c for c in plan["candidates"]}
    items = []
    for cid in plan["selected_ids"]:
        c = by_id[cid]
        item = {k: c[k] for k in ("id", "promotion_id", "source_name", "source_url",
                "price_cad", "pricing", "pack", "starts_on", "ends_on", "terms",
                "section", "assessment")}
        item["comparison"] = comparison_text(c)
        item["comparison_source"] = c["comparison"]["source_url"] if c["comparison"] else None
        items.append(item)
    result = {"format": "reviewed-selection-v1", "retailer": plan["retailer"],
              "market": plan["market"], "campaign_key": plan["campaign_key"],
              "period_label": plan["period_label"], "items": items,
              "coverage_note": plan["coverage"]["partial_note"],
              "shortfall_note": plan["shortfall"]["reason"]}
    # This locks the editorial selection; it is NOT the notification/deduplication key.
    result["selection_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result


def escape(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>|])", r"\\\1", value)


@traced('review.render')
def render(selection: dict, report_url: str) -> str:
    url(report_url)
    lines = [f"# {escape(selection['retailer'])} | {escape(selection['period_label'])}", ""]
    all_undated = all(not x["starts_on"] and not x["ends_on"] for x in selection["items"])
    if all_undated:
        lines += ["No advertised end date.", ""]
    for section in SECTIONS:
        items = [x for x in selection["items"] if x["section"] == section]
        if not items:
            continue
        lines += ["## " + section]
        for item in items:
            quantity = f" ({item['pack']})" if item["pack"] and norm(item["pack"]) not in norm(item["source_name"]) else ""
            unit = f" (${money(item['price_cad']) * Decimal('2.2046226218'):.2f}/kg)" if item["pricing"] == "per_lb" else ""
            dates = ""
            same_header_window = bool(item["starts_on"] and item["ends_on"] and
                                      item["starts_on"] in selection["period_label"] and
                                      item["ends_on"] in selection["period_label"])
            if (item["starts_on"] or item["ends_on"]) and not same_header_window:
                dates = f" Offer dates: {item['starts_on'] or 'not stated'} to {item['ends_on'] or 'not stated'}."
            elif not all_undated and not item["starts_on"] and not item["ends_on"]:
                dates = " No advertised end date."
            detail = " ".join([item["comparison"], item["assessment"], *item["terms"]]).strip()
            lines.append(f"- **{escape(item['source_name'] + quantity)} — {price_label(item)}{unit}**. {escape(detail + dates)}")
        lines.append("")
    for note in (selection["coverage_note"], selection["shortfall_note"]):
        if note:
            lines += [escape(note), ""]
    lines += [f"[Report and sources]({report_url})", ""]
    return "\n".join(lines)


@traced('body.verify')
def check_body(plan: dict, body: str, report_url: str, today: date | None = None) -> None:
    require(body == render(project(plan, today), report_url), "body_differs_from_reviewed_selection")


@traced('review.cli')
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--report-url", required=True)
    parser.add_argument("--out", type=Path, help="Create a NEW directory with public selection.json and digest.md")
    parser.add_argument("--check-body", type=Path, help="Require exact equality with the generated digest")
    args = parser.parse_args(argv)
    try:
        require(args.plan.stat().st_size <= 8_000_000, "review_plan_too_large")
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        selection = project(plan)
        body = render(selection, args.report_url)
        if args.check_body:
            require(args.check_body.read_text(encoding="utf-8") == body,
                    "body_differs_from_reviewed_selection")
        if args.out:
            # Never overwrite an earlier artifact or an already-sent edition.
            args.out.mkdir(parents=True, exist_ok=False)
            (args.out / "selection.json").write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (args.out / "digest.md").write_text(body, encoding="utf-8")
        print(json.dumps({"status": "review_passed", "selection_sha256": selection["selection_sha256"],
                          "items": len(selection["items"]), "full_coverage": not bool(selection["coverage_note"])}))
        return 0
    except Exception as exc:
        emit('review.cli', "blocked", exc=exc)
        code = safe_code(exc)
        print(json.dumps({"status": "blocked", "code": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
