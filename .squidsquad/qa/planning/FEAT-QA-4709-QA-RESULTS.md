# FEAT-QA-4709 QA Results — Harness Phase 2: Event Bus + Agent Communication

**Evaluated by**: QA subagent (structural code review)
**Date**: 2026-05-04
**Method**: Static code analysis — reading implementation files without a live harness

---

## Test Case Results

### TC-1: cycle_pre.py emits cycle-start event after writing cycle-input.json

- **Result**: PASS
- **Notes**: In `cycle_pre.py` lines 975–986, `cycle-input.json` is written first (`output_path.write_text(...)`), then `event_bus.emit("cycle-start", role, cycle_number=cycle_number)` is called in a `try/except (ImportError, Exception)` block. Ordering is explicitly correct — the file write precedes the emit. The comment on line 981 reads: `# Emit cycle-start event AFTER cycle-input.json is written (#4709)`.

---

### TC-2: cycle_post.py emits cycle-end event after commit/push

- **Result**: PASS
- **Notes**: In `cycle_post.py` lines 669–676, the emit call appears after steps 1 (commit/push), 2 (status transitions), 3 (tracker comments), 4 (working state), and 5 (iteration log). The payload includes `cycle_type`, `summary` (truncated to 60 chars), and `cycle_number`. The emit is wrapped in `try/except (ImportError, Exception)`. Ordering matches the requirement — cycle-end fires after the commit/push completes.

---

### TC-3: Harness /events endpoint receives and stores events

- **Result**: PASS
- **Notes**: `harness.py` lines 724–754 implement both POST and GET `/events`. The POST handler (`receive_event`) validates `event_type` and `role`, appends to `event_stream`, updates `AgentState`, and logs to console. Returns HTTP 200 `{"status": "ok"}`. GET `/events` returns `{"events": [...], "total": N}` via `event_stream.get_recent(limit)`. Both endpoints are correctly implemented. Events are stored in the order they arrive.

---

### TC-4: Harness console displays events in real-time

- **Result**: STRUCTURAL-PASS
- **Notes**: The `_log_event()` function (lines 671–717) prints to stdout with `flush=True` immediately upon event receipt in the POST handler. The format is `[HH:MM:SS] <role padded to 6> <event_type padded to 18> <detail>`. This matches the documented format (e.g., `[18:32:55] skill  cycle-start        #862`). Verified structurally — real-time behavior requires a running harness to confirm. The implementation pattern (synchronous `print(..., flush=True)` in the request handler) is correct for immediate output.

---

### TC-5: AgentState updates from received events

- **Result**: PASS
- **Notes**: `_update_agent_from_event()` (lines 648–668) handles all three event types:
  - `cycle-start`: sets `current_cycle = cycle_number`, `last_cycle_start = timestamp`
  - `cycle-end`: sets `last_cycle_end = timestamp`, `last_cycle_type = payload.get("cycle_type")`
  - `phase-change`: sets `current_phase = payload.get("phase")`
  If the agent does not exist in state, it is created via upsert: `agent = AgentState(role)` then `state.set_agent(role, agent)`. This satisfies the "create if not exists" upsert behavior described in the regression risks. The GET `/agents` endpoint returns `agent.to_dict()` which exposes all these fields.

---

### TC-6: Bounded event stream (does not exceed 1000 events)

- **Result**: PASS
- **Notes**: `EventStream` class (lines 345–367) uses `collections.deque(maxlen=1000)`. Python's `deque` with `maxlen` automatically evicts the oldest entry when capacity is exceeded — insertion of the 1001st event evicts event 1. The class is thread-safe via `threading.Lock()`. `__len__` reports the actual deque length. This exactly satisfies the TC-6 requirement.

---

### TC-7: .harness-port written to all agent clone directories on startup

