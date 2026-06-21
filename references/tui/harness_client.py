"""Harness HTTP data layer for the SquidSquad TUI (#12801, Story 1.2).

Pure, Textual-free functions that fetch and shape the harness HTTP surface
(`GET /status`, `GET /human/queue` — the #8704 endpoint model) into rows the
TUI panels render. Kept dependency-light (stdlib `urllib` only) and split so
the *derivation* logic (work-state, cursor-lag bar) is pure and unit-testable
without a running harness or Textual.

Contract: `.squidsquad/pm/planning/TUI-INTERFACE-DESIGN.md` (operator-approved).
"""

import datetime
import json
import urllib.error
import urllib.request

# --- Work-state vocabulary + colors (contract: operator-locked 2026-06-19) ---
# One activity vocabulary; "active"/"busy" collapsed into "working".
WORK_STATE_WORKING = "working"  # a cycle/task is in flight  → GREEN
WORK_STATE_IDLE = "idle"        # alive but nothing in progress → YELLOW
WORK_STATE_DOWN = "down"        # dead / paused / crashed / unresponsive → RED

WORK_STATE_COLOR = {
    WORK_STATE_WORKING: "green",
    WORK_STATE_IDLE: "yellow",
    WORK_STATE_DOWN: "red",
}

# Intents that mean the agent is not running normally (transitional/stopped).
_DOWN_INTENTS = frozenset({"stopping", "restarting", "stopped"})


def derive_work_state(agent, now):
    """Map a ``/status`` agent dict → ``working`` | ``idle`` | ``down``.

    - **down**: process not ``running``, or intent is stop/restart/stopped.
    - **working**: a cycle is in flight — ``current_cycle`` set OR
      ``in_flight_until`` in the future.
    - **idle**: alive but nothing in progress.

    ``now`` is the current epoch seconds (passed in so this stays pure/testable).
    """
    if agent.get("status") != "running":
        return WORK_STATE_DOWN
    if agent.get("intent") in _DOWN_INTENTS:
        return WORK_STATE_DOWN
    if agent.get("current_cycle") is not None:
        return WORK_STATE_WORKING
    in_flight = agent.get("in_flight_until")
    if in_flight is not None and in_flight > now:
        return WORK_STATE_WORKING
    return WORK_STATE_IDLE


def lag_to_bar(lag, scale=10, width=6):
    """Render the cursor-lag bar: a dashed track with a ``→`` arrow.

    Arrow at the **right** edge = cursor at the head (caught up, lag 0); it
    slides **left** as lag grows; lag ≥ ``scale`` pins it at the far left.
    Returns ``(bar_str, lag_alert)`` where ``lag_alert`` is True when the
    arrow sits in the left third (the "far behind" RED-left-edge alert the
    renderer applies). Pure — the colour is the renderer's job.
    """
    lag = max(0, int(lag))
    frac = min(1.0, lag / scale) if scale > 0 else 0.0
    # arrow index 0..width-1; right edge (width-1) == caught up.
    arrow_idx = round((1.0 - frac) * (width - 1))
    cells = ["-"] * width
    cells[arrow_idx] = "→"  # →
    bar = "[" + "".join(cells) + "]"
    lag_alert = arrow_idx <= (width - 1) // 3  # left third → alert
    return bar, lag_alert


def format_age(epoch, now):
    """Human "time since" for an epoch-seconds timestamp → e.g. ``3s`` /
    ``5m`` / ``2h`` / ``4d``. Returns ``—`` when ``epoch`` is missing or
    unparseable. A future/negative delta clamps to ``0s`` (clock skew is not
    worth surfacing). Pure — ``now`` is passed in so callers stay testable.
    """
    if epoch is None:
        return "—"  # em dash — "no data"
    try:
        delta = int(now) - int(epoch)
    except (TypeError, ValueError):
        return "—"
    if delta < 0:
        delta = 0
    if delta < 60:
        return f"{delta}s"
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}d"


def _iso_to_epoch(value):
    """Parse an ISO-8601 timestamp (e.g. GitHub's ``2026-06-21T00:31:21Z``) →
    epoch seconds, or ``None`` if absent/unparseable. Tolerant of a trailing
    ``Z`` (UTC), which ``datetime.fromisoformat`` rejects before Python 3.11.
    """
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()


def agent_rows(status_json, now):
    """Shape ``GET /status`` JSON → a list of TUI agent rows.

    Each row carries the already-derived display fields so panels render
    without re-deriving: role, work_state (+ color), lag, lag_bar, lag_alert,
    current task, and last-activity epoch.
    """
    rows = []
    for a in status_json.get("agents", []):
        lag = a.get("lag", 0) or 0
        bar, alert = lag_to_bar(lag)
        state = derive_work_state(a, now)
        rows.append({
            "role": a.get("role"),
            "work_state": state,
            "color": WORK_STATE_COLOR[state],
            "current_cycle": a.get("current_cycle"),
            "last_activity_at": a.get("last_activity_at"),
            "last_activity_age": format_age(a.get("last_activity_at"), now),
            "intent": a.get("intent"),
            "lag": lag,
            "lag_bar": bar,
            "lag_alert": alert,
        })
    return rows


def pipeline_counts(status_json):
    """(Placeholder hook) Pipeline panel counts are sourced from the forge,
    not ``/status``; Story 2 wires the real query. Kept here so the data-layer
    surface is discoverable. Returns an empty dict for now."""
    return {}


# Short status label for the Needs-You panel (strip the verbose prefix).
_HUMAN_STATUS_PREFIX = "pending-human-"


def human_queue_rows(human_queue_json, now):
    """Shape ``GET /human/queue`` JSON → display rows for the Needs-You panel.

    The harness already summarizes and orders items (priority high→low, then
    oldest-first); this preserves that order and adds TUI-display fields: a
    short status badge (``review`` / ``setup`` — the ``pending-human-`` prefix
    stripped) and a human ``age`` from ``updated_at``. Pure — ``now`` is passed
    in. Tolerant of a missing/``None`` payload (harness unreachable) → ``[]``.
    """
    if not human_queue_json:
        return []
    rows = []
    for item in human_queue_json.get("items", []):
        status = item.get("status", "") or ""
        status_short = (
            status[len(_HUMAN_STATUS_PREFIX):]
            if status.startswith(_HUMAN_STATUS_PREFIX)
            else status
        )
        rows.append({
            "number": item.get("number"),
            "title": item.get("title", ""),
            "status_short": status_short,
            "role": item.get("role"),
            "priority": item.get("priority"),
            "age": format_age(_iso_to_epoch(item.get("updated_at")), now),
            "url": item.get("url", ""),
        })
    return rows


def fetch_json(base_url, path, *, timeout=2):
    """GET ``base_url + path`` and parse JSON. Returns the parsed object, or
    ``None`` on any transport/parse error (the TUI degrades gracefully to a
    "harness unreachable" state rather than crashing)."""
    url = base_url.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def fetch_status(base_url, *, timeout=2):
    """Fetch ``GET /status`` (or ``None`` if unreachable)."""
    return fetch_json(base_url, "/status", timeout=timeout)


def fetch_human_queue(base_url, *, timeout=2):
    """Fetch ``GET /human/queue`` (the #8704 pending-human-* queue)."""
    return fetch_json(base_url, "/human/queue", timeout=timeout)
