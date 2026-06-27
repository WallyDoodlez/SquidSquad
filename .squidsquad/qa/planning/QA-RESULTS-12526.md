# QA-RESULTS-12526 — start.ps1/start.sh clone-sync used 'git pull --rebase'

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-20 00:56 · **Verifier:** qa · PR #12993 @ de1eae87c · branch `squidsquad/task/12526`.

Bug (type:issue/medium, auto-approved), filed by pm. shell-launcher infra → no CQ.
Verified in isolated worktree `D:\Dev\Dev\sq-12526-verify`. Append-only.

## Fix summary
`--rebase` → `--no-rebase` at all 4 sync sites: start.ps1 (primary L24 + clone loop L43),
start.sh (primary L42 + clone loop L56). Honors the standing never-rebase rule.

## AC walk (derived; all PASS)
- **AC1 (fix)** PASS — diff confirms all 4 `git pull --rebase` → `git pull --no-rebase` across
  both launchers' primary + clone-sync lines.
- **AC2 (scope — no other launcher/script uses --rebase)** PASS — repo-wide grep: NO `.sh/.ps1/.bat`
  uses `--rebase` post-fix; the only `.py` "rebase" references are state_bus.py (already
  `pull --no-rebase`, "per operator rule") and git_ops.py `pull()` = merge. All other `--rebase`
  strings are historical PM planning `.md` docs (prose, not executable). Only the 2 launchers
  carried the defect; both fixed.
- **AC3 (regression test)** PASS — test_12526_launcher_no_rebase.py (asserts no `--rebase` in
  either launcher + every sync pull is `--no-rebase`, incl. belt-and-suspenders regex; the
  --no-rebase form also defends against a clone with `pull.rebase=true` configured) + updated
  test_12525_bare_harness_launcher.py (TestFullLaunchersUntouched now asserts --no-rebase) → 20 passed.
- **No CQ** — shell launcher scripts only.

## No-regression
- 20 affected tests passed. Cross-test risk (#12912 lesson): 9 test files reference "rebase";
  only test_12525 asserted `--rebase` PRESENCE in the launchers (PR updated it).
- Full static gate: `run_tests.py static` → **PASS — 4698 gated tests, 0 failures, 0 errors** (exit 0). Only the 2 allowlisted #10360 known-failures. No cross-test broke.

## Disposition
pending-test → pending-ship (DM). No closing keyword on PR #12993, no review:human-required → merge
deferred to DM. Counter NOT bumped. TEST-PLAN-12526 + QA-RESULTS-12526 on main.
