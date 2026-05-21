# CONTEXT-9740 — Cursor Re-Anchor + Per-Event Advance Race in event_poll.py

**Issue**: #9740
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-21
**Status**: pending → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9740 + this CONTEXT-9740.md combined are the contract for skill at pickup.

---

## Scope

Fix the cursor re-anchor race in `references/scripts/event_poll.py`'s eviction-gap handler. The re-anchor write is moved to AFTER the per-event processing loop, conditional on `events == []`. This eliminates the window where a successful pre-loop re-anchor write followed by a failed per-event write leaves the cursor pointing at `oldest_id` without that event ever being emitted to stdout, causing permanent event loss on retry. No harness contract changes, no new files, no config changes. A ~5-line diff in `poll()`.

---

## 1. Locked Decisions

### D1. Option A — Move re-anchor write to after the per-event loop (conditional on empty batch)

**Locked: the fix is exactly Option A from RESEARCH-9740.md §3.** Remove the pre-loop re-anchor write at line 233 from its current position (before `for event in events:`). Replace it with a post-loop guard: write `oldest_id` only when `payload.get("evicted")` is true AND `oldest_id` is truthy AND `events` is empty (the all-filtered case). When events are present, the per-event loop's last successful write already leaves the cursor at a valid id >= `oldest_id`, so no separate re-anchor is needed.

Reasoning: the pre-loop write is the bug. It advances the cursor to `oldest_id` before any event is emitted. If any subsequent per-event write fails, the cursor is stuck at `oldest_id` but the `oldest_id` event was never delivered. On retry, `since=oldest_id` semantics skip it forever. Option A eliminates this by deferring the write until it is safe — after all events that can succeed have been processed. Option B (break instead of return) introduces double-delivery risk on retry. Option C (shadow-file two-phase) is over-engineered with no safety benefit over A. The fix is reversible, localized to the eviction branch, and has no behavioral change for non-eviction polls.

### D2. Partial-batch policy — ACCEPT partial delivery on mid-batch disk failure

**Locked: partial-batch delivery on a mid-batch per-event disk failure is ACCEPTED behavior.** If 3 of 5 events succeed and the 4th per-event write fails, the cursor sits at event 3's id (the last successful write), events 4 and 5 are lost, and `poll()` returns `None`. This matches the behavior of the existing non-eviction code path (lines 251–258 already return `None` on per-event write failure). All-or-nothing batch semantics would require a buffered-emit-with-rollback redesign — that is a separate enhancement, not in scope for this bug.

Reasoning: the reported bug is specifically about event loss when `oldest_id` itself is never emitted. Making the eviction path consistent with the existing fatal-on-disk-fail policy (which already accepts partial-batch loss on the non-eviction path) is the correct scope boundary. Widening to all-or-nothing guarantees would affect the non-eviction path too and is a deliberate design change requiring its own research and approval.

### D3. EVICTION warning position — STAYS in current pre-loop position

**Locked: the EVICTION warning print (currently around lines 227–232) stays where it is.** It fires when eviction is first detected, before any write or event processing. Only the cursor write moves. The warning is informational; its ordering relative to event emission is not part of the bug and is explicitly locked per CONTEXT-9331 §4 (warning format and position frozen).

Reasoning: moving the warning would be an unrelated change. It does not affect correctness, introduces unnecessary diff noise, and touches frozen territory. Keep the diff minimal.

### D4. `oldest_id is None` with `evicted: true` — fatal (return None)

**Locked: if `payload.get("evicted")` is true but `oldest_id` is None (or falsy), the post-loop guard must NOT write the cursor, and `poll()` must return `None` (fatal).** This is a harness bug indicator: the harness returned `evicted: true` without supplying `oldest_id`, which violates the eviction contract. Returning `None` causes the caller to exit with code 2, forcing operator attention rather than silently continuing with a stuck cursor.

Reasoning: papering over a missing `oldest_id` by staying on the stale evicted cursor would cause a permanent EVICTION warning loop — the same outcome as the current bug but triggered by a different root cause. This path should be unreachable if the harness is correct; treating it as fatal makes harness bugs visible immediately. The existing pre-loop guard at line 233 already checks `if oldest_id` — the post-loop guard must mirror this exactly.

### D5. Test injection — monkeypatch on `_write_cursor_atomic` (skill's call; no production hook)

**Locked: regression tests for disk-write failure simulate the failure by monkeypatching `_write_cursor_atomic` at test time. No injectable failure hook is added to the production function.** The existing `_write_cursor_atomic` signature (lines 91–126) is unchanged.

