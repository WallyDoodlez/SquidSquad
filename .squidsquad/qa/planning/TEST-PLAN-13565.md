# TEST-PLAN-13565

Derived independently from `CONTEXT-13565.md` (authoritative scope) + issue body ACs. Not read from the PR diff before writing this plan.

## ACs (from issue body, cross-checked against CONTEXT-13565.md)

- **AC1**: Composed CLAUDE.md size reduced >= 15% per role (measured, before/after in PR body).
- **AC2**: task-intake and verification hot-path cores <= ~8KB each; cold sections reachable and comprehension-tested.
- **AC3**: Re-read-discipline rule shipped with CQ scenarios covering: second cycle same session (skip), post-compaction (re-read), post-restart (re-read).
- **AC4**: All existing comprehension/CQ suites pass.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | Compare composed CLAUDE.md byte sizes, pre-#13565 commit vs branch tip, all 4 roles (`compose.py deploy-all` on a clean checkout of each). |
| TC2 | AC2 (verification) | `wc -c references/sub-skills/roles/verifier/verification.md` vs the ≤~8KB target. |
| TC3 | AC2 (task-intake) | `wc -c references/sub-skills/roles/pm/task-intake.md` vs the ≤~8KB target. |
| TC4 | AC2 (cold-path reachability) | Read the hot-path files for a `→ run sub-skill:` pointer into the cold file; confirm cold content is non-trivial and topically matches what was extracted. |
| TC5 | AC3 (rule wording) | Read the new re-read-discipline paragraph in `references/roles/instructions.md`; confirm it ties to "visible in current context," not "remembered" (Side Effect Mitigation requirement). |
| TC6 | AC3 (CQ coverage) | Search `tests/comprehension/*.json` for a spec covering the three required re-read scenarios. |
| TC7 | AC4 | `python references/scripts/comprehension_staleness.py check` — every spec referencing a file this PR touched must be refreshed (baseline == current hash) or explicitly `superseded_by`. |
| TC8 | sanity | `python -m pytest tests/test_13565_composed_prompt_diet.py -v` (worker's own regression tests). |

## Coverage matrix
- AC1 → TC1
- AC2 → TC2, TC3, TC4
- AC3 → TC5, TC6
- AC4 → TC7
