# CONTEXT-9415 — 32-bit Event ID Collision Audit

**Issue**: #9415
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-21 (cycle 1538)
**Status**: pending → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9415 + this CONTEXT-9415.md combined are the contract for skill at pickup. The body describes the symptom; this file locks the fix mechanism.

---

## 1. Locked Decisions

All 8 RESEARCH-9415.md §5 questions answered. Decisions:

### D1. Time-sortable IDs (Q1)

**Locked: not needed.** IDs stay opaque random/random-augmented hex strings; no time prefix, no sort order.

Reasoning: agents scan the event deque linearly. Sortability is not used today and would be premature optimization. KISS.

### D2. Content-collision fix in scope (Q2)

**Locked: yes, both ID paths fixed in this issue.**

The two paths:
- **Path 1** — `event_bus.py:_generate_id` (content-hash). Add randomness to inputs so identical-content events get distinct IDs.
- **Path 2** — `harness.py:2140` (pure random). Widen to 64-bit.

Reasoning: same audit scope; both produce 8-char hex; fix together, single PR.

### D3. Migration handling (Q3)

**Locked: accept one-time eviction-signal noise per agent.**

Existing 8-char cursors in `working-state.md` won't match any 16-char ID in the new world. First poll after upgrade → eviction-gap path fires → re-anchor to oldest available id → continue normally. Same pattern #9331 already established.

Reasoning: no migration code needed; eviction path is the documented recovery for this exact scenario.

### D4. Width (Q4)

**Locked: 16 hex characters (64-bit).**

Reasoning: 64-bit space → birthday collision at ~5 billion events. Practically infinite for our use case. 96-bit (24 char) is overkill; doubles payload size for no benefit at our scale.

### D5. Keep both paths or unify? (Q5)

**Locked: keep both, add entropy to the content-based path.**

Path 1 stays content-hashable (preserves the idempotency property for callers that want it) but adds 2 bytes of `os.urandom` to the hash input so distinct events with identical content still produce distinct IDs.

