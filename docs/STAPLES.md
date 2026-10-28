# Staples Canada monitoring policy

Apply this policy to the Staples entry in `config/profiles.toml`, together with the
mandatory notification and private-recipient rules in `automation/runbook.md`.
Metro, Shoppers Drug Mart and Rexall remain enabled. The current market is Kingston,
Ontario; changing cities requires updating the matching store/source configuration.

## Source selection and edition verification

Start with Staples Canada's official flyer hub and select the Kingston market/store.
Official Kingston store pages are source references, not personal locations, preferred
stores or proof that either store has a particular product in stock. Do not trust the
flyer hub's default store selection. Do not substitute Staples US prices, a Quebec-only
Bureau en Gros offer or a business-account price for an eligible Ontario retail offer.
National offers require confirmation they apply to the configured market.

Search the configured retailer/city/region with current and next-week dates; inspect
actual flyer images or product grids. Cross-check independent Canadian flyer archives
and local listings, not just Flipp. All Staples subdomains are one first-party source
family, not multiple independent confirmations. Archive headings, cached snippets or
a date change with recycled imagery are not evidence of a new edition. Source access
failures are not successful no-change checks.

Track weekly flyers, dated event supplements, business/member booklets and gift guides
separately using actual identities and validity periods. Keep current/preview editions
and overlapping catalogues in history so switching between them cannot create repeat
alerts. An evergreen product page, repeated catalogue, renamed headline or old offer
becoming active does not by itself qualify as a flyer change. Product pages may verify
a flyer's model/terms, but this profile is not an unrestricted product-price alert.
When first enabling this profile, record already-present verified editions silently;
older existing booklets discovered later must not be misrepresented as newly published.

## Useful deals and like-for-like comparison

Prioritize genuinely good-value stationery, paper, ink/toner, school/office supplies,
household/cleaning products, electronics/accessories, storage and office furniture.
There is no requirement to buy or recommend a category merely because it appears in
an advertisement. Aim for 5-10 good offers only when warranted; one excellent deal
can qualify, while zero worthwhile deals means no email.

For electronics, compare exact manufacturer model/SKU and configuration: processor,
RAM, storage, display and included accessories where relevant. Distinguish new, used,
refurbished and open-box stock, seller, warranty and return restrictions; do not present
unmatched configurations as equivalent. Verify compatibility rather than assuming a
recipient owns a compatible device. Do not put personal device details in public reports.

For consumables, compare pack count, sheet count, size and specifications. For ink/toner,
match cartridge compatibility and standard/high-yield capacity, and identify original
versus third-party supplies. For furniture, match model, included components, assembly,
delivery fees and warranty where relevant. Do not use a high suggested retail price or
advertised percentage as sufficient proof of value. Compare verified equivalent offers
at local/Canadian competitors such as Best Buy, Canada Computers, Walmart or the other
enabled retailers when relevant and accessible; never fabricate competitor prices.

## Cash prices, eligibility and costs

Verify item-level dates, quantity limits, required coupon/code, minimum spend, membership
or account eligibility, bundle quantity, exclusions, online-only versus in-store terms,
Kingston pickup availability and delivery charges. Do not claim free shipping, available
stock, eligible memberships or coupon stacking without current supporting evidence.
Publicly advertised account-specific or targeted offers remain conditional, not universal.
Do not collect a recipient's personal address or account data to evaluate a public flyer.

Show cash payable separately from later gift cards, rebates, rewards, trade-in value or
financing instalments. Do not subtract a future reward from the headline cash price or
call it an instant discount. Do not present a monthly instalment as the full product
price; show mandatory contract/subscription commitments separately when relevant.
Do not encourage extra spending just to reach a reward or coupon threshold.

The snapshot's `price_cad` is the verified cash merchandise price for the represented
unit/package, never a net-after-rewards value. Use `restrictions` for required bundle
quantity, exact applicable dates, coupons, eligible accounts, item condition, availability
limits and mandatory fees; explain total purchase cost in the report. The present schema
has no separate structured SKU or item-validity fields: include an exact model/SKU in
stable offer names and verify dates/conditions in the collector. Keep those names stable
between checks to avoid false alerts. Do not fabricate zero-price products for rewards-only
or service events without a verified item price. Preserve other retailers' schemas.

## Silent initialization, independent state and delivery

Use `data/staples/latest.json`, `reports/staples/` and this profile's separate private
state file. Never replace an existing retailer's baseline or reuse its delivery evidence.
No Staples offer prices or baseline are fabricated as part of adding the configuration.
At the first successful source inspection, save the initial baseline SILENTLY: no
first-coverage email, setup email or routine ChatGPT alert. Configuration changes do not
run an immediate deal check, backfill old reports or activate another scheduler.

After initialization, delivery requires BOTH a verified new/material flyer change
relative to established history AND at least one worthwhile verified deal. Confirm
publication, valid/upcoming useful offers and recipient-specific duplicate checks.
Keep the existing private authorized recipients and individual-message delivery.
An unchanged or weak flyer, source failure, repeated event or re-ranking is not an email.
Recorded qualifying pending work may be retried only under the full runbook's rules.
Keep all recipient details and private delivery state out of public GitHub.

The existing CLI accepts `config/staples.toml` as one profile. The registry remains
orchestrator metadata. A VM/other agent still needs its own collector and credentials,
silent baseline seeding, explicit change/value gate and recipient-specific delivery
orchestration. This addition does not deploy a collector, enable SMTP or change the
schedule. See `docs/MULTI_PROFILE.md` and `docs/PORTABILITY.md`.

## Public source entrypoints

These URLs are discovery references, not evidence of current prices:

- Official flyer hub: https://www.staples.ca/a/content/flyers
- Official Kingston directory: https://stores.staples.ca/on/kingston/
- Official store reference: https://stores.staples.ca/on/kingston/office-supplies-ca-23.html
- Official store reference: https://stores.staples.ca/on/kingston/office-supplies-ca-133.html
- Official promotion guidance: https://help.staples.ca/hc/en-us/articles/4402322974359-Deal-Promotion-Rebate-Information-and-Policies
- Canadian archive: https://flyers.smartcanucks.ca/staples-canada
- Additional archive: https://www.flyers-on-line.com/staples
- Kingston listing: https://www.flyerbox.ca/deals/kingston/staples/
- Local discovery: https://flipp.com/en-ca/kingston-on
