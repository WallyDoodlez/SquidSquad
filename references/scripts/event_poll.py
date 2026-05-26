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


def _resolve_squid_dir() -> Path:
    """#10265: honor SQUIDSQUAD_DIR env var so isolated test harnesses
    can be discovered by event_poll subprocesses without the live
    .harness-port file getting in the way. Without this, e2e tests
    that spawn event_poll.py have to write their port to the LIVE
    `.squidsquad/.harness-port` (which other SquidSquad processes
    then route to). Matches harness._resolve_squidsquad_dir and
    event_bus._resolve_squid_dir."""
    import os
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
         http_timeout=_DEFAULT_HTTP_TIMEOUT, sleep=time.sleep,
         max_consecutive_failures=None):
    """Poll for new events with retry/backoff.

    Returns the list of events (possibly empty) on success, or ``None`` if
    a fatal (non-retryable) error occurred, OR if ``max_consecutive_failures``
    transient errors accrue without an intervening success (#9742).
    Successful response advances the cursor atomically, one write per event
    (spec §3.5).

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

    cursor = _resolve_cursor(role, since)
    url = _build_url(port, role, cursor, limit, target_mode)

    attempt = 0
    consecutive_failures = 0
    while True:
        payload, retryable, fatal_msg = _fetch_once(url, http_timeout)
        if payload is not None:
            events = payload.get("events", [])
            evicted = bool(payload.get("evicted"))
            oldest_id = payload.get("oldest_id") if evicted else None
            if evicted:
                # Cursor predates the harness's retained window (#9331).
                # Warn once per response, naming the safe re-anchor + an
                # operator-forensic hint on how many events have rolled
                # off the deque since boot. The cursor re-anchor itself
                # happens AFTER the per-event loop (#9740) — see the
                # post-loop guard below.
                #
                # Why the warning fires here (pre-loop) but the write
                # happens post-loop: on the `/events/for/{role}` endpoint
                # the role filter can strip every event in the batch even
                # when the deque is non-empty, leaving `events == []`
                # with the cursor stuck on the (still-evicted) stale id
                # and the warning repeating every poll. Anchoring to
                # `oldest_id` after we know whether any events survived
                # avoids the #9740 race: if some per-event advance fails
                # mid-batch we leave the cursor at the last successfully
                # emitted event id (not at `oldest_id`, whose event was
                # never emitted), so on retry that emitted event is not
                # skipped. If `events == []`, the post-loop guard writes
                # `oldest_id` to guarantee forward progress for the next
                # poll. Warning format locked per CONTEXT-9331 §4.
                hint = payload.get("evicted_count_hint")
                print(
                    f"[event_poll] EVICTION: cursor predates retained "
                    f"window — advancing to {oldest_id}, "
                    f"~{hint} events evicted",
                    file=sys.stderr,
                )
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
                # #9898: emit BEFORE advancing the cursor. Previously the
                # order was reversed — cursor advanced, then print(). A crash
                # between the two (most plausibly BrokenPipeError from the
                # flushed print when Monitor's downstream pipe drops) would
                # leave the cursor past an unemitted event → silent loss
                # (at-most-once with no consumer-side recovery).
                #
                # Emit-then-advance makes the contract at-least-once: a crash
                # between print() and _write_cursor_atomic() means the next
                # poll re-fetches the just-emitted event, which Monitor /
                # downstream consumers can dedupe by event id. Idempotent
                # consumers are already required by the #9740 eviction-
                # re-anchor path (where the cursor moves to oldest_id while
                # earlier events in the same batch were already emitted), so
                # this is not a new requirement on consumers — it's the
                # contract this poll loop was already implicitly relying on.
                #
                # When #9873-B lands, this whole branch is replaced by an
                # ack-cursor emit to the harness. Until then this ordering
                # closes the loss window.
                print(json.dumps(event), flush=True)
                if not _write_cursor_atomic(role, str(event_id)):
                    # Cursor advance failed (disk full / permission). Return
                    # None so callers treat this like any other fatal error
                    # (single-shot: exit 2; --wait loop: exit 2). Operator
                    # intervention required — silently looping at HTTP-rate
                    # would burn CPU and re-fetch the same events forever.
                    return None
            # #9740: eviction re-anchor (post-loop). Only write `oldest_id`
            # when the batch was empty AFTER role-filtering — otherwise the
            # per-event advance above has already left the cursor at a valid
            # id >= oldest_id. If `evicted: true` was returned without a
            # truthy `oldest_id`, treat as fatal (harness contract violation,
            # CONTEXT-9740 D4) — return None so the operator sees the
            # failure rather than continuing on a stuck cursor.
            if evicted and not events:
                if not oldest_id:
                    return None
                if not _write_cursor_atomic(role, str(oldest_id)):
                    return None
            return events
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
        # #9742: cap consecutive transient failures inside each poll() call
        # so Monitor exits on sustained harness loss. The harness auto-reboot
        # intent path picks up from the resulting session exit.
        events = poll(args.role, since=since, limit=args.limit,
                      target_mode=args.target, http_timeout=http_timeout,
                      max_consecutive_failures=_WAIT_MAX_CONSECUTIVE_FAILURES)
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
