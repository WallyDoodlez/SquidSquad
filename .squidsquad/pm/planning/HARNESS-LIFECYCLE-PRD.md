# PRD: Harness Absorbs Wrapper — Full Agent Lifecycle Ownership

**Priority**: High
**Epic**: harness
**Reporter**: pm-lead
**Task**: #4966
**Research**: FEAT-PM-4966-RESEARCH.md, FEAT-PM-4966-SENTINEL-RESEARCH.md
**Context**: FEAT-PM-4966-CONTEXT.md

## Vision

The harness becomes the single owner of agent lifecycle. Wrapper scripts are eliminated. The harness spawns, monitors, restarts, and stops agents directly. All sentinel files are eliminated — zero files, API-only communication. Future: harness becomes a console app with agent view switching + web frontend relaying shells.

## Architecture Diagram

```mermaid
graph TD
    subgraph Harness ["harness.py (single supervisor process)"]
        HM[Intent Manager - per-agent state machine]
        HB[Health Monitor - direct process liveness]
        PM[Process Manager - spawn / kill / reboot]
        API[REST API]
        SF[State File - .harness-state.json]

        API -->|GET /agents/role| HM
        API -->|POST /agents/role/stop| HM
        API -->|POST /agents/role/restart| HM
        API -->|GET /agents/role/health| HB
        API -->|GET /agents/role/config| HM
        API -->|GET /status| HM

        HM -->|intent=restart| PM
        HM -->|intent=stopped| PM
        HB -->|process dead| HM
        PM -->|spawn via terminal| Launcher
        PM -->|on spawn/death| SF
    end

    subgraph Launcher ["Thin Launcher (one-shot script)"]
        L1[Start claude]
        L2[Write PID to known location]
        L3[Exit - no loop]
    end

    subgraph PreFlight ["Pre-Flight (split ownership)"]
        PF1[gh auth check - harness at startup]
        PF2[git pull + branch - cycle_pre.py per cycle]
        PF3[state bus init - cycle_pre.py]
        PF4[SQUIDSQUAD_ROLE env - harness at spawn]
    end

    subgraph Agent ["claude process (visible terminal)"]
        CyclePre[cycle_pre.py]
        Creative[Creative Work]
        CyclePost[cycle_post.py]

        CyclePre --> Creative --> CyclePost
        CyclePost -->|check intent| API
        CyclePost -->|exit 0| NormalExit[Normal - harness continues]
        CyclePost -->|exit 42| GracefulExit[Intent = stop or restart]
        CyclePost -->|exit 42| ContextPressure[Context pressure exceeded]
    end

    PM -->|detects death| HM
    HM -->|intent=running + death| PM
    Launcher -->|PID file| PM
```

## Scenario Sequence Diagrams

### 1. Startup — harness boots all agents

```mermaid
sequenceDiagram
    participant O as Operator
    participant H as Harness
    participant L as Thin Launcher (terminal)
    participant A as Agent (claude)

    O->>H: python harness.py
    H->>H: gh auth check (once)
    H->>H: Read config.md (agent list)

    loop For each configured agent
        H->>H: Set intent = running
        H->>L: Spawn via terminal (visible terminal)
        L->>A: Start claude --append-system-prompt SQUIDSQUAD_ROLE=skill
        L->>H: Write PID to known location
        H->>H: Read PID, store in .harness-state.json
        H->>H: Start monitoring PID liveness
    end

    Note over H: All agents running, harness monitoring

    loop Agent cycle (repeating)
        A->>A: cycle_pre.py (git pull, branch check)
        A->>A: Creative work
        A->>H: GET /agents/skill (check intent)
        H-->>A: {intent: "running"}
        A->>A: cycle_post.py exits 0 (continue)
    end
```

### 2. Context pressure — agent reboots

