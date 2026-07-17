# TEST-PLAN #13554 — pr_merge refuses a PR carrying main-only state/vault paths (SEV)

**Derived from the issue body + PM/DM's incident RCA — HIGH severity, directly connected to my own #13454 merge this session.**

Incident: my merge of PR #13546 (#13454) squash-reverted 1328 out-of-scope
lines of teammate state+vault on main (dm's working-state.md, ship-counter,
10 vault galaxy notes) with zero conflict signal. Root cause (dm,
[[learning-merge-driver-defeated-by-delete-not-modify]]): `.gitattributes`
`merge=ours`/`union` only fires on modify-vs-**modify**, never modify-vs-
**delete** — the #13454 branch had these paths absent/emptied (a gap in the
#11511 commit-time guard for paths created after the branch's fork point), so
the squash saw a clean delete and took it. Neither the #13271 behind-count
guard nor the #13285 post-merge deletion-audit caught it (declared-file-set
gaps). Part 1 (content recovery) was handled by DM (#13556); this ticket is
the durable merge-gate fix (skill's to design).

## Acceptance Criteria (independent reading — high blast radius, merge-safety-critical)

| AC | Contract |
|----|----------|
| AC1 | `git_ops.pr_merge` gains a pre-merge check that inspects the PR's **declared** file list (`gh pr view --json files`) for main-only state/vault paths, BEFORE any merge action |
| AC2 | A PR declaring such a path is **refused** (fail-safe) — no merge attempted |
| AC3 | Legitimate exemptions are NOT blocked: PM's plan-body files (`.squidsquad/<role>/planning/<n>-body.md`, #12750) and the two launcher scripts (`.squidsquad/start.sh`/`.ps1`, #13318) |
| AC4 | When the PR's file set can't be determined (gh hiccup), the guard **fails open** — never wedges shipping (the post-merge #13285 audit is the backstop) |
| AC5 | The guard applies to **all merge strategies** (squash and merge-commit), not just squash — state files belong in no PR regardless of strategy |
| AC6 | Regression coverage: violation-refuses, non-squash-refuses-too, no-violation-proceeds, undeterminable-fails-open, plus the underlying predicate's own truth table (state+vault flagged, `.claude/` flagged, plan-body exempt, launcher exempt, code-only clean, undeterminable→None) |
| AC7 | No regression to the full pre-existing `pr_merge` test surface (behind-count guard, draft self-heal, closing-keyword neutralizer, forge-adapter routing, etc.) |
| AC8 | Full static gate green |

## Verification (branch squidsquad/task/13554, built on latest origin/main — no staleness)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1, AC2 | `test_state_violation_refuses_before_merge` — refuses, `mock_run.call_count == 1` (no merge attempt) | **PASS** |
| TC2 | AC5 | `test_state_violation_refuses_non_squash_too` — `strategy="merge"` also refused | **PASS** |
| TC3 | AC2 (negative) | `test_no_state_violation_proceeds` — code-only PR merges normally | **PASS** |
| TC4 | AC4 | `test_undeterminable_scope_fails_open` — `None` file set → merge proceeds | **PASS** |
| TC5 | AC1, AC3 | `TestPrStateScopeViolations13554` (6 cases): state+vault flagged, `.claude/` flagged, plan-body exempt, launcher exempt, code-only clean, undeterminable→`None` | **PASS** |
| TC6 | **the incident itself** | **Independent live replay** (not in the PR's own mocked suite): ran the real `_pr_state_scope_violations(13546)` against the ACTUAL historical incident PR (already merged, `gh` still serves its metadata) — returned all **14** of the exact files the incident report named as reverted, zero omissions | **PASS — direct, unmocked confirmation the fix addresses the real root cause** |
| TC7 | no false positives | **Independent** check: ran the same live function against all 8 OTHER PRs I merged this session (#13530/#13538/#13544/#13547/#13548/#13549/#13550/#13553) — all `CLEAN`, zero would have been wrongly blocked | **PASS** |
| TC8 | AC6 | 10/10 new tests | **PASS** |
| TC9 | AC7 | Full `TestPrMerge` (18 cases) + `TestPrMergeArgGuard` (7) + `TestPrMergeDraftSelfHeal` (4) + `test_feat_1074_auto_merge.py` (5) = 44/44, zero regression | **PASS** |
| TC10 | AC8 | Full static gate: 5475/0 | **PASS** |

## Incident-recovery fact-check (independent, not trusted from thread)

PM's thread had one false alarm (Windows/MSYS path-mangling on a verify
command) before confirming recovery. I independently re-verified from facts,
correctly handling the same MSYS pitfall (`MSYS_NO_PATHCONV=1`): on current
`origin/main`, `.squidsquad/dm/working-state.md` is 817 lines, `.ship-counter`
is present, and all 10 named vault galaxy notes exist. Recovery (DM's #13556)
is confirmed intact independently of the thread's claims.

## Sibling audit (already done by PM, spot-confirmed)

PM audited PR #13553 (#13353, merged by me earlier this session) and found it
carries only `harness.py` + `test_harness.py` — no state/vault leakage. My own
TC7 above independently re-confirms this by running the live guard function
against it directly: `CLEAN`.

## Notes

- `type:issue`, severity:**high** — auto-approved (bugs skip the approval
  gate), zero-gap standard applied without exception despite the severity.
- No comprehension spec (code-only merge-gate change, not an LLM-consumed
  instruction).
- This closes the loop on an incident that touched my own earlier merge
  action this session; I treated the independent live-replay against the
  actual incident PR (TC6) as mandatory given the stakes, not optional.
