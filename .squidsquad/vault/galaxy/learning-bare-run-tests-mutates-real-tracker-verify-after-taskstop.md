---
type: learning
tags: [verifier, testing, integration-tests, taskstop, github-issues, safety]
created: 2026-07-18
updated: 2026-07-18
owner: verifier
status: active
confidence: high
source: observation
links: [learning-raw-pytest-shows-known-failures-use-run-tests-static]
---

## Context

Verifying #13672, I accidentally ran the bare `python tests/run_tests.py`
(no `static` argument) trying to reproduce the worker's "full suite 53/53"
claim. CONTRIBUTING.md documents this variant also runs **integration
tests that interact with real GitHub Issues** — I caught this mid-run and
called `TaskStop` on the background task. `TaskStop` killed the process,
but a **second, unrelated** background task I started right after (a simple
`tracker.py comment` call) showed leftover integration-test stdout
(`test_create_and_delete_issue ... ok`) when I polled it — the killed
process's buffered output bled into the next task's poll. That was the
signal something was still live: checking `gh issue list` found **two real
stray test-artifact issues** (`[TEST] cleanup test`, `[TEST] E2E bug status
flow test`) that the interrupted integration suite had created but never
torn down, since `TaskStop`'s hard-kill bypassed the suite's normal
`try/finally` cleanup path.

## Content

**`python tests/run_tests.py` with no arguments mutates the real GitHub
tracker — always use `static` (or `harness`/`status_flow` if you
specifically need those integration suites) unless you deliberately want
live integration coverage and are prepared to verify cleanup after.**
`tests/run_tests.py`'s own docstring documents this, and CONTRIBUTING.md
repeats the warning — but it's easy to type the bare command by habit when
chasing a worker's "run all tests" claim.

**If you `TaskStop` a test-suite background task, do not assume the kill
was clean.** The suite's own teardown (`cleanup_all()`/`verify_clean()`,
which `run_tests.py` normally runs "automatically after integration tests,
even on failure") only fires on a **graceful** Python-level exit — a hard
process kill (`TaskStop`, SIGKILL) skips it entirely, stranding whatever
the suite had already created (test issues, branches, files) in the real
target system. After any `TaskStop` of a test run: (1) check
`gh issue list --state all --limit N` for anything that looks like a test
artifact, (2) if found, run `python tests/run_tests.py --cleanup` (the
suite's own exposed cleanup entry point) rather than hand-deleting — it
knows the full artifact taxonomy (issues/branches/files) the ad-hoc eye
doesn't.

**Confusing leftover output across background tasks is itself a signal,
not noise.** Seeing output that doesn't match the command you just ran
(here: integration-test lines under a `tracker.py comment` task) means a
prior process's stdout is still flushing somewhere — treat it as "go check
what that process actually did," not as a rendering glitch to ignore.

## How to apply

- Default to `python tests/run_tests.py static` for any "does the worker's
  test claim hold up" check. Reach for the bare/`harness`/`status_flow`
  variants only with deliberate intent.
- After `TaskStop`-ing any test-suite process: sanity-check the real
  tracker (`gh issue list`) before continuing, and run
  `python tests/run_tests.py --cleanup` if anything stray turns up.
- Treat mismatched/leftover background-task output as an investigation
  trigger, not something to scroll past.
