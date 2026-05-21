# RESEARCH-9415 — 32-bit Event ID Collision Audit

**Issue**: #9415
**Phase**: 1 (Research)
**Author**: pm-lead
**Date**: 2026-05-21 (cycle 1538)

---

## 1. Question

Event IDs in the harness use a 32-bit identifier space (`os.urandom(4).hex()` in one path, `sha256(content)[:8]` in another — both yield 8-char hex). Per the birthday paradox, collision probability hits ~50% at ~65k events. Cursor logic that treats id-equality as "same event" can break under collision. What's the right fix?

Flagged by Ilya0527 (ALEF research agent) on #8999, cycle 1511.

---

## 2. The Actual Mechanism (Grounded in Code)

### 2.1 Two parallel ID generators

The codebase has TWO independent event-ID generation paths:

**Path 1 — `references/scripts/event_bus.py:_generate_id` (line 64):**
```python
def _generate_id(event_type, role, timestamp, payload):
    """Generate a short 8-char event ID from content hash."""
    raw = f"{timestamp}{role}{event_type}{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]
```
- Content-addressed (deterministic given inputs).
- 32-bit space (8 hex chars from SHA-256 prefix).
- Called from `event_bus.emit()` at line 88, which is called by `git_ops.py` and any caller using the public `emit()` API.

**Path 2 — `references/scripts/harness.py:2140`:**
```python
"id": os.urandom(4).hex(),
```
- Pure random.
- 32-bit space.
- Called from `_emit_event()` (harness-internal helper for events the harness itself produces — e.g. PR-merge events, compose-completed events).

Two paths, same 32-bit space, different generation strategies.

### 2.2 Where IDs are consumed

- **`event_poll.py:243`** — `event_id = event.get("id")` → used as the cursor value written to `working-state.md`.
- **`event_poll.py:251`** — `_write_cursor_atomic(role, str(event_id))` — cursor write.
- **`harness.py:get_since(since_id, limit)`** (line ~595) — linear scan over the `collections.deque`, comparing `event["id"] == since_id` to find the cursor position.
- **`harness.py:EventLifecycleManager`** (line ~610) — uses `event_id` as a dict key for `_in_flight`, `_dispatched`, `_dispatch_times`, `_retry_counts`. Direct equality matching.

If two events share an `id`, the linear scan in `get_since` will match the FIRST occurrence; the second is effectively skipped. The lifecycle manager's dict keys will collide; the second event's metadata silently overwrites the first.

### 2.3 Current state (live evidence from `.event-state.json`)

```
event count: 200
unique ids: 200
id lengths: {8}
```

All 200 events in the current retained window have unique IDs. No collision observed at this volume — but 200 is far below the birthday threshold.

### 2.4 Collision math

For an n-bit space (n=32 here, so 2^32 = ~4.3B possible values):
- 50% collision probability at ~sqrt(2 * 2^n * ln 2) ≈ sqrt(2 * 4.3B * 0.693) ≈ **77k events**
- 1% collision probability at ~sqrt(2 * 2^n * 0.01) ≈ **9.3k events**
- 0.1% at ~3k events

The harness deque has `maxlen=1000`, so at any moment only 1000 events are retained. Collisions within those 1000 are extremely rare (probability ~1000^2 / (2 * 4.3B) ≈ 0.012%). **The real risk is across the lifetime of the bus**, not within the deque.

Specifically:
- **`get_since(since_id)`** — searches the CURRENT deque (1000 events). Low collision risk WITHIN the search; just need the `since_id` to be unique within the deque, which it is at any given moment.
- **Persisted cursors** in `working-state.md` (and the `oldest_id` from eviction signals) — these are IDs that PREDATE the current deque. If an old id collides with a current id, an agent's cursor could "resolve" to the wrong position on resume.

So the real concern is: an agent's cursor written long ago could collide with a current event ID, causing the linear scan to anchor at the wrong position.

### 2.5 Are there ALSO collision risks from the content-based path?

Yes, but different. `event_bus._generate_id` is deterministic: two events with the same `{timestamp, role, event_type, payload}` produce the same ID. Two distinct events at the same second with identical payload (e.g., two `git-push main` events) WILL collide deterministically — not probabilistically.

Is that a bug or a feature?
- **Bug**: distinct events should have distinct IDs for tracking purposes.
- **Feature**: idempotency — emitting the same event twice produces the same id, so consumers can dedupe.

Per the current architecture (broadcast bus, agents react to event types not specific instances), idempotency on the content-based path is probably accidental — `git-push` events SHOULD be distinct each time they happen.

---

## 3. Failure Modes (Concrete)

### 3.1 Persisted cursor collision

