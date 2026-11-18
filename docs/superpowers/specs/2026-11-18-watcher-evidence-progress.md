# Watcher evidence-progress design — 2026-11-18

## Observed failure
The existing native hourly task has a validated private checkpoint (sequence 32) but no end-to-end retailer completion. All enabled profiles have empty live collector argv. The public `continuation.plan` only recommends research; the checkpoint keeps short page markers, not reusable item facts. Runs can therefore repeat source/prerequisite review without creating usable production input. The preceding invalid 112-character cursor was independently corrected and is not the remaining bottleneck.

## Required outcome
Within the **same native hourly task**, turn actual human/agent-inspected flyer products into compact, durable **public-only advertised facts**, and choose a single executable next action (and an independent second viable retailer only on blocker). Count a run successful only with actual completed quality stages or verified publication/delivery; a checkpoint increment alone is insufficient. Keep all source/market/edition/price and quality, immutable GitHub, privacy, recipient-specific Sent and write-ahead authorization requirements unchanged.

## Design
1. A standalone `advertised_facts.py` validates a batch of actually read retailer advertisements, rejects prohibited private/unsupported fields, exact cash price/pack/date/clean URL inconsistencies, and emits a canonical content-addressed **public advertising-facts snapshot** plus proposed create-only repository path. No source retrieval, upload, source-coverage flag or email is performed by this module. The existing task must verify live source observations and manually check the public projection before using connected GitHub to create the file. Such fact chunks can be reused across runs for evidence-led baseline/value work; they never prove full inventory/omission coverage.
2. A small `work_ticket.py` accepts the validated private checkpoint, actual current eligibility/viability and previous run's real progress, then proposes one primary next action: recover unfinished publication; process verified near-expiry candidates; move to structured source-fact capture; or rotate after a verified blocker. Refreshing a six-hour-old source proof is an action performed **inside** the chosen stage, not a stage restart or reason to reread every unrelated document. No invented eligibility, silent source conversion, mail or publication authorization.
3. The existing automation instructions shall reference these commands, prioritize one *real evidence-to-check* stage per execution and omit repeat broad doc-fetches when the pinned main commit did not change. Critical current source catalog, active policy/source rules, task instructions, and private mail facts remain authoritative and are checked at run start.

## Non-goals and hard limits
- No new scheduler, VM, GitHub Actions mail, SMTP, database, notification relay, Gmail test, or runtime cutover.
- No invented live product facts, hidden diagnostics, private source attempts or personal preferences in public GitHub. Snapshot content is **advertising-only** and cannot authorize shopping advice.
- No automatic interpretation of a verified Ontario region as current stock, or a wholesale savings amount as a cash price.
- This does not create a universal flyer scraper or promise that every store can be completed without access to actual original pages/grids.
