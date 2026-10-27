# Metro Kingston Flyer Watch

Public, privacy-safe grocery-flyer change tracking and value analysis for Metro stores in Kingston, Ontario.

## Flyer discovery (not Flipp-only)

The private monitor checks the official [Metro Kingston Barrie Street store flyer](https://www.metro.ca/en/find-a-grocery/241) and [Metro's flyer hub](https://www.metro.ca/en/flyer) first, then searches and cross-checks other published sources, including:

- [SmartCanucks' Metro Ontario flyer archive](https://flyers.smartcanucks.ca/metro-canada)
- [Flyerbox's Kingston Metro listing](https://www.flyerbox.ca/deals/kingston/metro/)
- [WeeklyFlyer's Metro archive](https://www.weeklyflyer.com/metro)
- Flipp, reebee, and other accessible Ontario flyer listings

A website headline that says "next week" is **not** evidence by itself: the page may show the prior week's image, products and prices. The monitor must confirm the region, image-level validity dates, advertised prices, quantities and restrictions, and corroborate a next-week preview with reliable independent or first-party evidence.

## Operation

- The private ChatGPT condition-watch schedule checks sources every six hours in `America/Toronto`, including future-week previews.
- Compare newly validated flyer ID/dates/product contents to `data/latest.json`. Do not email or commit if unchanged.
- On a verified new or materially revised flyer, calculate meaningful unit-price comparisons and highlight particularly good values against genuinely matching local alternatives.
- Commit public-only snapshots and a dated analysis under `reports/`; publish the GitHub revision and privately send the complete digest via connected Gmail with a ChatGPT notification.
- CI validates the code and the public snapshot. Scheduling and private email delivery **do not** run within GitHub Actions.
- Private contact addresses and any authentication/delivery metadata are **never included** in this public repository.

## Running locally

Requires Python 3.11+.

- `PYTHONPATH=src python -m metro_flyer_watch validate data/latest.json`
- `PYTHONPATH=src python -m metro_flyer_watch report data/latest.json`
- `PYTHONPATH=src python -m metro_flyer_watch compare incoming.json data/latest.json`
- `python -m unittest discover -s tests -v`

## Files

- `data/latest.json`: current confirmed flyer snapshot and selected offers
- `reports/`: public, dated, source-linked deal analyses
- `src/metro_flyer_watch/`: privacy-aware snapshot validation, fingerprinting, unit prices and report rendering
- `automation/runbook.md`: public workflow
- `.github/workflows/ci.yml`: tests and validation

## Privacy & accuracy

Do not commit contacts, precise user location, message metadata, tokens, authentication information or personalized/tracking URLs. Check that source dates, offer size, limitations and cuts align before ranking deals. Flipp is one of several sources, not the source of truth on its own. If a supposed new flyer cannot be verified from its page images and content, do not invent a new edition.