1. Agent A processes event with id `a3f2`, writes cursor=`a3f2` to working-state.
2. Agent A is idle for hours. Event id space rolls past 65k events; `a3f2` gets generated again for a different event.
3. Agent A boots. Reads cursor=`a3f2`. Linear scan finds the NEW event with `a3f2`. Agent skips all events between the OLD `a3f2` and the new one — possibly the entire deque.

Probability: low at current event rates (maybe 100 events/day = 65k events takes ~2 years). But it's a latent failure that only surfaces with system longevity.

### 3.2 Eviction-signal oldest_id collision

1. Eviction-gap path: harness returns `oldest_id` to agent.
2. Agent advances cursor to `oldest_id`.
3. Cursor written. Persists.
4. If a future event collides with this `oldest_id`, the same re-anchor problem applies.

### 3.3 EventLifecycleManager dispatch collision

1. Event A dispatched, recorded in `_dispatched[id]`.
2. Event B happens to share id. Dispatch overwrites the dict entry.
3. Ack for A or B can no longer be disambiguated.

This is much rarer (need collision within the in-flight set, which is small) but possible.

### 3.4 Same-content collision (Path 1 only)

1. Two `git-push` events for `main` at the same `timestamp` (truncated to second) with identical payload.
2. `_generate_id` produces same id.
3. Second event's metadata overwrites first in dispatch dict; the second event is effectively swallowed.

Probability: depends on activity. With multi-agent commits per second, plausible at busy times.

---

## 4. Options Surveyed

### Option A — ULID (128-bit time-sortable)

