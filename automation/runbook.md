# Public monitoring runbook — multiple sources, privacy-first

The authenticated private ChatGPT task handles scheduled checks, Gmail delivery, deduplication and private ChatGPT notifications. This public repository stores **only** published grocery flyer data, reusable logic, the public runbook and non-sensitive report history.

## A. Discover the correct Kingston/Metro flyers

1. Inspect official Metro pages: https://www.metro.ca/en/find-a-grocery/241 and https://www.metro.ca/en/flyer . Confirm Ontario/Kingston store selection.
2. Search publicly for "Metro Kingston Ontario flyer", "Metro Ontario flyer this week", "Metro Ontario flyer next week" and the upcoming date range. Cross-check https://flyers.smartcanucks.ca/metro-canada , https://www.flyerbox.ca/deals/kingston/metro/ , https://www.weeklyflyer.com/metro , Flipp, reebee and other accessible sources.
3. Match **actual image or product-grid content** with stated valid-from/valid-to dates; verify Ontario geography and item-level prices, product sizes, purchase limits and restrictions. A third-party page that labels old pages as "next week" is insufficient. Date-only previews must not trigger a notification. If the first-party listing is behind a dynamic iframe, validate using other independent published evidence.
4. Accept an early preview only with reliable corroboration of its new period, products and prices; clearly tell readers if it does not start until a future date. If no verifiable preview exists, retain the current verified baseline.
5. Compare the verified edition, dates and item contents with `data/latest.json`. No verified change means **no notification, no email, no data commit**. A source outage or unverified claim should never be interpreted as an update.

## B. Analyze actual value

6. Rank 5–10 genuinely worthwhile products, with price per kg/lb/piece and exact weight/count, account for bones and cuts, shelf life, loyalty limits, regional availability, and compare like-for-like with Food Basics, FreshCo, No Frills and Walmart when evidence exists.
7. Categorize must-buy, conditional and skip; include actual flyer start/end dates, clean public source links, and caution against misleading cross-store comparisons.

## C. Publish and privately deliver changes

8. Validate and commit ONLY public flyer data in `data/latest.json`, a dated `reports/` report, and any non-sensitive code/runbook updates. Verify commit outcome. Never store a private contact, address, token, Gmail message ID, credentials or private delivery log.
9. Check private Gmail Sent for the stable edition/content fingerprint before sending once through the configured private Gmail account to its privately stored recipient. Never send mail merely because this runbook or code changes.
10. Notify privately in ChatGPT with top deals, expiration and the public report link. On failure, report exactly the blocked step and retry without duplicate sends.

## Special case: delivery test

When the user expressly requests a test email, a single, explicitly labelled **TEST** message may be delivered from their authenticated account without altering the flyer baseline, public reports or public commit history. This is separate from the normal changed-flyer notification rule.
