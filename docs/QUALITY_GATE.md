# Mandatory pre-send review: all retailers and all runtimes

This supplements the runbook and DIGEST.md. It applies to every enabled profile, not
just grocery meat. It adds an executable consistency check without pretending that a
validator, green CI job or repeated instruction can prove that a flyer was actually read.
The source-reading agent remains responsible for truthful extraction and real value review.

## Workflow

Discover source inventory -> read pages/grids -> build candidates -> rank -> revisit
original sources for omissions -> run the review gate -> publish one canonical selection
and report -> verify the exact outgoing body -> check private recipient history -> send.

A source being unchanged, unreadable, partially read or fully reviewed are DIFFERENT
states. Preserve these distinctions privately. Never report a whole flyer unchanged
because its dates or one previously chosen product match. A partial historical shortlist
is not a full source inventory. Actual page-content fingerprints can support reuse of a
previous complete review only when every relevant page is proven unchanged; a date,
headline, search snippet or unchanged filename cannot.

## Source-first coverage and independent omission pass

For a finite flyer enumerate all pages/spreads from its actual index. Record each unit's
actual source URL, tool/read evidence, status and candidate identifiers. Try independent
sources for blocked content. Review all advertised departments before selection; front,
back and department pages are mandatory discovery, not a requirement to recommend an item
from every department. A retailer-category quota would itself risk crowding out good deals.

For grocery sources review all present meat cuts, seafood, produce, dairy, pantry, frozen
and household offers. For pharmacies include personal care, household, food and other
advertised departments. For general retailers and collections use all categories and
accessible pagination; never silently stop when ten convenient items have been found.
An unknown/inaccessible collection remainder means partial coverage, not zero offers.

The candidate pool must precede the top 8-10. Every identified offer has an inclusion or
exclusion decision, with genuine private reasoning. Prominent and strongly rated excluded
offers need an explicit second-pass note. Do not fabricate a rationale or lower a rating
to make the gate pass. A prominent item is not automatically a bargain, but it must be
considered rather than overlooked.

Second pass: re-open the actual source pages/grids, not just the draft or candidate list.
Check for omitted prominent products and stronger alternatives to weak filler, then check
names, cuts, packs, units, cash prices, conditions and dates. Use a separate reviewer/agent
when available, with the sources and mission supplied before the draft to reduce anchoring.
Otherwise perform a distinct source-first pass yourself; do not claim an independent
agent participated. Missing observations discovered here must be added to the candidate
inventory before rerunning validation. Do not invent read references or tick boxes for
unread pages. No automatic checker can detect a product omitted from both the source
inventory declaration and the candidate list without actually inspecting the source.

## Executable gate and canonical output

Python 3.11+; no additional runtime packages, network, credentials or email transport:

```sh
PYTHONPATH=src python -m grocery_flyer_watch.review /private/review.json \
  --report-url https://example.org/reports/edition \
  --out /private/new-reviewed-output

PYTHONPATH=src python -m grocery_flyer_watch.review /private/review.json \
  --report-url https://example.org/reports/edition \
  --check-body /private/new-reviewed-output/digest.md
```

Use an ACTUAL public report URL in production; the example URL is not evidence. Exit 0
means the supplied review passed; exit 2 means blocked. Do not send if the gate fails,
cannot run, or has unresolved findings. Continue other retailers independently. A genuine
partial-coverage exception must disclose the exact public gap briefly and still satisfy
verified-value/count rules; it is not a generic disclaimer or permission to skip pages.

The output directory must be new. It contains only `selection.json` and `digest.md`.
The full review plan, source-read/coverage logs, ranking rationale and private history
references are NOT public artifacts and must stay outside the public checkout.

`selection.json` uses a NEW `reviewed-selection-v1` schema; it is not a replacement for,
or accepted input to, the older dated-flyer CLI. Undated collection offers can have null
promotion dates; never invent dates to appease an old schema. Existing snapshots, archived
reports, delivery evidence and event identities remain intact.

For new qualifying digests publish the generated selection/report under a new, immutable
retailer/campaign path including `selection_sha256`. A public report can append source
references below the generated shopping section, but its shopping entries must remain
identical to the generated email body. Link email to that specific version, not a mutable
latest report that can silently become a different shopping list. Do not store email
headers, recipients or send records with it. The report is public shopping content only.
The selection hash is an editorial integrity lock, NOT a notification event ID. A rewording,
changed shortlist, correction or fresh review never becomes a new promotion simply because
its selection hash differs. Use actual campaign/change evidence and private Sent history.

Immediately before EACH authorized send recheck current eligibility/dates, run `--check-body`
on the actual Markdown supplied to Gmail, and verify public publication and recipient-specific
history. Do not rewrite the validated body from memory. Transport-specific HTML conversion
may change formatting, but it must not change product facts or omit purchase conditions.

## Review plan v1

