# Durable factual chunks for the existing native watcher

This is a PUBLIC-FACT ledger, not a new collector, notification channel, quality-bundle, private coverage log, or automation. It addresses loss of item observations when a scheduled ChatGPT execution inspects part of a flyer but cannot finish its full quality assessment. Never place private sources/diagnostics, reviewer cursors, user preferences, recipients or email attempt state in public GitHub.

## After an ACTUAL source read

1. Establish retailer, exact printed edition dates, Ontario/Kingston applicability, item names, original quoted cash prices, packs, channel and written terms. Read original image pages when text omits offers.
2. Write only publicly suitable advertising facts in a PRIVATE temporary JSON file with exact root keys: format, retailer_id, retailer, market, edition, offers. The format must be advertised-facts-v1. Edition keys: starts_on, ends_on, source_url. Each offer: name, pack, price_cad (positive two-decimal cash), pricing, source_url, source_quote, channel, terms. Include quoted footnotes when terms are edition-wide. No private evidence reference, source_cursor, coverage claim, reviewer notes, recipient, assessment, or mail state. Maximum 150 offers per batch.
3. Run, with Python 3.11+ standard library and the repository's existing code:

    PYTHONPATH=src python -m grocery_flyer_watch.advertised_facts /private/offers.json --market "Kingston, Ontario" --retailer-id walmart

   This offline consistency check rejects wrong market/profile, unsupported product/pack/terms/price quotes, SAVE amounts misrepresented as cash, wrong dates, private contacts, embedded tokens, shipping-only channels and duplicate records. It does not read live sources or prove item truth.
4. Manually privacy-review exact serialized output and ACTUAL source evidence. Use the existing connected GitHub create-only file operation for the returned content-addressed path in data/advertisements/<retailer>/<start>_<end>/<sha256>.json. Never overwrite, never publish unverified or fabricated facts. Fetch back the bytes at actual pinned commit and verify SHA256. Exact duplicate content needs no new write.
5. Keep a short PRIVATE task checkpoint pointer and original source read references; don't publish private coverage or attempt details. Reuse only actually verified advertising facts. Refresh expired source evidence before final quality/authorization; do not restart completed logical page or omission inventory.

## From facts to assessments

This partial source ledger NEVER establishes completed coverage, a new qualifying change, useful value, or delivery permission. Reconcile full logical edition, distinct omission revisit and real baseline/price comparisons, then use unchanged quality check/build, immutable create-only assessment, pinned publication, private Sent reconciliation and fresh per-recipient authorize and write-ahead rules. No code here sends mail or writes GitHub.

## Native work ticket (PRIVATE inputs)

First inspect existing task checkpoint and last run, current main SHA, source catalog and BRIEF current eligibility for all eight profiles. Provide an actual per-profile private JSON triage record, each with exactly these keys:
- verified_market_edition: true only with actual scope evidence
- source_readable: true only with a real item grid/page reading
- edition_start and edition_end: printed dates, or both null for undated collections
- undated_collection: true only for actual undated Staples collections
- evidence_ref: actual source/tool read reference; must be present if source_readable

Then invoke:

    PYTHONPATH=src python -m grocery_flyer_watch.work_ticket /private/checkpoint.json --availability /private/triage.json

Pass --previous-primary walmart --previous-no-progress only after verifying from the latest native run that Walmart produced no substantive factual/evaluative stage. The ticket chooses an exact action and deliverable or a precise blocker; with previous confirmed no-progress it rotates to a second independently viable retailer. It cannot invent readable sources or eligibility and never grants quality/publication/email authority. No more than two deep retailers in one run. Refresh of six-hour-old evidence is scoped to selected facts and does not erase cursors.

## Unknown edition dates are an expected triage outcome

For every enabled profile, include an availability record even if the current printed edition cannot be established. Use `edition_start: null`, `edition_end: null`, `undated_collection: false`, `verified_market_edition: false` and `source_readable: false` unless an actual item-bearing page was read (then provide the true `evidence_ref`). Unknown dates are **not a blocker for the other seven profiles**, but that retailer cannot be selected as a viable dated source. Claiming `verified_market_edition: true` without printed dates fails closed. Only an actual undated Staples collection may set `undated_collection: true`.

After an explicitly documented no-progress run, pass the prior primary to the ticket and honor a verified independent secondary. Do not ask the planner to choose among invented readable sources. The next run's primary deliverable must be **source-verified facts persisted create-only, a real baseline/value result, distinct omission review, executable quality result or downstream pinned proof**, not a new visit to the same index page.

## Repeat-stall source-verification routing (2026-11-19)

If a native hourly run again reports **no substantive progress**, the current `work_ticket` invocation must pass `--previous-primary` and `--previous-no-progress` using the **actual** prior retailer and run result. With a genuinely verified, eligible alternate, the next ticket resumes that retailer's ordinary work. If none is yet verified, the ticket now returns `action: verify_secondary_source_only` and names a *different* unfinished retailer as a **source-checking target**, explicitly marked `source_verification_only: true`, `verified_secondary: false`, `publication_authorized: false`, and `gmail_authorized: false`. It does **not** claim a valid local edition, cash price, inventory, changed deal or safe secondary. The next deliverable is an actual matching item-bearing original page/grid or an exact source/region/reader blocker. Follow the fixed official-first catalog for this one target, switch readers after at most two unproductive visits, and never treat source verification alone as substantive durable assessment progress. Do not deep-research more than two retailers.

This repairs a **planner deadlock**, not the missing live collector: all eight profile configs still have `collector = []`. A task without real readable, source-quoted product evidence cannot manufacture a valid advertised-fact file or send an alert. An unverified page, static source heading, task prompt edit, or repeated no-progress result is not a new bargain. The first actually verified offer batch should go immediately through `advertised_facts`, manual privacy review and create-only pinned digest; preserve independent omission, baseline/value and quality gates.

## Efficient run contract

Every run checks CURRENT task instructions, private checkpoint, canonical main SHA, current source catalog and changed retailer source/edition. On a verified unchanged main SHA, reuse the previous privately recorded policy reading rather than refetching 20 unchanged docs; re-read the exact changed policies on SHA change or specific ambiguity. This does not waive source freshness, baseline history, immutable assessment lookup, Gmail Sent reconciliation or delivery gates. Do not let static documentation consume the execution before any actual source facts are inspected.

Only actual durable reviewed item facts, a real baseline/value outcome, executable quality results, verified publication or verified recipient Sent outcome count as substantive progress. A landing page, repeated navigation, preflight/help, task prompt repair or checkpoint increment alone does not. Always report incomplete until the retailer genuinely passes all gates.
