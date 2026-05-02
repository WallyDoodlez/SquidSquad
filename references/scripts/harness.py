#!/usr/bin/env python3
"""SquidSquad Harness — FastAPI lifecycle manager for agent processes.

Console application that manages agent lifecycle via HTTP API. Agents run in
visible terminal windows (same as current boot_remote.py behavior). CLI commands
(squidsquad_cli.py) communicate with this harness over HTTP on localhost.

Architecture:
- Wraps existing boot_remote, reboot_agent, and health_check functions directly
- Reads sentinel files (.pid, .claude-pid, .health) for state — does NOT own PIDs
- Harness crash does NOT kill agents (they run in independent terminal windows)
- Port discovery via .squidsquad/.harness-port

Usage:
    python references/scripts/harness.py                    # Start on default port 7373
    python references/scripts/harness.py --port 8080        # Custom port
    SQUIDSQUAD_HARNESS_PORT=9090 python references/scripts/harness.py  # Env override

Phase 1 — no auth, no event bus, no frontend, no web terminal.
"""

import asyncio
import json
import os
import signal
import socket
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure script dir is importable
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
HARNESS_PORT_FILE = SQUIDSQUAD_DIR / ".harness-port"

DEFAULT_PORT = 7373
HEALTH_POLL_INTERVAL = 5  # seconds

import boot_remote
import health_check
import reboot_agent

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print(
        "ERROR: FastAPI and uvicorn are required.\n"
        "Install: pip install fastapi uvicorn",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Agent state model
# ---------------------------------------------------------------------------

class AgentState:
    """In-memory state for a single agent."""

    __slots__ = ("role", "status", "last_health_check", "boot_time", "clone_path")

    def __init__(self, role: str, clone_path: str = ""):
        self.role = role
        self.status = "unknown"  # unknown | starting | running | stopped | stalled | error
        self.last_health_check = None
        self.boot_time = None
        self.clone_path = clone_path

    def to_dict(self):
        return {
            "role": self.role,
            "status": self.status,
            "boot_time": self.boot_time,
            "last_health_check": self.last_health_check,
            "clone_path": self.clone_path,
        }


class HarnessState:
    """Global harness state — thread-safe via lock."""

    def __init__(self):
        self.agents: dict[str, AgentState] = {}
        self.start_time = time.time()
        self.port = DEFAULT_PORT
        self._lock = threading.Lock()
        self._poller_running = False
        self._poller_thread = None

    def get_agent(self, role: str) -> AgentState | None:
        with self._lock:
            return self.agents.get(role)

    def set_agent(self, role: str, state: AgentState):
        with self._lock:
            self.agents[role] = state

    def all_agents(self) -> list[dict]:
        with self._lock:
            return [a.to_dict() for a in self.agents.values()]

    def update_health(self):
        """Poll sentinel files and update agent states."""
        try:
            report = health_check.check_all_agents()
        except SystemExit:
            # health_check exits on missing .local-config
            return

        with self._lock:
            for agent_report in report.get("agents", []):
                role = agent_report["role"]
                if role not in self.agents:
                    self.agents[role] = AgentState(
                        role, agent_report.get("clone_path", "")
                    )
                agent = self.agents[role]
                agent.clone_path = agent_report.get("clone_path", "")
                agent.last_health_check = time.time()

                # Map health_check categories to harness status
                health = agent_report.get("health", "unknown")
                if health == "healthy":
                    agent.status = "running"
                elif health == "stalled":
                    agent.status = "stalled"
                elif health == "stopped":
                    agent.status = "stopped"
                elif health == "error":
                    agent.status = "error"
                else:
                    agent.status = "unknown"

    def start_poller(self):
        """Start background health polling thread."""
        if self._poller_running:
            return
        self._poller_running = True
        self._poller_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="health-poller"
        )
        self._poller_thread.start()

    def stop_poller(self):
        self._poller_running = False

    def _poll_loop(self):
        while self._poller_running:
            try:
                self.update_health()
            except Exception:
                pass  # Don't crash poller on transient errors
            time.sleep(HEALTH_POLL_INTERVAL)


