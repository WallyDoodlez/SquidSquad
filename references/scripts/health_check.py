#!/usr/bin/env python3
"""SquidSquad agent health check — deterministic cross-clone health probe.

Reads .local-config to find each agent's actual clone path, then checks
each agent's `.health` file (written by boot script wrapper) for liveness
and `current-state` file for cycle-level phase detail. Falls back to
current-state mtime when .health is missing (old boot scripts).

Usage:
    python scripts/health_check.py              # Pretty table for humans
    python scripts/health_check.py --json       # JSON for scripts/boot_remote.py
    python scripts/health_check.py --help

Exit codes:
    0 — all agents healthy (or no agents configured)
    1 — at least one agent is stalled or unknown
    2 — usage error or missing prerequisites
"""

import io
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

# Ensure stdout can handle Unicode emoji on Windows (cp1252 can't encode them)
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
LOCAL_CONFIG = SQUIDSQUAD_DIR / ".local-config"
CONFIG_MD = SQUIDSQUAD_DIR / "config.md"

# Health categories
HEALTHY = "healthy"
STALLED = "stalled"
UNKNOWN = "unknown"
STOPPED = "stopped"
ERROR = "error"

# Emoji for display
HEALTH_EMOJI = {
    HEALTHY: "\U0001f991",  # 🦑
    STALLED: "\U0001f47b",  # 👻
    UNKNOWN: "\u2753",       # ❓
    STOPPED: "\u23f9\ufe0f", # ⏹️
    ERROR: "\u274c",         # ❌
}


def _read_interval():
    """Read the iteration interval from config.md. Default 30."""
    if not CONFIG_MD.exists():
        return 30
    try:
        text = CONFIG_MD.read_text(encoding="utf-8")
        # Works for both v1 ("Minutes": N) and v2 ("Interval Minutes": N)
        m = re.search(r"Minutes\b.*?(\d+)", text)
        return int(m.group(1)) if m else 30
    except Exception:
        return 30


def _parse_local_config():
    """Parse .local-config → {role: Path(clone_root)}.

    Format: `- **role**: /absolute/path`
    Returns empty dict if file missing or unparseable.
    """
    if not LOCAL_CONFIG.exists():
        return {}
    result = {}
    try:
        text = LOCAL_CONFIG.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"-\s*\*\*(\w+)\*\*:\s*(.+)", line)
            if m:
                role = m.group(1).strip()
                path = Path(m.group(2).strip())
                result[role] = path
    except Exception:
        pass
    return result


def _get_file_mtime(path):
    """Return mtime as epoch float, or None if file doesn't exist."""
    try:
        return path.stat().st_mtime
    except (OSError, ValueError):
        return None


def _read_file_head(path, max_bytes=500):
    """Read the first `max_bytes` of a file, or None."""
    try:
        return path.read_text(encoding="utf-8")[:max_bytes]
    except (OSError, UnicodeDecodeError):
        return None


def _parse_current_state(text):
    """Extract phase and description from a current-state line.

    Format: `phase|description`
    """
    if not text:
        return "", ""
    line = text.strip().split("\n")[0]
    parts = line.split("|", 1)
    phase = parts[0].strip() if parts else ""
    desc = parts[1].strip() if len(parts) > 1 else ""
    return phase, desc


def _parse_working_state_task(text):
    """Extract the Task field from working-state.md."""
    if not text:
        return "unknown"
    m = re.search(r"\*\*Task\*\*:\s*(.+)", text)
    if m:
        val = m.group(1).strip()
        return val if val and val != "none" else "idle"
    return "unknown"


def _read_pid_file(squid_dir):
    """Read PID from .squidsquad/{role}/.pid. Returns int or None."""
    pid_file = squid_dir / ".pid"
    if not pid_file.exists():
        return None
    try:
        content = pid_file.read_text(encoding="utf-8").strip()
        return int(content) if content else None
    except (ValueError, OSError):
        return None


def _is_process_alive(pid):
    """Check if a process with the given PID is still running."""
    if pid is None:
        return False
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, check=False,
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def _parse_health_file(text):
    """Parse .health file content → (status, detail).

    Format: `status` or `status|detail`
    Valid statuses: booting, alive, restarting, backoff, dead, error
    """
    if not text:
        return None, None
    line = text.strip().split("\n")[0]
    parts = line.split("|", 1)
    status = parts[0].strip() if parts else ""
    detail = parts[1].strip() if len(parts) > 1 else ""
    return status, detail


