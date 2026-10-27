# Grocery Flyer Watcher

Location-configurable grocery flyer monitoring, deal reports and private notifications.
The application is **not tied to Kingston, Metro, ChatGPT, or a particular AI provider**.
The supplied profiles watch **Metro and Shoppers Drug Mart in Kingston, Ontario**.
Moving cities means changing the matching profiles and source URLs.
The current data model supports **Canadian dollars only**.

## Enabled watches

`config/profiles.toml` lists the enabled watches and their independent baseline/report paths:

| Retailer | Profile | Public baseline |
| --- | --- | --- |
| Metro | `config/watch.toml` | `data/latest.json` |
| Shoppers Drug Mart | `config/shoppers.toml` | `data/shoppers-drug-mart/latest.json` |

The Shoppers baseline is created only after its first verified flyer inspection; setup
does not invent advertised prices. See [Shoppers analysis rules](docs/SHOPPERS.md) for
cash-versus-points comparisons, item-specific validity dates, eligibility and purchase limits.
See [multiple-profile operation](docs/MULTI_PROFILE.md) for independent state and VM examples.

## What runs independently today

- A Python 3.11+ CLI with no third-party runtime dependencies.
- A verified-JSON input adapter and an external-command collector adapter.
- Region/source/date validation, unit-price reporting, persistent duplicate detection,
  pending-delivery retries, safe dry runs, local or Git publication, and TLS SMTP.
- Cron instructions, systemd templates, and an agent handoff in `AGENTS.md`.
- The original `python -m metro_flyer_watch` commands remain compatible.

**Important boundary:** there is no bundled universal live flyer scraper or AI service.
A collector must browse/parse the configured sources, verify offers, rank value and return
JSON. ChatGPT currently fills that role; another agent or a purpose-built scraper can use
exactly the same contract. The core validates structure and consistency, not the truth
of a price. Replacing the scheduler alone does not provide a browser, API credentials,
or equivalent deal-analysis intelligence.

## Quick start

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
grocery-flyer-watch validate data/latest.json
grocery-flyer-watch report data/latest.json
python -m unittest discover -s tests -v
```

`data/latest.json` and `reports/2026-10-22.md` are historical Metro baselines, not a
claim that those prices are current. The runtime rejects expired input for new alerts.

For freshly verified snapshots, use the matching retailer profile:

```sh
grocery-flyer-watch run --config config/watch.toml --input /path/to/metro.json --dry-run
grocery-flyer-watch run --config config/shoppers.toml --input /path/to/shoppers.json --dry-run
```

For automatic collection, configure the trusted `collector` argv in each local TOML,
then run without `--input` or `--dry-run`. Defaults deliberately have **no collector,
no email, and no Git push**; missing setup fails rather than inventing offers.
The existing CLI accepts one profile at a time; agents enumerate the registry and VM
operators can use the sequential wrapper in `docs/MULTI_PROFILE.md`.

## Configuration, not a location baked into code

Change `market`, `retailer`, `timezone` and matching store/source URLs together when moving.
Report headings, validation and state keys use those settings. Each profile has separate
private state; public archive paths also include retailer/market scope. An unchanged or
failed check for one retailer must not prevent checking the other.
Official store pages come first; cross-check independent sources, not just Flipp.

Delivery credentials and sender/recipient addresses are read from environment variables
only by the standalone SMTP adapter. Keep real deployment config, state, collector caches
and logs outside a public checkout. Public JSON has an explicit field allowlist; this is
a guardrail, **not a proof that arbitrary free text is private-information-free**.
Review public reports. The private scheduled task's connected Gmail settings stay private.

## Architecture

`Scheduler -> Profile registry -> Collector per profile -> Validation / change detection -> Public archive -> Private delivery`

Schedulers are interchangeable: the existing ChatGPT task, cron, systemd, or a coding
agent. Collectors are replaceable executables using the documented JSON protocol.
Publication and delivery have separate saved status, so a successful Git push does not
cause a failed email to be forgotten on the next unchanged check. Current and preview
editions can coexist; a mirror site's different edition ID does not create a duplicate.

See [deployment and collector contract](docs/PORTABILITY.md),
[agent instructions](AGENTS.md) and [operating runbook](automation/runbook.md).

## Repository identity

Project name: **Grocery Flyer Watcher**.
Canonical repository: [MikuMikuMe/grocery-flyer-watcher](https://github.com/MikuMikuMe/grocery-flyer-watcher).
The in-place GitHub rename is complete. Public repository ID `1435089073` still identifies
the same repository; existing history, reports and public visibility are preserved.
Resolve this stable ID when a future rename changes the canonical owner/name.

The installed CLI remains `grocery-flyer-watch`, the Python package remains
`grocery_flyer_watch`, and the existing service filenames and deployment paths stay
unchanged for compatibility. The repository name does not require renaming those interfaces.
See the deployment guide for updating an existing clone's remote.
