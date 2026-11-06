# Live delivery gate: coverage, canonical output and recipient-safe sending

This document supersedes the **offline-only transport boundary** in QUALITY_GATE.md.
The existing `review.py` stays available for historical compatibility; it is now a layer
inside a stricter delivery pipeline. The old `run` command with its built-in SMTP notifier
and direct `runner.send_smtp(snapshot, key)` refuse unaudited delivery. Validation,
comparison, legacy report rendering, dry runs, explicit seeding and local archival runs
remain available. No scheduler or account settings are changed by installing this code.

## What is enforced in code

`quality_gate.py` checks the actual private review bundle before public output or sending:

- Correct retailer, market and timezone, established baseline, real qualifying change,
  and distinct advertising/event identity versus editorial selection identity.
- All declared source pages accounted for; front and back coverage for finite flyers;
  department leads and candidate references reconciled; a separate source-read reference
  for the omission pass; content fingerprints and fresh evidence.
- Explicit attempts at alternate sources and a specific public gap for a genuine partial
  exception. A blocked front/back page cannot be used to claim a full flyer review.
- The existing 8-10-entry contract, with a narrow reviewed shortfall and mostly useful
  purchases. Candidates and leading exclusions are assessed before selection.
- Exact advertised wording, price, unit, pack, terms, dates and purchase channel reconciled
  against separately recorded fact evidence. An amount cannot borrow another price's
  per-pound unit; SAVE amounts are not checkout prices. Unknown bone content is not boneless.
- Offer-level expiry inside a weekly edition, comparison validity, actual local applicability,
  and evidence freshness at the moment of delivery. Undated collections remain undated.
- Public allowlist projection, explicit privacy review, private-phrase screening and no private
  reasons, coverage read references, receipt data or delivery state in public artifacts.

`reviewed_delivery.py` implements the production sending path:

- Both public files are fetched at an immutable GitHub commit and checked byte-for-byte.
- Report shopping entries and the email come from the same selected records. The email
  appends a commit-pinned report link, not a mutable `main` link. No general liability footer.
- A private SQLite journal reserves each event/recipient before transport. Separate messages;
  successful recipients are not retried, a failed recipient does not suppress another, and
  uncertain acceptance requires explicit provider reconciliation rather than a timeout retry.
- Existing baselines must be imported deliberately. Changing selection order, wording or
  campaign display labels cannot invent a new edition event. Initial/handled events stay quiet.
  A new recipient cannot receive a previously created event as a backfill.
- The full quality and publication checks run before **each** recipient. A stale/expired or
  mutated selection is blocked even if it passed earlier in the run.

## Limits: do not turn validation into fabricated evidence

The software checks supplied evidence, calculations, consistency and actual publication.
It cannot prove that a collector read a source image or discover an offer omitted from BOTH
its page inventory and candidate list. The collector must truly enumerate sources, inspect
all accessible departments, and perform the second source-first omission review. A content
hash must come from actual observed content, not a generated random value. A second read
reference must identify a real second inspection, not a copied first-pass reference.

This is not a new web scraper, optical-recognition system, stock API, value oracle or model
service. No subscriptions or paid providers are installed. No green test run authorizes
real offers. Tests use synthetic fixtures and mocked transports only.

The built-in CLI/default SMTP path cannot accidentally use the old unreviewed sender.
Arbitrary Python callback injection and direct Gmail connector tools are not sandboxed by
this module. The scheduled agent MUST use the authorization protocol below; Python cannot
revoke its independent Gmail permission. Do not call a custom transport to bypass validation.

## Private bundle format

Input is `quality-bundle-v1`, not a legacy `{flyer, offers}` snapshot:

```json
{"format":"quality-bundle-v1","plan":{},"audit":{}}
```

`plan` uses the existing strict review-plan v1 schema documented in QUALITY_GATE.md. It
contains all candidates, their factual source quotes, exact selected IDs, private inclusion/
exclusion reasons, page inventory and second-pass review. Do not pass it to legacy `run`.

