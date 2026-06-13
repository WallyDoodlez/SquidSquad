---
type: learning
tags: [skill, testing, run_tests, pytest, ci-gate, drift, auto-discovery]
created: 2026-06-12
updated: 2026-06-12
owner: skill
status: active
confidence: high
source: observation
links: [decision-deterministic-testing, learning-create-test-environments]
---

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
