#!/usr/bin/env python3
"""Poll harness event bus and emit a wake NUDGE to stdout (#8915 / #11329).

Designed for use with the Claude Code Monitor tool. Queries
`GET /events/for/<role>?since=<hwm>` and writes a single literal `NUDGE\n`
line to stdout whenever new events arrive past its high-water-mark. That
stdout is wired to the Monitor tool's stdin, waking the Claude session.

Model B (#11329 — per AGENT-RUNTIME.md §8.0/§8.1): `event_poll` is a pure
*wake signal*. It does **not** own the cursor and does **not** emit event
payloads:

  - The cursor is harness-owned in `.squidsquad/.event-state.json` and is
    advanced by the AGENT posting `ack-cursor` per tended event. `event_poll`
    never reads or writes it.
  - The nudge carries no payload. On waking, the agent does its own
    `GET /events/for/{role}?since=<cursor>` and walks events with per-event
    `ack-cursor` posts (see `cursor-management.md`).

`event_poll` tracks only a private in-memory **high-water-mark** (the newest
event id it has seen) so it can edge-trigger one nudge per new batch instead
of re-nudging the same events every poll. The hwm is NOT the cursor: it is
unpersisted, resets to empty on `event_poll` restart, and a stale/empty hwm
only ever produces a harmless extra NUDGE — the agent's GET-since-cursor
returns `[]` and it idles again (§8.0).

Cursor resolution order for the first poll's `since`:
  1. `--since N` flag (explicit override — seeds the initial hwm)
  2. Empty (server returns recent events; a single nudge fires if any exist)

Retry policy on transient errors (`ConnectionError`, `Timeout`, HTTP 5xx):
exponential backoff `[1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300, ...]`
capped at 300s — matches the boot-time retry policy (CONTEXT.md §3.1 step 5).
HTTP 4xx responses are treated as caller faults: not retried, non-zero exit.

Usage:
    python event_poll.py <role>                       Poll once, exit
    python event_poll.py <role> --since 123            Seed initial hwm
    python event_poll.py <role> --wait 5               HTTP timeout = 5s, loop forever
    python event_poll.py <role> --target               Use /events/for/<role>

Stdout: a literal `NUDGE\n` per new batch. Errors/diagnostics go to stderr.
Exit codes: 0 = nudge emitted / loop exit, 1 = no events, 2 = invocation error.
"""

import argparse
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent


def _resolve_squid_dir() -> Path:
    """#10265: honor SQUIDSQUAD_DIR env var so isolated test harnesses
    can be discovered by event_poll subprocesses without the live
    .harness-port file getting in the way. Without this, e2e tests
    that spawn event_poll.py have to write their port to the LIVE
    `.squidsquad/.harness-port` (which other SquidSquad processes
    then route to). Matches harness._resolve_squidsquad_dir and
    event_bus._resolve_squid_dir."""
    raw = (os.environ.get("SQUIDSQUAD_DIR") or "").strip()
    if not raw:
        return REPO_ROOT / ".squidsquad"
    return Path(raw).expanduser()


SQUID_DIR = _resolve_squid_dir()

_DEFAULT_HTTP_TIMEOUT = 2.0
_BACKOFF_CAP = 300
# #9742 D2: bounded retry ceiling for --wait mode. 10 retries with the
# existing capped-doubling backoff (cap 300s) gives sufficient tolerance
# for harness restarts (~15-30s in practice) without leaving Monitor
# wedged for hours on a genuinely dead harness.
_WAIT_MAX_CONSECUTIVE_FAILURES = 10
_NUDGE_LINE = "NUDGE"


