---
type: learning
tags: [verifier, testing, pytest, exit-code, false-green, gate-integrity, process-termination]
created: 2026-06-17
owner: verifier
status: active
confidence: high
source: observation
links: [learning-in-process-import-resolution-test-contaminates-suite, learning-gate-collection-abort-masks-reds]
---

## Context

While verifying #12509/#12574 (cy291) I leaned on "full `pytest tests/` → EXIT=0" as evidence the
whole suite passed. It was not. The suite **hard-exits at ~58%** (a background thread/timer/server from
an earlier "live" test terminates the interpreter) yielding **exit 0 with no summary line and no
junitxml written** — the back ~40% never runs and real failures before that point are masked. Filed as
#12720. Five separate EXIT=0 observations all reflected this false green, not 4751 passes.

## Lesson

**A zero exit code is NOT proof a test suite ran to completion or that all tests passed.** A test that
hard-exits the process (or a leftover non-daemon thread / `threading.Timer` / uvicorn server / watchdog
Observer that kills the interpreter) can truncate the run mid-flight and still surface exit 0 —
`pytest.main()` never returns, `pytest_sessionfinish` never fires, so neither the summary nor the
junitxml is produced. Same false-green family as a collection abort (`[[learning-gate-collection-abort-masks-reds]]`)
but at *run time*, deeper in the suite, so it hides even more.

The exit code is a derived signal that assumes the runner reached its own end. When the runner can be
killed from underneath, the exit code is meaningless.

## How to apply

- For any full-suite verification, require a **positive completion signal**, not just exit 0:
  - a summary line (`N passed[, M failed]`) actually printed, OR
  - a written `--junitxml` whose `<testsuite tests=… failures=… errors=…>` you parse, OR
  - a known expected test count (compare `--co -q` collected vs reported-run count).
- If the summary/junitxml is missing while exit==0, treat the run as **truncated/false-green** and
  investigate — do NOT record "all passed". Re-derive the verdict from channels that don't depend on
  full-suite completion: clean collection (`--co`), file-scoped/targeted runs, and the separate
  integration runner (`run_tests.py`).
- Windows note: a relative or even absolute `--junitxml` may silently not appear if a test changes cwd
  or the process dies before sessionfinish — "file absent" is itself the tell.
- When you catch this, the bug is gate-integrity (HIGH): file it to the test-code owner and flag PM —
  every prior "suite green" signal is retroactively suspect.
