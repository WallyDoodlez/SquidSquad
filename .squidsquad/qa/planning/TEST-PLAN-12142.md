# TEST-PLAN-12142 — Uncommitted WIP lost across context-pressure reboots

**Derived independently from issue #12142 AC list (not the worker's diff).**
Verifier: qa · Created: 2026-06-14 00:40 · PR under test: #12270 (head `squidsquad/task/12142`)

## Acceptance Criteria (from issue body)

- **AC1** — A large task that triggers a mid-cycle context-pressure reboot RESUMES on the next cycle (work preserved), not restarts.
- **AC2** — Either agents commit WIP incrementally before exit-42 AND/OR cycle_pre preserves uncommitted WIP across the sync (no silent stash-strand / no WIP-losing checkout).
- **AC3** — Regression: simulate reboot mid-task with uncommitted changes → changes present (committed or restored) next cycle.
- **AC4** — #11511 Part 2 completes (proves the loop is broken).

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC2 | Source inspection: `_preserve_wip` wired at top of `cycle_pre.main()` before `_enforce_branch` and `_do_pull` | Call ordering preserve < enforce < pull |
| TC-2 | AC2 | Verify git_ops dependency subcommands exist (`has-changes`, `commit-code`) | Both present in git_ops.py |
| TC-3 | AC2 | Verify output-string contracts the fix branches on (`"Committed code"`, `"true"`) | git_ops prints match the substring checks |
| TC-4 | AC1/AC2 | Live (un-mocked) `_get_branch_name` resolves fallback | `squidsquad/task/12142` (= #6526 canonical, matches task-begin) |
| TC-5 | AC1/AC2 | Live (un-mocked) issue-number regex parse across task-string variants | `#N`, `N`, `# N`, em-dash → number; prose/none → no-op |
| TC-6 | AC1/AC2 | Live `git_ops.py has-changes` against real tree | returncode 0, prints `true`/`false` |
| TC-7 | AC3 | Unit: `test_preserves_code_wip_when_in_progress_and_dirty` (dirty + in-progress → commit-code on canonical branch) | PASS |
| TC-8 | AC3 | Unit: `test_runs_before_enforce_branch_in_main` (regression guard on ordering — would have caught the original bug) | PASS |
| TC-9 | AC2 | Unit: fail-open + no-op edge cases (clean / not-in-progress / no-task / unparseable / state-only / exception) | All PASS |
| TC-10 | — | Full project suite (`tests/run_tests.py`) — no regression in blast-radius file (cycle_pre runs every cycle, every agent) | OK |
| TC-11 | AC4 | #11511 status check | shipped / closed |

## Notes

- Fix takes the **AC2 "cycle_pre preserves WIP"** branch of the AND/OR — deterministic, independent of agent commit discipline.
- No LLM-consumed instruction files touched (Python + docstrings only) → no comprehension spec required.
- Tests added to existing `tests/test_cycle_pre.py` module (8 new `TestPreserveWip` cases) — correct placement for a cycle_pre extension; preserved permanently.
