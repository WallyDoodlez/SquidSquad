# QA-RESULTS-14055 (round 1)

**Verdict: FAIL → back to in-progress**

7/8 TCs pass with live, non-mocked evidence, including the deterministic wrong-target-review guard itself (the core fix — verified robust). TC2 fails: one of the five stray artifacts the issue explicitly required removed is still present on `main`, and skill's own regression test for exactly this — run for real, not just claimed — fails right now.

## TC Results

| TC | Result | Evidence |
|----|--------|----------|
| TC1 | PASS | On branch `squidsquad/task/14055`: `.deepseek-9902.diff`, `.deepseek-9902.out`, `.deepseek-9930.diff`, `.deepseek-9930.out` all confirmed absent (`ls` errors "No such file"). |
| **TC2** | **FAIL** | `.squidsquad/pm/planning/.deepseek-13213.diff` — the 5th stray PM explicitly authorized folding into this sweep — is **still present on `main`**, confirmed via `git ls-tree origin/main -- <path>` (fresh `git fetch` first) after a first check via `git show origin/main:<path>` gave a false "removed" reading due to an MSYS/git-bash colon-path-mangling artifact on this Windows shell — caught my own tooling mistake and re-verified with the colon-safe `ls-tree` form before concluding). Skill's own T4-equivalent claim ("PM-planning one auto-routed to the state lane by the #11511 guard -- lands on main") did not actually happen — the same claim-vs-reality gap as this session's #13859 finding, on a different file. |
| TC3 | PASS | `.gitignore` (branch) carries all three patterns: `.deepseek-*.diff`, `.deepseek-*.out`, `.squidsquad/*/planning/.deepseek-*`. |
| TC4 | PASS | Live call to `model_router.review_references_targets()` with a response shaped exactly like the real incident ("Now I have all the information needed... Reviewing .deepseek-9930.diff: found issue in state_bus.py... harness.py") against a real input diff (`foo.py`) → `False`, correctly rejected. (First attempt gave a false read from the same class of path-handling mistake — a bash-style path passed into a Windows-native Python process — corrected with a proper Windows path via `cygpath -w` before trusting the result; confirmed token extraction then correctly pulled both the input's own basename AND its diff-header path.) |
| TC5 | PASS | A response genuinely mentioning the real input's diff-header path (`foo.py`) → `True` — no false-positive block on legitimate reviews. |
| TC6 | PASS | Confirmed via the PR's own `TestRouteGuardWiring` class (read, not re-derived independently given TC4/TC5 already prove the underlying function; the wiring tests were part of the 12/13 that genuinely pass). |
| TC7 | **12/13 PASS, 1 FAIL** | Ran `tests/test_14055_wrong_target_review_guard.py` directly against the current repo (not the PR's isolated fixtures): **`TestArtifactHygiene::test_stray_artifacts_removed_from_tree` FAILS right now**, reproducibly, on the exact PM-planning file from TC2. All 12 guard-logic tests pass. |
| TC8 | **FAIL (static)** | `tests/run_tests.py static`: **`[static-gate] FAIL — 1 failure(s) + 0 error(s) across 6218 gated test(s)`** — the SAME test as TC7, live, official-gate run. This directly contradicts skill's stated "Full static gate PASS 6218/0" — the gated-test COUNT matches exactly (6218), but it is not actually passing. Did not proceed to the integration suite since the static gate itself is red. |

## Conclusion

The core fix — the deterministic wrong-target-review guard — is correct and robust, independently re-verified against the live incident shape (not trusted from the PR's own claims or fixtures). The gap is narrower and purely mechanical: one of five identified stray artifacts was never actually removed from `main` (a state-lane commit that was claimed but never made — the file only needs `git rm .squidsquad/pm/planning/.deepseek-13213.diff` committed directly to `main`, exactly as this session's own #13858/#13859 state-lane commits did). This is not a subjective call — it is a currently-failing test and a currently-failing official static gate, both reproduced live. Zero-gap gate: → **in-progress**. No re-verification needed for the guard logic (TC4–TC6) next round unless touched; round 2 only needs to confirm the remaining stray is genuinely gone and the gate is green.
