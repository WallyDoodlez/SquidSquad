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
    """Lookup precedence: event-driven-<role> → event-driven → polling."""
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from config import get_field
    except Exception:
        return "polling"
    for field in (f"event-driven-{role}", "event-driven"):
        try:
            v = (get_field(field) or "").strip().lower()
        except SystemExit:
            v = ""
        if v in ("yes", "true", "1", "event-driven"):
            return "event-driven"
        if v in ("no", "false", "0", "polling"):
            return "polling"
    return "polling"


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


def cmd_phase(role):
    """Print `phase|description` for a role. Empty line if unavailable.

    Event-driven mode pulls phase + intent from the harness via
    `GET /agents/<role>` (in-memory state, updated by `phase-change` events)
    rather than `/agents/<role>/health` which only re-reads the on-disk
    current-state file (defeats the purpose in events mode).

    Falls back to the file when the harness is unreachable so the line
    doesn't go blank during a brief harness restart.
    """
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

    line = _read_current_state_file(role)
    if line:
        print(line)
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
