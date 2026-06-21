# TEST-PLAN-12526 — start.ps1/start.sh clone-sync uses 'git pull --rebase'

Bug (type:issue/medium, auto-approved), filed by pm. PR #12993, branch
`squidsquad/task/12526`, role:skill. No explicit AC list → ACs derived from the
issue's Expected + Scope. shell-launcher infra → **no CQ**. Verified in isolated
worktree `D:\Dev\Dev\sq-12526-verify`.

## Derived ACs
- **AC1 (fix):** start.ps1 + start.sh use the merge form `git pull --no-rebase` (NOT
  `--rebase`) in BOTH the primary-repo sync line AND the agent clone-sync loop —
  honoring the standing never-rebase rule.
- **AC2 (scope — no other launcher/script uses --rebase):** the issue requires verifying
  no other launcher/script still uses --rebase.
- **AC3 (regression test):** locks the no-rebase invariant on both launchers.
- **No CQ** — shell launcher scripts, no LLM-consumed instruction.

## Test cases / evidence
- **TC1 (AC1)** — diff: start.ps1 (primary L24 + clone loop L43) and start.sh (primary L42 +
  clone loop L56) all `--rebase` → `--no-rebase`. 4 sites total.
- **TC2 (AC2)** — repo-wide grep: NO `.sh/.ps1/.bat` uses `--rebase` post-fix; the only `.py`
  "rebase" hits are state_bus.py already on `pull --no-rebase` ("per operator rule") and
  git_ops.py `pull()` = merge. All remaining `--rebase` strings are historical PM planning
  .md docs (prose, not executable). Scope complete — only the 2 launchers had it.
- **TC3 (AC3)** — test_12526_launcher_no_rebase.py (no `--rebase` in either launcher + every
  sync pull uses --no-rebase, incl. belt-and-suspenders regex) + updated
  test_12525_bare_harness_launcher.py (TestFullLaunchersUntouched now asserts --no-rebase) → 20 passed.
- **TC4 (cross-test risk, #12912 lesson)** — 9 test files reference "rebase"; confirmed only
  test_12525 asserted --rebase PRESENCE in the launchers (PR updated it). Full static gate run
  to catch any other cross-test break (pending — see QA-RESULTS).
