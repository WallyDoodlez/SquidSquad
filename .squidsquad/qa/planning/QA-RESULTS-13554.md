# QA-RESULTS #13554 — pr_merge refuses a PR carrying main-only state/vault paths (SEV)

**Verifier**: qa (verifier-lead)
**Verdict**: **PASS → pending-ship** (zero gaps)
**PR**: #13559 (squidsquad/task/13554)
**Branch verified on**: squidsquad/task/13554 (built directly on latest origin/main — no staleness)

## AC walk

| AC | Contract | Evidence | Result |
|----|----------|----------|--------|
| AC1 | pre-merge declared-file scope check | diff review + live function call | **PASS** |
| AC2 | violation refuses before any merge action | `test_state_violation_refuses_before_merge` (call_count==1) | **PASS** |
| AC3 | plan-body + launcher exemptions preserved | `TestPrStateScopeViolations13554` (2 cases) | **PASS** |
| AC4 | fails open on undeterminable file set | `test_undeterminable_scope_fails_open` | **PASS** |
| AC5 | applies to all merge strategies | `test_state_violation_refuses_non_squash_too` | **PASS** |
| AC6 | regression coverage | 10/10 new tests | **PASS** |
| AC7 | no regression to existing pr_merge surface | 44/44 (existing + new) | **PASS** |
| AC8 | static gate | 5475/0 | **PASS** |

## The decisive check: live replay against the actual incident

Beyond the PR's own mocked unit tests, I ran the real `_pr_state_scope_violations()`
function directly against the **actual historical PR #13546** that caused this
incident (still queryable via `gh` post-merge). It returned exactly the 14
files the incident report named — `.ship-counter`, `.subloop-driver.json`,
`doc-scan-state.json`, `working-state.md`, and all 10 vault galaxy notes.
Zero omissions, zero extras. This is direct, unmocked proof the fix addresses
the real root cause, not just the mocked scenarios the PR's own tests describe.

I also ran the same live function against all 8 OTHER PRs I merged this
session — all `CLEAN`. The guard would not have wrongly blocked any of my
legitimate merges.

## Independent incident-recovery fact-check

PM's own verification thread had a false alarm from Windows/MSYS path
mangling before landing on the correct conclusion. I independently re-verified
the recovery from facts (not trusting the thread), using
`MSYS_NO_PATHCONV=1` to avoid the same trap: current `origin/main` has dm's
`working-state.md` at 817 lines, `.ship-counter` present, and all 10 named
vault notes present. Recovery confirmed intact.

## Test runs

- PR's own tests: 10/10 new (`TestPrMerge` additions + `TestPrStateScopeViolations13554`)
- Full pre-existing `pr_merge` surface: `TestPrMerge` (18) + `TestPrMergeArgGuard`
  (7) + `TestPrMergeDraftSelfHeal` (4) + `test_feat_1074_auto_merge.py` (5) —
  44/44, zero regression
- Full static gate: 5475 gated, 0 failures, 0 errors

## Notes

- `type:issue` severity:**high** — auto-approved, zero-gap standard applied
  without exception.
- No comprehension spec (code-only merge-gate change).
- PM already audited the sibling (#13353/PR #13553) as clean; I independently
  re-confirmed via the live function call (also `CLEAN`).
- This incident touched my own #13454 merge action earlier this session. I
  treated the live-replay-against-the-real-incident check as a hard
  requirement given the stakes, not a nice-to-have.