# Global state
state = HarnessState()


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def _log(msg: str):
    """Print a timestamped log line to the harness console."""
    ts = time.strftime("%H:%M:%S")
    print(f"[🦑 {ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    _log(f"Harness starting on port {state.port}...")

    # Initial health poll
    state.update_health()
    state.start_poller()

    # Write port discovery file (atomic)
    try:
        tmp = HARNESS_PORT_FILE.with_suffix(".tmp")
        tmp.write_text(str(state.port), encoding="utf-8")
        tmp.replace(HARNESS_PORT_FILE)
        _log(f"Port discovery file written: {HARNESS_PORT_FILE}")
    except OSError as e:
        _log(f"WARNING: Could not write port file: {e}")

    _log("Harness ready. Ctrl+C to stop.")
    _log(f"API: http://localhost:{state.port}/status")

    # Print initial agent roster
    agents = state.all_agents()
    if agents:
        _log(f"Agents: {', '.join(a['role'] + '=' + a['status'] for a in agents)}")
    else:
        _log("No agents detected yet (health poll will discover them).")

    yield

    # Shutdown
    _log("Shutting down...")
    state.stop_poller()

    # Clean up port file (retry for Windows file locking)
    for attempt in range(3):
        try:
            if HARNESS_PORT_FILE.exists():
                HARNESS_PORT_FILE.unlink()
            break
        except OSError as e:
            _log(f"WARNING: Could not delete port file (attempt {attempt + 1}/3): {e}")
            time.sleep(0.5)

    _log("Harness stopped.")


app = FastAPI(
    title="SquidSquad Harness",
    version="1.0.0",
    lifespan=lifespan,
)


def _validate_role(role: str) -> str:
    """Validate that a role is configured. Returns the role name or raises 404."""
    configured = boot_remote._get_all_roles()
    # Also allow "pm" even though _get_all_roles excludes it
    all_known = set(configured) | {"pm"}
    if role not in all_known:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown role: {role}. Configured: {sorted(all_known)}",
        )
    return role


# -- Endpoints --
# IMPORTANT: /agents/all/* routes MUST be defined BEFORE /agents/{role}/* routes.
# FastAPI matches routes in definition order — {role} would capture "all" as a role name.

@app.get("/status")
async def get_status():
    """Harness + all agent health."""
    state.update_health()
    uptime = int(time.time() - state.start_time)
    return {
        "harness": {
            "status": "running",
            "port": state.port,
            "uptime_seconds": uptime,
            "uptime_human": f"{uptime // 3600}h {(uptime % 3600) // 60}m {uptime % 60}s",
        },
        "agents": state.all_agents(),
    }


@app.get("/agents")
async def list_agents():
    """List agents with state."""
    state.update_health()
    return {"agents": state.all_agents()}


@app.post("/agents/all/start")
async def start_all():
    """Spawn all configured agents."""
    roles = boot_remote._get_all_roles()
    _log(f"Starting all agents: {', '.join(roles)}")

    results = []
    for role in roles:
        result = boot_remote.boot_agent(role)
        results.append(result)
        status = "OK" if result["success"] else "FAIL"
        _log(f"  {role}: {result['action']} -- {status}: {result['message']}")

        if result["success"]:
            agent_state = state.get_agent(role) or AgentState(role)
            if result["action"] == "spawn":
                agent_state.status = "starting"
                agent_state.boot_time = time.time()
            state.set_agent(role, agent_state)

    return {"results": results}


@app.post("/agents/all/stop")
async def stop_all():
    """Stop all agents gracefully. Only stops agents that are currently running."""
    roles = boot_remote._get_all_roles()
    _log(f"Stopping all agents: {', '.join(roles)}")

    results = []
    for role in roles:
        clone_path = boot_remote._get_clone_path(role)

        # Skip agents that are explicitly stopped (.stop sentinel)
        if boot_remote._has_stop_sentinel(clone_path, role):
            results.append({"role": role, "action": "skip", "success": True,
                            "message": "Already stopped"})
            _log(f"  {role}: skip (already stopped)")
            continue

        # Skip agents that need booting (dead/not running)
        needs_boot, reason, _ = boot_remote._needs_boot(role)
        if needs_boot:
            results.append({"role": role, "action": "skip", "success": True,
                            "message": "Not running"})
            _log(f"  {role}: skip (not running)")
            continue

        stop_file = Path(clone_path) / ".squidsquad" / role / ".stop"
        sac_file = Path(clone_path) / ".squidsquad" / role / ".stop-after-cycle"

        try:
            stop_file.parent.mkdir(parents=True, exist_ok=True)
            stop_file.write_text("stopped via harness", encoding="utf-8")
            sac_file.write_text("stopped via harness", encoding="utf-8")
            results.append({"role": role, "action": "stop", "success": True})
            _log(f"  {role}: stop sentinel written")
        except OSError as e:
            results.append({"role": role, "action": "stop", "success": False, "error": str(e)})
            _log(f"  {role}: FAILED -- {e}")

        agent_state = state.get_agent(role) or AgentState(role)
        agent_state.status = "stopped"
        state.set_agent(role, agent_state)

    return {"results": results}


