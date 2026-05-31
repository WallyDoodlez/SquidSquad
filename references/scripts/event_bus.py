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


# Module-level capture is kept for backwards compatibility with callers
# that grep this attribute (e.g. ``test_9398_squidsquad_dir_env_var.py``
# expects ``event_bus.SQUID_DIR`` to be the value resolved when the
# module loads, and ``patch.object(event_bus, 'SQUID_DIR', …)`` is used
# by ``test_event_bus.py`` to redirect emits to a tmp dir). Internal
# call sites that need a runtime ``SQUIDSQUAD_DIR`` read the env var at
# call time and fall back to this ``SQUID_DIR`` — see ``_discover_port``
# for the pattern. ``_resolve_squid_dir()`` itself is only used to
# initialise ``SQUID_DIR`` here at import time; it is intentionally NOT
# re-called from ``_discover_port`` because its fallback is
# ``REPO_ROOT / ".squidsquad"`` rather than the patchable
# ``SQUID_DIR``, which would silently break the existing test fixtures
# (#10516).
SQUID_DIR = _resolve_squid_dir()

# Timeout: 500ms — never blocks agent cycle
_TIMEOUT = 0.5


def _discover_port():
    """Discover harness port via .harness-port file (#7630 P-2).

    Reads directly from local .squidsquad/.harness-port. The harness
    distributes the port file to all clone directories at boot
    (harness.py lifespan), so parent-dir walk is unnecessary.

    Resolution order (#10516):

    1. ``SQUIDSQUAD_DIR`` env var if set at call time — honors a runtime
       override without requiring an ``importlib`` reload.
    2. Module-level ``SQUID_DIR`` — the value captured when the module
       loaded; what tests that ``patch.object(event_bus, 'SQUID_DIR', …)``
       expect to control.

    Returns port number or None if not discoverable.
    """
    raw = (os.environ.get("SQUIDSQUAD_DIR") or "").strip()
    squid_dir = Path(raw).expanduser() if raw else SQUID_DIR
    port_file = squid_dir / ".harness-port"
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


def ack_cursor(event_id, role):
    """Advance the harness consumer cursor past ``event_id`` for ``role``
    (#9873-A D10 / AC-10).

    Emits ``event_type="ack-cursor"`` with payload ``{event_id, role}``. The
    harness inline handler at ``harness.py`` calls ``advance_cursor`` (off
    the asyncio loop via ``asyncio.to_thread``), which:

    - rejects (silently) if ``event_id`` is no longer in the retained deque
      (FIFO-evicted) — AC-8 / AC-16
    - rejects (silently) if ``event_id`` appears earlier in the deque than
      the current cursor (out-of-order delivery) — AC-17
    - otherwise advances ``_cursors[role]`` and persists

    No-op when ``event_id`` or ``role`` is empty (defensive guard, no
    exception). Fire-and-forget — silent on transport failure.
    """
    if not event_id or not role:
        return
    emit("ack-cursor", role, payload={"event_id": event_id, "role": role})


def ack_stop(event_id, result, role=None):
    """Acknowledge a stop request from the harness (#9873-A D10 / AC-11).

    Emits ``event_type="ack-stop"`` with payload ``{event_id, result}``. The
    harness inline handler preserves the prior ``ack`` stop-confirmed
    behavior at AC-12 — when ``result == "stop-confirmed"`` and the agent is
    in ``INTENT_STOPPING``, the harness persists agent state without
    resetting ``intent_set_at`` (which would extend the 60s force-kill
    window per CONTEXT-4792 §3.3 Q7).

    The agent's role is normally read from ``SQUIDSQUAD_ROLE`` (set by
    ``thin_launcher.py`` at spawn time). Callers may pass ``role`` explicitly
    to override the env (#9902 F3) — useful for test harnesses and out-of-band
    callers that don't set the env var. No-op when ``event_id`` or ``result``
    is empty, or when no role can be resolved from either source.
    Fire-and-forget.
    """
    if not event_id or not result:
        return
    if role is None:
        role = (os.environ.get("SQUIDSQUAD_ROLE") or "").strip()
    if not role:
        return
    emit("ack-stop", role, payload={"event_id": event_id, "result": result})
