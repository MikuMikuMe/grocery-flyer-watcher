# Public automation runbook (no private identifiers)

The private ChatGPT task manages cadence, email delivery and deduplication. The public GitHub repository stores only store/deal data, reference logic and public reports.

1. Verify the latest valid Metro Ontario flyer for Kingston through a public Flipp/Metro source. Check dates, edition identity, item prices and exact size. Keep a clean public URL without personal query parameters.
2. Compare the live edition and material advertised offers against this repo's `data/latest.json`; no difference means end silently, without mail, chat alert or commit.
3. For an update, select standout values, compare unit price/kg or unit count, shelf life and truly matching alternatives in Kingston. Distinguish high-value, conditional and weak promotions.
4. Draft a practical and source-linked digest including flyer expiry. If data is unverified or source access fails, do not invent a price or mark the check complete.
5. Publish a fully validated public snapshot and a dated `reports/` analysis; check that the commit succeeds. If any non-sensitive analysis/runbook logic changes, commit corresponding runbook and test changes as well.
6. Check private Gmail sent-mail history with a deterministic flyer-ID/content-digest marker before sending. Send the report through the connected private account to the private task's designated recipient once. Do not put sender/recipient, message IDs or delivery logs in public GitHub.
7. Notify the user privately in ChatGPT with top deals, expiry and public report link. If a step fails, explain privately and retry safely on the next run; avoid duplicate email and alerts.

The task must not change public data, deliver new-sale notices or claim success when flyer identity and offers cannot be verified.