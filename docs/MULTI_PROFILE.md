# Multiple retailers without changing runtimes

`config/profiles.toml` is the public registry of enabled watches. It currently lists
Metro, Shoppers Drug Mart, Rexall and Staples in Kingston, Ontario. Each entry points to an ordinary
single-profile CLI TOML plus its public baseline/report destination and optional policy.
Registry paths are relative to the repository root; paths INSIDE each profile TOML are
relative to that TOML, following the existing CLI contract.

## ChatGPT or another coding agent

Read the registry on every run and process every entry independently. Read the entry's
profile and policy, verify sources, compare the matching baseline/edition archives,
and publish verified changes. Privately deliver a digest only after the runbook's BOTH
conditions pass: a verified change relative to an established baseline and genuinely
worthwhile deals. Initialize new profiles silently; do not email merely because a
profile, report or archived snapshot exists.
No update or a failure for one profile must not short-circuit any other profile's check.
Shared reports are unnecessary: retailer-labelled digests simplify deduplication.
Do not publish private delivery state, addresses or credentials to the registry.

Metro keeps its legacy baseline `data/latest.json`. Shoppers uses
`data/shoppers-drug-mart/latest.json` and `reports/shoppers-drug-mart/`.
Rexall uses `data/rexall/latest.json` and `reports/rexall/` with `docs/REXALL.md`.
Staples uses `data/staples/latest.json` and `reports/staples/` with `docs/STAPLES.md`.
Create each baseline only after actual source verification. Missing data initially means
not yet verified, not a zero-price offer and not permission to reuse another retailer's
data. Current and future editions also remain distinct in history. For Staples, preserve
weekly, event and catalogue histories separately so overlapping editions are not confused
with new offers. Existing already-published booklets are initialized silently.

## Existing standalone CLI

No new API or ChatGPT dependency is required. Invoke the existing CLI separately for
each profile, each with its own configured collector and private state:

```sh
grocery-flyer-watch run --config /private/metro.toml --dry-run
grocery-flyer-watch run --config /private/shoppers.toml --dry-run
grocery-flyer-watch run --config /private/rexall.toml --dry-run
grocery-flyer-watch run --config /private/staples.toml --dry-run
```

Before enabling live delivery, configure the collector and private delivery, silently
seed each initial baseline, and enforce the same change/value gate in the orchestrator.
The low-level SMTP adapter does not evaluate deal quality. A single cron/systemd wrapper
can run all profiles sequentially. Do not join them with `&&`, because one failure must
not suppress the others:

```sh
#!/bin/sh
status=0
/opt/grocery-flyer-watch/.venv/bin/grocery-flyer-watch run --config /etc/grocery-flyer-watch/metro.toml || status=1
/opt/grocery-flyer-watch/.venv/bin/grocery-flyer-watch run --config /etc/grocery-flyer-watch/shoppers.toml || status=1
/opt/grocery-flyer-watch/.venv/bin/grocery-flyer-watch run --config /etc/grocery-flyer-watch/rexall.toml || status=1
/opt/grocery-flyer-watch/.venv/bin/grocery-flyer-watch run --config /etc/grocery-flyer-watch/staples.toml || status=1
exit "$status"
```

This is a deployment example, not an installed scheduler or a bundled live scraper.
The existing CLI takes one profile; do NOT pass the registry to its `--config` flag.
An agent can enumerate the registry, or a VM operator can use the wrapper above.
When using Git publication, run profiles sequentially against the shared checkout,
and keep all state files outside the entire checkout as described in PORTABILITY.md.
The core's archive paths and event keys already include retailer/market scoping.

Keep only one active delivery scheduler for each profile. Follow the existing migration
procedure before replacing the ChatGPT task; do not seed a new retailer from another
retailer's snapshot. Public profile defaults remain no collector/no email/no Git push.
Private recipient-specific duplicate/retry handling is still required by the runbook;
a transport adapter alone does not provide that orchestration.
