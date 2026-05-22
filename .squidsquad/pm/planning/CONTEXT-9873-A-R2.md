# CONTEXT-9873-A-R2 — Amendment: DeepSeek Review Findings F1/F3/F4/F5/F6/F7

**Issue**: #9873-A (foundation slice of #9873 umbrella)
**Phase**: 2 (Locked Decisions — Revision 2)
**Author**: pm-lead
**Date**: 2026-05-21
**Supersedes**: `CONTEXT-9873-A.md` on findings F1, F3, F4, F5, F6, F7 only
**DeepSeek review source**: `.squidsquad/pm/planning/REVIEW-9873-A-DEEPSEEK.md`

---

## Authoritative Scope Statement

This R2 **amends** `CONTEXT-9873-A.md` on the six locked findings listed in the header. Every section of the original CONTEXT that is NOT explicitly amended here remains in force without change. Skill must read BOTH documents before pickup; where they conflict, R2 governs.

F2 (vault inconsistency) is a PM follow-up item outside skill's pickup scope — see §5.

---

## §1 Amendments to Locked Decisions

### Amendment to D5 (Finding F1 — ERROR: lock type mismatch)

**Original D5** required reading `_cursors[role]` "under `event_lifecycle._lock`" from the `GET /events/cursor/{role}` endpoint.

**R2 resolution — Option (c), lock-free dict read:**

`GET /events/cursor/{role}` reads `self._cursors.get(role)` **WITHOUT holding any lock**. CPython dict `.get()` is atomic at the interpreter level. A momentarily stale-by-microseconds value is acceptable; cursor updates are infrequent (one per agent ack batch). Holding `threading.Lock` on the async endpoint path would block the event loop — exactly the H6 hazard the design mitigates elsewhere.

**Write path (advance_cursor + persist)** uses `threading.Lock` — this is the existing `EventLifecycleManager._lock` type (confirmed by RESEARCH-9873-A §2.1: `_persist()` at `harness.py:665-686` acquires `self._lock` during sync file I/O, establishing it as a `threading.Lock`). No type change is required.

**D5 as amended**: The endpoint reads `self._cursors.get(role)` with no lock acquisition. The write path retains `threading.Lock` per D11.

---

### Amendment to D9 (Finding F3 — RESEARCH vs CONTEXT contradiction)

**Original D9** stated "the ack-consumer advances `_cursors[role]`" but did not explicitly call out removal of the old `event_lifecycle.ack()` call.

**RESEARCH-9873-A §8 Step 4** recommended retaining `event_lifecycle.ack(ack_for, role)` as a defensive no-op. **That recommendation is OVERRIDDEN.**

**R2 resolution:** The old `event_lifecycle.ack()` call in the inline handler at `harness.py:1533-1558` **MUST be removed** from the `ack-cursor` branch. It is dead code (dispatch() is never called → `_in_flight` is always empty → `ack()` always returns False). Retaining it creates a misleading code path. There is no defensive value; no in-flight entries exist. The CONTEXT-9873-A authoritative scope statement overrides RESEARCH §8 Step 4 on this point.

**D9 as amended**: The `ack-cursor` branch DOES NOT call `event_lifecycle.ack()`. It calls only `advance_cursor(role, event_id)` (wrapped in `asyncio.to_thread`). The `ack-stop` branch is unaffected.

Grounded reference: `harness.py:1533-1558` — the `if event_type == "ack":` block that becomes the `ack-cursor` / `ack-stop` split. The old `event_lifecycle.ack(ack_event_id, role)` call at approximately line 1537 is removed from the `ack-cursor` branch only.

---

### Amendment to D8 (Finding F4 — eviction check underspecified)

**Original D8** locked rejection of ack-cursor for evicted event_ids but left the membership check mechanism unspecified.

**R2 resolution:** Add a new method `EventStream.has_event(event_id: str) -> bool` that iterates `_stream` (the `collections.deque`) under `EventStream._lock`. Returns `True` if any event in the deque has the matching id, `False` otherwise.

Rationale for a named method over inline iteration: cleaner API, testable in isolation, consistent with existing `get_recent()` pattern on the same class.

Performance: deque is bounded at `maxlen=1000`. O(n) scan per ack is acceptable at current agent counts and ack frequency.

**Lock ordering**: `EventLifecycleManager._lock` (outer, write path) → `EventStream._lock` (inner, membership check). Consistent with existing `_persist()` path at `harness.py:665-686` which acquires `self._lock` then calls `self._stream.get_recent(200)` (which acquires `EventStream._lock`). See §4 for the lock-ordering audit step.

**D8 as amended**: The eviction check calls `event_lifecycle._stream.has_event(event_id)` (or equivalent via the new method). If `False`, ack is rejected, cursor unchanged, debug log emitted. This check happens BEFORE `advance_cursor` is called (check first, never advance then check).

---

### New Decision D15 — Cursor Regression Detection (Finding F6)

