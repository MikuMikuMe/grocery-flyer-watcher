# Costco Canada warehouse-savings monitoring policy

Costco is a separate Kingston, Ontario profile governed by the runbook and docs/DIGEST.md.
Its flyer-equivalent sources include Ontario regular-warehouse savings and dated savings
booklets/events. Do not assume a weekly publication cycle. Public warehouse 533 is the
Kingston reference, not a personal preference, membership identifier or residential address.

## Source and channel verification

Start with the official Warehouse Savings hub and coupon offers, select Ontario and
verify applicability to the regular Kingston warehouse. Corroborate dates/items using
independent Ontario archives and actual source pages, not only Flipp. Costco subdomains
and copied scans do not establish independent corroboration. Store-specific observations
elsewhere in Ontario do not prove Kingston pricing or inventory.

Keep regular-warehouse, Business Centre, Costco.ca online and Same-Day/Instacart pricing
separate. Do not import Quebec-only or US offers. The official savings page itself may
link delivery at a higher price; the linked online price is NOT the warehouse checkout
price. An item possibly available in a warehouse is not verified local stock. Respect
private allowed fulfillment channels; never recommend a shipping-only offer as an
in-store buy. Undocumented warehouse markdowns require their own verifiable evidence;
a price ending or an old crowd-sourced photo does not prove a current promotion.

## Discounts are not purchase prices

Many coupons show only 'SAVE $X', not the full price. NEVER store the dollar saving as
price_cad, subtract it from an unrelated online price, or invent a regular warehouse
price. A dated-flyer JSON snapshot requires at least one verified actual cash purchase
price and real advertised validity. Do not create a fake zero-price product or fabricated
expiry/edition merely to satisfy the schema. Preserve separate current/upcoming periods
and individual item dates when a page combines several promotions.

When a source verifies a discount/event but not its warehouse checkout price, retain
that limited public evidence in reports/costco/warehouse-savings.md instead of inventing
compatible JSON. For each observation keep a clean source URL, stable item number/model,
exact pack, advertised discount (explicitly labelled SAVING, not cash price), actual
advertised dates, public region/channel and whether a warehouse price is verified. Say
'warehouse cash price not verified' when necessary. Do not publish private coverage or
notification state. Create the ledger only after actual inspection, never at setup.
Existing event observations count as history; the absence of latest.json alone must not
cause repeated initialization. A later first observation of the same event's full price
is not automatically a new price reduction or permission to backfill email.

A discount-only item may be brief conditional context, but cannot establish the useful
value gate without a verified purchase price and meaningful assessment. It must not fill
an 8-10-item roundup with unsupported bargains. Establish actual warehouse cost before
recommending a buy; use the existing narrow evidence-shortfall rule if verification is
insufficient. Observation timestamps and new page layouts are not promotional changes.

## Membership and bulk-value analysis

Verify current membership and item-level eligibility; label membership requirements
concisely, without assuming the operator or any recipient holds a valid membership,
Executive tier, credit card or reward balance. Ordinary unknown membership status does
not disable monitoring: describe eligible member offers conditionally. Do not purchase,
renew or upgrade membership, log in to accounts or calculate speculative Executive/card
rebates as instant savings. Keep private membership status out of reports and GitHub.

Evaluate ALL advertised categories without a food-only or technology-only filter. Match
item numbers, exact pack quantities, sizes, condition and model specifications. Compare
unit prices and the FULL cash outlay against smaller packages at other enabled/local
retailers. Bulk is not automatically cheaper or useful: consider perishability and practical
quantity without inventing a household size, storage capacity or consumption rate. Verify
limits, redemption/coupon terms, exclusions, actual dates, required fees and applicable
warranty/returns. Never assume stacked offers or restricted eligibility.

## Independent history and notification

Use data/costco/latest.json for compatible verified dated cash-price snapshots,
reports/costco/ for edition reports, and the warehouse-savings ledger above for limited
coupon evidence. All initial coverage is SILENT. Prior comparisons elsewhere are not a
full Costco baseline. Do not change existing retailer histories, reset states or send
setup/backfill mail. Future alerts require a verified new/materially revised warehouse
promotion against established history AND useful verified value. Apply 8-10 assessed
entries per qualifying retailer, compact formatting, essential terms and per-recipient
deduplication. Merely reaching a known event's start date never triggers repeat mail.

The profile is compatible with the existing dated-flyer CLI; the separate Markdown ledger
is an agent/orchestrator contract, not an automatically parsed CLI input or a bundled live
warehouse scraper. Another runtime supplies collection, private state and credentials.

Public entrypoints and verification references:
- https://www.costco.ca/f/-/in-the-warehouse
- https://www.costco.ca/o/-/coupons
- https://www.costco.ca/w/-/on/kingston/533
- https://www.costco.ca/f/-/membership-conditions-regulations
- https://flyers.smartcanucks.ca/costco-canada
- https://customerservice.costco.ca/app/answers/answer_view/a_id/1017393/~/where-can-i-find-warehouse-savings%3F
