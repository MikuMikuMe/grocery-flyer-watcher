# GitHub/Gmail history adapter — existing connected task only

Use docs/GITHUB_STATE.md for state storage and delivery authorization. It takes precedence
for the connected task over the older mandatory private SQLite journal, `quality authorize
--journal` and `quality ack` instructions. Preserve the current schedule, enabled/paused
state, every retailer/source scope and all private sender/recipient/preferences. No new task,
private repository, database or external service is required or authorized.

GitHub is the public comparison/assessment history; Gmail Sent is recipient-specific delivery
evidence; existing private task/tool history records actual attempts and eligibility. Never
publish contacts, recipient-derived identifiers/counts, message data, delivery flags, private
preferences or a SQLite file. Do not replace missing history with fabricated records.

Keep the real source-first quality review, omission pass, check/build and pinned-publication
preflight. For genuinely qualified changes, generate a public-flyer-assessment-v1 through
repository_delivery assessment and publish its create-only stable event path with the generated
selection/report in one commit. Preserve old baselines and handled editions silently. An old
report, an expanded shortlist or absence from Sent is not itself qualifying/pending evidence.

Use runtime_preflight --state-backend github-gmail. Missing persistent local SQLite storage
must not block this mode. Restore the current runtime via actual pinned connector reads and
include repository_delivery.py in the verified runtime when required.

Immediately before each separate Gmail send, check actual private enrollment and run history
and perform the actual exact-recipient Sent search, including older edition formats and
identical cross-source offers. Run `python -m grocery_flyer_watch.repository_delivery authorize`
with the real immutable assessment, fresh proof of its GitHub read, canonical body, actual
Sent lookup and private context. Use no database or invented persistence attestations.
Only a fresh authorized result permits the matching Gmail recipient/subject/body. Acknowledge
outcomes in the existing private task history; do not call SQLite-only ack for this mode.

One actor at a time. No parallel manual and scheduled sends. On uncertain provider acceptance,
reconcile actual provider/Sent evidence; never infer safe retry from an empty search alone.
Continue independent retailers/recipients. No claim of atomic exactly-once delivery across
GitHub and Gmail. A future concurrent VM may retain the existing journal adapter separately.

This change authorizes no test email, immediate deal run, old-digest backfill or baseline reset.
All privacy, expiry, actual value, source coverage, compact 8-10-per-retailer and silent
no-change rules stay in force. New recipient enrollment remains private and does not backfill.
