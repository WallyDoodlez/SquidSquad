#!/usr/bin/env python3
"""SquidSquad watchdog — standalone agent lifecycle supervisor.

Replaces all agent self-health logic (self-restart, context pressure restart,
PM health check, PM boot remote). Agents become dumb workers; the watchdog
owns all lifecycle management.

Runs as a standalone process, checking agent health every ~30 seconds.
For each agent:
  1. If dead/stalled → boot via boot_remote.py
  2. If context pressure exceeds threshold → wait for cycle end, then restart
  3. If CLAUDE.md template changed since agent session start → restart

Usage:
    python scripts/watchdog.py                # Run continuously (~30s loop)
    python scripts/watchdog.py --once         # Single check, then exit
    python scripts/watchdog.py --json         # JSON output (implies --once)
    python scripts/watchdog.py --interval 15  # Custom interval in seconds
    python scripts/watchdog.py --help

Exit codes:
    0 — success (or clean shutdown)
    1 — at least one agent needed intervention
    2 — usage error
"""

import io
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

# Ensure stdout can handle Unicode on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
CONFIG_MD = SQUIDSQUAD_DIR / "config.md"
WATCHDOG_LOG = SQUIDSQUAD_DIR / "watchdog-log.txt"

DEFAULT_INTERVAL = 30  # seconds between checks
MAX_LOG_LINES = 500  # trim log when it exceeds this

# Import sibling modules
sys.path.insert(0, str(SCRIPT_DIR))
import health_check  # noqa: E402
import boot_remote  # noqa: E402


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _read_context_threshold():
    """Read context pressure threshold from config.md. Default 70."""
    if not CONFIG_MD.exists():
        return 70
    try:
        text = CONFIG_MD.read_text(encoding="utf-8")
        m = re.search(r"Threshold\*\*:\s*(\d+)", text)
        return int(m.group(1)) if m else 70
    except Exception:
        return 70


def _read_interval_minutes():
    """Read iteration interval from config.md. Default 30."""
    if not CONFIG_MD.exists():
        return 30
    try:
        text = CONFIG_MD.read_text(encoding="utf-8")
        m = re.search(r"Minutes\b.*?(\d+)", text)
        return int(m.group(1)) if m else 30
    except Exception:
        return 30


def _get_all_roles():
    """Get all agent roles from config.md (includes PM)."""
    roles = set()
    roles.add("pm")  # PM is always present

    if not CONFIG_MD.exists():
        return sorted(roles)

    try:
        text = CONFIG_MD.read_text(encoding="utf-8")
        # Dev agents
        m = re.search(r"Dev Agents\*\*:\s*(.+)", text)
        if m:
            for a in m.group(1).split(","):
                a = a.strip()
                if a:
                    roles.add(a)
        # DM
        if re.search(r"\*\*DM\*\*:\s*present", text, re.IGNORECASE):
            roles.add("dm")
        # QA
        if re.search(r"\*\*QA\*\*:\s*always present", text, re.IGNORECASE):
            roles.add("qa")
    except Exception:
        pass

    return sorted(roles)


# ---------------------------------------------------------------------------
# Agent state readers
# ---------------------------------------------------------------------------


def _read_context_pressure(role, clone_root):
    """Read context pressure percentage for an agent. Returns int or None."""
    pressure_file = Path(clone_root) / ".squidsquad" / role / "context-pressure"
    if not pressure_file.exists():
        return None
    try:
        raw = pressure_file.read_text(encoding="utf-8").strip().split("\n")[0].strip()
        return int(raw) if raw.isdigit() else None
    except (OSError, ValueError):
        return None


def _read_current_state(role, clone_root):
    """Read current-state for an agent. Returns (phase, desc) or ('', '')."""
    state_file = Path(clone_root) / ".squidsquad" / role / "current-state"
    if not state_file.exists():
        return "", ""
    try:
        text = state_file.read_text(encoding="utf-8").strip()
        if not text:
            return "", ""
        parts = text.split("\n")[0].split("|", 1)
        phase = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""
        return phase, desc
    except (OSError, UnicodeDecodeError):
        return "", ""


def _get_template_mtime(role, clone_root):
    """Get mtime of agent's CLAUDE.md template. Returns epoch float or None."""
    template = Path(clone_root) / ".squidsquad" / role / "CLAUDE.md"
    try:
        return template.stat().st_mtime if template.exists() else None
    except OSError:
        return None


def _get_session_start_time(role, clone_root):
    """Estimate session start time from .health file mtime when it was set to alive.

    Falls back to .pid file mtime as a proxy for when the session started.
    """
    squid = Path(clone_root) / ".squidsquad" / role
    # Use .pid mtime as session start proxy
    pid_file = squid / ".pid"
    try:
        if pid_file.exists():
            return pid_file.stat().st_mtime
    except OSError:
        pass
    return None


def _read_pid(role, clone_root):
    """Read PID from .squidsquad/{role}/.pid. Returns int or None."""
    pid_file = Path(clone_root) / ".squidsquad" / role / ".pid"
    if not pid_file.exists():
        return None
    try:
        content = pid_file.read_text(encoding="utf-8").strip()
        return int(content) if content else None
    except (ValueError, OSError):
        return None


