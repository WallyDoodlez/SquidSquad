# TEST-PLAN #13433 — git_ops.py pr-merge --help footgun

**Derived independently from the issue "Suggested fix" ACs — not from the diff.**
(This was my own prior-session improvement-scan finding.)

Bug: `git_ops.py pr-merge --help` consumed `--help` as the PR number → printed a
false `PR #--help merged (squash)` AND ran the post-merge scope-audit/compose,
regenerating 8 composed `.squidsquad/*/CLAUDE.md` files (dirtied the tree on a
no-op help request).

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | `-h`/`--help` (anywhere relevant) → subcommand usage, **no side effects** |
| AC2 | pr-merge PR-number validated as integer **before ANY merge/compose work**; clean error on non-numeric |
| AC3 | A malformed invocation must **never** trigger the compose/scope-audit side-effect |

## Live verification (real git_ops.py on branch squidsquad/task/13433)

| TC | AC | Command | Expected | Result |
|----|----|---------|----------|--------|
| TC1 | AC1 | `pr-merge --help` | exit 0, usage | **PASS** (EXIT 0) |
| TC2 | AC2 | `pr-merge notanumber` | exit ≠0, "no merge attempted" | **PASS** (EXIT 2) |
| TC3 | AC2 | `pr-merge --strategy squash` | exit ≠0 (flag in num position) | **PASS** (EXIT 2, "invalid PR number '--strategy'") |
| TC4 | AC1 | `pr-merge -h` | exit 0, usage | **PASS** (EXIT 0) |
| TC5 | AC3 | git status before/after the 4 commands | **zero tree churn**, no CLAUDE.md regenerated | **PASS** (IDENTICAL) |

## Independent regression test (`TEST-13433-tests.py`, black-box subprocess)

8 cases — complements the worker's white-box `pr_merge`-spy tests. Adds edge tokens
`12abc` (partial-numeric) and `-5` (negative) beyond the worker's set. All PASS.

## Coverage matrix
- AC1 → TC1, TC4, top-level `-h`
- AC2 → TC2, TC3, missing-number
- AC3 → TC5 (zero tree churn — the decisive check)

Not LLM-consumed instructions (pure Python) → no comprehension spec.
