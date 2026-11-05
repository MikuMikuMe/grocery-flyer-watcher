"""Operational CLI for reviewed output, publication checks and guarded delivery.

No command installs/resumes a schedule. `build` is offline; `preflight` reads public
GitHub only. Actual SMTP requires the explicit `send --send` command. All mutable
review, authorization and recipient state belongs OUTSIDE the public checkout.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from . import review
from .core import read_snapshot
from .runner import load_config
from .quality_gate import check, read_json, review_binding, verify_artifacts, write_artifacts
from .reviewed_delivery import (Journal, authorize_external, preflight, private_path,
                                recipient_address, send, connector_publication_fetcher, fetch_public)


def private_write(path: str | Path, content: str) -> None:
    p = private_path(path)
    fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='grocery-flyer-watch quality', description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    bind = commands.add_parser('binding', help='Print the record hash BEFORE an actual second-source review')
    bind.add_argument('bundle', type=Path)
    for name in ('check', 'build', 'preflight', 'authorize', 'send'):
        cmd = commands.add_parser(name)
        cmd.add_argument('bundle', type=Path)
        cmd.add_argument('--config', required=True, type=Path)
        if name == 'build':
            cmd.add_argument('--out', required=True, type=Path, help='Public output ROOT; hash subdirectory is created')
        if name in ('preflight', 'authorize', 'send'):
            cmd.add_argument('--publication', required=True, type=Path)
            cmd.add_argument('--published-copy', type=Path, help='Actual connector-fetched public copies when Python has no network')
            cmd.add_argument('--publication-proof', type=Path, help='PRIVATE proof of pinned-commit connector reads')
        if name == 'preflight':
            cmd.add_argument('--body-out', type=Path, help='New PRIVATE file for canonical email text')
            cmd.add_argument('--check-body', type=Path)
        if name in ('authorize', 'send'):
            cmd.add_argument('--journal', required=True, type=Path)
        if name == 'authorize':
            cmd.add_argument('--sent-lookup', required=True, type=Path)
            cmd.add_argument('--check-body', required=True, type=Path)
            cmd.add_argument('--authorization-out', required=True, type=Path)
            cmd.add_argument('--recipient-env', default='FLYER_RECIPIENT')
            cmd.add_argument('--recipients-env', default='FLYER_MAIL_TO', help='Full current PRIVATE authorized list; prevents old-event backfills')
        if name == 'send':
            cmd.add_argument('--recipient-env', default='FLYER_MAIL_TO')
            cmd.add_argument('--send', action='store_true', help='Required to enable actual SMTP; omitted means preflight only')
    seed = commands.add_parser('seed', help='Import a handled baseline, silently; never sends')
    seed.add_argument('--config', required=True, type=Path)
    seed.add_argument('--journal', required=True, type=Path)
    seed.add_argument('--source-scope', required=True)
    group = seed.add_mutually_exclusive_group(required=True)
    group.add_argument('--snapshot', type=Path, help='Previously handled dated legacy snapshot')
    group.add_argument('--collection-history', type=Path, help='Existing inspected source ledger; not an empty placeholder')
    ack = commands.add_parser('ack', help='Record an ACTUAL connected-provider result, privately')
    ack.add_argument('--journal', required=True, type=Path)
    ack.add_argument('--authorization', required=True, type=Path)
    ack.add_argument('--outcome', required=True, choices=['sent', 'failed', 'uncertain'])
    ack.add_argument('--receipt', required=True, type=Path, help='Private JSON with evidence_ref from actual tool result')
    resolve = commands.add_parser('reconcile', help='Resolve ambiguous delivery using an actual fresh provider lookup')
    resolve.add_argument('--journal', required=True, type=Path)
    resolve.add_argument('--lookup', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'binding':
            result = {'status': 'hash_only_not_approval', 'reviewed_bundle_sha256': review_binding(read_json(args.bundle))}
        elif args.command == 'seed':
            profile = load_config(args.config)
            if args.snapshot:
                f = read_snapshot(args.snapshot)['flyer']
                review.require(all(f[k] == profile[k] for k in ('retailer', 'market')), 'seed_profile_mismatch')
                start, end = f['starts_on'], f['ends_on']
            else:
                review.require(args.collection_history.is_file() and args.collection_history.stat().st_size > 0,
                               'existing_collection_history_required')
                start = end = None
            with Journal(args.journal) as journal:
                journal.seed(profile['retailer'], profile['market'], args.source_scope, start, end)
            result = {'status': 'history_imported_no_delivery'}
        elif args.command == 'ack':
            auth, receipt = read_json(args.authorization), read_json(args.receipt)
            review.require(auth.get('status') == 'authorized', 'authorization_required')
            review.keys(receipt, {'evidence_ref'}, 'actual_delivery_receipt_required')
            review.require(isinstance(receipt['evidence_ref'], str) and receipt['evidence_ref'].strip(),
                           'actual_delivery_receipt_required')
            with Journal(args.journal) as journal:
                journal.finish(auth['event_id'], auth['recipient'], auth['ticket'], args.outcome, receipt['evidence_ref'])
            result = {'status': 'delivery_outcome_recorded'}
        elif args.command == 'reconcile':
            lookup = read_json(args.lookup)
            review.keys(lookup, {'event_id', 'recipient', 'sent', 'checked_at', 'evidence_ref'}, 'reconciliation_schema')
            with Journal(args.journal) as journal:
                journal.reconcile(lookup['event_id'], lookup['recipient'], sent=lookup['sent'],
                    evidence_ref=lookup['evidence_ref'], checked_at=lookup['checked_at'], now=datetime.now(timezone.utc))
            result = {'status': 'reconciled_from_provider_evidence'}
        else:
            bundle, profile = read_json(args.bundle), load_config(args.config)
            approved = check(bundle, profile)
            result = {'status': 'gate_passed', 'event_id': approved.event_id,
                      'selection_sha256': approved.selection['selection_sha256'],
                      'items': len(approved.selection['items'])}
            if args.command == 'build':
                destination = args.out / approved.selection['selection_sha256']
                if destination.exists():
                    verify_artifacts(approved, destination)
                else:
                    write_artifacts(approved, destination)
                result['status'] = 'public_artifacts_built_not_published'
            elif args.command in ('preflight', 'authorize', 'send'):
                publication = read_json(args.publication)
                review.require(bool(args.published_copy) == bool(args.publication_proof), 'both_connector_copy_and_proof_required')
                fetcher = (connector_publication_fetcher(args.published_copy, read_json(args.publication_proof), publication)
                           if args.published_copy else fetch_public)
                body = args.check_body.read_text(encoding='utf-8') if getattr(args, 'check_body', None) else None
                approved, outgoing, _ = preflight(bundle, profile, publication, body=body, fetcher=fetcher)
                result['status'] = 'publication_and_body_verified_not_sent'
                if args.command == 'preflight' and args.body_out:
                    private_write(args.body_out, outgoing)
                elif args.command == 'authorize':
                    recipient = recipient_address(os.environ[args.recipient_env])
                    with Journal(args.journal) as journal:
                        journal.configure_recipients([x.strip() for x in os.environ[args.recipients_env].split(',') if x.strip()])
                        auth = authorize_external(bundle, profile, publication, journal, recipient,
                            read_json(args.sent_lookup), outgoing, fetcher=fetcher)
                    private_write(args.authorization_out, json.dumps(auth, indent=2)+'\n')
                    result = {'status': auth['status'], 'event_id': approved.event_id}
                elif args.command == 'send' and args.send:
                    recipients = [x.strip() for x in os.environ[args.recipient_env].split(',') if x.strip()]
                    with Journal(args.journal) as journal:
                        statuses = send(bundle, profile, publication, journal, recipients, fetcher=fetcher)
                    if all(x == 'already_handled' for x in statuses):
                        return 0
                    result = {'status': 'delivery_attempted', 'outcomes': statuses}
                    if any(x not in {'sent', 'already_handled'} for x in statuses):
                        print(json.dumps(result))
                        return 2
        print(json.dumps(result))
        return 0
    except Exception as exc:
        # Do not echo recipient values, credentials, SMTP text, private paths or raw plans.
        code = str(exc) if isinstance(exc, review.ReviewError) else type(exc).__name__
        print(json.dumps({'status': 'blocked', 'code': code}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
