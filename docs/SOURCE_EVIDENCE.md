# Source evidence: official-first, not official-only

This is the source-acceptance and execution policy for every enabled retailer. Read it
with DIGEST.md and the selected delivery adapter. It clarifies existing requirements;
it does not relax factual accuracy, market eligibility, the omission review, change/value
gates, privacy, publication or duplicate prevention. It creates no new database or gate.

## 1. The advertisement matters, not the hostname

A legible retailer-authored flyer image/PDF or equivalent complete offer grid hosted by
an appropriate third-party archive is usable advertising evidence. SmartCanucks, Flipp,
reebee, Flyers Online, WeeklyFlyer and other reliably matched regional/local archives are
eligible sources, not merely discovery links. A publisher name alone is not accreditation:
inspect the actual content, retailer, edition, printed validity, region and relevant terms.
An article, search snippet or future-dated heading without the actual advertisement is
not an equivalent substitute. Cross-check source families and edition identity honestly.

Try the official selected-market entrypoint normally. If it is blocked or lacks readable
content, move to an accessible archive in that same run. Do not repeatedly retry a 403,
security challenge or unusable selector while leaving readable advertisements unexamined.
Return to an official page only when it can resolve a specific missing or conflicting fact.
Success on the official domain is NOT a prerequisite for approving reliable alternative
content. Nor must an official store-specific product page repeat each selected price.

Use independent corroboration to establish the correct edition/market and resolve doubtful
facts. Do not invent a universal requirement for two independent webpages for EACH item.
Shared page footers and edition-wide terms can support multiple offers when they really
apply; retain more specific item dates or restrictions. Two hosts carrying the same feed
are not two independent confirmations, but the readable scan remains usable ad evidence.

## 2. Advertising applicability is not live inventory

For ordinary in-store flyer recommendations, establish the price advertised for the
selected market, not proof that someone bought it at a particular checkout today.

Accept market evidence from an actual selected-market flyer, a reliable local edition
mapping, or a clearly established region-wide advertisement covering that market. This
can come from third-party sources. Read exclusions and regional editions. A city landing
page listing a store does not, by itself, establish that every attached leaflet is local.
An Ontario heading does not settle known conflicting Ontario price variants.

`fact_proofs.local_scope_verified` means supported applicability of the advertised offer
to the market and claimed purchase channel. It does NOT require a live stock lookup,
signed-in account, successful official selector, shelf photo, receipt or checkout session.
Set it true only with actual geographic/eligibility evidence. Record that basis in the
private proof, not merely a bare assertion. An in-store flyer ad does not imply stock.

Retain stronger evidence for stronger claims: a branch-specific clearance price, asserted
pickup stock, online-only offer presented for local purchase, or warehouse cash price
requires evidence of that actual channel/location. A generic pickup-services page is not
item stock. Costco SAVE amounts remain discounts, not inferred checkout prices. This
policy does not permit national online prices to stand in for a local shelf offer.

For a specific regional price conflict, resolve that item or omit it from the buy selection;
do not silently choose the lowest variant and do not block unrelated verified products.
Unknown bone content, pack size, member eligibility or other critical facts are similarly
item-specific. Use a precisely qualified comparison only when permitted by the existing
schema; never invent a source quotation to encode an analyst's uncertainty.

## 3. Coverage follows logical pages, not failed mirrors

Inventory the actual flyer contents and accessible departments before selecting 8-10.
Use readable replacement pages from matching editions when necessary. A page inspected
in an archive is REVIEWED even if another host's copy returned 403. That failed duplicate
host is not a missing flyer page and must not be added as a blocked front/back unit.
Keep the failed access in private source-attempt notes, outside the logical page inventory.

Some publishers show two-page spreads or supplements separately. Reconcile page contents
rather than equating different image counts with missing departments. Do not assume two
editions are identical because their dates match. Preserve actual URLs and content hashes.
Inspect all accessible relevant pages, including meat/produce/dairy/pantry/frozen/household
sections and department-leading offers; read actual images when text extraction omits them.
A list of category headings is not page inspection. Candidate discovery has no ten-item cap.

The second omission pass means genuinely revisiting the original advertisements rather
than checking only the written shortlist. The same agent may revisit the same archive with
a distinct actual read reference. A second human, model, official host or outside reviewer
is NOT required. Do not call this an independent third-party audit unless one occurred.

Genuinely missing content still requires alternate-source attempts and the existing narrow
partial-coverage/shortfall rules. Do not claim complete review, invent hashes or change an
unread page to reviewed. No empty source resets or new-offer claims from partial collections.

## 4. Finish research instead of reporting perpetual prerequisites

Do a light discovery/history pass across enabled profiles, then complete each changed
retailer independently through candidate review, the omission pass and executable checks.
Do not spend every run rediscovering the same editions and returning only preliminary
candidates. Finishing one eligible retailer is preferable to leaving every retailer's
research incomplete; a difficult source must not suppress the others.

When evidence is sufficient, assemble the real bundle and actually run `quality check`.
If it fails, diagnose the precise code and affected field/item/page, repair real evidence
or a tested implementation defect, and retry. A readable-source task left unfinished is
`research_incomplete`, not proof that evidence is unavailable. Do not claim the quality
gate rejected a digest unless it was run and returned a failure. Startup preflight is not
a content-review pass. Do not record unqualified work as pending authorized delivery.

After a pass, continue build, immutable public assessment/publication, pinned content
verification and the appropriate per-recipient authorizer in the same authorized execution.
Send only after that authorizer passes. Do not add a new manual approval requirement or
stop merely because the host was unofficial. Preserve Gmail Sent checks, private uncertain
attempt handling and the GitHub/Gmail adapter's no-database contract. No test/status emails.

Keep exceptions precise: `source_access_unavailable`, `market_variant_unresolved`,
`item_terms_unresolved`, `research_incomplete`, or an actual executable validation error.
These are private diagnostic descriptions, not new public state-schema fields. A public
report contains shopping facts, not the operator's progress logs or personal preferences.

## 5. Regression boundary

`tests/test_alternative_flyer_sources.py` uses synthetic fixtures to demonstrate that the
existing production gate accepts reviewed archive evidence across retailer profiles,
regionally applicable in-store offers without stock claims, and shared printed validity.
It also checks that changing mirrors cannot invent a new dated event and that missing
market scope, unsupported prices and unresolved omissions still fail. Tests do not
verify any real flyer, source independence, actual stock, or successful email delivery.

The required execution correction is to gather and process acceptable evidence, not to
remove validation or replace genuine inspection with fixture flags. Schedule, recipients,
source scopes, historical baselines, create-only assessments and optional VM behavior stay
unchanged. Installing this policy does not authorize an immediate batch, test or backfill.