```mermaid
sequenceDiagram
    participant H as Harness
    participant A as Agent (claude)

    Note over A: Context at 72% (exceeds 70% threshold)
    A->>A: cycle_pre.py detects pressure in cycle-input.json
    A->>A: Checkpoint working state
    A->>A: Complete creative work normally
    A->>H: GET /agents/skill (check intent)
    H-->>A: {intent: "running"}
    A->>A: cycle_post.py detects context pressure
    A->>A: Exit code 42

    Note over H: Process monitor detects death
    H->>H: Check intent = running (no stop requested)
    H->>H: Exit code 42 = context pressure
    H->>H: Respawn decision: YES
    H->>H: Run pre-flight (spawn new terminal)
    H->>A: New claude process starts
    A->>A: cycle_pre.py runs, reads working-state.md
    A->>A: Resumes from checkpoint
```

### 3. Crash — unexpected agent death

```mermaid
sequenceDiagram
    participant H as Harness
    participant A as Agent (claude)

    A->>A: Creative work (mid-cycle)
    A-xA: Process dies unexpectedly

    Note over H: PID liveness check fails
    H->>H: Agent PID is dead
    H->>H: Check intent = running (no stop requested)
    H->>H: No exit code 42 (crash, not graceful)
    H->>H: Apply crash backoff
    H->>H: Respawn decision: YES
    H->>H: Update .harness-state.json
    H->>A: Spawn new claude process
    A->>A: cycle_pre.py runs
    A->>A: Reads working-state.md if exists
    A->>A: Resumes or starts fresh
```

### 4. User shutdown — graceful stop

```mermaid
sequenceDiagram
    participant O as Operator
    participant H as Harness
    participant A as Agent (claude)

    O->>H: Ctrl+C (first)
    H->>H: Set intent = stopping for all agents
    H->>H: Update .harness-state.json
    H->>O: "Graceful shutdown — waiting for agents to finish cycles..."

    Note over A: Agent is mid-cycle, continues working
    A->>A: Finishes creative work
    A->>H: GET /agents/skill (check intent)
    H-->>A: {intent: "stopping"}
    A->>A: cycle_post.py sees stopping intent
    A->>A: Exit code 42

    Note over H: Process monitor detects death
    H->>H: Check intent = stopping
    H->>H: Respawn decision: NO
    H->>H: Mark agent as stopped
    H->>H: Update .harness-state.json

    Note over H: All agents stopped
    H->>O: "All agents stopped. Harness exiting."
    H->>H: Clean up .harness-state.json
    H->>H: Exit

    Note over O: If impatient...
    O->>H: Ctrl+C (second, within 5s)
    H->>O: "WARNING: will force-kill. Press Ctrl+C again to confirm."
    O->>H: Ctrl+C (third)
    H->>H: Force kill all agent processes
    H->>H: Exit immediately
```

## What Gets Removed

| Component | Current Owner | Action |
|-----------|--------------|--------|
| start-*.sh / start-*.ps1 | Wrapper scripts | **Delete entirely** |
| .health heartbeat file | Wrapper background job | **Eliminated — harness monitors process directly** |
| .pid file | Wrapper singleton lock | **Eliminated — harness process table** |
| .claude-pid file | Wrapper | **Eliminated — harness process table** |
| .stop sentinel | harness + start_team | **Eliminated — harness in-memory intent** |
| .stop-after-cycle sentinel | harness + cycle_post | **Eliminated — replaced with GET /agents/role intent API** |
| .restart sentinel | reboot_agent | **Eliminated — harness manages restarts directly** |
| Crash retry logic | Wrapper (one retry) | **Moved to harness with configurable policy** |
| Respawn loop | Template wrapper | **Moved to harness** |
| Heartbeat background job | Wrapper | **Eliminated — harness monitors process directly** |

**Zero sentinel files in target architecture.**

## What Gets Added to Harness

### 1. Pre-Flight (split ownership)