**Context**: D11 accepted last-write-wins for concurrent acks, and Q3 (RESEARCH §9) acknowledged event IDs are random hex with no lexicographic ordering. However, deque insertion order IS reliable. Out-of-order ack delivery could silently regress a role's cursor without any detection mechanism.

**R2 resolution:** During the eviction check (the O(n) deque scan in `has_event`), also record the **deque position** of the current cursor (`_cursors.get(role)`) and the deque position of the ack target (`event_id`). Both lookups happen in the same O(n) pass at no additional cost.

If the ack target's deque position is **earlier** (lower index) than the current cursor's deque position, the ack is **rejected**:
- Do NOT advance the cursor.
- Emit debug log: `"ack-cursor regression rejected: event_id={event_id} at position {p_ack} < cursor at position {p_cursor} for role={role}"`

Edge cases:
- If the current cursor is `None` (first boot): no position comparison — accept the ack normally (no regression possible with no cursor).
- If the current cursor's event_id is itself not in the deque (prior eviction): skip the regression check and proceed to the standard eviction check for the ack target.

This detection uses deque ordering (reliable), not string comparison (not reliable for random hex IDs).

---

### Amendment to §2 Grounded References — load() backward compatibility (Finding F5)

**Original §2** row for `harness.py:610-658` described `load()` as extending to "restore `_cursors` from .event-state.json" without specifying the defensive pattern.

**R2 resolution:** `load()` MUST use `data.get("cursors", {})` (not `data["cursors"]`) to handle pre-migration `.event-state.json` files that lack the `"cursors"` key. A KeyError here would crash harness boot on existing deployments.

This is a backward-compatibility requirement, not optional. Existing `.event-state.json` files (shape documented in RESEARCH-9873-A §2.9) have no `"cursors"` key.

---

## §2 Updated Grounded File References

The following rows **replace** their counterparts in CONTEXT-9873-A.md §2. All other rows remain unchanged.

| File | Lines | Change (R2 amendment) |
|------|-------|----------------------|
| `references/scripts/harness.py` | 610–658 | `EventLifecycleManager`: add `_cursors` dict, `advance_cursor()`, `get_cursor()` methods; extend `_persist()` and `load()`. **`load()` MUST use `data.get("cursors", {})` for backward-compat with pre-migration state files (F5).** |
| `references/scripts/harness.py` | new endpoint after line ~1688 | `GET /events/cursor/{role}`: reads `self._cursors.get(role)` **with NO lock** (lock-free dict read — CPython atomicity; F1 amendment). Returns `{cursor, role}`, 200 always. |
| `references/scripts/harness.py` | 1533–1558 | Inline ack-handler: split into `ack-cursor` branch and `ack-stop` branch. **`ack-cursor` branch MUST NOT call `event_lifecycle.ack()` — old call is REMOVED (F3 amendment).** `ack-cursor` branch calls only `advance_cursor` via `asyncio.to_thread`. |
| `references/scripts/harness.py` | `EventStream` class | Add `has_event(event_id: str) -> bool` method: iterates `_stream` under `EventStream._lock`, returns `True` if any event matches `event_id` (F4). Also records deque positions for regression detection during the same pass (F6). |

---

## §3 New / Amended Acceptance Criteria

The following ACs are **added to** or **amend** those in CONTEXT-9873-A.md §3. Original AC-1 through AC-14 remain in force except where explicitly superseded below.

**AC-3 (AMENDED — lock-free read)**: `GET /events/cursor/{role}` reads `self._cursors.get(role)` without acquiring any lock. No `async with` or `with` lock acquisition occurs in the endpoint handler path. The read is fire-and-read; momentarily stale values are acceptable.

**AC-1 (AMENDED — backward-compat load)**: `EventLifecycleManager` initializes `_cursors` to `data.get("cursors", {})` when loading `.event-state.json`. If the `"cursors"` key is absent (pre-migration file), `_cursors` defaults to `{}` without raising a `KeyError`. Harness boot on an existing deployment (no `"cursors"` key in the state file) must succeed without error.

**AC-15 (`has_event` method)**: `EventStream` has a `has_event(event_id: str) -> bool` method. The method acquires `EventStream._lock` and iterates `_stream`. Returns `True` if any event object in the deque has an `id` (or equivalent field) matching `event_id`. Returns `False` otherwise. O(n) scan; deque maxlen=1000.

**AC-16 (eviction check uses `has_event`)**: The `ack-cursor` handler calls `has_event(event_id)` on the stream before calling `advance_cursor`. If `has_event` returns `False`, the cursor is NOT advanced, a debug-level log entry is emitted, and the ack is silently rejected (AC-8 from original CONTEXT remains the observable contract; this AC specifies the mechanism).

**AC-17 (regression detection)**: When the `ack-cursor` handler receives an `event_id` that IS present in the deque but at a deque position **earlier** than the current cursor's position, the cursor is NOT advanced and a debug-level log entry is emitted with the text `"ack-cursor regression rejected"`. The cursor value returned by `GET /events/cursor/<role>` is unchanged.

