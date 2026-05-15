#!/usr/bin/env python3
"""SquidSquad CLI — thin client for the harness HTTP API.

Cross-platform Python CLI that communicates with the SquidSquad harness.
Discovers the harness port via .squidsquad/.harness-port.

Usage:
    python squidsquad_cli.py start              # Boot harness + all agents
    python squidsquad_cli.py stop               # Stop all agents
    python squidsquad_cli.py stop <role>         # Stop one agent
    python squidsquad_cli.py restart <role>      # Restart one agent
    python squidsquad_cli.py status             # Show harness + agent health
    python squidsquad_cli.py shutdown           # Stop all agents + exit harness

Exit codes:
    0 — success
    1 — error (harness not running, API failure)
    2 — usage error
"""

import io
import json
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Ensure stdout can handle Unicode emoji on Windows (cp1252 can't encode them)
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
HARNESS_PORT_FILE = SQUIDSQUAD_DIR / ".harness-port"
HARNESS_SCRIPT = SCRIPT_DIR / "harness.py"

HARNESS_STARTUP_TIMEOUT = 15  # seconds to wait for harness to start
API_TIMEOUT = 10  # seconds for individual API calls


# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

def _read_port() -> int | None:
    """Read the harness port from the discovery file. Returns None if missing."""
    if not HARNESS_PORT_FILE.exists():
        return None
    try:
        content = HARNESS_PORT_FILE.read_text(encoding="utf-8").strip()
        return int(content) if content else None
    except (ValueError, OSError):
        return None


def _harness_alive(port: int) -> bool:
    """Ping the harness /status endpoint. Returns True if responsive."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _discover_harness() -> int | None:
    """Discover a running harness. Returns port or None.

    Reads .harness-port and pings /status. If the port file exists but the
    harness doesn't respond (stale crash remnant), returns None.
    """
    port = _read_port()
    if port is None:
        return None
    if _harness_alive(port):
        return port
    return None


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def _api_call(port: int, method: str, path: str) -> dict:
    """Make an HTTP call to the harness API. Returns parsed JSON."""
    url = f"http://localhost:{port}{path}"
    req = urllib.request.Request(url, method=method)

    # POST requires content-length header even with no body
    if method == "POST":
        req.add_header("Content-Type", "application/json")
        req.data = b""

    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except (json.JSONDecodeError, AttributeError):
            detail = body
        print(f"Error: {e.code} — {detail}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        print(f"Harness not running or unreachable: {e}. Start with: squidsquad start",
              file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_start():
    """Boot harness (if not running) + start all agents."""
    port = _discover_harness()

    if port is None:
        # Spawn harness in a new terminal window
        print("Starting harness...")
        port = _spawn_harness()
        if port is None:
            print("Failed to start harness.", file=sys.stderr)
            return 1

    # Start all agents via harness
    print(f"Starting all agents (harness on port {port})...")
    result = _api_call(port, "POST", "/agents/all/start")

    # Print results
    for r in result.get("results", []):
        status = "OK" if r.get("success") else "FAIL"
        print(f"  [{r.get('role', '?')}] {r.get('action', '?')} — {status}: {r.get('message', '')}")

    return 0


def cmd_stop(role: str | None = None):
    """Stop agent(s)."""
    port = _discover_harness()
    if port is None:
        print("Harness not running. Start with: squidsquad start", file=sys.stderr)
        return 1

    if role:
        result = _api_call(port, "POST", f"/agents/{role}/stop")
        print(f"  [{role}] {result.get('message', 'stopped')}")
    else:
        result = _api_call(port, "POST", "/agents/all/stop")
        for r in result.get("results", []):
            status = "OK" if r.get("success") else "FAIL"
            print(f"  [{r.get('role', '?')}] {status}")

    return 0


def cmd_restart(role: str):
    """Restart a single agent."""
    port = _discover_harness()
    if port is None:
        print("Harness not running. Start with: squidsquad start", file=sys.stderr)
        return 1

    print(f"Restarting {role}...")
    result = _api_call(port, "POST", f"/agents/{role}/restart")
    success = result.get("success", False)
    print(f"  [{role}] {'OK' if success else 'FAIL'}: {result.get('message', '')}")
    return 0 if success else 1


def cmd_status():
    """Show harness + agent health."""
    port = _discover_harness()
    if port is None:
        print("Harness not running. Start with: squidsquad start", file=sys.stderr)
        return 1

    result = _api_call(port, "GET", "/status")

    # Print harness info
    harness = result.get("harness", {})
    print(f"Harness: {harness.get('status', 'unknown')} (port {harness.get('port', '?')}, uptime {harness.get('uptime_human', '?')})")
    print()

    # Print agent table
    agents = result.get("agents", [])
    if not agents:
        print("No agents detected.")
        return 0

    # Status emoji mapping
    status_emoji = {
        "running": "🦑",
        "starting": "⏳",
        "stopped": "⏹️",
        "stalled": "👻",
        "error": "❌",
        "unknown": "❓",
    }

    w = max(len(a.get("role", "")) for a in agents)
    w = max(w, 5)
    print(f"{'Agent':<{w}}  Status")
    print(f"{'-' * w}  {'-' * 10}")

    for a in agents:
        role = a.get("role", "?")
        status = a.get("status", "unknown")
        emoji = status_emoji.get(status, "❓")
        print(f"{role:<{w}}  {emoji} {status}")

    return 0


def cmd_shutdown():
    """Stop all agents and exit harness."""
    port = _discover_harness()
    if port is None:
        print("Harness not running.", file=sys.stderr)
        return 0  # Nothing to shut down

    print("Shutting down harness and all agents...")
    try:
        result = _api_call(port, "POST", "/shutdown")
        print(result.get("message", "Shutdown complete."))
    except SystemExit:
        # _api_call may exit(1) if harness closes connection mid-request
        print("Harness shutting down...")

    return 0


# ---------------------------------------------------------------------------
# Harness spawning
# ---------------------------------------------------------------------------

def _spawn_harness() -> int | None:
    """Spawn the harness in a new terminal window. Returns port or None."""
    if not HARNESS_SCRIPT.exists():
        print(f"ERROR: harness.py not found at {HARNESS_SCRIPT}", file=sys.stderr)
        return None

    system = platform.system().lower()

    if system == "windows":
        wt = shutil.which("wt")
        if wt:
            try:
                subprocess.Popen(
                    [wt, "new-tab", "--title", "squidsquad-harness",
                     "-d", str(REPO_ROOT),
                     "python", str(HARNESS_SCRIPT)],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=str(REPO_ROOT),
                )
            except Exception as e:
                print(f"Failed to spawn via wt.exe: {e}", file=sys.stderr)
                return None
        else:
            # Fallback: cmd /c start
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", "squidsquad-harness",
                     "python", str(HARNESS_SCRIPT)],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=str(REPO_ROOT),
                )
            except Exception as e:
                print(f"Failed to spawn harness: {e}", file=sys.stderr)
                return None

    elif system == "darwin":
        try:
            import shlex
            apple_script = (
                f'tell application "Terminal" to do script '
                f'"cd {shlex.quote(str(REPO_ROOT))} && python {shlex.quote(str(HARNESS_SCRIPT))}"'
            )
            subprocess.Popen(["osascript", "-e", apple_script])
        except Exception as e:
            print(f"Failed to spawn harness: {e}", file=sys.stderr)
            return None

    else:  # Linux
        tmux = shutil.which("tmux")
        if tmux:
            try:
                subprocess.run([tmux, "kill-session", "-t", "squidsquad-harness"],
                               capture_output=True, check=False)
                import shlex
                subprocess.Popen(
                    [tmux, "new-session", "-d", "-s", "squidsquad-harness",
                     f"cd {shlex.quote(str(REPO_ROOT))} && python {shlex.quote(str(HARNESS_SCRIPT))}"],
                )
            except Exception as e:
                print(f"Failed to spawn harness via tmux: {e}", file=sys.stderr)
                return None
        else:
            print("No terminal available (need wt.exe, Terminal.app, or tmux).", file=sys.stderr)
            return None

    # Poll for harness startup
    print("Waiting for harness to start...", end="", flush=True)
    for _ in range(HARNESS_STARTUP_TIMEOUT):
        time.sleep(1)
        print(".", end="", flush=True)
        port = _read_port()
        if port and _harness_alive(port):
            print(f" ready (port {port})")
            return port

    print(" timeout", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

USAGE = """\
Usage: squidsquad <command> [args]

Commands:
  start              Boot harness + spawn all agents
  stop [<role>]      Stop all agents (or one agent)
  restart <role>     Restart a single agent
  status             Show harness + agent health
  shutdown           Stop all agents and exit harness

Examples:
  squidsquad start
  squidsquad restart skill
  squidsquad status
  squidsquad shutdown
"""


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print(USAGE)
        return 0

    cmd = args[0]

    if cmd == "start":
        return cmd_start()
    elif cmd == "stop":
        role = args[1] if len(args) > 1 else None
        return cmd_stop(role)
    elif cmd == "restart":
        if len(args) < 2:
            print("Usage: squidsquad restart <role>", file=sys.stderr)
            return 2
        return cmd_restart(args[1])
    elif cmd == "status":
        return cmd_status()
    elif cmd == "shutdown":
        return cmd_shutdown()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(USAGE)
        return 2


if __name__ == "__main__":
    sys.exit(main())
