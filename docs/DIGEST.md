# Shopping roundup and email contract

This is the current, runtime-neutral contract for selecting and presenting a qualifying
retailer update. It takes precedence over older references to 5-10 highlights, one-item
roundups or universal shipping eligibility in other documents. It does not relax source
verification, notification gates, privacy or duplicate prevention in the runbook.

## Two separate decisions

1. **May an alert be sent?** There must be a verified new edition or material advertised
   offer change against an established comparable baseline, plus useful verified value.
2. **What should its shopping roundup contain?** Research and assess **8-10 distinct
   offers for each qualifying changed retailer/flyer**, not just the item that passed
   the notification gate.

A single useful offer may satisfy the value gate; it is not a reason to stop investigating
an entire flyer. The 8-10 budget is per retailer, never shared across all changed stores.
Three qualifying changed retailers produce 24-30 assessed entries per recipient across
those digests. Preserve the existing separate-message and recipient-specific retry rules.

Most entries should be useful buys. Include outstanding bargains, modest verified savings,
and sensible everyday-value purchases rather than demanding a spectacular discount for
all items. A meaningful smaller saving must not be dismissed merely for falling below an
unstated percentage, cash-saving or trip threshold. An advertised sale label still does
not prove value; compare like brands, pack sizes, models, cuts and actual purchase terms.

Once a new edition qualifies, useful offers repeated in that newly issued flyer may be
included in its roundup. Do not claim they are newly reduced, and do not use their unchanged
price as an independent alert trigger. This is a roundup of a qualifying edition, not a
requirement that every listed item pass an independent change detector.

## Selection and counting

Use these sections as appropriate:

- **Best buys**: the strongest verified values.
- **Worth buying**: practical purchases, including modest savings and good everyday value.
- **Not worth treating as headline bargains**: weaker or conditional advertised offers
  whose comparison is useful to a shopper. Be specific about why they are less compelling.

Entries in the last section count WITHIN the same 8-10 total. They are not an additional
allowance, and the list should not be filled mostly with poor deals. Do not describe weak
prices as good merely to hit a count. A conditional offer can be a worthwhile buy when its
actual requirements are clear; membership alone does not make a deal weak.

Investigate more of the flyer and appropriate sources before falling short. Do not split
flavours/colours of one promotion into filler or count the same product twice because it
appears on multiple pages. Category discovery remains unrestricted, particularly for Staples.
Use the 8-10 target for collection-triggered retailer roundups when supported by comparable
verified offers too, without generating alerts for unchanged collections or repeated items.

If evidence genuinely supports fewer than eight distinct useful or meaningfully assessed
entries after reasonable investigation, report only the verified set and state the specific
coverage shortfall briefly. Never invent prices, pack equivalence, offers, stock or eligibility.
An empty or unavailable source is not a verified no-change result.

## Private ranking context stays private

The collector/orchestrator may use privately configured shopping preferences and practical
accessibility to rank useful purchases. Never invent travel costs, times, locations or
purchase thresholds. Honor the privately allowed fulfillment channels; source membership
alone does not make an online-only offer actionable. A website price is not proof of an
in-store price or local pickup stock.

Do not publish actual personal preferences, relative distances, travel modes, home-store
associations, convenience/travel-cost calculations or private selection rationale. Keep
those values out of emails, reports, commits, configuration examples and other recipients'
messages. Public price comparisons, pack sizes and factual purchase-channel conditions can
be shown without personal context. Another runtime needs separately supplied private settings.

## Compact email layout

Use `automation/digest-template.md` as the structural example. It contains nine placeholders,
not real prices or a required fixed split between sections. Replace them only with verified
entries and remove unused placeholders.

- Header: retailer, real start/end dates and a short future-start note when appropriate.
  Currency may be stated briefly in the header; do not add a currency/disclaimer footer.
- Each entry: product + exact size/model, cash price, useful unit price or short comparison
  and verdict, with purchase-critical requirements inline. Usually one tight line or sentence.
- Conditions: retain actual membership/coupon requirements, minimum quantities, short sale
  windows, final-sale terms or material availability limitations beside the affected item.
  Do not erase facts that change the purchase decision.
- Closing: a compact public report/source link, not a liability statement.

No closing sentence beginning **Prices CAD.**, and no replacement blanket disclaimer about
prices changing, stock, liability or checking everything at purchase. No long monitoring
methodology, gate explanations or repeated source paragraphs in email. The public report
may retain a separate source-evidence section, but its shopping lineup should use the same
clear categories and practical assessments. Keep material uncertainty item-specific.

Do not use a heading that excludes other advertised items merely because they did not
justify sending the message. Notification authorization is internal orchestration, not
shopping advice. Never include private travel mechanics in the public explanation.

## Delivery and migration

This policy does not change checking frequency, enabled/paused state, sender or recipients.
It does not authorize setup, test, backfill or duplicate email. A format/ranking change is
not a retailer offer change. Do not resend an already-handled edition or reset its identity
because a roundup becomes longer. Any revision to a public report is an editorial revision,
not new evidence of an advertised price change.

The connected agent applies this contract directly. A VM or another coding agent should
apply it in its collector/digest renderer after change detection and before transport.
The existing dated-flyer CLI's generic archival renderer and SMTP transport are not a live
research or private-preference engine, and this documentation/template update does not
implement a new collector or replace their formatter automatically. Keep source snapshots,
private selection decisions and public shopping output distinct when implementing an adapter.
