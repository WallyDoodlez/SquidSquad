I've reviewed all three planning documents for #9873-A. Here are my findings, focusing on correctness, edge cases, wedge-hazard interactions, and architectural consistency.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/CONTEXT-9873-A.md`
- **Line**: D4 (line ~53) + D11 (line ~88) + D5 (line ~62)
- **Severity**: error
- **Issue**: Lock type is incompatible with the two required usage contexts. D5 requires holding `event_lifecycle._lock` from a FastAPI async endpoint handler (asyncio event loop). D4+D11 require holding the same lock inside `asyncio.to_thread` (thread-pool thread). If `_lock` is `asyncio.Lock`, it cannot be acquired from `to_thread` (not async-safe across threads). If `_lock` is `threading.Lock`, holding it in the async endpoint blocks the event loop — exactly the H6 hazard the design is trying to mitigate elsewhere. The CONTEXT does not specify which lock type to use or how to resolve this tension.
- **Evidence**: D5 mandates "Read `_cursors[role]` under `event_lifecycle._lock`" in the endpoint. D4 mandates wrapping "cursor advance + persist" in `await asyncio.to_thread(...)`. D11 mandates holding `EventLifecycleManager._lock` during that same advance+persist. No lock type can satisfy both `async with` in an event-loop handler and `with` in a thread-pool worker without either crashing (asyncio.Lock across threads) or blocking the event loop (threading.Lock in async handler). RESEARCH §2.1 already flags the existing `_persist()` at harness.py:665-686 as an H6 hazard precisely because it holds a lock during sync file I/O on the event loop — suggesting the existing lock IS a `threading.Lock` and the hazard already exists.
- **Suggested fix**: Either: (a) document the lock as `threading.Lock` and accept the brief event-loop block for the D5 dict read (trivial for a dict lookup, unlike the file-I/O case), with explicit rationale in the CONTEXT; or (b) split into two locks — a `threading.Lock` for the write path (cursor advance+persist in to_thread) and an `asyncio.Lock` for the read path (endpoint), accepting a benign race between read and write; or (c) make the D5 endpoint read lock-free (read `_cursors[role]` without holding `_lock`, accepting a momentarily stale value) since a dict `.get()` is atomic in CPython.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/CONTEXT-9873-A.md` vs `.squidsquad/vault/galaxy/decision-event-bus-architecture-redesign.md`
- **Line**: CONTEXT D6 (line ~67) vs vault lines ~40-42
- **Severity**: warning
- **Issue**: The vault decision (authoritative architectural document) locks the payload field as `ack_for`: `payload {ack_for: <original_event_id>, role: <self>}`. CONTEXT D6 locks the payload field as `event_id`: `{event_id: str, role: str}` for `ack-cursor` and `{event_id: str, result: str}` for `ack-stop`. The CONTEXT's §7 Q1 resolution claims "Option 2 (human direction)" resolved this, but the vault was not updated to reflect the split or the field-name change. Anyone consulting the vault (which is labeled `status: active`, `confidence: high`) will find a conflicting schema.
- **Evidence**: Vault line ~40: `event_type="ack"`, payload `{ack_for: <original_event_id>, role: <self>}`. CONTEXT D6: `event_type="ack-cursor"`, payload `{event_id: str, role: str}`. These are incompatible. The vault is referenced in §5 of the CONTEXT risk notes ("The vault note uses `ack_for`") and in RESEARCH §7 as authoritative. If the vault is the canonical reference for architectural decisions, it now contains stale information that will misdirect future work.
- **Suggested fix**: Either update the vault to reflect the D6 split (two types, both using `event_id`), or add a changelog entry noting the human override and marking the single-`ack`/`ack_for` section as superseded. The vault's `updated` timestamp should be bumped.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/RESEARCH-9873-A.md` vs `.squidsquad/pm/planning/CONTEXT-9873-A.md`
- **Line**: RESEARCH §8 Step 4 (line ~318) vs CONTEXT D9 (line ~78)
- **Severity**: warning
- **Issue**: RESEARCH §8 Step 4 recommends retaining the old `event_lifecycle.ack(ack_for, role)` call alongside the new `advance_cursor` call in the ack-cursor handler: "Keep the existing `event_lifecycle.ack(ack_for, role)` call to maintain in-flight clearing for any events that were dispatched via the old path (defensive no-op if in-flight is empty)." CONTEXT D9 states "the ack-consumer advances `_cursors[role]` — it does not populate `_in_flight`" and the locked inline handler extension in D2/D6 makes no mention of preserving the old `ack()` call. The implementer following the RESEARCH as implementation guidance will include a dead code path that always returns False (since dispatch() is never called, `_in_flight` is always empty). Conversely, an implementer following only the CONTEXT may not realize the old `ack()` call needs to be explicitly removed rather than silently kept.
- **Evidence**: RESEARCH line ~318: "Keep the existing `event_lifecycle.ack(ack_for, role)` call." CONTEXT D9: "the ack-consumer advances `_cursors[role]` — it does not populate `_in_flight`." The CONTEXT's authoritative scope statement says the CONTEXT overrides the RESEARCH, but the RESEARCH is the implementation guidance artifact. This contradiction risks PR churn.
- **Suggested fix**: Add an explicit statement to CONTEXT §2 grounded references (harness.py:1533-1558 row) that the old `event_lifecycle.ack()` call in the inline handler is REMOVED from the `ack-cursor` branch. Or, if the intent is to keep it as a defensive no-op, state that explicitly in the CONTEXT with rationale.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/CONTEXT-9873-A.md`
- **Line**: D8 (line ~73) + AC-8 (line ~120)
- **Severity**: warning
- **Issue**: D8 and AC-8 require rejecting `ack-cursor` when "`event_id` is no longer in the deque (FIFO-evicted)." But the deque (`EventStream._stream`) stores event objects, not raw event_id strings. The CONTEXT provides no guidance on how to perform this membership check. RESEARCH §6 risk note 4 suggests "use the existing `get_recent` API" — but `get_recent(N)` returns the last N events, which requires scanning up to 1000 events per ack and constructs a new list. The eviction check's performance characteristics and correctness depend entirely on whether `get_recent` (or an equivalent) provides a linear scan with correct snapshot semantics under `EventStream._lock`.
- **Evidence**: RESEARCH §2.1 describes `EventStream._stream` as `collections.deque`. Deque membership for objects requires either iterating the deque or maintaining a separate ID→object index. Neither the CONTEXT nor the RESEARCH specifies which approach to use, nor whether there's a pre-existing method on `EventStream` that provides O(1) ID lookup. RESEARCH risk note 4 says "the check must hold `EventStream._lock` (or use the existing `get_recent` API)" — but `get_recent` is an O(n) copy operation, and it's unclear if it includes ALL events or only recent N.
- **Suggested fix**: Add a specification to CONTEXT §2 grounded references or risk notes: either (a) confirm that `EventStream` has or will gain an `__contains__` or `has_event(event_id)` method with O(n) linear scan acceptable for the expected ack volume; or (b) specify that the eviction check uses `get_recent(maxlen)` and document the performance implication. Also note whether the check is done under `EventStream._lock` and confirm the lock ordering with `EventLifecycleManager._lock`.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/CONTEXT-9873-A.md`
- **Line**: §2 grounded references, row "harness.py:665-686" (line ~104) + AC-2 (line ~113)
- **Severity**: warning
- **Issue**: The existing `.event-state.json` file (in deployments that predate -A) has no `"cursors"` key. On harness boot after -A deployment, the `load()` method must handle a missing `"cursors"` key without crashing. AC-1 addresses this ("defaults to an empty dict if absent"), but the grounded references for `_persist()` and `load()` at harness.py:665-686 only mention "add `'cursors'` key to JSON output; keep same atomic-write pattern." There is no explicit mention of the backward-compatible load path — the `load()` method must use `data.get("cursors", {})` or equivalent. An implementer who only extends `_persist()` may forget to make `load()` defensive.
- **Evidence**: AC-1: "The attribute is populated from `.event-state.json` on harness boot if the `'cursors'` key is present, and defaults to an empty dict if absent." Grounded references row for load: "extend `_persist()` + `load()` for cursor key" — no explicit mention of the defensive `.get()` pattern for pre-migration state files. The existing `.event-state.json` shape (§2.9 of RESEARCH) shows no `"cursors"` key.
- **Suggested fix**: Add an explicit note to the grounded references row for harness.py:665-686: "`load()` must use `data.get('cursors', {})` to handle pre-migration `.event-state.json` files that lack the `'cursors'` key."