- **Result**: FAIL
- **Notes**: The harness writes `.harness-port` only to a single location: `SQUIDSQUAD_DIR / ".harness-port"` (the primary repo's `.squidsquad/.harness-port`). See `lifespan()` lines 401–408 — only one file is written. The harness does NOT iterate over `.local-config` clone paths to write a copy into each agent clone's `.squidsquad/` directory.

  `event_bus.py` compensates for this via a parent-directory walk (lines 42–55) — if the direct `.squidsquad/.harness-port` doesn't exist, it walks up to 5 parent directories looking for a `.squidsquad/.harness-port`. This works when agent clones are children of the primary repo directory, but is not the same as the TC-7 requirement of "each clone directory has a `.squidsquad/.harness-port` file."

  The TC-7 precondition specifically states "write `.squidsquad/.harness-port` into each clone's `.squidsquad/` directory." This is not implemented. The parent-dir walk is a discovery fallback, not equivalent to writing per-clone files. This is a FAIL against the test plan's literal requirement, but the parent-dir walk means event emission will work in practice when clones are subdirectories of the primary repo.

---

### TC-8: event_bus.py no-ops silently when harness is down

- **Result**: PASS
- **Notes**: `event_bus.emit()` wraps the entire body (port discovery + HTTP POST) in a single `try/except Exception: pass` block (lines 73–103). If `urllib.request.urlopen` raises `URLError` (connection refused), `OSError`, `TimeoutError`, or any other exception, the `except Exception` catches it silently. No output to stdout or stderr. Return is implicit (`None`).

---

### TC-9: event_bus.py no-ops when .harness-port file missing

- **Result**: PASS
- **Notes**: `_discover_port()` returns `None` when no `.harness-port` file is found (after both the direct check and the 5-level parent walk). In `emit()`, the first thing after `try:` is `port = _discover_port(); if port is None: return`. This means no HTTP connection is attempted at all when the port file is absent — correct behavior per TC-9. The early return is inside the `try/except Exception` block, so even if `_discover_port()` raised, it would be caught silently.

---

### TC-10: 500ms timeout — never blocks agent cycle

- **Result**: PASS
- **Notes**: `_TIMEOUT = 0.5` (line 25) sets the timeout in seconds (Python's `urllib.request.urlopen` takes seconds, not milliseconds). 0.5 seconds = 500ms — correctly configured. The `urlopen(req, timeout=_TIMEOUT)` call on line 101 applies this timeout to both connect and read. Any timeout exception is caught by the broad `except Exception: pass`. Unit test `test_timeout_respected` verifies elapsed time < 1.5s with a generous CI tolerance.

---

### TC-11: Existing cycle behavior unchanged (events are additive)

- **Result**: STRUCTURAL-PASS
- **Notes**: Both `cycle_pre.py` and `cycle_post.py` wrap their `event_bus.emit()` calls in `try/except (ImportError, Exception): pass`. This means:
  1. If `event_bus.py` is missing → `ImportError` caught, cycle continues normally.
  2. If `event_bus.emit()` raises any exception → caught, cycle continues normally.
  3. If `.harness-port` is absent → `emit()` returns early before any network call.
  All pre-existing mechanical operations (git pull, cycle-input.json write, commit, push, iteration log, status transitions) are unaffected by the event emit calls. The emit calls are positioned at the end of each script's flow, after all critical operations complete. Structural analysis confirms additive-only behavior.

---

### TC-12: Full test suite regression

- **Result**: STRUCTURAL-PASS
- **Notes**: `tests/test_event_bus.py` exists and contains:
  - `TestEmit`: 6 tests covering emit success, port-file-missing no-op, harness-down no-op, timeout behavior, payload default, and optional cycle_number.
  - `TestDiscoverPort`: 3 tests covering direct port file, missing port file, invalid port file.
  - `TestGenerateId`: 3 tests covering 8-char hex output, determinism, and uniqueness.
  Total: 12 unit tests for `event_bus.py`. Tests use a real HTTP server fixture (`mock_server`) and temp directory patching (`patch_dirs`) — well-structured for isolation. The timeout test uses a conservative 1.5s bound (TC-10 requires < 700ms; test allows 1.5s for CI). Test suite structure is correct. Runtime pass/fail cannot be confirmed without executing `python tests/run_tests.py`.

---

## Comprehension Questions

### CQ-1: Port discovery path

**Question**: Where does `event_bus.py` look for the `.harness-port` file, and how does the harness know which directories to write it to at startup?

**Answer from code**:

`event_bus.py` uses a two-step discovery in `_discover_port()`:
1. **Direct path**: Checks `REPO_ROOT / ".squidsquad" / ".harness-port"` where `REPO_ROOT` is the root of whichever repo the script lives in (resolved from `__file__`).
2. **Parent-dir walk**: If not found, walks up to 5 parent directories of `REPO_ROOT`, checking `<parent>/.squidsquad/.harness-port` at each level.

The harness (`harness.py`) writes `.harness-port` to exactly **one location**: `SQUIDSQUAD_DIR / ".harness-port"` = the primary repo's `.squidsquad/.harness-port`. It does NOT read `.local-config` for clone paths and does NOT write per-clone port files.

**Deviation from expected answer**: The test plan expected the harness to read `.squidsquad/.local-config` for all agent clone paths and write a port file into each clone's `.squidsquad/` directory. The actual implementation does not do this. Instead, `event_bus.py` compensates with a parent-directory walk. This works for clones that are children of the primary repo but fails if clones are in unrelated directory trees.

---

### CQ-2: Silent failure contract

**Question**: List all conditions under which `event_bus.emit()` exits silently without raising an exception, and what mechanism ensures this?

**Answer from code**:

All conditions that produce silent no-ops, in order:

1. **`.harness-port` file missing** — `_discover_port()` returns `None`; the `if port is None: return` early-exit fires before any network call is attempted. This is inside `try/except`, so doubly safe.
2. **`.harness-port` contains invalid content** (non-integer) — `int(port_file.read_text(...).strip())` raises `ValueError`, which is caught by `except (ValueError, OSError): pass` inside `_discover_port()`. Falls through to parent walk, eventually returns `None`.
3. **HTTP POST fails** — `urllib.request.urlopen()` raises `urllib.error.URLError` (connection refused, DNS failure, etc.) — caught by `except Exception: pass`.
4. **Timeout exceeded** — `urlopen` raises `socket.timeout` or `urllib.error.URLError` wrapping timeout — caught by `except Exception: pass`.
5. **Non-200 HTTP response** — `urlopen` raises `urllib.error.HTTPError` — caught by `except Exception: pass`. (Note: the harness returns 200 on success and 400/422 on bad input; either way, emit catches it.)
6. **`event_bus.py` missing** — callers in `cycle_pre.py` and `cycle_post.py` use `try: from event_bus import emit ... except (ImportError, Exception): pass` — the missing module is caught before `emit()` is even called.

**Mechanism**: A single broad `try/except Exception: pass` wrapping the entire `emit()` body (lines 73–103). No re-raise anywhere in the function.

---

### CQ-3: Event emission ordering guarantee

**Question**: At what point in `cycle_pre.py` is the `cycle-start` event emitted relative to writing `cycle-input.json`?

**Answer from code**:

The `cycle-start` event is emitted **after** `cycle-input.json` is written. In `cycle_pre.py` `main()`:

1. Line 975: `output_path.write_text(json.dumps(cycle_input, ...), encoding="utf-8")` — writes `cycle-input.json`
2. Lines 982–986: `from event_bus import emit as _emit_event; _emit_event("cycle-start", role, cycle_number=cycle_number)` — emits the event

The comment on line 981 makes the intention explicit: `# Emit cycle-start event AFTER cycle-input.json is written (#4709)`.

This ordering matters because: if a harness or downstream consumer reads `cycle-input.json` upon receiving the `cycle-start` event, the file is guaranteed to exist and be populated. Emitting before the write would create a race condition where the harness receives the event but the file is not yet available. The ordering guarantee is enforced by sequential Python execution — no async race is possible since the emit is a synchronous (blocking, but short-timeout) HTTP call that happens after the file write returns.

---

## Summary

| TC | Result | Key Finding |
|----|--------|-------------|
| TC-1 | PASS | cycle-start emitted after cycle-input.json write, code comment confirms intent |
| TC-2 | PASS | cycle-end emitted after commit/push, payload includes cycle_type + summary |
| TC-3 | PASS | /events POST+GET implemented, validation, storage, and AgentState update all present |
| TC-4 | STRUCTURAL-PASS | _log_event prints flush=True immediately; format matches spec |
| TC-5 | PASS | _update_agent_from_event upserts AgentState for all three event types |
| TC-6 | PASS | deque(maxlen=1000) with threading.Lock — eviction is automatic and thread-safe |
| TC-7 | FAIL | Harness only writes ONE .harness-port file (primary repo); no per-clone writes |
| TC-8 | PASS | except Exception: pass catches all network errors including connection refused |
| TC-9 | PASS | _discover_port() returns None → early return before any HTTP attempt |
| TC-10 | PASS | _TIMEOUT = 0.5 (seconds = 500ms); all exceptions caught |
| TC-11 | STRUCTURAL-PASS | emit calls wrapped in try/except; positioned after all critical operations |
| TC-12 | STRUCTURAL-PASS | test_event_bus.py exists with 12 tests covering all key behaviors |

**Overall**: 6 PASS, 1 FAIL (TC-7), 4 STRUCTURAL-PASS, 1 FAIL.

**Critical finding**: TC-7 is a FAIL. The harness does not write `.harness-port` to each agent clone directory. `event_bus.py` compensates with a parent-directory walk, which works when clone directories are children of the primary repo but is not robust for arbitrary clone layouts. This deviation from the spec is a known design trade-off but does not match the test plan requirement.

**No regressions identified** in existing cycle mechanics. The event bus is purely additive — all emit calls are guarded by broad try/except blocks and positioned after critical operations.
