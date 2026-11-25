# Abandoned run recovery implementation plan

Goal: break RUN_STARTED recovery loops without fabricating retailer progress or weakening native delivery safeguards.

- Reproduce missing recovery action on the pinned controller; use synthetic records in public tests.
- Add a recovery bundle command for empty RUN_STARTED only. Require verified canonical sequence, no unresolved native delivery, no other active writer, and actual terminal or strictly later completed native invocation evidence. Unknown historical outcome remains unknown. Never recover pending operations via this path.
- Generate append-only recovery history and optional new START plus handoff and journal in one local command. Stable keys and bodies make retries idempotent. Persist/read back history and handoff first, then journal; do not start research until journal readback. No network or external writes in controller.
- Test matching and superseding evidence, unknown/out-of-order/active records, pending and saved results, uncertainty, stale revision, sequence drift, repeated crashes, history replay, and optional initialization.
- Commit tested public files using expected HEAD, verify blobs, update private cache and reconcile actual abandoned state with independent readback. Keep native checkpoint, schedule and all publication/email gates unchanged. Verify actual scheduled execution separately.
