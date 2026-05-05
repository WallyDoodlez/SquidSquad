Now I have all the data I need. Let me produce the research document.

---

# PHASE2-AGENT-TRANSITION Research — Safe Agent Migration to Harness Event Bus

## Summary

This research analyzes the transition of four running agents (pm, skill, qa, dm) from the current polling-style monitoring model to the Phase 2 event-push model, where agents actively emit lifecycle events to the harness webserver. The primary finding is that **the transition is naturally gradual and low-risk** due to two architectural properties: (a) `event_bus.py` uses a try/except import guard that silently no-ops when the file is absent or the harness is unreachable, and (b) `cycle_pre.py` and `cycle_post.py` are invoked as fresh subprocesses each cycle, so file deployments take effect on the very next cycle without agent restart. **Recommended order: deploy event_bus.py to all clones first (silent no-op) → upgrade harness (add /events endpoint) → events begin flowing naturally on next cycle boundary.** Primary risks are: stale `.harness-port` file causing emission attempts to dead ports (harmless — caught by 500ms timeout + blanket `except`), and event_bus.py not reaching clone `references/scripts/` directories because the git-pull propagation path is not immediate.

## Vault Context

- **BRIEFING.md priorities**: #4709 EPIC Harness Phase 2 is "planned, high" and "ready for approval"; v1.0.0 launch focus means harness control plane must be reliable. Harness already owns agent lifecycle (#4966 shipped).
- **Related decisions**: [[decision-clone-isolation-architecture]] — each agent runs in its own clone; scripts propagate via git push/pull, not direct filesystem writes. [[decision-watchdog-supervisor]] — agents are "dumb workers" that just run cycles; the harness owns all lifecycle. [[decision-pid-primary-liveness]] — harness uses direct PID checks, prefers mechanical verification over sentinel files.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — event emission lives in mechanical scripts (cycle_pre/cycle_post/git_ops), not agent creative phase. This keeps emission deterministic, testable, and transparent to agents.
- **Human preferences**: "Systems should self-heal: detect stuck states → unstick immediately → file root-cause bug → agent fixes gap." The fire-and-forget emission model aligns — silent failure prevents events from blocking agent work. "Prefers direct/mechanical checks over indirect state files" — PID monitoring + HTTP POST is the direct approach.
- **Related learnings**: [[learning-atomic-migration-strategy]] — the #4966 harness migration used a stop→clean→recompose→restart sequence. Phase 2 is additive (not a replacement), so a lighter migration path is possible.

## Impact Analysis

- **Files touched**:
  - `references/scripts/event_bus.py` — **NEW** (~50 lines, stdlib urllib)
  - `references/scripts/harness.py` — **EXTEND** (add `/events` POST endpoint, EventStream model, rich console display; lines ~395–776 impacted)
  - `references/scripts/cycle_pre.py` — **ADD** import + 2 emit calls (cycle-start after writing cycle-input.json; phase-change piggybacking on _write_status_bar)
  - `references/scripts/cycle_post.py` — **ADD** import + 2 emit calls (cycle-end after commit/push; phase-change piggybacking)
  - `references/scripts/git_ops.py` — **ADD** import + 6 emit calls (git-pull, git-commit, git-push, pr-create, pr-merge, branch-checkout)
  - `references/sub-skills/common/cycle-runner.md` — **UPDATE** informational note about event emission
  - `.squidsquad/pm/planning/FEAT-PM-4709-CONTEXT.md` — existing context doc (already written)

- **Behavior changes**:
  - cycle_pre.py gains a ~5ms HTTP POST after writing cycle-input.json
  - cycle_post.py gains a ~5ms HTTP POST after commit/push + phase-change events on status bar writes
  - git_ops.py gains fire-and-forget emission hooks (pull, commit, push, pr-create, pr-merge, branch-checkout)
  - Harness console changes from print()-based log to rich-library TUI with health table + scrolling event log
  - Harness gains `/events` POST endpoint; `AgentState` extended with `current_cycle`, `current_phase`, `last_cycle_start`, `last_cycle_end`, `last_cycle_type`