---

### Finding 6

- **File**: `.squidsquad/pm/planning/CONTEXT-9873-A.md`
- **Line**: D11 (line ~88) + §7 Q3 resolution (line ~160)
- **Severity**: warning
- **Issue**: D11 locks "Last-write-wins is acceptable" for concurrent `ack-cursor` events to the same role, justified by "acks are monotonically increasing in practice." However, the Q3 resolution acknowledges that event IDs are "16-char random hex — not lexicographically ordered" and sequence numbers are deferred. In the window between -A shipping and sequence numbers being added (deferred to -B or later), out-of-order ack delivery could regress a role's cursor to an earlier event. This would cause `GET /events/for/{role}?since={regressed_cursor}` to re-deliver events the agent already processed. While "very unlikely in practice" (RESEARCH §9 Q3), there is zero guard against it — no timestamp check, no sequence number, not even a log warning when cursor moves backward.
- **Evidence**: D11: "Last-write-wins is acceptable (acks are monotonically increasing in practice; event IDs are not lexicographically ordered so no monotonic comparison is possible)." Q3 resolution: "Sequence numbers deferred." The interaction: if two `ack-cursor` events for role "pm" arrive with event_ids "abc123" (newer) and "def456" (older, delayed), and "def456" is processed last, the cursor regresses to "def456". The agent would then re-poll events between "def456" and "abc123" — creating a duplicate-delivery cycle with no detection mechanism.
- **Suggested fix**: At minimum, add a debug-log warning when an `ack-cursor` advances the cursor to an event_id that appears earlier in the deque than the current cursor (detectable by deque position comparison, not string comparison). Alternatively, defer the eviction check's "is in deque" to also verify the acked event_id is not behind the current cursor position (reject acks that would regress the cursor). This uses deque ordering, which is reliable.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/CONTEXT-9873-A.md`
- **Line**: §6 risk notes, item 4 (line ~148)
- **Severity**: warning
- **Issue**: Risk note 4 says "Skill must implement a deque membership lookup before advancing the cursor. The deque is `EventStream._stream` (a `collections.deque`) — the check must hold `EventStream._lock` (or use the existing `get_recent` API) to be safe. Do not advance and then check; check first." This adds a lock-acquisition requirement (`EventStream._lock`) that is NOT reflected in D11, which only mentions `EventLifecycleManager._lock`. The implementer must acquire TWO locks in the correct order. If `advance_cursor` holds `EventLifecycleManager._lock` and then acquires `EventStream._lock` for the eviction check, the lock ordering is `EventLifecycleManager._lock` → `EventStream._lock`. The CONTEXT does not verify that this ordering is consistent with all other code paths. RESEARCH §2.1 confirms `_persist()` does `self._lock` → `self._stream.get_recent(200)` (which acquires `EventStream._lock`), so the ordering is consistent for those two paths — but no audit is documented for other paths that might acquire these locks in reverse order.
- **Evidence**: D11: "The ack-consumer must hold `EventLifecycleManager._lock` during cursor advance and persist." Risk note 4: "the check must hold `EventStream._lock` (or use the existing `get_recent` API) to be safe." Two distinct locks required, but the CONTEXT's lock-ordering guidance is a one-line risk note rather than a verified lock-ordering specification.
- **Suggested fix**: Add a verified lock-ordering statement to D11 or §6: "Confirmed: all code paths acquiring both `EventLifecycleManager._lock` and `EventStream._lock` do so in the order `EventLifecycleManager._lock` → `EventStream._lock`. No reverse-order acquisition exists. The eviction check in `advance_cursor` follows this same ordering." This requires a one-time audit of the codebase.

---

**Summary**: One error (lock type incompatibility across asyncio/thread contexts), six warnings spanning vault inconsistency, RESEARCH/CONTEXT contradiction on old `ack()` call, underspecified eviction-check implementation, missing backward-compat load path specification, cursor-regression detection gap, and undocumented two-lock ordering requirement. No architecturally regressive choices identified — the locked decisions are internally consistent in intent, but the implementation-level specifications have hazardous gaps around concurrency primitives and mutation-detection.