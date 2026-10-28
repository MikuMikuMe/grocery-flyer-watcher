# Grocery Flyer Watcher — runtime-neutral operating contract

This public runbook applies equally to ChatGPT, another coding agent, or a VM collector.
Private scheduler/contact configuration is not part of the public contract.
Canonical repository: `MikuMikuMe/grocery-flyer-watcher` (stable ID `1435089073`).
The in-place rename is complete; resolve this ID to follow any future name changes.

## Mandatory notification rule

The schedule controls **source checks, not email frequency**. A deal email requires BOTH:

1. A verified new flyer edition or material advertised-offer change relative to an
   established baseline for the same retailer and market.
2. At least one genuinely worthwhile, source-verified deal found in that change.

For Staples, eligible monitored sources include the official flyer, Deals Centre and
Clearance Centre, across ALL categories. A verified new/material collection offer can
qualify without appearing in a flyer. See `docs/STAPLES.md` for source baselines,
undated-observation handling and cross-source duplicate prevention. Other retailer
scopes are unchanged; a source being newly added does not itself satisfy either gate.

A new edition or changed collection with no worthwhile bargains does not qualify.
Do not pad a weak report or treat an advertised sale label as proof of value. Send once
per qualifying change per authorized recipient, after successful publication and private
recipient-specific duplicate checking. Recheck actual validity and eligibility before
sending. These rules supersede older first-coverage and Staples flyer-only instructions.

NO emails for routine checks, unchanged/weak offers, first-run initialization, new source,
retailer or recipient setup, source failures, status reports, or configuration changes.
A previously advertised event starting, an unchanged offer being re-ranked or a product
moving between source pages is not an identified offer change. No no-change/weak-deal
emails. Routine ChatGPT output is suppressed when no profile qualifies. A persistent
blocker requiring action may be reported privately in ChatGPT, never as a status/error
email. A fresh explicit user request is required for a separate TEST email.

## Profiles and discovery

1. Read `config/profiles.toml`, then EVERY listed profile and optional policy. The registry
   enables Metro, Shoppers Drug Mart, Rexall and Staples in Kingston, Ontario. Derive market,
   retailer, timezone and sources from the profile. Registry paths are repository-root-relative.
   See `docs/MULTI_PROFILE.md`. Keep personal home-store selection in private runtime settings.
2. Process profiles independently. An unchanged/weak source, an outage or a failed delivery
   must not prevent checking another profile. Continue useful independent work; never call
   a failed source check unchanged. Keep failures and incomplete coverage private.
3. Inspect the configured official selected-store sources first. Search retailer, city,
   region, current/next week and exact dates; cross-check independent regional archives
   and Flipp/reebee. Do not rely on Flipp alone. For Staples inspect BOTH configured
   Deals/Clearance Centre pages as well as flyers; do not apply a category allowlist.
4. Verify actual images/product grids, region, dates, prices, sizes, counts and restrictions.
   A future-dated title recycling old images is not a preview. Verify item/event dates
   as well as the overall flyer period. Never invent successful checks or validity dates.
   Apply privately selected home-store context before pickup/stock checks; a website's
   default store or national online inventory is not evidence of stock at that branch.

## Analysis and publication

5. Rank genuinely worthwhile changed offers using suitable unit prices/specifications,
   package sizes, shelf life, eligibility and verified equivalent alternatives. Aim for
   5-10 highlights only when warranted; one excellent deal can qualify and zero means
   no email. Report must-buy, conditional and weak offers with clean sources and validity.
   A shortlist target limits presentation, not the categories eligible for discovery.
6. Apply `docs/SHOPPERS.md`, `docs/REXALL.md` and `docs/STAPLES.md` as appropriate. Separate
   each retailer's cash price from rewards, redemption and financing; verify current terms,
   membership, minimum spend, coupons, exclusions, bundle quantities and short event dates.
   Do not assume targeted offers, points balances, restricted eligibility or stacking.
   Staples categories are unrestricted: furniture/chairs, cleaning supplies, candy/snacks,
   drinks, household goods and electronics are examples, not a closed list. Verify exact
   models/variants, condition, pack sizes, returns, fees and actual purchase channels.
