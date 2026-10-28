# Rexall monitoring policy

Apply this policy to the Rexall entry in `config/profiles.toml`, together with the
mandatory notification gate in `automation/runbook.md`. Metro and Shoppers remain enabled.
The shipped profile is Kingston, Ontario; moving cities requires matching source URLs.

## Verify the correct flyer and local applicability

Start with the official Rexall flyer and select Kingston, Ontario. The configured
store reference is a public Kingston retail location, not the operator's personal
location or a requirement to shop only at that store. Verify store participation;
do not assume one store's stock or a store-specific price applies throughout the city.
Search Rexall + configured city/region + this week / next week + exact dates, and
cross-check the Ontario edition using independent archives and local Flipp listings.
SmartCanucks flyer/deals subdomains count as one source family, not independent proof.

The source URLs are discovery entrypoints only. Dynamic content, cached/expired archive
pages and blocked pages do not verify a current offer. Inspect actual flyer images or
product grids and their printed dates, package sizes, cash prices, fine print and region.
Never accept a future-dated headline that reuses old images. Verify weekly flyers,
supplements and short promotions separately, retaining each validity period in history.
A source failure is not a no-change finding. Do not invent a snapshot during setup.

## Analyze value and conditions

Prioritize useful grocery, household/paper/cleaning, personal-care and beauty deals.
Compare equivalent products with the other enabled retailers and verified local
competitors. Match brand, size/count, sheets/plies, concentration and purchase terms.
Do not encourage medication or supplement purchases merely because a price is low,
or infer medical suitability from an advertisement.

Show cash payable separately from Be Well rewards, coupons or redemption value.
Verify the current program and event terms before any points conversion; do not
hard-code a rewards exchange rate or assume the program's conditions remain unchanged.
Do not carry over Shoppers' PC Optimum assumptions to Rexall.

For each deal, verify member/app/loaded/targeted requirements, minimum spend, eligible
products, purchase limits, coupon requirements, excluded products, multi-buy quantities,
online-versus-store pricing and item/event start and end dates. Do not assume eligibility
for age- or occupation-restricted discounts, a points balance, targeted offers or stacking.
A conditional rewards-adjusted value must remain clearly labelled; it is not the cash
price and does not justify unnecessary spending to reach a threshold.

`price_cad` is the applicable cash purchase price, never a net-after-points number.
Put necessary bundle quantities, event dates and eligibility conditions in `restrictions`.
Explain conditional value in `why` and the report. Rewards-only events with no verified
item prices can be contextual notes but must not become zero-price products or invented
flyer changes. An already-recorded promotion beginning does not authorize another email.

## Isolated state and silent first baseline

Use `data/rexall/latest.json`, `reports/rexall/` and this profile's private state file.
Never overwrite another retailer's baseline or treat its sent digest as Rexall delivery.
The standalone archive and event keys remain retailer/market-scoped.

At the first successful verification, establish Rexall's baseline SILENTLY. There is
no first-coverage email, setup email or routine ChatGPT alert. No initial flyer prices
are supplied by this configuration change. Adding Rexall must not resend Metro or
Shoppers offers or change their baselines, checking schedule or private delivery settings.

After initialization, email only when BOTH an actual flyer/offer change relative to
that baseline is verified AND at least one genuinely worthwhile deal is found. Confirm
publication, current/upcoming eligibility and private duplicate checks before delivery.
No worthwhile deals, unchanged flyers, source failures and routine checks produce no mail.
Only recorded previously qualifying unsent work can be retried; missing Sent history
alone does not create pending work. Follow the full runbook for skipped and pending state.

## Runtime and public sources

The existing single-profile CLI accepts `config/rexall.toml`; the registry is read by
an orchestrator/agent, not passed to `--config`. A VM still needs its own verified
collector, private credentials, silent baseline seeding and change/value gate. This
addition neither deploys a VM nor starts another scheduler.

Discovery entrypoints:

- Official flyer: https://www.rexall.ca/eflyer
- Official Kingston store reference: https://www.rexall.ca/storelocator/store/1529
- Official promotions and conditions: https://www.rexall.ca/pharmacy-promotions
- SmartCanucks flyer archive: https://flyers.smartcanucks.ca/rexall-canada
- SmartCanucks deal archive: https://deals.smartcanucks.ca/rexall-canada
- Ontario edition selection: https://www.flyers-on-line.com/rexall
- Kingston flyer discovery: https://flipp.com/en-ca/kingston-on
