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
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent


def _resolve_squid_dir() -> Path:
    """#9398: honor SQUIDSQUAD_DIR env var so isolated test harnesses
    can be discovered by event_bus.emit() in agent subprocesses
    without the live .harness-port file getting in the way.

    Default unchanged for production callers when env var is unset.
    Strips whitespace, expands ``~``, treats empty as unset — same
    foot-gun handling as harness._resolve_squidsquad_dir (Sonnet
    code review of PR #9614).
    """
    raw = (os.environ.get("SQUIDSQUAD_DIR") or "").strip()
    if not raw:
        return REPO_ROOT / ".squidsquad"
    return Path(raw).expanduser()


SQUID_DIR = _resolve_squid_dir()

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
    """Generate a 16-char (64-bit) event ID from content hash + per-emit nonce.

    The previous 8-char width hit birthday collisions at ~65k events and
    silently collapsed distinct emits with identical ``(event_type, role,
    timestamp, payload)`` to the same ID. Both failure modes are addressed
    by #9415:

    - Width doubles to 16 hex (64-bit) per CONTEXT-9415 D4 — practically
      infinite for our event volume.
    - A 4-hex (``os.urandom(2)``) nonce is folded into the hash input per
      CONTEXT-9415 D5 so distinct emits never collide even when content
      is byte-identical. Callsite signature is unchanged (D5/§6.5); a
      future caller that needs deterministic-from-content IDs can pre-
      compute the nonce upstream — no such caller exists today.
    """
    nonce = os.urandom(2).hex()
    raw = f"{timestamp}{role}{event_type}{json.dumps(payload, sort_keys=True)}{nonce}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


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
    if not event_id:
        return
    emit("ack", role, payload={"event_id": event_id})


def bootup_complete(role):
    """Signal that the agent has finished initial boot (#8695 / #8914).

    Event-driven agents call this after: L1 init done, working-state.md read,
    initial backlog scan complete, Monitor subscription active. The harness
    records the signal on `AgentState.bootup_complete` and exposes it via
    `GET /agents/{role}` for operator / TUI consumption. Informational only —
    no per-role gating, queuing, or dispatch (CONTEXT.md §5.2).

    Fire-and-forget like emit(). Safe to call multiple times.
    """
    if not role:
        return
    emit("bootup-complete", role, payload={})
