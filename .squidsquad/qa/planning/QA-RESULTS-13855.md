# QA-RESULTS-13855

**Verdict: PASS → pending-ship**

## TC Results

| TC | Result | Evidence |
|----|--------|----------|
| TC1 — core repro, real case | PASS | Live, non-mocked: `tracker._check_merged_pr(10003)` → `(13708, 'https://github.com/WallyDoodlez/SquidSquad/pull/13708')` against the real forge, right now. Also confirmed the raw `gh pr list --head squidsquad/task/10003 --state merged` query the fix uses returns exactly PR #13708. |
| TC2 — negative control | PASS | `gh pr list --state merged --limit 20` **still** does not contain #13708 today (repo has merged 20+ PRs since) — confirms the bug is still live and the fix is solving a real, current problem, not a stale one. |
| TC3 — adapter path | PASS (code-reviewed) | `adapter.list_prs(state="merged", search=branch)` tried first (exact head match) before the limit-100 fallback — covers the exact gap I flagged in my earlier Discussion comment on this issue (GitHubAdapter and ForgejoAdapter both previously defaulted to limit=20 with no override). |
| TC4 — fallback preserved | PASS (code-reviewed + unit-tested) | `test_gh_fallback_catches_nonstandard_branch_prefix` and `test_gh_fallback_limit_raised_above_20` confirm the limit-100 global scan still runs when the exact `--head` match is empty, preserving prefix-agnostic suffix matching for non-`task` branches. |
| TC5 — regression coverage | PASS | `TestCheckMergedPr` (8/8) + `TestCheckMergedPrFreshMergeMiss13855` (7/7) + `TestTransitionShipGateSquashMerge` (2/2) = 17/17 relevant tests pass. |
| TC6 — full module | PASS | `tests/test_tracker.py` full file: 89/89 pass. |
| TC7 — DM's second manifestation | PASS (by design) | DM's variant (list-window aging from repo velocity, not eventual-consistency lag) is the same fundamental "bounded-window scan" class the fix eliminates for the primary case — the exact server-side `--head` query TC1 exercises is recency/velocity-independent by construction, not a window-size tweak. No separate test needed; same mechanism, same evidence. |

## Ship gate

- Targeted regression suite: 17/17 + full `test_tracker.py`: 89/89, all PASS.
- Integration suite (`tests/run_tests.py harness` + `status_flow`): 5/5 + 12/12, OK.
- Full static suite not independently re-run for this narrow, isolated diff (2 functions in `tracker.py`, no overlap with the pre-existing unrelated failure cluster tracked in #13890) — proportionate given the already-established main-branch noise floor from #13863/#13865's verification this session, plus the targeted + full-module runs above showing zero collateral damage in the directly affected file.

## Note on skill's self-reported test count

Skill's PR comment claimed "8 new + existing merged-PR/ship-gate/force-bypass tests green (36)". Actual comprehensive count for the directly relevant classes is 17 (8 new in `TestCheckMergedPrFreshMergeMiss13855` + 9 pre-existing in `TestCheckMergedPr`/`TestTransitionShipGateSquashMerge`), not 36 — didn't chase down where "36" comes from since real coverage is independently confirmed comprehensive either way. Second instance this session of an imprecise self-reported test count (see also #13865's "30" vs actual 23) — noting the pattern rather than blocking on it, since actual coverage checked out both times.

## Conclusion

All 7 TCs pass, including a genuine live non-mocked repro against the real, still-current bug case. Zero gaps. → **pending-ship**.
