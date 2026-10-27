# Shoppers Drug Mart monitoring policy

Apply this policy to the Shoppers profile in `config/profiles.toml`. It supplements,
not replaces, the retailer-neutral runbook. Metro remains independently enabled.
The current profile is Kingston, Ontario; changing cities requires matching source URLs.

## Sources and dates

Start with the official flyer hub and a Kingston store selection. The configured
store-locator reference is a public retail location, not a personal location. Search
for Shoppers Drug Mart + configured city/region + current/next week and exact dates.
Cross-check the Ontario edition on independent archives; do not substitute Atlantic,
Western Canada or Quebec/Pharmaprix flyers. Flipp is one source, never the sole source.
The links in config are discovery entrypoints, not proof of a current offer.

If an official page is dynamically rendered or blocks access, record the limitation
privately and use corroborated, actual flyer images/product details from other sources.
An inaccessible source is not evidence that a flyer is unchanged. Never fabricate an
edition or copy dates/prices solely from a search snippet or a future-dated heading.

Verify the overall flyer dates AND item/event-specific dates. Flag weekend-only,
one-day, member-only, online-only and store-specific offers. Do not recommend an
expired weekend price merely because the rest of the flyer is still valid. State
future dates clearly. A newly published, verified short promotion can be a material
update, but qualifies for email only when worthwhile deals are found too. Rechecking
an already reported event or reaching its start date is not a reason to email again.

## Value analysis

Prioritize genuinely strong grocery, household, paper, cleaning, personal-care and
beauty deals. Rank roughly 5-10 only when enough strong offers exist; never pad a list.
One excellent deal can qualify, but zero worthwhile deals means NO EMAIL even when
there is a new flyer. Compare like-for-like with Metro and other local competitors
where verified: brand, weight/count, concentration, sheets/plies, cut and purchase
requirements matter. Do not infer medical suitability from an advertised price or
encourage medicine stockpiling.

Always distinguish:

- Cash payable at checkout, and whether the advertised price requires a multi-buy.
- PC Optimum points earned or redeemed, shown separately from the cash price.
- Conditions: membership, app/loaded or targeted offers, minimum spend, exclusions,
  redemption thresholds, purchase limits and precise event dates.

Do not assume a public points promotion is available to every member or that the user
has a particular points balance/targeted offer. Do not claim stacking without explicit
terms. Only calculate a conditional points-adjusted value when the conversion and all
conditions are verified; label assumptions, and never call points an instant cash discount.
Avoid encouraging unnecessary spending solely to reach a reward threshold.

In snapshots, `price_cad` is the applicable cash purchase price, NOT a net-after-points
number. Record required bundle quantity, point/event conditions and item-specific dates
in `restrictions`; explain conditional value in `why` and the report. Changing those
restrictions is material to the content fingerprint. The current schema does not have
structured promotion-date fields: date/eligibility verification is the collector's job.
Pure points events with no verified item prices may be noted as context in a verified
deal report, but must not become invented zero-price products or fake flyer snapshots.

## Independent state and silent initialization

Read/write the baseline and reports named by this profile's registry entry. Never
replace Metro's `data/latest.json` with Shoppers data. Standalone public archives are
already separated by retailer/market, and this profile has its own private state file.
Check private delivery deduplication separately for each retailer and edition/event.

No Shoppers flyer snapshot is fabricated during setup. At the first successful scheduled
inspection, verify and save the current baseline SILENTLY. Do not send a first-coverage
email or routine ChatGPT alert. Establishing a baseline does not identify a flyer change.
The older instruction to send a first-coverage digest is superseded by this policy.

After initialization, email only when BOTH a new/material flyer change is verified AND
at least one genuinely worthwhile deal is found. Check duplicate delivery and current
validity before sending. A new flyer with no good deals can update the public baseline,
but is handled privately without email; do not later reclassify an unchanged flyer to
create an alert. Retry only previously qualified, unsent digests with recorded private
pending evidence and still-useful offers. Missing Sent history alone is not pending work.

Routine checks, source failures, weak/unchanged flyers, new profile setup and config/code
changes do not trigger email. Adding this profile or changing this policy must not resend
Metro's existing baseline. The six-hour cadence controls checks, not email frequency.

## Source entrypoints

- Official flyer: https://www.shoppersdrugmart.ca/flyer
- Official Kingston store selection: https://www.shoppersdrugmart.ca/store-locator/store/607
- Ontario archive selection: https://flyers.smartcanucks.ca/shoppers-drug-mart-canada
- Additional archive: https://www.weeklyflyer.com/shoppers-drug-mart
- Local listing: https://ca-flyers.com/stores/kingston/shoppers-drug-mart/1011-princess-st
- Local flyer discovery: https://flipp.com/en-ca/kingston-on
