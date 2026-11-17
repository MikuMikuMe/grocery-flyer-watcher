# Progress-first source research and failover

This applies to the existing Kingston Grocery Flyer Watcher. Preserve the single native task,
its currently configured cadence (hourly after the user's explicit change), enabled state, private delivery context and the full
quality/publication/Gmail safeguards. Do not add an agent, scheduler, collector service,
notification transport or database. This is a *runbook*, not proof that a source or offer was
inspected.

## Why prior runs stalled

As of 2026-11-15, each public profile's `collector = []`: the repository supplies
validated offline workflows but **no live flyer scraper**. Scheduled source reading is
therefore an agent/manual evidence-gathering step. A 20-page Food Basics flyer was viewed
once, but later runs only revisited SmartCanucks /all and /single HTML. Those pages may be
text-accessible while the actual ad graphics are not; navigation was repeatedly mistaken
for progress. A separate indexed offer grid may expose item names and prices while using
another city's store default; without verified Kingston applicability, it is a candidate
source, not Kingston offer proof.

## Mandatory stage-based work and progress check

1. First read the fixed Kingston catalog, current registry, private continuation and the
   actual previous run outcome. Check historical handled editions and source freshness. Pick
   one primary retailer, no more than one secondary (as specified by the private task).
2. First source attempt: official Kingston flyer. If 403, anti-bot, inaccessible graphics
   or unhelpful selector, mark that attempt and switch **immediately** to the next saved
   original-page source, using image-capable inspection where the tool permits. Repeated
   visits to a page *without extracting products* do **not** count as research progress.
3. If original images cannot be read with the available tools, use a verified matching
   *complete* retailer-authored offer grid, not an article or category index. Maintain the
   exact page/department coverage, item size, price, dates, and source provenance. A
   Toronto-default / different-variant grid may be used for leads but **never** asserted
   as Kingston pricing without actual regional matching evidence. If uncertainty remains,
   omit conflicting items while retaining verified ones if the policy permits.
4. Spend the primary retailer's research allocation compiling a broad source-native item
   inventory first (not a hand-picked ten); identify important excluded bargains. Return
   to the same original pages/grid in a separate read for an omission check. Compute only
   actual page/response hashes from the retrieved bytes; never invent read identifiers.
5. Require at least one **substantive** completed unit in each deep-research execution:
   an actual page/group item inventory, a real omission-pass chunk, a successful quality
   check/build, an immutable publication, or a verified recipient outcome. A source tab,
   URL, edition heading, repeated search or navigation alone is **not** such a unit.
6. After two unproductive access attempts on a logical source/reader combination, stop
   reopening it within that run. Try a genuinely different source/mode or mark the precise
   reader limitation. If the same retailer stalled in the preceding run and cannot yield
   a substantive unit now, move to the SECOND retailer within the allowed two-retailer
   cap; use the oldest unfinished viable retailer with an accessible original ad.
   The difficult primary remains `incomplete`/blocked with its actual source cursor.
7. Do not re-inventory previously reviewed pages simply because its source link still
   works. Resume the next missing item/department/omission unit; re-read stale evidence
   when the six-hour quality freshness window requires it. Historical first reads do NOT
   themselves satisfy a current omission review or a new quality authorization.
8. When an edition truly qualifies, run actual source/value gates, the unchanged
   executable quality checks, create-only publication and per-recipient authorization.
   The next run should not stop at a successful preflight or a preliminary shortlist.

## Private checkpoint invariant

Use the exact canonical stage values defined in
`src/grocery_flyer_watch/continuation.py`. The descriptive substage and literal page
cursor belong in `source_cursor`, not the stage enum. A reported 20-page first read
may leave `last_completed=triage` and `next_stage=source_inventory` if a complete item
inventory hasn't actually been compiled. Keep reason (<=230 characters) and next cursor
unit (<=90 characters) within the validator contract. Save with `embed`, then reread
and run `verify_saved_prompt`. Check schedule/enabled equality outside the helper.
**Do not claim a checkpoint was verified if JSON parsing/schema validation fails.**

If source work remains incomplete, state exactly what pages, items or market proofs
are missing. No unverified deal or routine status gets emailed. An interrupted send
remains recipient-specific `uncertain`, never safe to retry by assumption.

## Reliability repair: durable stage progression (2026-11-17)

**Checkpoint first.** At run start retrieve the live task prompt and validate its entire existing checkpoint with the current `continuation.extract` and `validate`. If invalid, report the precise validator code privately; do not silently replace or truncate the checkpoint. After each substantive stage, update only canonical stage fields and bounded cursor values, serialize via `embed`, update the SAME native task prompt with no schedule/enabled arguments, then reread with `peek`. Verify the entire saved state via `verify_saved_prompt` and separately compare the original and new schedule and enabled state. A failed round-trip is an explicit `checkpoint_persistence_blocked` outcome, not successful progress; do not send Gmail. Preserve the original state and investigate schema violations (length limits, duplicate cursor units, invalid enums) before retrying.

**No page-reading loop.** First inventory and separate omission pass are distinct finite stages. A page/group is counted once per pass in the private cursor, with real read references. If a pass is complete, immediately advance to baseline comparison, value assessment and executable quality; do not start another omission pass just because an earlier read is old. Refresh source evidence required by the six-hour quality gate **only for the selected qualifying evidence**; freshness refreshes do not reset the page cursor. If a required source cannot be read twice, record the exact URL/mode and affected units and rotate to the second eligible retailer instead of revisiting navigation.

**Measurable per-run exit.** Every deep-research run must produce at least one of: (a) a completed, evidenced inventory/omission stage with a new stage cursor; (b) a real baseline/value decision; (c) an executed quality check/build with actual output; (d) verified create-only publication; (e) verified per-recipient provider outcome; or (f) a precise blocker plus a DIFFERENT safe next action/retailer. Merely reading 2-3 more previously covered pages or finding a flyer landing is not sufficient. Report `research_incomplete` until the assessment finishes. Never label a platform completed status as retailer completion.

**Applicability.** Apply the Ontario-to-Kingston presumption in `docs/KINGSTON_FLYER_SOURCES.md`; search narrowly for genuine regional exceptions instead of repeatedly blocking generic Ontario editions. Do not relax price, pack, source, baseline, quality, immutable publication, privacy or Gmail gates.


## Executable failover, coverage and retailer rotation (2026-11-17)

The optional, pinned continuation helper now has **four research decisions** in addition to checkpoint validation. They operate on real private observations; none invents a scraper, source read, market proof, inventory, publication, email authorization or a Gmail send. Use the current repository module and keep input JSON/diagnostics outside the public checkout.

**1. Page/grid blocked: choose real alternate evidence, not another navigation pass.**
After an inaccessible original/grid page (do not retry the same failing reader more than twice), run:

    PYTHONPATH=src python -m grocery_flyer_watch.continuation source-failover /private/checkpoint.json \
      --catalog config/kingston_flyer_sources.json --profile walmart \
      --failed-url ACTUAL_GRID_PAGE_URL --attempts 1 \
      --reviewed-original-url ACTUAL_FIXED_CATALOG_ORIGINAL_FLYER_URL \
      --missing-unit grid-page-3 --missing-unit grid-page-4 --missing-unit grid-page-5

Use the **actual** failed URL and review URL from tool/source history; these placeholders are not evidence. When a matching registered original ad was already visually read, the helper proposes extracting the missing *item groups* from those originals. It does **not** label the grid or its unseen pages reviewed. Reconcile a grid's pagination against actual *logical* flyer pages, check editions, extract item names/packs/prices/terms and preserve distinct source-read references. If original scans were not reviewed, it chooses the next unattempted registered flyer source. When none is safe, record exact gaps and rotate to another independently viable retailer.

**2. Decide when logical source coverage is sufficient.**
The private coverage proof (never commit it) must contain exactly these fields:

    {
      "expected_unit_ids": ["logical-page-1", "logical-page-2"],
      "inventory_reads": {"logical-page-1": "ACTUAL_FIRST_READ_REF", "logical-page-2": "ACTUAL_FIRST_READ_REF_2"},
      "omission_reads": {"logical-page-1": "ACTUAL_DISTINCT_REVISIT_REF", "logical-page-2": "ACTUAL_DISTINCT_REVISIT_REF_2"},
      "blocked_unit_ids": [],
      "edition_verified": true, "market_verified": true,
      "allow_partial": false, "partial_note": ""
    }

    PYTHONPATH=src python -m grocery_flyer_watch.continuation coverage /private/coverage-proof.json

Only include truly inspected logical units in the read maps. Values must be distinct actual first/second read references, not invented labels from this example. Do **not** include broken mirrors as separate missing logical units when the same full original page was actually inventoried and revisited elsewhere. If the helper returns prepare_baseline_value_and_quality, proceed to the real matching baseline, value assessment and unchanged review/check/build; no more redundant flyer pagination is needed. If omissions remain, finish them. If actual logical pages are inaccessible, use a matching alternate; the optional partial exception still requires the precise policy disclosure and must pass the **same** executable quality gate.

**3. Rotate after a confirmed source blocker.**
Use results of the current genuine eight-profile eligibility/source triage, not every historical checkpoint link, as the viable IDs:

    PYTHONPATH=src python -m grocery_flyer_watch.continuation rotate /private/checkpoint.json \
      --primary walmart --viable-profile ACTUALLY_VIABLE_OTHER_RETAILER_ID

The helper chooses the oldest unfinished eligible secondary and explicitly excludes handled or recipient-uncertain publication states. Maximum **two** deep-researched retailers in one run. Keep the primary incomplete and retain its cursor; do not erase page observations. If no source is actually viable, report the precise blocker instead of pretending to finish.

**4. Measure outcomes, not checkpoint sequence.**

    PYTHONPATH=src python -m grocery_flyer_watch.continuation outcomes /private/checkpoint.json

The output separates checkpoint-claimed publication/delivery completions from unfinished profiles. These are only *claims until checked* against the immutable pinned GitHub assessment and each recipient's authentic Sent evidence. A higher sequence, more extracted products, green runtime preflight or platform completed status does **not** equal a finished retailer assessment. Do not change recipient safety, source proof validity, selected terms, deduplication or actual send rules.

