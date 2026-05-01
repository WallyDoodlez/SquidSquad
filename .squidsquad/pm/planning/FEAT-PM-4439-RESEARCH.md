# FEAT-PM-4439 Research — FastAPI Lifecycle Harness (Phase 1: visible terminals)

## Summary

The goal is a FastAPI process on localhost that owns agent lifecycle: spawn, kill,
restart. Agents still run in visible Windows Terminal windows (wt.exe). A CLI (`squidsquad
start/stop/restart`) curls the harness instead of calling scripts directly.

The current infrastructure is well-understood — `boot_remote.py`, `reboot_agent.py`, and
`start_team.py` already encapsulate all spawn/kill logic cleanly. The harness can wrap
these functions directly rather than reimplementing them. FastAPI (0.135.1) and uvicorn
(0.41.0) are already installed — no new dependencies needed for the minimal case.

**Recommendation**: Feasible. Low implementation risk. The harness is a thin HTTP wrapper
around existing Python functions. The key design decision is how the harness stays alive
(background thread vs. its own terminal window) and how the CLI discovers its port.

---

## Vault Context

- **BRIEFING.md priorities**: v1.0.0 launch focus — harness is part of the public-facing
  control plane
- **Related decisions**: none in vault yet
- **Related patterns**: none yet
- **Human preferences**: keep agents in visible terminal windows (stated in issue)
- **Related learnings**: clone-isolation architecture — all paths must be project-local

---

## 1. Current Spawn Mechanism

### How `boot_remote.py` launches agents

The spawn path for Windows is:

```python
wt new-tab --title squidsquad-{role} -d {clone_root} pwsh -NoExit -File .squidsquad/start-{role}.ps1
```

Key facts:
- `subprocess.Popen` with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` — fire-and-forget
- The harness gets back the `wt.exe` PID, which is NOT the Claude process PID. `wt.exe`
  exits almost immediately after opening the tab.
- The actual Claude PID is written by the wrapper script to `.squidsquad/{role}/.claude-pid`
  after `Start-Process claude.exe -PassThru` completes (a few seconds after boot).
- The wrapper PID is written to `.squidsquad/{role}/.pid`.

**Harness implication**: The harness can call `boot_remote._spawn_terminal()` and
`boot_remote.boot_agent()` directly — no need to reinvent spawn. The wt.exe call is
fire-and-forget; the harness cannot get a synchronous "spawned OK" confirmation. It must
poll `.health` (same as `boot_remote` does today, up to 30s).

### Boot script lookup

`boot_remote._find_boot_script(clone_root, role)` finds `.squidsquad/start-{role}.ps1` or
`.sh`. The harness calls this function — it already handles OS priority ordering.

---

## 2. PID Tracking

### Current (file-based)

| File | Written by | Content |
|------|-----------|---------|
| `.squidsquad/{role}/.pid` | wrapper (start-{role}.ps1) | PowerShell `$PID` — the wrapper process |
| `.squidsquad/{role}/.claude-pid` | wrapper (Start-Process -PassThru) | Claude subprocess PID |
| `.squidsquad/{role}/.health` | wrapper background job every 5s | Unix epoch integer |
| `.squidsquad/{role}/.booting` | `boot_remote` (pre-spawn) | boot_remote PID |

### Harness approach

In-memory state table (keyed by role):

```python
agents: dict[str, AgentState] = {
    "pm": AgentState(
        status="alive",         # spawning | alive | dead | stopped
        wrapper_pid=None,       # from .pid file (polled after spawn)
        claude_pid=None,        # from .claude-pid file
        last_heartbeat=None,    # from .health epoch
        clone_path=Path(...),
        boot_time=None,
    )
}
```

The harness polls the sentinel files on a background thread every 5s to keep in-memory
state fresh. File-based sentinels remain authoritative — the harness is an observer, not
the source of truth. This preserves backward compatibility: `health_check.py` and
`reboot_agent.py` continue to work without the harness.

**No new PID tracking mechanism needed.** The harness reads existing files.

---

## 3. Windows Terminal Specifics

### The wt.exe PID problem

`wt.exe` spawns a new terminal tab and exits quickly. The PID returned by `subprocess.Popen`
is wt.exe's PID, which dies within seconds. The actual agent process hierarchy is:

```
wt.exe (exits immediately)
  └─ Windows Terminal host process
       └─ pwsh.exe (start-pm.ps1 — the wrapper, writes .pid)
            └─ claude.exe (writes .claude-pid)
