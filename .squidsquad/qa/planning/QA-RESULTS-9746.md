# QA-RESULTS-9746 — Regenerate agent-instructions.md + drift detection

**Issue**: #9746
**PR**: #9778
**Branch**: squidsquad/task/9746
**Verified by**: qa-lead
**Date**: 2026-05-21
**Verdict**: **PASS** (with one non-blocking observation about run_tests.py wiring)

## 1. Live-system pytest

```
7 passed in 0.57s
```

| TC | Covers | Result |
|----|--------|--------|
| TC-1 | canonical exists + non-trivial | PASS |
| TC-2 | matches fresh compose_all() | PASS |
| TC-3 | has post-#9588 boot-bootstrap section | PASS |
| TC-4 | no stale inline ralph-loop-overview | PASS |
| TC-5 | no pre-#9478 branch-workflow vestiges | PASS |
| TC-6 | drift test exists at documented path | PASS |
| TC-7 | drift test runs green under plain pytest | PASS |

## 2. Dev unit suite

`tests/test_feat_9746_agent_instructions_drift.py` — **4/4 PASS** (canonical exists; matches fresh compose; no branch-workflow; has boot-bootstrap).

## 3. AC walk

| AC | Verdict | Notes |
|----|---------|-------|
| AC-1 (regenerate + commit references/agent-instructions.md) | PASS | TC-1 + TC-2: file present, 1482 lines, byte-identical to fresh `compose_all()` output |
| AC-2 (CI check or pre-commit hook preventing future drift) | PASS | Dev's `tests/test_feat_9746_agent_instructions_drift.py` (4 tests) catches drift. Discoverable via plain `pytest tests/` (TC-7) — the standard invocation used by humans and any future CI |

## 4. Non-blocking observation

The drift test is NOT wired into `tests/run_tests.py:STATIC_TEST_MODULES`. Anyone running `python tests/run_tests.py static` (the project's curated entry point) will NOT execute it. Anyone running plain `pytest tests/` WILL.

Disposition: Accept as-is. The test file follows the `test_*.py` pattern so pytest auto-discovers it. No CI workflow exists in `.github/workflows/`, so wiring it into `run_tests.py` would be the only formal trigger. Suggest a one-line follow-up: append `"test_feat_9746_agent_instructions_drift"` to `STATIC_TEST_MODULES`. Non-blocking — the test runs and catches drift under standard pytest invocation today.

## 5. Setup & Upgrade Sync Check

- New config values: N/A
- New files/directories: N/A
- Modified template structure: regenerated `references/agent-instructions.md` to reflect #9588 + #9478 source state
- Added/removed sub-skills: N/A
- Changed role composition: N/A
- Upgrade path: zero-touch

## 6. Decision

**Verdict**: PASS.

- Promote `TEST-9746-tests.py` → `tests/test_feat_9746_agent_instructions_qa_live.py`
- Comment QA verdict on PR #9778
- Auto-merge via harness
- Transition #9746 pending-test → pending-ship
- Increment `Shipped Since Last Bump` 9 → 10 (Ship Threshold reached — DM triggers version bump)
