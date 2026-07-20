#!/usr/bin/env python3
"""SquidSquad event-mode periodic-driver state machine (#12506).

Deterministic lifecycle for the idle-work scheduler defined in
``AGENT-RUNTIME`` §8.6.1. The *scheduling* of a self-wake is an agent tool
call (prose — see ``idle-cooldown-loop.md``); this module owns the
*decisions* — when to arm, scan, cancel, and re-arm — so they are
unit-testable and identical across every event-mode agent.

Why a script and not prose: the driver's correctness conditions (lazy enable,
bounded burst, re-arm + counter reset, config consumption) are exactly the
#12506 acceptance criteria. Encoding them deterministically here lets them be
tested; the probabilistic agent only has to map each returned ``action`` to
the matching scheduling tool call.

State file (per alias): ``.squidsquad/<alias>/.subloop-driver.json``::

    {"armed": bool, "scan_count": int, "last_run": "<iso8601>"|null}

Config (read via ``config.py``, graceful defaults per §8.6.1):
  - ``Idle Scan Burst`` (``idle-scan-burst``, default 3) — max scans per
    sustained-idle burst before the driver cancels itself.
  - ``Improvement Scan Cool-Down`` (``improvement-scan-cool-down``, default
    ``30m``) — minutes between idle scans; tolerant of a bare integer or an
    ``m`` suffix (existing installs carry ``30``; #12506 moves it to ``30m``).

CLI (agent-facing — the agent maps each ``action`` to a scheduling tool call):
  arm <alias>                              ensure armed (lazy first idle)
  tick <alias> --drained BOOL [--now ISO]  driver-tick decision
  record-scan <alias> [--now ISO]          record that a scan just ran
  reidle <alias>                           re-arm + reset after forge work
  status <alias>                           dump state JSON

Every command prints a single JSON object to stdout.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(SCRIPT_DIR))
from shared_fs import atomic_write_text  # #10007 — atomic state writes
import config as _config

_DEFAULT_STATE = {"armed": False, "scan_count": 0, "last_run": None}


# --------------------------------------------------------------------------
# Config readers (tolerant; graceful defaults per §8.6.1)
# --------------------------------------------------------------------------

def idle_scan_burst():
    """Max idle scans per sustained-idle burst (``Idle Scan Burst``, default 3)."""
    raw = _config.get_field("idle-scan-burst")
    try:
        val = int(str(raw).strip())
        return val if val > 0 else 3
    except (TypeError, ValueError):
        return 3


def cooldown_minutes():
    """Minutes between idle scans (``Improvement Scan Cool-Down``, default 30).

    Tolerant of a bare integer (``30`` — legacy installs) or an ``m`` suffix
    (``30m`` — the #12506 form). An unparseable/empty value falls back to 30.
    """
    raw = _config.get_field("improvement-scan-cool-down")
    if raw is None:
        return 30
    s = str(raw).strip().lower()
    if s.endswith("m"):
        s = s[:-1].strip()
    try:
        val = int(s)
        return val if val > 0 else 30
    except ValueError:
        return 30


# --------------------------------------------------------------------------
# State I/O
# --------------------------------------------------------------------------

def _state_path(alias):
    return REPO_ROOT / ".squidsquad" / alias / ".subloop-driver.json"


def read_state(alias):
    """Return the driver state for ``alias``, defaulting fields if absent/corrupt.

    Defends against both structural corruption (missing file, invalid JSON,
    non-dict) and *type* corruption within otherwise-valid JSON (e.g. a
    hand-edited ``"scan_count": "2"`` or ``"last_run": 1700000000``): each
    field is coerced to its expected type, and any coercion failure falls the
    whole state back to the default rather than crashing a downstream caller.
    """
    path = _state_path(alias)
    if not path.exists():
        return dict(_DEFAULT_STATE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return dict(_DEFAULT_STATE)
    if not isinstance(data, dict):
        return dict(_DEFAULT_STATE)
    state = dict(_DEFAULT_STATE)
    try:
        if "armed" in data:
            # #13722: bare bool(data["armed"]) coerced a hand-edited
            # {"armed": "false"} (JSON string) to True -- Python's
            # bool("false") == True gotcha, the exact opposite of an
            # operator's evident intent. Only an exact JSON `true` counts as
            # armed; any other type (string, int, etc.) is treated as
            # corruption and falls to False -- the safer failure direction
            # for an idle-scan scheduler (a wrongly-disarmed driver just
            # re-arms on the next idle wake; a wrongly-armed one keeps
            # scanning against the operator's intent).
            state["armed"] = data["armed"] is True
        if "scan_count" in data:
            state["scan_count"] = int(data["scan_count"])
        if "last_run" in data:
            lr = data["last_run"]
            state["last_run"] = None if lr is None else str(lr)
    except (TypeError, ValueError):
        return dict(_DEFAULT_STATE)
    return state


def write_state(alias, state):
    path = _state_path(alias)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(state, indent=2) + "\n")


# --------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------

def _now(now=None):
    if now is None:
        return datetime.datetime.now(datetime.timezone.utc)
    if isinstance(now, datetime.datetime):
        return now
    return _parse_iso(str(now))


def _parse_iso(s):
    dt = datetime.datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _iso(dt):
    return dt.astimezone(datetime.timezone.utc).isoformat()


def cooldown_elapsed(last_run, now_dt, cooldown_min):
    """True if ``cooldown_min`` minutes have passed since ``last_run``.

    A ``None`` ``last_run`` (never scanned this install) counts as elapsed so
    the first idle scan is not blocked.
    """
    if not last_run:
        return True
    try:
        last = _parse_iso(last_run)
    except (ValueError, TypeError):
        return True
    return (now_dt - last) >= datetime.timedelta(minutes=cooldown_min)


# --------------------------------------------------------------------------
# Lifecycle decisions (the §8.6.1 state machine)
# --------------------------------------------------------------------------

def arm(alias):
    """Lazy enable on first idle/drained. Idempotent — no reset if already armed.

    Returns ``action=schedule`` (the agent should create the self-wake) when
    the driver transitions from disarmed to armed, else ``already-armed``.
    """
    state = read_state(alias)
    if state["armed"]:
        # interval_minutes is included even on the already-armed path: after a
        # restart the session-scoped cron is gone while the state file still
        # reads armed, so the agent must be able to rebuild the cron from this
        # return without a second call (DS #12506-unit3 F3).
        return {"action": "already-armed", "scan_count": state["scan_count"],
                "interval_minutes": cooldown_minutes()}
    state["armed"] = True
    state["scan_count"] = 0
    write_state(alias, state)
    return {"action": "schedule", "interval_minutes": cooldown_minutes(),
            "scan_count": 0}


def reidle(alias):
    """Re-enter idle after processing forge work: re-arm and RESET the counter.

    Distinct from :func:`arm` in that it always zeroes ``scan_count`` (a fresh
    burst for the new idle period) and re-arms a driver that had cancelled at
    cap. ``last_run`` is preserved so the global cool-down throttle still holds
    across the re-arm (re-arming must not bypass the throttle).
    """
    state = read_state(alias)
    was_armed = state["armed"]
    state["armed"] = True
    state["scan_count"] = 0
    write_state(alias, state)
    return {"action": "already-armed" if was_armed else "schedule",
            "interval_minutes": cooldown_minutes(), "scan_count": 0,
            "rearmed": not was_armed}


def tick(alias, drained, now=None):
    """Driver-tick decision. Called when the self-wake timer fires.

    Per §8.6.1 the agent forge-reads ``work_queue()`` first; ``drained`` is the
    result (True = no work past cursor). Returns one of:

      - ``absorb-work``  queue not drained — process the work, then ``reidle``.
      - ``cancel``       burst cap reached — stop rescheduling the self-wake.
      - ``scan``         drained + throttle elapsed — run one subloop task,
                         then call ``record-scan`` and reschedule.
      - ``wait``         drained but throttle not elapsed — reschedule, no scan.
    """
    state = read_state(alias)
    burst = idle_scan_burst()
    now_dt = _now(now)

    # Self-defend against a stale self-wake firing after cancel() disarmed the
    # driver (DS finding #3): a disarmed driver never authorizes a scan.
    if not state["armed"]:
        return {"action": "cancel", "reason": "disarmed",
                "scan_count": state["scan_count"]}

    if not drained:
        return {"action": "absorb-work", "scan_count": state["scan_count"],
                "note": "queue not drained; process work then reidle to re-arm"}

    if state["scan_count"] >= burst:
        return {"action": "cancel", "reason": "at-cap",
                "scan_count": state["scan_count"], "burst": burst}

    if cooldown_elapsed(state["last_run"], now_dt, cooldown_minutes()):
        return {"action": "scan", "scan_count": state["scan_count"],
                "burst": burst}

    return {"action": "wait", "reason": "cooldown-not-elapsed",
            "scan_count": state["scan_count"], "burst": burst,
            "cooldown_minutes": cooldown_minutes()}


def record_scan(alias, now=None):
    """Record that a subloop scan just ran: ``scan_count++`` and stamp ``last_run``.

    Returns the new ``scan_count`` and whether the burst cap is now reached
    (``at_cap`` — the agent should ``cancel`` rather than reschedule).
    """
    state = read_state(alias)
    state["scan_count"] += 1
    state["last_run"] = _iso(_now(now))
    write_state(alias, state)
    burst = idle_scan_burst()
    return {"scan_count": state["scan_count"], "burst": burst,
            "at_cap": state["scan_count"] >= burst, "last_run": state["last_run"]}


def cancel(alias):
    """Disarm the driver (agent stops rescheduling). Re-arms via :func:`reidle`."""
    state = read_state(alias)
    was_armed = state["armed"]
    state["armed"] = False
    write_state(alias, state)
    return {"action": "cancelled", "was_armed": was_armed,
            "scan_count": state["scan_count"]}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _emit(obj):
    print(json.dumps(obj))


def main(argv=None):
    from cli_stdio import harden_stdio  # #13198: crash-proof CLI stdio (cp1252)
    harden_stdio()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")

    p_arm = sub.add_parser("arm", help="lazy enable on first idle")
    p_arm.add_argument("alias")

    p_reidle = sub.add_parser("reidle", help="re-arm + reset after forge work")
    p_reidle.add_argument("alias")

    p_tick = sub.add_parser("tick", help="driver-tick decision")
    p_tick.add_argument("alias")
    p_tick.add_argument("--drained", required=True,
                        choices=["true", "false"], help="is the work queue drained?")
    p_tick.add_argument("--now", default=None, help="ISO8601 override (testing)")

    p_rec = sub.add_parser("record-scan", help="record a scan just ran")
    p_rec.add_argument("alias")
    p_rec.add_argument("--now", default=None, help="ISO8601 override (testing)")

    p_cancel = sub.add_parser("cancel", help="disarm the driver")
    p_cancel.add_argument("alias")

    p_status = sub.add_parser("status", help="dump driver state")
    p_status.add_argument("alias")

    args = parser.parse_args(argv)

    if args.cmd == "arm":
        _emit(arm(args.alias))
    elif args.cmd == "reidle":
        _emit(reidle(args.alias))
    elif args.cmd == "tick":
        _emit(tick(args.alias, args.drained == "true", now=args.now))
    elif args.cmd == "record-scan":
        _emit(record_scan(args.alias, now=args.now))
    elif args.cmd == "cancel":
        _emit(cancel(args.alias))
    elif args.cmd == "status":
        state = read_state(args.alias)
        state["burst"] = idle_scan_burst()
        state["cooldown_minutes"] = cooldown_minutes()
        _emit(state)
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