**AC-18 (old `ack()` call removed from `ack-cursor` branch)**: The `ack-cursor` branch of the inline handler at `harness.py:1533-1558` does NOT call `event_lifecycle.ack()`. A code search for `event_lifecycle.ack(` in the `ack-cursor` branch returns no results. The `ack-stop` branch is unaffected.

**AC-19 (lock ordering — write path)**: The `advance_cursor` method (called from thread pool via `asyncio.to_thread`) acquires `EventLifecycleManager._lock` before calling any `EventStream` method (including `has_event`). No code path in the `ack-cursor` handler acquires `EventStream._lock` before `EventLifecycleManager._lock`. Skill documents the verified lock ordering in a code comment on `advance_cursor`.

---

## §4 Audit Step for Skill (Finding F7 — Lock Ordering Verification)

**Before merging this PR**, skill must perform a one-time codebase audit to verify no reverse-order lock acquisition exists:

**Verified ordering**: `EventLifecycleManager._lock` (outer) → `EventStream._lock` (inner).

**Audit procedure**:
1. Find every code path that acquires `EventLifecycleManager._lock` (search for `self._lock` within `EventLifecycleManager` methods): `_persist()`, `ack()`, `dispatch()`, and the new `advance_cursor()`.
2. For each such path, check if it also calls any `EventStream` method that acquires `EventStream._lock` (currently: `get_recent()`, and the new `has_event()`). If yes, confirm `EventLifecycleManager._lock` is already held at the call site.
3. Find every code path that acquires `EventStream._lock` directly (within `EventStream` methods or external callers).
4. Confirm no path acquires `EventStream._lock` and then attempts to acquire `EventLifecycleManager._lock` (reverse order = potential deadlock).

**Known safe paths** (from RESEARCH-9873-A §2.1): `_persist()` at `harness.py:665-686` already acquires `self._lock` → calls `self._stream.get_recent(200)` → acquires `EventStream._lock`. This is the established ordering.

**PR gate**: Add a comment to `advance_cursor` citing the verified lock ordering. The PR description must include a one-line statement: "Lock ordering audit complete — no reverse-order acquisition found" (or document any exceptions found and their mitigations).

This is a **verification task**, not new code. No implementation change is required if existing paths are already correct.

---

## §5 PM Follow-Up TODOs (Outside Skill's Pickup Scope)

**F2 — Vault note update (PM action, separate operation):**

The vault note `.squidsquad/vault/galaxy/decision-event-bus-architecture-redesign.md` contains a stale schema (`event_type="ack"`, payload `{ack_for, role}`) that conflicts with the CONTEXT-9873-A D6 locks (`ack-cursor` / `ack-stop` split, payload field `event_id`). This inconsistency was noted in REVIEW-9873-A-DEEPSEEK.md Finding 2.

PM will update this vault note in a separate vault-update operation (not part of this PR). The update will:
- Mark the single-`ack`/`ack_for` section as superseded by the two-type split
- Add a changelog entry referencing the human override and the locked CONTEXT-9873-A D6 decision
- Bump the `updated` timestamp

**Skill does NOT need to update the vault note.** This is PM's domain.

---

## §6 Open Questions Resolved (DeepSeek Findings Map)

| Finding | Severity | Resolution |
|---------|----------|------------|
| F1 — Lock type incompatible across asyncio/thread contexts | error | Lock-free dict read on endpoint (Option c). Write path uses existing `threading.Lock`. D5 amended. |
| F2 — Vault `decision-event-bus-architecture-redesign.md` has stale schema | warning | PM vault-update in separate operation. Not part of skill's PR. See §5. |
| F3 — RESEARCH §8 Step 4 recommends retaining old `ack()` call; CONTEXT D9 does not | warning | Old `ack()` call REMOVED from `ack-cursor` branch. RESEARCH recommendation overridden. D9 amended. AC-18 added. |
| F4 — Eviction check mechanism unspecified | warning | New `EventStream.has_event(event_id) -> bool` method specified. Lock ordering documented. D8 amended. AC-15/AC-16 added. |
| F5 — `load()` lacks explicit backward-compat pattern for pre-migration files | warning | `data.get("cursors", {})` mandated. AC-1 amended. §2 grounded ref row updated. |
| F6 — No regression detection for out-of-order acks | warning | Deque-position comparison during eviction scan. Reject + debug-log if regression detected. D15 added. AC-17 added. |
| F7 — Two-lock ordering undocumented and unaudited | warning | Lock ordering specified: ELM._lock → EventStream._lock. Audit step added as PR gate. AC-19 added. See §4. |

---

## §7 Next Step

R2 stands as the **final locked contract** for #9873-A. The combined CONTEXT-9873-A.md (original) + this R2 amendment are the authoritative specification.

PM transitions #9873-A `planning` → `planned`. Skill picks up on human approval (`planned` → `approved`). The pre-approval body-vs-CONTEXT sync check applies to both CONTEXT-9873-A.md and this R2 — the GitHub issue body must be consistent with the union of both documents at the `planned → approved` transition.
