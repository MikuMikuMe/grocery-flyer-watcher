# Private project-wide diagnostics

Set `FLYER_DIAGNOSTICS=1` on the actual production Python command to emit JSON lines to
stderr. Default behavior stays quiet and stdout keeps its existing result/report format.
Use a private log destination outside every checkout, restricted to the operator. Do not
upload logs to GitHub, CI artifacts, public reports, issues, or email. They describe private
operational activity even though values are minimized. Existing schedules and credentials
are not changed by installing this feature. Do not send test mail to test diagnostics.

Example (use an existing authorized private directory, not a checkout):

```sh
umask 077
FLYER_DIAGNOSTICS=1 PYTHONPATH=src python -m grocery_flyer_watch quality check \
  /private/bundle.json --config config/watch.toml 2>/private/check-diagnostics.jsonl
```

## What is recorded

Every instrumented phase emits `started` and then `completed`, `failed` or `interrupted`.
Records use `schema: flyer-diagnostic-v1`, UTC timestamp, randomly generated `run_id`,
increasing `sequence`, a fixed `stage`, and terminal `duration_ms`. Nested calls share the
run ID. Independent commands get new IDs; relate them using existing private task context,
not recipient-derived IDs. Caught delivery/profile errors emit an explicit outcome too.

Coverage includes configuration; collector input and timeout/JSON errors; snapshot validation,
scope and comparison; source-evidence/coverage/offer review; quality checks; projection and
rendering; artifact creation and drift verification; publication fetch/write/bridge verification;
private path/state/reservation/acknowledgement/reconciliation; SMTP and external-send authorization;
independent-profile failures; and runtime capability/history preflight. The bootstrap verifies
`diagnostics.py` alongside the other mandatory modules before restoring/running current code.
Its pre-import failures retain the existing safe `runtime_blocked` codes.

Errors preserve a finite, source-controlled `code` such as `collector_not_configured`,
`snapshot_scope_mismatch`, `local_purchase_claim_not_verified`,
`public_artifact_differs_from_reviewed_selection`, or `private_state_must_be_outside_checkout`.
Read that named check in the indicated module and repair real inputs or environment.
Do not relax a validation guard, manufacture evidence or reset state to clear a diagnostic.
Unknown exceptions use `unexpected_error` and a bounded error type, never their raw text.
New gate codes must be added to `SAFE_CODES` with regression tests; unknown codes stay suppressed.

No arguments, returns, source contents, command argv, environment values, exception messages,
stack traces, filenames, URLs, recipient data/counts/hashes, headers, receipts, or tokens are
included. Labels and codes are allowlisted, not merely stripped of unsafe characters. Log sink
failures do not replace a business result or trigger retries. Diagnostics are not a durable
transaction journal or delivery authority. Preserve the selected adapter's real private history.

## Interpret the outcome precisely

- `completed` means a Python phase returned. A blocked result can return normally. It does
  not mean the flyer qualified, a publication was committed, or email was sent. Inspect the
  command's actual result and the narrower phase/outcome events.
- `failed` identifies an observed exception. At `delivery.transport`, `smtp_not_started`
  proves no SMTP submission began; `smtp_acceptance_unknown` is ambiguous, not safe to retry.
- `accepted` with `transport_accepted` means the SMTP transport returned and private journal
  acknowledgement succeeded. It does not prove inbox receipt or a separate Sent lookup.
- `uncertain` records ambiguity after transport/reservation or acknowledgement failure.
  Keep the existing reservation/history and reconcile actual provider evidence before retry.
- `skipped` with `already_handled` is duplicate suppression, not a new successful send.
- A `started` phase without a terminal event is **unknown/incomplete**, not evidence of failure
  or success. A hard kill/power loss cannot emit an interruption record. `KeyboardInterrupt`
  and escaping `SystemExit` are recorded as `interrupted`; inspect the exit status for intentional
  CLI help/argument exits. Never infer safe retry from a missing terminal record.

A code pin, successful tests, capability discovery, authorization or artifact build is NOT
an actual publication or provider mutation. Preserve the distinction on every run.

## Connected tools and research outside Python

The Python package does not intercept browser, GitHub or Gmail connector calls. The operator
must retain their actual outcomes in existing PRIVATE task history, together with which stage
was attempted and its real evidence reference. Never invent a failed validator run when no
validator was invoked. Likewise, unfinished research is not a rejected flyer.

For each stage, distinguish `not_started`, `research_incomplete`, actual validator rejection,
permission denial before execution, authentication error, source/network outage, confirmed
provider failure, provider acceptance, acceptance unknown, and actual Sent verification.
Record the specific operation and safe reason separately from the private provider evidence.
Do not paste raw error bodies or private recipient details into public diagnostics.

A blocked official viewer is one source attempt, not a whole-flyer rejection when a matching
reputable archive was reviewed. Keep the actual regional/dated source and logical-page evidence
under the existing source policy. For interrupted publication, inspect the actual repository
before retrying; for ambiguous sending, inspect provider/Sent evidence and prior attempt history.
An empty search alone does not resolve ambiguity. Continue independent profiles safely.

## Continuation diagnostics

See docs/CONTINUATION.md. A checkpoint, saved page cursor or scheduled
follow-up never proves a live source inspection, public GitHub mutation or
successful Gmail send. Missing terminal events remain incomplete/unknown;
actual provider outcomes and private uncertain attempts need reconciliation.
Checkpoint records and diagnostic logs are PRIVATE, never GitHub artifacts.

## Offline regression checks

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

Framework tests cover no-op defaults, safe vocabulary, hostile private values and exception
classes, nested correlation/order, interruption, return/exception identity and broken sinks.
Pipeline tests exercise collector timeouts and malformed JSON, wrong scope, local-price evidence,
artifact drift, profile isolation, CLI failure correlation and SMTP known/ambiguous failures.
Existing integration tests retain publication gating, duplicate suppression, authorization,
acknowledgement failure, enrollment/backfill prevention and all retailer-source regressions.

Test temporary directories must be outside a checkout because private-state guards apply in
tests too. If `/tmp` has a `.git` marker in a managed environment, use an authorized private
`TMPDIR` outside checkouts. Do not remove the guard or its marker to make tests pass.
