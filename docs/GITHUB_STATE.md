# Connected watcher: GitHub history, Gmail delivery evidence, no separate database

This is the current state-storage contract for the single scheduled GitHub/Gmail adapter.
It supersedes the mandatory durable-SQLite journal, `quality authorize --journal` and
`quality ack` requirements for THAT adapter only. The standalone SMTP/VM journal remains
supported. Source research, omission review, both change/value gates, exact body checks,
privacy and no-duplicate/no-backfill rules are unchanged.

## Why the separate journal is optional

A journal records advertising decisions and delivery outcomes so a restarted worker can
resume safely. The connected watcher already has durable public GitHub history, private
Gmail Sent history, and the existing private task's run context. Use these rather than
making provisioning a separate storage service a prerequisite. Temporary files are working
copies, not purported permanent state. Do not create a second repository or database.

Public GitHub contains source-linked baselines, reviewed selections/reports and public
assessment decisions. It NEVER contains recipient addresses/identifiers/hashes/counts,
message IDs/headers, private preferences, personal receipt information, delivery results,
send attempts, or per-recipient pending state. No `sent: true` flags or disguised recipient
slots belong in this public repository. Do not upload an existing SQLite journal.

Gmail Sent answers whether the intended recipient already received a campaign. Actual
private task/tool history supplies the original qualifying decision, recipient eligibility
and whether a previous attempt was definitely rejected or ambiguous. Native task context
is already present; this mode does not provision another backend. Do not invent a history
reference or confuse an empty Gmail search with proof of a never-attempted campaign.

## Public history and immutable assessments

Keep ALL existing baseline paths, ledgers, reports and handled editions. They do not need
to be copied into a new database. Read current and preview archives, not just latest.json.
Legacy handled records remain handled even when Sent history is missing; never manufacture
new qualifications for them during this migration. Weak changes and initial baselines stay
silent; preserve their public comparison records with factual editorial status where needed,
not private notification statuses. Source failures must not erase known observations.

For a genuinely qualifying NEW event:

1. Perform the real source-first inventory, candidate evaluation and second omission pass.
   Build the private quality-bundle-v1 using the existing evidence schema. Public historical
   files provide the baseline; quote actual source hashes/read references, not invented ones.
2. Run the existing `quality check` and `quality build`. These remain mandatory and unchanged.
3. Generate the allowlisted public assessment:

   ```sh
   PYTHONPATH=src python -m grocery_flyer_watch.repository_delivery assessment \
     /private/bundle.json --config config/watch.toml --out /private/assessment.json
   ```

   It records retailer/market/source, actual event and period, advertising fingerprints,
   the fixed selection hash, public review time and `decision: qualified`. It records NO
   delivery status or private review evidence. It is not a whole-flyer candidate inventory.
4. Publish the generated selection.json/report.md to their content-addressed report directory
   and the assessment to `state/assessments/<event_id>.json` in the SAME public commit.
   The event path is CREATE-ONLY. Check for existing records across all history before writing;
   reuse an existing qualified record, never overwrite it or change its selection merely to
   create a new send. On a conflict, re-read the repository; do not force a replacement.
5. Pin the actual commit, fetch the two shopping files, and run `quality preflight` to produce
   the exact outgoing Markdown. The existing offline connector-copy proof bridge is supported.
   Also fetch the assessment from that same commit and retain the actual read proof privately.

A selection/report alone is not a pending-delivery record. The public assessment proves which
advertising decision was made, not whether any person was emailed. For retries, reread that
original immutable record, refresh the source facts, and inspect actual private attempt history.
No old-digest backfill, no alert from re-ranking, observation time, source migration or restock.

## Per-recipient authorization without SQLite

Use the real Gmail connector before EACH separate send. Search for the exact target plus
stable retailer/market/period/event identity, older edition subject formats and equivalent
cross-source offers; exclude TEST. Inspect matches rather than trusting a broad subject hit.
Gmail supports `in:sent`, `to:` and `subject:` queries. Never delete sent receipts as cleanup.

Private adapter inputs (never publish these):

