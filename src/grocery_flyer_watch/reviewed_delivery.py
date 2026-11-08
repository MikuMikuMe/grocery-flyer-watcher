"""Audited publication and per-recipient delivery; no collector or scheduler is installed.

Every production entry point invokes the live gate. Public GitHub artifacts are fetched at
an immutable commit and compared byte-for-byte. Private SQLite state distinguishes sent,
failed and ambiguous attempts; ambiguous sends are never automatically retried.
"""
from __future__ import annotations

from .diagnostics import traced, emit

from contextlib import contextmanager, suppress
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import parseaddr
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import smtplib
import sqlite3
import ssl
from typing import Callable, Mapping
from urllib.request import Request, urlopen

from . import review
from .quality_gate import Approved, artifacts, check, digest, edition_key, scope_key, shopping_body, timestamp


def recipient_address(value: str) -> str:
    review.require(isinstance(value, str) and not any(c in value for c in '\r\n,;'), "recipient_schema")
    name, address = parseaddr(value)
    review.require(not name and address == value and re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value)
                   is not None and len(value) <= 254, "recipient_schema")
    # Do not strip plus-tags or provider-specific dots: these are distinct authorized targets.
    local, domain = address.rsplit('@', 1)
    return local + '@' + domain.lower()


@traced('private_path.validate')
def private_path(path: str | Path) -> Path:
    p = Path(path).expanduser().absolute()
    review.require(not p.is_symlink(), "private_state_symlink")
    p = p.resolve()
    review.require(all(not (parent / '.git').exists() for parent in p.parents),
                   "private_state_must_be_outside_checkout")
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p


