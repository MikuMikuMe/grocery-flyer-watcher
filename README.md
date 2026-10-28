# Grocery Flyer Watcher

Location-configurable retailer flyer and deal monitoring with public reports and private
notifications. The application is **not tied to Kingston, Metro, ChatGPT or an AI provider**.
The supplied profiles watch **Metro, Shoppers Drug Mart, Rexall and Staples in Kingston,
Ontario**. Moving cities means changing matching profiles and source URLs. The current
price model supports **Canadian dollars only**.

## Notification policy: checks are not emails

The existing six-hour schedule is a checking cadence, not an email frequency. Email
requires BOTH a verified advertised-offer change relative to an established baseline
AND genuinely worthwhile deals, followed by validity and recipient-specific duplicate
checks. Send once per qualifying change per authorized recipient. No good deals means
no email even when a flyer changes. For Staples, the named Deals/Clearance Centre sources
also qualify under this rule; a product need not appear in a flyer.

Initialize new retailer/source baselines silently. Do not email for routine checks,
unchanged or weak deals, source errors, setup or configuration changes. Routine ChatGPT
output is also suppressed without a qualifying update. Separate test emails require a
fresh explicit request. See [notification and retry rules](automation/runbook.md).

These gates are applied by the connected task. Standalone collectors/agents must apply
the same rules before enabling SMTP. A report or working transport is not evidence of
a qualifying change. Source/configuration changes preserve a task's enabled/paused state.

## Enabled watches

`config/profiles.toml` lists enabled retailer profiles and independent baseline paths:

| Retailer | Profile | Dated-flyer baseline |
| --- | --- | --- |
| Metro | `config/watch.toml` | `data/latest.json` |
| Shoppers Drug Mart | `config/shoppers.toml` | `data/shoppers-drug-mart/latest.json` |
| Rexall | `config/rexall.toml` | `data/rexall/latest.json` |
| Staples | `config/staples.toml` | `data/staples/latest.json` |

### Staples: all categories, flyers plus deals and clearance

Always inspect the official flyer hub AND these collections:

- [Deals Centre](https://www.staples.ca/collections/staples-deals-centre)
- [Clearance Centre](https://www.staples.ca/collections/staples-clearance-centre-7922)

**No category allowlist.** Chairs, cleaning supplies, candies, snacks, household goods,
electronics and other categories are all eligible. Examples are not filters. Follow
accessible pagination and rank verified value rather than restricting departments.

Apply the privately configured home store before checking pickup or branch-specific
prices/stock. Do not assume a site's default store or national inventory matches it.
Online-only shipping offers can still qualify with verified costs and applicability.
Personal store preferences stay private; public retail facts may be cited as evidence.

New collection sources initialize silently. Deduplicate identical offers across sources,
and do not treat reordering, partial coverage or newly noticed old products as new deals.
Undated collection observations use separate public Markdown ledgers under
`reports/staples/collections/`; never invent a flyer expiry to fit them into dated JSON.
The existing CLI does not automatically consume those ledgers: the connected task or a
replacement collector/orchestrator implements this policy. See [Staples rules](docs/STAPLES.md).

See also [Shoppers rules](docs/SHOPPERS.md), [Rexall rules](docs/REXALL.md), and
[multiple-profile operation](docs/MULTI_PROFILE.md). Setup never fabricates prices.

## What runs independently today

- A Python 3.11+ CLI with no third-party runtime dependencies.
- Verified dated-flyer JSON and external-command collector adapters.
- Region/source/date validation, unit-price reports, persistent duplicate detection,
  pending-delivery retries, dry runs, local/Git publication and TLS SMTP transport.
- Cron instructions, systemd templates and an agent handoff in `AGENTS.md`.
- Compatible original `python -m metro_flyer_watch` commands.

**Boundary:** no universal live flyer/collection scraper or AI service is bundled.
A collector must inspect sources, verify items and assess value. The core validates
structure/consistency, not the truth of a price. A new scheduler does not supply a
browser, credentials, undated-collection adapter or equivalent deal-analysis intelligence.

## Quick start

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
grocery-flyer-watch validate data/latest.json
grocery-flyer-watch report data/latest.json
python -m unittest discover -s tests -v
```

Historical files are not a claim that saved prices are current. The runner rejects
expired flyers for new delivery. Use the matching profile for freshly verified dated JSON:

```sh
grocery-flyer-watch run --config config/watch.toml --input /path/to/metro.json --dry-run
grocery-flyer-watch run --config config/shoppers.toml --input /path/to/shoppers.json --dry-run
grocery-flyer-watch run --config config/rexall.toml --input /path/to/rexall.json --dry-run
grocery-flyer-watch run --config config/staples.toml --input /path/to/staples.json --dry-run
```

Configure a trusted `collector` argv in each private TOML before running without `--input`.
Defaults deliberately contain no collector, no email and no Git push. Missing setup fails
rather than inventing offers. The CLI accepts one profile at a time; the registry is for
orchestration. See the sequential VM example in `docs/MULTI_PROFILE.md`.

## Configuration and privacy

Change market, retailer, timezone and matching sources together when moving. Each profile
has separate private state and scoped public archives. One unchanged/failed profile must
not suppress the others. Prefer official store sources and cross-check beyond Flipp.

Standalone SMTP reads addresses and credentials from environment variables. Keep actual
settings, personal home-store preferences, private state, caches and delivery logs outside
a public checkout. Public schema/privacy checks are guardrails, not proof arbitrary text
is safe. Review exact public paths. Connected Gmail settings remain private.

## Architecture

`Scheduler -> Profile registry -> Source collector -> Validation / change detection -> Public archive -> Private delivery`

Schedulers are interchangeable: ChatGPT, cron, systemd or another agent. Publication and
delivery have separate state so a failed email is not forgotten after a successful public
commit. Current/preview editions and collection observations remain distinct; identical
material offers across sources must not produce duplicate messages.

See [deployment and dated-JSON contract](docs/PORTABILITY.md),
[agent instructions](AGENTS.md), [runbook](automation/runbook.md) and
[Staples collection/store rules](docs/STAPLES.md).

## Repository identity

Canonical repository: [MikuMikuMe/grocery-flyer-watcher](https://github.com/MikuMikuMe/grocery-flyer-watcher).
Stable repository ID `1435089073` survives the completed in-place rename. Resolve that ID
for future name changes. History, reports and public visibility are preserved.

The installed CLI remains `grocery-flyer-watch`, the Python package `grocery_flyer_watch`,
and existing service names/deployment paths remain unchanged for compatibility.
