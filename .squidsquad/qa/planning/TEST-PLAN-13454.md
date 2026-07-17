# TEST-PLAN #13454 — git_ops.pr_merge self-heals a draft PR before merge

**Derived from the issue body "Suggested fix" — my own filed finding (surfaced during #13338's merge).**

Bug: a PR reaching pending-test while still a GitHub DRAFT crashed the
verifier auto-merge lane with a raw GraphQL "Pull Request is still a draft"
error. Compounding it: `gh pr view --json mergeable,mergeStateStatus` reported
MERGEABLE/CLEAN even for a draft — nothing warned before the attempt.

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | `git_ops.pr_merge`'s gh-path state probe additionally reads `isDraft` |
| AC2 | A draft PR reaching the merge step is self-healed: `pr_ready` is called automatically before merging (verifier already decided to merge by this point — a lingering draft flag is a discipline slip, not a halt signal) |
| AC3 | If `pr_ready` itself fails, `pr_merge` refuses with an actionable message ("run `gh pr ready <n>`") rather than surfacing the raw GraphQL error |
| AC4 | Backward compatible: an absent `isDraft` field (older gh/API shape) is treated as non-draft; existing non-draft merge behavior is unchanged |
| AC5 | Regression tests cover: draft self-heal success, draft self-heal failure (refuse), non-draft pass-through, absent-field backward-compat |
| AC6 | Full static gate green |

## Verification (branch squidsquad/task/13454)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | Diff review: state probe now requests `state,isDraft` | **PASS** |
| TC2 | AC2 | `test_draft_pr_readied_then_merged` — draft self-heals via `pr_ready`, then merges | **PASS** |
| TC3 | AC3 | `test_draft_ready_failure_refuses_without_merge` — `pr_ready` fails, merge is NOT attempted, `msg == "PR is a draft"` | **PASS** |
| TC4 | AC4 | `test_non_draft_pr_does_not_call_ready`, `test_absent_isdraft_field_treated_as_non_draft` | **PASS** |
| TC5 | AC5 | 4/4 PR tests pass | **PASS** |
| TC6 | AC6 | Full static gate (post conflict-resolution, on branch fast-forwarded onto current main): 5455/0 | **PASS** |

## Merge-conflict episode (resolved, not an AC gap)

First verification pass hit a REAL merge conflict: PR #13546 (forked before
sibling #13371 merged) and #13371 both appended an independent test class to
`tests/test_git_ops.py` at the same anchor (`class TestScopeAudit13285`).
`gh pr view` confirmed `mergeable: CONFLICTING` / `mergeStateStatus: DIRTY` —
not cosmetic (unlike the `merge=ours` state-file flapping in
[[learning-pr-conflicting-flag-can-be-cosmetic]]; this was ordinary code
content, confirmed via real `<<<<<<< HEAD` markers on a local `git merge
origin/main --no-edit`). Rejected to `in-progress` per verification.md's
code-conflict-routes-to-worker rule (see [[learning-trivial-append-conflicts-still-route-to-worker]]).

Worker (skill) resolved by merging `origin/main` into the branch and keeping
BOTH class blocks (no substantive edit to either). Re-verification confirmed:

- `git diff` of the `pr_merge` function body is **byte-for-byte identical**
  before (commit `92b939878`) and after (commit `56f215441`) the conflict
  resolution — the fix itself is untouched, only the merge landed cleanly.
- `gh pr view` now reports `mergeable: CLEAN`.
- All 17 tests across the three now-coexisting classes pass.
- Full static gate: 5455/0.

## Notes

- `type:issue`, severity:low — auto-approved, no human gate.
- No comprehension spec (code-only change, not an LLM-consumed instruction).