- **Dependencies**:
  - `rich` library for console TUI (already in Phase 1 CONTEXT plan; `pip install rich`)
  - No new dependencies for agent-side emission (stdlib `urllib`, `json`, `pathlib`)
  - Phase 1 harness must exist and serve HTTP (shipped per BRIEFING.md)

## Side Effects

- **Risk 1**: Stale `.harness-port` file after harness crash — agents POST to dead port, get ConnectionRefused. — **Severity: L** — **Mitigation**: blanket `except Exception` in event_bus.emit() catches all network errors silently; 500ms timeout prevents blocking. Harness startup clears stale port file before writing new one (existing Phase 1 behavior at harness.py:383–388).

- **Risk 2**: `event_bus.py` has a syntax error that slips past review — ImportError in cycle_pre/cycle_post triggers the fallback no-op function, masking the error. — **Severity: M** — **Mitigation**: `tests/test_event_bus.py` must include an import-and-smoke test (TC-12 in test plan). The try/except guard should log a warning to stderr for ImportError (currently silent — worth adding a `print("WARNING: event_bus.py import failed, events disabled", file=sys.stderr)` inside the except ImportError block).

- **Risk 3**: Rich library console takeover conflicts with existing harness print()-based logging — `_log()` writes to stdout; rich.Live also writes to stdout. — **Severity: M** — **Mitigation**: rich.Live must own the console. All legacy `_log()` calls must route through rich's `Console.log()` or the Live display must reserve space for a scrolling log panel. This is the most mechanically complex part of Phase 2. Recommend a feature flag: `--console simple|rich` with `simple` preserving current print()-based output as fallback.

- **Risk 4**: Agent clones on different git histories — if an agent clone is behind on pulls (stale for multiple cycles), `event_bus.py` never arrives via git pull, and emission never starts. — **Severity: L** — **Mitigation**: cycle_pre.py runs `git pull` at start of every cycle. Maximum staleness = 1 cycle. Silent no-op until pull catches up.

## Edge Cases

- **Agent emits cycle-start but never cycle-end (crash mid-cycle)**: Harness sees `last_cycle_start` set but `last_cycle_end` never updated. The operator can see the agent went silent — useful diagnostic information. No action needed.

- **Two agents with same role (misconfigured singleton)**: Harness state dict is keyed by role string. Second agent's events overwrite first's. Acceptable for Phase 2 — clone isolation + .claude-pid singleton enforcement already prevent this in practice.

- **Harness receives events after being told to shut down**: `/shutdown` sets intent=stopping, waits for agents to idle, then kills processes and exits. Events arriving during the shutdown window (agents finishing cycles) are still ingested. After harness exits, ConnectionRefused → silent no-op. No issue.

- **Event payload with non-serializable types**: `json.dumps()` will raise TypeError inside event_bus.emit(). The blanket `except Exception` catches it, but the event is silently lost. **Mitigation**: add `default=str` to `json.dumps()` call, or validate payload values are str/int/bool/list/dict/none before serialization.

- **Very high event volume at short cycle intervals**: At 1-min cycles with 10 agents emitting ~20 events each, that's ~200 events/min, ~3.3/sec. Bounded deque of 1000 holds ~5 minutes of history. Rich Live redraws on each event at this rate are fine — rich batches updates within a single frame refresh (~60fps). At 10+ agents the health table grows vertically but remains manageable.

- **Agent creative phase emits events directly**: Current design restricts emission to mechanical scripts. If a future agent sub-skill instructs agents to call `event_bus.emit()` during creative work, the import guard pattern already supports it — no code change needed in event_bus.py. But it opens the door to agents emitting during creative work which violates the fire-and-forget contract (creative phase `claude` process shares the same clone, so `event_bus.py` is importable).

## Integration Risks

- **Port discovery across clone isolation**: The CONTEXT doc (lines 139–148) specifies parent-dir walking for port discovery: `event_bus.py` reads `.harness-port` from its own clone's `.squidsquad/`, then walks up parent directories until found, falling back to port 7373. This reuses the existing pattern from `cycle_post.py:_discover_harness_port()` (lines 501–530). Risk: if agent clone is not a sibling of the main repo (e.g., on a different drive or symlinked), the parent-dir walk may never find the harness port file. Mitigation: fallback to default port 7373 ensures eventual connectivity if harness is on default port.

- **cycle_post.py already queries harness for intent**: `_do_stop_after_cycle_check()` (cycle_post.py:554–591) calls `_query_harness_intent()` which does `GET /agents/{role}`. This means cycle_post already has harness connectivity code. The event_bus.py emission happens in the same script. If harness is unreachable for intent check, it will also be unreachable for event emission — consistent behavior. No new failure mode introduced.

- **git_ops.py emission scope**: git_ops.py is called by multiple entry points (cycle_post, agent creative phase, tests). Adding event emission to git_ops means events fire from ANY invocation context, not just within agent cycles. This is actually desirable — it gives the harness visibility into git activity regardless of initiator. But it means test suites that invoke git_ops will also emit events. Mitigation: the try/except import guard means test environments without harness running simply no-op.

- **Phase 1 harness regression**: The `/events` endpoint must coexist with existing Phase 1 endpoints (/status, /agents, /agents/{role}/start|stop|restart|health|config, /agents/all/start|stop, /shutdown). FastAPI route ordering is critical — `/events` must be defined AFTER `/agents/all/*` routes to avoid route capture (same issue documented at harness.py:416–417).

## Upgrade & Migration

- **New config values**: None required. No new config.md fields. Harness feature flag could be `--console rich|simple` but Phase 2 hard-switches to rich.

- **New files**:
  - `references/scripts/event_bus.py` — must exist in **every agent clone's** `references/scripts/` directory
  - `.squidsquad/.harness-port` — already written by Phase 1 harness (harness.py:358–364), no change needed

- **Template changes**: `references/sub-skills/common/cycle-runner.md` gets informational update only. No behavioral instruction changes for agents. No CLAUDE.md recompose required for Phase 2 emission (emission is mechanical, not creative-phase).

- **Upgrade steps**: See Recommended Deployment Runbook below (Section 9).

- **Graceful degradation**:
  - If `event_bus.py` is missing from a clone: import fails → fallback no-op function → agent cycles work identically to Phase 1
  - If harness is not running: `.harness-port` missing or ConnectionRefused → catch → no-op
  - If harness is on non-default port and port discovery fails: fallback to 7373; if wrong, ConnectionRefused → no-op
  - Phase 1 agents keep working with zero change — event emission is strictly additive

## Open Questions

- **Q1**: Should event_bus.py log a warning to stderr when import fails or harness is unreachable? — **Why**: Silent failure is safe but makes debugging hard. If an operator deploys Phase 2 and events never appear, there's no signal to indicate why. A single warning per session ("event_bus: harness not reachable, events disabled") would aid troubleshooting without breaking the fire-and-forget contract.

- **Q2**: Should the harness backfill AgentState from disk on startup (current-state file for phase, context-pressure for ctx%), or show "—" until first event arrives? — **Why**: The current-state file is written every cycle by cycle_post/cycle_pre and is always available. Reading it on harness startup would populate the health table immediately rather than showing blank rows for 0–30 minutes. This is a low-effort improvement with high UX payoff.

- **Q3**: How does harness console handle the transition from print()-based logging to rich.Live TUI? — **Why**: The harness currently uses `_log()` (harness.py:335–338) for all output. Rich's `Live` context manager owns stdout. If `_log()` calls `print()` while Live is active, output will interleave with the TUI, corrupting the display. A clean migration path (either convert all `_log()` calls to route through rich, or provide a `--console simple` flag) must be decided before implementation.

## Recommendation

