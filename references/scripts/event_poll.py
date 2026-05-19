#!/usr/bin/env python3
"""Poll harness event bus and stream events to stdout (#8915 / #7630 2-5).

Designed for use with the Claude Code Monitor tool. Queries
`GET /events?since=<cursor>&role=<role>`, writes one JSON object per line
to stdout, advances the cursor in `.squidsquad/<role>/working-state.md`.

Cursor resolution order:
  1. `--since N` flag (explicit override)
  2. `Last Processed Event ID: <id>` line in `working-state.md`
  3. Empty (server defaults to `0`); a warning is written to stderr

Retry policy on transient errors (`ConnectionError`, `Timeout`, HTTP 5xx):
exponential backoff `[1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300, ...]`
capped at 300s — matches the boot-time retry policy (CONTEXT.md §3.1 step 5).
HTTP 4xx responses are treated as caller faults: not retried, non-zero exit.

Usage:
    python event_poll.py <role>                       Poll once, exit
    python event_poll.py <role> --since 123            Override cursor
    python event_poll.py <role> --wait 5               HTTP timeout = 5s, loop forever
    python event_poll.py <role> --target               Use /events/for/<role>

Stdout: clean JSON only (one object per line). Errors go to stderr.
Exit codes: 0 = events found / loop exit, 1 = no events, 2 = invocation error.
"""

import argparse
import http.client
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

_DEFAULT_HTTP_TIMEOUT = 2.0
_BACKOFF_CAP = 300
_CURSOR_LINE_PREFIX = "- **Last Processed Event ID**:"