@app.get("/agents/{role}")
async def get_agent(role: str):
    """Get single agent state."""
    _validate_role(role)
    state.update_health()
    agent = state.get_agent(role)
    if agent is None:
        return {"role": role, "status": "unknown", "message": "No health data yet"}
    return agent.to_dict()


@app.post("/agents/{role}/start")
async def start_agent(role: str):
    """Spawn an agent in a visible terminal."""
    _validate_role(role)

    # Check if already running
    agent = state.get_agent(role)
    if agent and agent.status == "running":
        return JSONResponse(
            status_code=200,
            content={"role": role, "action": "skip", "message": "Already running"},
        )

    _log(f"Starting {role}...")
    result = boot_remote.boot_agent(role)
    _log(f"  {role}: {result['action']} -- {'OK' if result['success'] else 'FAIL'}: {result['message']}")

    if result["success"]:
        agent_state = state.get_agent(role) or AgentState(role)
        agent_state.status = "starting"
        agent_state.boot_time = time.time()
        state.set_agent(role, agent_state)

    status_code = 200 if result["success"] else 500
    return JSONResponse(status_code=status_code, content=result)


@app.post("/agents/{role}/stop")
async def stop_agent(role: str):
    """Graceful stop — writes .stop sentinel."""
    _validate_role(role)
    clone_path = boot_remote._get_clone_path(role)
    stop_file = Path(clone_path) / ".squidsquad" / role / ".stop"

    try:
        stop_file.parent.mkdir(parents=True, exist_ok=True)
        stop_file.write_text("stopped via harness", encoding="utf-8")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .stop: {e}")

    # Also write .stop-after-cycle for graceful exit
    sac_file = Path(clone_path) / ".squidsquad" / role / ".stop-after-cycle"
    try:
        sac_file.write_text("stopped via harness", encoding="utf-8")
    except OSError:
        pass

    _log(f"Stopped {role} (sentinel written)")

    agent_state = state.get_agent(role) or AgentState(role)
    agent_state.status = "stopped"
    state.set_agent(role, agent_state)

    return {"role": role, "action": "stop", "message": "Stop sentinel written"}


@app.post("/agents/{role}/restart")
async def restart_agent(role: str):
    """Kill and respawn an agent."""
    _validate_role(role)

    _log(f"Restarting {role}...")

    # Remove .stop sentinel if present (allow re-start)
    clone_path = boot_remote._get_clone_path(role)
    stop_file = Path(clone_path) / ".squidsquad" / role / ".stop"
    try:
        stop_file.unlink(missing_ok=True)
    except OSError:
        pass

    # Use reboot_agent's force mode for immediate restart
    rc = reboot_agent.reboot(role, timeout=30, force=True)
    success = rc == 0

    if success:
        agent_state = state.get_agent(role) or AgentState(role)
        agent_state.status = "starting"
        agent_state.boot_time = time.time()
        state.set_agent(role, agent_state)
        _log(f"  {role}: restarted")
    else:
        _log(f"  {role}: restart failed (exit code {rc})")

    return {
        "role": role,
        "action": "restart",
        "success": success,
        "message": "Restarted" if success else f"Restart failed (code {rc})",
    }


