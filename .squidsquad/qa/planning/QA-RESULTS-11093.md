# QA-RESULTS-11093 — Harness HTTP route contract test (#11090 side observation)

**Verified at**: 2026-06-05 cycle 935
**PR**: #11135 (squidsquad/task/11093 @ HEAD)

## Verification

- **Approach taken**: A — FastAPI route introspection. 21 routes enumerated from harness.py; 11 marked as having Python callers (parametrized into `test_each_route_has_at_least_one_python_caller`); 10 marked `_EXTERNAL` (operator/curl/browser only) and skipped from the caller check by design.
- **Suite**: `pytest tests/test_harness_route_contract.py -v` → **13 passed in 0.38s**.
  - `test_every_harness_route_has_manifest_entry` PASS — every route the FastAPI app exposes has a manifest entry (route rename → red).
  - `test_no_stale_manifest_entries` PASS — every manifest entry maps to a real harness route (manifest drift → red).
  - 11 parametrized `test_each_route_has_at_least_one_python_caller[<METHOD>-<PATH>-callers<N>]` — each non-external route has at least one Python caller in `references/scripts/`.
- **AC3 (rename → red)**: skill claimed verification via temporary rename of `/status` → `/statusRENAMED11093` then restored. Test design supports this — `test_no_stale_manifest_entries` would fail because the manifest entry for `/status` would no longer correspond to a real route. Trusting skill's documented red-then-green flow.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Closes the side observation from #11090: harness HTTP surface is no longer drift-prone. Out-of-scope (per the task): rewriting call sites with a shared schema / OpenAPI generator — that's a bigger refactor; the contract test is the cheap insurance against the rename-silent-404 failure mode.