def _discover_port():
    port_file = SQUID_DIR / ".harness-port"
    if port_file.exists():
        try:
            return int(port_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass
    return None


def _working_state_path(role):
    return SQUID_DIR / role / "working-state.md"


def _read_cursor_from_working_state(role):
    path = _working_state_path(role)
    if not path.exists():
        return ""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(_CURSOR_LINE_PREFIX):
                return line.split(":", 1)[1].strip()
    except (OSError, UnicodeDecodeError):
        # Corrupted working-state.md (non-UTF-8 bytes from disk bit-rot or
        # external mangling) must not crash the long-running poll loop.
        pass
    return ""


def _resolve_cursor(role, since_arg):
    """Resolve the cursor following the spec's three-step order."""
    if since_arg is not None:
        return str(since_arg)
    cursor = _read_cursor_from_working_state(role)
    if cursor:
        return cursor
    print(
        f"WARNING: no cursor for role={role!r} (no --since flag, "
        f"no 'Last Processed Event ID' in working-state.md); defaulting to 0",
        file=sys.stderr,
    )
    return ""


def _write_cursor_atomic(role, cursor):
    """Update `Last Processed Event ID` in working-state.md atomically.

    Writes to `<path>.tmp` then `os.replace` so a reader never sees a
    half-written file (CONTEXT.md atomic-update rule). Returns True on
    success, False on filesystem failure — the caller MUST gate event
    emission on the result to avoid silent re-delivery on the next poll.
    """
    path = _working_state_path(role)
    new_line = f"{_CURSOR_LINE_PREFIX} {cursor}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines(keepends=False)
            replaced = False
            for i, line in enumerate(lines):
                if line.startswith(_CURSOR_LINE_PREFIX):
                    lines[i] = new_line
                    replaced = True
                    break
            if not replaced:
                lines.append(new_line)
            body = "\n".join(lines)
            if text.endswith("\n"):
                body += "\n"
        else:
            body = new_line + "\n"
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(path)
        return True
    except (OSError, UnicodeDecodeError) as e:
        print(f"ERROR: cursor write failed for role={role!r}: {e}",
              file=sys.stderr)
        return False


def _backoff_seconds(attempt):
    """Capped doubling: 1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300, ..."""
    return min(2 ** attempt, _BACKOFF_CAP)


def _build_url(port, role, cursor, limit, target_mode):
    if target_mode:
        params = {"limit": limit}
        if cursor:
            params["since"] = cursor
        return (
            f"http://127.0.0.1:{port}/events/for/{urllib.parse.quote(role)}"
            f"?{urllib.parse.urlencode(params)}"
        )
    params = {"role": role, "limit": limit}
    if cursor:
        params["since"] = cursor
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


def poll(role, since=None, limit=50, target_mode=False,
         http_timeout=_DEFAULT_HTTP_TIMEOUT, sleep=time.sleep):
    """Poll for new events with retry/backoff.

    Returns the list of events (possibly empty) on success, or ``None`` if
    a fatal (non-retryable) error occurred. Successful response advances
    the cursor atomically, one write per event (spec §3.5).
    """
    port = _discover_port()
    if port is None:
        print("ERROR: harness port not found", file=sys.stderr)
        return None

    cursor = _resolve_cursor(role, since)
    url = _build_url(port, role, cursor, limit, target_mode)

    attempt = 0
    while True:
        payload, retryable, fatal_msg = _fetch_once(url, http_timeout)
        if payload is not None:
            events = payload.get("events", [])
            if payload.get("evicted"):
                # Cursor predates the harness's retained window (#9331).
                # Warn once per response naming the safe re-anchor + an
                # operator-forensic hint on how many events have rolled
                # off the deque since boot. Then re-anchor the cursor
                # to `oldest_id` BEFORE processing events.
                #
                # Re-anchoring up front is needed because on the
                # `/events/for/{role}` endpoint, the role filter can
                # strip every event in the batch even when the deque
                # is non-empty — leaving `events == []` with the
                # cursor stuck on the (still-evicted) stale id and the
                # warning repeating every poll. Anchoring to
                # `oldest_id` first guarantees forward progress; if
                # events DO survive the filter, the per-event advance
                # below will overwrite the cursor to a later id, which
                # is fine (events are oldest-first; their ids are
                # >= oldest_id).
                oldest_id = payload.get("oldest_id")
                hint = payload.get("evicted_count_hint")
                # Locked format per CONTEXT-9331 §4 — kept verbatim so
                # QA's grep-based assertions stay deterministic across
                # rewords.
                print(
                    f"[event_poll] EVICTION: cursor predates retained "
                    f"window — advancing to {oldest_id}, "
                    f"~{hint} events evicted",
                    file=sys.stderr,
                )
                if oldest_id and not _write_cursor_atomic(role, str(oldest_id)):
                    # Same fatal-on-disk-fail policy as the per-event
                    # advance below — silently retrying would burn CPU
                    # forever against an unwritable cursor file.
                    return None
            for event in events:
                if not isinstance(event, dict):
                    print(f"WARNING: malformed event (not an object); "
                          f"skipping: {event!r}", file=sys.stderr)
                    continue
                event_id = event.get("id")
                if not event_id:
                    # No id ⇒ cursor cannot advance past this event, so
                    # emitting it would cause infinite re-delivery on the
                    # next poll. Skip and warn.
                    print(f"WARNING: event has no id; skipping: {event!r}",
                          file=sys.stderr)
                    continue
                if not _write_cursor_atomic(role, str(event_id)):
                    # Cursor advance failed (disk full / permission). Return
                    # None so callers treat this like any other fatal error
                    # (single-shot: exit 2; --wait loop: exit 2). Operator
                    # intervention required — silently looping at HTTP-rate
                    # would burn CPU and re-fetch the same events forever.
                    return None
                print(json.dumps(event), flush=True)
            return events
        if not retryable:
            print(f"ERROR: {fatal_msg}", file=sys.stderr)
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
        description="Stream harness events as JSON-lines to stdout.",
    )
    p.add_argument("role")
    p.add_argument("--since", type=str, default=None,
                   help="Override cursor (default: read working-state.md).")
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
        events = poll(args.role, since=args.since, limit=args.limit,
                      target_mode=args.target)
        if events is None:
            sys.exit(2)
        sys.exit(0 if events else 1)

    http_timeout = args.wait
    since = args.since
    while True:
        events = poll(args.role, since=since, limit=args.limit,
                      target_mode=args.target, http_timeout=http_timeout)
        if events is None:
            sys.exit(2)
        # --since is a one-time bootstrap; subsequent iterations must
        # read the advanced cursor from working-state.md or they will
        # re-fetch the same events forever.
        since = None
        if not events:
            time.sleep(http_timeout)


if __name__ == "__main__":
    main()
