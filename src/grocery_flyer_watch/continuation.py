"""Private scheduled-task checkpoint validation; NEVER a delivery authorizer.

Only serialize this JSON into the *existing private task context* (or a private
temporary file). Do not commit checkpoint values, recipient state or run history
to the public repository. All live source/publication/Gmail gates remain required.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import tomllib

VERSION = "private-flyer-continuation-v1"
BEGIN = "\n<!-- FLYER_PRIVATE_CONTINUATION_V1\n"
END = "\nEND_FLYER_PRIVATE_CONTINUATION_V1 -->\n"
STAGES = (
    "not_started", "triage", "source_inventory", "candidate_review",
    "omission_review", "quality_check", "quality_build", "assessment",
    "publication", "preflight", "authorization", "send_started", "sent_verified",
)
STATUSES = {"not_started", "incomplete", "blocked", "done"}
DELIVERIES = {
    "not_attempted", "definitely_failed_before_acceptance",
    "uncertain", "accepted_verified_in_sent",
}
PROFILE_KEYS = {
    "id", "scope", "period", "status", "last_completed", "next_stage",
    "observed_at", "evidence_ref", "source_cursor", "publication",
    "recipients", "reason",
}
ROOT_KEYS = {"format", "updated_at", "sequence", "profiles", "continuation_count"}
CURSOR_KEYS = {"source", "completed_units", "next_unit"}
PUB_KEYS = {"commit", "directory", "assessment_path"}
EMAIL_RE = re.compile(r"[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")


class CheckpointError(ValueError):
    """Fail closed, without printing private source or provider values."""


def require(ok: bool, code: str) -> None:
    if not ok:
        raise CheckpointError(code)


def timestamp(value: str) -> datetime:
    require(isinstance(value, str) and len(value) <= 40, "invalid_checkpoint_timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CheckpointError("invalid_checkpoint_timestamp") from None
    require(dt.tzinfo is not None and dt.utcoffset() is not None,
            "checkpoint_timestamp_needs_timezone")
    return dt.astimezone(timezone.utc)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def text_field(value: object, maxlen: int = 400) -> bool:
    return isinstance(value, str) and len(value) <= maxlen and not EMAIL_RE.search(value)


def validate(state: dict, registry_ids: set[str] | None = None) -> dict:
    require(isinstance(state, dict) and set(state) == ROOT_KEYS, "checkpoint_schema")
    require(state["format"] == VERSION, "checkpoint_version")
    timestamp(state["updated_at"])
    require(type(state["sequence"]) is int and state["sequence"] >= 0,
            "checkpoint_sequence")
    require(type(state["continuation_count"]) is int and
            0 <= state["continuation_count"] <= 3, "checkpoint_continuation_count")
    profiles = state["profiles"]
    require(isinstance(profiles, list) and len(profiles) <= 25, "checkpoint_profiles")
    ids: set[str] = set()
    for entry in profiles:
        require(isinstance(entry, dict) and set(entry) == PROFILE_KEYS, "checkpoint_profile_schema")
        ident = entry["id"]
        require(isinstance(ident, str) and ID_RE.fullmatch(ident) is not None and
                ident not in ids, "checkpoint_profile_identity")
        ids.add(ident)
        require(text_field(entry["scope"], 100) and
                text_field(entry["period"], 130), "checkpoint_source_scope")
        require(entry["status"] in STATUSES and entry["last_completed"] in STAGES and
                entry["next_stage"] in STAGES, "checkpoint_stage")
        require(STAGES.index(entry["next_stage"]) >= STAGES.index(entry["last_completed"]) or
                entry["next_stage"] in {"triage", "source_inventory"},
                "checkpoint_stage_order")
        require(entry["observed_at"] is None or isinstance(entry["observed_at"], str),
                "checkpoint_observed_at")
        if entry["observed_at"] is not None:
            timestamp(entry["observed_at"])
        require(entry["evidence_ref"] is None or text_field(entry["evidence_ref"], 500),
                "checkpoint_evidence_ref")
        require(text_field(entry["reason"], 230), "checkpoint_reason")
        cursor = entry["source_cursor"]
        require(isinstance(cursor, dict) and set(cursor) == CURSOR_KEYS,
                "checkpoint_cursor_schema")
        require(text_field(cursor["source"], 240) and isinstance(cursor["completed_units"], list)
                and len(cursor["completed_units"]) <= 200 and
                all(text_field(x, 90) for x in cursor["completed_units"]) and
                len(cursor["completed_units"]) == len(set(cursor["completed_units"])) and
                (cursor["next_unit"] is None or text_field(cursor["next_unit"], 90)),
                "checkpoint_cursor")
        publication = entry["publication"]
        if publication is not None:
            require(isinstance(publication, dict) and set(publication) == PUB_KEYS,
                    "checkpoint_publication_schema")
            require(isinstance(publication["commit"], str) and
                    re.fullmatch(r"[0-9a-f]{40}", publication["commit"]) is not None and
                    all(text_field(publication[k], 280)
                        for k in ("directory", "assessment_path")),
                    "checkpoint_publication")
        require(publication is not None or STAGES.index(entry["last_completed"]) <
                STAGES.index("publication"), "checkpoint_publication_missing")
        recipients = entry["recipients"]
        require(isinstance(recipients, dict) and len(recipients) <= 10 and
                all(isinstance(k, str) and ID_RE.fullmatch(k) is not None and
                    v in DELIVERIES for k, v in recipients.items()), "checkpoint_delivery_status")
        require(entry["last_completed"] != "send_started" or
                "uncertain" in recipients.values() or
                "accepted_verified_in_sent" in recipients.values(),
                "send_started_requires_uncertain_state")
    if registry_ids is not None:
        require(ids <= registry_ids, "checkpoint_unknown_profile")
    serialized = json.dumps(state, ensure_ascii=True, separators=(",", ":"))
    require(len(serialized) <= 18000, "checkpoint_too_large")
    return state


def blank(registry_ids: list[str]) -> dict:
    require(len(registry_ids) == len(set(registry_ids)) and len(registry_ids) <= 25,
            "invalid_profile_registry")
    state = {
        "format": VERSION, "updated_at": now_iso(), "sequence": 0,
        "continuation_count": 0, "profiles": [
            {
                "id": ident, "scope": "", "period": "", "status": "not_started",
                "last_completed": "not_started", "next_stage": "triage",
                "observed_at": None, "evidence_ref": None,
                "source_cursor": {"source": "", "completed_units": [], "next_unit": None},
                "publication": None, "recipients": {}, "reason": "",
            } for ident in registry_ids
        ],
    }
    return validate(state, set(registry_ids))


def registry_ids(path: Path) -> list[str]:
    profiles = tomllib.loads(path.read_text(encoding="utf-8"))["profiles"]
    ids = [p["id"] for p in profiles]
    require(all(isinstance(x, str) and ID_RE.fullmatch(x) for x in ids),
            "invalid_profile_registry")
    return ids


def embed(prompt: str, state: dict) -> str:
    validate(state)
    require(isinstance(prompt, str) and len(prompt) <= 120000, "invalid_task_prompt")
    require(prompt.count(BEGIN) <= 1 and prompt.count(END) <= 1,
            "multiple_private_checkpoints")
    require((BEGIN in prompt) == (END in prompt), "unterminated_private_checkpoint")
    clean = prompt.split(BEGIN, 1)[0] + prompt.split(END, 1)[1] if BEGIN in prompt else prompt
    payload = json.dumps(state, indent=2, ensure_ascii=True, sort_keys=True)
    candidate = clean.rstrip() + BEGIN + payload + END
    # Verify the *whole* embedded payload, not merely matching start/end markers.
    require(extract(candidate) == state, "checkpoint_embed_roundtrip_failed")
    return candidate


def extract(prompt: str) -> dict:
    require(prompt.count(BEGIN) == 1 and prompt.count(END) == 1,
            "private_checkpoint_missing_or_duplicated")
    raw = prompt.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    try:
        state = json.loads(raw)
    except (ValueError, TypeError):
        raise CheckpointError("invalid_private_checkpoint_json") from None
    return validate(state)


def verify_saved_prompt(saved_prompt: str, expected_state: dict) -> dict:
    """After a native task update, reread and compare the *entire* persisted state.

    The caller must separately verify that schedule and enabled state did not change.
    This does not authenticate source claims or authorize publication or Gmail.
    """
    validate(expected_state)
    actual = extract(saved_prompt)
    require(actual == expected_state, "checkpoint_saved_state_mismatch")
    return actual


def update(state: dict, profile_id: str, *, last_completed: str, next_stage: str,
           evidence_ref: str, reason: str, status: str = "incomplete") -> dict:
    validate(state)
    require(bool(evidence_ref) and text_field(evidence_ref, 500),
            "actual_stage_evidence_required")
    require(last_completed in STAGES and next_stage in STAGES and status in STATUSES,
            "checkpoint_stage")
    entries = [p for p in state["profiles"] if p["id"] == profile_id]
    require(len(entries) == 1, "checkpoint_unknown_profile")
    entry = entries[0]
    require(STAGES.index(last_completed) >= STAGES.index(entry["last_completed"]) or
            next_stage in {"triage", "source_inventory"}, "checkpoint_stage_regression")
    require(STAGES.index(next_stage) >= STAGES.index(last_completed) or
            next_stage in {"triage", "source_inventory"}, "checkpoint_stage_order")
    require(text_field(reason, 230), "checkpoint_reason")
    entry.update(status=status, last_completed=last_completed, next_stage=next_stage,
                 evidence_ref=evidence_ref, observed_at=now_iso(), reason=reason)
    state["sequence"] += 1
    state["updated_at"] = now_iso()
    return validate(state)


def before_send(state: dict, profile_id: str, recipient_slot: str, authorization_ref: str) -> dict:
    """Write-ahead marker MUST be persisted to task history BEFORE calling Gmail."""
    validate(state)
    require(bool(authorization_ref) and text_field(authorization_ref, 500),
            "actual_authorization_ref_required")
    entries = [p for p in state["profiles"] if p["id"] == profile_id]
    require(len(entries) == 1, "checkpoint_unknown_profile")
    entry = entries[0]
    require(entry["publication"] is not None and
            STAGES.index(entry["last_completed"]) >= STAGES.index("preflight"),
            "publication_preflight_required")
    require(recipient_slot in entry["recipients"], "unknown_recipient_slot")
    require(entry["recipients"][recipient_slot] in
            {"not_attempted", "definitely_failed_before_acceptance"},
            "recipient_requires_reconciliation")
    entry["recipients"][recipient_slot] = "uncertain"
    entry["last_completed"] = "send_started"
    entry["next_stage"] = "sent_verified"
    entry["status"] = "incomplete"
    entry["evidence_ref"] = authorization_ref
    entry["observed_at"] = now_iso()
    entry["reason"] = "write_ahead_send_started_not_yet_accepted"
    state["sequence"] += 1
    state["updated_at"] = now_iso()
    return validate(state)



def after_sent_verification(state: dict, profile_id: str, recipient_slot: str,
                            sent_evidence_ref: str) -> dict:
    """Record a real, exact-recipient Gmail Sent lookup after transport.

    The caller must have inspected the actual provider result. This merely
    checkpoints that observation; it cannot independently verify Gmail.
    """
    validate(state)
    require(bool(sent_evidence_ref) and text_field(sent_evidence_ref, 500),
            "real_sent_evidence_required")
    entries = [p for p in state["profiles"] if p["id"] == profile_id]
    require(len(entries) == 1, "checkpoint_unknown_profile")
    entry = entries[0]
    require(entry["recipients"].get(recipient_slot) == "uncertain",
            "send_started_or_uncertain_required")
    entry["recipients"][recipient_slot] = "accepted_verified_in_sent"
    entry["last_completed"] = "sent_verified"
    entry["next_stage"] = "sent_verified"
    entry["evidence_ref"] = sent_evidence_ref
    entry["observed_at"] = now_iso()
    entry["reason"] = "accepted_verified_in_sent_not_inbox"
    entry["status"] = ("done" if entry["recipients"] and
                       all(x == "accepted_verified_in_sent"
                           for x in entry["recipients"].values()) else "incomplete")
    state["sequence"] += 1
    state["updated_at"] = now_iso()
    return validate(state)


def after_preacceptance_failure(state: dict, profile_id: str,
                                recipient_slot: str, provider_evidence_ref: str) -> dict:
    """A tool/transport result MUST prove rejection happened before acceptance."""
    validate(state)
    require(bool(provider_evidence_ref) and text_field(provider_evidence_ref, 500),
            "real_provider_failure_evidence_required")
    entries = [p for p in state["profiles"] if p["id"] == profile_id]
    require(len(entries) == 1, "checkpoint_unknown_profile")
    entry = entries[0]
    require(entry["recipients"].get(recipient_slot) == "uncertain",
            "send_started_or_uncertain_required")
    entry["recipients"][recipient_slot] = "definitely_failed_before_acceptance"
    entry["reason"] = "provider_definitely_rejected_before_acceptance"
    entry["evidence_ref"] = provider_evidence_ref
    entry["observed_at"] = now_iso()
    entry["status"] = "incomplete"
    state["sequence"] += 1
    state["updated_at"] = now_iso()
    return validate(state)

def plan(state: dict, *, now: datetime | None = None) -> dict:
    """Recommendations only. NOT permission to use Gmail or publish."""
    validate(state)
    current = now or datetime.now(timezone.utc)
    entries = []
    for p in state["profiles"]:
        if p["status"] == "done":
            action, priority = "skip_handled_after_history_reconciliation", 9
        elif "uncertain" in p["recipients"].values():
            action, priority = "reconcile_actual_gmail_sent_before_retry", 0
        elif p["publication"] is not None:
            action, priority = "verify_pinned_publication_refresh_and_authorize", 1
        elif p["status"] == "blocked":
            action, priority = "investigate_specific_blocker_without_restarting_others", 8
        elif p["observed_at"] and current - timestamp(p["observed_at"]) > timedelta(hours=6):
            action, priority = "refresh_expired_source_evidence_then_resume_cursor", 3
        elif p["last_completed"] == "not_started":
            action, priority = "triage_matching_registry_baseline", 5
        else:
            action, priority = "resume_" + p["next_stage"], 2
        entries.append({"profile": p["id"], "action": action, "priority": priority,
                        "cursor": p["source_cursor"]["next_unit"]})
    entries.sort(key=lambda e: (e["priority"], e["profile"]))
    return {"status": "checkpoint_only_not_delivery_authorization",
            "continuation_count": state["continuation_count"], "next": entries}




# Research helpers are advisory only: they never approve a review or a send.
def _catalog_source(url: str | None, sources: list[dict]) -> dict | None:
    """Accept a dated URL only under an exact fixed-source host/path boundary."""
    from urllib.parse import urlsplit
    if not isinstance(url, str) or not url.startswith("https://"):
        return None
    target = urlsplit(url)
    for source in sources:
        base = source.get("url")
        if not isinstance(base, str) or not base.startswith("https://"):
            continue
        anchor = urlsplit(base)
        prefix, path = anchor.path.rstrip("/"), target.path.rstrip("/")
        if (target.scheme == anchor.scheme and target.netloc == anchor.netloc and
                (path == prefix or path.startswith(prefix + "/"))):
            return source
    return None


def source_failover(state: dict, catalog: dict, profile_id: str, *,
                    failed_url: str, attempts: int,
                    attempted_urls: list[str] | None = None,
                    reviewed_original_url: str | None = None,
                    missing_units: list[str] | None = None) -> dict:
    """Prefer real previously read original ads, then the next fixed source.

    Previous visual reads are NOT structured inventory, market proof, omission
    review or quality authorization. The caller must resolve logical pages.
    """
    validate(state)
    require(type(attempts) is int and 1 <= attempts <= 2, "source_failover_attempt_limit")
    require(isinstance(failed_url, str) and failed_url.startswith("https://") and
            text_field(failed_url, 1000), "source_failover_url")
    attempted, missing = list(attempted_urls or []), list(missing_units or [])
    require(len(attempted) <= 30 and all(text_field(x, 1000) for x in attempted) and
            len(missing) <= 100 and len(missing) == len(set(missing)) and
            all(text_field(x, 90) and x for x in missing), "source_failover_arguments")
    require(isinstance(catalog, dict) and isinstance(catalog.get("retailers"), list),
            "source_catalog_invalid")
    profile = [x for x in state["profiles"] if x["id"] == profile_id]
    retailer = [x for x in catalog["retailers"]
                if isinstance(x, dict) and x.get("id") == profile_id]
    require(len(profile) == len(retailer) == 1, "source_failover_unknown_profile")
    sources = retailer[0].get("sources")
    require(isinstance(sources, list) and bool(sources) and
            all(isinstance(x, dict) for x in sources), "source_catalog_invalid")
    original = _catalog_source(reviewed_original_url, sources)
    cursor = profile[0]["source_cursor"]
    has_visual_read = any("original-image-first-read" in unit or
                          ("original-page-" in unit and "first-read" in unit)
                          for unit in cursor["completed_units"])
    if (original and "original" in str(original.get("role", "")) and
            has_visual_read and missing):
        return {"action": "extract_missing_inventory_from_original_scans",
                "source_url": reviewed_original_url, "unresolved_units": missing,
                "coverage_complete": False, "quality_authorized": False,
                "note": "Reconcile logical pages with the real original ad; past visual reads are not an item inventory."}
    for source in sources:
        role, url = source.get("role"), source.get("url")
        if not isinstance(role, str) or not isinstance(url, str):
            continue
        if not ("original" in role or "flyer" in role or "warehouse_savings" in role):
            continue
        if any(_catalog_source(u, [source]) for u in [failed_url, *attempted]):
            continue
        return {"action": "switch_to_next_fixed_source", "source_url": url,
                "unresolved_units": missing, "coverage_complete": False,
                "quality_authorized": False,
                "note": "Inspect matching actual ad pages; fallback does not make missing units reviewed."}
    return {"action": "source_blocked_rotate_retailer", "source_url": None,
            "unresolved_units": missing, "coverage_complete": False,
            "quality_authorized": False,
            "note": "Preserve exact failed source/units and rotate to a verified viable second retailer."}


def coverage_decision(proof: dict) -> dict:
    """Count logical ad units once across mirrors and require distinct omission reads.

    Consistency-only planning: actual source facts, partial exception and quality
    still need verification by the existing unchanged production gate.
    """
    keys = {"expected_unit_ids", "inventory_reads", "omission_reads",
            "blocked_unit_ids", "edition_verified", "market_verified",
            "allow_partial", "partial_note"}
    require(isinstance(proof, dict) and set(proof) == keys, "research_coverage_schema")
    expected, first, second = (proof[k] for k in (
        "expected_unit_ids", "inventory_reads", "omission_reads"))
    blocked = proof["blocked_unit_ids"]
    require(isinstance(expected, list) and 0 < len(expected) <= 250 and
            all(isinstance(x, str) and bool(x) and text_field(x, 90) for x in expected) and
            len(expected) == len(set(expected)), "research_coverage_units")
    require(isinstance(first, dict) and isinstance(second, dict) and
            isinstance(blocked, list) and
            all(isinstance(x, str) for x in blocked), "research_coverage_reads")
    universe = set(expected)
    require(set(first) <= universe and set(second) <= set(first) and
            set(blocked) <= universe and len(blocked) == len(set(blocked)) and
            not (set(blocked) & set(first)) and
            all(isinstance(x, str) and bool(x) and text_field(x, 500)
                for x in [*first.values(), *second.values()]) and
            all(first[k] != v for k, v in second.items()), "research_coverage_reads")
    require(all(type(proof[k]) is bool for k in (
        "edition_verified", "market_verified", "allow_partial")) and
        text_field(proof["partial_note"], 500), "research_coverage_scope")
    missing = sorted(universe - set(first) - set(blocked))
    omission_pending = sorted(set(first) - set(second))
    if not proof["edition_verified"] or not proof["market_verified"]:
        action = "resolve_market_and_edition"
    elif missing:
        action = "inventory_missing_units_from_original_or_alternate"
    elif blocked and (not proof["allow_partial"] or not proof["partial_note"].strip()):
        action = "blocked_units_require_fallback_or_rotation"
    elif omission_pending:
        action = "finish_distinct_omission_pass"
    elif not first:
        action = "no_inspected_units_rotate"
    else:
        action = ("prepare_disclosed_partial_bundle_for_quality" if blocked
                  else "prepare_baseline_value_and_quality")
    ready = action in {"prepare_disclosed_partial_bundle_for_quality",
                       "prepare_baseline_value_and_quality"}
    return {"action": action, "source_units": len(expected),
            "inventory_units": len(first), "omission_units": len(second),
            "missing_units": missing, "blocked_units": sorted(blocked),
            "omission_pending": omission_pending,
            "ready_for_baseline_value": ready,
            "coverage_complete": ready and not blocked,
            "quality_authorized": False}


def rotate_retailer(state: dict, primary: str, viable_profiles: list[str]) -> dict:
    """Select one second retailer using CURRENT verified source viability."""
    validate(state)
    by_id = {p["id"]: p for p in state["profiles"]}
    require(primary in by_id and isinstance(viable_profiles, list) and
            len(viable_profiles) <= 25 and
            len(viable_profiles) == len(set(viable_profiles)) and
            all(x in by_id for x in viable_profiles), "research_rotation_arguments")
    choices = [by_id[x] for x in viable_profiles if x != primary and
               by_id[x]["status"] != "done" and
               by_id[x]["publication"] is None and
               "uncertain" not in by_id[x]["recipients"].values()]
    choices.sort(key=lambda p: (p["observed_at"] or "0000", p["id"]))
    if not choices:
        return {"action": "no_verified_viable_secondary", "primary": primary,
                "secondary": None, "deep_retailer_cap": 2,
                "quality_authorized": False}
    return {"action": "switch_to_second_retailer", "primary": primary,
            "secondary": choices[0]["id"], "deep_retailer_cap": 2,
            "quality_authorized": False,
            "note": "Keep the blocked primary cursor; work on the secondary independently."}


def outcome_metrics(state: dict) -> dict:
    """Do not count checkpoint sequence increments as completed assessments."""
    validate(state)
    published = [p for p in state["profiles"] if p["publication"] is not None]
    delivered = [p for p in published if p["status"] == "done" and
                 p["recipients"] and all(v == "accepted_verified_in_sent"
                                           for v in p["recipients"].values())]
    return {"status": "checkpoint_claims_require_external_verification",
            "checkpoint_sequence_is_not_completion": True,
            "publication_claims": len(published),
            "completed_qualified_delivery_claims": len(delivered),
            "unfinished_profiles": sum(p["status"] != "done" for p in state["profiles"]),
            "quality_authorized": False}


def private_save(path: Path, content: str) -> None:
    """Create a 0600 checkpoint file outside any Git checkout, never overwrite."""
    dest = path.absolute()
    parents = [dest.parent, *dest.parents]
    require(not any((parent / ".git").exists() for parent in parents),
            "checkpoint_must_stay_outside_public_checkout")
    require(not dest.exists(), "checkpoint_file_exists_choose_new_path")
    try:
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
    except FileExistsError:
        raise CheckpointError("checkpoint_file_exists_choose_new_path") from None

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    cmds = p.add_subparsers(dest="command", required=True)
    seed = cmds.add_parser("seed")
    seed.add_argument("--registry", required=True, type=Path)
    seed.add_argument("--out", required=True, type=Path)
    for name in ("validate", "plan", "outcomes", "before-send", "sent-verified", "preacceptance-failed"):
        c = cmds.add_parser(name)
        c.add_argument("checkpoint", type=Path)
        if name in ("before-send", "sent-verified", "preacceptance-failed"):
            c.add_argument("--profile", required=True)
            c.add_argument("--recipient-slot", required=True)
            c.add_argument("--provider-evidence-ref", required=True)
            c.add_argument("--out", required=True, type=Path)
    sf = cmds.add_parser("source-failover")
    sf.add_argument("checkpoint", type=Path)
    sf.add_argument("--catalog", required=True, type=Path)
    sf.add_argument("--profile", required=True)
    sf.add_argument("--failed-url", required=True)
    sf.add_argument("--attempts", required=True, type=int)
    sf.add_argument("--attempted-url", action="append", default=[])
    sf.add_argument("--reviewed-original-url")
    sf.add_argument("--missing-unit", action="append", default=[])
    cv = cmds.add_parser("coverage")
    cv.add_argument("proof", type=Path)
    rt = cmds.add_parser("rotate")
    rt.add_argument("checkpoint", type=Path)
    rt.add_argument("--primary", required=True)
    rt.add_argument("--viable-profile", action="append", default=[])
    ex = cmds.add_parser("extract")
    ex.add_argument("--prompt", required=True, type=Path)
    ex.add_argument("--out", required=True, type=Path)
    em = cmds.add_parser("embed")
    em.add_argument("--prompt", required=True, type=Path)
    em.add_argument("--checkpoint", required=True, type=Path)
    em.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        if args.command == "seed":
            result = blank(registry_ids(args.registry))
            private_save(args.out, json.dumps(result, indent=2) + "\n")
        elif args.command == "extract":
            result = extract(args.prompt.read_text(encoding="utf-8"))
            private_save(args.out, json.dumps(result, indent=2) + "\n")
        elif args.command == "embed":
            state = json.loads(args.checkpoint.read_text(encoding="utf-8"))
            private_save(args.out, embed(args.prompt.read_text(encoding="utf-8"), state))
            result = {"status": "private_prompt_updated_locally_not_saved_to_task"}
        elif args.command == "coverage":
            result = coverage_decision(json.loads(args.proof.read_text(encoding="utf-8")))
        else:
            state = validate(json.loads(args.checkpoint.read_text(encoding="utf-8")))
            if args.command in {"before-send", "sent-verified", "preacceptance-failed"}:
                operation = {
                    "before-send": before_send,
                    "sent-verified": after_sent_verification,
                    "preacceptance-failed": after_preacceptance_failure,
                }[args.command]
                result = operation(state, args.profile, args.recipient_slot,
                                   args.provider_evidence_ref)
                private_save(args.out, json.dumps(result, indent=2) + "\n")
            elif args.command == "plan":
                result = plan(state)
            elif args.command == "outcomes":
                result = outcome_metrics(state)
            elif args.command == "source-failover":
                result = source_failover(
                    state, json.loads(args.catalog.read_text(encoding="utf-8")),
                    args.profile, failed_url=args.failed_url, attempts=args.attempts,
                    attempted_urls=args.attempted_url,
                    reviewed_original_url=args.reviewed_original_url,
                    missing_units=args.missing_unit)
            elif args.command == "rotate":
                result = rotate_retailer(state, args.primary, args.viable_profile)
            else:
                result = {"status": "checkpoint_valid_not_delivery_authorization"}
        print(json.dumps(result))
        return 0
    except (CheckpointError, ValueError, KeyError, OSError) as exc:
        code = str(exc) if isinstance(exc, CheckpointError) else "checkpoint_read_or_format_error"
        print(json.dumps({"status": "checkpoint_blocked", "code": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

