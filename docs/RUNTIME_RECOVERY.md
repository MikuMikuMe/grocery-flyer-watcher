# Recover startup failures without weakening delivery checks

This is supplemental startup/recovery tooling for the existing live quality gate.
It does not add a second scheduler, a mail provider, a private-storage backend or new
permissions. It does not change advertised-offer verification or the send authorization
contract. Deployment requires publishing these files and applying the accompanying
instruction fragment to the existing task through an actual writable adapter.

## 1. Discover operations, not marketing descriptions

At the start of a run, inspect the CURRENT callable tool schemas. A targeted discovery
query may be followed by ONE unfiltered listing for the relevant app when inconclusive.
Record the actual action names and discovery evidence. Do not repeatedly rediscover the
same absent action or claim a function exists because the app description mentions it.

Treat these facts separately:

- App-specific approval setting (for example, Allow all actions).
- Provider-account connection and its permitted access.
- Actions actually exposed to this execution environment.
- A provider result confirming a real operation succeeded.

A successful profile read does not prove mail-send authorization. A repository's push
permission does not conjure a missing connector write method. An exposed send schema
means available to invoke, not successfully sent. An unknown or incomplete action listing
is not a confirmed missing capability. Never blame OAuth or ask for reconnection without
specific evidence of an authorization problem.

Use `python -m grocery_flyer_watch.runtime_preflight /private/capabilities.json` to classify
supplied observations. Input `callable-actions-v1` has `format`, an actual timezone-aware
`observed_at`, and `discovery`: one object per provider with `provider`, `complete`, the
actual `evidence_ref`, and fully qualified `actions` from callable schemas. Recognized
providers are Gmail, GitHub, GitHub_Auto_Project_Connector and Automations. Exact aliases
are in the implementation; add an adapter only after verifying a newly exposed schema.
Unknown function names are never synthesized or invoked. Observations expire after
15 minutes and may not be copied from another run or model response.

This validator does not discover tools itself. The executing agent obtains real schemas;
its observation file is not independent proof or permission to perform a side effect.
Synthetic tests must never be copied into actual run evidence.

## 2. Missing executable is a recoverable startup condition

Use the interpreter/module entry point instead of requiring a globally installed binary:

```sh
python automation/runtime_bootstrap.py \
  --root /private/runtime \
  --manifest /private/pinned-runtime-manifest.json \
  --cache /private/actual-connector-fetched-source \
  -- quality check /private/actual-bundle.json --config /private/retailer.toml
```

The manifest identifies the actual repository and immutable commit and contains the
Git blob identities for all nine production modules (including diagnostics.py). Obtain it from an actual pinned
GitHub read, not a guessed successful revision. The cache contains matching source bytes
obtained through the connector or an already authenticated archive. The helper validates
all bytes, restores only missing modules, and refuses to overwrite unexpected changes.
It needs no pip, setuptools downloads, network, credentials or globally installed command.
A restored runtime and a passing help probe do not authorize email.

After recovery, repeat the original quality check/build/preflight operation. Do not downgrade
to the old sender, rewrite factual claims to satisfy validation, or manufacture source reads.
If code fetch fails, try the already-authorized connector once; if the action is absent,
classify that limitation exactly rather than retrying an impossible invocation.

### When GitHub reads succeed but the Python cache is empty

The `cache_module_missing` code means a file was not actually present under
the requested `--cache` directory. A GitHub connector response is **not**
automatically a Python filesystem file. Do not infer a missing GitHub source
file, repeat the same empty-cache invocation or invent a file-read receipt.

The bootstrap also supports `--cache-stdin` as an alternative to `--cache`.
Fetch the **current pinned commit** through the actual callable GitHub connector.
For every path in the manifest's `git_blobs`, request `fetch_file` at that
exact commit with `encoding=base64`. Retain the actual connector response
and compare each returned Git blob SHA against the manifest. Transfer the
returned base64 content (including GitHub base64 line breaks) in one private
JSON object shaped as follows; `modules` must cover all missing paths:

~~~json
{
  "format": "pinned-connector-module-cache-v1",
  "repository_id": 1435089073,
  "commit": "<the actual full 40-character pinned commit SHA>",
  "modules": {
    "src/grocery_flyer_watch/__init__.py": "<actual connector base64 content>",
    "src/grocery_flyer_watch/__main__.py": "<actual connector base64 content>"
  }
}
~~~

These two module entries illustrate the structure only: include **every**
missing module in the actual manifest, including diagnostics and optional
modules where pinned. The JSON must be created from actual GitHub responses;
never insert placeholder source bytes into a production run. A host-side copy
or a direct stdin pipe is required; merely fetching files into a tool result
does **not** populate the Python process. If that transfer is unavailable,
classify the bridge as blocked rather than claiming restoration succeeded.

After transferring the real private bundle, invoke:

~~~sh
python automation/runtime_bootstrap.py \
  --root /private/runtime \
  --manifest /private/pinned-runtime-manifest.json \
  --cache-stdin \
  -- quality check /private/actual-bundle.json --config /private/retailer.toml \
  < /private/real-connector-module-bundle.json
~~~

An operator able to pipe connector responses directly can avoid the
intermediate JSON file. The stdin input is capped at 8 MiB, must match the
manifest's repository ID and commit, may include only manifest module paths,
and every decoded byte sequence still has to pass the original Git-blob hash
check **before any repair file is written**. Existing runtime edits remain
protected. The alternate transport neither changes source/quality policy nor
authorizes publication or sending. Keep runtime inputs and diagnostic logs
private, outside the public checkout. Do not place connector bundles in
GitHub, CI artifacts, Gmail or scheduled task prompts.

## 3. Private state is not a disposable cache

The preflight's optional `--journal` reads an existing SQLite journal without creating or
initializing it. It checks the production schema and existing scope history, not personal
rows in its output. Missing, corrupt, uninitialized and durability-unverified state are
distinct. A file existing in a temporary runtime is not evidence of persistence across runs.

`--persistence-proof` accepts a PRIVATE record with `kind` (`durable_mount` or
`existing_private_store`), `restore_ref` and `checkpoint_ref`. These must identify actual
operations on an already authorized state backend. The diagnostic deliberately labels
this as attested persistence, not cryptographic proof that an external backend is durable.
Existing per-scope, baseline, recipient and uncertain-delivery checks remain mandatory.

Restore the actual journal from its configured private store. If that location is not
configured, do not create an empty journal and declare recovery complete, import a guessed
history, expose state in public GitHub, or create a new service. Import genuine handled
history only under the existing documented migration procedure. No backfill is authorized.

## 4. Resume exactly the unfinished authorized work

Once startup and actual source verification recover, proceed through the existing live
quality gate, public artifact publication, commit-pinned verification, fresh recipient-specific
Sent search, quality authorization, exact-body send and provider acknowledgement.

Never infer a pending digest merely from missing Sent results. Never retry an ambiguous
send before reconciliation. Do not automatically substitute SMTP or a different authenticated
account because a Gmail operation is unavailable. Continue independent research for other
profiles even when one source or side effect is blocked.

A missing task-update operation prevents changing the schedule's instructions, but does
not itself block an otherwise authorized deal delivery. Do not create a replacement task.
A permission problem, absent action, missing runtime, source-verification gap and unavailable
private state should never be combined into a generic 'read-only' or 'unchanged' claim.

## 5. Tests and truthful rollout status

`tests/test_runtime_recovery.py` exercises offline module restoration, integrity failures,
partial/stale discovery, capability/approval distinction and read-only journal diagnostics.
The deployed production modules are unchanged. Tests use synthetic data and send no mail.

This module adds operational checks, not a platform capability switch. Direct Gmail and
GitHub action availability is controlled outside the repository. A locally passing patch
is not a published commit or a saved task change; verify both actual results before saying
it is live. Report a persistent actionable platform blocker once with exact observations,
not repeated speculative reconnection advice or invented success.
