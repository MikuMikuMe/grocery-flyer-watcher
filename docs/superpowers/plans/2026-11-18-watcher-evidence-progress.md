# Watcher Verified Evidence Progress Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans with test-first steps, and wshobson workflow-patterns for red/green/refactor, verification and small commits.

**Goal:** Prevent no-progress scheduled research loops by persisting source-verified public advertising facts and generating a concrete safe run ticket.

**Architecture:** The existing scheduled ChatGPT task remains sole executor. Offline Python modules validate public-only ad facts and produce private, non-authorizing work instructions, feeding the unchanged quality and connected GitHub/Gmail delivery gates. The task saves only bounded checkpoint cursors and source-fact commit/path references privately.

**Tech Stack:** Python 3.11+ standard library, unittest, existing GitHub connector + native Automations task.

**Spec:** `docs/superpowers/specs/2026-11-18-watcher-evidence-progress.md`

## Global Constraints
- Preserve the native hourly schedule and enabled state, no additional executor/sender/DB.
- New modules do not fetch sources or send, publish, or authorize anything themselves.
- All public output must be factual, privacy-screened advertising data with exact source evidence; incomplete research is never `unchanged`.
- Preserve actual market/edition/terms, second omission pass, baseline/value, immutable publication, and per-recipient Gmail safety gates.

## Review Focus
- Secret/contact injection in an offer name, URL, quote or term must fail closed.
- A `SAVE $X` reduction must never become an invented cash price.
- Product/pack/amount not present in the actual quoted advertisement must be rejected.
- Stale source proof must refresh the chosen evidence, not reset completed inventory.
- Source-blocked retailer must rotate only to genuinely viable eligible other profiles, never skip an uncertain Gmail attempt.

### Task 1: Public advertisement-fact snapshot

**Files:** Create `tests/test_advertised_facts.py`, `src/grocery_flyer_watch/advertised_facts.py`.

**Interface:** `validate_snapshot(snapshot)` and `build(snapshot) -> {path,sha256,public_document}`, with `main` CLI taking a JSON input and printing canonical JSON. No network or Git actions.

- [ ] Write failing unittest fixture for accurate dated Ontario product facts, deterministic stable content/path, and rejection of private fields, noncash savings, bad quotes, unclean links, wrong packs.
- [ ] Run CI red to verify the expected missing-module failure.
- [ ] Implement minimal pure validator and stable renderer, no data mutation or I/O beyond reading CLI argument.
- [ ] Run CI green and inspect public serialization for privacy and delivery separation.

### Task 2: Stage-based run ticket

**Files:** Create `tests/test_work_ticket.py`, `src/grocery_flyer_watch/work_ticket.py`.

**Interface:** `choose(state, availability, *, previous_primary, previous_made_progress, now) -> dict`; `availability` is explicit caller-verified status for up to eight profiles; no actual eligibility inferred.

- [ ] Write failing tests for pending publication > source research, proven near expiry, blocked retailer rotation, no-progress consecutive run, six-hour freshness without cursor reset, and unsafe/unknown eligibility exclusion.
- [ ] Run red tests before creating implementation.
- [ ] Implement deterministic bounded priority and fail-closed schema checking; return no action when no safe current source is proven.
- [ ] Run green full suite and verify no Gmail output or unsafe state mutations.

### Task 3: Integrate without changing scheduler

**Files:** Modify `docs/RUN_PROGRESS_RECOVERY.md`, `docs/CONTINUATION.md`, existing task prompt *outside the checkpoint marker only*.

- [ ] Document evidence-to-ledger-to-assessment workflow and legitimate partial/blocked states.
- [ ] Update this ONE automation's instructions to prioritize an actual source-fact chunk and baseline/value or quality over repeat library-document reads, using current main SHA to detect changed docs.
- [ ] Verify entire current checkpoint parse+schema, task prompt round-trip and identical schedule/enabled; do not modify recipient states or send mail.
- [ ] Confirm CI on Python 3.11/3.12/3.13 and merge only when passing. Report unsolved live source limitations candidly.