def _discover_port():
    port_file = SQUID_DIR / ".harness-port"
    if port_file.exists():
        try:
            return int(port_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass
    return None


def _backoff_seconds(attempt):
    """Capped doubling: 1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300, ..."""
    return min(2 ** attempt, _BACKOFF_CAP)


def _build_url(port, role, since, limit, target_mode):
    if target_mode:
        params = {"limit": limit}
        if since:
            params["since"] = since
        return (
            f"http://127.0.0.1:{port}/events/for/{urllib.parse.quote(role)}"
            f"?{urllib.parse.urlencode(params)}"
        )
    params = {"role": role, "limit": limit}
    if since:
        params["since"] = since
    return f"http://127.0.0.1:{port}/events?{urllib.parse.urlencode(params)}"


def _fetch_once(url, http_timeout):
    """Single HTTP attempt. Returns (payload|None, retryable, fatal_message).

    - (dict, False, None)        — success; payload carries ``events`` plus
                                   optional ``evicted``/``oldest_id``/
                                   ``evicted_count_hint`` keys (#9331)
    - (None, True, reason)       — transient (retry with backoff)
    - (None, False, reason)      — fatal (4xx or invalid body); caller exits
    """
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            try:
                data = json.loads(resp.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                return None, False, f"invalid JSON from harness: {e}"
        if not isinstance(data, dict):
            return None, False, f"harness payload not an object: {type(data).__name__}"
        events = data.get("events", [])
        if not isinstance(events, list):
            return None, False, f"harness 'events' not a list: {type(events).__name__}"
        return data, False, None
    except urllib.error.HTTPError as e:
        if 500 <= e.code < 600:
            return None, True, f"HTTP {e.code}"
        return None, False, f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError, OSError,
            http.client.HTTPException) as e:
        # IncompleteRead / connection drop mid-body inherits from
        # HTTPException, not URLError — caught here so a flapping
        # connection cannot crash a long-running --wait loop.
        return None, True, f"{type(e).__name__}: {e}"


def _newest_id(events):
    """Return the id of the last event in the batch that carries one.

    Used to advance the local high-water-mark. Events without an id cannot
    move the hwm (they are still nudge-worthy — finding any event triggers a
    nudge — but they cannot serve as a `since` anchor). Walk from the end so
    the hwm lands on the newest anchorable id.

    Id contract: harness event ids are **non-empty strings** (hex / prefixed,
    e.g. ``ev-assigned-to-...``). The truthiness check below is deliberate —
    it rejects both ``None`` (JSON null) and ``""``, the two values that are
    invalid as a `since` anchor (an empty `since` is dropped by `_build_url`,
    so anchoring on it would silently re-read the whole window). A numeric
    ``0`` id cannot occur under the harness contract; were it ever introduced
    it would also need handling in the `since or ""` URL path, so the fix
    belongs at the id-generation boundary, not here.
    """
    for event in reversed(events):
        if isinstance(event, dict):
            eid = event.get("id")
            if eid:
                return str(eid)
    return ""


def poll(role, since=None, limit=50, target_mode=False,
         http_timeout=_DEFAULT_HTTP_TIMEOUT, sleep=time.sleep,
         max_consecutive_failures=None):
    """Poll once for events past ``since``; emit a NUDGE if any are found.

    Returns ``(events, next_since)`` on success, or ``None`` if a fatal
    (non-retryable) error occurred, OR if ``max_consecutive_failures``
    transient errors accrue without an intervening success (#9742).

    - ``events`` is the filtered batch the harness returned (possibly empty).
    - ``next_since`` is the local high-water-mark to use on the next poll:
      the newest event id when events were found, ``oldest_id`` when the
      harness reported an eviction gap with no surviving events, or the
      input ``since`` unchanged when nothing new arrived.

    A single literal ``NUDGE\\n`` is written to stdout when the batch is
    non-empty OR an eviction gap is reported — the agent then does its own
    ``GET /events/for`` + per-event ``ack-cursor`` (model B, #11329). This
    function never writes the cursor; the harness owns it.

    ``max_consecutive_failures``: optional cap on transient connection
    failures within a single ``poll()`` call. ``None`` (default) preserves
    the original unlimited-retry behavior for single-shot mode. The
    ``--wait`` outer loop passes 10 per CONTEXT-9742 D2, so a sustained
    harness outage causes Monitor (and therefore the agent session) to exit
    after ~10 backoff cycles instead of hanging forever.
    """
    port = _discover_port()
    if port is None:
        print("ERROR: harness port not found", file=sys.stderr)
        return None

    url = _build_url(port, role, since or "", limit, target_mode)

    attempt = 0
    consecutive_failures = 0
    while True:
        payload, retryable, fatal_msg = _fetch_once(url, http_timeout)
        if payload is not None:
            events = payload.get("events", [])
            evicted = bool(payload.get("evicted"))
            oldest_id = payload.get("oldest_id") if evicted else None

            # Drop malformed (non-dict) entries with a warning so a bad
            # payload can't crash the long-running --wait loop. They do not
            # block the nudge — any surviving event still wakes the agent.
            clean = []
            for event in events:
                if not isinstance(event, dict):
                    print(f"WARNING: malformed event (not an object); "
                          f"skipping: {event!r}", file=sys.stderr)
                    continue
                clean.append(event)

            # #9740/#11329: eviction with an empty batch AND no anchor
            # (falsy oldest_id) is a harness-contract violation (degraded /
            # cold-start deque). Return None (fatal) so main() exits 2 and
            # the harness auto-reboot path recovers — rather than holding the
            # stale hwm and re-nudging the same unrecoverable gap every poll
            # forever. This is the escape hatch the pre-migration #9740 guard
            # provided; the model-B hwm cannot otherwise advance past it.
            if evicted and not clean and not oldest_id:
                print("ERROR: eviction with empty batch and no oldest_id "
                      "anchor (harness contract violation); giving up",
                      file=sys.stderr)
                return None

            if evicted:
                # Cursor predates the harness's retained window (#9331).
                # In model B the AGENT performs the eviction recovery
                # (forge-read + a single ack-cursor(oldest_id)); event_poll
                # only nudges so the agent wakes to do it. We still advance
                # our LOCAL hwm past the gap (to oldest_id when the batch is
                # empty) so we don't re-nudge the same evicted range forever.
                hint = payload.get("evicted_count_hint")
                print(
                    f"[event_poll] EVICTION: cursor predates retained "
                    f"window — nudging agent to recover past {oldest_id}, "
                    f"~{hint} events evicted",
                    file=sys.stderr,
                )

            if clean or evicted:
                # Single edge-triggered wake. No payload — the agent does
                # GET /events/for + per-event ack-cursor on waking (§8.1).
                print(_NUDGE_LINE, flush=True)

            next_since = _newest_id(clean)
            if not next_since:
                # No anchorable id in the batch. On an eviction gap fall back
                # to oldest_id so the hwm still moves past the evicted range;
                # otherwise keep the prior since (nothing new to anchor on).
                next_since = str(oldest_id) if oldest_id else (since or "")
            return clean, next_since

        if not retryable:
            print(f"ERROR: {fatal_msg}", file=sys.stderr)
            return None
        consecutive_failures += 1
        if (max_consecutive_failures is not None
                and consecutive_failures >= max_consecutive_failures):
            # #9742: bounded retry ceiling so Monitor exits on sustained
            # harness loss instead of hanging forever. Returning None
            # makes the --wait outer loop sys.exit(2), which thin_launcher
            # then catches via the harness auto-reboot intent path.
            print(
                f"ERROR: harness unreachable after {consecutive_failures} "
                f"consecutive transient errors (last: {fatal_msg}); "
                f"giving up",
                file=sys.stderr,
            )
            return None
        delay = _backoff_seconds(attempt)
        print(
            f"WARNING: harness transient error ({fatal_msg}); "
            f"retrying in {delay}s",
            file=sys.stderr,
        )
        sleep(delay)
        attempt += 1


def _parse_args(argv):
    p = argparse.ArgumentParser(
        prog="event_poll.py",
        description="Emit a wake NUDGE to stdout when harness events arrive.",
    )
    p.add_argument("role")
    p.add_argument("--since", type=str, default=None,
                   help="Seed the initial high-water-mark (default: empty).")
    p.add_argument("--wait", type=float, default=None,
                   help="HTTP timeout in seconds. When set, run in a long-poll "
                        "loop instead of exiting after one poll.")
    p.add_argument("--target", action="store_true",
                   help="Use /events/for/<role> targeted endpoint.")
    p.add_argument("--limit", type=int, default=50)
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    if args.wait is not None and args.wait <= 0:
        print(f"ERROR: --wait must be positive (got {args.wait})",
              file=sys.stderr)
        sys.exit(2)

    if args.wait is None:
        result = poll(args.role, since=args.since, limit=args.limit,
                      target_mode=args.target)
        if result is None:
            sys.exit(2)
        events, _ = result
        sys.exit(0 if events else 1)

    http_timeout = args.wait
    since = args.since
    while True:
        # #9742: cap consecutive transient failures inside each poll() call
        # so Monitor exits on sustained harness loss. The harness auto-reboot
        # intent path picks up from the resulting session exit.
        result = poll(args.role, since=since, limit=args.limit,
                      target_mode=args.target, http_timeout=http_timeout,
                      max_consecutive_failures=_WAIT_MAX_CONSECUTIVE_FAILURES)
        if result is None:
            sys.exit(2)
        events, since = result
        if not events:
            time.sleep(http_timeout)


if __name__ == "__main__":
    main()