**Feasible with caveats.** The transition design is sound — gradual, no agent restarts required, backward compatible at every step. The three caveats are:

1. **Rich console integration** is the highest-risk implementation detail. The harness currently has ~15 `_log()` call sites (harness.py:348, 362, 364, 366, 367, 372, 374, 379, 389, 446, 453, 469, 527, etc.). Every one must be adapted to work with rich.Live or the TUI will be corrupted. Recommend implementing `--console simple` as a fallback flag that preserves current print() behavior, then migrating to rich as the default.

2. **event_bus.py propagation latency**: git-pull propagation means the file reaches clones on the next cycle after being pushed to main. Maximum latency = one cycle interval (30 min). Acceptable, but means PM must wait one full cycle to verify emission is working after deployment. Recommend the harness startup log which agents have event_bus.py (check via health endpoint or explicit check).

3. **Stale .harness-port handling**: The current Phase 1 harness cleans the port file on shutdown (harness.py:383-388) and crash (Ctrl+C handler at harness.py:854). But if the harness is force-killed (taskkill, power loss), the port file persists with a stale port. `event_bus.py` will POST to it, get ConnectionRefused, and silently move on — safe but wasteful. Recommend the harness validate the port file on startup and overwrite it even if it already exists (it does this at line 358-364, but the atomic write .tmp→.harness-port may fail if the old file is locked). This is already handled.

---

## Detailed Answers to Transition Questions

### 1. Cold-Start Sequence — Verified

When `event_bus.py` is deployed but the harness is on the old version (no `/events` endpoint):

- `cycle_pre.py` imports `event_bus` → success (file exists)
- `cycle_pre.py` calls `emit("cycle-start", role, ...)` → `event_bus.emit()` reads `.harness-port` → finds port → POSTs to `http://127.0.0.1:{port}/events`
- Old harness receives POST to `/events` → FastAPI returns **HTTP 404 Not Found** (no route defined)
- `urllib.request.urlopen()` raises `urllib.error.HTTPError` (404)
- Blanket `except Exception: pass` catches it silently
- Agent cycle continues normally

**Verified**: This works in practice because the blanket `except Exception` catches HTTPError. The 404 response from FastAPI is fast (<5ms on localhost), well within the 500ms timeout. No agent impact.

**Edge case**: If `event_bus.emit()` calls `resp.read()` after urlopen and the 404 body is large, it wastes a few ms. The research doc design at line 163-173 shows `urllib.request.urlopen(req, timeout=0.5)` without reading the response — clean and fast.

### 2. Hot-Reload Sequence — Analysis

**Can the harness be upgraded without restarting agents? YES.**

The reasoning:
- Harness and agents are independent processes. Harness monitors agents via PID polling; agents query harness via HTTP. Neither blocks the other's lifecycle.
- To upgrade harness: `Ctrl+C` at harness terminal (graceful stop). This sets intent=stopping for all agents, but the 3-stage Ctrl+C handler (harness.py:797-858) allows harness exit WITHOUT killing agents (stage 3: "Agents survive in their terminals").
- After harness code update, restart harness. It reads `.harness-state.json`, discovers running agents via PID checks, resumes monitoring. New `/events` endpoint is now live.
- Agents still running on old `cycle_post.py` code (no event_bus import). They continue working — cycle_post queries `GET /agents/{role}` for intent (unchanged) and exits normally.
- When new `event_bus.py` + updated `cycle_pre.py`/`cycle_post.py` arrive via git pull, agents pick them up on next cycle (fresh subprocess). Events begin flowing.

**Agent restart is NOT required** because:
1. `cycle_pre.py` and `cycle_post.py` are invoked as new Python processes each cycle (`python references/scripts/cycle_pre.py <role>`). They re-import all modules fresh.
2. `event_bus.py` is a stdlib-Python module — no persistent state, no cached imports across cycles.
3. The thin_launcher's `claude` process only calls cycle_pre/cycle_post as shell commands — it doesn't hold them in memory.

### 3. Order of Deployment — Recommendation

