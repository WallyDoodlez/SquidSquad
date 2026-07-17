# QA-RESULTS #13357 — run_tests.py argument validation

**Verifier**: qa (verifier-lead)
**Verdict**: **PASS → pending-ship** (zero gaps)
**PR**: #13550 (squidsquad/task/13357)
**Branch verified on**: squidsquad/task/13357, combined with current origin/main

## AC walk

| AC | Contract | Evidence | Result |
|----|----------|----------|--------|
| AC1 | `--help` exits 0, no suite launched | live subprocess: usage printed, exit 0, no collection | **PASS** |
| AC2 | typo'd target rejected | live subprocess: `staitc` -> "invalid choice", exit 2 | **PASS** |
| AC3 | unknown flag rejected | live subprocess: `--bogus` -> "unrecognized arguments", exit 2 | **PASS** |
| AC4 | all prior invocations behave identically | diff review: downstream `main()` dispatch logic byte-identical pre/post | **PASS** |
| AC5 | regression coverage | 10/10 PR tests pass | **PASS** |
| AC6 | static gate, self-referential | `run_tests.py static` on combined state — 5451/0 | **PASS** |

## Test runs

- PR's own tests: `tests/test_13357_run_tests_argparse.py` — 10/10 passed (parser-level)
- My own independent **live subprocess** probes (not in the PR's own suite, which only tests the parser in-process): actually invoked `python tests/run_tests.py --help`, `... staitc`, `... --bogus` and confirmed exit codes + messages match the AC contract exactly
- Self-referential gate run: `python tests/run_tests.py static` on combined state — 5451 gated, 0 failures, 0 errors (the exact command I've used throughout this session, confirming zero drift in my own gate)

## Branch staleness

Forked before #13345 (merged this session). Verified via local
`git merge origin/main --no-edit` (no push) — clean, no conflicts.

## Notes

- `type:issue` severity:low — auto-approved, no human gate.
- No comprehension spec (code-only CLI change, not agent-consumed instructions).
- Given this PR modifies the fleet's shared test gate, I deliberately went
  beyond the PR's own parser-unit tests and ran the real CLI subprocess for
  the three critical behaviors, plus re-ran my own `static` gate command
  end-to-end to rule out any daemon-vs-live drift before trusting it further
  this session.