@app.post("/shutdown")
async def shutdown():
    """Stop all agents, then exit harness. Only stops agents that are running."""
    roles = boot_remote._get_all_roles()
    _log("Shutdown requested...")

    # Only stop agents that are actually running (not stopped, not dead)
    running_roles = []
    for role in roles:
        clone_path = boot_remote._get_clone_path(role)
        # Skip explicitly stopped agents
        if boot_remote._has_stop_sentinel(clone_path, role):
            _log(f"  {role}: skip (already stopped)")
            continue
        # Skip dead/not-running agents
        needs_boot, _, _ = boot_remote._needs_boot(role)
        if needs_boot:
            _log(f"  {role}: skip (not running)")
            continue
        running_roles.append(role)

    if running_roles:
        _log(f"Stopping running agents: {', '.join(running_roles)}")
        for role in running_roles:
            clone_path = boot_remote._get_clone_path(role)
            stop_file = Path(clone_path) / ".squidsquad" / role / ".stop"
            sac_file = Path(clone_path) / ".squidsquad" / role / ".stop-after-cycle"
            try:
                stop_file.parent.mkdir(parents=True, exist_ok=True)
                stop_file.write_text("stopped via harness shutdown", encoding="utf-8")
                sac_file.write_text("stopped via harness shutdown", encoding="utf-8")
            except OSError:
                pass

        # Wait briefly for running agents to reach idle
        _log("Waiting for agents to idle (max 30s)...")
        for _ in range(6):
            all_idle = True
            for role in running_roles:
                state_file = SQUIDSQUAD_DIR / role / "current-state"
                try:
                    content = state_file.read_text(encoding="utf-8").strip()
                    if not content.startswith("idle"):
                        all_idle = False
                        break
                except (OSError, FileNotFoundError):
                    pass  # No state file = not running = idle
            if all_idle:
                break
            time.sleep(5)

        # Kill remaining running agent processes
        for role in running_roles:
            clone_path = boot_remote._get_clone_path(role)
            claude_pid, alive = reboot_agent._read_claude_pid(Path(clone_path), role)
            if alive and claude_pid:
                _log(f"  Killing {role} (PID {claude_pid})...")
                reboot_agent._kill_process(claude_pid)
    else:
        _log("No running agents to stop.")

    # Clean up port file BEFORE os._exit to prevent stale file.
    # Retry on Windows where file locking can cause transient failures.
    for attempt in range(3):
        try:
            if HARNESS_PORT_FILE.exists():
                HARNESS_PORT_FILE.unlink()
                _log("Port discovery file deleted.")
            break
        except OSError as e:
            _log(f"WARNING: Could not delete port file (attempt {attempt + 1}/3): {e}")
            time.sleep(0.5)

    _log("Harness exiting.")

    # Schedule process exit after response is sent
    def _exit():
        time.sleep(1)
        os._exit(0)

    threading.Thread(target=_exit, daemon=True).start()

    return {"status": "shutting_down", "message": "All agents stopped. Harness exiting."}


# ---------------------------------------------------------------------------
# Port management
# ---------------------------------------------------------------------------

def find_free_port(default: int = DEFAULT_PORT) -> int:
    """Find an available port, preferring the default."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", default))
        s.close()
        return default
    except OSError:
        s.close()
        # Find any free port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port


def _read_config_port() -> int:
    """Read harness port from config.md or env var."""
    # Env var takes priority
    env_port = os.environ.get("SQUIDSQUAD_HARNESS_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass

    # Try config.md
    try:
        import config as cfg
        val = cfg._parse_field(cfg._read_config(), "Harness", "Port")
        if val:
            return int(val)
    except (SystemExit, ValueError, Exception):
        pass

    return DEFAULT_PORT


# ---------------------------------------------------------------------------
# Console banner
# ---------------------------------------------------------------------------

def _print_banner(port: int):
    """Print the harness startup banner."""
    print()
    print("  ▗▄▖")
    print("  ▟█ █▙")
    print(" ▐█• •█▌")
    print("███████")
    print("▐█████▌")
    print(" ▐▌▐▌▐▌")
    print()
    print("S Q U I D S Q U A D   H A R N E S S")
    print(f"Port: {port} | API: http://localhost:{port}/status")
    print(f"PID: {os.getpid()} | Ctrl+C to stop")
    print("─" * 50)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SquidSquad Harness — agent lifecycle manager")
    parser.add_argument("--port", type=int, default=None, help=f"Listen port (default: {DEFAULT_PORT})")

    args = parser.parse_args()

    # Determine port
    desired_port = args.port or _read_config_port()
    actual_port = find_free_port(desired_port)

    if actual_port != desired_port:
        print(f"Port {desired_port} in use — using {actual_port}")

    state.port = actual_port
    _print_banner(actual_port)

    # Run uvicorn
    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=actual_port,
            log_level="warning",  # Suppress uvicorn access logs (harness has its own logging)
        )
    except KeyboardInterrupt:
        print("\nHarness stopped by Ctrl+C.")
    finally:
        # Ensure port file cleanup
        try:
            HARNESS_PORT_FILE.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