class Journal:
    """Per-event AND per-recipient state; never export this database or its sidecars."""
    def __init__(self, path: str | Path):
        self.path = private_path(path)
        # Create with private permissions before sqlite opens it; reject symlinks above.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        self.db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS scopes (id TEXT PRIMARY KEY);
          CREATE TABLE IF NOT EXISTS recipients (address TEXT PRIMARY KEY);
          CREATE TABLE IF NOT EXISTS handled_editions (id TEXT PRIMARY KEY);
          CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY, scope TEXT NOT NULL, edition TEXT NOT NULL,
            selection TEXT NOT NULL, publication TEXT NOT NULL, body_hash TEXT NOT NULL,
            triggers TEXT NOT NULL, audience TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS deliveries (
            event TEXT NOT NULL REFERENCES events(id), recipient TEXT NOT NULL,
            status TEXT NOT NULL, ticket TEXT NOT NULL, reserved_at TEXT NOT NULL,
            receipt TEXT, PRIMARY KEY(event, recipient));
          CREATE TABLE IF NOT EXISTS delivered_offers (
            recipient TEXT NOT NULL, fingerprint TEXT NOT NULL,
            PRIMARY KEY(recipient, fingerprint));
        ''')
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(events)')}
        if 'audience' not in columns:
            # An older journal never grants newly added recipients a historical event.
            self.db.execute("ALTER TABLE events ADD COLUMN audience TEXT NOT NULL DEFAULT '[]'")

    def configure_recipients(self, recipients: list[str]) -> None:
        clean = [recipient_address(x) for x in recipients]
        review.require(clean and len(clean) == len(set(clean)), 'authorized_recipient_list_required')
        with self.transaction():
            self.db.execute('DELETE FROM recipients')
            self.db.executemany('INSERT INTO recipients VALUES (?)', [(x,) for x in clean])

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def seed(self, retailer: str, market: str, source_scope: str,
             starts_on: str | None, ends_on: str | None) -> None:
        """Explicitly import handled history. This never creates a pending delivery."""
        for value in (retailer, market, source_scope):
            review.text(value, "seed_scope_missing")
        if starts_on is not None or ends_on is not None:
            review.require(review.iso(starts_on) <= review.iso(ends_on), "seed_dates")
        with self.transaction():
            self.db.execute('INSERT OR IGNORE INTO scopes VALUES (?)',
                            (scope_key(retailer, market, source_scope),))
            self.db.execute('INSERT OR IGNORE INTO handled_editions VALUES (?)',
                            (edition_key(retailer, market, source_scope, starts_on, ends_on),))

    @traced('state.reserve')
    def reserve(self, approved: Approved, recipient: str, body: str, publication: str,
                now: datetime) -> str | None:
        recipient = recipient_address(recipient)
        with self.transaction():
            review.require(self.db.execute('SELECT 1 FROM scopes WHERE id=?',
                           (approved.scope_id,)).fetchone() is not None,
                           "private_history_not_initialized_seed_before_delivery")
            if approved.kind == 'new_edition' and self.db.execute(
                    'SELECT 1 FROM handled_editions WHERE id=?', (approved.edition_id,)).fetchone():
                return None
            review.require(self.db.execute('SELECT 1 FROM recipients WHERE address=?', (recipient,)).fetchone()
                           is not None, 'recipient_not_in_private_configuration')
            audience_row = self.db.execute('SELECT audience FROM events WHERE id=?', (approved.event_id,)).fetchone()
            if audience_row and recipient not in json.loads(audience_row[0]):
                return None  # Never backfill an old campaign to a newly added recipient.
            old = self.db.execute('SELECT status FROM deliveries WHERE event=? AND recipient=?',
                                 (approved.event_id, recipient)).fetchone()
            if old:
                if old[0] == 'sent':
                    return None
                review.require(old[0] == 'failed', "delivery_uncertain_reconcile_sent_history_first")
            if approved.trigger_fingerprints and all(self.db.execute(
                    'SELECT 1 FROM delivered_offers WHERE recipient=? AND fingerprint=?',
                    (recipient, fp)).fetchone() for fp in approved.trigger_fingerprints):
                return None
            values = (approved.scope_id, approved.edition_id, approved.selection['selection_sha256'],
                      publication, hashlib.sha256(body.encode()).hexdigest(),
                      json.dumps(approved.trigger_fingerprints))
            existing = self.db.execute('SELECT scope,edition,selection,publication,body_hash,triggers '
                                      'FROM events WHERE id=?', (approved.event_id,)).fetchone()
            review.require(existing is None or tuple(existing) == values,
                           "pending_event_content_or_publication_changed")
            audience = json.dumps([r[0] for r in self.db.execute('SELECT address FROM recipients ORDER BY address')])
            self.db.execute('INSERT OR IGNORE INTO events '
                            '(id,scope,edition,selection,publication,body_hash,triggers,audience) VALUES (?,?,?,?,?,?,?,?)',
                            (approved.event_id, *values, audience))
            ticket = secrets.token_urlsafe(32)
            self.db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?,NULL) '
                            'ON CONFLICT(event,recipient) DO UPDATE SET status=excluded.status, '
                            'ticket=excluded.ticket,reserved_at=excluded.reserved_at,receipt=NULL',
                            (approved.event_id, recipient, 'reserved', ticket, now.isoformat()))
            return ticket

    @traced('state.finish')
    def finish(self, event: str, recipient: str, ticket: str, status: str, receipt: str = '') -> None:
        review.require(status in {'sent', 'failed', 'uncertain'}, "invalid_delivery_outcome")
        recipient = recipient_address(recipient)
        review.require(isinstance(receipt, str) and len(receipt) <= 1000, "private_receipt_schema")
        with self.transaction():
            row = self.db.execute('SELECT status,ticket FROM deliveries WHERE event=? AND recipient=?',
                                  (event, recipient)).fetchone()
            review.require(row is not None and row[0] == 'reserved' and
                           secrets.compare_digest(row[1], ticket), "invalid_delivery_ticket")
            self.db.execute('UPDATE deliveries SET status=?,receipt=? WHERE event=? AND recipient=?',
                            (status, receipt, event, recipient))
            if status == 'sent':
                triggers = json.loads(self.db.execute('SELECT triggers FROM events WHERE id=?',
                                                      (event,)).fetchone()[0])
                for fp in triggers:
                    self.db.execute('INSERT OR IGNORE INTO delivered_offers VALUES (?,?)', (recipient, fp))

    @traced('state.reconcile')
    def reconcile(self, event: str, recipient: str, *, sent: bool, evidence_ref: str,
                  checked_at: str, now: datetime) -> None:
        """Explicit operator/connector lookup, not an automatic timeout retry."""
        review.require(type(sent) is bool and isinstance(evidence_ref, str) and evidence_ref.strip(),
                       "reconciliation_evidence_required")
        age = now - timestamp(checked_at)
        review.require(timedelta(0) <= age <= timedelta(minutes=10), "reconciliation_lookup_stale")
        recipient = recipient_address(recipient)
        with self.transaction():
            review.require(self.db.execute('SELECT 1 FROM recipients WHERE address=?', (recipient,)).fetchone()
                           is not None, 'recipient_not_in_private_configuration')
            old = self.db.execute('SELECT status FROM deliveries WHERE event=? AND recipient=?',
                                  (event, recipient)).fetchone()
            review.require(old is not None and old[0] in {'reserved', 'uncertain'}, "not_uncertain_delivery")
            self.db.execute('UPDATE deliveries SET status=?,receipt=? WHERE event=? AND recipient=?',
                            ('sent' if sent else 'failed', evidence_ref, event, recipient))
            if sent:
                for fp in json.loads(self.db.execute('SELECT triggers FROM events WHERE id=?',
                                                     (event,)).fetchone()[0]):
                    self.db.execute('INSERT OR IGNORE INTO delivered_offers VALUES (?,?)', (recipient, fp))


@traced('publication.urls')
def publication_urls(receipt: dict, approved: Approved) -> tuple[str, dict[str, str]]:
    review.keys(receipt, {'repository', 'commit', 'directory'}, "publication_receipt_schema")
    repo, commit, directory = (receipt[k] for k in ('repository', 'commit', 'directory'))
    review.require(isinstance(repo, str) and re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+', repo)
                   is not None and repo.rsplit('/', 1)[1] not in {'.', '..'}, "publication_repository")
    review.require(isinstance(commit, str) and re.fullmatch(r'[a-f0-9]{40}', commit) is not None,
                   "publication_requires_commit_not_branch")
    review.require(isinstance(directory, str) and re.fullmatch(r'[a-zA-Z0-9_./-]+', directory)
                   is not None, "publication_path")
    parts = PurePosixPath(directory).parts
    review.require(not directory.startswith('/') and '..' not in parts and '.' not in parts and
                   directory == str(PurePosixPath(directory)) and
                   parts[-1] == approved.selection['selection_sha256'], "publication_must_be_content_addressed")
    base = f'https://raw.githubusercontent.com/{repo}/{commit}/{directory}'
    return (f'https://github.com/{repo}/blob/{commit}/{directory}/report.md',
            {name: f'{base}/{name}' for name in artifacts(approved)})


@traced('publication.fetch')
def fetch_public(url: str) -> bytes:
    """Bounded public GET only; no cookies, account tokens or private request bodies."""
    request = Request(url, headers={'User-Agent': 'Grocery-Flyer-Watcher/quality-gate'})
    try:
        with urlopen(request, timeout=20) as response:
            review.require(response.geturl() == url, "publication_redirect_refused")
            content = response.read(2_000_001)
            review.require(len(content) <= 2_000_000, "publication_too_large")
            return content
    except review.ReviewError:
        raise
    except Exception:
        raise review.ReviewError('publication_not_verified') from None


@traced('publication.verify')
def verify_publication(approved: Approved, receipt: dict,
                       fetcher: Callable[[str], bytes] = fetch_public) -> str:
    report_url, urls = publication_urls(receipt, approved)
    for name, expected in artifacts(approved).items():
        review.require(fetcher(urls[name]) == expected, "published_artifact_mismatch")
    return report_url


@traced('delivery.preflight')
def preflight(bundle: dict, profile: dict, receipt: dict, *, body: str | None = None,
              now: datetime | None = None, fetcher: Callable[[str], bytes] = fetch_public) -> tuple[Approved, str, str]:
    approved = check(bundle, profile, now=now)
    report_url = verify_publication(approved, receipt, fetcher)
    # Recheck the gate after potentially slow publication verification.
    latest = check(bundle, profile, now=now)
    review.require(latest.selection == approved.selection, "review_changed_during_preflight")
    canonical_body = shopping_body(approved.selection) + f'\n[Report and sources]({report_url})\n'
    if body is not None:
        review.require(body == canonical_body, "outgoing_body_differs_from_reviewed_selection")
    return approved, canonical_body, report_url


class KnownDeliveryFailure(RuntimeError):
    """No message was accepted. The per-recipient retry can safely remain pending."""


class AmbiguousDelivery(RuntimeError):
    """Acceptance is unknown. Reconcile private Sent/provider evidence before retrying."""


@traced('delivery.transport')
def _smtp_transport(recipient: str, subject: str, body: str, event_id: str,
                    env: Mapping[str, str]) -> str:
    """Private implementation; public send() performs the gate immediately before this."""
    client = None
    try:
        mode = env.get('FLYER_SMTP_MODE', 'ssl')
        if mode not in {'ssl', 'starttls'}:
            raise KnownDeliveryFailure('smtp_tls_required')
        sender = recipient_address(env['FLYER_MAIL_FROM'])
        recipient = recipient_address(recipient)
        message = EmailMessage()
        message['From'], message['To'], message['Subject'] = sender, recipient, subject
        # Only this private message header uses a recipient-derived value, never public GitHub.
        ident = hashlib.sha256((event_id + '\0' + recipient).encode()).hexdigest()
        message['Message-ID'] = f'<flyer-{ident}@grocery-flyer-watch.invalid>'
        message.set_content(body)
        ctx = ssl.create_default_context()
        port = int(env.get('FLYER_SMTP_PORT', '465' if mode == 'ssl' else '587'))
        try:
            client = (smtplib.SMTP_SSL(env['FLYER_SMTP_HOST'], port, timeout=30, context=ctx)
                      if mode == 'ssl' else smtplib.SMTP(env['FLYER_SMTP_HOST'], port, timeout=30))
            if mode == 'starttls':
                client.ehlo()
                client.starttls(context=ctx)
                client.ehlo()
            if env.get('FLYER_SMTP_USER'):
                client.login(env['FLYER_SMTP_USER'], env['FLYER_SMTP_PASSWORD'])
        except Exception:
            raise KnownDeliveryFailure('smtp_not_started') from None
        try:
            if client.send_message(message):
                raise KnownDeliveryFailure('recipient_refused')
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
            raise KnownDeliveryFailure('server_rejected_message') from None
        except KnownDeliveryFailure:
            raise
        except Exception:
            raise AmbiguousDelivery('smtp_acceptance_unknown') from None
        return str(message['Message-ID'])
    except (KeyError, ValueError):
        raise KnownDeliveryFailure('smtp_config_invalid') from None
    finally:
        if client is not None:
            # An error closing an accepted connection must not turn success into a retry.
            with suppress(Exception):
                client.close()


@traced('delivery.send')
def send(bundle: dict, profile: dict, receipt: dict, journal: Journal, recipients: list[str], *,
         env: Mapping[str, str] | None = None, now: datetime | None = None,
         fetcher: Callable[[str], bytes] = fetch_public,
         transport: Callable = _smtp_transport) -> list[str]:
    """Actual standalone live path. Separate messages and isolated outcomes per recipient.

    Network/transport injection exists for offline tests; deployment callers use defaults.
    Return statuses in input order, never contact data, SMTP errors or message IDs.
    """
    review.require(bool(recipients), "no_recipients")
    clean = [recipient_address(r) for r in recipients]
    review.require(len(clean) == len(set(clean)), "duplicate_recipients")
    journal.configure_recipients(clean)
    # Freeze input against concurrent caller mutation. The entire bundle stays private.
    frozen = json.loads(json.dumps(bundle))
    outcomes = []
    for recipient in clean:
        ticket = None
        approved = None
        transport_started = False
        try:
            approved, body, report_url = preflight(frozen, profile, receipt, now=now, fetcher=fetcher)
            clock = now or datetime.now(timezone.utc)
            ticket = journal.reserve(approved, recipient, body, report_url, clock)
            if ticket is None:
                emit('delivery.outcome', 'skipped', code='already_handled')
                outcomes.append('already_handled')
                continue
            # Do not send expired/stale items if the clock crossed a boundary after reservation.
            check(frozen, profile, now=now)
            subject = f"{approved.selection['retailer']} | {approved.selection['period_label']} | {approved.event_id[:16]}"
            transport_started = True
            proof = transport(recipient, subject, body, approved.event_id, env if env is not None else os.environ)
            journal.finish(approved.event_id, recipient, ticket, 'sent', proof)
            emit('delivery.outcome', 'accepted', code='transport_accepted')
            outcomes.append('sent')
        except KnownDeliveryFailure as exc:
            emit('delivery.outcome', 'failed', exc=exc)
            if ticket and approved:
                try:
                    journal.finish(approved.event_id, recipient, ticket, 'failed')
                except Exception:
                    # Keep the reservation unresolved rather than risking a duplicate.
                    emit('delivery.outcome', 'uncertain', code='state_ack_failed')
                    outcomes.append('uncertain')
                    continue
            outcomes.append('failed')
        except review.ReviewError as exc:
            emit('delivery.outcome', 'uncertain' if transport_started else 'blocked', exc=exc)
            if ticket and approved:
                # Once transport began, an acknowledgement/state failure is ambiguous.
                with suppress(Exception):
                    journal.finish(approved.event_id, recipient, ticket,
                                   'uncertain' if transport_started else 'failed')
            outcomes.append('uncertain' if transport_started else 'blocked')
        except Exception as exc:
            emit('delivery.outcome', 'uncertain' if ticket else 'blocked', exc=exc)
            if ticket and approved:
                # Includes a crash/error after provider acceptance but before local commit.
                with suppress(Exception):
                    journal.finish(approved.event_id, recipient, ticket, 'uncertain')
            outcomes.append('uncertain' if ticket else 'blocked')
    return outcomes


@traced('delivery.authorize')
def authorize_external(bundle: dict, profile: dict, publication: dict, journal: Journal,
                       recipient: str, sent_lookup: dict, body: str, *, now: datetime | None = None,
                       fetcher: Callable[[str], bytes] = fetch_public) -> dict:
    """For connected Gmail: verify exact body, then reserve one private delivery ticket.

    The connector MUST perform the actual Sent lookup. The evidence reference below is an
    attestation, not a forged or simulated lookup. Direct Gmail tools cannot be technically
    disabled by this Python module; the task instructions must require this adapter.
    """
    approved, checked_body, report_url = preflight(bundle, profile, publication, body=body,
                                                  now=now, fetcher=fetcher)
    now = now or datetime.now(timezone.utc)
    recipient = recipient_address(recipient)
    review.keys(sent_lookup, {'recipient', 'event_id', 'checked_at', 'already_sent', 'evidence_ref'},
                "sent_lookup_schema")
    review.require(sent_lookup['recipient'] == recipient and sent_lookup['event_id'] == approved.event_id,
                   "sent_lookup_scope_mismatch")
    review.require(isinstance(sent_lookup['evidence_ref'], str) and sent_lookup['evidence_ref'].strip(),
                   "actual_sent_lookup_required")
    age = now - timestamp(sent_lookup['checked_at'])
    review.require(timedelta(0) <= age <= timedelta(minutes=10), "sent_lookup_stale")
    review.require(type(sent_lookup['already_sent']) is bool, "sent_lookup_result_required")
    if sent_lookup['already_sent']:
        return {'status': 'already_handled'}
    ticket = journal.reserve(approved, recipient, checked_body, report_url, now)
    if ticket is None:
        return {'status': 'already_handled'}
    # This authorization is PRIVATE and is not an email or a record to publish.
    return {'status': 'authorized', 'event_id': approved.event_id, 'recipient': recipient,
            'ticket': ticket, 'expires_at': (now + timedelta(minutes=5)).isoformat(),
            'body_sha256': hashlib.sha256(body.encode()).hexdigest(),
            'subject': f"{approved.selection['retailer']} | {approved.selection['period_label']} | {approved.event_id[:16]}"}


@traced('profiles.run')
def run_profiles(profiles: list[dict], worker: Callable[[dict], str]) -> dict[str, str]:
    """A per-profile failure never short-circuits another enabled retailer.

    Use `insufficient_evidence`/`not_checked`, not `unchanged`, for failed/missing reads.
    This orchestrates the supplied worker; it does not itself browse or invent candidates.
    """
    results = {}
    for profile in profiles:
        pid = profile['id']
        review.require(pid not in results, "duplicate_profile")
        if profile.get('enabled', True) is False:
            emit('profile', 'skipped', code='profile_disabled')
            results[pid] = 'disabled'
            continue
        try:
            result = worker(profile)
            review.require(result in {'sent', 'unchanged', 'initial_baseline', 'insufficient_evidence',
                                      'pending_delivery', 'no_useful_value', 'not_checked'}, "unknown_run_outcome")
            results[pid] = result
        except Exception as exc:
            emit('profile', 'failed', exc=exc)
            results[pid] = 'insufficient_evidence'
    return results


@traced('publication.bridge')
def connector_publication_fetcher(directory: str | Path, proof: dict, receipt: dict, *,
                                  now: datetime | None = None) -> Callable[[str], bytes]:
    """Offline bridge for a runtime whose GitHub CONNECTOR, not Python, has network access.

    The operator must fetch BOTH files at the actual pinned commit with GitHub tools and
    record those read references. This validates the copies, scope, freshness and hashes;
    it cannot cryptographically authenticate a model-written connector attestation.
    Never use this with invented evidence or merely a local git commit.
    """
    review.keys(proof, {'repository', 'commit', 'directory', 'verified_at', 'evidence_refs', 'sha256'},
                'connector_publication_proof_schema')
    review.require(all(proof[k] == receipt[k] for k in ('repository', 'commit', 'directory')),
                   'connector_publication_scope_mismatch')
    clock = now or datetime.now(timezone.utc)
    age = clock - timestamp(proof['verified_at'])
    review.require(timedelta(0) <= age <= timedelta(minutes=10), 'connector_publication_proof_stale')
    names = {'selection.json', 'report.md'}
    review.require(isinstance(proof['evidence_refs'], dict) and set(proof['evidence_refs']) == names,
                   'actual_connector_reads_required')
    review.require(isinstance(proof['sha256'], dict) and set(proof['sha256']) == names,
                   'connector_artifact_hashes_required')
    root = Path(directory).resolve()
    content = {}
    for name in names:
        ref = proof['evidence_refs'][name]
        review.require(isinstance(ref, str) and ref.strip(), 'actual_connector_reads_required')
        p = root / name
        review.require(p.is_file() and not p.is_symlink() and p.stat().st_size <= 2_000_000,
                       'connector_copy_missing')
        content[name] = p.read_bytes()
        review.require(hashlib.sha256(content[name]).hexdigest() == proof['sha256'][name],
                       'connector_copy_hash_mismatch')
    prefix = f"https://raw.githubusercontent.com/{receipt['repository']}/{receipt['commit']}/{receipt['directory']}/"
    def fetcher(url: str) -> bytes:
        age = (now or datetime.now(timezone.utc)) - timestamp(proof['verified_at'])
        review.require(timedelta(0) <= age <= timedelta(minutes=10), 'connector_publication_proof_stale')
        review.require(url.startswith(prefix) and url[len(prefix):] in names, 'unexpected_publication_resource')
        return content[url[len(prefix):]]
    return fetcher
