# TEST-PLAN-10540 — DM batch-ship "Base branch was modified" race

**Issue**: #10540 (type:issue, severity:medium, role:skill) — 8/10 PR merges fail with "Base branch was modified" when a deep ship queue drains.
**PR**: #13144, branch `squidsquad/task/10540` (no closing keyword). **CQ**: none (deterministic code).
**Timely**: this is exactly the failure that will hit when DM (#13139) reboots into the current 6-item backlog.

## ACs
- **AC1** `pr_merge` retries the transient "Base branch was modified" error (base SHA moved by a prior batch merge) with a settle delay, so a serially-dispatched deep queue drains.
- **AC2** a REAL merge conflict ("merge conflict"/"not mergeable") is terminal — NEVER retried (routes back for rebase). Conflict guard checked BEFORE the race retry.
- **AC3** retries are bounded; on exhaustion returns honest failure (not silent, not mislabeled as conflict).
- **AC4** a race that surfaces a real conflict on retry becomes terminal.
- **AC5** no-regression: full static gate green.

## Test cases
| TC | Scenario | Expected |
|----|----------|----------|
| TC1 | base-modified ×2 then success | merged; 5 _run_list calls |
| TC2 | base-modified all attempts | (False, "merge failed: ...Base branch was modified"); 4 merge attempts |
| TC3 | real conflict | (False, "merge conflict"); exactly 1 merge attempt (no retry) |
| TC4 | base-modified then real conflict | (False, "merge conflict"); terminal on the conflict |
| TC5 | happy path single merge | unchanged |

## Method
1. Read git_ops.py pr_merge diff — confirm conflict-guard-before-retry ordering, bounded loop, honest exhaustion.
2. Run test_git_ops.py PrMerge.
3. Full static gate.

## Pass condition
All ACs PASS; conflict-never-retried confirmed; bounded; zero-gap; static gate green.
