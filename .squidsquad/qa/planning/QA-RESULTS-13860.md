# QA-RESULTS-13860

**Verdict: PASS -> pending-ship** (PR #14126, branch squidsquad/task/13860, merge-clean vs origin/main d0b1bbdd9+)

## TC Results

| TC | Result | Evidence |
|----|--------|----------|
| TC1 | PASS | Live vs throwaway #14129 (closed): `## Vault context` appended with 4 notes (engine tier evidence), 4 impressions written; re-inject left exactly 1 section. |
| TC2 | PASS | lineage-path -> exists:false; init-fix-plan 99001 -> `.squidsquad/skill/planning/99001-fix-plan.md` (Root cause/Intended direction/Impact + both receipt headings); empty skeleton -> check-receipts fail. |
| TC3 | PASS | bullets: cited pass; None relevant/None matched pass; Engine unavailable pass-with-note (both notes quoted); prose `- todo` fail; empty heading fail; missing `## Applicable rules` fail. |
| TC4 | PASS | Real PR: `check-receipts 13860 --diff-base origin/main` pass (13860-fix-plan.md in the PR's 34-file diff, i.e. state-guard exemption works); `--diff-base HEAD` -> fail "not in the PR diff". |
| TC5 | PASS | cite two real slugs -> 2 `used` events (agent, task, slug, counter); unresolved slug -> events 0, listed as unresolved. |
| TC6 | PASS | Real 169-note vault: duplicate title -> update (filename tier, Jaccard .625); unrelated -> create; content-only -> create; archived and superseded copy -> create; dedupThreshold 0.9 -> create, 0.3 -> update; dedup probes: telemetry delta 0. |
| TC7 | PASS | 3 fresh sonnet agents (worker/pm+verifier/vault groups) answered Q1-Q10 correctly from the files alone (Q8: merge-target criteria are script-owned by design; file says decision is the script's). |
| TC8 | PASS | `run_tests.py static` on branch: 6543 passed, 0 failures. |
| TC9 | PASS | PR mergeStateStatus CLEAN, trial merge with origin/main clean; wiring test test_l1_vault_slot_names_engine_and_receipts in gate. |

## Observations (non-blocking, filed separately)
- `inject_context` runs the search (writes impressions) before `gh issue view`; a view failure leaves impressions with nothing shown, contrary to the code's "shown == impressed" comment.
- check-receipts validates format only; a cited `[[slug]]` that does not exist passes (TRD 9.4 requires presence + rule compliance, so within spec).
