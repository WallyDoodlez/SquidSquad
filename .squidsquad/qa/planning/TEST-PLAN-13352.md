# TEST-PLAN-13352 — test runs leak into live surfaces

**Issue**: #13352 (verifier-filed, severity:medium, type:issue — auto-approved lane)
**PR**: #13372, branch `squidsquad/task/13352`, head 4fece99fc
**Derived from**: the issue's Behavior/Impact/Ask sections (I authored the issue; the asks are the ACs). Independent of the worker's diff.

Issue asks → ACs:
- **AC1** (find + isolate the bus-event writer): a test/experiment run must not be able to post events onto the production bus. Observed leak: fabricated issue-87654 `status-transition` events.
- **AC2** (find + isolate the port-file writer): a test/experiment run must not overwrite `.squidsquad/.harness-port` in live agent clones. Observed leak: 8251 in the qa clone.
- **AC3** (scratch artifacts, added via my 2026-07-06 23:21Z evidence comment): experiments must not write scratch into live `.squidsquad/` clone surfaces. Observed leak: `.squidsquad/skill/planning/wt-env-probe.txt`.
- **AC4** (consider port clearing/liveness at harness boot): either implemented or explicitly assessed with the residual gap tracked in its own lane.
- **AC5** (implicit zero-gap): regression tests for each class; full static gate green; landing safe.

## Test cases

- **TC-1 fixture isolation (AC1)**: `env_with_gh_shim()` must set `SQUIDSQUAD_DIR` by default to an isolated location with NO port file (bus emits become silent no-ops). Code-read + run the worker's isolation tests, incl. the end-to-end subprocess no-port-discovery case.
- **TC-2 live-surface E2E (AC1+AC2+AC3, real live instance)**: snapshot the live `.squidsquad/.harness-port` (content+mtime) and the live bus cursor head; run the affected 9398 integration suites (the family whose run produced the 09:54 leaks) on the branch; then assert (a) port file byte-identical, (b) zero new events on the live bus past my snapshot, (c) zero new files under any live `.squidsquad/*/planning/` or clone scratch surfaces.
- **TC-3 harness distribution guard (AC2)**: `_distribute_port_to_clones()` runs only when `SQUIDSQUAD_DIR` resolves to the repo's live `.squidsquad`; isolated harness logs a skip and writes nothing; production path still distributes (self-exclusion non-vacuous).
- **TC-4 experiment scratch (AC3)**: zero cwd-relative `.squidsquad` write paths in `references/experiments/`; scratch confined to `tempfile` locations; source-level ban test present and passing.
- **TC-5 regression suite (AC5)**: `tests/test_13352_test_isolation_leaks.py` — all pass on branch HEAD.
- **TC-6 static gate (AC5)**: full `run_tests.py static` on branch HEAD.
- **TC-7 landing safety (AC5)**: base main, no unexpected deletions, no fleet/state artifacts.
- **TC-8 ask-4 disposition (AC4)**: verify the claim "production harness rewrites every clone's port file at each boot" from harness.py code on the branch; confirm the residual agent-side stale-port gap is tracked open in #13356.

Every TC: PASS / FAIL / HUMAN-REQUIRED. Zero-gap gate applies.
