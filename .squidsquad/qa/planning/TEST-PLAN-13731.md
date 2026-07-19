# TEST-PLAN-13731

Derived independently from the issue body (`type:issue` — Found-by/Observation/Root-cause/This-blocks/Suggested-fix bug report). Not read from the PR diff before writing this plan.

## ACs (from issue body)

- **AC1**: `python tests/run_tests.py static` (specifically `test_no_silently_stale_comprehension_specs`) passes cleanly — the 4 reported stale pairs are resolved.
- **AC2** (load-bearing, per the issue's own suggested-fix caveat): the fix must not be a blind hash refresh. For each of the 2 affected specs (`9184_spec.json`, `12818_spec.json`), every CQ question's expected answer must still be directly evidenced by the reworded (post-#13565) text — a mechanical `refresh` alone does not confirm this; it only silences the staleness detector. If any question's answer is no longer evidenced, that question needs a rewrite, not a refresh.
- **AC3**: The root-cause diagnosis (drift traces to #13565's composed-prompt re-diet condensing shared event-mode-contract paragraphs, content preserved not removed) is independently confirmed, not just trusted from skill's comment.
- **AC4**: Fix is scoped correctly — only the 2 named specs' baseline entries change; no unrelated baseline drift introduced or masked.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | `python references/scripts/comprehension_staleness.py check` on the branch — confirm exit 0, no stale pairs remain. Then full `python tests/run_tests.py static` — confirm the previously-failing test now passes. |
| TC2 | AC2 (the real gate) | Read `tests/comprehension/9184_spec.json` and `tests/comprehension/12818_spec.json` in full. For each CQ question, locate the corresponding passage in the current (post-#13565) `.squidsquad/pm/CLAUDE.md`, `.squidsquad/qa/CLAUDE.md`, `.squidsquad/skill/CLAUDE.md` and confirm the expected answer is still directly stated/derivable — not just "probably still true." |
| TC3 | AC3 | `git diff <old-baseline-blob> HEAD -- .squidsquad/pm/CLAUDE.md` (and skill/qa equivalents) — independently confirm the diff is a condense/reword, not a content deletion that would invalidate a CQ answer. |
| TC4 | AC4 | `git diff origin/main...origin/squidsquad/task/13731 -- tests/comprehension/.staleness-baseline.json` — confirm only the 2 named specs' entries changed. |
| TC5 | (regression) | Full test suite / static gate — confirm clean beyond this specific fix (no other pre-existing gaps newly exposed). |

## Note

This issue is itself the pre-existing gap I flagged as "unrelated, out of scope" in QA-RESULTS-13709/13710/13714/13722/13723's Sanity Checks sections throughout this session. High severity is warranted — it silently blocked every role's static gate. TC2 is the real verification work here, not TC1 (which just confirms the symptom is gone) — a refresh that papers over a genuinely-broken CQ answer would be worse than the stale-detector firing, since it would silence the safety net permanently.
