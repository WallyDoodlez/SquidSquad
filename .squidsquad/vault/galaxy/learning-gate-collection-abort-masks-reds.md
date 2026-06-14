---
type: learning
tags: [skill, testing, run_tests, pytest, ci-gate, drift, auto-discovery]
created: 2026-06-12
updated: 2026-06-14
owner: skill
status: active
confidence: high
source: observation
links: [decision-deterministic-testing, learning-create-test-environments]
---

## Second masking mode — in-suite hard-exit (#12408, 2026-06-14)

A SECOND way `run_tests.py` static reports green over reds, distinct from the
collection-abort below. Found by QA verifying #12380: the gated run shows an `F`
at ~52%, then truncates at ~56% with **no final summary and no junit written**,
yet `subprocess.returncode == 0`. A test executing mid-suite hard-exits the
process (`os._exit(0)` / `sys.exit(0)` / `pytest.exit(returncode=0)`), bypassing
pytest's session-finish and exit-code aggregation — every failure before AND
after it is masked, and the run never completes. Filed #12408.

Reinforces Lesson 4 below and adds: **don't trust returncode alone — also assert
the session reached completion.** A run that exits 0 without writing its junit /
summary did not finish; treat an incomplete session as failure. Detect via
`--junit-xml` presence + testcase count, or a sentinel "expected N tests" check.
Repro reliably *in-process* (`subprocess.run(..., capture_output=True)`) — naive
shell `>` redirect races the inherited-fd pytest stream against Python's buffered
stdout on Windows and truncates the captured log misleadingly.

## Context

`tests/run_tests.py` gated the static suite via a hand-maintained `STATIC_TEST_MODULES`
allowlist passed to `pytest <file1> <file2> ...`. The v0.44.0 cutover (#11331) deleted
`test_l2_l3_op_anchoring_11227.py` but left its name in the list. pytest aborts the
WHOLE run on a missing file argument (collection error → exit 4, **0 tests collected**).
So `python tests/run_tests.py static` had been "passing" by running *nothing* since the
cutover, silently masking **23 red test files** (most stale post-v2/rename, but ~4
possibly-real regressions). Discovered while implementing #11394; tracked in #11503.

## Lesson

1. **A test gate that can pass with zero tests collected is a dangerous failure mode.**
   "OK" with no work done reads identical to "OK, all green." Always assert the gate
   actually ran something — `if not modules: return False` (empty-gate fail-fast).
2. **Prefer auto-discovery over a hand-maintained allowlist for drift-prone gates.**
   Globbing `test_*.py` minus *documented* exclusions closes both drift modes at once:
   forgotten-adds (new file silently ungated) AND deleted-listed (dangling entry breaks
   collection). The glob only ever yields files that exist.
3. **Quarantine, don't hide.** Replace silent omission with an explicit exclusion dict
   (reason + issue ref per entry) printed as a NOTICE every run, plus a regression test
   asserting every test file is accounted for and every exclusion names an existing file.
4. **Verify the gate's exit semantics, not just its last line.** The original "OK" I saw
   post-cutover was the *integration* suite; static's non-zero exit was masked by a
   `| tail` pipe in a spot-check. Check the return code, and beware pipes that swallow it.

## How to apply

When touching any aggregate test runner: confirm it errors loudly on missing/empty
inputs, auto-discovers rather than enumerates, and has a regression guarding the
discovery invariants. See `tests/test_11394_static_discovery.py` for the invariant set.
