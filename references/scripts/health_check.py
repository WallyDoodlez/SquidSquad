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
import re
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

    Catches `SystemExit` because `config.get_field` calls `sys.exit(1)`
    when the field is absent and not in `_FIELD_DEFAULTS`, same for
    `_read_config()` on missing config.md. SystemExit is a BaseException,
    not an Exception, so a narrow `except Exception` would miss it (#10348).
    KeyboardInterrupt deliberately propagates — Ctrl+C must abort, not
    silently fall through to the default.
    """
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        val = get_field("interval")
        if val:
            return int(val)
    except (SystemExit, Exception):
        pass
    return 30


# #13742 verifier round 1: raw (pre-resolution) .local-config values from the
# most recent _parse_local_config() call, keyed by role. "." is compose.py's
# ONE special-cased default (only ever assigned to "pm") -- a NON-pm role
# storing raw "." is always a stale/misconfigured entry by construction, so
# its resolution to REPO_ROOT must never be trusted as ground truth, even
# when it happens to numerically match. A role with a genuine sibling-
# relative raw value (e.g. "../SquidSquad-qa") that ALSO resolves to
# REPO_ROOT (via legitimate sibling-symmetric self-reference) is NOT
# ambiguous the same way. check_all_agents() consults this to distinguish
# the two cases when exempting a role from collision-flagging.
_LAST_PARSED_RAW = {}


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
    raw = {}

    # .local-config (project-scoped, always correct)
    # Format: `- **role**: <path>` — relative paths resolve against repo root.
    try:
        text = LOCAL_CONFIG.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"-\s*\*\*([\w-]+)\*\*:\s*(.+)", line)
            if m:
                role = m.group(1).strip()
                raw_str = m.group(2).strip()
                raw[role] = raw_str
                raw_path = Path(raw_str)
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

    global _LAST_PARSED_RAW
    _LAST_PARSED_RAW = raw
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
            "current_state_stale": bool,  # #12854: phase/desc is past the
                                          # staleness window — treat as
                                          # last-known, NOT current activity
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
        "current_state_stale": False,
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

    # #12854: flag whether the current-state CONTENT can still be trusted as
    # *current* activity. A still-alive agent that stopped/stalled mid-cycle
    # never reaches cycle_post's "idle" write, so its current-state freezes on
    # the last in-flight phase/desc (e.g. "implementing — #X running suite").
    # Past the staleness window that frozen content is no longer "what the
    # agent is doing" — but it reads as authoritative and seeds wrong root-cause
    # theories (the #12854 incident: a frozen "running full suite" sent PM down
    # a hung-suite theory). The agent cannot self-correct it (it's stopped), so
    # this reader-side flag is the reliable signal; consumers (PM health checks,
    # operator, pipeline-sentinel) must treat phase/desc as last-known-stale,
    # not current, when it is set. (current-state is gitignored, so its mtime is
    # never spuriously refreshed by git — the staleness measure is sound.)
    if state_mtime is not None:
        result["current_state_stale"] = (now - state_mtime) / 60 > stale_threshold

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


def check_all_agents(local_config_overrides=None, local_config_raw_overrides=None):
    """Check health of every agent found in .local-config.

    Args:
        local_config_overrides: optional dict {role: Path} to use instead
            of reading .local-config (for testing)
        local_config_raw_overrides: optional dict {role: str} of the raw
            (pre-resolution) .local-config value per role, paired with
            local_config_overrides (for testing the #13742 exemption below).
            Ignored when local_config_overrides is None (a real read
            populates _LAST_PARSED_RAW from the actual file).

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
        raw_map = local_config_raw_overrides or {}
    else:
        agents_map = _parse_local_config()
        raw_map = _LAST_PARSED_RAW

    # #13742: a misconfigured/stale .local-config can resolve two DIFFERENT
    # roles' relative paths to the SAME clone_path (most commonly: pm's "."
    # shorthand only resolves correctly when read from pm's own clone --
    # every other clone reading "pm: ." resolves it to ITS OWN root instead,
    # colliding with whichever OTHER role also maps there). A collision like
    # this produces a health verdict built from the WRONG agent's on-disk
    # files -- confirmed live to sometimes read as a confident but false
    # "stalled" (a stray/unrelated .claude-pid under the wrong clone), not
    # merely "unknown". Detect collisions up front and flag every affected
    # role loudly instead of silently running the normal check against data
    # that structurally cannot be trusted.
    path_to_roles = {}
    for role, clone_root in agents_map.items():
        path_to_roles.setdefault(Path(clone_root), []).append(role)
    colliding_roles = {
        role
        for roles in path_to_roles.values() if len(roles) > 1
        for role in roles
    }
    # #13742 verifier round 1: a role whose OWN resolved path equals
    # REPO_ROOT (this script's own execution root) is independently
    # ground-truthed -- this process IS running from that root -- BUT ONLY
    # when its raw (pre-resolution) value isn't "." itself. "." is
    # compose.py's ONE special-cased default (assigned only to "pm"); any
    # OTHER role storing raw "." is always a stale/misconfigured entry by
    # construction, and its coincidental resolution to REPO_ROOT is exactly
    # the untrustworthy case this whole check exists to catch -- exempting
    # it would silently re-trust the very data that's broken. A role with a
    # genuine sibling-relative raw value (e.g. "../SquidSquad-qa") that also
    # resolves to REPO_ROOT via legitimate sibling-symmetric self-reference
    # is not ambiguous the same way, and is safe to exempt. Without this
    # distinction, a role whose entry is genuinely correct could get swept
    # into "don't trust this" purely because a DIFFERENT role's broken "."
    # entry happens to collide onto the same path -- a regression from a
    # previously-accurate reading.
    colliding_roles -= {
        role for role in colliding_roles
        if agents_map[role] == REPO_ROOT and raw_map.get(role) != "."
    }

    results = []
    for role in sorted(agents_map):
        clone_root = agents_map[role]
        if role in colliding_roles:
            other_roles = sorted(
                r for r in path_to_roles[Path(clone_root)] if r != role
            )
            result = {
                "role": role,
                "health": UNKNOWN,
                "health_source": "local-config-collision",
                "clone_path": str(clone_root),
                "current_state_phase": "",
                "current_state_desc": "",
                "current_state_stale": False,
                "task": "unknown",
                "last_active_minutes_ago": None,
                "reason": (
                    f".local-config error: '{role}' resolves to the same "
                    f"clone_path as {other_roles} ({clone_root}) -- this is "
                    f"a misconfigured/stale .local-config entry, not a "
                    f"genuine health reading. Fix .local-config before "
                    f"trusting this result."
                ),
            }
        else:
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
        phase = a["current_state_phase"] if a["current_state_phase"] else "-"
        # #12854: a leading "~" marks the phase as last-known-stale, not current,
        # so the table never presents frozen content as live activity. The
        # authoritative signal is the `current_state_stale` JSON field.
        if a.get("current_state_stale") and a["current_state_phase"]:
            phase = "~" + phase
        phase = phase[:15]
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
