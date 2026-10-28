# Grocery Flyer Watcher — runtime-neutral operating contract

This public runbook applies equally to ChatGPT, another coding agent, or a VM collector.
Private scheduler/contact configuration is not part of the public contract.
Canonical repository: `MikuMikuMe/grocery-flyer-watcher` (stable ID `1435089073`).
The in-place rename is complete; resolve this ID to follow any future name changes.

## Mandatory notification rule

The schedule controls **source checks, not email frequency**. A deal email requires BOTH:

1. A verified new flyer edition or material advertised-offer change relative to an
   established baseline for the same retailer and market.
2. At least one genuinely worthwhile, source-verified deal found in that changed flyer.

A new edition with no worthwhile bargains does not qualify. Do not pad a weak report
or treat an advertised sale label as proof of value. Send once per qualifying change
per authorized recipient, after successful publication and private recipient-specific
duplicate checking. Recheck actual offer dates and eligibility before sending.
These rules supersede older first-coverage instructions.

NO emails for routine checks, unchanged flyers, weak flyers, first-run initialization,
new retailer or recipient setup, source failures, status reports, or code/config/repository
changes. A previously advertised event starting or an unchanged offer being re-ranked is
not an identified flyer change. Do not send a no-change or no-good-deals email.
Routine ChatGPT output is also suppressed when no profile qualifies. A persistent blocker
requiring action may be reported privately in ChatGPT, never as a status/error email.
A fresh explicit user request is required for a separate TEST email.

## Profiles and discovery

1. Read `config/profiles.toml`, then EVERY listed profile and optional policy. The registry
   currently enables Metro, Shoppers Drug Mart, Rexall and Staples in Kingston, Ontario. Derive
   market, retailer, timezone and sources from each profile, not hard-coded city/store assumptions.
   Profile paths in the registry are repository-root-relative. See `docs/MULTI_PROFILE.md`.
2. Process profiles independently. Unchanged offers, no good deals, a source outage or a
   failed delivery must not prevent checking another profile. Keep errors private and
   continue useful independent work; never call a failed source check unchanged.
3. Inspect the configured official selected-store flyer first. Search the retailer,
   city, region, this week, next week and explicit upcoming dates. Cross-check reliable
   independent flyer archives as well as Flipp/reebee; do not rely on Flipp alone.
4. Verify actual page images/product grids, region, valid dates, prices, weights,
   cuts, pack quantities and restrictions. A future-dated title recycling old images
   is not a preview. Verify item/event dates as well as overall flyer validity.
   Never invent prices, editions or successful source checks.

## Analysis and publication

5. Rank the genuinely worthwhile deals per changed retailer with cost per kg/lb/piece,
   shelf life, package sizes, loyalty/quantity limits and matching nearby alternatives.
   Aim for 5-10 only when supported by evidence; one excellent deal can qualify, and
   zero good deals means NO EMAIL. Separate must-buy, conditional and weak promotions.
   Include clean sources, applicable conditions and exact start/expiry dates.
6. Apply `docs/SHOPPERS.md` to Shoppers and `docs/REXALL.md` to Rexall. Check household,
   groceries, personal-care and beauty value; distinguish cash prices from each retailer's
   rewards/redemption. Verify current terms, membership, spend thresholds, exclusions,
   multi-buys and short promotional windows. Do not assume personal offers, points balances,
   age/occupation eligibility or stacking, or transfer one retailer's reward rules to another.
   Apply `docs/STAPLES.md` to Staples: include office/school supplies, consumables,
   household products, electronics and furniture when genuinely worthwhile. Match exact
   models/SKUs, configurations, pack sizes and product condition. Verify coupons, account
   eligibility, full cash price versus rebates/gift cards/financing, shipping and Kingston
   pickup/store applicability. Keep weekly flyers and overlapping catalogues/events distinct.
7. Compare against the matching retailer/market/period and public history. A different
   mirror-site edition ID or editorial wording alone is not a new deal. Keep current
   and preview editions distinct. Preserve source-backed offer labels across runs.
