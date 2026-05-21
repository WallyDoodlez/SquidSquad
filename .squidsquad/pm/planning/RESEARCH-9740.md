# RESEARCH-9740 — Cursor Re-Anchor + Per-Event Race Loses Event

**Issue**: #9740
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## 1. Problem Statement

In `references/scripts/event_poll.py` lines 204–258, the eviction-gap handler contains a race
window that can permanently lose one event.

**Trigger**: An agent's cursor predates the harness's retained deque window (eviction detected via
`payload.get("evicted")`). The handler is supposed to re-anchor the cursor to `oldest_id` and then
process the batch. But the re-anchor write is performed BEFORE the per-event processing loop. If
the re-anchor write succeeds (line 233) but any subsequent per-event cursor write fails (line 251),
the cursor file is left pointing at `oldest_id`. The event stored at `oldest_id` was never emitted
to stdout, so the calling agent never sees it. On retry, the poll call resolves the cursor as
`oldest_id`, which the harness treats as "already seen," and that event is skipped forever.

**Loss condition**: exactly one event (the one whose id equals `oldest_id`) is permanently dropped.
All subsequent events in the same batch that precede the failed write are also dropped (cursor
advanced past them without stdout emission), but `oldest_id` itself is the canonical case named in
the issue.

**Failure vector**: disk full, permission error, or OS-level filesystem fault during a
`_write_cursor_atomic` call (line 251). This is non-hypothetical: `_write_cursor_atomic` is already
documented as returning `False` on `OSError` (line 123–126).

---

## 2. Code-Grounded Findings

### 2.1 Re-anchor write (the premature cursor advance)

```
references/scripts/event_poll.py:233
    if oldest_id and not _write_cursor_atomic(role, str(oldest_id)):
        return None
```

This write sets the cursor to `oldest_id` BEFORE the `for event in events:` loop at line 238.
The comment at lines 210–221 explains the rationale: on the `/events/for/{role}` endpoint, a role
filter may strip every event in the batch (`events == []`), leaving the cursor stuck on the
still-evicted stale id. Anchoring first guarantees forward progress in that all-filtered case.

The intent is correct. The ordering is the bug.

### 2.2 Per-event cursor advance (the failing write that triggers the race)

```
references/scripts/event_poll.py:251–258
    if not _write_cursor_atomic(role, str(event_id)):
        return None
    print(json.dumps(event), flush=True)
```

When this write fails, `poll()` returns `None`. The caller (main loop, lines 307–311) exits with
code 2. No event has been emitted to stdout for the failed write's target event. But the cursor
file already holds `oldest_id` from line 233.

### 2.3 Retry reads cursor from working-state.md

```
references/scripts/event_poll.py:80–88  (_read_cursor_from_working_state)
references/scripts/event_poll.py:76–88  (_resolve_cursor)
```

On next invocation, `_resolve_cursor` reads `working-state.md`. It finds `oldest_id`. The next
`GET /events?since=oldest_id` call returns events with id >= oldest_id EXCLUSIVE (harness standard
"since" semantics). The event at `oldest_id` itself is never re-delivered.

### 2.4 Atomic write implementation

```
references/scripts/event_poll.py:91–126  (_write_cursor_atomic)
```

The write uses the `tmp-then-replace` pattern (`tmp.write_text(body)` then `tmp.replace(path)`).
The atomicity guarantee covers the file-swap step. It does NOT help when `tmp.write_text` or
`tmp.replace` raises `OSError` — the function returns `False` and the caller gets `None`.

### 2.5 The all-filtered path (why re-anchoring has value)

```
references/scripts/event_poll.py:238  (for event in events:)
```

If `events == []` (all events stripped by role filter), the `for` loop body never executes, so the
per-event advance at line 251 never runs. Without the pre-loop re-anchor (line 233), the cursor
stays on the stale evicted id and the EVICTION warning repeats on every poll forever. This is the
legitimate forward-progress case that the current code solves — but at the cost of the race.

---

## 3. Options

### Option A — Move re-anchor write to AFTER the per-event loop, only on empty batch

**Proposed by**: issue body + AUDIT-A Risk 1.

