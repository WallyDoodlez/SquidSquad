#!/usr/bin/env python
"""#12443 — activity-heartbeat poster (HARNESS-ARCH §15.1, #12271 slice b).

Two roles:

1. **Claude Code command hook** — wired per-clone (by compose) as the
   ``PostToolUse`` / ``PostToolUseFailure`` hook with ``async: true``, so Claude
   Code backgrounds it and IGNORES its exit code/output: it can never block,
   delay, or fail the agent's tool call (AC2). Run that way it reads the agent
   role from the inherited ``$SQUIDSQUAD_ROLE`` env var and the hook payload
   (``tool_name`` / ``hook_event_name``) from stdin, then POSTs a lightweight
   heartbeat to the harness ``POST /hooks/activity``.

2. **Importable poster** — ``cycle_post`` imports ``post_activity()`` to emit a
   heartbeat at cycle end (AC3), passing its own liveness-aware harness port.

Why a command hook and not a native ``type: http`` hook: native http hooks are
SYNCHRONOUS (they block the tool call; their default timeout is 600s) and only
``type: command`` hooks support ``async``/fire-and-forget — verified against the
Claude Code hook API (#12443). These fire on EVERY tool call, so they MUST be
async command hooks. (SessionEnd, slice a, is once-per-session, so it stays a
native http hook.)

Fail-open contract (HARNESS-ARCH §15.5 / §16.3): NOTHING here raises and the
process ALWAYS exits 0 — a telemetry hook must never stall, fail, or error the
agent's work.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_DEFAULT_PORT = 7373
# Bound the POST. ``async: true`` already keeps the hook off the agent's
# critical path, so this only caps how long this background process lingers.
_HEARTBEAT_TIMEOUT = 2


def _repo_root() -> Path:
    # references/scripts/activity_hook.py → repo root is three parents up.
    return Path(__file__).resolve().parent.parent.parent


def _discover_port() -> int:
    """Best-effort harness port: this clone's ``.squidsquad/.harness-port``,
    else the default 7373. No liveness probe — fail-open means a wrong/dead
    port just yields a swallowed connection error and a no-op heartbeat."""
    try:
        txt = (_repo_root() / ".squidsquad" / ".harness-port").read_text(
            encoding="utf-8").strip()
        return int(txt)
    except (OSError, ValueError):
        return _DEFAULT_PORT


def post_activity(role, event, tool=None, phase=None, port=None,
                  timeout=_HEARTBEAT_TIMEOUT) -> bool:
    """POST an activity heartbeat to the harness. Returns True on a 2xx
    response, False otherwise. NEVER raises — every error (no role, unreachable
    harness, timeout, bad response) is swallowed (fail-open telemetry)."""
    if not role:
        return False
    if port is None:
        port = _discover_port()
    url = f"http://127.0.0.1:{port}/hooks/activity"
    body = {"event": event}
    if tool:
        body["tool"] = tool
    if phase:
        body["phase"] = phase
    try:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "X-Agent-Role": role},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def main() -> int:
    """Command-hook entrypoint: role from env, payload from stdin → heartbeat."""
    role = (os.environ.get("SQUIDSQUAD_ROLE") or "").strip()
    payload = {}
    try:
        raw = sys.stdin.read()
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
    except Exception:
        payload = {}
    event = payload.get("hook_event_name") or "PostToolUse"
    tool = payload.get("tool_name")
    post_activity(role, event, tool=tool)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Absolute fail-open: a telemetry hook must never surface a non-zero
        # exit to Claude Code, even on an unforeseen error.
        sys.exit(0)
