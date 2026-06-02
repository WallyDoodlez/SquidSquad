## Worker/Skill Project Operations — SquidSquad

These instructions apply to the worker/skill agent on this project.

### Boot & Queue

- **Run `tracker.py check-gh` at boot.** If it fails, report and halt.
- **Deterministic work queue — no cherry-picking.** Pick the first item returned by `tracker.py work-queue`. The script decides priority, not you.
- **Verifier-rejected items are highest priority.** Fix existing work before starting new.
- **Skip `design:needed` / `design:in-progress` items.** Wait for designer to complete.

### Branch + PR Workflow (#9478)

- **Use `git_ops.py task-begin` / `task-end`** for feature branch checkout/return.
- **Branch+PR is the only mode**: code goes to `squidsquad/task/<number>` (unified branch — PM and worker share one branch per task #5040), state to main via `git_ops.py commit-code` vs `commit-state`. Branch pattern configured in config.md `branch-pattern`.
- **PR flow enabled**: create PRs with full summary (`git_ops.py pr-create`). Check `review:human-required` label — if present, hold for human review instead of auto-merge.
- **Run `git_ops.py has-changes`** before transitioning to pending-test. If no changes, re-read the issue and apply the fix.

### Implementation Standards

- **Unit tests required for all new code.** Every new function, script, or module needs corresponding test cases. No pending-test without tests.
- **ALWAYS run smoke tests before submitting to the Verifier.** Run `python tests/run_tests.py` and confirm zero failures BEFORE transitioning to pending-test. This is non-negotiable — it is the heart of quality and stops the Verifier rejection turnaround cycle. If tests fail, fix them. Never push broken work to the Verifier.
- **Copy changed non-composed `references/` files to live `.squidsquad/`** (e.g., `statusline.sh`, `hints-*.txt`) after implementation so changes take effect immediately. For sub-skill templates and role files, run `compose.py deploy` instead.
- **Push back on missing planning artifacts.** If PM comments reference RESEARCH.md, CONTEXT.md, or TEST-PLAN.md you cannot find, stop and ask for clarification.

### Scanning & Vault

- **Improvement scan file targeting**: use `scan_index.py suggest-targets` for query-driven targeting. Scan source files belonging to the target project only.
- **Vault remember 4-gate logic**: write budget → dedup check → reusability → fresh context test. Max 2 writes per cycle.
- **Use `model: "sonnet"` for subagents.**

### Cross-Team

- **Cross-file issues directly to owning role** via `tracker.py create-issue --role [target]`. Don't wait for PM to discover and route.
- **Auto-merge enabled**: Verifier handles merge. Check for `review:human-required` before assuming auto-merge.

### Front-loaded planning for batched issue work

On every wake, **before touching any code**, look across the full set of issues currently assigned to you. If **any** of these is true, switch into front-loaded planning mode:

- 2+ open issues assigned to you, or
- a single issue whose body cites multiple findings (umbrella bug — e.g. the PRD-A/B/C DS-audit umbrellas #10751/#10752/#10753), or
- issues that touch the same file / module / sub-skill repeatedly.

**Front-loaded planning mode** — heavy work up front, mechanical execution after:

1. **Read everything first.** Read every assigned issue body, every cited CONTEXT / RESEARCH / AUDIT artifact, and the prior comments on each issue — end-to-end — before opening any source file with intent to edit. Skim-then-fix is the failure mode this rule exists to prevent.
2. **Identify systematic patterns.** What recurs across findings? A shared abstraction, a single protocol violation duplicated across modules, a common missing check, an identical fix recipe? Findings often look independent and turn out to share one root cause.
3. **Plan one strategy that resolves the whole set, not N fixes that resolve one finding each.** Heavy loaded up front (thinking, sequencing, edge-case enumeration) so execution eases out (the actual edits should feel mechanical because the strategy already settled the ambiguity).
4. **Publish the strategy before executing.** Post the plan as a tracker comment on the umbrella (or, if no umbrella, on the first issue you'll pick up). Cite which findings it covers, the order you'll execute, and what you'll defer with reasoning. This is your work contract — both for the verifier and for your own consistency.
5. **Then execute.** Re-plan only if execution surfaces something the strategy didn't anticipate — then update the comment with the revision, don't silently drift.

**Why**: fixing in isolation surfaces emergent contradictions during the last fix that force re-work of the first. Front-loading thought is cheap; re-doing landed work is expensive.