- **Harness at startup**: `gh auth` verification (once, not per-spawn)
- **Harness at spawn**: Set `SQUIDSQUAD_ROLE` env var, spawn via terminal with thin launcher
- **cycle_pre.py per cycle**: git checkout working branch, git pull --ff-only, state bus init
- ~~Inject permissions~~ — not needed
- Singleton enforcement via harness process table (not PID file)

### 2. Process Management

- Spawn claude via terminal (platform-agnostic: wt.exe, Terminal.app, tmux, or PTY — dev discretion)
- Thin launcher writes claude PID to known location, harness reads it
- Track PIDs in `.squidsquad/.harness-state.json` (durable across harness restarts)
- Monitor process liveness directly (PID check, no heartbeat file)
- Detect death -> check intent -> act (respawn or stop)

### 3. Intent State Machine

Per-agent states: `running`, `stopping`, `restarting`, `stopped`, `crashed`

Transitions:
- `/stop` -> intent=stopping -> cycle_post queries API -> sees stopping -> exits 42 -> harness: intent=stopped
- `/restart` -> intent=restarting -> cycle_post queries API -> sees restarting -> exits 42 -> harness: respawn -> intent=running
- crash detected (process dies, intent was running) -> harness: respawn -> intent=running
- context pressure (cycle_post detects locally) -> exits 42 -> harness: respawn -> intent=running

### 4. Intent API (replaces .stop-after-cycle)

`GET /agents/{role}` already returns `intent` field. cycle_post.py calls this endpoint at cycle end:
- intent = `stopping` or `restarting` -> exit 42
- intent = `running` -> exit 0 (continue)
- API unreachable -> safe default: exit 0 (continue running)

Port discovery: default port 7373 + parent-directory walk for `.harness-port` fallback.
HTTP timeout: 5 seconds.

### 5. Health Endpoint

`GET /agents/{role}/health` returns:
- Process alive/dead (direct PID check)
- Last cycle timestamp
- Current phase (from current-state file)
- Context pressure

### 6. Config Endpoint

`GET /agents/{role}/config` exposes agent configuration sync state.

### 7. Ctrl+C Graceful Shutdown

- First Ctrl+C -> graceful stop (set intent=stopping, wait for cycle end)
- Second Ctrl+C within 5s -> warn: "Will force-kill agent. Press Ctrl+C again to confirm."
- Third Ctrl+C -> force kill process

### 8. Crash Recovery

On harness restart:
- Read `.squidsquad/.harness-state.json` for per-agent PIDs and intents
- Check which PIDs are still alive
- Resume monitoring live agents
- Respawn dead agents that had intent=running

## User Stories

**US-1: Operator starts agents via harness**
As an operator, I run `python references/scripts/harness.py` and it spawns all configured agents in visible terminals. No separate wrapper scripts needed.

**US-2: Operator stops an agent gracefully**
As an operator, I call `/agents/skill/stop` or press Ctrl+C. The harness sets intent=stopping. The agent finishes its current cycle, cycle_post queries the API, sees intent=stopping, and exits. The harness does not respawn it.

**US-3: Operator restarts an agent**
As an operator, I call `/agents/skill/restart`. The agent finishes its current cycle, exits, and the harness respawns it. cycle_pre.py handles git pull on the new session.

**US-4: Agent crashes and auto-recovers**
An agent dies unexpectedly. The harness detects process death via PID monitoring. Intent was `running` (no stop requested), so harness respawns automatically. No operator intervention.

**US-5: Context pressure triggers restart**
cycle_post.py detects context pressure exceeded (from cycle-input.json). It exits with code 42. The harness detects the exit, intent is `running`, so it respawns with fresh session.

**US-6: Operator queries agent health**
As an operator (or PM agent), I call `GET /agents/skill/health`. It returns process status, last cycle time, current phase, and context pressure — no file reading needed.

**US-7: Agent config sync**
As an operator, I call `GET /agents/skill/config` to see the agent's current configuration state.

