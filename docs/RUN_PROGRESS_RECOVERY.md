# Progress-first source research and failover

This applies to the existing Kingston Grocery Flyer Watcher. Preserve the single native task,
its actual **three-hour** cadence, enabled state, private delivery context and the full
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
