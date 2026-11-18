# Resumable single-task execution

This protocol applies to the existing connected Grocery Flyer Watcher only.
It does not add a scheduler, database, VM, mail provider or test email, and it
preserves the current configured cadence and enabled/paused state.

## Durable state boundaries

The public GitHub repository keeps verified retail advertising history:
baselines, source observations, edition archives, public reports and immutable
assessments. Never put an operational checkpoint, source review log, private
store preferences, recipients or delivery data in that PUBLIC repository.

The same scheduled task's PRIVATE saved prompt and prior tool/run context
hold a compact private-flyer-continuation-v1 checkpoint. Use the one
FLYER_PRIVATE_CONTINUATION_V1 marker block and the optional
grocery_flyer_watch.continuation helper to validate/replace it. A prompt
checkpoint is only durable AFTER the existing task's native update action
successfully returns and the task is reread. Preserve every other instruction,
the original schedule and enabled state. A file in an ephemeral runtime is NOT
persistent across runs. If private task writing is unavailable, do not claim
that ephemeral work was checkpointed.

Gmail Sent plus genuine private attempt history, not a checkpoint flag or an
empty search, determine whether an individual recipient's delivery is handled.

## Resume procedure

1. On every execution, read the latest private task checkpoint and actual
   prior run results, resolve the stable GitHub repository ID and compare the
   canonical profile registry, reports, baselines and public assessments.
   Search genuine Gmail Sent for previously handled or uncertain campaigns.
   Do not equate a platform 'completed' status with completed retailer work.
2. Briefly triage all enabled profiles, then prioritize one actionable
   unfinished retailer and finish it end to end before deeply researching the
   next. A failed or blocked source must not suppress independent profiles.
3. After EACH truly successful research or publication stage, save the PRIVATE
   checkpoint: retailer/source scope, period hint, last completed stage, next
   stage, actual tool evidence reference, source page cursor, observation time,
   exact pending reason and any pinned public commit/path. Update the same
   task and reread it before claiming durable persistence. A stopped or
   unreturned operation is unknown, not completed.
4. The page cursor prevents rediscovering where research stopped, but does
   NOT preserve the freshness of source proofs. For the full quality gate,
   reread original advertisements and refresh evidence older than six hours.
   Perform the distinct omission review and maintain all value/expiry/privacy
   checks; an old candidate list cannot prove complete source coverage.
5. For truly qualified NEW advertising events, run the unchanged quality
   check/build, create-only public assessment plus immutable report/selection
   in one commit, read back pinned files, run preflight and rerun
   repository_delivery authorization before EACH separate recipient.
   A checkpoint never supplies an authorization.
6. Immediately BEFORE each Gmail send, privately persist the write-ahead
   recipient status 'uncertain', and verify the task update succeeded. Only
   then call the authorized Gmail sender once. Verify the exact message in
   Sent and record 'accepted_verified_in_sent'. A confirmed rejection before
   acceptance may be recorded as 'definitely_failed_before_acceptance'.
   A timeout or interrupted/no-result send stays uncertain and MUST NOT be
   automatically retried merely because a later Sent search is empty.
   Another recipient/retailer can still continue independently.
7. If the run ends incomplete, preserve the stage/cursor and exact next safe
   action in PRIVATE task context. The NEXT normal scheduled run recovers it
   before broad new research. Do not send a status/error email, invent new
   promotion identity, reset baselines, reopen handled editions or publish
   delivery state. Report actual incomplete work truthfully.

## Restart timing and limitation

This is automatic resume on the SAME task's next scheduled execution, not an
instant, guaranteed back-to-back cloud run. The native run_now action does not
establish a non-overlapping 'queue after my current run ends' guarantee; do not
self-trigger a concurrent sender, create a second scheduler or silently
change the configured checking cadence. Faster safe reruns require a separately
verified same-task serialization capability.

## Optional executable helper

The optional src/grocery_flyer_watch/continuation.py module supports seed,
validate, plan, extract, embed, before-send, sent-verified and
preacceptance-failed operations, plus source-failover, coverage, rotate and outcomes. It needs only standard-library Python.
Use temporary PRIVATE paths outside every public checkout. It never sends
email, updates a task, mutates GitHub or authorizes delivery by itself.

Example of initial PRIVATE checkpoint creation:
    PYTHONPATH=src python -m grocery_flyer_watch.continuation seed
      --registry config/profiles.toml --out /private/checkpoint.json

Example planning command:
    PYTHONPATH=src python -m grocery_flyer_watch.continuation plan
      /private/checkpoint.json

Example PRIVATE write-ahead marker after a fresh authorization:
    PYTHONPATH=src python -m grocery_flyer_watch.continuation before-send
      /private/checkpoint.json --profile EXAMPLE_PROFILE
      --recipient-slot PRIVATE_SLOT
      --provider-evidence-ref ACTUAL_AUTHORIZATION_REFERENCE
      --out /private/writeahead.json

The task operator must actually save and reread its private task prompt
after embedding writeahead.json, before invoking Gmail. Generated local files
and successful tests are not durable persistence, publication or transport.
Set FLYER_DIAGNOSTICS=1 on actual production Python commands and keep all
diagnostics and native connector outcomes private.

## Reliable persisted-checkpoint verification

A marker pair, an API success response, and text equality without schema checking are
**not** sufficient evidence that a saved checkpoint can be resumed. Before any native
update, run `continuation.validate(state)` (all canonical stage names, bounded fields,
valid JSON and size). Serialize using `continuation.embed(old_prompt, state)`, never a
manual partial JSON/string insertion. Immediately after native update, fetch the whole
saved prompt and call `continuation.verify_saved_prompt(saved_prompt, state)`; also
compare the task schedule/enabled state to its pre-update values. If validation or
readback fails, state is **not durable**; no subsequent send is allowed. Report the
checkpoint error privately and repair from verified prior source state, preserving any
recipient uncertainty and completed page references. Never dump raw task JSON to chat.

For progress that doesn't yet complete a formal stage, use the canonical previous
`last_completed` and next stage, while keeping truthful page/group details in the
bounded `source_cursor.completed_units`. Do not invent a stage like
`weekly-original-page-first-visual-inspection` that the validator cannot accept.
See [RUN_PROGRESS_RECOVERY.md](RUN_PROGRESS_RECOVERY.md) for fallback and rotation.

Research recovery commands and their private evidence contract are documented in [RUN_PROGRESS_RECOVERY.md](RUN_PROGRESS_RECOVERY.md). These decisions must be invoked on actual stalled source work. They cannot themselves authorize a quality bundle or a send.

## Reusable advertising facts (2026-11-18)

The validated native checkpoint preserves stage/cursor/recipient uncertainty but is intentionally bounded; it cannot carry the entire source item pool. For actual reviewed products, use [ADVERTISED_FACTS.md](ADVERTISED_FACTS.md): validate only PUBLIC advertising facts, manually privacy review the output, create-only commit content-addressed verified chunks, and pin verified pointers in the PRIVATE cursor. The executable private work-ticket prioritizes unfinished review/quality gates and rotates after real no-progress. Neither helper creates a live collector, source proof, source-wide coverage flag, authorization ticket or email. Stage publication and write-ahead Gmail rules remain unchanged. A six-hour refresh changes source evidence freshness, not already-completed logical page inventory.