`audit` has exactly these fields:

| Field | Required content |
| --- | --- |
| `source_scope` | Stable source identifier, for example `weekly-flyer`, `deals-centre` or `clearance-centre`; never a changing crawl timestamp. |
| `source_kind` | `flyer`, `collection` or `warehouse`. |
| `edition` | Real `starts_on` and `ends_on`; both null for an undated collection. |
| `baseline` | Established matching retailer/market/source and period, actual content hash, coverage completeness, material offer facts and private reference. |
| `trigger_ids` | Actual changed offer IDs for a material-offer event; empty for a genuinely new dated edition. |
| `source_sha256` | Fingerprint of actual source content; not the selected-report hash. |
| `page_proofs` | One record per inventoried source unit, described below. |
| `fact_proofs` | One independently transcribed evidence record per selected offer ID. |
| `partial_exception` | Null for complete coverage, otherwise actual alternate-source attempts and a private reason. |
| `privacy_reviewed` | True only after inspecting ALL projected public text. |
| `forbidden_phrases` | Actual private phrases that must never appear in public output; the list itself stays private. |
| `reviewed_bundle_sha256` | Binding of the final bundle confirmed during an actual source-first second review. |

Baseline keys: `retailer`, `market`, `source_scope`, `starts_on`, `ends_on`, `source_sha256`,
`inventory_complete`, `offers`, `reference`. Each material baseline offer has `promotion_id`,
`source_name`, `price_cad`, `pricing`, `pack`, `starts_on`, `ends_on`, `terms`. For a new edition,
previous period/content/reference are mandatory; prior selected lists must not be presented
as exhaustive inventories. For material collection changes, additions require a complete
prior inventory, while known-product comparisons can use reliable overlapping observations.

Each page proof: `unit_id`, `role` (`front`, `back`, `front_back`, `content`, `grid`),
`departments`, `lead_ids`, `content_sha256`, `observed_at`, `first_read_ref`, `second_read_ref`.
A blocked unit has null content hash, no purported lead observations and genuine failed-read
references. Reviewed pages require real hashes; fresh evidence is limited to six hours.

Each fact proof: `facts`, `source_url`, `read_ref`, `observed_at`, `price_excerpt`,
`terms_excerpt`, `validity_excerpt`, `channel_excerpt`, `local_scope_verified`,
`comparison_window`. The `facts` object contains exactly `source_name`, `price_cad`,
`price_kind`, `pricing`, `pack`, `starts_on`, `ends_on`, `terms`, `channel`, matching the
source-native candidate. Numeric/technical claims must not be hidden inside the free-form
assessment to evade structured fact checks. Terms must be supported by the cited excerpt.
The collector remains responsible for preserving *all* material conditions, not just those
it happened to transcribe. Regional in-store eligibility is not a guarantee of live shelf stock.

`comparison_window` is null without a comparison; otherwise it records `starts_on`,
`ends_on`, `verified_on`, `evidence_ref`, and must cover the stated comparison period.
The existing structured comparison checks require matching evidenced attributes and units.

See `tests/quality_fixture.py` for an executable, dynamically dated SYNTHETIC schema example.
Never use its prices, hashes, review flags or evidence references for production. Its `seal`
helper is test-only; real inspection cannot be replaced by recomputing a hash.

## Authoring, review and offline build

Use Python 3.11+ with the existing package installation. There are no new runtime dependencies.
Keep the real bundle, baseline references, private phrases, transport settings and journal
outside the public checkout. Commands below use generic paths and never embed addresses.

```sh
# Compute the record binding before the actual second-source check. This is NOT approval.
grocery-flyer-watch quality binding /private/bundle.json
# Inspect the original sources again, resolve findings, and record the reviewed binding.
grocery-flyer-watch quality check /private/bundle.json --config config/watch.toml
# Produces only <selection hash>/selection.json and report.md.
grocery-flyer-watch quality build /private/bundle.json --config config/watch.toml \
  --out /private/public-output
```

