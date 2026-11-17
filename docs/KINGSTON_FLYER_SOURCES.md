# Deterministic Kingston flyer-source playbook

Last source review: **2026-11-14**. Machine-readable, stable retailer-specific endpoints and actual store anchors: [`config/kingston_flyer_sources.json`](../config/kingston_flyer_sources.json). These are vetted **entrypoints**, not assurances that a particular edition or item price is current, readable or valid at every Kingston store.

## Mandatory workflow on every run

1. Read `config/profiles.toml`, then load **this source catalog** once, and use it for every enabled retailer. Do not start with a new broad web search.
2. Resolve retailer and Kingston store from `store_anchors`. Use the source list **in order**: local official flyer/store selector first, then direct page-bearing Ontario archive(s), then a Kingston archive. Store URLs verify the location, not every advertised product.
3. Read the in-date **original retailer advertisement pages/grid** from the first working source that matches the retailer, exact Ontario/Kingston market, channel, and printed validity. Cross-check with a distinct family or local selector to establish applicability. Do not require official pages to be accessible when a reliable archive provides equivalent ad evidence.
4. If one entrypoint is 403, JS spinner, stale, or mismatched, **immediately advance** to the next fixed entrypoint; do not repeatedly search for the same domain. A once-per-run revisit is acceptable only for a specific unresolved detail. If one source supports some pages and another fills gaps, preserve their page-level provenance.
5. Record each attempt in the **private** task checkpoint: retailer, date/edition, URL, working/blocked/stale/mismatched, actual inspected page cursor, source identity, and exact next unit. Resume that cursor on the next run. Do not reset because the weekly URL changed; find the new edition by following the same landing page.
6. Broad search is an **exception**, not default: allow it only if the catalog's working links fail, the edition is missing/unreadable, a local market conflict needs resolution, or a previously identified source has moved. Search a narrowly scoped exact edition/market query, verify it, and update this catalog only if it is a **better stable entrypoint**. Never save ephemeral dated CDN image URLs as long-term catalog roots.
7. After verifying source eligibility, inventory **all** flyer pages and departments, then perform the distinct source-first omission pass and existing value, quality, publication and Gmail checks. Do not claim completeness just because a summary grid loads. No first-baseline notification, missing-market guesses or fabricated hashes.

## Verified details and recurring pitfalls

- Metro Barrie Street #241 has a store page showing flyer dates. Its generic flyer page can default to an unrelated store, so **never** interpret the default selected store as Kingston.
- Food Basics official pages may yield 403; the Princess/Barrack/Gardiners/Hwy-15 stores are Kingston locations, but a current archive needs printed Ontario-market applicability. Flyerbox's local Food Basics listing was observed stale.
- Walmart #3043's official store page links the flyer. WeeklyFlyer has a legible **Ontario weekly edition** distinct from early-Black-Friday online and longer holiday catalogues.
- Loblaws Kingston is **Loblaws (ON)**; `Loblaws City Market`, No Frills and Real Canadian Superstore are different editions. Flyerbox's dated banner does not override printed ad dates.
- Shoppers' flyer is dynamically rendered; SmartCanucks identifies the current **Ontario** issue. Saturday-start promotions often differ from grocery Thursday-start cycles.
- Rexall SmartCanucks slug is **`rexall--canada`** (two hyphens). Its store #1529 and official postal-code locator are the local anchors. Do not use the invalid single-hyphen source as a success proof.
- Staples has two Kingston stores: #23 and #133. Verify store-specific promotions; official flyers, Deals Centre and Clearance Centre have distinct coverage.
- Costco #533 Kingston is a **regular warehouse**. The official coupons/savings listing is readable but **SAVE $** is a discount, not a cash checkout price; follow the existing warehouse-price and discount-only reporting policy. SmartCanucks separately indexes the Ontario regular-warehouse offer sheet, Quebec and Business Centre; use the Ontario edition as a backup host, not as checkout-price evidence.
- Flipp requires choosing a location and can error in noninteractive retrieval; it is an optional exception fallback, **not a higher-priority default**. General Kingston aggregator landings may list nonlocal chains and cached past flyers. Never use their city title alone as local validation.
- The catalog is public and includes only store locations and flyer URLs. Personal account data, preferences, recipients, and Gmail records remain private.

## Configuration integration

Each retailer's existing `sources` list contains its curated source list for compatibility with the current single-profile CLI. The **catalog's ordered sources and explicit store anchors control the connected scheduled task**; older miscellaneous URLs in documents are discovery references only. The catalog does **not** install a scraper, auto-select a store in an inaccessible JS widget, or imply live stock.

## Ontario-to-Kingston applicability decision (2026-11-17)

For an Ontario-wide **in-store** flyer from the same retailer/banner, with an established Kingston store anchor, **presume the Ontario edition applies to Kingston** unless the printed ad, store selector, retailer policy or credible conflicting local evidence says otherwise. Record the scope, store anchor, printed dates and any exclusion. This is an applicability presumption, **not** proof of stock, item size, cash price, or a separate online-only offer. Do not require an item-by-item Kingston store-page confirmation when the printed Ontario flyer has no exclusion.

When the edition is explicitly regional (Toronto-only, GTA, selected stores), conflicting, or ambiguous, perform a **targeted** web lookup combining retailer, Kingston, flyer dates and disputed product/region; use an independent source when available. Exclude unresolved conflicting items, rather than blocking every uncontroversial Ontario offer. Continue to distinguish banners, online-only offers, member conditions and Costco savings from cash prices.
