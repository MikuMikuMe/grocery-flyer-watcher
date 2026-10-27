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
future dates clearly. A newly published, verified short promotion is a material update;
rechecking an already reported event is not a reason to send it again.

## Value analysis

Prioritize genuinely strong grocery, household, paper, cleaning, personal-care and
beauty deals. Rank roughly 5-10 only when enough strong offers exist; never pad a list.
Compare like-for-like with the Metro profile and other local competitors where verified:
brand, weight/count, concentration, sheets/plies, cut and purchase requirements matter.
Do not infer medical suitability from an advertised price or encourage medicine stockpiling.

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

## Independent state and first coverage

Read/write the baseline and reports named by this profile's registry entry. Never
replace Metro's `data/latest.json` with Shoppers data. Standalone public archives are
already separated by retailer/market, and this profile has its own private state file.
Check private delivery deduplication separately for each retailer and edition/event.

No Shoppers flyer snapshot is fabricated during setup. At the first successful scheduled
inspection, verify the current edition, publish its baseline and send one clearly
labelled first-coverage digest. Do not describe it as newly published unless publication
has actually been verified. Afterward, notify only on verified updates or pending-delivery
retries. Adding this profile alone must not resend Metro's existing baseline.

## Source entrypoints

- Official flyer: https://www.shoppersdrugmart.ca/flyer
- Official Kingston store selection: https://www.shoppersdrugmart.ca/store-locator/store/607
- Ontario archive selection: https://flyers.smartcanucks.ca/shoppers-drug-mart-canada
- Additional archive: https://www.weeklyflyer.com/shoppers-drug-mart
- Local listing: https://ca-flyers.com/stores/kingston/shoppers-drug-mart/1011-princess-st
- Local flyer discovery: https://flipp.com/en-ca/kingston-on
