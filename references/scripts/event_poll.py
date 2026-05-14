#!/usr/bin/env python3
"""Poll harness event bus and output events as JSON to stdout (#7630 2-5).

Designed for use with the Claude Code Monitor tool. Queries
GET /events?since=<cursor>&role=<role>, outputs one JSON object per event
to stdout. Saves cursor in .squidsquad/<role>/.event-cursor for resumption.

Usage:
    python event_poll.py <role>               # Poll once, output events
    python event_poll.py <role> --wait <sec>   # Poll in loop with interval

Stdout: clean JSON only (one object per line). Errors go to stderr.
Exit codes: 0 = events found, 1 = no events, 2 = harness unreachable
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"

_TIMEOUT = 2  # seconds — longer than emit (agent can afford brief wait)


def _discover_port():
    """Read harness port from .harness-port file."""
    port_file = SQUID_DIR / ".harness-port"
    if port_file.exists():
        try:
            return int(port_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass
    return None


def _read_cursor(role):
    """Read last processed event ID from cursor file."""
    cursor_file = SQUID_DIR / role / ".event-cursor"
    if cursor_file.exists():
        try:
            return cursor_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return ""


def _write_cursor(role, cursor):
    """Save cursor atomically."""
    cursor_file = SQUID_DIR / role / ".event-cursor"
    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = cursor_file.with_suffix(".tmp")
    try:
        tmp.write_text(cursor, encoding="utf-8")
        tmp.replace(cursor_file)
    except OSError:
        pass


def poll(role, limit=50):
    """Poll for new events. Returns list of event dicts."""
    port = _discover_port()
    if port is None:
        print("ERROR: harness port not found", file=sys.stderr)
        return None

    cursor = _read_cursor(role)
    params = {"role": role, "limit": limit}
    if cursor:
        params["since"] = cursor
    url = f"http://127.0.0.1:{port}/events?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, TimeoutError):
        print("ERROR: harness unreachable", file=sys.stderr)
        return None

    events = data.get("events", [])
    if events:
        last_id = events[-1].get("id", "")
        if last_id:
            _write_cursor(role, last_id)

    return events


def main():
    if len(sys.argv) < 2:
        print("Usage: event_poll.py <role> [--wait <seconds>]", file=sys.stderr)
        sys.exit(2)

    role = sys.argv[1]
    wait = None
    if "--wait" in sys.argv:
        idx = sys.argv.index("--wait")
        if idx + 1 < len(sys.argv):
            try:
                wait = int(sys.argv[idx + 1])
            except ValueError:
                print("ERROR: --wait requires integer seconds", file=sys.stderr)
                sys.exit(2)

    while True:
        events = poll(role)
        if events is None:
            sys.exit(2)

        for event in events:
            print(json.dumps(event), flush=True)

        if wait is None:
            sys.exit(0 if events else 1)

        time.sleep(wait)


if __name__ == "__main__":
    main()
