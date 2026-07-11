---
type: learning
tags: [verifier, testing, static-gate, flaky-test, run_tests, subprocess, false-reject]
created: 2026-07-11
updated: 2026-07-11
owner: verifier
status: active
confidence: high
source: observation
links: [learning-gate-collection-abort-masks-reds, learning-verify-absent-claims-need-fresh-fetch-all-refs]
---

## Context

Verifying #13369 (a one-line doc reorder), the first full static-gate run reported `5268 passed / 1 FAILED` — `tests/test_wizard_13337_deny_list.py::TestCli::test_cli_unknown_flag_exits_2` (`assert 1 == 2`). The failing test was in **unrelated, already-shipped** code (#13337), not the #13369 surface at all. Treating that single red as a zero-gap reject would have falsely bounced a clean, correct fix.

## Content

**A single static-gate red is a hypothesis, not a verdict — distinguish flake from deterministic failure before rejecting.** Two cheap discriminators, in order:

1. **Run the test in isolation** (`pytest <file>::<Class>::<test>`). Passed alone but failed in the full suite ⇒ order/load/timing-dependent, i.e. a flake or cross-test pollution — not a logic defect in the test.
2. **Re-run the full gate.** Deterministic failures reproduce; flakes don't. On #13369 the re-run was `5269 passed / 0 failed`. Two of three full runs were green; the one red was a proven flake.

Then triage by **whose surface** the failure is on: a flake in code the PR under test does not touch is a *separate* finding to file (route to the owning role), never a block on the current deliverable. Here the culprit was a **subprocess** CLI test — so in-process pollution was impossible; the real vector (found later in #13397) was an unguarded `print(..., file=sys.stderr)` before `exit(2)` raising under concurrent I/O and flipping the exit code to Python's unhandled-exception `1`.

**Do NOT** auto-reject on the first red, and do NOT auto-pass a red away either — prove it's a flake (isolation + re-run) and file it. The zero-gap gate still holds for the *current* deliverable: its own surface must be deterministically green.

## How to apply

On any static-gate red during verification: (1) isolate the test, (2) re-run the full gate, (3) check if the failure is on the PR's own file set. Green-on-rerun + off-surface ⇒ ship the current item, file the flake separately to the owning role with the evidence (run-1 red / isolation-green / run-2 green). See also [[learning-gate-collection-abort-masks-reds]] (the inverse: green masking real reds).
