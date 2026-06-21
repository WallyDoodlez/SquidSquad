# QA-RESULTS-13179 — progress_liveness unbounded 'booting' escape (shadow-only)

**Verifier**: qa
**Date**: 2026-06-21 19:42
**Verdict**: PASS — zero gaps. Status → Pending Ship.
**Change under test**: PR #13191, branch `squidsquad/task/13179` (harness.py + tests).

## AC walk (issue body AC1–AC5)

| AC | Result |
|----|--------|
| AC1 wedged-boot-timeout past grace, booting within | PASS |
| AC2 config-tunable threshold, same pattern as ACTIVITY_GRACE_SECONDS, documented ~600s | PASS |
| AC3 regression test that would have caught the unbounded escape | PASS |
| AC4 no reboot behavior change (shadow-verdict-only) | PASS |
| AC5 shadow logging surfaces the new verdict | PASS |

## Test Cases (isolated worktree of the branch)

### TC-1 (AC1) — verdict bounds — **PASS**
`test_not_booted_past_boot_grace_is_wedged` (→ `(False,"wedged-boot-timeout")`),
`test_not_booted_within_boot_grace_is_alive`, `test_not_booted_at_grace_boundary_is_alive`
(== grace stays booting; strictly-exceeds required), `test_not_booted_boot_time_fallback_when_no_spawn`
all PASS. Code: ages from `last_spawn_at` (fallback `boot_time`); `> BOOT_GRACE_SECONDS` → non-alive; no spawn ref → conservatively booting.

### TC-2 (AC2) — documented tunable — **PASS**
`BOOT_GRACE_SECONDS = 600  # 10m` named module constant with doc comment (harness.py), matching the
existing `ACTIVITY_GRACE_SECONDS = 600` pattern (itself a bare named module constant, L176). Not a
magic inline number — "don't hardcode bare" intent satisfied.

### TC-3 (AC3) — regression catches the escape (pre-fix proof) — **PASS**
Pre-fix (origin/main) `progress_liveness` for bootup_complete=False, age 700s > grace returned
`(True, 'booting')` — the unbounded escape (qa sat bootup_complete=False ~54m). Post-fix returns
`(False, 'wedged-boot-timeout')`. The new test asserts the post-fix verdict → catches the bug.

### TC-4 (AC4) — shadow-only, no reboot change — **PASS**
Health poller (harness.py:725-740) compares `prog_alive` to PID `alive` only for the shadow LIVENESS
DIVERGENCE log: "This does NOT change `alive` or the reboot decision." Diff touches no reboot path; PID
authoritative until #12492 cutover.

### TC-5 (AC5) — shadow logging surfaces verdict — **PASS**
Poller divergence log includes `({prog_reason})` (harness.py ~737), so `wedged-boot-timeout` is logged
when PID-alive disagrees — sharper #12492 cutover data.

### TC-6 (no regression) — full gate — **PASS**
progress_liveness module: 28 passed. Full `tests/run_tests.py`: `4896 passed, 17 skipped, 12 subtests passed`; static-gate verdict `PASS — 4925 gated test(s) passed (0 failures, 0 errors)`.

## Coverage matrix
- AC1→TC-1, AC2→TC-2, AC3→TC-3, AC4→TC-4, AC5→TC-5, guard→TC-6 ✓

## Notes
Deterministic harness code — no CQ. Tests ship under `tests/` (preserved). No HUMAN-REQUIRED TCs.
Motivating symptom (this clone's earlier 54-min boot wedge) is now bounded in the shadow verdict.