- `--record-proof`: repository, commit, path, checked_at, evidence_ref, sha256. The path is
  the actual event assessment; the hash is SHA-256 of its exact generated bytes. The read
  must be a real connector read from the actual pinned commit within ten minutes.
- `--sent-lookup`: recipient, event_id, checked_at, already_sent, evidence_ref,
  older_editions_checked, equivalent_offers_checked. The last two booleans record real checks,
  not assumed success. Evidence must be fresh within ten minutes.
- `--context`: recipient, authorized_recipients, eligible_since, eligibility_ref, history_ref,
  history_checked_at, serial_execution, prior_attempt, attempt_ref. This is a PRIVATE working
  copy of actual configured authorization and actual task history, not a new durable database.
  `prior_attempt` is not_attempted, definitely_failed, uncertain or unknown. The first two
  require supporting actual run/provider evidence; an empty Sent search alone is insufficient.
  Concurrent scheduled/manual sends are forbidden under this single-worker mode.

Recipient enrollment stays in the existing private task. At rollout, keep the existing
recipients eligible for future qualified assessments, without backfilling legacy campaigns.
Record future recipient additions' effective times privately; a recipient added after the
original assessment is not eligible for its retry. Do not republish the record with a later
review time to evade that rule. Do not disclose the roster or enrollment times in GitHub.

```sh
PYTHONPATH=src python -m grocery_flyer_watch.repository_delivery authorize \
  /private/bundle.json --config config/watch.toml \
  --publication /private/publication.json --record /private/actual-assessment-copy.json \
  --record-proof /private/record-proof.json --sent-lookup /private/lookup.json \
  --context /private/context.json --check-body /private/outgoing.md \
  --authorization-out /private/authorization.json
```

When Python networking is unavailable, add the same `--published-copy` and
`--publication-proof` arguments used by `quality preflight`. They must come from ACTUAL
connector reads, never locally generated output pretending to be public.

This executable reruns the full existing source quality/publication/body checks, validates
the event record and fresh private evidence, and returns a short-lived authorization for
one target and exact subject/body. It does not create a database or send mail. Only
`status=authorized` permits the actual Gmail tool call, once, within five minutes. Send
individual messages without another recipient in To/CC/BCC/body. A sent match skips that
recipient. Record the actual tool outcome in private task history and verify Sent afterward;
transport acceptance is not a promise of inbox receipt. Do not call the SQLite-only `ack`
command for this adapter or announce that no journal blocks it.

## Uncertain attempts, outages and realistic guarantees

GitHub and Gmail are NOT one transaction. There is no exactly-once guarantee across two
independent services or overlapping workers in this adapter. Do not claim one. Keep one
scheduler, serialized sends and no simultaneous manual run. For stronger multi-worker
requirements a transactional private transport journal remains an optional VM architecture.

If Gmail times out or a previous run crashed after starting a send, mark that private attempt
uncertain. Check actual Sent/provider evidence before considering any retry. A found message
means handled; confirmed pre-acceptance failure can be retried while the original offers are
still useful. Continued absence of a match does not itself resolve ambiguity. Unknown/uncertain
attempts stay blocked for that recipient only and must not suppress independent retailers.
No public delivery logs or unsafe automatic resends. If required native private history is
actually unavailable, report that specific ambiguity, not a generic missing-database blocker.

## Startup and portability

Use `runtime_preflight --state-backend github-gmail` for this connected task. It still checks
actual action schemas, but the lack of a SQLite file is NOT an operational blocker. Its
output does not claim per-event history was already read or that any mail was delivered.
Recover missing executable files from pinned GitHub bytes. The bootstrap manifest can include
repository_delivery.py and runtime_preflight.py as verified optional modules; it preserves the
core module interface, now including diagnostics.py for safe stage diagnostics. Load current source files rather than an old runtime ZIP.

The existing SMTP `quality send --send` and its SQLite journal are unchanged and available
for VM operators. The public dated-flyer CLI/schema and all source profiles remain compatible.
No tests, live checks, setup emails, baseline resets or schedule changes follow automatically
from installing this adapter.

Primary references: https://support.google.com/mail/answer/7190 and
https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories .
