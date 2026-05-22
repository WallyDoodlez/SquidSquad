# RESEARCH-9874 — Harness Internal Architecture Review: Map Layers, Surface Wedge Causes

**Issue**: #9874
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## 1. Problem Statement

`references/scripts/harness.py` is a single-file FastAPI/uvicorn process that mixes async HTTP
handler code with sync I/O, subprocess calls, threading.Lock acquisitions, and direct file writes
— all within the asyncio event loop. From cycles 1535–1539 the HTTP layer intermittently stalls 5
seconds or longer: a single `curl` returns HTTP 000 while an immediate retry succeeds in ~2ms.
This pattern is a classic event-loop blockage: the loop accepts the connection, queues the
handler coroutine, but cannot resume it (or cannot accept the next connection) because the loop is
frozen executing synchronous work.

**Prior fixes**:
- **#9242**: diagnostic escape hatch `--no-auto-start`; role validation at event ingestion
- **#9481 / PR #9551**: wrapped `update_health()` calls in `asyncio.to_thread` on specific
  endpoints (`/status`, `/agents`) — this moved the Windows `tasklist` subprocess out of the loop
- **#9562 / PR #9568**: set `WindowsSelectorEventLoopPolicy` at `main()` to eliminate
  `ProactorEventLoop._call_connection_lost` crashes

Memory rule `feedback_proactor_loop_two_bugs` confirms both #9481 and #9562 addressed distinct
causes. Stalls persist after both fixes, indicating a third (or more) hazard class.

**Applying `feedback_minimal_repro_over_symptom_match`**: this document maps mechanisms with
file:line citations. It does not assert a root cause without citing a mechanism — each hazard below
names the specific call site that blocks the loop, not a pattern-match to the symptom.

---

## 2. Today's Actual Layering

### 2.1 Thread inventory at runtime

| Thread name          | Started by              | Type                     | Lives in loop? |
|----------------------|-------------------------|--------------------------|----------------|
| main                 | `main()` — OS entry     | signal-handler wait loop | No             |
| uvicorn              | `threading.Thread`      | asyncio event loop host  | Yes (owns it)  |
| health-poller        | `HarnessState.start_poller()` | `threading.Thread` daemon | No (sync)  |
| event-timeout-scanner | `EventLifecycleManager.start_timeout_scanner()` | daemon | No (sync) |
| activity-detector    | `ExternalActivityDetector.start()` | daemon | No (sync) |
| deferred-init        | lifespan `_deferred_init` | one-shot daemon           | No (sync) |
| shutdown             | `POST /shutdown`         | one-shot daemon           | No (sync) |
| merge-{N}            | `POST /merge`            | one-shot daemon per PR    | No (sync) |

The asyncio event loop runs inside `uvicorn` thread only. All other threads are standard OS
threads that share module-level objects (`state`, `event_lifecycle`, `event_stream`,
`activity_detector`).

### 2.2 Shared mutable state and lock discipline

| Object               | Module-level | Lock                | Who writes it |
|----------------------|-------------|---------------------|---------------|
| `state` (HarnessState) | Yes       | `state._lock` (threading.Lock) | endpoints (async), health-poller (sync), deferred-init (sync), shutdown thread (sync) |
| `state.agents` dict  | Yes          | same `state._lock`  | same writers  |
| `event_stream` (EventStream) | Yes  | `EventStream._lock` (threading.Lock) | `receive_event`, EventLifecycleManager._persist |
| `event_lifecycle` (EventLifecycleManager) | Yes | `EventLifecycleManager._lock` (threading.Lock) | same + timeout-scanner |
| `activity_detector._emitted_issues` | Yes | `_emitted_lock` (threading.Lock) | activity-detector thread |
| `_NO_AUTO_START`     | Yes         | None (write-once at startup) | `main()` only |

Lock discipline is consistent within each object. The hazards arise from calling methods on these
objects inside `async def` handlers — which is fine as long as the methods return quickly. The
problem is when the methods also perform slow I/O while holding a lock (see §3).

### 2.3 Layer map vs. human's hypothesized 4-layer architecture

```
Human's ideal:          Actual today (harness.py):
┌─────────────────┐     ┌──────────────────────────────────────────────────────┐
│ async API layer │     │ async def handlers — FastAPI/uvicorn                  │
│ (FastAPI)       │     │   • Some: pure dict read → JSON (safe)                │
│                 │     │   • Some: acquire threading.Lock inside async handler  │
│                 │     │   • Some: direct sync file I/O inside async handler   │
│                 │     │   • Some: subprocess.run inside async handler         │
│                 │     │   • Some: wrapped with await asyncio.to_thread(...)   │
├─────────────────┤     ├──────────────────────────────────────────────────────┤
│ queue (broker)  │     │ *** ABSENT ***                                        │
│                 │     │ No queue between API layer and BL.                    │
│                 │     │ Handlers call BL directly and synchronously.          │
├─────────────────┤     ├──────────────────────────────────────────────────────┤
│ sync BL layer   │     │ HarnessState methods (update_health, save_state,      │
│                 │     │   load_state) and EventLifecycleManager methods —      │
│                 │     │   all sync. BUT they are called directly from async   │
│                 │     │   handlers in several places (see §3).                │
├─────────────────┤     ├──────────────────────────────────────────────────────┤
│ sync data-      │     │ .harness-state.json and .event-state.json writes via  │
│ persistence     │     │   .write_text() + os.replace. Sync. Woven throughout. │
│ layer           │     │   Some wrapped in to_thread (after #9481), many not. │
└─────────────────┘     └──────────────────────────────────────────────────────┘
```

The queue layer does not exist. Business logic and persistence are inlined directly into async
handlers. The #9481 fix applied `to_thread` to `save_state` on specific endpoints but not
uniformly. Several hazard classes remain.

---

## 3. Identified Hazards

### H1 — Direct sync file reads in `async def get_agent_health` (harness.py:1351–1362)

```
harness.py:1353  result["current_phase"] = state_file.read_text(encoding="utf-8").strip()
harness.py:1360  result["context_pressure"] = int(ctx_file.read_text(encoding="utf-8").strip())
```

`GET /agents/{role}/health` performs two synchronous `Path.read_text()` calls directly on the
asyncio event loop. These read files from agent clone directories — potentially remote mounts, slow
network paths, or Windows NTFS under antivirus scan. There is no `await asyncio.to_thread` wrapper.
If either file is slow (network share, AV intercept), the event loop freezes for the duration.

**Mechanism**: asyncio is cooperative. `state_file.read_text()` is a blocking syscall. While it
blocks, the loop cannot process any other I/O events, including new incoming connections. This
produces the exact HTTP 000 + immediate-retry-succeeds pattern.

**Reproduction condition**: `GET /agents/{role}/health` called while clone directory is on a slow
or congested path. Frequency increases when health probe polling is high-rate.

### H2 — `_validate_role()` calls `boot_remote._get_all_roles()` synchronously on every request (harness.py:1128–1137)

```
harness.py:1129  configured = boot_remote._get_all_roles()
```

`_validate_role` is a sync function called directly from async handlers
(`start_agent`, `get_agent`, `get_agent_health`, `get_agent_config`, `stop_agent`, `restart_agent`,
`get_in_flight_events`, `get_events_for_role`). `_get_all_roles()` reads `.squidsquad/config.md` and
parses it synchronously. This is a file read on the hot request path, not wrapped in `to_thread`,
blocking the event loop on every single request to a role-scoped endpoint.

**Mechanism**: same as H1 — blocking file I/O blocks the loop. Every `GET /agents/{role}` and
`POST /agents/{role}/stop` etc. reads the config file synchronously. Under any file contention
(another thread writing config, AV, or slow disk), the loop freezes.

**Reproduction condition**: high request rate to role-scoped endpoints during disk activity.

### H3 — `GET /human/queue` calls `subprocess.run(["gh", ...])` directly on the event loop (harness.py:1852–1885)

```
harness.py:1864  raw = _gh_list_pending_human_issues()
# which calls:
harness.py:1797  result = subprocess.run(["gh", "issue", "list", ...], ...)
```

`_gh_list_pending_human_issues()` is a sync function that makes two `subprocess.run` calls to the
`gh` CLI (one per status label). `gh` makes HTTPS requests to GitHub — latency is 200–2000ms
under normal conditions, and up to 10–30s on rate-limiting or network degradation. There is no
`await asyncio.to_thread` wrapper. The entire `GET /human/queue` handler blocks the event loop
for the duration of both `gh` calls.

**Mechanism**: `subprocess.run` is a blocking syscall. Two of them, back to back, on the event
loop. Any request arriving during these calls cannot be accepted. Worst case: two `gh` calls ×
potential 10s each = 20s stall. This is the highest-impact single hazard in the file.

**Reproduction condition**: any call to `GET /human/queue` while GitHub is slow, rate-limited, or
the network has elevated latency. The TUI or any monitoring client that polls this endpoint
triggers the stall on every cycle.

### H4 — `POST /events/{event_id}/complete` calls `_execute_transition` and `_execute_comment` synchronously (harness.py:1729–1746)

```
harness.py:1732  _execute_transition(transition)    # calls subprocess.run(tracker.py)
harness.py:1738  _execute_comment(comment)           # calls subprocess.run(tracker.py)
# inside helpers:
harness.py:2108  result = subprocess.run([sys.executable, "tracker.py", "transition", ...], timeout=30)
harness.py:2127  result = subprocess.run([sys.executable, "tracker.py", "comment", ...], timeout=30)
```

Both helpers run `tracker.py` as a subprocess with `timeout=30`. The `complete_event` async handler
calls these synchronously, blocking the event loop for up to 30 seconds per transition/comment.
With multiple transitions and comments in a single completion payload, the total block can exceed
a minute.

**Mechanism**: same subprocess.run blocking pattern. 30s timeout means the absolute worst-case
stall is bounded, but 30s is catastrophic for the event loop.

**Reproduction condition**: any agent that calls `POST /events/{event_id}/complete` with
`transitions` or `comments` payloads. This endpoint is Phase 4 plumbing (no current callers), but
the code is live and accepting requests.

### H5 — `POST /agents/{role}/restart` calls `state_file.read_text()` and `reboot_agent._kill_process()` on the event loop (harness.py:1964–1981)

```
harness.py:1967  current_state = state_file.read_text(encoding="utf-8").strip()
harness.py:1978  reboot_agent._kill_process(claude_pid)
```

The `restart_agent` handler reads the agent's `current-state` file (sync file I/O, same H1 risk)
and conditionally calls `_kill_process()`. The kill itself is OS-level and fast, but the file read
is blocking I/O on the event loop. Additionally, `await asyncio.to_thread(state.save_state)` is
called at line 1953 — this part is correctly wrapped — but the `read_text` at 1967 is not.

**Mechanism**: blocking file I/O on the async handler. The save_state path was fixed by #9481 but
the current-state read was missed.

**Reproduction condition**: `POST /agents/{role}/restart` while the clone's filesystem is slow.

### H6 — `EventLifecycleManager._persist()` acquires `self._lock` then calls `EventStream.get_recent()` which acquires `EventStream._lock` (harness.py:665–686)

```
harness.py:672  with self._lock:
harness.py:673      recent_events = list(self._stream.get_recent(200))   # acquires EventStream._lock
harness.py:683      tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
harness.py:684      tmp.replace(EVENT_STATE_FILE)
```

`_persist()` holds `self._lock` while calling `get_recent(200)` (which acquires `EventStream._lock`)
and while performing the file write. This lock chain is called from `event_lifecycle.append()` on
the hot `POST /events` path. If the event state file write is slow (large file, slow disk, Windows
AV), the `EventLifecycleManager._lock` is held for the entire write duration.

Meanwhile, the `receive_event` handler (line 1512) calls `event_lifecycle.append(body)` which calls
`_persist()` — this is in the async handler body, WITHOUT `await asyncio.to_thread`. So the entire
file write (including the lock hold) happens synchronously on the event loop.

**Mechanism**: sync file I/O inside async handler, with a threading.Lock held during the I/O. This
is the hottest path in the entire harness — `POST /events` is called by every agent on every
mechanical script invocation (cycle-start, cycle-end, git-commit, etc.). A slow `.event-state.json`
write blocks the loop on every event emission.

**Reproduction condition**: `.event-state.json` grows large (up to 200 events × full JSON payloads),
Windows AV scanning the file on write, or any disk contention. Frequency: every event emitted by
any agent.

### H7 — `ExternalActivityDetector._check_for_changes()` calls `subprocess.run(["gh", ...])` but runs in a daemon thread (NOT on the event loop) (harness.py:2511–2526)

```
harness.py:2511  result = subprocess.run(["gh", "issue", "list", ...])
```

This is in `_check_for_changes()` which runs in the `activity-detector` daemon thread (not the
event loop). The `subprocess.run` blocking call is correctly isolated. However: this thread calls
`_emit_event()` (line 2558), which calls `event_lifecycle.append()`, which calls `_persist()` —
the same file-write path as H6 — but from a non-async context. The `_persist()` call in a
background thread is fine for thread safety (locks are threading.Locks), but it contends with the
event loop thread which is also calling `_persist()` on every `POST /events`. Lock contention
under high event volume could cause the event loop's `_persist()` to wait for the background
thread's `_persist()` to finish. **This is not a direct loop-block but is a lock-contention
amplifier for H6.**

### H8 — `HarnessState.update_health()` contains `health_check.check_agent_health()` with no subprocess isolation guarantee (harness.py:256–267)

```
harness.py:256  health_report = health_check.check_agent_health(role, clone_path, interval_minutes=30)
```

This is in `update_health()`, which runs in the `health-poller` daemon thread. #9481 fixed the
loop-blocking case by removing the inline call from async handlers. However, `check_agent_health()`
is legacy fallback code and its implementation in `health_check.py` is not examined in this
document. If `health_check.check_agent_health` internally calls `subprocess.run` (to run
`health_check.py`), it would run on the poller thread — correct and safe. Confirm during
implementation review. **Flagged as conditional hazard pending health_check.py review.**

---

## 4. Options

### Option A — Minimal: wrap remaining sync-on-async hazards in `to_thread`

Apply `await asyncio.to_thread(...)` to each identified sync call site in async handlers,
following the #9481 pattern:

- H1: wrap `state_file.read_text()` calls in `get_agent_health` in `to_thread`
- H2: cache `_get_all_roles()` result at startup and refresh on SIGHUP/periodic interval, OR wrap
  `_validate_role()` call in `to_thread` (the latter requires making it async)
- H3: wrap `_gh_list_pending_human_issues()` call in `get_human_queue` in `to_thread`
- H4: wrap `_execute_transition` and `_execute_comment` calls in `complete_event` in `to_thread`
- H5: wrap `state_file.read_text()` in `restart_agent` in `to_thread`
- H6: move `event_lifecycle.append()` call in `receive_event` to `await asyncio.to_thread(...)`

**Cost**: Low per-hazard. Each is a targeted 1–2 line change. No architecture change. Follows
existing #9481 precedent. All hazards become isolated from the event loop.

**Benefit**: Eliminates all identified sync-on-async crossings. The event loop remains responsive
during any slow I/O or subprocess call. Least blast radius.

**Risk**: Correctness — `to_thread` calls run on the asyncio thread pool. State mutations must be
thread-safe (they are, via threading.Lock). Each wrap must be reviewed for lock ordering to avoid
new contention.

**Pre-flip readiness**: High. Each fix is surgical and independently testable. Fixes can be
shipped incrementally, one endpoint at a time, with a minimal repro confirming the fix.

### Option B — Medium: asyncio.Queue between API layer and BL worker thread

Introduce an `asyncio.Queue` inside each async handler for mutation-heavy operations: handlers
enqueue a task dict, a single worker coroutine dequeues and runs the BL synchronously. Handlers
await the queue put (non-blocking) and return a 202 Accepted or poll for completion.

**Cost**: Medium. Requires redesigning the mutation endpoints (stop, restart, events POST, merge)
to be async-first with a response model. Read endpoints (GET /status, GET /agents) remain
unchanged.

**Benefit**: Cleanly separates the API layer from BL execution. Provides natural backpressure.
Enables future batching and prioritization.

**Risk**: 202 Accepted semantics are a behavior change — current callers (agents, CLI) expect
synchronous responses. Significant test surface change.

**Pre-flip readiness**: Medium. Substantial change, but the queue is entirely internal — callers
don't know about it if response semantics are preserved via polling or callback.

### Option C — Full: redesign per human's 4-layer hypothesis

Separate process boundaries:
- Layer 1: async FastAPI process (thin HTTP adapter only — no BL, no state)
- Layer 2: queue (asyncio.Queue or Redis/SQLite-backed)
- Layer 3: sync BL process (state machine, intent handling, lifecycle) — pure Python, no async
- Layer 4: sync persistence process (file writes in dedicated thread or process)

**Cost**: High. Requires restructuring all state management, IPC protocol design, and process
management. Weeks of work.

**Benefit**: Architecturally correct. Wedge becomes structurally impossible — blocking I/O in
Layer 3/4 cannot affect Layer 1's accept() loop by design.

**Risk**: Very high blast radius. Complete rewrite of the harness. Pre-flip is blocked for
weeks.

**Pre-flip readiness**: Low.

---

## 5. Recommended Option + Reasoning

**Recommended: Option A**, with H3 and H6 prioritized first.

**H3** (`GET /human/queue` → `subprocess.run` to GitHub) is the highest-impact hazard: two
blocking `gh` calls with up to 10–30s latency each, directly on the event loop, called on every
TUI refresh. A single `await asyncio.to_thread(_gh_list_pending_human_issues)` at `harness.py:1864`
eliminates it.

**H6** (`POST /events` → `_persist()` sync file write on the hot path) affects every event
emission from every agent. Wrapping `event_lifecycle.append(body)` in `to_thread` at
`harness.py:1512` isolates the file write from the loop.

H1, H2, H5 are secondary — lower frequency endpoints. H4 is Phase 4 plumbing with no current
callers. H7 and H8 are thread-isolated already (confirm H8 pending health_check.py review).

Option B is the right long-term architecture but is not pre-flip work. Option C is post-v1.

**Applying `feedback_minimal_repro_over_symptom_match`**: before each fix, a minimal repro should
be run to confirm the stall disappears after the fix. Suggested probe for H3: measure `curl` latency
on `GET /human/queue` while a concurrent `gh issue list` runs at 5s latency (using `tc netem` or
equivalent). Confirm that after the `to_thread` wrap, the concurrent curl returns in <50ms.

---

## 6. Open Questions for PM/Human

**Q1 — Scope cap: incremental vs. full restructure**
Option A fixes the symptoms incrementally. Each fix can ship independently. The alternative (Option
C) is weeks away and blocks the flip. Is the human comfortable shipping Option A hazard-by-hazard,
or is there a minimum architectural separation required before the flip?

**Q2 — H6 behavior change: to_thread on receive_event**
Wrapping `event_lifecycle.append(body)` in `to_thread` means the disk write happens asynchronously
after the HTTP response is already returned to the caller. The caller currently sees the event
persisted before the 200 OK. After the fix, persistence is eventually consistent. Is this
acceptable for the event-driven flip's reliability contract?

**Q3 — H3 polling frequency: is /human/queue called by TUI/monitoring?**
If the TUI polls `/human/queue` every N seconds, it is the primary trigger for H3 stalls. Confirm
polling frequency and whether the TUI also polls during high-activity windows (many agents active
+ many events flowing). This determines the practical stall frequency and helps prioritize H3 vs
H6.

**Q4 — H8 confirmation: does health_check.check_agent_health call subprocess?**
H8 is currently in the health-poller daemon thread (correct), but if `health_check.py`'s
`check_agent_health()` calls back into subprocess or disk I/O in a way that conflicts with lock
discipline, it warrants a separate fix. Reading `health_check.py` is a 10-minute task — recommend
confirming during implementation.

---

## 7. Out of Scope

- **`event_poll.py` hang on harness loss** — covered by RESEARCH-9742 (#9742).
- **Cursor re-anchor race** — covered by RESEARCH-9740 (#9740).
- **EventLifecycleManager dispatch/ack dormancy** — covered by AUDIT-A findings, tracked separately.
- **Option B/C architecture redesign** — post-v1, not pre-flip readiness work.
- **health_check.py internals** — scoped to harness.py in this task; health_check.py is adjacent.
- **boot_remote.py, reboot_agent.py internals** — these are called from async handlers but the
  fix is always `to_thread` at the call site in harness.py, not changes to the callee.
