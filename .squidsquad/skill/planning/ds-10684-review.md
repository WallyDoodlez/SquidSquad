Here are my findings:

---

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 626–653 (`save_state`), 676–680 (`load_state`), 234 (`__init__`), 108–110 (comment)
- **Severity**: error
- **Issue**: `compose_freshness_failed` is documented as "persisted" but is never written to or read from `.harness-state.json`. The module comment at line 108–110 says: *"if a previous boot persisted `compose_freshness_failed=True`, that's still honored."* The E5 task description says the escape hatch *"leaves any persisted compose_freshness_failed flag alone (intentional — operator bypass shouldn't clear a real prior failure)."* But:
  - `save_state()` (line 653) constructs `state_data` with keys `harness_pid`, `start_time`, `port`, `last_compose_checksum`, and `agents` — **no `compose_freshness_failed` key**.
  - `load_state()` (line 680) restores only `last_compose_checksum` — **no `compose_freshness_failed` restoration**.
  - `HarnessState.__init__` (line 234) always sets `self.compose_freshness_failed = False`.

  **Consequence**: On a harness restart with `--no-freshness-check` after a prior compose failure, the flag is always `False` (initialized by `__init__`, never restored from disk). The `_deferred_init` thread at line 1397 reads `False` → proceeds to auto-start agents against a potentially broken compose set. The escape hatch's documented protection ("operator bypass shouldn't clear a real prior failure") is dead code.

  The test at `test_harness_freshness_restart_e5.py` line 180–181 even assumes this persistence works: *"load_state() reads from disk and could restore it from a prior crash"* — but `load_state()` does not do this.

- **Evidence**: AC4 requires "failed compose restart" to refuse spawning. The code does this for the current boot (in-memory flag), but a restart with the escape hatch silently clears it. The comment explicitly claims cross-boot persistence that doesn't exist.

- **Suggested fix**: 
  1. Add `"compose_freshness_failed": self.compose_freshness_failed` to the `state_data` dict in `save_state()` (line 626–653).
  2. In `load_state()`, after restoring `last_compose_checksum` (line 680), add:
     ```python
     self.compose_freshness_failed = state_data.get("compose_freshness_failed", False)
     ```
  3. As a forward-compat migration, use `.get("compose_freshness_failed", False)` so legacy state files without the key default safely.

---

### Finding 2

- **File**: `references/scripts/harness.py`
- **Line**: 1491–1502
- **Severity**: warning
- **Issue**: The "failed" freshness branch sets `state.compose_freshness_failed = True` (line 1492) but does **not** call `state.save_state()`. Only the "repaired" branch (line 1505) calls `save_state()`. If Finding 1 is fixed and `compose_freshness_failed` is added to `save_state`'s output, the failed path must also flush to disk. Otherwise the flag lives only in memory and is lost if the harness crashes before any other code path triggers `save_state()` (e.g., the health poller, an agent event, or a stop/restart request).

- **Evidence**: Compare lines 1503–1505 (`elif _freshness.status == "repaired":` → `state.save_state()`) with lines 1491–1502 (`if _freshness.status == "failed":` → no `save_state()`). The "clean" path (line 1510) also doesn't call `save_state()`, but that's correct — no persistent state changed. The "failed" path changes `compose_freshness_failed`, so it should persist that change.

- **Suggested fix**: After the failed-path log block (line 1502), add `state.save_state()` — placed so it fires after the flag is set and the diagnostic logs are emitted, matching the "repaired" branch's pattern.

---

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 229–230 (comment in `HarnessState.__init__`)
- **Severity**: warning
- **Issue**: The comment says `compose_freshness_failed` is *"Set to True by `_deferred_init` when `compose_freshness.check_and_repair` returns `status='failed'"`*. This is wrong — the flag is set in `lifespan` (line 1492), not in `_deferred_init`. `_deferred_init` only *reads* the flag (line 1397) to short-circuit auto-start. The incorrect comment misleads future readers about where the mutation occurs.

- **Evidence**: Line 1492 (`state.compose_freshness_failed = True`) is inside `async def lifespan(...)`, not inside `def _deferred_init()`. `_deferred_init` at line 1397 only checks `if state.compose_freshness_failed:`.

- **Suggested fix**: Change the comment to: *"Set to True by the lifespan freshness-check block when `compose_freshness.check_and_repair` returns `status='failed'`. The deferred-init thread and all spawn endpoints read this flag to refuse spawning."*