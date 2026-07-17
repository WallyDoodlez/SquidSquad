# QA-RESULTS-13370 — tracker.py gh body via UTF-8 stdin (non-ASCII no longer crashes)

**Verdict: PASS — zero gaps.**
**Verifier**: qa (verifier-lead). **PR**: #13493. **Type**: type:issue (bug, auto-approved). **Provenance**: verifier-filed (the em-dash/cp1252 crash class).

## Verification approach

Verified LIVE (real create+comment round-trip on this Windows cp1252 box) + hermetic (mechanism). This is the verifier's own tooling — the live round-trip is the definitive gate.

## AC walk

| AC | Criterion | Evidence | Result |
|----|-----------|----------|--------|
| AC1 | tracker.py comment with non-ASCII body (em-dash/arrow) does NOT crash gh | LIVE: comment rc=0 on artifact #13495 with em-dash+arrow | PASS |
| AC2 | non-ASCII round-trips intact (no U+FFFD mojibake) | LIVE: body+comment em-dash — arrow → quotes “x” all present, mojibake=False | PASS |
| AC3 | create-issue/create-task --body non-ASCII also works (same _run_gh_with_body) | LIVE: create rc=0 with non-ASCII body | PASS |
| mech | body passed via `--body-file -` on UTF-8 stdin, never argv --body/--message | hermetic: cmd ends [--body-file, -]; input==body; encoding utf-8; no non-ASCII in argv | PASS |
| AC4 | regression test present | tests/test_13370_gh_body_via_stdin.py | PASS |

## Test runs

- LIVE E2E (artifact #13495, created+commented+closed): create rc=0, comment rc=0, em-dash/arrow/smart-quote intact in body AND comment, mojibake=False -> RESULT PASS.
- Independent hermetic tests (TEST-13370-tests.py): **4 passed**.
- Worker regression test (tests/test_13370_gh_body_via_stdin.py): (recorded at merge).
- Full static gate: (recorded at merge).

## Residual (noted, acceptable)

Titles stay argv (gh has no --title-file); titles are short/ASCII by convention. Documented rare residual exposure, not a gap for this fix.

## Impact note (verifier)

This retires the standing verifier workaround "tracker.py comments must be ASCII-only" ([[project_tracker_comments_ascii_only]]) once shipped to main — em-dashes/arrows in comment/body no longer crash gh. Titles remain ASCII.

## Decision

All ACs satisfied (live round-trip + hermetic mechanism); regression test present. Zero gaps. -> PASS: verdict comment BEFORE transition + merge PR #13493 + Pending Ship.
