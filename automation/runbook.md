# Grocery Flyer Watcher — runtime-neutral operating contract

This public runbook applies equally to ChatGPT, another coding agent, or a VM collector.
Private scheduler/contact configuration is not part of the public contract.
Canonical repository: `MikuMikuMe/grocery-flyer-watcher` (stable ID `1435089073`).
The in-place rename is complete; resolve this ID to follow any future name changes.

## Profiles and discovery

1. Read `config/profiles.toml`, then EVERY listed profile and optional policy. The registry
   currently enables Metro and Shoppers Drug Mart in Kingston, Ontario. Derive market,
   retailer, timezone and sources from each profile, not hard-coded city/store assumptions.
   Profile paths in the registry are repository-root-relative. See `docs/MULTI_PROFILE.md`.
2. Process profiles independently. Unchanged Metro offers, a source outage or a failed
   delivery must not prevent checking Shoppers, and vice versa. Keep per-profile errors
   private and continue useful independent work; never call a failed source check unchanged.
3. Inspect the configured official selected-store flyer first. Search the retailer,
   city, region, this week, next week and explicit upcoming dates. Cross-check reliable
   independent flyer archives as well as Flipp/reebee; do not rely on Flipp alone.
4. Verify actual page images/product grids, region, valid dates, prices, weights,
   cuts, pack quantities and restrictions. A future-dated title recycling old images
   is not a preview. Verify item/event dates as well as overall flyer validity.
   Never invent prices, editions or successful source checks.

## Analysis and publication

5. Rank roughly 5-10 worthwhile deals per changed retailer when supported by evidence,
   with cost per kg/lb/piece, shelf life, package sizes, loyalty/quantity limits and
   matching nearby alternatives. Do not pad a weak flyer to hit a quota. Separate
   must-buy, conditional and weak deals, with clean sources and expiry dates.
6. Apply `docs/SHOPPERS.md` to Shoppers: check household, groceries, personal-care and
   beauty value; distinguish checkout price from PC Optimum rewards/redemption; verify
   membership, spend thresholds, exclusions, multi-buys and short promotional windows.
   Do not assume personal offers, points balances, eligibility or stacking.
7. Compare against the matching retailer/market/period and public history. A different
   mirror-site edition ID or editorial wording alone is not a new deal. Keep current
   and preview editions distinct. Preserve source-backed offer labels across runs.
8. Use the registry's baseline and report destinations. Metro retains `data/latest.json`
   and its historical reports; Shoppers uses `data/shoppers-drug-mart/latest.json` and
   `reports/shoppers-drug-mart/`. Never overwrite one retailer with another. Standalone
   runs use scoped `public/` archives; inspect those too when checking or migrating.
9. No Shoppers snapshot is created during configuration. On its first verified check,
   publish the baseline and one clearly labelled first-coverage digest, without falsely
   claiming the edition is newly published. Then apply normal update-only rules.
   Adding Shoppers must not resend the intentionally initialized Metro baseline.
10. Commit verified public JSON/reports and non-sensitive instruction/config changes.
    Validate and review the exact staged paths, then verify commit/push success.
    Never publish contacts, credentials, private state/config, message IDs, personal
    postal codes, exact personal location or delivery logs. Privacy checks are guardrails.

## Private delivery and retries

11. Publication and delivery are distinct states. An unchanged public snapshot must NOT
    discard a previously attempted but failed delivery. Check private state/Sent history
    and retry pending verified digests safely. A genuinely unchanged, already-handled
    edition produces no mail, ChatGPT notification or public commit.
12. Prefer separate retailer-labelled digests with stable retailer/market/period/content
    identifiers, excluding mirror IDs and editorial changes. A Metro message must never
    count as evidence that a Shoppers digest was sent. Test emails do not count as real
    flyer delivery. Verify transport outcomes; acceptance is not proof of inbox receipt.
13. ChatGPT uses its private connected Gmail account and private recipient configuration.
    A VM uses separately configured SMTP/other delivery. Never assume ChatGPT OAuth
    transfers to a VM, and never copy private task prompts into the public repository.
14. Only an explicit user request authorizes a delivery TEST. Do not send tests or
    setup-only announcements by email, and do not alter flyer baselines for test delivery.

## Runtime independence

Read `docs/PORTABILITY.md` and `docs/MULTI_PROFILE.md` for the collector contract, CLI,
state migration and VM setup. `AGENTS.md` is the handoff for other coding agents.
The existing CLI processes one profile at a time; it does not directly parse the registry.
For a shared Git checkout run profiles sequentially, with private state outside it.
Only one scheduler owns a profile at a time. Keep the existing schedule until an explicit
cutover; do not silently start another scheduler when adding a retailer.