If facts change after the review, repeat the real second pass; do not rubber-stamp a new
hash. `build` never browses, sends, publishes, installs a timer or resets handled history.
An already-existing output directory is accepted only when both file contents still match.

Publish ONLY the generated two public files to a versioned directory ending in their
selection SHA-256, for example `reports/reviewed/<retailer>/<selection-sha256>/`. Preserve
all old baselines and report paths. Use an authorized Git writer; the code does not perform
an unaudited `git add .` or push private review files.

## Verify actual publication and compose the exact outgoing body

After the real Git push succeeds, create a private publication receipt:

```json
{"repository":"OWNER/REPOSITORY","commit":"ACTUAL_40_HEX_COMMIT_SHA","directory":"reports/reviewed/RETAILER/ACTUAL_SELECTION_SHA256"}
```

```sh
grocery-flyer-watch quality preflight /private/bundle.json --config config/watch.toml \
  --publication /private/publication.json --body-out /private/outgoing.md
```

Preflight reads both committed files over public HTTPS and compares them with newly
validated expected bytes. A local commit, branch name, missing file or mismatching body
fails. `--body-out` creates a NEW private file rather than overwriting an old sent digest.
A later check uses `--check-body /private/outgoing.md`. Do not reconstruct it from memory.

### Network-restricted ChatGPT runtimes

When Python has no internet but the GitHub connector works, fetch BOTH files from that
actual pinned commit using the connector. Save exact returned UTF-8 file bytes to a
private directory, and record actual read references and SHA-256 values in a PRIVATE proof:

```json
{
  "repository":"OWNER/REPOSITORY",
  "commit":"ACTUAL_40_HEX_COMMIT_SHA",
  "directory":"reports/reviewed/RETAILER/ACTUAL_SELECTION_SHA256",
  "verified_at":"ACTUAL_UTC_TIMESTAMP",
  "evidence_refs":{"selection.json":"ACTUAL_CONNECTOR_READ_REF","report.md":"ACTUAL_CONNECTOR_READ_REF"},
  "sha256":{"selection.json":"ACTUAL_CONTENT_SHA256","report.md":"ACTUAL_CONTENT_SHA256"}
}
```

Add `--published-copy /private/connector-copies --publication-proof /private/proof.json`
to preflight/authorize/send. This bridge checks exact content, scope and a ten-minute
freshness window; it CANNOT cryptographically prove a model-written read attestation.
Never fill it from local output alone or invent connector calls to claim publication.
If there is no authenticated writer or durable private state, keep the event pending;
do not pretend it was published/sent, expose private state publicly or bypass the gate.

## Migration: preserve handled editions and sources

Before any live send, import EVERY already-handled edition, including previews that have
since started. Do not seed only a stale `latest.json` while ignoring already-sent previews.
Use the existing private history and actual provider evidence when classifying handled
and genuinely pending work. Importing history never sends anything.

```sh
grocery-flyer-watch quality seed --config config/watch.toml \
  --journal /private/delivery.sqlite --source-scope weekly-flyer \
  --snapshot /path/to/already-handled-edition.json
# For undated sources, supply actual existing inspected history, not a placeholder.
grocery-flyer-watch quality seed --config config/staples.toml \
  --journal /private/delivery.sqlite --source-scope deals-centre \
  --collection-history /path/to/existing-source-ledger.md
```

Source scope identifiers must stay stable across migration and later runs. A missing
journal is not authorization to resend a baseline: uninitialized scopes are blocked.
Keep the SQLite file and sidecars outside any public checkout, with private permissions,
and persist them across scheduled runs. If the execution environment is ephemeral, use
an actual durable private state store or restore the private journal before operating.
The code does not install a cloud private-state backend.

A new dated edition derives its event ID from scope plus dates, not report content or
an agent-chosen label. Material changes use actual before/after advertising facts.
The journal freezes event content/publication after the first attempted delivery; pending
recipients cannot silently receive a rewritten version of the same event. Changes to
scope IDs or an incorrect baseline cannot be used to manufacture a fresh event.