```

The harness cannot track the Claude process directly at spawn time. It must wait for the
wrapper to write `.pid` and `.claude-pid`. The existing `boot_remote` 30-second polling
loop on `.health` is the correct pattern.

### Alternative: spawn without wt.exe

For Phase 1, agents must stay in visible terminal windows (user requirement). If the harness
ever needs to spawn headlessly (Phase 2+), it can call `claude.exe` directly as a subprocess
with `stdin=subprocess.DEVNULL` and capture stdout to a log file — no wt.exe needed. But
that breaks the visible-terminal constraint, so it's out of scope for Phase 1.

### Kill path

`reboot_agent.py` kills `claude_pid` (not the wrapper). The wrapper detects the exit and
respawns if `.restart` sentinel is present. The harness should use the same kill path:
read `.claude-pid`, call `taskkill /F /PID {pid}` on Windows (or `os.kill(pid, SIGINT)` on
POSIX). This is already in `reboot_agent._kill_process()`.

---

## 4. FastAPI Setup

FastAPI 0.135.1 and uvicorn 0.41.0 are already installed. No new dependencies needed.

Minimal harness file:

```python
# references/scripts/harness.py
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="SquidSquad Harness", version="1.0.0")

@app.get("/health")
def health(): ...

@app.post("/agents/{role}/spawn")
def spawn(role: str): ...

@app.post("/agents/{role}/kill")
def kill(role: str): ...

@app.post("/agents/{role}/restart")
def restart(role: str): ...

@app.get("/agents")
def list_agents(): ...

@app.get("/agents/{role}")
def agent_status(role: str): ...
```

**stdlib fallback**: If FastAPI/uvicorn were not available, `http.server.BaseHTTPRequestHandler`
could serve the same API. This is not needed now but worth noting for future portability.

---

## 5. Port Management

### Port selection

Default port: **7373** (memorable, unlikely to be in use, not a well-known service).
Configurable via environment variable `SQUIDSQUAD_HARNESS_PORT` or a new config.md field.

Port conflict detection:

```python
import socket
def find_free_port(default=7373):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", default))
        s.close()
        return default
    except OSError:
        s.close()
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port
```

### Discovery file

The harness writes its port to `.squidsquad/.harness-port` on startup. The CLI reads this
file to know where to curl:

```
.squidsquad/.harness-port  →  "7373\n"
```

The CLI checks this file first; if missing, it knows the harness is not running.

---

## 6. Startup Sequence

### Option A — Harness in its own terminal window (recommended for Phase 1)

```
squidsquad start
  → Checks if .squidsquad/.harness-port exists and harness is alive
  → If not, spawns harness in new wt.exe tab: "squidsquad-harness"
      python references/scripts/harness.py
  → Harness starts, writes .harness-port
  → CLI polls .harness-port (up to 10s)
  → CLI POSTs /agents/all/spawn to harness
  → Harness calls boot_remote.boot_agent() for each role
```

Pros: harness is visible, easy to debug, consistent with existing agent model.
Cons: one more terminal window.

### Option B — Harness as background thread in CLI process

```
squidsquad start
  → CLI starts uvicorn in background daemon thread
  → CLI calls /agents/all/spawn internally (same process)
  → CLI exits — background daemon thread dies with it
```

Pros: no extra terminal window.
Cons: harness dies when CLI exits; other CLI calls (restart, stop) cannot reach it.
**This option does not work** — the harness must be a persistent process.

### Option C — Harness as Windows service / detached process

Could use `subprocess.Popen` with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` to spawn
the harness as a headless background process. No terminal window. CLI finds it via
`.harness-port`.

Pros: clean, no extra window.
Cons: harder to debug; no visible output; more complex lifecycle.

**Recommendation**: Option A for Phase 1 (visible terminal, consistent with existing model).
Option C can be a Phase 2 upgrade.

---

## 7. Graceful Shutdown

`squidsquad stop`:

1. CLI reads `.squidsquad/.harness-port`
2. CLI POSTs `/shutdown` to harness
3. Harness calls `start_team.cmd_stop(all_roles)` — writes `.stop` sentinels
4. Harness deletes `.squidsquad/.harness-port`
5. Harness calls `os._exit(0)` (FastAPI background shutdown)

For stopping individual agents: `squidsquad stop --role skill` → POST `/agents/skill/stop`
→ harness writes `.squidsquad/skill/.stop`.

The harness does NOT wait for agents to finish their cycles before exiting (that's
`start_team.cmd_reboot` behavior with `.stop-after-cycle`). Graceful restart uses the
existing sentinel mechanism.

---

## 8. Integration With Existing Scripts

| Script | Phase 1 role | Change |
|--------|-------------|--------|
| `boot_remote.py` | Core library, called by harness | No change — harness imports and calls its functions directly |
| `reboot_agent.py` | Core library for kill logic | No change — harness imports `_kill_process()` |
| `start_team.py` | Thin wrapper over boot_remote | No change — still works standalone; harness duplicates its logic internally |
| `health_check.py` | Standalone, still works | No change — harness calls it for `/agents` status endpoint |
| `start-squad.ps1` | Calls `boot_remote.py --all` | Remains as fallback for users without harness |
| `squidsquad` CLI | NEW — thin curl wrapper | New script; replaces direct script calls for users |

**Key principle**: All existing scripts continue to work unchanged. The harness is additive.
Users who run `python references/scripts/boot_remote.py --all` directly still get the
same behavior. The harness is an optional control plane, not a required dependency.

---

## 9. New Config.md Fields

Two new optional fields under a new section:

```markdown
## Harness

- **Enabled**: yes
- **Port**: 7373
```

