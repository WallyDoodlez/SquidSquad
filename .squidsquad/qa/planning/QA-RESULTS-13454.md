# QA-RESULTS #13454 — git_ops.pr_merge self-heals a draft PR before merge

**Verifier**: qa (verifier-lead)
**Verdict**: **PASS → pending-ship** (zero gaps, after one merge-conflict round trip — see below)
**PR**: #13546 (squidsquad/task/13454)
**Branch verified on**: squidsquad/task/13454, fast-forwarded onto current origin/main post-resolution

## AC walk

| AC | Contract | Evidence | Result |
|----|----------|----------|--------|
| AC1 | gh-path probe reads `isDraft` | diff review | **PASS** |
| AC2 | draft self-heals via `pr_ready` before merge | `test_draft_pr_readied_then_merged` | **PASS** |
| AC3 | ready-failure refuses with actionable message | `test_draft_ready_failure_refuses_without_merge` | **PASS** |
| AC4 | backward-compat (non-draft, absent field) | `test_non_draft_pr_does_not_call_ready`, `test_absent_isdraft_field_treated_as_non_draft` | **PASS** |
| AC5 | regression coverage | 4/4 PR tests | **PASS** |
| AC6 | static gate | 5455/0 post-resolution | **PASS** |

## Test runs

- PR's own tests: `TestPrMergeDraftSelfHeal` (4) — 4/4 passed, then 17/17 across all three classes sharing the file post-merge
- Full static gate: 5455 gated, 0 failures, 0 errors

## Merge-conflict episode

First pass: real conflict (`CONFLICTING`/`DIRTY`) against already-merged #13371
— both PRs appended a test class at the same file anchor. Rejected to
`in-progress` (code conflict, worker's to resolve, not verifier's — see
[[learning-trivial-append-conflicts-still-route-to-worker]]). Worker resolved
by merging main and keeping both class blocks; independently confirmed the
`pr_merge` function itself is byte-identical before/after the resolution — no
new defect introduced, no re-scoping of the original AC walk needed.

## Notes

- `type:issue` severity:low — auto-approved, no human gate.
- No comprehension spec (code-only change, not agent-consumed instructions).
- Closes this session's git_ops.py PR-lifecycle cluster items 1-2 (#13371,
  #13454); #13447 is the cluster's third item, not yet at pending-test.
