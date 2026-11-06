"""GitHub public assessment history + Gmail private delivery evidence; no database.

This single-worker connector adapter retains the executable quality/publication gates.
Evidence objects describe ACTUAL connector operations; this code cannot authenticate
an invented tool reference, lock Gmail, or make GitHub and Gmail one transaction.
Never publish a lookup, recipient roster, authorization or private review bundle.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

from . import review
from .quality_gate import check, read_json, timestamp
from .quality_cli import private_write
from .reviewed_delivery import preflight, fetch_public, connector_publication_fetcher, recipient_address
from .runner import load_config


def _ref(value: object, code: str) -> None:
    review.require(isinstance(value, str) and bool(value.strip()), code)


def _fresh(value: str, now: datetime, code: str) -> None:
    review.require(timedelta(0) <= now - timestamp(value) <= timedelta(minutes=10), code)


def assessment(bundle: dict, profile: dict, *, assessed_at: str | None = None,
               now: datetime | None = None) -> dict:
    """Public offer-review decision, not a delivery log. Generate only after real review."""
    now = now or datetime.now(timezone.utc)
    approved = check(bundle, profile, now=now)
    stamp = timestamp(assessed_at) if assessed_at else now
    review.require(stamp <= now, 'assessment_timestamp_in_future')
    a = bundle['audit']
    return {
        'format': 'public-flyer-assessment-v1', 'decision': 'qualified',
        'event_id': approved.event_id, 'retailer': profile['retailer'], 'market': profile['market'],
        'source_scope': a['source_scope'], 'change_kind': approved.kind,
        'starts_on': a['edition']['starts_on'], 'ends_on': a['edition']['ends_on'],
        'source_sha256': a['source_sha256'], 'baseline_source_sha256': a['baseline']['source_sha256'],
        'selection_sha256': approved.selection['selection_sha256'],
        'assessed_at': stamp.isoformat(),
    }


def assessment_bytes(record: dict) -> bytes:
    return (json.dumps(record, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def authorize(bundle: dict, profile: dict, publication: dict, record: dict,
              record_proof: dict, lookup: dict, context: dict, body: str, *,
              now: datetime | None = None, fetcher=fetch_public) -> dict:
    """Validate one prospective Gmail send without requiring a durable local journal.

    The caller serializes runs, reads REAL GitHub/Gmail/task history, and invokes Gmail
    only once for the returned private authorization. A missing Sent match alone never
    establishes pending work. Known ambiguity blocks until separately reconciled.
    """
    approved, outgoing, _ = preflight(bundle, profile, publication, body=body, now=now, fetcher=fetcher)
    clock = now or datetime.now(timezone.utc)
    expected = assessment(bundle, profile, assessed_at=record.get('assessed_at'), now=clock)
    review.require(record == expected, 'assessment_mismatch_or_unqualified')
    # Both the shopping output and its immutable event-level decision must be public.
    review.keys(record_proof, {'repository', 'commit', 'path', 'checked_at', 'evidence_ref', 'sha256'},
                'assessment_read_proof_schema')
    review.require(record_proof['repository'] == publication['repository'] and
                   record_proof['commit'] == publication['commit'] and
                   record_proof['path'] == f"state/assessments/{approved.event_id}.json",
                   'assessment_publication_scope_mismatch')
    _fresh(record_proof['checked_at'], clock, 'assessment_read_stale')
    _ref(record_proof['evidence_ref'], 'actual_pinned_assessment_read_required')
    review.require(record_proof['sha256'] == hashlib.sha256(assessment_bytes(record)).hexdigest(),
                   'assessment_read_hash_mismatch')
    # These fields are PRIVATE. Read actual task/recipient enrollment and attempt history.
    review.keys(context, {'recipient', 'authorized_recipients', 'eligible_since', 'eligibility_ref',
        'history_ref', 'history_checked_at', 'serial_execution', 'prior_attempt', 'attempt_ref'},
        'private_delivery_context_schema')
    recipient = recipient_address(context['recipient'])
    review.require(isinstance(context['authorized_recipients'], list), 'authorized_roster_required')
    roster = [recipient_address(r) for r in context['authorized_recipients']]
    review.require(roster and len(roster) == len(set(roster)) and recipient in roster,
                   'recipient_not_in_private_configuration')
    _ref(context['eligibility_ref'], 'actual_recipient_eligibility_evidence_required')
    _ref(context['history_ref'], 'actual_campaign_history_required')
    _fresh(context['history_checked_at'], clock, 'campaign_history_check_stale')
    review.require(context['serial_execution'] is True, 'overlapping_workers_not_supported')
    review.require(context['prior_attempt'] in {'not_attempted', 'definitely_failed', 'uncertain', 'unknown'},
                   'attempt_history_status_required')
    _ref(context['attempt_ref'], 'actual_attempt_history_required')
    review.keys(lookup, {'recipient', 'event_id', 'checked_at', 'already_sent', 'evidence_ref',
                         'older_editions_checked', 'equivalent_offers_checked'}, 'sent_lookup_schema')
    review.require(recipient_address(lookup['recipient']) == recipient and
                   lookup['event_id'] == approved.event_id, 'sent_lookup_scope_mismatch')
    _fresh(lookup['checked_at'], clock, 'sent_lookup_stale')
    _ref(lookup['evidence_ref'], 'actual_sent_lookup_required')
    review.require(type(lookup['already_sent']) is bool and lookup['older_editions_checked'] is True and
                   lookup['equivalent_offers_checked'] is True, 'complete_sent_lookup_required')
    if lookup['already_sent']:
        return {'status': 'already_handled', 'event_id': approved.event_id}
    if timestamp(context['eligible_since']) > timestamp(record['assessed_at']):
        return {'status': 'not_eligible_no_backfill', 'event_id': approved.event_id}
    review.require(context['prior_attempt'] in {'not_attempted', 'definitely_failed'},
                   'uncertain_attempt_requires_provider_reconciliation')
    # Recheck after publication/history work. No report rewrite or recipient data in subject.
    check(bundle, profile, now=now)
    return {'status': 'authorized', 'mode': 'github-gmail', 'event_id': approved.event_id,
            'recipient': recipient, 'expires_at': (clock + timedelta(minutes=5)).isoformat(),
            'subject': f"{profile['retailer']} | {approved.selection['period_label']} | {approved.event_id[:16]}",
            'body_sha256': hashlib.sha256(outgoing.encode()).hexdigest()}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('assessment', 'authorize'):
        cmd = sub.add_parser(name)
        cmd.add_argument('bundle', type=Path)
        cmd.add_argument('--config', required=True, type=Path)
        if name == 'assessment':
            cmd.add_argument('--out', required=True, type=Path, help='NEW public assessment JSON; never overwrite an existing event')
        else:
            cmd.add_argument('--publication', required=True, type=Path)
            cmd.add_argument('--record', required=True, type=Path)
            cmd.add_argument('--record-proof', required=True, type=Path)
            cmd.add_argument('--sent-lookup', required=True, type=Path)
            cmd.add_argument('--context', required=True, type=Path)
            cmd.add_argument('--check-body', required=True, type=Path)
            cmd.add_argument('--authorization-out', required=True, type=Path)
            cmd.add_argument('--published-copy', type=Path)
            cmd.add_argument('--publication-proof', type=Path)
    args = p.parse_args(argv)
    try:
        bundle, profile = read_json(args.bundle), load_config(args.config)
        if args.command == 'assessment':
            record = assessment(bundle, profile)
            # Contains only allowlisted PUBLIC review facts, no message or recipient metadata.
            with args.out.open('xb') as stream:
                stream.write(assessment_bytes(record))
            result = {'status': 'assessment_built_not_published', 'event_id': record['event_id'],
                      'repository_path': f"state/assessments/{record['event_id']}.json"}
        else:
            publication = read_json(args.publication)
            review.require(bool(args.published_copy) == bool(args.publication_proof), 'both_connector_copy_and_proof_required')
            fetcher = (connector_publication_fetcher(args.published_copy, read_json(args.publication_proof), publication)
                       if args.published_copy else fetch_public)
            result = authorize(bundle, profile, publication, read_json(args.record), read_json(args.record_proof),
                read_json(args.sent_lookup), read_json(args.context), args.check_body.read_text(encoding='utf-8'), fetcher=fetcher)
            # Private ticket is never printed to logs or committed. No database is created.
            private_write(args.authorization_out, json.dumps(result, indent=2) + '\n')
            result = {'status': result['status'], 'event_id': result['event_id']}
        print(json.dumps(result))
        return 0
    except Exception as exc:
        code = str(exc) if isinstance(exc, review.ReviewError) else type(exc).__name__
        print(json.dumps({'status': 'blocked', 'code': code}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