8. Use the registry's baseline and report destinations. Metro retains `data/latest.json`
   and its historical reports; Shoppers uses `data/shoppers-drug-mart/latest.json` and
   `reports/shoppers-drug-mart/`; Rexall uses `data/rexall/latest.json` and `reports/rexall/`;
   Staples uses `data/staples/latest.json` and `reports/staples/`. Never overwrite one
   retailer with another. Standalone runs use scoped `public/` archives; inspect those
   too when checking or migrating.
9. If no reliable baseline exists, verify and save an initial baseline SILENTLY. This
   applies to every new profile, including Staples: no first-coverage email or routine
   ChatGPT alert. Baseline creation is not evidence of a change. Existing baselines
   remain handled; missing Sent history, an algorithm change or a rename is not a
   reason to resend them. Adding a recipient does not authorize old-digest backfills;
   new recipients receive future qualifying updates only. If a verified change has no
   worthwhile deals, record the public change as appropriate and mark it handled privately
   without delivery. Do not later email it merely because unchanged offers received
   different rankings. Do not backfill already-published catalogues as new flyer changes.
10. Commit verified public JSON/reports and non-sensitive instruction/config changes.
    Validate and review the exact staged paths, then verify commit/push success.
    Public archive changes do not automatically authorize a notification. Unchanged
    offers require no public data commit. Never publish contacts, credentials, private
    state/config, message IDs, personal postal codes, exact personal location, recipient
    identifiers/hashes/counts or delivery logs. Privacy checks are guardrails, not proof
    that free text contains no private data.

## Private delivery and retries

11. Publication and delivery are distinct states. Retry a failed delivery only when
    private state/run evidence records the ORIGINAL qualifying change and worthwhile
    deals, the offers remain valid or upcoming and useful, and the digest has not been
    sent to that recipient. Missing Sent history alone is insufficient. Never turn a
    silently initialized or weak-deal baseline into pending mail. Pending work must
    survive a public commit, but already-handled delivery must not produce repeat mail.
12. Prefer separate retailer-labelled digests with stable retailer/market/period/content
    identifiers, excluding mirror IDs and editorial changes. Check Sent history using
    the exact intended recipient and digest/edition evidence, excluding TEST messages.
    Delivery to one recipient is not proof of delivery to another, and a message for
    one retailer never satisfies another retailer's deduplication. Immediately before
    each send, check both required gates, publication, offer validity and recipient-specific
    delivery evidence. Confirm each transport outcome independently; acceptance is not
    proof of inbox receipt. No email is sent merely because six hours elapsed.
13. ChatGPT uses its private connected Gmail account and private authorized recipient
    list. Send each recipient an individual message, without other recipients in the
    message headers or body. Include only the public deal digest and public report links,
    not private configuration or personal context. Continue other authorized recipients
    if one send fails; retry only recorded failed/unsent recipients, never those already
    successful. Keep pending recipient state private and avoid duplicate ChatGPT alerts
    on recipient-specific retries. A VM needs separately configured delivery and the same
    recipient-specific orchestration; ChatGPT OAuth does not transfer automatically.
14. Only a fresh explicit user request authorizes a delivery TEST. Do not send tests,
    setup-only announcements or failure/status reports automatically by email. Recipient
    changes do not trigger checks, mail, old-digest backfills or a new schedule. Do not
    alter flyer baselines or archive private delivery records for test messages.

## Runtime independence

Read `docs/PORTABILITY.md` and `docs/MULTI_PROFILE.md` for the collector contract, CLI,
state migration and VM setup. `AGENTS.md` is the handoff for other coding agents.
The existing CLI processes one profile at a time; it does not directly parse the registry.
For a shared Git checkout run profiles sequentially, with private state outside it.
Only one scheduler owns a profile at a time. Keep the existing schedule until an explicit
cutover; do not silently start another scheduler when adding a retailer or recipient.

The connected scheduled task applies the two-condition notification rule and private
recipient orchestration above. A standalone SMTP adapter is only a transport, not evidence
of a verified change, good value or recipient-specific duplicate/retry handling. Before
migration, the collector/orchestrator must enforce the same gate, silently seed initial
baselines and retain private skipped/pending decisions separately for each recipient.
This documentation update does not add automatic deal-value assessment or a new
recipient-state adapter to the Python CLI. No actual recipient list, contact information
or delivery metadata belongs in public examples, commits or reports.
