#!/usr/bin/env python3
"""SquidSquad Event Bus — fire-and-forget event emission to the harness (#4709).

Agents emit events via HTTP POST to the harness. Silent no-op on failure.
Zero behavior change for agents — events are purely observational.

Usage (from mechanical scripts only):
    from event_bus import emit
    emit("cycle-start", "skill", {"cycle_number": 862})
"""

import hashlib
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

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


def _generate_id(event_type, role, timestamp, payload):
    """Generate a short 8-char event ID from content hash."""
    raw = f"{timestamp}{role}{event_type}{json.dumps(payload, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def emit(event_type, role, payload=None, cycle_number=None):
    """Emit an event to the harness. Silent no-op on any failure.

    Args:
        event_type: Event type string (e.g. "cycle-start", "git-pull")
        role: Agent role (e.g. "skill", "pm", "qa", "dm")
        payload: Optional dict of event-specific data
        cycle_number: Optional cycle number (included at top level if provided)
    """
    try:
        port = _discover_port()
        if port is None:
            return

        if payload is None:
            payload = {}

        timestamp = datetime.now().isoformat(timespec="seconds")
        event_id = _generate_id(event_type, role, timestamp, payload)

        event = {
            "id": event_id,
            "event_type": event_type,
            "role": role,
            "timestamp": timestamp,
            "payload": payload,
        }
        if cycle_number is not None:
            event["cycle_number"] = cycle_number

        data = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/events",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=_TIMEOUT)
    except Exception:
        # Silent no-op — fire-and-forget contract
        pass


def ack(event_id, role):
    """Acknowledge event completion — posts ack event to harness (#7630 2-6).

    Fire-and-forget like emit(). If harness is unreachable, silently drops.
    """
    emit("ack", role, payload={"event_id": event_id})