Replace the pre-loop re-anchor write with a post-loop conditional: write `oldest_id` only when
`events` is empty (the all-filtered case). When events are present, the per-event loop's last
successful write leaves the cursor at a valid id >= oldest_id.

Pseudocode:
```python
if payload.get("evicted"):
    oldest_id = payload.get("oldest_id")
    # ... print EVICTION warning ...
    # Do NOT write cursor here

for event in events:
    # ... existing per-event advance + emit ...

# After loop: if no events survived the filter, advance to oldest_id now
if payload.get("evicted") and oldest_id and not events:
    if not _write_cursor_atomic(role, str(oldest_id)):
        return None
```

**Pros**:
- Eliminates the race entirely. Either no events were processed (batch was all-filtered) and the
  re-anchor write is the only cursor change, or at least one event was processed and the last
  successful per-event write is a valid cursor position.
- Minimal diff — one block moved, one guard added.
- Preserves the forward-progress guarantee (the re-anchor still fires for all-filtered batches).
- No behavior change for the common (non-eviction) path.

**Cons**:
- If the post-loop re-anchor write fails on the all-filtered path, the function returns `None`
  with the cursor still pointing at the stale evicted id. On retry, the EVICTION warning fires
  again. This is safe (no data loss — no events to lose) but means persistent disk failures on
  the all-filtered path loop on EVICTION warnings rather than on per-event failures. The behavior
  is arguably better (no data loss) and matches the fatal-on-disk-fail policy throughout.
- Requires careful variable scoping: `oldest_id` and the `evicted` flag must be accessible after
  the for-loop. The current code reads them inside the `if payload.get("evicted"):` block; they
  need to survive to the post-loop site.

**Risk**: LOW. The change is localized to the eviction branch, which is an uncommon path (only
fires when the cursor predates the retained window — essentially an agent that restarted after a
long outage).

### Option B — Write cursor BEFORE emitting to stdout (tighten per-event ordering; keep re-anchor)

The current per-event code at line 251–258 writes the cursor first, then emits. This ordering is
ALREADY correct for the per-event case (spec §3.5: advance-then-emit). The bug is not in the
per-event ordering but in the pre-loop re-anchor.

Option B attacks the problem differently: keep the re-anchor write but make the per-event write
non-fatal — on disk failure, skip the emit but continue. The cursor stays at `oldest_id`, and the
failed event is re-fetched on next poll.

Pseudocode:
```python
if not _write_cursor_atomic(role, str(event_id)):
    # Instead of return None, break and retry from oldest_id
    break  # cursor already at oldest_id — next poll re-fetches from there
print(json.dumps(event), flush=True)
```

**Pros**:
- No variable-scope changes; the re-anchor block is untouched.
- On per-event disk failure, the function returns the partial batch (events processed so far)
  rather than `None`. The `--wait` loop continues instead of exiting 2.
- The event whose write failed is re-delivered on the next poll (since the cursor is still
  `oldest_id`), at the cost of re-delivering all events from `oldest_id` onward.

**Cons**:
- **Re-delivery of already-emitted events.** All events between `oldest_id` and the failed
  event's predecessor have already been emitted to stdout. On retry, they are emitted again.
  Agents that are not idempotent (most are not currently) will process them twice.
- Changes the fatal-on-disk-fail policy. The current design treats disk failure as "operator
  intervention required" (exit 2). Option B silently re-delivers. This is a semantic change with
  broader implications for the agent contract.
- Does not fix the root cause (premature re-anchor write) — it papers over it.

**Risk**: MEDIUM. The double-delivery side effect may introduce correctness bugs in agents.

### Option C — Two-phase write with rollback: shadow-write oldest_id, overwrite only on empty batch

Write `oldest_id` into a separate per-role shadow cursor file (e.g.
`.squidsquad/<role>/working-state.md.eviction-anchor`). If the batch has events, the per-event
loop writes to the real cursor file as today, and the shadow file is discarded. If the batch is
empty (all-filtered), atomically promote the shadow to the real cursor file.

**Pros**:
- Clean separation of "re-anchor intent" from "committed cursor advance".
- If a per-event write fails, the shadow exists as a recovery hint but does not corrupt the
  real cursor file.