Implementation sketch:
```python
def _generate_id(event_type, role, timestamp, payload):
    """Generate a 16-char event ID — content hash + per-emit entropy."""
    nonce = os.urandom(2).hex()  # 4 hex chars of randomness
    raw = f"{timestamp}{role}{event_type}{json.dumps(payload, sort_keys=True)}{nonce}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

Path 2 implementation:
```python
"id": os.urandom(8).hex(),  # was: os.urandom(4).hex()
```

Reasoning: Path 1's idempotency-via-content-hash might be useful for niche callers (none observed today, but easy to preserve). Adding the nonce makes distinct emits distinct without removing the content-derived property.

### D6. Library dependency (Q6)

**Locked: stdlib only.** No `ulid-py`, no `uuid` (overkill at 122-bit), no external libraries. `os.urandom` + `hashlib` already in use.

### D7. Tests (Q7)

**Locked: two targeted tests, not a stress test.**

1. **Length assertion**: emit one event each through Path 1 and Path 2, assert `len(id) == 16` for both. Catches typos like `[:8]`, `os.urandom(4).hex()` left in place.
2. **Same-content emits differ (Path 1 only)**: emit two events with identical `{event_type, role, timestamp, payload}`. Assert IDs are distinct. Catches missing entropy in `_generate_id`.

Dropped from initial draft: the 100-unique spot check. Defense against `os.urandom` being silently constant is paranoia; the OS-provided randomness source is trustworthy. Two tests above cover the realistic implementation bugs.

### D8. Communication to existing agents (Q8)

**Locked: no notification needed.**

Migration is mechanical:
- Agents currently running have old-format 8-char cursors in their `working-state.md`.
- After upgrade, their next event poll triggers the eviction-gap path (cursor not found in deque).
- Agent logs the eviction warning, re-anchors to oldest available id, continues.
- No PR comment, no tracker message, no human intervention.

If a fleet-wide reboot happens to coincide with the upgrade (which it often does given how SquidSquad ships): agents restart with the new behavior already in place; eviction fires once and clears.

---

## 2. Grounded File References

### 2.1 Primary fix sites

- `references/scripts/event_bus.py:_generate_id` (line 64) — change SHA-256 slice from `[:8]` → `[:16]` + add `os.urandom(2).hex()` nonce to the hash input per D5.
- `references/scripts/harness.py:2140` (`_emit_event` helper) — change `os.urandom(4).hex()` → `os.urandom(8).hex()`.

### 2.2 Files that consume IDs (no change needed, listed for verification)

- `references/scripts/event_poll.py:243-251` — treats IDs as opaque strings; works on 16-char strings unchanged.
- `references/scripts/harness.py:EventStream.get_since` (~line 595) — string equality comparison; width-agnostic.
- `references/scripts/harness.py:EventLifecycleManager` (~line 610) — dict keys are strings; width-agnostic.

### 2.3 Documentation that mentions ID format

- `references/sub-skills/common-events/cursor-management.md` — uses `<event-id>` placeholder, no concrete width. No change needed.
- `docs/EVENT-BUS-ARCHITECTURE.md` — verify it doesn't pin the 8-char width somewhere. If it does, update to 16-char.

### 2.4 Tests

- `tests/test_event_bus.py` (if exists) — update if it has hardcoded 8-char assertions. Add the two D7 tests.
- `tests/test_harness.py` — update similarly.

---

## 3. Acceptance (Restated from #9415 Body)

- `event_bus._generate_id` produces 16-char hex; identical-content emits produce distinct IDs.
- `harness._emit_event` produces 16-char hex (via `os.urandom(8).hex()`).
- Existing tests pass (with updated length assertions where needed).
- Two new D7 tests added.
- Live: post-upgrade, existing agents' first poll triggers the eviction-gap path once, then resumes normally. Verify via the next cycle's `orphan-cleanup.jsonl` and per-agent diagnostics (or just watch tracker comments).
- No regression in `event_poll.py` cursor handling.
- `docs/EVENT-BUS-ARCHITECTURE.md` checked for stale 8-char references; updated if found.

---

## 4. Out of Scope

- Reviving #9265's in-stream gap scenario (still architecturally inapplicable to broadcast bus).
- Monotonic/sequential IDs.
- ULID or UUID adoption.
- Migrating existing `.event-state.json` events to new format (let them age out of the 1000-event deque).
- Reorganizing the two ID-generation paths into a single shared helper (could be a refactor follow-up if desired; out of #9415 scope).

---

## 5. Sequencing

- Ship independently of #9588, #9725, #9688, #9478. No ordering constraint.
- After ship: agents on next poll trigger eviction-gap once each, resume cleanly. No human action required.
- Watch for ~30 minutes post-ship to confirm no regression (eviction-gap path was already exercised in #9331 work, so this is just re-running through it).

---

## 6. Risk Notes (for skill at pickup)

1. **Eviction-signal noise on first post-upgrade poll**: expected, documented above (D3). Don't treat eviction logs as errors.
2. **Tests with hardcoded 8-char ID expectations** will fail. Audit before push: `grep -rn "\.id.*[a-f0-9]\{8\}[^a-f0-9]\|len.*== ?8\|\[:8\]" tests/ references/` then update.
3. **Path 1 entropy: don't over-engineer.** `os.urandom(2)` is 4 hex chars = 65k combinations, well sufficient when combined with content hash. No need for larger nonce.
4. **Path 1 deterministic property is preserved by callers passing the SAME pre-generated nonce.** If any caller depends on identical-content-produces-identical-id behavior, it can pre-compute the nonce (or accept it as a parameter). Currently no such caller exists per audit; if you find one in the wild, surface it before shipping.
5. **Don't change the call signature of `_generate_id`** unless you find a need — Path 1 callers depend on `(event_type, role, timestamp, payload)`. Adding entropy inside is invisible to them.

---

## 7. Next Step

PM presents this CONTEXT-9415.md to the human for approval. On approval: PM transitions `pending → planning → planned`, then human approves `planned → approved`. Skill picks up.
