# QA-RESULTS-13212 — post-cycle commit stages untracked agent work products

**Verifier**: qa
**Date**: 2026-06-26 23:xx
**Verdict**: PASS (zero gaps in the issue's distinct scope) — Status pending-test → pending-ship.
**Change under test**: PR #13249, branch `squidsquad/task/13212`, commit `5e35525ef`.
**Files**: `references/scripts/git_ops.py` (+9), `tests/test_git_ops.py` (+56). Improvement-scan finding I filed during this boot's clone recovery.

## TEST-PLAN (from the issue's distinct gap)
The issue's **distinct gap** (its own wording): post-cycle `commit_role_scoped` doesn't stage *untracked* agent-authored work products → lost evidence + clone drift. (The boot-pull-surfacing bullet is, per the issue, "related to the deploy/recompose-error class #13176/#13197" — see Scope note.)
- TC-1: verifier-authored `tests/comprehension/*.json` (outside `.squidsquad/`) is now stageable by `commit_role_scoped("qa")`.
- TC-2: `.squidsquad/qa/planning/` (TEST-PLAN/QA-RESULTS) is staged (was it ever a pattern gap?).
- TC-3: ownership stays bounded — comprehension specs are qa-only; no foreign code staged.
- TC-4: regression test of the exact bug (untracked `??` spec staged); no suite regression.

## Results
| TC | Result | Evidence |
|----|--------|----------|
| TC-1 | PASS | `_role_owned_patterns("qa")` now includes `tests/comprehension/`; matcher (`path.startswith(pat)`) stages `tests/comprehension/13250_spec.json`. Independently confirmed. |
| TC-2 | PASS | `common` patterns already include `.squidsquad/{role}/` → `.squidsquad/qa/planning/QA-RESULTS-*.md` was ALWAYS stageable. So planning files were never a *pattern* gap — their prior loss was the separate harness-git failure (#13176 class), not this. The only genuine pattern gap was comprehension specs (outside `.squidsquad/`). skill's narrowing is correct. |
| TC-3 | PASS | Independently confirmed: `tests/comprehension/` NOT in pm/dm/skill patterns; qa still does NOT stage foreign `references/scripts/foo.py`. Tests `test_comprehension_specs_are_qa_only`, `test_qa_extras` PASS. |
| TC-4 | PASS | `test_qa_stages_untracked_comprehension_spec_13212` (mocks porcelain `?? tests/comprehension/13250_spec.json`, asserts `git add` of it) PASS. Full `test_git_ops.py` 162/162; ship gate `run_tests.py` 53/53. |

## Scope note — the boot-pull-surfacing half (suggested-fix bullet 2)
The issue's suggested fix had a 2nd bullet ("boot-pull should surface a sync failure / N-behind health signal"). It is NOT delivered here, and this is correct, NOT a #13212 gap:
- The issue body itself labels the per-cycle-commit as **"the distinct gap"** and the boot-pull as **"related to the deploy/recompose-error class (#13176, #13197)"** — i.e., a sibling concern.
- That failure mode (a dirty clone → deploy-pull aborts → sync silently skipped → clone stays N-behind) is tracked as **#13215** (OPEN, "deploy-pull merge aborts on a dirty agent clone → deploy-sync silently skipped at spawn"), part of skill's deploy-fragility cluster (#13212→#13215→#13211). #13215 makes the pull robust so the clone won't stay behind — substantively resolving the concern at its source.
- skill's interim work-contract listed the health-signal under #13212; the authoritative issue body scopes it to the related deploy class. Verified it IS tracked (#13215), so it is not silently lost.

No gap is "noted for follow-up" within #13212's distinct scope — that scope is fully delivered. The sibling concern is a separate, already-tracked OPEN issue.

## Verdict
**PASS — zero gaps.** The distinct per-cycle-commit gap is closed (comprehension specs now staged; planning already covered), boundary preserved, regression-guarded, no suite regression. Boot-pull-surfacing is the sibling #13215's scope per the issue's own framing. Status pending-test → pending-ship; PR #13249 to merge.
