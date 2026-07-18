# TEST-PLAN #13517 — ASCII-safe gh --title for create-issue/create-task

**Derived from the issue body "Suggested fix" — not the diff.**

Bug class: #13370 fixed non-ASCII crash for BODIES (routed via `gh --body-file -`
stdin), but TITLES are still passed as a `--title` argv argument (gh has no
`--title-file`), so a non-ASCII title (em-dash, arrow, smart quote) still
crashes `gh` on a cp1252 Windows console — the same class, unaddressed on the
title field. This is my own finding (filed while verifying #13370).

## Acceptance Criteria (independent reading — scope = tracker.py create_issue/create_task gh path)

| AC | Contract |
|----|----------|
| AC1 | Titles are transliterated (em/en-dash, smart quotes, arrows, ellipsis, nbsp, bullet) to readable ASCII before `--title`, in both `create_issue` and `create_task` |
| AC2 | An `encode("ascii","replace")` backstop guarantees the result is pure ASCII even for un-transliterated codepoints (residual -> `?`) — gh can never crash on the argv |
| AC3 | The forge-adapter (non-GitHub) API path is unaffected — Unicode preserved there (no argv, no crash risk) |
| AC4 | A stderr NOTE is emitted when the title was altered (transparency, not silent mangling) |
| AC5 | Regression test suite covers the transliteration + the ascii-backstop + routing through create_issue/create_task; full static gate green |

## Verification (branch squidsquad/task/13517, combined with current main — see below)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | PR's own `TestAsciiizeTitle` (em-dash, en-dash, arrows, smart quotes, ellipsis/bullet/nbsp) + my own independent probes (`'Fix wizard—stale docstring'`, `'Use '..'' quotes ""..""'`, `'Step 1->Step 2... done'`, `'Bullet*item'`) | **PASS** |
| TC2 | AC2 | PR's `test_residual_non_ascii_replaced_not_crashed`, `test_output_is_always_ascii` + my own probe (emoji -> `?`) — every output round-tripped through `.encode('ascii')` with no raise | **PASS** |
| TC3 | AC3 | **Independent** probe (not in PR's own suite): monkeypatched `_get_forge_adapter`, confirmed `create_issue` passes the RAW Unicode title (em-dash intact) to the adapter — gh-only fix does not touch the non-GitHub path | **PASS** |
| TC4 | AC4 | Source read: `if gh_title != full_title: print("NOTE: ...", file=sys.stderr)` present in both `create_issue` and `create_task` | **PASS** |
| TC5 | AC5 | 12/12 PR tests pass; full static gate on combined state 5437/0 | **PASS** |

## Branch-staleness handling

`squidsquad/task/13517` forked at `c161bbd1c` (after #13323, before #13434 and
#13371 — both merged by me earlier this session). Verified combined
post-merge state via local `git merge origin/main --no-edit` (no push) — clean
merge, no conflicts (this PR's `tracker.py` region does not overlap #13371's
`git_ops.py` region). Full static gate on combined state: 5437/0.

## Notes

- `type:issue`, severity:low — auto-approved, no human gate.
- No comprehension spec (code-only change, not an LLM-consumed instruction).
