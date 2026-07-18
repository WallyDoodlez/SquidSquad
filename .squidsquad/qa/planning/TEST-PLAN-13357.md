# TEST-PLAN #13357 — run_tests.py argument validation

**Derived from the issue body — own filed finding, observed live 2026-07-06.**

Bug: `run_tests.py --help` silently launched the full ~5213-test static suite
instead of printing usage; unknown/typo'd args were silently filtered out by
the old `[a for a in sys.argv[1:] if not a.startswith("-")]` logic rather than
rejected — a typo like `staitc` would run whatever the (empty) filtered target
list implied instead of erroring.

## Acceptance Criteria (independent reading — scope = CLI argument validation only)

| AC | Contract |
|----|----------|
| AC1 | `--help` prints usage and exits 0 WITHOUT launching any test suite |
| AC2 | An unrecognized target/typo (e.g. `staitc`) is rejected with a non-zero exit, not silently run |
| AC3 | An unrecognized flag (e.g. `--bogus`) is rejected with a non-zero exit |
| AC4 | Every prior invocation shape still behaves identically: no-args -> static+integration; `static` -> static-only; a valid integration target name -> that suite; `--cleanup` -> cleanup-only |
| AC5 | Regression test suite covers all of the above at the parser level |
| AC6 | Full static gate green — **self-referentially**, using the very `run_tests.py static` invocation this PR modifies |

## Verification (branch squidsquad/task/13357, combined with current main — see below)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | **Live subprocess** (not just the PR's parser-level test): `python tests/run_tests.py --help` — printed usage, exit 0, no test collection ran | **PASS** |
| TC2 | AC2 | **Live subprocess**: `python tests/run_tests.py staitc` — `error: argument TARGET: invalid choice`, exit 2 | **PASS** |
| TC3 | AC3 | **Live subprocess**: `python tests/run_tests.py --bogus` — `error: unrecognized arguments`, exit 2 | **PASS** |
| TC4 | AC4 | Diff review: downstream `main()` logic (`static_only`, `integration_only`, dispatch) is byte-identical to the pre-PR version — only the args source changed from raw `sys.argv` filtering to `argparse` | **PASS — confirmed no behavioral drift** |
| TC5 | AC5 | 10/10 tests in `tests/test_13357_run_tests_argparse.py` | **PASS** |
| TC6 | AC6 | **Self-referential live run**: `python tests/run_tests.py static` on combined state — 5451 gated, 0 failures, 0 errors (same command I've used all session) | **PASS** |

## Branch-staleness handling

Forked before #13345 (merged this session). Verified combined post-merge
state via local `git merge origin/main --no-edit` (no push) — clean, no
conflicts.

## Notes

- `type:issue`, severity:low (improvement) — auto-approved, no human gate.
- No comprehension spec (code-only CLI change, not an LLM-consumed instruction).
- Extra care taken here beyond the usual pattern: this modifies the fleet's
  own test gate, so I ran the actual CLI subprocess (not just the PR's
  parser-unit tests) for the three critical behaviors (`--help`, typo, valid
  `static` invocation) to rule out any daemon-vs-live drift.
