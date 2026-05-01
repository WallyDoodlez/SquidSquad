# FEAT-PM-4439 Context — SquidSquad Harness Phase 1

## Scope

FastAPI harness on localhost that manages agent lifecycle via HTTP API. Agents run in visible terminal windows (same as now). CLI commands curl the harness. Replaces sentinel-file reboot mechanism with real PID control.

## Locked Decisions (human decided)

- **Console app**: Harness runs as a console application in its own terminal. Shows live output: agent start/stop events, basic health info (which agents are alive, last cycle time, current phase). Ctrl+C to stop. Not a silent background daemon — it's the operator's view of the squad.
- **Agents stay visible**: All agents in visible terminal windows (not headless). User can see and type into them directly.
- **CLI language**: Python script (squidsquad.py). Cross-platform. Uses urllib to hit harness API.
- **No auth**: Localhost only, no token for Phase 1. Add auth when exposing to network (Phase 4+).
- **IPC**: HTTP on localhost (FastAPI). Same server grows into web frontend later.
- **Port**: Default 7373, writes to `.squidsquad/.harness-port` for CLI discovery.
- **Reuses existing scripts**: Harness imports boot_remote.boot_agent() and reboot_agent._kill_process() directly. No reimplementation.
- **PID tracking**: Harness owns all PIDs in-memory. When harness spawns an agent, it holds the PID directly from subprocess/wt.exe. No .pid files, no .claude-pid files, no .health file polling. Harness IS the source of truth for process state. Sentinel files (.pid, .health) are deprecated — harness replaces them entirely.
- **Phase 1 only**: No event bus, no frontend, no web terminal, no comms adapters.

## API Endpoints (Phase 1)

```
GET  /status                    # harness + all agent health
GET  /agents                    # list agents with state
POST /agents/<role>/start       # spawn agent
POST /agents/<role>/stop        # graceful stop
POST /agents/<role>/restart     # kill + respawn
POST /agents/all/start          # spawn all configured agents
POST /agents/all/stop           # stop all
POST /shutdown                  # stop all agents, then exit harness
```

## CLI Commands

```
squidsquad start          # spawn harness (if not running) + POST /agents/all/start
squidsquad stop           # POST /agents/all/stop
squidsquad stop <role>    # POST /agents/<role>/stop
squidsquad restart <role> # POST /agents/<role>/restart
squidsquad status         # GET /status
squidsquad shutdown       # POST /shutdown (stops everything including harness)
```

## Startup Sequence

1. `squidsquad start` checks if harness is running (reads .harness-port, pings /status)
2. If not running: spawns harness in new wt.exe tab
3. Harness starts FastAPI on port 7373 (or fallback free port)
4. Harness writes `.squidsquad/.harness-port`
5. CLI POSTs `/agents/all/start`
6. Harness calls `boot_remote.boot_agent()` for each configured agent
7. Harness polls .health files to confirm agents booted

## Graceful Shutdown

1. `squidsquad shutdown` → POST /shutdown
2. Harness writes .stop sentinels for all agents
3. Waits for agents to go idle (reads current-state)
4. Kills any remaining agent processes
5. Deletes .harness-port
6. Exits

## Dev Discretion

- Internal state model structure (dict? dataclass? pydantic model?)
- Background polling interval for health checks (5s recommended)
- Whether to add `/logs` endpoint in Phase 1 or defer
- Error response format
- How `squidsquad start` detects stale .harness-port from crashed harness

## Side Effect Mitigations (required)

- Existing scripts (boot_remote.py, reboot_agent.py, health_check.py) must continue working standalone as fallback
- If harness is not running, CLI should print clear error: "Harness not running. Start with: squidsquad start"
- Harness crash must not kill agents (they run in their own terminals)
- Port collision: if 7373 taken, try next free port, write actual port to discovery file

## Config

```
## Harness

- **Enabled**: yes
- **Port**: 7373
```

## Out of Scope (Phase 1)

- Event bus / agent communication sub-skill
- Web frontend / dashboard
- Web terminal (xterm.js)
- Chat room
- Comms adapters (Telegram, Discord)
- Headless agents
- Auth tokens
- Log aggregation endpoint
