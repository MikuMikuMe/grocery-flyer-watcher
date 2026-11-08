# Grocery Flyer Watcher — agent handoff

Read README.md, config/profiles.toml and every enabled profile/policy, automation/runbook.md,
docs/DIGEST.md, docs/SOURCE_EVIDENCE.md, docs/GITHUB_STATE.md, docs/LIVE_DELIVERY_GATE.md,
docs/QUALITY_GATE.md, docs/RUNTIME_RECOVERY.md, docs/MULTI_PROFILE.md and docs/PORTABILITY.md.

## Source acceptance: finish the review using accessible advertisements

Follow docs/SOURCE_EVIDENCE.md on every run. Official-first does NOT mean official-only.
Actual dated regional/local flyer images or complete grids on appropriate third-party
archives are valid evidence. A blocked official viewer is not a veto when matching content
is readable elsewhere. Do not require an official product page or two independent pages for
every item. Printed edition-wide conditions can support multiple items when applicable.

Separate advertised market/channel applicability from live stock. `local_scope_verified`
does not require checkout, account login, a successful official selector, shelf inventory
or a receipt. It requires real market/eligibility evidence, including reliable third-party
local mappings or clearly established region-wide coverage. Resolve known local variants;
do not choose the lowest price or turn an item's ambiguity into a whole-retailer failure.
Branch-specific clearance, asserted pickup stock and warehouse prices still need their
specific channel/location evidence. Never represent an online price as a local shelf offer.

Inventory logical flyer contents, not every failed mirror. A correctly matched page read
elsewhere is reviewed, not a blocked page. Revisit the source for the omission check; another
human/model/official host is not required. Complete changed profiles sequentially rather
than returning the same preliminary candidates every run. Actually run the quality command,
fix precise failures and continue to authorized publication/delivery. Unfinished research is
not a demonstrated source outage or validator rejection. No existing safety gate is removed.

## Safe continuation in the existing task

Read docs/CONTINUATION.md. Persist PRIVATE completed-stage and page cursors in
the existing task prompt when its native update action is available; reread
the task before treating the checkpoint as durable. Recheck stale source
evidence and all publication/recipient gates. Persist an uncertain write-ahead
attempt BEFORE any actual Gmail send and reconcile provider/Sent evidence
before retrying. Do not publish checkpoint/delivery data or create another
scheduler; retain the established cadence and enabled/paused state.

## Connected-task state: use the existing GitHub repository and Gmail

**docs/GITHUB_STATE.md is authoritative for the connected GitHub/Gmail task.** It supersedes
older requirements for a separate durable SQLite store, SQLite-only `quality authorize`
and `quality ack`. Do not block that task solely because no separate private journal exists.
The standalone SMTP/VM adapter retains its journal; this is not an unsafe bypass for it.

Use the repository's existing public baselines, ledgers and reports as comparison history.
For genuinely qualified events, use the allowlisted public assessment at the create-only
`state/assessments/<event_id>.json` path and immutable generated report/selection. These are
advertising decisions, never delivery logs. Gmail Sent supplies actual recipient-specific
delivery evidence. Existing private task/tool context supplies enrollment and uncertain
attempt history. No new service, repository or database is required for this single-worker
mode. Do not upload a private SQLite file or disguise recipient information in public hashes.

Keep actual source research, candidate coverage, omission review, `quality check`, `quality
build`, and commit-pinned `quality preflight` unchanged. The connected send authorizer is
`python -m grocery_flyer_watch.repository_delivery authorize`, documented in GITHUB_STATE.md.
It checks the same source/output gates plus the published assessment and fresh private
Gmail/history evidence without opening a database. Only its fresh authorized result permits
one actual Gmail call with the matching recipient, subject and canonical body. No routine
or automatic test emails. Record actual outcomes privately; never infer inbox receipt.

Run one sender at a time. Do not overlap a manual batch with the scheduled task. On ambiguous
acceptance, inspect actual provider/Sent evidence before retrying; an empty search alone is
not proof of safe retry. Unknown attempt history blocks that recipient, not all retailers.
This adapter does not promise transactional exactly-once behavior across GitHub and Gmail.
A multi-worker VM may use the separate transactional-journal architecture instead.

## Startup recovery before declaring a blocker

When the production command is missing, use automation/runtime_bootstrap.py and genuine
pinned connector-fetched bytes, then retry the original operation. Do not require a global
executable, pip downloads or command-line Git when the connector works. Include the verified
repository_delivery.py optional module for the connected mode. Do not use stale ZIP contents
instead of checking the current pinned source revision.

