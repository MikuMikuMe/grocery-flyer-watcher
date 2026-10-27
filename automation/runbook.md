# Grocery Flyer Watch — runtime-neutral operating contract

This public runbook applies equally to ChatGPT, another coding agent, or a VM collector.
Private scheduler/contact configuration is not part of the public contract.

## Profile and discovery

1. Read `config/watch.toml` (or the operator's private equivalent): market, retailer,
   timezone and source URLs. Do not assume Kingston, Metro or any fixed store ID.
   The shipped public profile currently selects Metro in Kingston, Ontario.
2. Inspect the configured official selected-store flyer first. Search the retailer,
   city, region, this week, next week and explicit upcoming dates. Cross-check reliable
   independent flyer archives as well as Flipp/reebee; do not rely on Flipp alone.
3. Verify the actual page images/product grid, region, valid dates, prices, weights,
   cuts, pack quantities and restrictions. A future-dated page title recycling old
   images is not a verified preview. Distinguish future prices from active prices.
4. Source failures are failures, not evidence of no change. Never invent prices or
   claim a successful check without actual source inspection.

## Analysis and publication

5. Rank roughly 5-10 genuinely worthwhile deals with cost per kg/lb/piece, shelf life,
   pack sizes, loyalty/quantity limits and matching nearby alternatives when verified.
   Separate must-buy, conditional and weak deals. Keep source links and expiry dates.
6. Compare against the matching market/retailer and validity period, including prior
   public reports and `public/` edition archives. The historical `data/latest.json`
   remains a legacy baseline. A different source's edition ID alone is not a new deal.
7. Publish only verified changes: validated public JSON and a dated/source-linked report.
   ChatGPT may keep updating `data/latest.json` plus `reports/`; the standalone runner
   writes namespaced `public/` archives. Read both when migrating or checking history.
   Synchronize non-sensitive instruction/code changes to this repository as well.
8. Do not stage private state, real config, credentials, contact addresses, message IDs,
   personal postal codes or raw delivery logs. Validate before publication and verify
   the commit/push outcome. Automated privacy checks do not replace human/agent review.

## Private delivery and retries

9. Publication and delivery are distinct states. An unchanged public snapshot must NOT
   discard a previously failed delivery. Check private delivery state/Sent history and
   retry a pending verified digest safely. For a genuinely unchanged, already-delivered
   edition, stay silent: no mail, ChatGPT notification or public commit.
10. ChatGPT uses its private connected Gmail account and private recipient configuration.
    A VM uses a separately configured SMTP/other adapter. Never assume a ChatGPT OAuth
    connection is available outside ChatGPT, and never publish the private task prompt.
11. Use a stable retailer/market/period/content fingerprint, excluding source mirror IDs
    and editorial changes. Confirm publication and transport acceptance before claiming
    success. SMTP acceptance is not proof of inbox receipt; crash retries can duplicate.
12. A user-requested delivery test is separate: label it TEST and do not change flyer
    baselines or archive test delivery data publicly. Do not send tests routinely.

## Runtime independence

Read `docs/PORTABILITY.md` for the executable JSON collector contract, CLI, state migration,
Git/SMTP adapters and cron/systemd setup. `AGENTS.md` is the handoff for other coding agents.
Only one scheduler owns a profile at a time; preserve/import handled state at cutover.
The existing ChatGPT schedule remains active until an explicit migration is requested.
