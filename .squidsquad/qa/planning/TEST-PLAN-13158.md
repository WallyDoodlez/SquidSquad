# TEST-PLAN-13158

**Issue**: #13158 — harness deploy-signal git pull fatals on diverged main (no merge strategy); recurring deploy-error stage=pull
**Type**: type:issue (auto-approved), severity:medium, role:skill
**PR**: #13160 (branch squidsquad/task/13158 @ 01faacba9, base main; harness.py +27/-9 + test +20)
**Authored by**: verifier (qa), derived from issue observed-behavior + reproduction. Independent of PR.

## Derived Acceptance Criteria

- **AC1**: the deploy-sequence pull (`_run_deploy_sequence`) reconciles a diverged main via MERGE instead of fataling; a genuine conflict still fails → §11 recovery.
- **AC2**: regression test reproducing the divergence/command-shape (fails pre-fix on --ff-only).
- **AC3**: no regression (static gate).
- **AC4 (project rule)**: reconcile is MERGE, never rebase (--no-rebase, not --rebase).

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1/AC4 | Inspect harness.py diff | deploy-pull = `git pull --no-rebase --no-edit origin main` (was --ff-only); conflict→§11 preserved |
| TC2 | AC2 | Run test_harness_deploy_12912.py on fixed branch | 44 passed incl test_deploy_pull_merges_not_ff_only_13158 |
| TC3 | AC2 | Revert ONLY harness.py to origin/main, re-run #13158 test | FAILS (`'--no-rebase' not found in ['pull','--ff-only',...]`) — proves it catches the original |
| TC4 | AC3 | `python tests/run_tests.py static` | PASS, no regression |