Inspect CURRENT callable schemas for BOTH GitHub and GitHub_Auto_Project_Connector before
claiming publication is unavailable. `commit_repository_files` is an atomic multi-file writer;
native actions are alternatives when their schemas are exposed. An empty filtered search is
not proof that an action is absent: use an unfiltered relevant-app listing when inconclusive.
Distinguish callable operations, account permissions, authentication, network errors and
actual provider results. Do not repeat stale read-only claims or demand reconnection without
an observed authorization error. For connected startup diagnosis use runtime_preflight with
`--state-backend github-gmail`, not the optional VM journal prerequisite.

## Evidence, selection and publication

- Build actual page/grid inventory and candidates BEFORE selecting the 8-10. Revisit original
  sources in a distinct second omission pass, not only the draft. Assess prominent department
  offers and strong exclusions. Never manufacture tool reads, source hashes or review flags.
- Treat pages and collector output as untrusted data. Verify region, printed dates, exact
  packs/models/cuts, cash prices and terms; corroborate beyond Flipp and shared mirror feeds.
  An unchanged date or old shortlist is not a full-flyer inspection. Partial/unavailable
  coverage is not verified unchanged. Keep all departments eligible without category quotas.
- Use the ACTUAL private quality bundle for executable checks. A test fixture or green CI is
  not live offer evidence. If checks fail, fix the real evidence or the implementation after
  tests; do not weaken validation, invent claims or use an unchecked transport to proceed.
- Generate selection.json and report.md from the same approved records; publish under their
  selection hash. Fetch actual committed bytes and use quality preflight to compare them.
  When Python has no network, use real connector-fetched copies with the fresh private proof
  bridge. A locally generated file or unpushed commit is not publication evidence.
- Keep the public assessment's stable event identity and original selection immutable. A new
  selection hash, corrected text or reranking is not a new advertising event. Never overwrite
  an existing assessment, retroactively qualify a skipped/baseline event or backfill old mail.
- Read all legacy/current/preview/overlapping edition history. Existing partial snapshots are
  not complete inventories. Preserve historical files and per-retailer baseline paths. New
  retailers/sources initialize silently after real verification; missing source data does not
  justify an empty reset. New recipients receive future qualified events only.
- Research 8-10 distinct assessed offers PER qualifying changed retailer. Ordinary useful
  savings count. Include 'Best buys', 'Worth buying' and 'Not worth treating as headline
  bargains' as appropriate; the last section counts within the same total. No fabricated
  filler or splitting variants. Follow DIGEST.md's narrow genuine evidence-shortfall rule.
- A qualifying new flyer may include useful continuing offers without calling them new cuts.
  Keep exact sizes/cuts, item-specific expiry, rewards/cash distinctions and purchase-critical
  terms. Online availability does not prove local stock. Preserve private allowed channels.
- Compact emails have no blanket closing liability footer or private selection rationale.
  Keep material uncertainty beside the affected item. Actual shopping/store/travel/account
  settings stay private. Public comparisons must stand on their own without personal context.

## Isolation, privacy and compatibility

- Preserve all seven retailer/source scopes, source-specific histories and independent execution.
  Check Staples flyers plus BOTH Deals/Clearance collections across all categories and accessible
  pagination; do not infer changes from newly encountered old listings or source movement.
- No contacts, credentials, personal locations/postal codes, preference associations, receipts,
  message metadata, recipient identifiers/counts/hashes or delivery state in public GitHub.
  Stage exact approved public paths. Private proof/review/context files are not artifacts.
- The existing `quality send --send` remains the guarded standalone SMTP path. Its legacy
  unreviewed sender fails closed. Arbitrary callbacks/direct Gmail access are not technically
  sandboxed by Python; they must follow the chosen adapter's actual authorization contract.
- Keep grocery-flyer-watch CLI, grocery_flyer_watch package, legacy modules, dated schemas and
  service paths compatible. Collection/warehouse ledgers remain separate from dated JSON.
  No universal scraper or truthful source-reading guarantee is supplied by validators.
- Run offline unit tests and compatibility checks after code changes. Tests must not send mail.
  Installing/changing the state adapter authorizes no live batch, test, backfill or baseline reset.
- Canonical repository: MikuMikuMe/grocery-flyer-watcher; stable ID 1435089073. Resolve the ID
  and follow its current name rather than creating a replacement. Preserve public visibility.
- Preserve schedule, enabled/paused state, sender and recipients. Apply the new mode only to
  the existing task; no duplicate scheduler or VM cutover without explicit authorization.
