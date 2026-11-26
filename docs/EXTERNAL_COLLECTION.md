# External deterministic collection — Food Basics pilot

GitHub Actions handles bounded public acquisition, source hashing, candidate extraction,
immutable persistence and retries. This workflow runs hourly at minute 23 UTC and on manual
request or collector changes. It has no Gmail, private checkpoint, user preferences, receipt,
secret or personal address data. Native ChatGPT remains the sole evaluation and authorized
mail executor. The external workflow is collection only; no competing sender.

The pilot discovers a current dated weekly archive at SmartCanucks, fetches the actual first
JPEG and records its SHA-256, and requests the publicly accessible syndicated flyer index and
one matching Food Basics edition for the public Kingston store region K7L (not a personal
postal address). The endpoint is an unofficial web endpoint and may fail; do not bypass access
controls or assume service stability. Exact date/merchant match required, ambiguous editions
fail closed. Archive dates are metadata, not proof of a printed date or exact market variant.
If the syndicated endpoint fails, try the fixed WeeklyFlyer featured grid once; require the
visible date range to match the archive and accept only isolated explicit price strings.
This is partial and regional scope is unverified; exclude ambiguous multi-price blocks.
Candidate fields are source-provided numeric price and associated product/terms text, never
interpreted as unconditional cash prices, verified packs, or complete coverage. All candidates
are explicitly non-authorizing and require independent original ad verification. Do not turn
SAVE amounts, multi-buy or member prices into unconditional prices. A first-page fingerprint
alone is not full page inventory or an independent omission pass.

Source evidence and candidates use separate content-addressed create-only files:
`data/external-source-evidence/food-basics/<start>_<end>/<sha256>.json` and
`data/external-candidates/food-basics/<start>_<end>/<sha256>.json`. If syndicated extraction
fails after the original page fetch, retain the source evidence and mark the job incomplete.
Empty/failed retrieval never resets historical data. The same bytes produce the same file;
conflicts fail rather than overwrite. No force pushes. Retry on a later hour if main moves.
The GitHub Actions logs provide actual collection outcomes. A passing synthetic fixture test
is not proof of live source access. Check actual commit and file before claiming a live batch.

## Handoff and migration gates

1. Read the latest in-date immutable candidate and source evidence from actual GitHub HEAD.
2. ChatGPT reviews original source pages, exact region, printed prices, pack, terms and expiry;
   use the existing advertised_facts validator to promote only independently supported facts.
3. Apply existing historical price comparison, quality/build, independent omission and
   publication gates. All public assessed outputs remain separate; no alert on first baseline
   or source migration. Private recipient-specific history and authorization remain untouched.
4. Expand adapters one retailer at a time after real live tests. Staples and Costco require
   distinct collection/warehouse channels. This pilot does not claim the remaining seven are
   migrated, full inventory extracted, historical value computed or end-to-end delivery proven.
   Use the existing native task until the collector's live handoff is verified. No source or
   native state reset. No Vercel or paid API introduced.
