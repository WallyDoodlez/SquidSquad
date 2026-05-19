#!/usr/bin/env python3
"""SquidSquad agent health check — offline fallback for human diagnostics.

Prefer `GET /status` (`squidsquad_cli.py status`) when the harness is running;
the harness has authoritative liveness via direct PID monitoring (#4966). This
script is an offline fallback for cases where the harness is unreachable — it
walks each agent's `.claude-pid` and `current-state` files directly.

Reads `.local-config` to find each agent's clone path, then checks each
agent's `.claude-pid` (PID-liveness, primary signal) and `current-state`
mtime (staleness, secondary signal).

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

sys.path.insert(0, str(SCRIPT_DIR))
from process_utils import is_process_alive as _is_process_alive  # noqa: E402  (#8891)

# Health categories
HEALTHY = "healthy"
STALLED = "stalled"
UNKNOWN = "unknown"

# Emoji for display
HEALTH_EMOJI = {
    HEALTHY: "\U0001f991",  # 🦑
    STALLED: "\U0001f47b",  # 👻
    UNKNOWN: "❓",      # ❓
}


def _read_interval():
    """Read the iteration interval from config.md. Default 30.

    Uses config.py get_field (section-aware via FIELD_MAP) to avoid
    matching unrelated 'Minutes' occurrences in other config sections.
    """
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        val = get_field("interval")
        if val:
            return int(val)
    except (ImportError, ValueError, TypeError):
        pass
    return 30


def _parse_local_config():
    """Parse clone paths → {role: Path(clone_root)}.

    Reads project-local .local-config (scoped to this repo).
    .local-config is mandatory — if missing, exits with a clear error.

    The global ~/.squidsquad/clones/ fallback was removed (#3100) because
    it caused cross-project contamination when stale paths from other
    projects were present (#2750).
    """
    if not LOCAL_CONFIG.exists():
        print(
            f"ERROR: {LOCAL_CONFIG} not found.\n"
            "Run the SquidSquad setup flow to create .local-config, or create it manually.\n"
            "Format: - **role**: /absolute/path/to/clone",
            file=sys.stderr,
        )
        sys.exit(2)

    result = {}

    # .local-config (project-scoped, always correct)
    # Format: `- **role**: <path>` — relative paths resolve against repo root.
    try:
        text = LOCAL_CONFIG.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"-\s*\*\*([\w-]+)\*\*:\s*(.+)", line)
            if m:
                role = m.group(1).strip()
                raw_path = Path(m.group(2).strip())
                # Resolve relative paths against repo root
                if not raw_path.is_absolute():
                    raw_path = (REPO_ROOT / raw_path).resolve()
                result[role] = raw_path
    except Exception as e:
        print(
            f"ERROR: Failed to parse {LOCAL_CONFIG}: {e}\n"
            "Fix the file or re-run the SquidSquad setup flow.",
            file=sys.stderr,
        )
        sys.exit(2)

    if not result:
        print(
            f"ERROR: {LOCAL_CONFIG} exists but contains no valid entries.\n"
            "Expected format: - **role**: /absolute/path/to/clone",
            file=sys.stderr,
        )
        sys.exit(2)

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


def _read_claude_pid_file(squid_dir):
    """Read PID from .squidsquad/{role}/.claude-pid. Returns int or None.

    .claude-pid is written by the thin launcher (#4966) and contains the
    PID of the claude process itself (not the wrapper).
    """
    pid_file = squid_dir / ".claude-pid"
    if not pid_file.exists():
        return None
    try:
        content = pid_file.read_text(encoding="utf-8").strip()
        return int(content) if content else None
    except (ValueError, OSError):
        return None


def check_agent_health(role, clone_root, interval_minutes, now=None):
    """Check a single agent's health via .claude-pid + current-state mtime.

    PID-liveness on .claude-pid is the primary signal. current-state mtime
    is used for staleness only (agent alive but not progressing through
    cycles). When .claude-pid is missing, falls back to mtime-only.

    Args:
        role: agent id (e.g. "skill", "pm")
        clone_root: Path to the agent's git clone root
        interval_minutes: from config.md
        now: current epoch time (injectable for testing)

    Returns a dict:
        {
            "role": str,
            "health": "healthy" | "stalled" | "unknown",
            "health_source": "pid-check" | "mtime-fallback",
            "clone_path": str,
            "current_state_phase": str,
            "current_state_desc": str,
            "task": str,
            "last_active_minutes_ago": int | None,
            "reason": str,
            "pid": int (only when .claude-pid was read),
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

    # #4792: stop-detection lives in harness state (intent=stopping/stopped),
    # not file-based. health_check.py reports phase/PID-liveness only —
    # lifecycle intent is the harness's job via /agents/<role>.

    # Read current-state for phase info (always)
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
        result["last_active_minutes_ago"] = int((now - state_mtime) / 60)

    stale_threshold = interval_minutes * 2

    # --- Primary: PID-liveness via .claude-pid ---
    pid = _read_claude_pid_file(squid)
    if pid is not None:
        result["pid"] = pid
        result["health_source"] = "pid-check"
        if _is_process_alive(pid):
            if state_mtime is None:
                result["health"] = HEALTHY
                result["reason"] = f"PID {pid} alive (no current-state yet — freshly booted)"
            else:
                elapsed_minutes = int((now - state_mtime) / 60)
                if elapsed_minutes <= stale_threshold:
                    result["health"] = HEALTHY
                    result["reason"] = (
                        f"PID {pid} alive, active {elapsed_minutes}m ago "
                        f"(threshold {stale_threshold}m)"
                    )
                else:
                    result["health"] = STALLED
                    result["reason"] = (
                        f"PID {pid} alive but current-state stale "
                        f"({elapsed_minutes}m ago, threshold {stale_threshold}m)"
                    )
        else:
            result["health"] = STALLED
            result["reason"] = f"PID {pid} is dead (.claude-pid stale)"
        return result

    # --- Fallback: mtime-based detection (no .claude-pid file) ---
    if state_mtime is None:
        result["health"] = UNKNOWN
        result["reason"] = "no .claude-pid file, no current-state file"
        return result

    elapsed_minutes = int((now - state_mtime) / 60)
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

    all_healthy = all(r["health"] == HEALTHY for r in results) if results else True

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
        source = "pid" if a["health_source"] == "pid-check" else "mtime"
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