def check_agent_health(role, clone_root, interval_minutes, now=None):
    """Check a single agent's health.

    Uses .health file for liveness (primary), current-state mtime as fallback.

    Args:
        role: agent id (e.g. "skill", "pm")
        clone_root: Path to the agent's git clone root
        interval_minutes: from config.md
        now: current epoch time (injectable for testing)

    Returns a dict:
        {
            "role": str,
            "health": "healthy" | "stalled" | "unknown" | "stopped" | "error",
            "health_source": "health-file" | "mtime-fallback",
            "health_file_status": str | None,
            "health_file_detail": str | None,
            "clone_path": str,
            "current_state_phase": str,
            "current_state_desc": str,
            "task": str,
            "last_active_minutes_ago": int | None,
            "reason": str,
        }
    """
    if now is None:
        now = time.time()

    clone_root = Path(clone_root)
    squid = clone_root / ".squidsquad" / role
    result = {
        "role": role,
        "health": UNKNOWN,
        "health_source": "mtime-fallback",
        "health_file_status": None,
        "health_file_detail": None,
        "clone_path": str(clone_root),
        "current_state_phase": "",
        "current_state_desc": "",
        "task": "unknown",
        "last_active_minutes_ago": None,
        "reason": "",
    }

    # Check if clone root is reachable
    if not clone_root.exists():
        result["reason"] = f"clone path does not exist: {clone_root}"
        return result

    # Check .stop sentinel
    stop_file = squid / ".stop"
    if stop_file.exists():
        result["health"] = STOPPED
        result["reason"] = ".stop sentinel present — agent explicitly stopped"
        return result

    # Read current-state for phase info (always, regardless of .health)
    state_file = squid / "current-state"
    state_mtime = _get_file_mtime(state_file)
    state_text = _read_file_head(state_file)
    phase, desc = _parse_current_state(state_text)
    result["current_state_phase"] = phase
    result["current_state_desc"] = desc

    # Read working-state for task info
    ws_file = squid / "working-state.md"
    ws_text = _read_file_head(ws_file)
    result["task"] = _parse_working_state_task(ws_text)

    # Compute last_active from current-state mtime
    if state_mtime is not None:
        elapsed_seconds = now - state_mtime
        result["last_active_minutes_ago"] = int(elapsed_seconds / 60)

    # --- Primary: read .health file for liveness ---
    health_file = squid / ".health"
    health_text = _read_file_head(health_file)
    health_status, health_detail = _parse_health_file(health_text)

    if health_status is not None:
        result["health_source"] = "health-file"
        result["health_file_status"] = health_status
        result["health_file_detail"] = health_detail

        if health_status == "alive":
            # PID cross-check: .health can go stale if process was killed externally
            pid = _read_pid_file(squid)
            pid_alive = _is_process_alive(pid)
            result["pid"] = pid

            if not pid_alive:
                # PID is dead — agent is not actually alive regardless of .health
                result["health"] = STALLED
                if pid is not None:
                    result["reason"] = (
                        f".health=alive but PID {pid} is dead — stale .health file"
                    )
                else:
                    result["reason"] = (
                        ".health=alive but no .pid file — cannot verify liveness"
                    )
                # Auto-correct stale .health to 'dead'
                try:
                    health_file.write_text("dead|stale - corrected by health_check\n",
                                           encoding="utf-8")
                except OSError:
                    pass
                return result

            # PID is alive — check current-state staleness
            stale_threshold = interval_minutes * 2
            if state_mtime is not None:
                elapsed_minutes = int((now - state_mtime) / 60)
                if elapsed_minutes <= stale_threshold:
                    result["health"] = HEALTHY
                    result["reason"] = (
                        f"PID {pid} alive, active {elapsed_minutes}m ago "
                        f"(threshold {stale_threshold}m)"
                    )
                else:
                    # PID alive but current-state is stale — agent may be stuck
                    result["health"] = STALLED
                    result["reason"] = (
                        f"PID {pid} alive but current-state stale "
                        f"({elapsed_minutes}m ago, threshold {stale_threshold}m)"
                    )
            else:
                # PID alive but no current-state yet (agent just booted)
                result["health"] = HEALTHY
                result["reason"] = f"PID {pid} alive (no current-state yet — freshly booted)"

        elif health_status == "booting":
            result["health"] = HEALTHY
            result["reason"] = ".health=booting (agent starting up)"

        elif health_status == "restarting":
            result["health"] = HEALTHY
            result["reason"] = ".health=restarting (wrapper restarting agent)"

        elif health_status == "backoff":
            result["health"] = STALLED
            result["reason"] = ".health=backoff (crash loop — exponential backoff)"

        elif health_status == "dead":
            result["health"] = STALLED
            result["reason"] = ".health=dead (wrapper exited)"

        elif health_status == "error":
            result["health"] = ERROR
            detail_msg = f": {health_detail}" if health_detail else ""
            result["reason"] = f".health=error{detail_msg}"

        else:
            # Unknown .health status — treat as unknown
            result["health"] = UNKNOWN
            result["reason"] = f".health={health_status} (unrecognized)"

        return result

    # --- Fallback: mtime-based detection (no .health file) ---
    result["health_source"] = "mtime-fallback"

    if state_mtime is None:
        result["health"] = UNKNOWN
        result["reason"] = "no .health file, no current-state file"
        return result

    elapsed_seconds = now - state_mtime
    elapsed_minutes = int(elapsed_seconds / 60)
    stale_threshold = interval_minutes * 2
    if elapsed_minutes <= stale_threshold:
        result["health"] = HEALTHY
        result["reason"] = (
            f"mtime fallback: active {elapsed_minutes}m ago "
            f"(threshold {stale_threshold}m)"
        )
    else:
        result["health"] = STALLED
        result["reason"] = (
            f"mtime fallback: last active {elapsed_minutes}m ago "
            f"(threshold {stale_threshold}m)"
        )

    return result


