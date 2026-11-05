"""Strict live-send gate layered on the existing offline review module.

No browsing, mail or state mutation occurs here. Evidence is supplied by a collector;
this module verifies consistency and required provenance, not the truth of a website.
The PRIVATE bundle is never a public artifact. Use artifacts() for the allowlisted output.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

from . import review

FACTS = ("source_name", "price_cad", "price_kind", "pricing", "pack", "starts_on",
         "ends_on", "terms", "channel")
MATERIAL = ("promotion_id", "source_name", "price_cad", "pricing", "pack",
            "starts_on", "ends_on", "terms")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
MAX_AGE = timedelta(hours=6)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path: str | Path) -> dict:
    """Reject oversized files, duplicate keys, non-finite numbers and non-object roots."""
    p = Path(path)
    review.require(p.is_file() and p.stat().st_size <= 8_000_000, "input_missing_or_too_large")
    def pairs(items):
        result = {}
        for key, value in items:
            review.require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def constant(_):
        raise review.ReviewError("nonfinite_json")
    try:
        result = json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                            parse_constant=constant)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise review.ReviewError("invalid_json") from None
    review.require(isinstance(result, dict), "json_object_required")
    return result


def timestamp(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        review.require(result.tzinfo is not None, "timezone_required")
        return result.astimezone(timezone.utc)
    except (AttributeError, ValueError, TypeError):
        raise review.ReviewError("invalid_timestamp") from None


def fresh(value: Any, now: datetime, code: str = "stale_source_evidence") -> None:
    age = now - timestamp(value)
    review.require(-timedelta(minutes=2) <= age <= MAX_AGE, code)


def _hash(value: Any, code: str) -> None:
    review.require(isinstance(value, str) and SHA256.fullmatch(value) is not None, code)


def _strings(value: Any, code: str) -> list[str]:
    review.require(isinstance(value, list) and all(isinstance(x, str) and x.strip()
                   for x in value) and len(value) == len(set(value)), code)
    return value


def _private_note(value: Any, code: str) -> None:
    # Reasons stay private, but must exist. Do not echo them into an exception.
    review.require(isinstance(value, str) and bool(value.strip()) and len(value) <= 20_000, code)


def material(offer: dict) -> dict:
    """Advertising identity: no ranking, layout, source URL, observation time or stock."""
    result = {k: offer[k] for k in MATERIAL}
    result["price_cad"] = str(review.money(result["price_cad"]).normalize())
    for field in ("promotion_id", "source_name", "pack"):
        result[field] = review.norm(result[field])
    result["terms"] = sorted(review.norm(term) for term in result["terms"])
    return result


def scope_key(retailer: str, market: str, source_scope: str) -> str:
    return digest([review.norm(retailer), review.norm(market), source_scope])


def edition_key(retailer: str, market: str, source_scope: str,
                starts_on: str | None, ends_on: str | None) -> str:
    return digest([scope_key(retailer, market, source_scope), starts_on, ends_on])


def review_binding(bundle: dict) -> str:
    """Compute BEFORE the real second pass; do not recompute to rubber-stamp edits."""
    audit = {k: v for k, v in bundle["audit"].items() if k != "reviewed_bundle_sha256"}
    return digest({"plan": bundle["plan"], "audit": audit})


def _check_price_binding(candidate: dict, excerpt: str) -> None:
    review.text(excerpt, "cash_price_excerpt_missing")
    review.require(review.norm(excerpt) in review.norm(candidate["source_quote"]),
                   "price_excerpt_not_in_source")
    cash = review.money(candidate["price_cad"])
    review.require(review.contains_amount(excerpt, cash), "cash_price_not_in_bound_excerpt")
    # The SAME amount must have the asserted per-weight unit next to it. Merely finding
    # a different per-lb price elsewhere in the source is not sufficient.
    if candidate["pricing"] in {"per_lb", "per_kg"}:
        unit = "lb" if candidate["pricing"] == "per_lb" else "kg"
        matches = re.finditer(r"\$\s*(\d+(?:\.\d{1,2})?)\s*(?:/|per\s+)" + unit + r"\b", excerpt, re.I)
        review.require(any(Decimal(m.group(1)) == cash for m in matches),
                       "price_and_unit_not_bound_together")
    amount = re.escape(f"{cash:.2f}")
    review.require(not re.search(r"(?:regular|reg\.?|was|save|saving|savings)\s*\$\s*" + amount + r"\b",
                                 excerpt, re.I), "regular_or_saving_price_not_checkout")


def _assert_public_text(selection: dict, forbidden: list[str]) -> None:
    raw = canonical(selection).decode("utf-8")
    review.require(not review.CONTACT.search(raw) and not review.SECRET.search(raw),
                   "private_data_in_public_output")
    folded = review.norm(raw)
    for phrase in forbidden:
        review.require(review.norm(phrase) not in folded, "private_phrase_in_public_output")
    # A second, explicit human/agent privacy review is still needed for non-pattern data.
    for item in selection["items"]:
        prose = item["assessment"]
        # Numeric/technical claims belong in evidenced facts/structured comparisons,
        # not an unconstrained verdict such as 'boneless, 50% cheaper'.
        review.require(not re.search(r"\d|\$|%|\b(boneless|bone-in|skinless|skin-on|cheaper|lowest|save|saves)\b",
                                      prose, re.I), "factual_claim_in_unbound_assessment")


@dataclass(frozen=True)
class Approved:
    # Instances are produced by check(). Public APIs recheck rather than trusting a
    # caller-created instance. Python itself is not a hostile-plugin sandbox.
    selection: dict
    event_id: str
    scope_id: str
    edition_id: str
    kind: str
    trigger_fingerprints: tuple[str, ...]
    binding: str


def check(bundle: dict, profile: dict, *, now: datetime | None = None) -> Approved:
    now = now or datetime.now(timezone.utc)
    review.require(now.tzinfo is not None, "timezone_required")
    now = now.astimezone(timezone.utc)
    review.keys(bundle, {"format", "plan", "audit"}, "bundle_schema")
    review.require(bundle["format"] == "quality-bundle-v1", "bundle_version")
    plan, audit = bundle["plan"], bundle["audit"]
    for field in ("retailer", "market", "timezone"):
        review.require(plan.get(field) == profile.get(field), "profile_scope_mismatch")
    today = now.astimezone(ZoneInfo(profile["timezone"])).date()
    review.validate(plan, today)
    review.keys(audit, {"source_scope", "source_kind", "edition", "baseline", "trigger_ids",
        "source_sha256", "page_proofs", "fact_proofs", "partial_exception", "privacy_reviewed",
        "forbidden_phrases", "reviewed_bundle_sha256"}, "audit_schema")
    review.require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", audit["source_scope"]) is not None,
                   "invalid_source_scope")
    review.require(audit["source_kind"] in {"flyer", "collection", "warehouse"}, "source_kind")
    _hash(audit["source_sha256"], "source_content_hash_required")
    review.require(audit["reviewed_bundle_sha256"] == review_binding(bundle),
                   "bundle_changed_after_second_review")
    review.require(audit["privacy_reviewed"] is True, "public_privacy_review_missing")
    forbidden = _strings(audit["forbidden_phrases"], "forbidden_phrases_schema")

    edition = audit["edition"]
    review.keys(edition, {"starts_on", "ends_on"}, "edition_schema")
    if audit["source_kind"] == "collection":
        review.require(edition == {"starts_on": None, "ends_on": None}, "invented_collection_dates")
        review.require(plan["period_label"] == "Verified collection offers", "collection_period_label")
    else:
        start, end = review.iso(edition["starts_on"]), review.iso(edition["ends_on"])
        review.require(start <= end and end >= today and start <= today + timedelta(days=14),
                       "invalid_or_expired_edition")
        review.require(plan["period_label"] == f"{start.isoformat()} to {end.isoformat()}",
                       "header_dates_do_not_match_edition")

    units = {u["id"]: u for u in plan["coverage"]["units"]}
    candidates = {c["id"]: c for c in plan["candidates"]}
    review.require(isinstance(audit["page_proofs"], list), "page_proofs_missing")
    pages = {}
    roles = set()
    for p in audit["page_proofs"]:
        review.keys(p, {"unit_id", "role", "departments", "lead_ids", "content_sha256",
                        "observed_at", "first_read_ref", "second_read_ref"}, "page_proof_schema")
        uid = p["unit_id"]
        review.require(uid in units and uid not in pages, "page_proof_mismatch")
        review.require(p["role"] in {"front", "back", "front_back", "content", "grid"}, "page_role")
        roles.add(p["role"])
        departments = _strings(p["departments"], "departments_missing")
        leads = _strings(p["lead_ids"], "department_leads_missing")
        _private_note(p["first_read_ref"], "first_read_missing")
        _private_note(p["second_read_ref"], "second_source_read_missing")
        review.require(p["first_read_ref"] != p["second_read_ref"], "second_pass_reused_first_read")
        fresh(p["observed_at"], now)
        if units[uid]["status"] == "reviewed":
            _hash(p["content_sha256"], "page_content_hash_required")
            for cid in units[uid]["candidate_ids"]:
                review.require(candidates[cid]["department"] in departments, "department_not_accounted_for")
            for cid in leads:
                review.require(cid in units[uid]["candidate_ids"] and candidates[cid]["prominent"],
                               "unassessed_department_lead")
        else:
            review.require(p["content_sha256"] is None and not leads, "blocked_page_invented_content")
            review.require(p["role"] not in {"front", "back", "front_back"}, "critical_page_unavailable")
        pages[uid] = p
    review.require(set(pages) == set(units), "source_page_proof_missing")
    if audit["source_kind"] == "flyer":
        review.require("front_back" in roles or {"front", "back"} <= roles, "front_or_back_not_accounted_for")

    partial = not plan["coverage"]["inventory_complete"] or any(u["status"] == "blocked" for u in units.values())
    exc = audit["partial_exception"]
    if partial:
        review.keys(exc, {"alternate_sources", "reason"}, "partial_exception_missing")
        refs = _strings(exc["alternate_sources"], "alternate_sources_missing")
        review.require(len(refs) >= 2, "retry_alternate_sources_before_partial")
        for ref in refs:
            review.url(ref)
        _private_note(exc["reason"], "partial_exception_reason_missing")
    else:
        review.require(exc is None, "spurious_partial_exception")

    facts = audit["fact_proofs"]
    review.require(isinstance(facts, dict) and set(facts) == set(plan["selected_ids"]),
                   "selected_fact_evidence_missing")
    for cid in plan["selected_ids"]:
        c, proof = candidates[cid], facts[cid]
        review.keys(proof, {"facts", "source_url", "read_ref", "observed_at", "price_excerpt",
                           "terms_excerpt", "validity_excerpt", "channel_excerpt", "local_scope_verified",
                           "comparison_window"}, "fact_proof_schema")
        review.keys(proof["facts"], set(FACTS), "source_facts_schema")
        review.require(proof["facts"] == {k: c[k] for k in FACTS}, "claim_differs_from_source_facts")
        review.url(proof["source_url"])
        review.require(proof["source_url"] == c["source_url"], "selected_source_mismatch")
        _private_note(proof["read_ref"], "item_evidence_ref_missing")
        fresh(proof["observed_at"], now)
        _check_price_binding(c, proof["price_excerpt"])
        for field in ("terms_excerpt", "validity_excerpt", "channel_excerpt"):
            review.text(proof[field], "item_terms_or_channel_evidence_missing")
        for term in c["terms"]:
            review.require(review.norm(term) in review.norm(proof["terms_excerpt"]),
                           "condition_not_in_evidence")
        review.require(type(proof["local_scope_verified"]) is bool, "local_scope_not_assessed")
        if c["channel"] in {"in_store", "pickup"}:
            review.require(proof["local_scope_verified"], "local_purchase_claim_not_verified")
        if audit["source_kind"] != "collection":
            review.require(c["starts_on"] is not None and c["ends_on"] is not None,
                           "dated_flyer_item_dates_required")
            review.require(edition["starts_on"] <= c["starts_on"] <= c["ends_on"] <= edition["ends_on"],
                           "item_dates_outside_edition")
        if c["comparison"]:
            w = proof["comparison_window"]
            review.keys(w, {"starts_on", "ends_on", "verified_on", "evidence_ref"}, "comparison_window_missing")
            a, b = review.iso(w["starts_on"]), review.iso(w["ends_on"])
            review.require(review.iso(w["verified_on"]) == today and a <= b and b >= today,
                           "expired_or_stale_comparison")
            _private_note(w["evidence_ref"], "comparison_validity_evidence_missing")
            if c["starts_on"] and c["ends_on"]:
                review.require(a <= max(today, review.iso(c["starts_on"]))
                               and b >= review.iso(c["ends_on"]), "comparison_period_not_equivalent")
        else:
            review.require(proof["comparison_window"] is None, "unexpected_comparison_evidence")

    baseline = audit["baseline"]
    review.keys(baseline, {"retailer", "market", "source_scope", "starts_on", "ends_on",
                          "source_sha256", "inventory_complete", "offers", "reference"}, "baseline_schema")
    for field in ("retailer", "market"):
        review.require(baseline[field] == plan[field], "baseline_wrong_market_or_retailer")
    review.require(baseline["source_scope"] == audit["source_scope"], "baseline_wrong_source")
    review.require(baseline["reference"] == plan["change"]["baseline_ref"], "baseline_reference_mismatch")
    _hash(baseline["source_sha256"], "baseline_content_hash_required")
    review.require(type(baseline["inventory_complete"]) is bool, "baseline_coverage_missing")
    review.require(audit["source_sha256"] != baseline["source_sha256"], "no_source_content_change")
    scope = scope_key(plan["retailer"], plan["market"], audit["source_scope"])
    ed_key = edition_key(plan["retailer"], plan["market"], audit["source_scope"], **edition)
    kind = plan["change"]["kind"]
    triggers = _strings(audit["trigger_ids"], "change_trigger_ids")
    trigger_fingerprints = []
    if kind == "new_edition":
        review.require(audit["source_kind"] != "collection", "undated_collection_not_new_edition")
        old_start, old_end = review.iso(baseline["starts_on"]), review.iso(baseline["ends_on"])
        review.require(old_start <= old_end and review.iso(edition["starts_on"]) > old_start,
                       "edition_not_newer_than_baseline")
        review.require(not triggers, "new_edition_uses_period_not_shortlist_identity")
        event = digest(["new_edition", ed_key])
    else:
        review.require(edition == {k: baseline[k] for k in ("starts_on", "ends_on")},
                       "material_change_cannot_change_edition")
        review.require(triggers and set(triggers) <= set(candidates), "material_change_needs_known_triggers")
        review.require(isinstance(baseline["offers"], list), "baseline_offer_inventory_missing")
        prior = {}
        for offer in baseline["offers"]:
            review.keys(offer, set(MATERIAL), "baseline_offer_schema")
            oid = review.norm(offer["promotion_id"])
            review.require(oid not in prior, "duplicate_baseline_offer")
            prior[oid] = material(offer)
        changes = []
        useful_trigger = False
        for cid in triggers:
            c = candidates[cid]
            after = material(c)
            before = prior.get(after["promotion_id"])
            review.require(before is not None or baseline["inventory_complete"],
                           "new_to_partial_coverage_is_not_new_offer")
            review.require(before != after, "reorder_restock_or_editorial_not_material")
            changes.append([after["promotion_id"], before, after])
            trigger_fingerprints.append(digest([review.norm(plan["retailer"]), review.norm(plan["market"]), after]))
            if cid in plan["selected_ids"] and c["priority"] >= 3 and c["section"] != review.SECTIONS[2]:
                useful_trigger = True
        review.require(useful_trigger, "changed_offer_has_no_useful_selected_purchase")
        event = digest(["material_offer_change", scope, sorted(changes, key=lambda x: x[0])])
    selection = review.project(plan, today)
    _assert_public_text(selection, forbidden)
    return Approved(selection, event, scope, ed_key, kind, tuple(sorted(trigger_fingerprints)),
                    audit["reviewed_bundle_sha256"])


def unit_cost(item: dict) -> str:
    """Calculate from explicitly verified pack text only; never guess a missing size."""
    price = review.money(item['price_cad'])
    if item['pricing'] == 'per_lb':
        return f"${price * Decimal('2.2046226218'):.2f}/kg"
    if item['pricing'] != 'package':
        return ''
    pack = item['pack'].strip().casefold()
    mass = re.fullmatch(r"(?:(\d+)\s*[x×]\s*)?(\d+(?:\.\d+)?)\s*(kg|g|ml|l)", pack)
    if mass:
        count = Decimal(mass.group(1) or '1')
        quantity = count * Decimal(mass.group(2))
        unit = mass.group(3)
        if unit in {'g', 'ml'}:
            quantity /= 1000
        review.require(quantity > 0, 'invalid_pack_quantity')
        value = (price / quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return f"${value:.2f}/{'kg' if unit in {'g','kg'} else 'L'}"
    count = re.fullmatch(r"(\d+)\s*(?:-?count|-?pack|pieces|sheets)", pack)
    if count:
        quantity = Decimal(count.group(1))
        review.require(quantity > 0, 'invalid_pack_quantity')
        value = (price / quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return f"${value:.2f} each"
    return ''


def shopping_body(selection: dict) -> str:
    """Canonical shared shopping section; email adds a commit-pinned link AFTER publication."""
    esc = review.escape
    lines = [f"# {esc(selection['retailer'])} | {esc(selection['period_label'])}", '']
    if all(not x['starts_on'] and not x['ends_on'] for x in selection['items']):
        lines += ['No advertised end date.', '']
    for section in review.SECTIONS:
        chosen = [i for i in selection['items'] if i['section'] == section]
        if not chosen:
            continue
        lines.append('## ' + section)
        for item in chosen:
            name = item['source_name']
            if item['pack'] and review.norm(item['pack']) not in review.norm(name):
                name += f" ({item['pack']})"
            cost = unit_cost(item)
            price = review.price_label(item) + (f" ({cost})" if cost else '')
            detail = ' '.join([item['comparison'], item['assessment'], *item['terms']]).strip()
            same = bool(item['starts_on'] and item['ends_on'] and
                        item['starts_on'] in selection['period_label'] and
                        item['ends_on'] in selection['period_label'])
            if (item['starts_on'] or item['ends_on']) and not same:
                detail += f" Offer dates: {item['starts_on'] or 'not stated'} to {item['ends_on'] or 'not stated'}."
            elif not item['ends_on'] and selection['period_label'] != 'Verified collection offers':
                detail += ' No advertised end date.'
            lines.append(f"- **{esc(name)} — {price}**. {esc(detail)}")
        lines.append('')
    for note in (selection['coverage_note'], selection['shortfall_note']):
        if note:
            lines += [esc(note), '']
    return '\n'.join(lines).rstrip() + '\n'


def artifacts(approved: Approved) -> dict[str, bytes]:
    selection = approved.selection
    sources = sorted({x["source_url"] for x in selection["items"]} |
                     {x["comparison_source"] for x in selection["items"] if x["comparison_source"]})
    report = shopping_body(selection) + "\n## Sources\n" + "".join(f"- {s}\n" for s in sources)
    return {"selection.json": json.dumps(selection, ensure_ascii=False, indent=2,
                                        allow_nan=False).encode() + b"\n",
            "report.md": report.encode()}


def verify_artifacts(approved: Approved, directory: str | Path) -> None:
    for name, content in artifacts(approved).items():
        p = Path(directory) / name
        review.require(p.is_file() and not p.is_symlink() and p.read_bytes() == content,
                       "public_artifact_differs_from_reviewed_selection")


def write_artifacts(approved: Approved, directory: str | Path) -> None:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    for name, content in artifacts(approved).items():
        (root / name).write_bytes(content)
