# QA-RESULTS-9415 — Widen event IDs to 16 hex + nonce

**Issue**: #9415
**PR**: #9738
**Branch**: squidsquad/task/9415
**Verified by**: qa-lead
**Date**: 2026-05-21
**Verdict**: **PASS**

## 1. Live-system pytest

```
8 passed in 3.88s
```

(See `.squidsquad/qa/planning/TEST-9415-tests.py` → promoted to `tests/test_feat_9415_event_id_widening_live.py`)

| TC | Covers | Result |
|----|--------|--------|
| TC-1 | AC-1 (16-char lowercase hex from `_generate_id`) | PASS |
| TC-2 | AC-1 (identical-content emits distinct via nonce) | PASS |
| TC-3 | AC-1 (different content still distinct — sanity) | PASS |
| TC-4 | AC-2 (`harness._emit_event` produces 16-char hex) | PASS |
| TC-5 | AC-3 (dev's `tests/test_event_bus.py` 16/16 green) | PASS |
| TC-6 | AC-6 (no hardcoded 8-char width assumption in `event_poll.py`) | PASS |
| TC-7 | AC-7 (no stale 8-char refs in `docs/EVENT-BUS-ARCHITECTURE.md`) | PASS |
| TC-8 | regression guard (nonce not a cached constant) | PASS |

## 2. Dev unit suite

- `tests/test_event_bus.py` — 16/16 PASS (includes new D7 tests `test_produces_16_char_hex` and `test_same_inputs_produce_distinct_ids`, plus the new `TestEmitEventIdWidth9415` class for Path 2).
- `tests/test_harness.py` — 10/10 PASS on id-related tests (`-k "_id or _emit or width"`).

## 3. AC walk

| AC | Verdict | Notes |
|----|---------|-------|
| AC-1 (`_generate_id` 16-char + identical content distinct) | PASS | TC-1, TC-2, TC-3, TC-8 + dev's D7 length + distinct-emit tests |
| AC-2 (`harness._emit_event` 16-char) | PASS | TC-4 — harness emits 16-char lowercase hex via `os.urandom(8).hex()` |
| AC-3 (existing tests pass with updated length assertions) | PASS | TC-5 + 16/16 + 10/10 |
| AC-4 (two new D7 tests added) | PASS | Both `test_produces_16_char_hex` and `test_same_inputs_produce_distinct_ids` present in `tests/test_event_bus.py`; plus `TestEmitEventIdWidth9415` for Path 2 |
| AC-5 (post-upgrade eviction-gap path fires once per agent) | PASS structurally | The #9331 eviction-gap path is unchanged and well-tested. The transition fires naturally on first post-upgrade poll — operational, not directly testable in pre-merge QA without deploying. Per CONTEXT D3, this is the documented recovery path |
| AC-6 (no regression in `event_poll.py` cursor handling) | PASS | TC-6 — `event_poll.py` contains no hardcoded 8-char width assumptions |
| AC-7 (`docs/EVENT-BUS-ARCHITECTURE.md` updated) | PASS | TC-7 — no stale `os.urandom(4)` / `[:8]` / "8-hex" / "32-bit" claims; doc references nonce + 16-char width |

## 4. Observation (NOT blocking)

CONTEXT-9415 D5 locks a **2-byte (16-bit / 65k-value) nonce** in `_generate_id`. This satisfies the AC literal ("identical-content emits produce distinct IDs") at the realistic-use-case level: 2 same-content emits collide with probability 1/65536 ≈ 0.0015%, and SquidSquad's actual emit cadence (≈1 event per cycle per role, 30-min cycle) makes same-content same-timestamp bursts vanishingly rare.

A QA stress-test of 5000 same-content emits produced ~4823 unique IDs (collisions consistent with birthday paradox in a 16-bit nonce space). This is **not a regression** — it's the locked behavior. CONTEXT Risk Note #3 explicitly anticipated this trade-off ("Path 1 entropy: don't over-engineer. `os.urandom(2)` is 4 hex chars = 65k combinations, well sufficient when combined with content hash").

If a future task needs high-burst same-content emits (e.g. a stress fixture or batch-emission API), a wider nonce or per-call timestamp jitter would be the appropriate follow-up. Not in scope for #9415.

## 5. Out-of-scope verifications

- `references/scripts/monitor_smoke_poller.py:24` still uses `uuid.uuid4().hex[:8]` — this is a stand-alone smoke-test poller, not a production event-bus path, and is not named in CONTEXT-9415 §2.1. Confirmed via inspection: emits its own arbitrary ids for the Monitor-tool smoke test, never enters `event_bus.emit` or `harness._emit_event`. No regression.

## 6. Setup & Upgrade Sync Check

- New config values: N/A
- New files/directories: N/A
- Modified template structure: N/A
- Added/removed sub-skills: N/A
- Changed role composition: N/A
- Upgrade path: zero-touch. Per CONTEXT D3 + D8, existing agents trigger the #9331 eviction-gap path once on their first post-upgrade poll, re-anchor, and continue. No human action required.

## 7. Decision

**Verdict**: PASS.

- Promote `TEST-9415-tests.py` → `tests/test_feat_9415_event_id_widening_live.py`
- Comment QA verdict on PR #9738 (self-approve blocked — same author)
- Auto-merge via harness per project config
- Transition #9415 pending-test → pending-ship
- Increment `Shipped Since Last Bump` 8 → 9
