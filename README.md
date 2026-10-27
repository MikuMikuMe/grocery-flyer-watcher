# Metro Kingston Flyer Watch

Public, privacy-safe Metro grocery-flyer change tracking and value analysis for Kingston, Ontario.

**Latest source:** https://flipp.com/en-ca/kingston-on/flyer/8192488-metro-ontario

## How it works

1. A **private ChatGPT condition-watch scheduled task** checks the current Metro Ontario flyer for Kingston using public Flipp/Metro pages.
2. The task compares the published edition ID and meaningful price/size changes to `data/latest.json`. An unchanged flyer produces no email, notification or commit.
3. On changes it analyzes strongest everyday-value buys: price per kg/piece, useful quantities and genuinely comparable deals at competing Kingston stores.
4. It commits **public-only** changes to `data/latest.json` and dated `reports/` Markdown analyses, then privately delivers the digest via connected Gmail and a ChatGPT notification. A stable content fingerprint helps prevent duplicate alerts.
5. GitHub Actions automatically validates snapshots and runs tests when code or data changes. **GitHub Actions does not have access to private email accounts** and does not control the private schedule.

The authenticated scheduled task is managed privately in ChatGPT. This repository houses shareable source logic, examples, a public audit trail and CI. A standalone GitHub-hosted notifier would need a separately configured private messaging integration.

## Local usage

Requires Python 3.11+; no third-party packages.

- Validate: `PYTHONPATH=src python -m metro_flyer_watch validate data/latest.json`
- Render ranked report: `PYTHONPATH=src python -m metro_flyer_watch report data/latest.json`
- Compare snapshots: `PYTHONPATH=src python -m metro_flyer_watch compare incoming.json data/latest.json`
- Test: `python -m unittest discover -s tests -v`

## Public data and files

- `data/latest.json` — public baseline: flyer dates and ID, market, clean source URL, selected offers and unit sizes.
- `reports/` — dated public deal shortlists.
- `src/metro_flyer_watch/core.py` — strict schema/privacy validation, change fingerprint and unit-price conversions.
- `automation/runbook.md` — address-free operating contract and retry rules.
- `.github/workflows/ci.yml` — tests and snapshot validation.

## Privacy and deal integrity

**PUBLIC REPOSITORY:** never include personal contacts, precise home location, OAuth material, API keys, tokens, sent-mail IDs, user-specific query strings or other credentials. The snapshot validator rejects unknown fields, email addresses, obvious secrets and tracking queries. Delivery settings are kept only in private connected services.

Price comparisons must use matching cuts, weights and other conditions. Check the flyer date, loyalty/quantity limits and stock. Do not call a deal 'cheapest' without comparable local evidence. Some flyer prices are image-only, and public sources can change or be inaccessible; no offer should be fabricated.