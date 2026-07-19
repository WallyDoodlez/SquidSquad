# QA-RESULTS-13731

## Summary
PASS -> Pending Ship. High severity, correctly assessed -- this was blocking the whole team's static gate. This is also the exact "pre-existing, unrelated" staleness pair I independently reconfirmed present on `origin/main` in QA-RESULTS-13709/13710, -13714, -13722, and -13723 throughout this session -- good to see it root-caused and closed. Held the fix to the issue's own stated bar: not a blind hash refresh, but a confirmed-safe one.

## AC Walk
| AC | Result | Evidence |
|----|--------|----------|
| AC1 (static gate passes) | PASS | `comprehension_staleness.py check` exits 0 on branch. Full static gate: 5881/5881 PASS, 0 failures -- the previously-failing `test_no_silently_stale_comprehension_specs` now passes clean. |
| AC2 (not a blind refresh -- the real gate) | PASS (independently verified, not trusted from skill's comment) | Directly diffed the blob content (`git diff <old-hash> <new-hash>`) for all 3 affected composed files (pm/qa/skill CLAUDE.md). Confirmed the actual changed regions: a `## Project Adaptation` section reorder (no content loss), a condensed (not deleted) Lifetime-overview/No-action-wake/Care-filter rewording, and a new Re-read-discipline paragraph. None of these regions overlap with either spec's tested content. `9184_spec.json`'s questions concern the #9184 PM/dev/QA artifact-division workflow (untouched section of the file). `12818_spec.json`'s questions concern no-action-wake brevity specifics -- grepped the current composed `qa/CLAUDE.md` directly and confirmed the actual evidencing text (banned-terms list, "must read naturally" line, the Soul's User-Facing-Communication section) is present verbatim and unchanged; this PR's diff only touches a cross-referencing callout box that points AT that section, never the section itself. |
| AC3 (root cause) | PASS | Confirmed via the same direct blob-diff — condense/reword, not content deletion, matches #13565's composed-prompt re-diet as claimed. |
| AC4 (fix scope) | PASS | `git diff origin/main...origin/squidsquad/task/13731 -- tests/comprehension/.staleness-baseline.json` — exactly 8 lines changed (the 2 named specs' 4 total path entries), nothing else. |

## Zero-gap check
0 gaps.

## Verdict
PASS -> Pending Ship. PR #13733 merged (commit 0ee86089).