7. Compare matching retailer/market/period history. Mirror IDs, URLs, observation timestamps,
   sorting and editorial wording alone are not changes. Keep current/preview editions and
   overlapping catalogues distinct. Preserve stable product labels and exact SKU/variants.
   For Staples, compare collection offers against separate source observations and deduplicate
   unchanged material offers appearing in multiple collections or flyers. Partial pagination
   or newly visible categories cannot by themselves establish a new promotion.
8. Preserve registry baseline/report destinations. Metro retains `data/latest.json` and its
   reports; Shoppers uses `data/shoppers-drug-mart/latest.json` and its report directory;
   Rexall uses `data/rexall/latest.json`; Staples dated flyers use `data/staples/latest.json`.
   Never replace one retailer/edition with another. Read scoped `public/` archives too.
   Staples undated collection observations use separate source-linked Markdown ledgers under
   `reports/staples/collections/`, as specified in `docs/STAPLES.md`. Do not fabricate flyer
   dates or put incompatible collection records in the dated-flyer JSON schema.
9. Verify and save missing retailer/source baselines SILENTLY: no first-coverage mail or
   routine ChatGPT alert. Existing baselines remain handled. Missing Sent history, adding
   sources, a rename or an algorithm change is not permission to resend. New recipients
   get future qualifying updates only. Record verified weak-deal changes as appropriate
   but mark handled privately without delivery; later re-ranking cannot create a new alert.
   Do not backfill existing catalogues or already-listed collection items as new offers.
10. Commit verified public snapshots/reports and non-sensitive instruction/config changes.
    Validate and review exact public paths and verify commit/push success. A public write
    does not authorize email. Do not commit unchanged records just to refresh a timestamp.
    Never publish contacts, credentials, private state/config, message IDs, personal postal
    codes, personal locations, home-store preference associations, recipient identifiers,
    hashes/counts or delivery logs. Public retail facts are distinct from private preferences.
    Privacy checks are guardrails, not proof that arbitrary text is safe.

## Private delivery and retries

11. Publication and delivery are distinct states. Retry only when private evidence records
    the ORIGINAL qualifying change and good value, the offer remains useful and valid or
    verified upcoming, and that recipient has not received it. Missing Sent history alone
    is insufficient. Do not turn an initialized or weak-deal baseline into pending mail.
    Preserve genuine pending work after public publication without duplicating handled work.
12. Use retailer-labelled subjects with stable content identifiers, excluding mirror IDs,
    observation times and editorial text. Check Sent with the exact intended recipient and
    digest/edition, excluding TEST messages. Delivery to another person or for another
    retailer is not proof of delivery. For Staples, check the same material product offer
    across flyer and collection sources before notifying. Immediately recheck both gates,
    publication, validity and recipient-specific delivery evidence. Transport acceptance
    is not proof of inbox receipt. No mail is sent merely because six hours elapsed.
13. Use private authorized sender/recipient settings. Send each person an individual message,
    without other recipients or private configuration in headers/body. Include only the
    public deal digest and report links. Continue other authorized recipients if one fails;
    retry only recorded unsent recipients, not successful ones. Keep pending state private
    and avoid repeated ChatGPT alerts for recipient-specific retries. A VM needs its own
    delivery credentials and orchestration; ChatGPT OAuth does not transfer automatically.
14. Only an explicit fresh request authorizes TEST delivery. No automatic setup, source-error
    or status mail, no backfills, and no baseline edits for testing. Source/store/category
    configuration changes do not run immediate deal checks, alter schedules or resume a
    paused task. Preserve enabled/paused status unless an operator asks to change it.

## Runtime independence

Read `docs/PORTABILITY.md`, `docs/MULTI_PROFILE.md` and retailer policies for collector
contracts and migration. `AGENTS.md` is the coding-agent handoff. The existing CLI accepts
one dated-flyer profile, not the registry or undated collection observation ledgers.
For a shared Git checkout process profiles sequentially and keep private state outside it.
Only one scheduler owns a profile; changing sources must not start a duplicate scheduler.

The connected task applies the change/value and private-recipient rules. A standalone
SMTP adapter is transport only. A replacement collector/orchestrator must implement
silent initialization, private home-store selection, source-aware comparisons and
recipient-specific decisions. The added collection URLs do not constitute a bundled
collection scraper or automatic undated-offer/value engine in the existing Python CLI.
No actual contacts, private store preference or delivery metadata belong in public examples.
