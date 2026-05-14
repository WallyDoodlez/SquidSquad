#!/usr/bin/env python3
"""SquidSquad Event Bus Reader — cursor-based event consumption from harness (#5622).

Agents read events via HTTP GET from the harness. Silent empty-list on failure.
Designed for use in cycle_pre.py — mechanical layer only.

Usage:
    from event_bus_reader import query
    events = query(since="a1b2c3d4", role="skill", limit=50)
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlencode

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"

# Timeout: 500ms — never blocks agent cycle
_TIMEOUT = 0.5


def _discover_port():
    """Discover harness port via .harness-port file (#7630 P-2).

    Reads directly from local .squidsquad/.harness-port. The harness
    distributes the port file to all clone directories at boot
    (harness.py lifespan), so parent-dir walk is unnecessary.

    Returns port number or None if not discoverable.
    """
    port_file = SQUID_DIR / ".harness-port"
    if port_file.exists():
        try:
            return int(port_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass
    return None


def query(since=None, role=None, event_type=None, limit=100):
    """Query events from the harness event bus.

    Args:
        since: Event ID — return events after this ID. None = get recent.
        role: Filter by emitting role (e.g. "skill", "pm").
        event_type: Filter by event type (e.g. "pr-merge,verification-failed").
        limit: Max events to return (default 100).

    Returns:
        List of event dicts, or [] on any failure (timeout, unreachable, etc).
    """
    try:
        port = _discover_port()
        if port is None:
            return []

        params = {"limit": str(limit)}
        if since and since != "none":
            params["since"] = since
        if role:
            params["role"] = role
        if event_type:
            params["event_type"] = event_type

        url = f"http://127.0.0.1:{port}/events?{urlencode(params)}"
        req = urllib.request.Request(url, method="GET")
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("events", [])
    except Exception:
        # Silent empty-list — same contract as emit's fire-and-forget
        return []