def check_all_agents(local_config_overrides=None):
    """Check health of every agent found in .local-config.

    Args:
        local_config_overrides: optional dict {role: Path} to use instead
            of reading .local-config (for testing)

    Returns:
        {
            "agents": [check_agent_health result per agent],
            "interval_minutes": int,
            "all_healthy": bool,
            "timestamp": str (ISO 8601),
        }
    """
    interval = _read_interval()
    now = time.time()

    if local_config_overrides is not None:
        agents_map = local_config_overrides
    else:
        agents_map = _parse_local_config()

    results = []
    for role in sorted(agents_map):
        clone_root = agents_map[role]
        result = check_agent_health(role, clone_root, interval, now=now)
        results.append(result)

    all_healthy = all(
        r["health"] in (HEALTHY, STOPPED)
        for r in results
    ) if results else True

    return {
        "agents": results,
        "interval_minutes": interval,
        "all_healthy": all_healthy,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def format_table(report):
    """Render a human-readable table from check_all_agents output."""
    agents = report["agents"]
    if not agents:
        return "No agents configured in .local-config.\n"

    # Column widths
    w_role = max(len(a["role"]) for a in agents)
    w_role = max(w_role, 5)  # min "Agent"

    lines = []
    header = f"{'Agent':<{w_role}}  Health  Source   Last     Phase            Task"
    lines.append(header)
    lines.append("-" * len(header))

    for a in agents:
        emoji = HEALTH_EMOJI.get(a["health"], "?")
        source = "file" if a["health_source"] == "health-file" else "mtime"
        last = (
            f"{a['last_active_minutes_ago']}m"
            if a["last_active_minutes_ago"] is not None
            else "n/a"
        )
        phase = a["current_state_phase"][:15] if a["current_state_phase"] else "-"
        task = a["task"][:20] if a["task"] else "-"
        lines.append(
            f"{a['role']:<{w_role}}  {emoji:<7} {source:<8} {last:<8} {phase:<16} {task}"
        )

    return "\n".join(lines) + "\n"


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    use_json = "--json" in args

    if not SQUIDSQUAD_DIR.exists():
        print(
            "ERROR: .squidsquad/ not found — not a SquidSquad project",
            file=sys.stderr,
        )
        return 2

    if not LOCAL_CONFIG.exists():
        if use_json:
            print(json.dumps({
                "agents": [],
                "all_healthy": False,
                "warning": ".local-config not found — no cross-clone paths configured",
            }, indent=2))
        else:
            print(
                "WARNING: .squidsquad/.local-config not found. "
                "No cross-clone agent paths configured.\n"
                "Health check requires .local-config with agent clone paths.\n"
                "Format: - **role**: /absolute/path/to/clone"
            )
        return 1  # No agents checked — surface as non-healthy

    report = check_all_agents()

    if use_json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_table(report))

    return 0 if report["all_healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