- `Enabled`: whether `squidsquad start` launches the harness or falls back to direct
  `boot_remote.py` calls. Default `yes` when harness.py exists.
- `Port`: default listen port. Overridden by `SQUIDSQUAD_HARNESS_PORT` env var.

The `config.py` script reads these via existing `get` command after adding parsing support.

---

## Impact Analysis

- **Files touched**:
  - `references/scripts/harness.py` — NEW (FastAPI app)
  - `references/scripts/squidsquad_cli.py` or `squidsquad` script — NEW (CLI wrapper)
  - `.squidsquad/config.md` — add `## Harness` section
  - `references/scripts/config.py` — add harness field parsing
  - `.squidsquad/.harness-port` — runtime file, gitignored
- **Behavior changes**: None for existing scripts. New entry point for users who adopt the CLI.
- **Dependencies**: None new (FastAPI + uvicorn already installed).

---

## Side Effects

- **Risk 1**: Harness port collision if two projects run simultaneously. Severity: **Low**.
  Mitigation: per-project `.harness-port` file + auto-port fallback.
- **Risk 2**: Harness terminal window adds noise when `squidsquad start` is run.
  Severity: **Low**. Mitigation: harness tab title is `squidsquad-harness`, easily
  identifiable; Option C (headless) available for Phase 2.
- **Risk 3**: CLI uses `.squidsquad/.harness-port` discovery — if harness crashes and port
  file is stale, CLI gets connection refused. Severity: **Low**. Mitigation: CLI catches
  `ConnectionRefusedError` and prints "harness not running, use squidsquad start".

---

## Edge Cases

- **Harness not running, CLI called**: CLI reads `.harness-port`, GET fails → print helpful
  error "harness not running — run `squidsquad start` first."
- **Harness already running, `squidsquad start` called again**: CLI checks harness health
  via `GET /health` before spawning a new one. If alive, just spawn agents.
- **Partial spawn failure**: Harness returns per-agent status. CLI prints which agents
  failed and which succeeded.
- **Role not in config**: Harness validates role against `boot_remote._get_all_roles()`.
  Returns 404 for unknown roles.
- **Windows-only**: harness.py must be cross-platform (wt.exe paths are inside
  `boot_remote._spawn_windows()` already — harness just calls the existing function).

---

## Integration Risks

- `start_team.py` has its own `cmd_stop` and `cmd_reboot` — if both harness and direct
  script calls are used simultaneously, sentinel files remain the arbitration layer.
  The `.booting` sentinel already prevents double-spawn races.

---

## Upgrade & Migration

- **New config values**: `Harness > Enabled: yes`, `Harness > Port: 7373`
- **New files**: `references/scripts/harness.py`, CLI entry point
- **Template changes**: None — harness is infrastructure, not agent instructions
- **Upgrade steps**: `squidsquad-upgrade` should add the `## Harness` section to config.md
  if missing. Existing installs without the section fall back to direct `boot_remote.py`.
- **Graceful degradation**: If harness.py is missing or FastAPI is not installed, the CLI
  can fall back to calling `boot_remote.py --all` directly (same behavior as today).

---

## Capability Gaps

No capability gaps — all required Python packages are present. No new LLM capabilities
needed.

---

## Open Questions

- **Q1**: Should the harness terminal window be visible (Option A) or headless/detached
  (Option C) in Phase 1? Why it matters: user experience — visible is easier to debug,
  headless is cleaner.
- **Q2**: Should `squidsquad start` be a Python script (`squidsquad_cli.py`) or a PS1/shell
  script? Why it matters: PS1 integrates with existing start-squad.ps1 pattern; Python is
  cross-platform.
- **Q3**: Should the harness authenticate requests (e.g., require a token from
  `.squidsquad/.harness-token`)? Why it matters: localhost only in Phase 1, so auth adds
  complexity for minimal security benefit. Relevant for Phase 2+ if harness is exposed.
- **Q4**: Should `GET /agents` call `health_check.py` as a subprocess, or import it as a
  library? Why it matters: subprocess is isolated but slower; import is faster but ties
  harness to health_check's internals.

---

## Recommendation

Straightforward. The harness is ~150 lines of FastAPI wrapping existing functions.
Implementation risk is low because:
1. FastAPI + uvicorn already installed.
2. All spawn/kill/health logic already exists in boot_remote, reboot_agent, health_check.
3. The harness adds no new sentinel files — it reads existing ones.
4. Existing scripts remain fully functional as fallbacks.

Suggest resolving Q1 (visible vs. headless terminal) and Q2 (CLI language) before
implementation begins.

---

## Vault Candidates

- **Type**: pattern — "HTTP wrapper over file-based control plane" — why: the pattern of
  keeping file sentinels as source of truth while adding HTTP as a convenience layer is
  reusable for other SquidSquad infrastructure.
- **Type**: decision — "FastAPI harness is additive, not a dependency gate" — why: the
  explicit decision to keep existing scripts working unchanged is worth preserving so
  future contributors don't accidentally break the fallback path.

---

*Research by PM subagent — 2026-04-28*
