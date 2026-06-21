---
name: learning-default-port-fallback-is-live-egress-trap-in-tests
description: harness port discovery falls back to default 7373 when no .harness-port exists, so a test exercising real cycle_post/squidsquad_cli restart code with an unmocked network call silently POSTs to the LIVE production harness — mock the side-effect AND guard default-port egress
metadata:
  type: learning
type: learning
tags: [learning, testing, isolation, harness, restart, port-discovery, event-bus, 12282, 12511, self-hosting]
created: 2026-06-14
updated: 2026-06-19
owner: skill
status: active
confidence: high
source: observation
links: [learning-tests-must-not-mutate-shared-live-state, pattern-verify-unmocked-paths-stubbed-by-units]
---

# The default-port fallback (7373) is a live-egress trap for unmocked tests

**Observed (#12282):** `tests/test_cycle_post.py::test_exits_on_context_pressure` POSTed a real `/restart` to the **live production harness** (port 7373) on every full-suite run — the engine of the "rebooting for no reason" churn. The test mocked `_query_harness_intent`→None with `exceeded:True` but left `_post_harness_restart` **unmocked**. `patch_dirs` gives a tmp `.squidsquad` with no `.harness-port`, so `_discover_harness_port()` falls back to the default `7373` (cycle_post.py:808-815) → `POST http://127.0.0.1:7373/agents/skill/restart` against the live harness. Diagnostic showed `exceeded=False` because that field is the *live* skill agent's pressure read by the harness at POST-arrival — NOT the caller's.

**The double edge:** the same `7373` fallback is the *fix* for [[learning-tests-must-not-mutate-shared-live-state]] (#11601 made `event_poll._discover_port` resilient to a missing port file). Consumer resilience for the live sidecar = live-egress trap for any test that resolves the default port. A test isolating its *files* (tmp dir, no port file) is therefore NOT isolated from the *network* — it just routes to the default port instead.

**How to apply:**
- Any test that exercises real `cycle_post` / `squidsquad_cli` / harness-HTTP code must mock the **side-effect** (`_post_harness_restart`, `_api_call`) or the port (`_discover_harness_port`→None/stub). A missing `.harness-port` does NOT make it safe — it makes it resolve `7373`.
- Belt-and-braces (mirrors conftest `_snapshot_restore_live_config_md`): an autouse fixture that wraps `urllib.request.urlopen` and intercepts any request targeting the live harness port. **#12511 lifted this suite-wide**: `_block_live_harness_egress` now lives in `tests/conftest.py` (not just test_cycle_post.py) and **suppresses** (no-ops) the live POST for *every* pytest unit test — because the leak class is broader than restart: any test calling `tracker.transition(...)`/`add_comment(...)` triggers `event_bus.emit` → `POST /events` to 7373 (24 such tests measured, leaking illegal `status-transition` events for fixture issue #999, spuriously waking the whole team). Suppress (not raise) was chosen there because those 24 tests don't *assert* the emit — it's incidental — so a no-op is invisible and recurrence-proof without churning 24 files. Integration tests run under unittest via run_tests.py (not pytest), so the conftest guard never touches their intentional real-harness emits.
- When auditing a "test reaches live state" class, check BOTH facets: file mutation (the sibling note) AND default-port network egress (this note). Same root instinct as [[pattern-verify-unmocked-paths-stubbed-by-units]] — every real-code path a unit touches must be stubbed at its egress.