**Cons**:
- Introduces a second file in the role's state directory. This file must be cleaned up on normal
  exit paths (non-eviction polls, successful all-filtered writes, etc.) to avoid stale shadow
  files confusing future recovery logic.
- More code surface than Option A — the shadow-file lifecycle (create, promote, discard) adds
  ~4–6 lines compared to Option A's ~3-line change.
- No meaningful benefit over Option A: Option A is simpler and achieves the same safety guarantee
  without the shadow file.

**Risk**: LOW for correctness, MEDIUM for maintenance complexity.

---

## 4. Recommended Option

**Option A** — move the re-anchor write to after the per-event loop, conditional on `events` being
empty.

Reasons:
- It is the fix suggested by the issue body AND AUDIT-A, which means the contract for the fix is
  already written.
- Minimal code change (one conditional block repositioned, one guard added).
- Preserves all existing behaviors for non-eviction polls.
- No semantic change to the fatal-on-disk-fail policy.
- No re-delivery risk.
- Option B introduces double-delivery risk; Option C is over-engineered relative to the scope.

The implementation is a ~5-line diff in the `poll()` function body. There are no config changes,
no new files, and no harness contract changes.

---

## 5. Open Questions for PM Before Locking Phase 2

1. **Edge case: what if `events` is partially processed before failure?**
   Under Option A, if 3 of 5 events succeed and the 4th per-event write fails, the cursor is at
   event 3's id (last successful write). The 4th and 5th events are lost (per existing fatal-on-
   disk-fail semantics). This is the same behavior as today for the non-eviction path. Is the same
   "no partial delivery guarantee" acceptable for the eviction path, or should we guarantee that
   all-or-nothing within a batch? If all-or-nothing is needed, that is a larger redesign (buffered
   emit with rollback), out of scope for this bug.

2. **Regression test spec: how to simulate disk-write failure deterministically?**
   The acceptance criteria in the issue body say: "simulate disk-write failure mid-batch; assert
   cursor stays at last successfully-persisted event id." The `_write_cursor_atomic` function
   accepts no injectable failure mode today. The dev agent will need to either mock the function
   at test time (monkeypatch) or add an injectable sleep/fail hook. Which approach is preferred
   for this project's test style?

3. **Is `oldest_id` scoping the only diff, or should the EVICTION warning also move?**
   Currently the EVICTION warning prints before the re-anchor write (line 227–232). Under Option A,
   the warning could stay at line 227 (fires as soon as eviction is detected, before any write) or
   move to just before the post-loop write. AUDIT-A notes the warning format is locked per
   CONTEXT-9331 §4. Moving the warning would not change its text, but the order relative to event
   emission would change (warning fires before any event is emitted either way). PM should confirm:
   warning stays in its current position (before the for-loop), and only the write moves.

4. **Should the fix also guard `oldest_id is None`?**
   Line 233 already checks `if oldest_id and not _write_cursor_atomic(...)`. Under Option A, the
   post-loop guard should mirror this: `if evicted and oldest_id and not events`. If `oldest_id`
   is `None` (harness returned `evicted: true` but omitted `oldest_id` — a harness bug), the fix
   should fail gracefully. Is the desired behavior `return None` (fatal) or `continue polling with
   old cursor` (retry)? PM should ask the human or lock in CONTEXT.

---

## 6. Out-of-Scope Notes

- **AUDIT-A Risk 2** (in-flight dispatch with no consumer, `harness.py:1674-1678`): separate
  issue, not touched by this fix.
- **AUDIT-A Risk 5** (cursor advance before Monitor output is read during scan): architectural,
  not a fix-by-reorder problem; tracked as a documentation gap, not a code fix.
- **`_write_cursor_atomic` hardening** (e.g., retry logic on transient OS errors): not in scope.
  The fatal-on-disk-fail policy is intentional per the inline comment at lines 253–257; improving
  it is a separate enhancement.
- **Harness-side `oldest_id` guarantees**: whether the harness always returns `oldest_id` when
  `evicted: true` is a harness contract question. This fix assumes the existing behavior (line 233
  already guards `if oldest_id`); it does not harden the harness.
- **`event_bus_reader.py` silent eviction drop** (AUDIT-A Integration Risks): polling-mode agents
  use this path, not `event_poll.py`; out of scope for #9740.
