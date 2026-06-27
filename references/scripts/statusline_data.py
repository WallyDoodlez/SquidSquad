#!/usr/bin/env python3
"""SquidSquad statusline data source — bridges file-based and harness-API state (#8700).

The statusline.sh script renders per-role state. Historically it has read
`.squidsquad/<role>/current-state` directly, which works only when
`cycle_pre.py` / `cycle_post.py` are writing that file on every /loop tick.

In event-driven mode there are no /loop ticks, so the file goes stale.
This helper provides a single data source the shell script can call:

- If the role's wake mode is `event-driven` (config field
  `event-driven-<role>` or global `event-driven` set to yes/true/1) AND the
  harness HTTP API responds: query `GET /agents/<role>/health` and print
  `phase|description` (mirrors the current-state file format).
- Otherwise: read `.squidsquad/<role>/current-state` and pass through.

Exit code 0 on success (including the "no state available" empty case),
non-zero only on usage errors. The shell script never relies on this exit
status for liveness — it parses stdout.

Usage:
    python references/scripts/statusline_data.py phase <role>
    python references/scripts/statusline_data.py mode  <role>      # print "event-driven" or "polling"
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"
PORT_FILE = SQUID_DIR / ".harness-port"
DEFAULT_PORT = 7373
_HTTP_TIMEOUT = 1.5  # statusline renders frequently — keep tight


def _get_wake_mode(role):
    """Delegate to canonical config.get_wake_mode (#9745)."""
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from config import get_wake_mode
    except Exception:
        return "polling"
    return get_wake_mode(role)


def _harness_port():
    if PORT_FILE.exists():
        try:
            return int(PORT_FILE.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass
    return DEFAULT_PORT


def _harness_get(path):
    """GET <path> on the harness API. Returns dict on success, None on any failure."""
    port = _harness_port()
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        return None


def _read_current_state_file(role):
    """Read the existing on-disk current-state for a role. Returns the first line or empty."""
    state_file = SQUID_DIR / role / "current-state"
    if not state_file.exists():
        return ""
    try:
        return state_file.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return ""


def _is_inline_marker(line):
    """True if `line` is the agent-self-written `inline` current-state marker.

    During a live operator (inline) turn the cycle wrappers do not fire
    (#12800), so the agent self-writes `inline|...` to `current-state` and
    clears it when the turn ends. Because the wrappers are quiet, the
    harness phase is necessarily stale during that window — so this explicit,
    agent-cleared marker must take precedence over the harness, not be masked
    by it (#12451 AC4 / #12854 lingering-content).
    """
    return line.split("|", 1)[0].strip().lower() == "inline"


def cmd_phase(role):
    """Print `phase|description` for a role. Empty line if unavailable.

    Precedence: an explicit `inline` marker in `current-state` wins in either
    wake mode (#12451 AC4) — it's a self-written operator-session state the
    wrappers can't refresh, so a stale harness phase must not mask it.

    Otherwise, event-driven mode pulls phase + intent from the harness via
    `GET /agents/<role>` (in-memory state, updated by `phase-change` events)
    rather than `/agents/<role>/health` which only re-reads the on-disk
    current-state file (defeats the purpose in events mode).

    Falls back to the file when the harness is unreachable so the line
    doesn't go blank during a brief harness restart.
    """
    file_line = _read_current_state_file(role)

    # Inline marker takes precedence over the (stale) harness phase, in either
    # mode — render it as a distinct, clearly-labelled operator-session state.
    if _is_inline_marker(file_line):
        desc = file_line.split("|", 1)[1].strip() if "|" in file_line else ""
        print(f"inline|{desc or 'operator session'}")
        return 0

    if _get_wake_mode(role) == "event-driven":
        data = _harness_get(f"/agents/{role}")
        if isinstance(data, dict):
            phase = (data.get("current_phase") or "").strip()
            intent = (data.get("intent") or "").strip().lower()
            # Surface non-running intent (stopping/restarting/stopped) when
            # we don't have a phase from a recent event — operators rely on
            # this badge to see lifecycle state at a glance.
            if not phase and intent and intent != "running":
                phase = intent
            if phase:
                # /agents/<role> returns just the phase name (set from
                # `phase-change` event payload); there's no separate task
                # description on this endpoint yet. Emit `phase|` so the
                # shell parser stays consistent with the file format.
                print(f"{phase}|")
                return 0
        # Fall through to file on harness-unreachable / unknown agent so the
        # line doesn't go blank during a brief harness restart.

    if file_line:
        print(file_line)
    return 0


def cmd_mode(role):
    print(_get_wake_mode(role))
    return 0


def main():
    if len(sys.argv) < 3:
        print("Usage: statusline_data.py {phase|mode} <role>", file=sys.stderr)
        return 2
    cmd, role = sys.argv[1], sys.argv[2]
    if cmd == "phase":
        return cmd_phase(role)
    if cmd == "mode":
        return cmd_mode(role)
    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