Replace both id generators with [ULID](https://github.com/ulid/spec) — 26-char alphanumeric, 128-bit, time-sortable. Each ULID encodes a 48-bit millisecond timestamp prefix + 80-bit randomness.

Implementation: add `ulid-py` dependency (PyPI), use `ulid.new()` in both ID-gen sites.

**Pros**:
- 128-bit space — collision probability negligible (~2^-128 per generation).
- Time-sortable — events naturally sort by ID, useful for monotonic-id-curious future work (e.g., reviving #9265's in-stream gap idea).
- Standard format (RFC-like spec, widely supported).

**Cons**:
- New dependency (ulid-py).
- Existing persisted cursors (8-char hex) will not match any ULID — one-time eviction-signal fires per agent at migration boundary. Acceptable noise.
- 26-char IDs are ~3x longer than current 8-char ones — slightly larger payloads in events + cursors.

### Option B — 64-bit random hex

Replace `os.urandom(4).hex()` with `os.urandom(8).hex()`, and `sha256(...)[:8]` with `sha256(...)[:16]`. Same generators, double-length output.

Implementation: change two literal numbers (4→8, 8→16). No new dependencies.

**Pros**:
- Minimal change (no new dependency).
- 64-bit space — collision probability at 65k events drops from ~50% to ~0.000000001%. Effectively immune to birthday paradox at any practical volume.
- Compatible with existing string-based ID handling everywhere (just a wider string).

**Cons**:
- Doesn't address content-based path's same-content collisions (Path 1 issue from §3.4). Need separate fix there.
- No ordering guarantee — IDs are still random, can't reason about temporal order from ID alone.
- Migration: same one-time eviction-signal noise as Option A.

### Option C — UUID4

Use `uuid.uuid4()` → 36-char or 32-char hex string. 122-bit randomness.

Implementation: replace both ID-gen calls with `uuid.uuid4().hex`. No new dependency (stdlib).

**Pros**:
- Standard library, no extra dep.
- 122-bit space — effectively unique forever.
- Widely understood format.

**Cons**:
- No time-sortability (vs ULID).
- 32-char IDs (longer than current).
- Doesn't address content-collision in Path 1.

### Option D — Hybrid time-prefix + random suffix

Format: `<6-byte epoch-ms hex>-<6-byte random hex>` (e.g., `01856f3a4ab7-a3f29b41ce82`). 24 chars total, 96-bit total space, time-sortable.

Implementation: small custom function, no dep.

**Pros**:
- Time-sortable (prefix orders).
- 96-bit space (50% collision at ~9 quintillion events).
- No external dependency.
- Cleaner than ULID's base32 encoding for log readability.

**Cons**:
- Custom format — yet another non-standard ID scheme in the world.
- Same migration noise.
- Same content-collision concern in Path 1 needs separate handling.

### Option E — Status quo + collision-detection guard

Keep 32-bit IDs. Add a sanity check in `event_bus.emit()` and `harness._emit_event()` that detects collisions with the current deque before persisting; on collision, regenerate.

**Pros**:
- No format change.
- No migration impact.

**Cons**:
- Doesn't fix cross-deque-lifetime collisions (the cursor-resumption scenario in §3.1).
- Adds a deque-scan on every emit — performance impact.
- Doesn't fix content-collision in Path 1.

### Recommendation

**Option B (64-bit random hex)** + **fix Path 1 separately**. Reasoning:

- Option B is the minimum viable change for the random path (#3 occurrences in code, all literal-number changes). Removes the 32-bit birthday risk entirely without new dependencies or 3x-longer IDs.
- ULID's time-sortability is nice but not load-bearing — agents don't currently sort events by ID; they scan linearly.
- UUID is overkill at 122 bits and 32 chars.
- The CONTENT-collision risk on Path 1 (`_generate_id`) is a separate bug — need to add some entropy beyond `{timestamp, role, event_type, payload}` so two identical-content events at the same second produce distinct IDs. Recommendation: append `os.urandom(2).hex()` to the hash input (4 hex chars of randomness per content hash), or include a per-process emit counter.

Two fixes ship together:
1. Path 2 (harness `os.urandom(4)`): change to `os.urandom(8)` → 64-bit random.
2. Path 1 (event_bus `_generate_id`): keep sha256 base but add randomness so distinct events don't collide; widen output to 16 hex chars while we're touching it.

---

## 5. Open Questions for CONTEXT (Phase 2)

1. **Do we need time-sortable IDs?** If yes, Option A (ULID) or D (hybrid). If no, Option B suffices.
   - PM rec: **no**. Agents scan linearly, sortability isn't used today. KISS — Option B.

2. **Path 1's content-collision bug — fix in scope or separately?**
   - PM rec: **fix in scope of #9415** since both paths produce 8-char hex and the audit scope is "event id space." Adding randomness to Path 1 is a 1-line change.

3. **Migration handling — do existing cursors in `working-state.md` break?**
   - PM rec: **accept one-time eviction-signal noise** per agent. Once an agent's old cursor (8-char hex) doesn't match any retained event in the new (16-char hex) world, the eviction-gap path fires once, re-anchors to oldest available, and continues. Same migration pattern we documented for #9331.

4. **Width: 16 hex (64-bit) vs 24 hex (96-bit)?**
   - PM rec: **16 hex (64-bit)** — sufficient. 96-bit is overkill for the collision math and adds 8 chars to every event payload + cursor write.

5. **Drop the content-based path entirely and use random everywhere?**
   - PM rec: **keep both, but unify on random + entropy.** Content-based has the deterministic property which is useful for idempotency in some niche cases. Add per-emit randomness so distinct events with same content still differ.

6. **Library dependency: stdlib only?**
   - PM rec: **yes, stdlib only.** Avoid ulid-py.

7. **Tests**: how to verify the fix?
   - PM rec: assert ID lengths increased to 16; emit 10000 events, assert all unique; emit same-content event twice, assert distinct IDs.

8. **Communication to existing in-flight agents**: anything?
   - PM rec: no notification needed. Migration is mechanical (run cycle, eviction-signal fires once, agent re-anchors).

---

## 6. Dependencies

- `references/scripts/event_bus.py:_generate_id` (line 64) — change `[:8]` → `[:16]` + add entropy.
- `references/scripts/harness.py:2140` — change `os.urandom(4).hex()` → `os.urandom(8).hex()`.
- `references/scripts/harness.py:EventStream.get_since` (~line 595) — works correctly on longer IDs (string equality), no change needed.
- `references/scripts/event_poll.py:243-251` — works on longer IDs (treats as opaque strings), no change needed.
- `references/sub-skills/common-events/cursor-management.md` — text mentions `<event-id>` generically, no change needed.
- Tests under `tests/test_event_bus.py` (if exists) — update length assertions.
- Tests under `tests/test_harness.py` — update if any test asserts specific id format.

## 7. Non-Goals

- Reviving #9265's in-stream gap scenario (still architecturally inapplicable to broadcast bus).
- Monotonic / sequential IDs (separate discussion if ever needed).
- Migrating existing `.event-state.json` events to the new format — let them age out of the deque (1000-event window cycles in hours).
- Backward compatibility for any external tooling that parses 8-char IDs (none exists per audit).

## 8. Risks

1. **Migration produces one-time eviction-signal noise per agent.** Each agent's `working-state.md` has an old-format cursor; first poll after upgrade triggers the eviction-gap path. Acceptable per our existing eviction-handling protocol.
2. **Tests with hardcoded 8-char ID assertions will fail** post-upgrade. Audit + update.
3. **Same-content collision in Path 1 was perhaps intentional** somewhere we haven't seen. Recommend a quick audit before adding entropy.
4. **Slight payload size increase** (~16 chars per event). Negligible.

## 9. Next Step

Write CONTEXT-9415.md locking the chosen approach + answers to the 8 questions. Then human approval gate. Then skill picks up (autonomously since it's role:skill + status:pending — though the human direction was "don't auto-approve tasks," only bugs).