Reasoning: adding an injectable fail hook (`fail_at_call_n` parameter or similar) to production code is test-induced pollution. The function is a pure file-system operation with a well-defined return value on failure (`False`). Monkeypatching at the call site used in the eviction handler is sufficient, standard Python testing practice, and leaves production code clean. This is consistent with the project's existing test patterns.

---

## 2. Grounded File References

All line numbers from RESEARCH-9740.md §2 (based on current main):

### 2.1 Primary edit target

- `references/scripts/event_poll.py:233` — **REMOVE** the pre-loop re-anchor write block:
  ```python
  if oldest_id and not _write_cursor_atomic(role, str(oldest_id)):
      return None
  ```
  This block sits inside `if payload.get("evicted"):`, before the `for event in events:` loop at line 238.

- `references/scripts/event_poll.py:238` (post-loop, after the `for` loop body) — **ADD** post-loop re-anchor guard:
  ```python
  if payload.get("evicted") and oldest_id and not events:
      if not _write_cursor_atomic(role, str(oldest_id)):
          return None
  ```
  Variable scoping: `oldest_id` is currently read inside the `if payload.get("evicted"):` block. It must survive to the post-loop site. Extract it before the `for` loop begins, or ensure the eviction block sets it in the enclosing function scope.

### 2.2 Read-only context (do not edit)

- `references/scripts/event_poll.py:80–88` — `_read_cursor_from_working_state` / `_resolve_cursor`: shows how `oldest_id` becomes the cursor on retry (the "since=oldest_id skips the event" path explained in RESEARCH-9740.md §2.3).
- `references/scripts/event_poll.py:91–126` — `_write_cursor_atomic`: the function being monkeypatched in tests. Signature, return value, and failure behavior are unchanged.
- `references/scripts/event_poll.py:251–258` — per-event cursor advance + emit: unchanged by this fix. This is the correct advance-then-emit ordering per spec §3.5.
- `references/scripts/event_poll.py:307–311` — main loop: calls `poll()`, exits code 2 on `None` return. No change.

---

## 3. Acceptance Criteria

**AC-1 (core fix — non-eviction path unchanged)**: On a normal (non-eviction) poll with a successful batch, `event_poll.py` behavior is identical to before this fix. The per-event cursor advance at line 251 and the stdout emit at line 257 still fire in the same order for every event.

**AC-2 (core fix — eviction + non-empty batch, all writes succeed)**: When `payload.get("evicted")` is true and `events` is non-empty and all per-event writes succeed, the function completes normally. The cursor is left at the id of the last event in the batch (the last successful per-event write). No pre-loop re-anchor write occurs.

**AC-3 (core fix — eviction + empty batch, re-anchor write succeeds)**: When `payload.get("evicted")` is true and `events` is empty (all-filtered), the function writes `oldest_id` to the cursor after the (no-op) for loop and returns normally. Forward progress is preserved: the next poll call will use `oldest_id` as the cursor, not the stale evicted id.

**AC-4 (core fix — eviction + non-empty batch, per-event write fails mid-batch)**: When `payload.get("evicted")` is true and the per-event `_write_cursor_atomic` call fails partway through the batch, the function returns `None`. The cursor is at the id of the LAST SUCCESSFULLY written event (not `oldest_id`). The `oldest_id` event and all events emitted before the failure were already emitted to stdout. No pre-loop write has set the cursor to `oldest_id`.

**AC-5 (regression — no pre-loop re-anchor on eviction + non-empty batch)**: The pre-loop re-anchor write (previously at line 233) no longer exists. Confirmed by code inspection and by test: given an eviction payload with non-empty events, `_write_cursor_atomic` is NOT called before the per-event loop begins.

**AC-6 (D4 — `oldest_id is None` with evicted)**: When `payload.get("evicted")` is true but `oldest_id` is `None` or absent from the payload, the post-loop guard does not call `_write_cursor_atomic`. The function returns `None` (fatal). No silent continuation.

**AC-7 (D4 — `oldest_id is None` + empty batch)**: Same as AC-6 but with an empty `events` list — function still returns `None`, not a no-op success.

**AC-8 (variable scope)**: `oldest_id` is accessible at the post-loop site. If previously scoped inside the `if payload.get("evicted"):` block, it is now extracted or re-read at the correct scope level without duplication.

---

## 4. Out of Scope

