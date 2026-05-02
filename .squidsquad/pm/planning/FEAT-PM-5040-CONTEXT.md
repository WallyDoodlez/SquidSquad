# FEAT-PM-5040 Context — Unified Branch Model

## Scope

Change branch pattern from `squidsquad/<role>/<number>` to `squidsquad/task/<number>` so PM, dev, and QA share one branch per task. PM creates the branch with PRD, dev adds code, QA verifies, one PR merges everything. Config-driven, L4 project override.

## Locked Decisions (human decided)

- **Config field + L4 reference**: Add `branch-pattern` to config.md under `## Git Branches`. Default: `squidsquad/{role}/{number}` (backward compat). This project overrides to `squidsquad/task/{number}` via L4. Scripts read config via `config.py`. Agent instructions say "use the configured branch pattern" — never hardcode.

- **task-begin prints branch name to stdout**: Agents capture the output and use it for commit-code, PR creation, etc. Eliminates all hardcoded branch patterns in agent prose instructions. Aligns with deterministic-scripts-over-prose vault pattern.

- **Status bar shows current branch**: PM, QA, and dev status bars should display the current git branch. This is an **L2 instruction** (role-level, applies to all projects). Goes in the common status bar sub-skill or role-level instructions.

- **Immediate cutover**: No migration window. Parsing is already pattern-tolerant (`squidsquad/*/NUMBER` matches both old and new). PR searches work for both. Clean cut.

## Dev Discretion (dev agent can choose)

- Factory function name and signature (`_get_branch_name` or `branch_name` or similar)
- How task-begin outputs the branch name (stdout line format)
- How agents capture the branch name (variable, file, or inline)
- Config field format details (e.g., `squidsquad/{type}/{number}` with `type` defaulting to role name)
- Status bar branch display format

## Side Effect Mitigations (required)

- **21 parsing/reference sites**: All must be updated. Use `parts[-1]` for issue number extraction (last segment) — works for both old and new patterns.
- **Agent prose instructions**: Remove all hardcoded `squidsquad/<role>/<number>` patterns from sub-skills and agent-instructions.md. Replace with "call task-begin and use the output."
- **cycle_pre.py QA input**: Lines 609/632 construct branch names directly — must use the factory function.
- **Existing open PRs**: Any open PRs on old-pattern branches at cutover time will still match searches. Close/merge before cutover if possible.

## Upgrade Path (required)

1. Add `branch-pattern` field to config.py FIELD_MAP and config.md
2. Add `_get_branch_name(role, number)` factory to git_ops.py reading config
3. Replace 4 construction sites with factory calls
4. Make task-begin print branch name to stdout
5. Update 21 parsing/reference sites to use `parts[-1]` for issue number
6. Update L4 project instructions to set pattern to `squidsquad/task/{number}`
7. Add L2 status bar branch display instruction
8. Update all sub-skill templates — replace hardcoded patterns with "use task-begin output"
9. Update 5 test files
10. Compose and deploy all agents

## Out of Scope

- Changing the state branch pattern (squid-squad) — stays as-is
- Multi-project branch namespacing — future concern
- Harness branch awareness (#4966) — separate task
