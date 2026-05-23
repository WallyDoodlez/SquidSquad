## Worker/Skill Project Operations — SquidSquad

These instructions apply to the worker/skill agent on this project.

### Boot & Queue

- **Run `tracker.py check-gh` at boot.** If it fails, report and halt.
- **Deterministic work queue — no cherry-picking.** Pick the first item returned by `tracker.py work-queue`. The script decides priority, not you.
- **QA-rejected items are highest priority.** Fix existing work before starting new.
- **Skip `design:needed` / `design:in-progress` items.** Wait for designer to complete.

### Branch + PR Workflow (#9478)

- **Use `git_ops.py task-begin` / `task-end`** for feature branch checkout/return.
- **Branch+PR is the only mode**: code goes to `squidsquad/task/<number>` (unified branch — PM and dev share one branch per task #5040), state to main via `git_ops.py commit-code` vs `commit-state`. Branch pattern configured in config.md `branch-pattern`.
- **PR flow enabled**: create PRs with full summary (`git_ops.py pr-create`). Check `review:human-required` label — if present, hold for human review instead of auto-merge.
- **Run `git_ops.py has-changes`** before transitioning to pending-test. If no changes, re-read the issue and apply the fix.

### Implementation Standards

- **Unit tests required for all new code.** Every new function, script, or module needs corresponding test cases. No pending-test without tests.
- **ALWAYS run smoke tests before submitting to QA.** Run `python tests/run_tests.py` and confirm zero failures BEFORE transitioning to pending-test. This is non-negotiable — it is the heart of quality and stops the QA rejection turnaround cycle. If tests fail, fix them. Never push broken work to QA.
- **Copy changed non-composed `references/` files to live `.squidsquad/`** (e.g., `statusline.sh`, `hints-*.txt`) after implementation so changes take effect immediately. For sub-skill templates and role files, run `compose.py deploy` instead.
- **Push back on missing planning artifacts.** If PM comments reference RESEARCH.md, CONTEXT.md, or TEST-PLAN.md you cannot find, stop and ask for clarification.

### Scanning & Vault

- **Improvement scan file targeting**: use `scan_index.py suggest-targets` for query-driven targeting. Scan source files belonging to the target project only.
- **Vault remember 4-gate logic**: write budget → dedup check → reusability → fresh context test. Max 2 writes per cycle.
- **Use `model: "sonnet"` for subagents.**

### Cross-Team

- **Cross-file issues directly to owning role** via `tracker.py create-issue --role [target]`. Don't wait for PM to discover and route.
- **Auto-merge enabled**: QA handles merge. Check for `review:human-required` before assuming auto-merge.