- **AUDIT-A Risk 2** — in-flight dispatch with no consumer (`harness.py:1674–1678`): separate issue, untouched.
- **AUDIT-A Risk 5** — cursor advance before Monitor output is read during scan: architectural documentation gap, not a code fix.
- **`_write_cursor_atomic` hardening** (retry logic on transient OS errors): separate enhancement. The fatal-on-disk-fail policy is intentional.
- **Harness-side `oldest_id` guarantee** — whether the harness always supplies `oldest_id` when `evicted: true` is a harness contract question. This fix assumes existing behavior and does not harden the harness.
- **`event_bus_reader.py` silent eviction drop** (AUDIT-A Integration Risks): polling-mode agents only, separate path.
- **All-or-nothing batch semantics**: accepted as out of scope per D2.
- **Non-eviction per-event write failure behavior**: the current `return None` on disk failure for non-eviction polls is unchanged and not reviewed here.

---

## 5. Sequencing

**Tier**: 1 — pre-event-flip blocker. This fix must ship before the fleet is flipped to `event-driven: yes`.

**Ordering relative to active pipeline**:

| Issue | Description | Relationship |
|-------|-------------|--------------|
| #9741 | (other pre-flip item) | Sibling Tier 1 — independent, can ship in parallel |
| #9742 | (other pre-flip item) | Sibling Tier 1 — independent, can ship in parallel |
| #9744 | (other pre-flip item) | Sibling Tier 1 — independent, can ship in parallel |
| Fleet event-driven flip | `event-driven: yes` in config | Blocked on #9740 + siblings all merged |

**This fix is self-contained**: no dependency on #9741/#9742/#9744. Skill can pick up immediately once this CONTEXT is approved. A merged #9740 unblocks nothing on its own — the full Tier 1 set must ship before the flip.

**Agent reboot**: this fix does not require an agent reboot on its own. The eviction-gap handler is exercised only when an agent cursor predates the retained deque window (rare — typically only after a long outage). The fleet reset that accompanies the event-driven flip will reboot all agents anyway.

---

## 6. Risk Notes for Skill at Pickup

1. **Variable scoping is the only non-trivial part of the diff.** Confirm that `oldest_id` is extracted from the `if payload.get("evicted"):` block scope and is reachable at the post-loop guard site. If `oldest_id` was only set inside that block, it may be `None` by reference at the post-loop site if `payload.get("evicted")` is false — guard correctly with `if payload.get("evicted") and oldest_id and not events`.

2. **Eviction flag must also be captured before the loop.** The post-loop guard calls `payload.get("evicted")` again. This is fine (payload is immutable within `poll()`), but if skill prefers a local variable (`evicted = payload.get("evicted")`), ensure it is set before the `if evicted:` block so both the pre-loop EVICTION warning and the post-loop write guard use the same value.

3. **Test the all-filtered path explicitly.** The all-filtered case (`events == []`) is the legitimate forward-progress path that motivated the original pre-loop write. A test that monkeypatches `_write_cursor_atomic` on the post-loop path and asserts it IS called (with `oldest_id`) on an empty batch is the regression that would have caught the original bug.

4. **Monkeypatch target**: `_write_cursor_atomic` is a module-level function in `event_poll.py`. Monkeypatch as `event_poll._write_cursor_atomic` (or wherever it is imported/defined in the test's module context). Skill confirms the exact patch path against the import structure.

5. **Low blast radius.** The eviction branch fires only when `payload.get("evicted")` is true — an uncommon operational condition. The change is safe to ship without a coordinated fleet operation.

6. **No compose step needed.** This fix is a script change only (`references/scripts/event_poll.py`). No sub-skill rewrites, no `compose.py deploy`, no `installer-files.txt` update.

---

## 7. Open Questions Resolved

| Q | From RESEARCH | Locked |
|---|---------------|--------|
| Q1 | Partial-batch-on-mid-batch failure: acceptable or all-or-nothing? | **ACCEPT** partial batch — matches existing non-eviction path behavior. All-or-nothing is a separate larger redesign, out of scope. |
| Q2 | Test injection: monkeypatch vs injectable fail hook in production? | **Monkeypatch** `_write_cursor_atomic` at test time. No production hook added. |
| Q3 | EVICTION warning position: move with the write or stay? | **STAYS** in current pre-loop position. Only the cursor write moves. |
| Q4 | `oldest_id is None` + `evicted: true`: fatal or retry silently? | **Fatal** — return None. Harness bug indicator; do not paper over. |

---

## 8. Next Step

PM transitions #9740 `open → planned`. Human reviews CONTEXT-9740.md. On approval, PM transitions `planned → approved`. Skill picks up, implements the ~5-line diff in `references/scripts/event_poll.py`, writes unit tests (monkeypatch `_write_cursor_atomic`), and opens a PR targeting main. QA derives `TEST-PLAN-9740.md` from the AC list above at verification time.
