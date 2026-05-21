# QA-RESULTS-9745 — Consolidate wake-mode resolution

**Issue**: #9745
**PR**: #9784
**Branch**: squidsquad/task/9745
**Verified by**: qa-lead
**Date**: 2026-05-21
**Verdict**: **PASS**

## 1. Live-system pytest

```
12 passed in 1.39s
```

| TC | Covers | Result |
|----|--------|--------|
| TC-1 | `config.get_wake_mode` exists as canonical | PASS |
| TC-2 | All 3 callers (compose / cycle_post / statusline_data) delegate to `config.get_wake_mode` | 3/3 PASS |
| TC-3 | No inline field-probe duplication remains in any caller | 3/3 PASS |
| TC-4 | Bootstrap prose mentions per-role override / global / polling consistent with canonical docstring | PASS |
| TC-5 | Behavioral: per-role override beats global default | PASS |
| TC-5b | Behavioral: global default applied when no per-role | PASS |
| TC-5c | Behavioral: default polling on missing config | PASS |
| TC-6 | Dev suites `test_feat_9745_wake_mode_canonical` + `test_compose` + `test_statusline_data` green | PASS (125 in combined invocation) |

## 2. AC walk

| AC | Verdict | Notes |
|----|---------|-------|
| Single shared implementation | PASS | `config.get_wake_mode(role)` at `config.py:176` |
| All three Python callers import from shared location | PASS | TC-2 confirms `from config import get_wake_mode` in compose, cycle_post, statusline_data |
| Bootstrap prose verified against the code via test | PASS | TC-4 + dev's bootstrap-audit tests (4 in test_feat_9745) cover this |

## 3. Setup & Upgrade Sync Check

All N/A — internal refactor, no surface changes.

## 4. Decision

**Verdict**: PASS.

- Promote `TEST-9745-tests.py` → `tests/test_feat_9745_wake_mode_qa_live.py`
- Comment QA verdict on PR #9784
- Auto-merge via harness
- Transition #9745 pending-test → pending-ship
- Increment `Shipped Since Last Bump` 10 → 11 (DM should already be triggering version bump from prior 10)
