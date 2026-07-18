# Working State

- **Task**: none (between items). [2026-07-18 ~00:5x] Multiple in-flight handoffs — see below.

## IN-FLIGHT — resume triggers (do not lose)
- **#13577 pending-test, PR 1 of 2 (PR #13578 reworked guard-clean)**: on its pr-merged event → IMMEDIATELY do PR 2 of 2: fresh branch squidsquad/task/13577 (old one consumed by squash), apply the 2-hunk inject-permissions.ps1 em-dash→'-' fix (byte-parity with primary clone), passes the #13554 guard under the then-live predicate; pending-test again. This turns main's last red launcher test green.
- **#13574 in-progress (branch aeaa250f5, pushed)**: DONE — code + review fixes (timeout probe, ASCII prints, health-check/pipeline-sentinel additions) + Sonnet review applied (DS router misfired twice — reviewed stray .deepseek diffs; fell back per step-7.2). BLOCKED on: (a) PM authoring the CQ AC (asked on issue), (b) clean re-gate after #13577 PRs land (branch inherits main's launcher reds; own ASCII violation already fixed). Then: PR via pr-create + pending-test.
- **#13562 SHIPPED** ✔ (incl. threshold bump 70→75 landed c2034851d + dm reset 50bb6b323). #13556 SHIPPED ✔.

## Queue next
- #13579 (open, low): document #13562 size discipline in working-state.md sub-skill — instruction file → CQ gate; check body for CQ AC before implementing (if absent, ask PM first, same as #13574).
- #13575 (open, low, improvement-scan): comprehension-spec staleness check.
- Re-triage after: #13557/#13558/#13555 (low); #13552/#13551/#13354/#13356/#13316/#13317 CQ-gated; #13531 design-gated; #13447 cross-clone confirmation.

## Standing lessons (session additions)
- #13554 guard bootstrap: allow-list extensions land code-only FIRST, content follow-up second (documented in _pr_state_scope_violations docstring).
- TestPull-class suites MUST patch _restore_merge_dropped_state. Tests mocking _run_list must ALSO mock _run_list_timeout (tracker) — new call paths need new mocks, every time.
- NEVER tail-truncate a background gate's output; retain full log. Never chain DS review behind another command with & (shell exit kills it).
- model_router code-review can misfire onto stray .deepseek-*.diff artifacts — if findings reference files not in your bundle, treat as route failure → Sonnet subagent fallback.
- merge=ours/union modify-vs-DELETE gap now guarded by live post-merge hook (#13556). #11511 guard unstages .squidsquad/ on branches. MSYS mangles origin/main slash. State/vault = main-only.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative.

## Quiet Cycle Counter: 0