## Connected Gmail: authorize, send exactly once, acknowledge

Preserve the existing private sender and full recipient list. Store them only in private
configuration/environment variables. `FLYER_MAIL_TO` is the full authorized comma-separated
list; `FLYER_RECIPIENT` is the one target of the next individual message. Changing the full
list does not backfill old events to newly added recipients.

Immediately before each send, perform an ACTUAL Gmail Sent search for that recipient and
retailer/period/event, including the previously used subject/edition identity and excluding
TEST messages. This must cover older formats and equivalent cross-source offers, not just
the newly computed event hash. Save a private lookup:

```json
{"recipient":"ACTUAL_PRIVATE_TARGET","event_id":"ACTUAL_EVENT_ID","checked_at":"ACTUAL_UTC_TIMESTAMP","already_sent":false,"evidence_ref":"ACTUAL_GMAIL_SEARCH_REFERENCE"}
```

```sh
grocery-flyer-watch quality authorize /private/bundle.json --config config/watch.toml \
  --publication /private/publication.json --journal /private/delivery.sqlite \
  --sent-lookup /private/lookup.json --check-body /private/outgoing.md \
  --authorization-out /private/authorization.json
```

Only `status=authorized` permits the task to invoke Gmail. Check the ticket's recipient,
subject, body hash and five-minute expiry, then pass the exact outgoing Markdown with no
other recipient in To/CC/BCC/body. The Python authorization step does not itself send mail.
Record the actual tool result via `quality ack --journal ... --authorization ... --outcome
sent|failed|uncertain --receipt ...`; the receipt file contains only a private
`{"evidence_ref":"ACTUAL_PROVIDER_RESULT"}`. Do not claim inbox receipt from transport
acceptance. A crashed/ambiguous send is reserved/uncertain and cannot be retried automatically.
Resolve it only after an actual fresh Sent lookup using `quality reconcile --lookup ...`.
The reconciliation JSON requires event_id, recipient, sent, checked_at and evidence_ref.

Do not describe direct Gmail access as mechanically revoked: the task instructions enforce
use of the adapter. The new task override accompanies this implementation; it must be added
to the existing task by a runtime exposing task-update capability, while preserving its
private prompt, cadence and enabled/paused state. Do not create another task as a workaround.

## Standalone SMTP: real integrated gate

```sh
# Without --send this is preflight only; it does not create delivery state or send mail.
grocery-flyer-watch quality send /private/bundle.json --config config/watch.toml \
  --publication /private/publication.json --journal /private/delivery.sqlite
# Live command ONLY after legitimate qualifying research, migration and authorization:
grocery-flyer-watch quality send /private/bundle.json --config config/watch.toml \
  --publication /private/publication.json --journal /private/delivery.sqlite --send
```

The latter reads private SMTP/TLS settings from the existing `FLYER_SMTP_*` variables,
`FLYER_MAIL_FROM` and `FLYER_MAIL_TO`. It sends individually, after all live gates and
publication validation. SSL or STARTTLS is mandatory. Safe pre-acceptance failures retry
only the failed recipient; acceptance-ambiguous failures require provider reconciliation.
No automatic test mail or forced retry/ignore-validation switch exists.

`run_profiles(profiles, worker)` isolates failures and disabled profiles across the seven
configured watches. The caller still supplies actual collection/research work; failed or
partial verification must remain `insufficient_evidence`, not `unchanged`.

## Tests and rollout

Run `PYTHONPATH=src python -m unittest discover -s tests -v` in the full repository.
Regression cases cover the previous omission/attribute/expiry/drift failures plus live
publication/body checks, TLS, partial/ambiguous delivery, recipient additions, independent
retailer execution and fail-closed legacy SMTP. Historical archive/state tests remain.
CI should execute the same suite but is not evidence of real flyer accuracy.

No credentials, real recipient lists, private receipt values, new deal reports, source
scope changes, scheduler changes or live emails are part of installing this implementation.