The strict keys are defined in `src/grocery_flyer_watch/review.py`. The synthetic, dynamically
dated `fixture()` in `tests/test_review_gate.py` is a complete executable schema example,
NOT a source of real offers or an authorized email. Never copy its successful review flags
or values into real observations.

Top level: version=1, retailer, market, timezone, campaign_key, period_label, change,
coverage, candidates, selected_ids, second_pass and shortfall.

- `change`: kind (`new_edition` or `material_offer_change` only), private baseline_ref and
  public evidence_refs. The collector must actually establish the change; the validator
  checks these fields, not remote history or the truth of the assertion. Initialization,
  unchanged content and editorial corrections fail the sending gate.
- `coverage`: inventory_url, inventory_complete, expected_unit_ids, units and partial_note.
  Each unit: id, url, status (`reviewed` or genuinely `blocked`), evidence_ref, candidate_ids,
  note. No pending/unreviewed units. Declared candidates and page inventories must reconcile.
  Blocked/unknown inventory requires an accurate brief public partial_note. Source evidence
  logs remain private; only that necessary gap statement is projected into the digest.
- Each candidate has the exact CANDIDATE keys from the module. `source_name` must occur
  verbatim apart from whitespace/case in `source_quote`; preserve the source wording.
  Transcribe the relevant product, pack, price and terms faithfully from actually observed
  content, not generated guesses. `price_kind` distinguishes cash from saving-only amounts.
  `pack` is required for package pricing; each/per-weight products need no invented pack.
  `starts_on`/`ends_on` are actual item dates or null where not advertised. `verified_on`
  must be the current local date for selected items. The timestamp is not a promotion date.
- `channel` records verified purchase applicability, not a promise of shelf inventory:
  in_store, pickup, unverified or shipping_only. The latter is blocked under this workflow's
  purchase-channel policy. Unknown local eligibility cannot be a best/worth-buying claim;
  it may be an explicitly qualified comparison entry. Public regional in-store eligibility
  is not a claim that a branch currently has stock. Do not mislabel either.
- `priority` is 1-5; `prominent` is boolean. `decision` is include/exclude, `reason` is private.
  `section` is Best buys, Worth buying or Not worth treating as headline bargains.
  `assessment` and `terms` are PUBLIC: use concise, source-backed text with no private
  travel, location, account, membership-status or receipt information. No arbitrary savings
  threshold. Do not hide factual comparison claims inside prose to bypass structured checks.
- `comparison` is null unless actually supported. Otherwise use retailer, source_url,
  source_quote, price_cad, pricing, kind and ours/theirs attribute dictionaries. Kind meat
  requires species/cut/bone/state; model requires model/condition; pack requires brand/product/pack.
  Required values must match and be present in each respective source quote. Unknown bone
  content is not equivalent to boneless. Package sizes and pricing units must match.
  This deliberately rejects uncertain comparisons; omit the comparison rather than invent
  an attribute or replace an unknown with a guess. Additional attributes and all prose still
  need actual source review; this is not a general natural-language fact checker.
- `selected_ids`: 8-10 distinct promotions, not variants counted as separate offers. Most
  entries must be useful and purchase-eligible. Shorter digests need a real evidence shortfall,
  a completed review and no unexplained omitted useful candidates. Shortfall fields are
  reason and reviewed; normally empty string and false. Exact conditions remain inline.
- `second_pass`: source_unit_ids, candidate_ids, prominent_ids, omission_notes and unresolved.
  Lists must account for the reviewed sources/candidates. omission_notes covers every excluded
  prominent or priority-4/5 candidate. unresolved must be empty. These are records of a real
  second pass, not independent proof of one; never manufacture them to obtain a green result.

The allowlisted public projection excludes private rationale and run evidence. Automated
contact/secret screening is a guardrail, not a privacy proof: manually inspect all public
text, including terms, assessments and coverage notes before publication.

## Regression tests and boundary

Offline regressions cover missing butcher pages, unreviewed sections, undisclosed partial
coverage, silently excluded beef/wings/pork candidates, unsupported boneless claims,
wrong prices/units/packs, coupon saving versus cash price, expired item promotions, stale
selected evidence, shipping-only/unknown applicability, padding variants, weak-heavy lists,
report/body drift, privacy projection and all seven enabled retailers.

Existing CI discovers these tests on its Python version matrix. Green CI proves the tested
logic, NOT that today's offers, candidate extraction or judgments are correct.
The legacy `runner.send_smtp` is intentionally unchanged for compatibility; it does NOT
automatically call this gate. The scheduled Gmail workflow MUST execute the gate before
sending; any future VM or alternative notifier must integrate it explicitly too. This
update is not a universal scraper, browser integration, price-truth oracle, Gmail API
permission restriction, or a guarantee that no human/agent can bypass the checks.

No setup/test/backfill emails or baseline changes are authorized by installing these
safeguards. Preserve cadence, enabled/paused state, existing recipients and all source scopes.
