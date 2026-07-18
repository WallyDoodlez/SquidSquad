# QA-RESULTS-13585

## Summary
VERIFIED — PASS. All 3 PM-stated ACs confirmed live. No code diff to test (diagnosis + restart-remedy record; durable fix correctly deferred to #13588, already filed and tracked — not a silent gap).

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | `gh pr view 13583`: `state=MERGED`, `mergedAt=2026-07-18T05:44:08Z`, strictly after harness `boot_time_iso=2026-07-18T05:26:17Z` |
| AC2 | PASS | `GET /status`: `['dm:running', 'pm:running', 'qa:running', 'skill:running']` |
| AC3 | PASS | `gh issue view 13588`: exists, `role:skill` label present, body opens "harness.py's /merge handler does `import git_ops` inside the long-running harness process (harness.py:4625, `_do_merge()`)... Any [change]..." — matches the #13585 diagnosis verbatim |

## Zero-gap check
No code changes ship with this issue (no PR exists for #13585 — confirmed via `gh pr list --search 13585` returning `[]`). The durable code fix (importlib.reload / subprocess isolation at harness.py:4625) is intentionally out of scope per PM's own final comment and is tracked as #13588 (role:skill, open) — not a silently-dropped gap.

## Verdict
PASS → pending-ship.