def _kill_agent(pid):
    """Kill an agent process. Returns True if killed."""
    if pid is None:
        return False
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                capture_output=True, text=True, check=False,
            )
            return result.returncode == 0
        else:
            os.kill(pid, signal.SIGINT)
            # Wait briefly for graceful shutdown
            time.sleep(2)
            try:
                os.kill(pid, 0)
                # Still alive — force kill
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass  # Already dead
            return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def _is_cycle_complete(role, clone_root):
    """Check if agent's current cycle is complete (phase is 'idle')."""
    phase, _ = _read_current_state(role, clone_root)
    return phase == "idle"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log(message, level="INFO"):
    """Append a timestamped line to the watchdog log."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {level} | {message}"
    try:
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    print(f"[watchdog {ts}] {message}")


def _trim_log():
    """Keep watchdog log to MAX_LOG_LINES."""
    if not WATCHDOG_LOG.exists():
        return
    try:
        lines = WATCHDOG_LOG.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_LOG_LINES:
            WATCHDOG_LOG.write_text(
                "\n".join(lines[-MAX_LOG_LINES:]) + "\n",
                encoding="utf-8",
            )
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Core watchdog logic
# ---------------------------------------------------------------------------


def check_and_act(roles=None):
    """Run one watchdog check cycle. Returns list of action dicts."""
    clone_paths = boot_remote._parse_local_config()
    ctx_threshold = _read_context_threshold()
    interval_minutes = _read_interval_minutes()

    if roles is None:
        roles = _get_all_roles()

    actions = []

    for role in roles:
        clone_root = clone_paths.get(role, REPO_ROOT)
        action = {
            "role": role,
            "action": "none",
            "detail": "",
        }

        # Step 1: Health check — boot dead agents
        health = health_check.check_agent_health(
            role, clone_root, interval_minutes
        )

        if health["health"] == health_check.STOPPED:
            action["action"] = "skip"
            action["detail"] = "explicitly stopped"
            actions.append(action)
            continue

        if health["health"] in (health_check.STALLED, health_check.UNKNOWN,
                                health_check.ERROR):
            # Agent is dead/stalled — boot it
            result = boot_remote.boot_agent(role)
            action["action"] = "boot"
            action["detail"] = result.get("message", "")
            action["boot_result"] = result
            _log(f"{role}: booting — {health['reason']}")
            actions.append(action)
            continue

        # Agent is healthy — check for lifecycle interventions

        # Step 2: Context pressure check
        pressure = _read_context_pressure(role, clone_root)
        if pressure is not None and pressure >= ctx_threshold:
            pid = _read_pid(role, clone_root)
            if pid and _is_cycle_complete(role, clone_root):
                _log(
                    f"{role}: context pressure {pressure}% >= {ctx_threshold}% "
                    f"and cycle complete — restarting"
                )
                _kill_agent(pid)
                action["action"] = "restart"
                action["detail"] = (
                    f"context pressure {pressure}% (threshold {ctx_threshold}%)"
                )
                actions.append(action)
                continue
            elif pid:
                # Pressure is high but cycle not complete — note but don't act yet
                action["action"] = "pending-restart"
                action["detail"] = (
                    f"context pressure {pressure}% — waiting for cycle to complete"
                )
                actions.append(action)
                continue

        # Step 3: Template change check
        template_mtime = _get_template_mtime(role, clone_root)
        session_start = _get_session_start_time(role, clone_root)
        if (
            template_mtime is not None
            and session_start is not None
            and template_mtime > session_start
        ):
            pid = _read_pid(role, clone_root)
            if pid and _is_cycle_complete(role, clone_root):
                _log(
                    f"{role}: template changed since session start — restarting"
                )
                _kill_agent(pid)
                action["action"] = "restart"
                action["detail"] = "template changed since session start"
                actions.append(action)
                continue

        action["action"] = "healthy"
        action["detail"] = health["reason"]
        actions.append(action)

    return actions


def run_once():
    """Run a single watchdog check. Returns (actions, any_intervention)."""
    actions = check_and_act()
    any_intervention = any(
        a["action"] in ("boot", "restart")
        for a in actions
    )
    return actions, any_intervention


def run_loop(interval=DEFAULT_INTERVAL):
    """Run the watchdog loop continuously."""
    _log(f"Watchdog started (interval={interval}s)")
    _trim_log()

    running = True

    def handle_signal(signum, frame):
        nonlocal running
        _log("Shutdown signal received")
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, handle_signal)

    while running:
        try:
            actions, _ = run_once()

            # Summarize
            interventions = [
                a for a in actions if a["action"] in ("boot", "restart")
            ]
            if interventions:
                summary = ", ".join(
                    f"{a['role']}:{a['action']}" for a in interventions
                )
                _log(f"Interventions: {summary}")
        except Exception as e:
            _log(f"Error during check: {e}", level="ERROR")

        # Sleep in small increments so we can respond to signals
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    _log("Watchdog stopped")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    use_json = "--json" in args
    once = "--once" in args or use_json

    interval = DEFAULT_INTERVAL
    for i, a in enumerate(args):
        if a == "--interval" and i + 1 < len(args):
            try:
                interval = int(args[i + 1])
            except ValueError:
                print(f"Invalid interval: {args[i + 1]}", file=sys.stderr)
                return 2

    if not SQUIDSQUAD_DIR.exists():
        print(
            "ERROR: .squidsquad/ not found — not a SquidSquad project",
            file=sys.stderr,
        )
        return 2

    if once:
        actions, any_intervention = run_once()
        if use_json:
            print(json.dumps({
                "actions": actions,
                "any_intervention": any_intervention,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, indent=2, default=str))
        else:
            for a in actions:
                status = a["action"].upper()
                print(f"[{a['role']}] {status}: {a['detail']}")
        return 1 if any_intervention else 0
    else:
        run_loop(interval=interval)
        return 0


if __name__ == "__main__":
    sys.exit(main())
