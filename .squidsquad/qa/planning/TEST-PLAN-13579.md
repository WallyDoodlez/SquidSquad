# TEST-PLAN #13579 — working-state.md sub-skill silent on #13562 size discipline

**Derived from the issue body's own contract (PM-authored, incl. the CQ AC) — my own independent reading.**

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | `references/sub-skills/common/working-state.md` states the ~8KB size bound |
| AC2 | States oversized content is tail-truncated in cycle-input behind a marker (not silently dropped, not head-truncated) |
| AC3 | States an oversized write draws a warning |
| AC4 | States history belongs in git/iteration logs, not an in-file journal |
| AC5 | Doesn't crowd out or contradict the pre-existing clear-on-complete guidance |
| AC6 | **CQ gate (#9184, hard, PM-stated in issue body)**: a fresh agent given ONLY the modified file states both the size bound AND the clear-on-complete rule unprompted |
| AC7 | No regressions on combined state |

## Verification (branch squidsquad/task/13579, freshly fetched, merged with current origin/main — 3 commits ahead)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1-AC5 | Read the full updated sub-skill file | New bullet states ~8KB bound, tail-truncation + `[TRUNCATED (#13562)]` marker, oversized-write warning, history-belongs-in-git/iteration-logs, rewrite-not-archive — all present, additive (existing clear-on-complete bullet untouched) |
| TC2 | AC6 | **Comprehension gate**: fresh sonnet general-purpose agent, given ONLY the modified file's content inline, explicitly told to use no other file/tool/prior knowledge. 4 questions (size bound + consequence, clear-on-complete, journal-growth remediation + history location, tail-vs-head truncation direction) | **4/4 correct, zero must_not violations.** Spec: `tests/comprehension/13579_spec.json` |
| TC3 | AC7 | `pytest tests/ -k "working_state or sub_skill"` on combined state | 60 passed, 1 skipped, 0 failed |
| TC4 | AC7 | Full static gate on combined state | 1 failure, 0 errors, 5511 gated — confirmed identical to the already-tracked, disclosed #13582 residual (`inject-permissions.ps1` ascii test), not introduced by this PR |

## Verdict: PASS

The sub-skill now documents the size discipline agents actually operate
under, closing the authoring-vs-runtime drift #13562 introduced. Comprehension
gate confirms a fresh reader derives the correct, complete behavior from the
instruction alone — the exact bar PM set in the issue body. No regressions;
the one static-gate failure present is the already-filed, unrelated #13582.
