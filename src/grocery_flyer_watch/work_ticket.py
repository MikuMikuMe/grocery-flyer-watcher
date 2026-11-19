"""Choose ONE concrete next native-run action; no browsing, publication or send.

Use freshly verified source/edition status from the existing task's source
inspection. This cannot assert source truth, qualify a bargain or authorize
Gmail. It never mutates the private checkpoint.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from . import continuation

RECORD_KEYS = {"verified_market_edition", "source_readable", "edition_start",
               "edition_end", "undated_collection", "evidence_ref"}
QUICK_STAGES = {"triage", "source_inventory", "candidate_review", "omission_review"}
ACTION = {
    "not_started": ("triage_current_source", "verified_current_edition_and_source"),
    "triage": ("triage_current_source", "verified_current_edition_and_source"),
    "source_inventory": ("resume_source_inventory", "source_verified_public_facts_chunk"),
    "candidate_review": ("resume_candidate_review", "real_baseline_and_value_assessment"),
    "omission_review": ("resume_omission_review", "distinct_source_omission_pass"),
    "quality_check": ("resume_quality_check", "actual_executable_quality_result"),
    "quality_build": ("resume_quality_build", "actual_executable_quality_build"),
    "assessment": ("resume_assessment", "real_public_assessment"),
    "publication": ("resume_publication", "create_only_immutable_publication"),
    "preflight": ("resume_preflight", "pinned_publication_preflight"),
    "authorization": ("resume_authorization", "fresh_recipient_specific_authorization"),
    "send_started": ("reconcile_sent_uncertainty", "verified_provider_sent_outcome"),
    "sent_verified": ("reconcile_sent_evidence", "recipient_specific_sent_reconciliation"),
}


class TicketError(ValueError):
    """Safe codes only; do not expose private source or task data."""


def check(value: bool, code: str) -> None:
    if not value:
        raise TicketError(code)


def _date(value: object) -> date:
    check(isinstance(value, str), "ticket_edition_dates")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise TicketError("ticket_edition_dates") from None


def _valid_sources(state: dict, availability: dict, today: date) -> list[tuple[dict, date]]:
    by_id = {p["id"]: p for p in state["profiles"]}
    check(isinstance(availability, dict) and set(availability) == set(by_id),
          "ticket_full_registry_triage_required")
    viable: list[tuple[dict, date]] = []
    for ident, entry in availability.items():
        check(isinstance(entry, dict) and set(entry) == RECORD_KEYS,
              "ticket_availability_schema")
        check(all(type(entry[x]) is bool for x in (
            "verified_market_edition", "source_readable", "undated_collection")),
            "ticket_availability_flags")
        # Validate every source reference before a branch can skip an
        # unverified edition: unknown dates do not excuse invented read proof.
        ref = entry["evidence_ref"]
        check(ref is None or continuation.text_field(ref, 500) and bool(ref),
              "ticket_source_evidence")
        check(not entry["source_readable"] or bool(ref),
              "ticket_source_evidence_required")
        start, end = entry["edition_start"], entry["edition_end"]
        check((start is None) == (end is None), "ticket_edition_dates")
        if start is not None:
            a, b = _date(start), _date(end)
            check(a <= b and (b - a).days <= 70 and
                  not entry["undated_collection"], "ticket_edition_dates")
        elif entry["undated_collection"]:
            check(ident == "staples",
                  "ticket_undated_only_staples_collections")
            b = date.max
        else:
            # Most retailers will not have a confirmed edition during quick triage.
            # Unknown dates are not evidence of a current offer, but must not
            # invalidate a real, verified source from another retailer.
            check(not entry["verified_market_edition"],
                  "ticket_verified_edition_missing_dates")
            continue
        if (entry["verified_market_edition"] and entry["source_readable"] and
                not by_id[ident]["status"] == "done" and
                today <= b and (start is None or _date(start) <= today + timedelta(days=14))):
            viable.append((by_id[ident], b))
    return viable


def choose(state: dict, availability: dict, *,
           previous_primary: str | None = None,
           previous_substantive: bool | None = None,
           now: datetime | None = None) -> dict:
    """Make a finite work ticket from actual all-profile source triage.

    A prior no-progress execution must change retailers or explicitly report
    no verified safe secondary. This is NOT a publication or email ticket.
    """
    try:
        continuation.validate(state)
    except continuation.CheckpointError:
        raise TicketError("ticket_checkpoint_invalid") from None
    current = now or datetime.now(timezone.utc)
    check(isinstance(current, datetime) and current.tzinfo is not None and
          current.utcoffset() is not None, "ticket_timezone_required")
    check(previous_primary is None and previous_substantive is None or
          (isinstance(previous_primary, str) and
           previous_primary in {p["id"] for p in state["profiles"]} and
           type(previous_substantive) is bool), "ticket_previous_run")
    today = current.astimezone(ZoneInfo("America/Toronto")).date()
    viable = _valid_sources(state, availability, today)

    base = {"kind": "private_non_authorizing_work_ticket_v1",
            "max_deep_retailers": 2, "publication_authorized": False,
            "gmail_authorized": False, "checkpoint_sequence": state["sequence"]}

    # An uncertain provider attempt is never inferred failed merely because
    # the last run was incomplete. It must be reconciled ahead of source work.
    uncertain = [p for p in state["profiles"]
                 if "uncertain" in p["recipients"].values()]
    if uncertain:
        p = sorted(uncertain, key=lambda x: x["id"])[0]
        return {**base, "primary": p["id"], "rotated_from": None,
                "action": "reconcile_sent_uncertainty",
                "next_deliverable": "verified_provider_sent_outcome",
                "last_completed": p["last_completed"], "cursor": p["source_cursor"]["next_unit"],
                "refresh_selected_source_evidence": False}

    published = [p for p in state["profiles"]
                 if p["publication"] is not None and p["status"] != "done"]
    if published:
        p = sorted(published, key=lambda x: x["id"])[0]
        return {**base, "primary": p["id"], "rotated_from": None,
                "action": "verify_pinned_assessment_and_authorize",
                "next_deliverable": "fresh_recipient_specific_authorization_or_blocker",
                "last_completed": p["last_completed"], "cursor": p["source_cursor"]["next_unit"],
                "refresh_selected_source_evidence": False}

    def source_verification_only(exclude: str) -> dict | None:
        # A failed deep read should not force another hour on the same flyer
        # when the other retailers were not yet verified. Propose a different
        # retailer's SOURCE-ONLY triage, never claim it is a viable offer.
        candidates = [p for p in state["profiles"]
                      if p["id"] != exclude and p["status"] != "done"
                      and p["publication"] is None
                      and not (availability[p["id"]]["verified_market_edition"]
                               and availability[p["id"]]["source_readable"])]
        if not candidates:
            return None
        p = min(candidates, key=lambda x: (
            x["last_completed"] != "not_started",
            x["observed_at"] is not None, x["observed_at"] or "", x["id"]))
        return {**base, "primary": p["id"], "rotated_from": exclude,
                "action": "verify_secondary_source_only",
                "next_deliverable": "actual_current_flyer_proof_or_precise_source_blocker",
                "source_verification_only": True,
                "verified_secondary": False,
                "last_completed": p["last_completed"],
                "cursor": p["source_cursor"]["next_unit"],
                "refresh_selected_source_evidence": False}

    if not viable:
        if previous_primary is not None and previous_substantive is False:
            probe = source_verification_only(previous_primary)
            if probe is not None:
                return probe
            return {**base, "primary": None, "rotated_from": previous_primary,
                    "action": "no_verified_viable_secondary",
                    "next_deliverable": "specific_source_blocker",
                    "last_completed": None, "cursor": None,
                    "refresh_selected_source_evidence": False}
        return {**base, "primary": None, "rotated_from": None,
                "action": "no_verified_viable_source",
                "next_deliverable": "specific_source_blocker",
                "last_completed": None, "cursor": None,
                "refresh_selected_source_evidence": False}

    # A current report already at quality stage is more actionable than a
    # new batch of source discovery, subject to actual unexpired source proof.
    stage_rank = {s: n for n, s in enumerate(continuation.STAGES)}
    def rank(item: tuple[dict, date]) -> tuple:
        p, end = item
        stage = p["next_stage"]
        quality = stage_rank[stage] >= stage_rank["quality_check"]
        # Quality first; then nearest expiration; then most advanced stage;
        # then oldest substantive source observation for fair rotation.
        return (0 if quality else 1, end.toordinal(),
                -stage_rank[stage], p["observed_at"] or "", p["id"])

    ordered = sorted(viable, key=rank)
    rotated_from = None
    if previous_primary is not None and previous_substantive is False:
        alternatives = [item for item in ordered if item[0]["id"] != previous_primary]
        if not alternatives:
            probe = source_verification_only(previous_primary)
            if probe is not None:
                return probe
            return {**base, "primary": None, "rotated_from": previous_primary,
                    "action": "no_verified_viable_secondary",
                    "next_deliverable": "precise_blocker_and_different_safe_source_action",
                    "last_completed": None, "cursor": None,
                    "refresh_selected_source_evidence": False}
        ordered = alternatives
        rotated_from = previous_primary

    p = ordered[0][0]
    stage = p["next_stage"]
    action, deliverable = ACTION.get(stage, ("resume_" + stage, "verified_stage_result"))
    expired_evidence = (p["observed_at"] is None or
                        current.astimezone(timezone.utc) -
                        continuation.timestamp(p["observed_at"]) > timedelta(hours=6))
    return {**base, "primary": p["id"], "rotated_from": rotated_from,
            "action": action, "next_deliverable": deliverable,
            "last_completed": p["last_completed"],
            "cursor": p["source_cursor"]["next_unit"],
            "refresh_selected_source_evidence": expired_evidence}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--availability", required=True, type=Path)
    parser.add_argument("--previous-primary")
    parser.add_argument("--previous-no-progress", action="store_true")
    args = parser.parse_args(argv)
    try:
        state = json.loads(args.checkpoint.read_text(encoding="utf-8"))
        avail = json.loads(args.availability.read_text(encoding="utf-8"))
        if args.previous_no_progress and not args.previous_primary:
            raise TicketError("ticket_previous_run")
        result = choose(state, avail, previous_primary=args.previous_primary,
                        previous_substantive=(not args.previous_no_progress
                                              if args.previous_primary else None))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (TicketError, OSError, ValueError) as exc:
        code = str(exc) if isinstance(exc, TicketError) else "ticket_input_error"
        print(json.dumps({"status": "ticket_blocked", "code": code,
                          "gmail_authorized": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