**US-8: Graceful shutdown from terminal**
As an operator at the harness terminal, I press Ctrl+C to initiate graceful stop. Double Ctrl+C warns about force kill. Triple Ctrl+C force-kills.

**US-9: Harness crash recovery**
The harness crashes while agents are running (in visible terminals). On restart, harness reads `.harness-state.json`, checks which PIDs are alive, and resumes monitoring them.

## Acceptance Criteria

- [ ] All start-*.sh and start-*.ps1 wrapper scripts deleted from .squidsquad/ and all clones
- [ ] Template wrappers (references/templates/start-role.*) deleted or replaced with thin launcher
- [ ] compose.py boot subcommand generates thin launcher (PID-reporting one-shot) not full wrapper
- [ ] Harness spawns agents via terminal with thin launcher (visible terminals)
- [ ] Thin launcher writes claude PID to known location, harness reads it after spawn
- [ ] ALL sentinel files eliminated: .health, .pid, .claude-pid, .stop, .stop-after-cycle, .restart
- [ ] Harness tracks per-agent PIDs and intents in `.squidsquad/.harness-state.json`
- [ ] Intent state machine: running/stopping/restarting/stopped/crashed transitions correct
- [ ] cycle_post.py queries `GET /agents/{role}` for intent instead of reading .stop-after-cycle file
- [ ] cycle_post.py safe default on API failure: continue running (exit 0)
- [ ] cycle_post.py port discovery: default 7373 + parent-directory walk for .harness-port
- [ ] Harness auto-reboots on unexpected agent death (PID monitoring, intent=running)
- [ ] Harness crash recovery: reads .harness-state.json, checks PIDs, resumes monitoring
- [ ] `GET /agents/{role}/health` returns process status, last cycle, phase, context pressure
- [ ] `GET /agents/{role}/config` exposes agent config sync state
- [ ] Ctrl+C escalation: single=graceful, double=warn, triple=force-kill
- [ ] Context pressure exit (42) from cycle_post triggers harness reboot
- [ ] Pre-flight split: harness does gh auth at startup, cycle_pre.py does git pull/branch per cycle
- [ ] health_check.py updated to query harness API instead of reading .health files (or deprecated)
- [ ] boot_remote.py updated to call harness API instead of spawning terminals (or deprecated)
- [ ] start_team.py updated to call harness API instead of writing sentinels
- [ ] agent-lifecycle sub-skill updated to reflect zero-sentinel, API-based lifecycle
- [ ] self-restart sub-skill removed (harness owns restart)
- [ ] cycle-runner sub-skill updated for API intent check
- [ ] All existing tests updated or replaced for new architecture
- [ ] Upgrade path documented: stop agents, deploy, clean stale files, recompose, start via harness

## Implementation Sequence

1. Add intent API to harness (extend existing `GET /agents/{role}` — already exposes intent)
2. Add `.harness-state.json` persistence (write on spawn/death/intent change)
3. Implement harness process monitoring (PID liveness check loop, replace heartbeat)
4. Implement harness crash recovery (read state file on startup, check PIDs)
5. Add harness agent spawn via terminal + thin launcher (PID report back)
6. Implement Ctrl+C escalation in harness
7. Update cycle_post.py: replace .stop-after-cycle file check with `GET /agents/{role}` API call
8. Add port discovery helper to cycle_post.py (default 7373 + parent-dir walk)
9. Split pre-flight: move gh auth to harness startup, ensure cycle_pre handles git
10. Add `/agents/{role}/health` and `/agents/{role}/config` endpoints
11. Update health_check.py, boot_remote.py, start_team.py to use harness API
12. Delete wrapper scripts (start-*.sh, start-*.ps1) from all clones and templates
13. Update compose.py boot command to generate thin launcher
14. Update sub-skills: agent-lifecycle, self-restart, cycle-runner
15. Recompose all agents
16. Write upgrade documentation