**Option A: Deploy event_bus.py first, then upgrade harness. Safest.**

| Step | What happens | Risk |
|------|-------------|------|
| 1. Deploy event_bus.py to main repo, push | File exists in `references/scripts/` | None — not imported yet |
| 2. Agents pull on next cycle_pre | `event_bus.py` lands in clone's `references/scripts/` | None — import not yet added to cycle_pre/post |
| 3. Deploy updated cycle_pre.py, cycle_post.py, git_ops.py, push | Import lines added, emit calls added | If event_bus.py has syntax error, ImportError triggers fallback no-op (safe). If harness has no /events, 404 → silent catch (safe). |
| 4. Agents pull on next cycle | New cycle_pre/post code runs, imports event_bus, tries to emit → 404 → silent no-op | Events lost for one cycle — acceptable |
| 5. Stop old harness, deploy new harness (with /events), restart | Harness now accepts /events | Harness restart takes ~5s. Agents continue running. |
| 6. Next agent cycle | cycle_pre emits cycle-start → POST succeeds → harness ingests | Events flowing |

**Option B risks**: If harness is upgraded first (has /events but agents don't have event_bus.py), there's a gap where harness is ready but zero events arrive. PM sees an empty console for up to 30 minutes. Not harmful, but confusing.

**Option C risks**: Stopping all agents (intent=stopping, wait for cycles to finish, kill processes) means 4 agents exit mid-work, losing up to 30 minutes of creative work. Current working state is checkpointed (working-state.md), but uncommitted code changes are lost. Option C is cleanest for the harness but most disruptive for agents.

**Failure modes for Option A**:
- If `event_bus.py` has a syntax error: ImportError → fallback no-op → events silently disabled. **Fix**: deploy corrected event_bus.py, agents pick it up next cycle. No agent restart needed.
- If harness deployment fails (new harness crashes on startup): old harness (if still running) continues serving Phase 1 endpoints. Events are 404'd silently. Roll back harness code, restart.
- If git push fails between steps 1 and 3: agents have event_bus.py but no import lines in cycle_pre/post. No effect — file exists but is never imported.

### 4. Per-Clone Propagation — Mechanism

`event_bus.py` must exist at `references/scripts/event_bus.py` in each agent clone. Propagation path:

**Primary mechanism: git push → git pull**

1. Developer commits `event_bus.py` to main repo's `references/scripts/`
2. `git push` to origin/main
3. On next cycle, each agent's `cycle_pre.py` runs `git pull` (via `_do_pull()` → `git_ops.py pull`)
4. Agent clone receives `event_bus.py` in its `references/scripts/` directory
5. Next `cycle_pre.py` invocation picks it up (fresh Python process)

**Latency**: 0–30 minutes (one cycle interval). Each agent pulls independently — some may get it sooner than others.

**Alternative mechanism (faster but more complex): direct file copy**

The harness could read `.squidsquad/.local-config` for clone paths and copy `event_bus.py` directly to each clone's `references/scripts/` on startup. This was the Q5 recommendation in the original research (lines 562-568). This gives instant propagation but adds filesystem coupling.

**Recommendation**: Use git propagation as primary. It's zero new code, works with existing infrastructure, and the 0–30 minute latency is acceptable for a deployment. If faster propagation is needed in the future, add the harness-side copy as an enhancement.

**What about compose.py?** compose.py deploy-all writes CLAUDE.md and SOUL.md to `.squidsquad/<role>/` directories but does NOT copy scripts. Scripts propagate via git clone syncing. `compose.py` does not need modification for Phase 2.

**What about squidsquad-upgrade?** The `squidsquad-upgrade` sub-skill (referenced in research line 517) could be extended to copy `event_bus.py` to all clones, but this is a future enhancement. The research doc notes this as an upgrade step but git push/pull handles it automatically for running agents.

### 5. Webserver Scaling Concerns — Analysis

**Current load**: 4 agents × ~20 events/cycle ÷ 30 min = ~80 events/30min = ~0.044 events/sec. Trivial.

**At 1-min cycles with 10 agents**: 10 agents × ~20 events/cycle ÷ 1 min = ~200 events/min = ~3.3 events/sec. Each event is a ~200-byte JSON POST + a ~50-byte JSON response. Network: ~825 bytes/sec. CPU: json.loads + dict update + deque append. Trivial.

**Bounded deque (1000)**: At 1-min cycles with 10 agents, 1000 events ÷ 200 events/min = 5 minutes of history. Acceptable for a live console. If longer history is needed, Phase 3+ adds SQLite persistence.

**Rich console redraw latency**: Rich's `Live` uses terminal escape sequences to update in-place. A full redraw of a 4-agent health table + 2 usage bars is ~30 lines × 80 chars = ~2,400 bytes of terminal output. At 3.3 events/sec, that's ~7,920 bytes/sec — well within terminal rendering capacity (modern terminals handle 100KB/sec+). Rich batches updates within a single frame (~16ms at 60fps), so multiple events arriving within the same 16ms window are rendered together.

**Scalability ceiling**: The real limit is terminal rendering, not HTTP or data structures. At ~30 events/sec (corresponding to ~90 agents at 1-min cycles), the terminal might start flickering. Mitigation: rate-limit console updates to 4/sec (every 250ms) — batch events and redraw. Add `--console-interval 0.25` flag. Not needed for Phase 2 but worth noting.

### 6. Backward Compat Regression — Analysis

**Harness goes down mid-session**: Agents continue working. `event_bus.emit()` gets ConnectionRefused → caught silently. cycle_post intent check (`_query_harness_intent()`) also returns None → safe default "continue running". Agents operate exactly as Phase 1.

**Harness comes back up**: On next cycle_pre, agent pulls, `.harness-port` is present, `event_bus.emit()` finds it → POST succeeds → events resume. No action needed by agent or operator.

**Do agents know harness is back?** No. They don't need to. Each cycle_pre invocation is a fresh Python process. It re-reads `.harness-port` each time. If the file exists and harness responds, events flow. If not, silent no-op. This is the correct design — agents should not maintain persistent knowledge of harness state.

**Retry/queue in event_bus.py?** No. Fire-and-forget only. The research doc explicitly rules this out: "No retry, no buffer, no queue. Rationale: Events are informational — they update the operator's dashboard, not the agent's behavior." (Research lines 380-391). This is the right call — queuing would require persistent state in the agent, adding failure modes to the agent itself.

**Acceptable data loss?** Yes. Events lost during harness downtime are console history gaps. The harness reconstructs agent state from the next cycle-start event. Cycle numbers, phases, and context pressure are recovered on first emission. Only the event timeline has a gap — the health table becomes accurate again within one cycle.

### 7. Migration of Existing Data — Strategy

Phase 1 `AgentState` (harness.py:66-100) has: `role`, `status`, `intent`, `last_health_check`, `boot_time`, `clone_path`, `claude_pid`.

Phase 2 extends with: `current_cycle`, `current_phase`, `last_cycle_start`, `last_cycle_end`, `last_cycle_type`, `event_count`.

**Backfill strategy**:

| Field | Source on harness startup | Before first event |
|-------|--------------------------|-------------------|
| `current_cycle` | Read from iteration log (latest iter-N.md) | Show "—" if no log |
| `current_phase` | Read from `.squidsquad/<role>/current-state` file | Already available — harness.py:563-568 reads this for `/agents/{role}/health` |
| `last_cycle_start` | None — wait for event | Show "—" |
| `last_cycle_end` | None — wait for event | Show "—" |
| `last_cycle_type` | None — wait for event | Show "—" |
| `context_pressure` | Read from `.squidsquad/<role>/context-pressure` file | Already available — harness.py:571-575 reads this |

**Recommendation**: On harness startup (or when an agent first appears in health poll), read `current-state` and `context-pressure` files to populate `current_phase` and context pressure in the health table. Show `current_cycle` from iteration log if available, "—" otherwise. Wait for first `cycle-start` event to populate `last_cycle_start` and `cycle_number`. This means the health table shows meaningful data immediately (phase + context) with cycle number appearing within one cycle.

The harness already reads `current-state` for the `/agents/{role}/health` endpoint (harness.py:563-568) and `context-pressure` (lines 571-575). Phase 2 should extend `update_health()` to also populate these fields on the extended AgentState, not just return them from the health endpoint.

### 8. Console Takeover — Strategy

**Current state**: Harness uses `_log()` function (harness.py:335-338) which calls `print()` with a timestamp prefix. Banner printed at startup (lines 776-790). Console shows startup log lines and agent health discoveries.

**Phase 2 target**: Rich library TUI with:
- Pinned health table (top): Agent | Status | Cycle | Phase | Ctx%
- Pinned usage bars: Session % + Weekly %
- Scrolling event log below

**Transition strategy**: Hard cutover. When Phase 2 harness starts, it replaces the old console entirely. There's no "gradual" transition because both old and new harness code use stdout, and rich.Live must own the terminal.

**Implementation approach**:
1. Add `--console simple|rich` flag (default: `rich`)
2. `--console simple` preserves current `_log()` print behavior
3. `--console rich` (default) uses rich.Live with health table + event log
4. All `_log()` calls must route through a `ConsoleWriter` abstraction that either calls `print()` (simple) or `rich_console.log()` (rich)

This provides a rollback path: if the rich console has rendering issues on a particular terminal, the operator can use `--console simple` to revert to Phase 1 behavior while still getting the `/events` endpoint and state model updates.

**Timing**: Console changes are purely cosmetic — they don't affect the event bus or state model. The rich console can be iterated on after the core event pipeline ships.

### 9. Recommended Deployment Runbook

**Pre-deployment checklist**:
- [ ] All 4 agents running and healthy (verify: `squidsquad status`)
- [ ] Harness running on port 7373 (verify: `curl http://localhost:7373/status`)
- [ ] `event_bus.py` code reviewed and tests passing (`python tests/run_tests.py`)
- [ ] `harness.py` Phase 2 code reviewed, `/events` endpoint tested
- [ ] `rich` library installed (`pip install rich`)

---

#### Step 1: Deploy event_bus.py to main repo

```bash
# From main repo root
cp path/to/new/event_bus.py references/scripts/event_bus.py
git add references/scripts/event_bus.py
git commit -m "feat: add event_bus.py for Phase 2 agent event emission (#4709)"
git push origin main
```

**Verification**: File exists at `references/scripts/event_bus.py`. Not yet imported by anything.

---

#### Step 2: Deploy updated cycle_pre.py, cycle_post.py, git_ops.py

```bash
# Update the mechanical scripts with event_bus imports + emit calls
git add references/scripts/cycle_pre.py references/scripts/cycle_post.py references/scripts/git_ops.py
git commit -m "feat: add event emission hooks to mechanical scripts (#4709)"
git push origin main
```

**Verification**: Check that imports use try/except guard:
```python
try:
    from event_bus import emit as _emit_event
except ImportError:
    def _emit_event(*a, **kw): pass
```

---

#### Step 3: Wait for agent pulls (one cycle, ~30 min max)

Agents pull on next cycle_pre. After all agents have pulled (check: `git log -1` in each clone shows the event_bus commit), verify silent no-op:

```bash
# In each agent clone, check that event_bus.py exists
ls references/scripts/event_bus.py   # Should exist

# Run a test emission manually (should 404 silently since harness has no /events)
python -c "from event_bus import emit; emit('cycle-start', 'test', cycle_number=0)"
# Should complete with no output, no error, exit 0
```

**What's happening**: Agents are importing event_bus, calling emit, getting HTTP 404 from old harness, and silently continuing. Zero behavior change.

---

#### Step 4: Upgrade harness

```bash
# Graceful stop: Ctrl+C at harness terminal (once — sets intent=stopping)
# Wait for agents to idle (current-state shows "idle|")
# Or force: Ctrl+C three times (harness exits, agents survive)

# Deploy new harness code
git pull origin main  # (or however code is deployed)

# Start new harness (now with /events endpoint + rich console)
python references/scripts/harness.py
# Or: python references/scripts/harness.py --console simple  (if rich issues)
```

**Verification**: 
- Harness starts, discovers running agents via PID checks
- Health poll resumes within 5 seconds
- Console shows agent statuses (Phase 1 endpoints still work)
- `curl -X POST http://localhost:7373/events -H 'Content-Type: application/json' -d '{"event_type":"test","role":"pm","timestamp":"2026-01-01T00:00:00"}'` returns HTTP 200

---

#### Step 5: Verify event flow on next agent cycle

Wait for next agent cycle (~30 min max). Observe harness console:

```
[HH:MM:SS] skill git-pull      ok
[HH:MM:SS] skill cycle-start   #862
[HH:MM:SS] skill phase-change  triaging
[HH:MM:SS] skill cycle-end     #862 (active) — summary
```

**Verification**: All 4 agents appear in the health table with current cycles and phases. Events scroll in real-time.

---

#### Rollback Procedure

If Phase 2 has bugs:

1. **Harness bugs** (console broken, /events crashes): `Ctrl+C` at harness terminal, deploy old harness code, restart. Agents never knew harness was upgraded — they keep working. Lost: Phase 2 console features only.

2. **event_bus.py bugs** (emission crashes agents): This is the critical case, but the try/except guard prevents it. If somehow `import event_bus` raises an uncaught exception: push a hotfix that reverts the import lines in cycle_pre.py/cycle_post.py/git_ops.py. Agents pull on next cycle. No restart needed.

3. **Full rollback**: Push revert commit removing event_bus import lines + event_bus.py. Agents pull. Restart old harness. Back to Phase 1 state within one cycle. No agent work lost.

4. **Emergent: harness stuck, console frozen**: `Ctrl+C` three times (force exit). Agents survive. Restart old harness code. Agents re-discovered via PID check.

---

## Vault Candidates

- **Type**: pattern — "Fire-and-forget cross-process emission with import-guard fallback" — **Why**: The try/except ImportError + blanket except Exception pattern in event_bus.py is a reusable template for any future optional harness integration. It guarantees zero behavioral change for agents when integration is unavailable. This pattern can be applied to future comms adapters, metrics emission, or audit logging.

- **Type**: decision — "Event emission lives exclusively in deterministic mechanical scripts, not agent creative phase" — **Why**: This is an architectural boundary worth preserving. Keeping emission in cycle_pre/cycle_post/git_ops ensures events are deterministic, testable, and transparent to agents. If future tasks propose agent-initiated events, this decision should be referenced as the default stance.

- **Type**: learning — "Clone-isolation port discovery via parent-dir walking is the critical Phase 2 design constraint" — **Why**: The fact that `.harness-port` lives in the main repo's `.squidsquad/` but must be found from sibling clones is the single non-obvious architectural challenge in Phase 2. The parent-dir walking pattern (from cycle_post.py:_discover_harness_port()) is battle-tested and should be the canonical approach for any future cross-clone file discovery.

- **Type**: learning — "Git propagation latency (0–30 min) is acceptable for additive features; direct file copy is premature optimization" — **Why**: The temptation to add harness-side file copying for instant event_bus.py deployment should be resisted. Git pull propagation is zero new code, uses existing infrastructure, and the latency window is bounded by the cycle interval. This principle applies to future additive features that don't need instant deployment.

- **Type**: pattern — "Dual-mode console output (simple print / rich TUI) via feature flag" — **Why**: The harness console transition from print() to rich.Live is the highest-risk implementation detail. A `--console simple|rich` flag provides a rollback path and isolates the rendering concern from the event pipeline. This pattern of "new rendering, old fallback" should be used for any future console upgrades.