# Multiple retailers without changing runtimes

`config/profiles.toml` is the public registry of enabled watches. It currently lists
Metro, Shoppers Drug Mart, Rexall, Staples, Food Basics, Walmart and Costco in Kingston,
Ontario. Each entry points to an ordinary single-profile CLI TOML plus its public
baseline/report destination and optional policy. Registry paths are repository-root-relative;
paths INSIDE each profile TOML are relative to that TOML, following the existing CLI contract.

## ChatGPT or another coding agent

Read the registry on every run and process every entry independently. Read the entry's
profile and policy, verify sources, compare the matching baseline/edition archives,
and publish verified changes. Privately deliver a digest only after BOTH runbook
conditions pass: a verified change against an established baseline and useful value.
Follow docs/DIGEST.md for 8-10 assessed entries PER qualifying retailer, not one shared
budget across all retailers. Initialize new profiles silently; a profile/report/archived
snapshot existing does not alone authorize email. One unavailable or unchanged retailer
must not short-circuit the others. Keep all private preferences and delivery state private.

Metro retains data/latest.json and reports/. Other profiles use data/<profile-id>/latest.json
and reports/<profile-id>/ as specified in the registry. New independent profiles must not
adopt individual competitor quotes from other retailer reports as a complete baseline.
Never overwrite one retailer with another. Preserve current, preview and overlapping
edition histories. Existing already-published booklets are initialized silently.

Staples' flyer and two undated collection ledgers remain separate as specified in STAPLES.md.
Costco may advertise only a discount, not a full warehouse purchase price. Follow COSTCO.md:
keep such verified evidence in reports/costco/warehouse-savings.md and do NOT invent a
price_cad or weekly dates. A missing dated JSON does not erase established ledger history.
The observation ledgers are agent/orchestrator formats, not inputs accepted by the CLI.

## Standalone deployment

The existing CLI takes one profile; do NOT pass config/profiles.toml to --config. Use
one privately configured collector/state per retailer and dry-run before live delivery:

```sh
grocery-flyer-watch run --config /private/food-basics.toml --dry-run
grocery-flyer-watch run --config /private/walmart.toml --dry-run
grocery-flyer-watch run --config /private/costco.toml --dry-run
```

The new profiles have the same interface as Metro, Shoppers, Rexall and Staples. A
scheduler/agent enumerates the registry; a VM can run this sequential wrapper after
configuring collection, private delivery, silent baseline seeding and change/value gates:

```sh
#!/bin/sh
status=0
for profile in metro shoppers rexall staples food-basics walmart costco; do
  /opt/grocery-flyer-watch/.venv/bin/grocery-flyer-watch run \
    --config "/etc/grocery-flyer-watch/${profile}.toml" || status=1
done
exit "$status"
```

These are private deployment filenames; metro.toml is a private copy of config/watch.toml.
Do not chain retailers with &&: one failure must not skip the others. Use separate private
state files and sequential Git publication for a shared checkout. Keep every state file
outside the entire public checkout when enabling Git publication, as in PORTABILITY.md.

This is an example, not an installed scheduler or universal scraper. Default public profiles
still have no live collector, no email and no Git push. The transport does not evaluate
value, local eligibility or per-recipient duplicate/retry rules: the orchestrator must.
Do not start another active delivery scheduler or import another retailer's baseline.
Adding a retailer changes neither existing cadence nor enabled/paused state. A migration
requires explicit cutover and deliberate handled-state import, never old-digest backfill.
