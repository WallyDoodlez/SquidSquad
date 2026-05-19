#!/usr/bin/env python3
"""SquidSquad Harness — FastAPI lifecycle manager for agent processes (#4966).

Single supervisor that owns all agent lifecycle. Spawns agents via thin launcher
in visible terminal windows, monitors liveness via direct PID checks, manages
intent state machine (running/stopping/restarting/stopped), and persists state
to .harness-state.json for crash recovery.

Architecture:
- Owns agent PIDs directly via AgentState.claude_pid + .claude-pid file fallback
- Intent-based lifecycle: stop/restart set in-memory intent, cycle_post queries API
- Health polling: direct PID check (primary) → .claude-pid file → health_check.py (legacy)
- Harness exit does NOT kill agents (they run in independent terminal windows)
- Crash recovery via .harness-state.json (PIDs, intents, boot times)
- Port discovery via .squidsquad/.harness-port

Usage:
    python references/scripts/harness.py                    # Start on default port 7373
    python references/scripts/harness.py --port 8080        # Custom port
    SQUIDSQUAD_HARNESS_PORT=9090 python references/scripts/harness.py  # Env override
"""

import asyncio
import collections
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure script dir is importable
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"
HARNESS_PORT_FILE = SQUIDSQUAD_DIR / ".harness-port"

DEFAULT_PORT = 7373
HEALTH_POLL_INTERVAL = 5  # seconds
# #4792 Phase 1 (Q7): seconds after intent flip to STOPPING/RESTARTING before
# the harness force-kills the claude PID. The cooperative path (cycle_post
# exit 42 → /quit → process exits) typically wins in under 5s; this safety
# net catches the case where the agent never reaches a cycle boundary or
# /quit hangs (CONTEXT-4792.md §3.3 Q7).
FORCE_KILL_TIMEOUT_SECONDS = 60
HARNESS_STATE_FILE = SQUIDSQUAD_DIR / ".harness-state.json"

import boot_remote
import health_check
import reboot_agent

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print(
        "ERROR: FastAPI and uvicorn are required.\n"
        "Install: pip install fastapi uvicorn",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Agent state model
# ---------------------------------------------------------------------------

class AgentState:
    """In-memory state for a single agent."""

    __slots__ = ("role", "status", "intent", "intent_set_at",
                 "last_health_check", "boot_time",
                 "clone_path", "claude_pid", "terminal_pid",
                 "current_cycle", "current_phase", "last_cycle_start",
                 "last_cycle_end", "last_cycle_type", "bootup_complete")

    # Intent values:
    #   "running"    — agent should be alive; auto-reboot on death (#4949)
    #   "stopping"   — graceful stop requested; do NOT reboot after death
    #   "restarting" — graceful restart; reboot after death
    #   "stopped"    — agent died as requested; terminal state
    INTENT_RUNNING = "running"
    INTENT_STOPPING = "stopping"
    INTENT_RESTARTING = "restarting"
    INTENT_STOPPED = "stopped"

    def __init__(self, role: str, clone_path: str = ""):
        self.role = role
        self.status = "unknown"  # unknown | starting | running | stopped | stalled | error
        self.intent = self.INTENT_RUNNING  # default: agent should be alive
        # #4792 / #8979 Phase 1: wall-clock timestamp at which intent was last
        # flipped to STOPPING or RESTARTING. Drives the 60s force-kill safety
        # net per CONTEXT-4792.md §3.3 (Q7). None when intent is RUNNING or
        # STOPPED.
        self.intent_set_at = None
        self.last_health_check = None
        self.boot_time = None
        self.clone_path = clone_path
        self.claude_pid = None  # PID of claude process (#4966)
        self.terminal_pid = None  # PID of terminal window (#7630 P-6)
        # Phase 2 event-derived state (#4709)
        self.current_cycle = None
        self.current_phase = None
        self.last_cycle_start = None
        self.last_cycle_end = None
        self.last_cycle_type = None
        # #8695 / #8914: bootup_complete is informational only. False until
        # the agent emits `bootup-complete`; exposed via GET /agents/{role} so
        # operators / the TUI can see whether a role has finished its boot
        # sequence. The harness does NOT gate, queue, or hold events on this
        # flag — CONTEXT.md §2 + §5.2 lock the harness as a pure broadcast pipe.
        self.bootup_complete = False

    def to_dict(self):
        return {
            "role": self.role,
            "status": self.status,
            "intent": self.intent,
            "intent_set_at": self.intent_set_at,
            "boot_time": self.boot_time,
            "last_health_check": self.last_health_check,
            "clone_path": self.clone_path,
            "claude_pid": self.claude_pid,
            "terminal_pid": self.terminal_pid,
            "current_cycle": self.current_cycle,
            "current_phase": self.current_phase,
            "last_cycle_start": self.last_cycle_start,
            "last_cycle_end": self.last_cycle_end,
            "last_cycle_type": self.last_cycle_type,
            "bootup_complete": self.bootup_complete,
        }


class HarnessState:
    """Global harness state — thread-safe via lock."""

    def __init__(self):
        self.agents: dict[str, AgentState] = {}
        self.start_time = time.time()
        self.port = DEFAULT_PORT
        # #9243: code_version probed once at boot, cached. Includes
        # squidsquad_version, git_sha, git_branch, git_dirty — see
        # compute_code_version(). Stays None until lifespan fills it.
        self.code_version = None
        self._lock = threading.Lock()
        self._poller_running = False
        self._poller_thread = None

    def get_agent(self, role: str) -> AgentState | None:
        with self._lock:
            return self.agents.get(role)

    def set_agent(self, role: str, state: AgentState):
        with self._lock:
            self.agents[role] = state

    def all_agents(self) -> list[dict]:
        with self._lock:
            return [a.to_dict() for a in self.agents.values()]

    # #4792 Phase 2: the per-class `_read_claude_pid` was a near-duplicate
    # of `reboot_agent._read_claude_pid`. All three call sites (this class
    # + two restart endpoints) now share the module-level helper.

    def update_health(self):
        """Check agent health via direct PID monitoring (#4966).

        Primary: check stored claude_pid or read .claude-pid file.
        Fallback: health_check.py for legacy wrapper agents.
        Auto-reboots dead agents with intent=running.
        """
        # Discover agent clone paths from .local-config
        try:
            all_roles = boot_remote._get_all_roles()
        except (SystemExit, Exception):
            return

        reboot_roles = []
        state_changed = False

        with self._lock:
            for role in all_roles:
                try:
                    clone_path = boot_remote._get_clone_path(role)
                except Exception:
                    continue

                if role not in self.agents:
                    self.agents[role] = AgentState(role, clone_path)
                agent = self.agents[role]
                agent.clone_path = clone_path
                agent.last_health_check = time.time()
                prev_status = agent.status

                # Direct PID check (#4966) — primary health detection
                pid = agent.claude_pid
                alive = False
                pid_changed = False
                if pid:
                    alive = boot_remote._is_process_alive(pid)

                # If no stored PID or PID stale, try reading .claude-pid file
                if not alive:
                    file_pid, file_alive = reboot_agent._read_claude_pid(clone_path, role)
                    if file_pid and file_alive:
                        pid = file_pid
                        alive = True
                        if agent.claude_pid != pid:
                            pid_changed = True
                        agent.claude_pid = pid
                        state_changed = True

                # Fallback: check .health file for legacy wrapper agents
                if not alive and not pid:
                    try:
                        health_report = health_check.check_agent_health(
                            role, clone_path,
                            interval_minutes=30,
                        )
                        legacy_health = health_report.get("health", "unknown")
                        if legacy_health == "healthy":
                            alive = True
                        # #4792: removed the elif `legacy_health == "stopped"`
                        # branch — health_check.py no longer returns "stopped"
                        # (stop intent moved to harness state).
                    except Exception:
                        pass

                # #4792 Phase 1 (Q7) — 60s force-kill safety net.
                # If the agent has been STOPPING/RESTARTING for longer than
                # the timeout AND the claude PID is still alive, the
                # cooperative shutdown path (cycle_post exit 42 → /quit) has
                # not completed; kill the PID directly so the operator's
                # intent eventually wins. CONTEXT-4792.md §3.3. Idempotent:
                # the kill races against the cooperative exit and we re-check
                # on the next poll either way.
                if alive and pid and agent.intent in (
                    AgentState.INTENT_STOPPING, AgentState.INTENT_RESTARTING,
                ) and agent.intent_set_at is not None and (
                    time.time() - agent.intent_set_at
                    > FORCE_KILL_TIMEOUT_SECONDS
                ):
                    elapsed = time.time() - agent.intent_set_at
                    _log(
                        f"{role}: force-kill safety net firing "
                        f"(intent={agent.intent}, elapsed={elapsed:.1f}s, "
                        f"timeout={FORCE_KILL_TIMEOUT_SECONDS}s) — killing "
                        f"claude PID {pid}"
                    )
                    try:
                        reboot_agent._kill_process(pid)
                    except Exception as e:
                        _log(
                            f"{role}: force-kill of PID {pid} raised "
                            f"{type(e).__name__}: {e}"
                        )
                    # Clear intent_set_at so we don't re-log the kill every
                    # 5s while the OS reaps the process. The next poll cycle
                    # will see the dead PID and run the normal STOPPING →
                    # STOPPED / auto-reboot paths below.
                    agent.intent_set_at = None
                    state_changed = True

                # Update status
                if alive:
                    agent.status = "running"
                    if agent.intent == AgentState.INTENT_RESTARTING:
                        agent.intent = AgentState.INTENT_RUNNING
                        agent.intent_set_at = None  # #4792 Phase 1
                        state_changed = True
                    elif agent.intent in (
                        AgentState.INTENT_STOPPING,
                        AgentState.INTENT_STOPPED,
                    ) and pid_changed:
                        # New PID appeared while intent was stale — manual reboot (#7637).
                        # Only reset when PID changed to avoid undoing an in-flight stop.
                        old_intent = agent.intent
                        agent.intent = AgentState.INTENT_RUNNING
                        agent.intent_set_at = None  # #4792 Phase 1
                        state_changed = True
                        _log(f"{role}: alive with new PID (stale intent={old_intent}), reset to running (#7637)")
                elif agent.status != "starting":
                    # #4792: stop is now expressed via intent (INTENT_STOPPING
                    # → INTENT_STOPPED), not a sentinel file.
                    if agent.intent in (
                        AgentState.INTENT_STOPPING, AgentState.INTENT_STOPPED
                    ):
                        agent.status = "stopped"
                    elif prev_status == "running":
                        agent.status = "stalled"
                    elif agent.status not in ("stopped",):
                        agent.status = "unknown"

                # Auto-reboot: agent is dead but should be alive (#4949)
                is_dead = agent.status in ("stopped", "error", "stalled")
                was_alive = prev_status == "running"
                should_reboot = agent.intent in (
                    AgentState.INTENT_RUNNING,
                    AgentState.INTENT_RESTARTING,
                )
                if is_dead and was_alive and should_reboot:
                    reboot_roles.append(role)
                    agent.status = "starting"
                    agent.claude_pid = None  # Clear stale PID
                    # #8695: the replacement process needs to re-emit
                    # bootup-complete before we'll dispatch events to it.
                    agent.bootup_complete = False
                    state_changed = True

                # Stopping intent fulfilled — agent died as requested (#4966)
                if is_dead and agent.intent == AgentState.INTENT_STOPPING:
                    agent.intent = AgentState.INTENT_STOPPED
                    agent.intent_set_at = None  # #4792 Phase 1
                    agent.claude_pid = None
                    state_changed = True

        # Persist state if anything changed (#4966)
        if state_changed or reboot_roles:
            self.save_state()

        # Reboot outside the lock to avoid blocking health updates
        for role in reboot_roles:
            _log(f"Auto-rebooting {role} (was running, intent={self.agents[role].intent})")
            try:
                result = boot_remote.boot_agent(role)
                if result.get("success") and result.get("terminal_pid"):
                    with self._lock:
                        agent = self.agents.get(role)
                        if agent:
                            agent.terminal_pid = result["terminal_pid"]
                self.save_state()
            except Exception as e:
                _log(f"Auto-reboot of {role} failed: {e}")

    def start_poller(self):
        """Start background health polling thread."""
        if self._poller_running:
            return
        self._poller_running = True
        self._poller_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="health-poller"
        )
        self._poller_thread.start()

    def stop_poller(self):
        self._poller_running = False

    def _poll_loop(self):
        while self._poller_running:
            try:
                self.update_health()
            except Exception:
                pass  # Don't crash poller on transient errors
            time.sleep(HEALTH_POLL_INTERVAL)

    def save_state(self):
        """Persist per-agent PIDs and intents to .harness-state.json (#4966).

        Called on spawn, death, intent change. Enables crash recovery.
        Snapshot and disk write are under one lock to prevent concurrent
        callers from clobbering each other's state (#7441).
        """
        with self._lock:
            state_data = {
                "harness_pid": os.getpid(),
                "start_time": self.start_time,
                "port": self.port,
                "agents": {
                    role: {
                        "intent": a.intent,
                        # #4792 Phase 1: persist so the 60s force-kill window
                        # survives harness restarts. CONTEXT-4792.md §3.6.
                        "intent_set_at": a.intent_set_at,
                        "status": a.status,
                        "boot_time": a.boot_time,
                        "clone_path": a.clone_path,
                        "claude_pid": a.claude_pid,
                        "terminal_pid": a.terminal_pid,
                        # #8695: must survive harness crash recovery — otherwise
                        # already-running agents stay gated forever after a
                        # harness restart, since boot_remote skips already-alive
                        # agents and the agent has no way to know we restarted.
                        "bootup_complete": a.bootup_complete,
                    }
                    for role, a in self.agents.items()
                },
            }
            try:
                tmp = HARNESS_STATE_FILE.with_suffix(".tmp")
                tmp.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
                tmp.replace(HARNESS_STATE_FILE)
            except OSError as e:
                _log(f"WARNING: Could not write state file: {e}")

    def load_state(self):
        """Load state from .harness-state.json for crash recovery (#4966).

        On harness restart, reads the file and restores agent intents.
        Process liveness is checked separately via health polling.
        """
        if not HARNESS_STATE_FILE.exists():
            return
        try:
            raw = HARNESS_STATE_FILE.read_text(encoding="utf-8")
            state_data = json.loads(raw)
        except (json.JSONDecodeError, OSError) as e:
            _log(f"WARNING: Could not read state file: {e}")
            return

        with self._lock:
            for role, agent_data in state_data.get("agents", {}).items():
                if role not in self.agents:
                    self.agents[role] = AgentState(
                        role, agent_data.get("clone_path", "")
                    )
                agent = self.agents[role]
                agent.intent = agent_data.get("intent", AgentState.INTENT_RUNNING)
                # #4792 Phase 1 — two-case migration per CONTEXT-4792.md §5.1.
                # We distinguish absent key from explicit null so an explicit
                # null is always honored (case b: "load as-is") and only an
                # absent key triggers the migration seed (case a):
                #   (a) legacy state file: intent is STOPPING/RESTARTING and
                #       the `intent_set_at` key is ABSENT → seed with
                #       time.time() so the force-kill clock starts now rather
                #       than firing immediately on a pre-existing intent.
                #   (b) present state file: load as-is (may be None when the
                #       intent is RUNNING/STOPPED, or a float when STOPPING/
                #       RESTARTING).
                if "intent_set_at" not in agent_data and agent.intent in (
                    AgentState.INTENT_STOPPING, AgentState.INTENT_RESTARTING,
                ):
                    agent.intent_set_at = time.time()
                else:
                    agent.intent_set_at = agent_data.get("intent_set_at")
                agent.boot_time = agent_data.get("boot_time")
                agent.claude_pid = agent_data.get("claude_pid")
                agent.terminal_pid = agent_data.get("terminal_pid")
                # #8695: restore so already-running agents stay ungated after
                # a harness restart. Defaults to False for older state files.
                agent.bootup_complete = agent_data.get("bootup_complete", False)

        _log(f"Restored state for {len(state_data.get('agents', {}))} agents from state file")


# ---------------------------------------------------------------------------
# Event stream (#4709 Phase 2)
# ---------------------------------------------------------------------------

class EventStream:
    """Bounded event stream — thread-safe deque with max 1000 events."""

    def __init__(self, maxlen=1000):
        self._events = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, event: dict):
        with self._lock:
            self._events.append(event)

    def get_all(self) -> list[dict]:
        with self._lock:
            return list(self._events)

    def get_recent(self, n: int = 50) -> list[dict]:
        with self._lock:
            items = list(self._events)
            return items[-n:] if len(items) > n else items

    def get_since(self, since_id: str, limit: int = 100) -> list[dict]:
        """Return events after the given ID. If ID not found, return oldest available."""
        with self._lock:
            items = list(self._events)
            if not since_id:
                return items[-limit:] if len(items) > limit else items
            # Find the index of the since_id event
            for i, event in enumerate(items):
                if event.get("id") == since_id:
                    after = items[i + 1:]
                    return after[-limit:] if len(after) > limit else after
            # ID not found (evicted) — return oldest available up to limit
            return items[-limit:] if len(items) > limit else items

    def __len__(self):
        with self._lock:
            return len(self._events)


EVENT_STATE_FILE = SQUIDSQUAD_DIR / ".event-state.json"


class EventLifecycleManager:
    """Manages event dispatch, per-role queues, and disk persistence (#7630 P-1/P-3).

    Wraps EventStream with:
    - Disk persistence: events survive harness restarts
    - Per-role in-flight tracking: one event at a time per role
    - Dispatch/ack lifecycle for future event-driven mode
    """

    DEFAULT_TIMEOUT_MINUTES = 10
    DEFAULT_MAX_RETRIES = 3
    SCAN_INTERVAL = 30  # seconds between timeout scans

    def __init__(self, stream: EventStream, max_in_flight: int = 50,
                 timeout_minutes: int = 10, max_retries: int = 3):
        self._stream = stream
        self._lock = threading.Lock()
        self._in_flight: dict[str, list[str]] = {}  # role → [event_ids]
        self._max_in_flight = max_in_flight
        self._dispatched: dict[str, dict] = {}  # event_id → event dict
        self._dispatch_times: dict[str, float] = {}  # event_id → dispatch timestamp
        self._retry_counts: dict[str, int] = {}  # event_id → retry count
        self._timeout_minutes = timeout_minutes
        self._max_retries = max_retries
        self._loaded = False
        self._scanner_running = False
        self._scanner_thread = None

    def append(self, event: dict):
        """Store event in stream and persist to disk."""
        self._stream.append(event)
        self._persist()

    def dispatch(self, event_id: str, role: str, event: dict):
        """Mark an event as dispatched to a role (in-flight tracking).

        NOTE: Not yet wired into POST /events — Phase 4 plumbing. Currently
        dormant; will be activated when event-driven mode replaces the loop.
        """
        with self._lock:
            if role not in self._in_flight:
                self._in_flight[role] = []
            # Skip if already dispatched (prevents re-dispatch on cursor loss)
            if event_id in self._dispatched:
                return
            if len(self._in_flight[role]) < self._max_in_flight:
                self._in_flight[role].append(event_id)
                self._dispatched[event_id] = event
                self._dispatch_times[event_id] = time.time()
        self._persist()

    def ack(self, event_id: str, role: str) -> bool:
        """Acknowledge event completion. Returns True if event was in-flight."""
        found = False
        with self._lock:
            if role in self._in_flight and event_id in self._in_flight[role]:
                self._in_flight[role].remove(event_id)
                self._dispatched.pop(event_id, None)
                self._dispatch_times.pop(event_id, None)
                self._retry_counts.pop(event_id, None)
                found = True
        if found:
            self._persist()
        return found

    def get_in_flight(self, role: str) -> list[str]:
        """Get list of in-flight event IDs for a role."""
        with self._lock:
            return list(self._in_flight.get(role, []))

    def _persist(self):
        """Write event state to disk atomically.

        Persist last 200 events for crash recovery; full 1000 are in-memory only.
        Lock ordering: self._lock → EventStream._lock (via get_recent).
        Entire snapshot+write is inside self._lock to prevent concurrent .tmp clobber.
        """
        with self._lock:
            recent_events = list(self._stream.get_recent(200))
            data = {
                "events": recent_events,
                "in_flight": {r: list(ids) for r, ids in self._in_flight.items()},
                "dispatched": {eid: ev for eid, ev in self._dispatched.items()},
                "dispatch_times": dict(self._dispatch_times),
                "retry_counts": dict(self._retry_counts),
            }
            try:
                tmp = EVENT_STATE_FILE.with_suffix(".tmp")
                tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
                tmp.replace(EVENT_STATE_FILE)
            except OSError:
                pass  # Best-effort — don't crash harness on persist failure

    def load(self):
        """Restore event state from disk on harness restart. Idempotent."""
        if self._loaded:
            return
        if not EVENT_STATE_FILE.exists():
            self._loaded = True
            return
        try:
            raw = EVENT_STATE_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError):
            self._loaded = True
            return

        # Restore in-flight/dispatch state under lock, then load events outside
        # to maintain consistent lock ordering: self._lock → EventStream._lock
        events_to_load = data.get("events", [])
        with self._lock:
            self._in_flight = {
                r: list(ids) for r, ids in data.get("in_flight", {}).items()
            }
            self._dispatched = data.get("dispatched", {})
            self._dispatch_times = {
                k: float(v) for k, v in data.get("dispatch_times", {}).items()
            }
            self._retry_counts = {
                k: int(v) for k, v in data.get("retry_counts", {}).items()
            }
        # Append events outside self._lock (acquires EventStream._lock)
        for event in events_to_load:
            self._stream.append(event)
        self._loaded = True

    def timeout_scan(self):
        """Check for overdue in-flight events and escalate (#7630 2-3).

        For each overdue event:
        - If retries < max: increment retry count, reset dispatch time
        - If retries >= max: mark as timed-out, remove from in-flight
        All logging happens outside the lock to prevent deadlock with print().
        """
        now = time.time()
        timeout_secs = self._timeout_minutes * 60
        timed_out = []
        retry_messages = []

        with self._lock:
            for role, event_ids in list(self._in_flight.items()):
                to_remove = []
                for event_id in list(event_ids):
                    dispatch_time = self._dispatch_times.get(event_id, now)
                    if now - dispatch_time > timeout_secs:
                        retries = self._retry_counts.get(event_id, 0)
                        if retries < self._max_retries:
                            self._retry_counts[event_id] = retries + 1
                            self._dispatch_times[event_id] = now
                            retry_messages.append(
                                f"Event {event_id} overdue for {role} "
                                f"(retry {retries + 1}/{self._max_retries})")
                        else:
                            timed_out.append((role, event_id))
                            to_remove.append(event_id)
                            self._dispatched.pop(event_id, None)
                            self._dispatch_times.pop(event_id, None)
                            self._retry_counts.pop(event_id, None)
                # Remove timed-out events from live list
                for eid in to_remove:
                    if eid in event_ids:
                        event_ids.remove(eid)

        # Log outside lock
        for msg in retry_messages:
            _log(msg)
        for role, event_id in timed_out:
            _log(f"Event {event_id} TIMED OUT for {role} after {self._max_retries} retries — escalating")

        if timed_out or retry_messages:
            self._persist()

        return timed_out

    def start_timeout_scanner(self):
        """Start background thread that scans for overdue events."""
        if self._scanner_running:
            return
        self._scanner_running = True
        self._scanner_thread = threading.Thread(
            target=self._scan_loop, daemon=True, name="event-timeout-scanner"
        )
        self._scanner_thread.start()

    def stop_timeout_scanner(self):
        self._scanner_running = False

    def _scan_loop(self):
        while self._scanner_running:
            try:
                self.timeout_scan()
            except Exception:
                pass  # Don't crash scanner on transient errors
            time.sleep(self.SCAN_INTERVAL)

    @property
    def stream(self) -> EventStream:
        return self._stream


# Global state
state = HarnessState()
event_stream = EventStream()
event_lifecycle = EventLifecycleManager(event_stream)


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def _log(msg: str):
    """Print a timestamped log line to the harness console."""
    ts = time.strftime("%H:%M:%S")
    print(f"[🦑 {ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Code-version probe (#9243) — read once at boot, cache for /status + /
# ---------------------------------------------------------------------------


def _read_squidsquad_version():
    """Read `SquidSquad Version` from config.md. Returns the value string or
    None if config.md is missing or the field is absent. Never raises."""
    try:
        cfg = SQUIDSQUAD_DIR / "config.md"
        for line in cfg.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("- **SquidSquad Version**:"):
                return stripped.split(":", 1)[1].strip()
    except (OSError, UnicodeDecodeError):
        pass
    return None


def _git_probe(args):
    """Run `git <args>` in REPO_ROOT and return stripped stdout, or None on
    any failure (no git, not a repo, non-zero exit). Never raises."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
            check=False,
        )
    except Exception:
        # "Never raises" boot-time contract — catch broadly so a stray
        # ValueError / malformed args / locale glitch on Windows cannot
        # bring down the lifespan probe.
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def compute_code_version():
    """Probe squidsquad version + git state once at boot. All fields
    individually fall back to `None` on failure so a non-git environment or
    missing config.md still produces a stable response shape."""
    version = _read_squidsquad_version()
    sha = _git_probe(["rev-parse", "--short=8", "HEAD"])
    branch = _git_probe(["rev-parse", "--abbrev-ref", "HEAD"])
    porcelain = _git_probe(["status", "--porcelain"])
    if porcelain is None:
        dirty = None
    else:
        dirty = bool(porcelain)
    return {
        "squidsquad_version": version,
        "git_sha": sha,
        "git_branch": branch,
        "git_dirty": dirty,
    }


# ---------------------------------------------------------------------------
# Legacy-sentinel cleanup (#4792 Phase 2 §5.1)
# ---------------------------------------------------------------------------

LEGACY_SENTINEL_FILES = (".stop", ".restart", ".health")


def _cleanup_legacy_sentinels(clone_paths):
    """Unlink pre-#4792 lifecycle sentinel files from each agent clone.

    Before #4792 the wrapper/PM stack wrote `.stop`, `.restart`, and
    `.health` files under `.squidsquad/<role>/` to signal lifecycle
    intent and liveness. Those signals are now owned by the harness
    intent state machine (`.harness-state.json`) and the `.claude-pid`
    file (CONTEXT-4792.md §5.1).

    On harness boot, sweep the legacy files so a stale `.stop` left over
    from a previous SquidSquad version cannot influence `update_health`
    or be misread by any remaining legacy reader during the upgrade
    window. Idempotent: missing files are silently ignored; any other
    OSError is logged but does not abort startup.

    Returns ``(removed, errors)`` so the caller can log a summary.
    """
    removed = 0
    errors = 0
    for role, clone_root in clone_paths.items():
        role_dir = Path(clone_root) / ".squidsquad" / role
        if not role_dir.is_dir():
            continue
        for name in LEGACY_SENTINEL_FILES:
            sentinel = role_dir / name
            # Skip the syscall entirely for non-existent files so the
            # counters reflect real removals only. `missing_ok=True` on
            # the unlink then swallows the FileNotFoundError that arises
            # in the rare TOCTOU window where the file disappears
            # between the `exists()` check and the unlink — in that
            # case the post-condition (file gone) is satisfied so it
            # still counts as a removal.
            if not sentinel.exists():
                continue
            try:
                sentinel.unlink(missing_ok=True)
                removed += 1
            except OSError as e:
                errors += 1
                _log(
                    f"legacy-sentinel cleanup: {role}/{name} unlink "
                    f"failed: {type(e).__name__}: {e}"
                )
    return removed, errors


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    _log(f"Harness starting on port {state.port}...")

    # #9243: Probe code version once at boot. Each field falls back to None
    # on failure (no git, missing config.md) — never blocks startup.
    state.code_version = compute_code_version()
    cv = state.code_version
    _log(
        f"Code version: squidsquad={cv['squidsquad_version']} "
        f"git_sha={cv['git_sha']} branch={cv['git_branch']} "
        f"dirty={cv['git_dirty']}"
    )

    # --- Verify agent clones ---
    _log("Verifying agent clones...")
    try:
        clone_map = boot_remote._parse_local_config()
        all_ok = True
        for role, clone_root in sorted(clone_map.items()):
            clone_path = Path(clone_root)
            claude_md = clone_path / ".squidsquad" / role / "CLAUDE.md"
            if not clone_path.exists():
                _log(f"  {role}: MISSING — {clone_path}")
                all_ok = False
            elif not claude_md.exists():
                _log(f"  {role}: clone exists but no CLAUDE.md — {clone_path}")
                all_ok = False
            else:
                _log(f"  {role}: OK — {clone_path}")
        if not all_ok:
            _log("WARNING: Some clones are missing. Run add_role.py to create them.")
    except (SystemExit, Exception) as e:
        _log(f"WARNING: Could not verify clones: {e}")

    # Write port discovery file FIRST so CLI can detect us ASAP.
    # The server starts accepting connections after lifespan yields,
    # so minimize work before the port file + yield.

    # Write port discovery file (atomic) — primary repo
    try:
        tmp = HARNESS_PORT_FILE.with_suffix(".tmp")
        tmp.write_text(str(state.port), encoding="utf-8")
        tmp.replace(HARNESS_PORT_FILE)
        _log(f"Port discovery file written: {HARNESS_PORT_FILE}")
    except OSError as e:
        _log(f"WARNING: Could not write port file: {e}")

    _log("Harness ready. Ctrl+C to stop.")
    _log(f"API: http://localhost:{state.port}/status")

    # All slow I/O (clone port distribution, crash recovery, health check) runs
    # in background so the server accepts connections immediately (fixes CLI timeout).
    def _deferred_init():
        # Write port file to each agent clone's .squidsquad/ directory (#4709 TC-7)
        try:
            clone_paths = boot_remote._parse_local_config()
            for role, clone_root in clone_paths.items():
                clone_squid = Path(clone_root) / ".squidsquad"
                if clone_squid.is_dir() and Path(clone_root).resolve() != REPO_ROOT.resolve():
                    clone_port_file = clone_squid / ".harness-port"
                    try:
                        clone_tmp = clone_port_file.with_suffix(".tmp")
                        clone_tmp.write_text(str(state.port), encoding="utf-8")
                        clone_tmp.replace(clone_port_file)
                    except OSError:
                        pass
            _log(f"Port file distributed to {len(clone_paths)} clone(s)")
        except (SystemExit, Exception) as e:
            _log(f"WARNING: Could not distribute port to clones: {e}")

        _log("Loading saved state...")
        state.load_state()
        event_lifecycle.load()
        event_lifecycle.start_timeout_scanner()
        activity_detector.start()
        _log(f"Event state loaded: {len(event_stream)} events in stream")

        # Skip initial update_health() — it's slow on Windows (tasklist per agent).
        # The health poller will pick up state within HEALTH_POLL_INTERVAL seconds.

        # Auto-start all agents on harness boot
        _log("Auto-starting all agents...")
        try:
            roles = boot_remote._get_all_roles()
            for role in roles:
                result = boot_remote.boot_agent(role)
                status = "OK" if result["success"] else "FAIL"
                _log(f"  {role}: {result['action']} -- {status}: {result['message']}")
                if result["success"]:
                    agent_state = state.get_agent(role) or AgentState(role)
                    if result["action"] == "spawn":
                        agent_state.status = "starting"
                        agent_state.intent = AgentState.INTENT_RUNNING
                        agent_state.intent_set_at = None  # #4792 Phase 1
                        # #8695: a fresh spawn must re-assert bootup-complete
                        # before events flow — match the other spawn paths.
                        agent_state.bootup_complete = False
                        agent_state.boot_time = time.time()
                        agent_state.terminal_pid = result.get("terminal_pid")
                    state.set_agent(role, agent_state)
            state.save_state()
        except Exception as e:
            _log(f"Auto-start failed: {e}")

    # Sweep pre-#4792 legacy lifecycle sentinels SYNCHRONOUSLY before the
    # health poller starts, so a stale `.stop`/`.restart`/`.health` cannot
    # be observed by the first `update_health` pass during an upgrade
    # window (CONTEXT-4792.md §5.1). Best-effort — failures here do not
    # block startup. Must run on the lifespan thread, NOT inside
    # `_deferred_init`: the deferred thread races against `start_poller`,
    # which would let the poller hit the legacy `.health` fallback in
    # `update_health` before cleanup completes.
    try:
        clone_paths_for_cleanup = boot_remote._parse_local_config()
        removed, errors = _cleanup_legacy_sentinels(clone_paths_for_cleanup)
        if removed or errors:
            _log(
                f"Legacy-sentinel cleanup: removed {removed}, "
                f"errors {errors}"
            )
    except (SystemExit, Exception) as e:
        _log(f"WARNING: legacy-sentinel cleanup failed: {e}")

    threading.Thread(target=_deferred_init, daemon=True, name="deferred-init").start()
    state.start_poller()

    yield

    # Shutdown
    _log("Shutting down...")
    state.stop_poller()

    # Clean up port files (primary + clones, retry for Windows file locking)
    for attempt in range(3):
        try:
            if HARNESS_PORT_FILE.exists():
                HARNESS_PORT_FILE.unlink()
            break
        except OSError as e:
            _log(f"WARNING: Could not delete port file (attempt {attempt + 1}/3): {e}")
            time.sleep(0.5)

    # Clean up clone port files (#4709)
    try:
        clone_paths = boot_remote._parse_local_config()
        for role, clone_root in clone_paths.items():
            clone_port = Path(clone_root) / ".squidsquad" / ".harness-port"
            try:
                clone_port.unlink(missing_ok=True)
            except OSError:
                pass
    except (SystemExit, Exception):
        pass

    _log("Harness stopped.")


app = FastAPI(
    title="SquidSquad Harness",
    version="1.0.0",
    lifespan=lifespan,
)


def _validate_role(role: str) -> str:
    """Validate that a role is configured. Returns the role name or raises 404."""
    configured = boot_remote._get_all_roles()
    # Also allow "pm" even though _get_all_roles excludes it
    all_known = set(configured) | {"pm"}
    if role not in all_known:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown role: {role}. Configured: {sorted(all_known)}",
        )
    return role


# -- Endpoints --
# IMPORTANT: /agents/all/* routes MUST be defined BEFORE /agents/{role}/* routes.
# FastAPI matches routes in definition order — {role} would capture "all" as a role name.

@app.get("/status")
async def get_status():
    """Harness + all agent health."""
    state.update_health()
    uptime = int(time.time() - state.start_time)
    # #9243: include code_version + boot_time_iso so operators can verify
    # which code is actually running without a restart probe.
    cv = state.code_version if state.code_version is not None else compute_code_version()
    code_version = dict(cv)
    code_version["boot_time_iso"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(state.start_time)
    )
    return {
        "harness": {
            "status": "running",
            "port": state.port,
            "uptime_seconds": uptime,
            "uptime_human": f"{uptime // 3600}h {(uptime % 3600) // 60}m {uptime % 60}s",
            "code_version": code_version,
        },
        "agents": state.all_agents(),
    }


@app.get("/")
async def get_root():
    """Slim liveness/version probe (#9243). Replaces the default 404."""
    cv = state.code_version if state.code_version is not None else compute_code_version()
    return {
        "service": "squidsquad-harness",
        "version": cv.get("squidsquad_version"),
        "git_sha": cv.get("git_sha"),
    }


@app.get("/agents")
async def list_agents():
    """List agents with state."""
    state.update_health()
    return {"agents": state.all_agents()}


@app.post("/agents/all/start")
async def start_all():
    """Spawn all configured agents."""
    roles = boot_remote._get_all_roles()
    _log(f"Starting all agents: {', '.join(roles)}")

    results = []
    for role in roles:
        result = boot_remote.boot_agent(role)
        results.append(result)
        status = "OK" if result["success"] else "FAIL"
        _log(f"  {role}: {result['action']} -- {status}: {result['message']}")

        if result["success"]:
            agent_state = state.get_agent(role) or AgentState(role)
            if result["action"] == "spawn":
                agent_state.status = "starting"
                agent_state.intent = AgentState.INTENT_RUNNING
                agent_state.intent_set_at = None  # #4792 Phase 1
                # #8695: match the other four spawn paths — a fresh agent
                # must re-assert bootup-complete before we'll dispatch events.
                agent_state.bootup_complete = False
                agent_state.boot_time = time.time()
                agent_state.terminal_pid = result.get("terminal_pid")
            state.set_agent(role, agent_state)

    state.save_state()
    return {"results": results}


@app.post("/agents/all/stop")
async def stop_all():
    """Stop all agents gracefully (#4966). Sets intent via API — no sentinel files."""
    roles = boot_remote._get_all_roles()
    _log(f"Stopping all agents: {', '.join(roles)}")

    results = []
    for role in roles:
        clone_path = boot_remote._get_clone_path(role)

        # Check if agent is already stopped (intent or health)
        agent_state = state.get_agent(role)
        if agent_state and agent_state.intent == AgentState.INTENT_STOPPING:
            results.append({"role": role, "action": "skip", "success": True,
                            "message": "Already stopping"})
            _log(f"  {role}: skip (already stopping)")
            continue

        # Skip agents that need booting (dead/not running)
        needs_boot, reason, _ = boot_remote._needs_boot(role)
        if needs_boot:
            results.append({"role": role, "action": "skip", "success": True,
                            "message": "Not running"})
            _log(f"  {role}: skip (not running)")
            continue

        # Set intent — cycle_post.py queries API for intent (#4966)
        if not agent_state:
            agent_state = AgentState(role, clone_path)
        agent_state.intent = AgentState.INTENT_STOPPING
        agent_state.intent_set_at = time.time()  # #4792 Phase 1
        state.set_agent(role, agent_state)
        results.append({"role": role, "action": "stop", "success": True})
        _log(f"  {role}: intent=stopping")

    state.save_state()
    return {"results": results}


@app.get("/agents/{role}")
async def get_agent(role: str):
    """Get single agent state."""
    _validate_role(role)
    state.update_health()
    agent = state.get_agent(role)
    if agent is None:
        return {"role": role, "status": "unknown", "message": "No health data yet"}
    return agent.to_dict()


@app.post("/agents/{role}/start")
async def start_agent(role: str):
    """Spawn an agent in a visible terminal."""
    _validate_role(role)

    # Check if already running
    agent = state.get_agent(role)
    if agent and agent.status == "running":
        return JSONResponse(
            status_code=200,
            content={"role": role, "action": "skip", "message": "Already running"},
        )

    _log(f"Starting {role}...")
    result = boot_remote.boot_agent(role)
    _log(f"  {role}: {result['action']} -- {'OK' if result['success'] else 'FAIL'}: {result['message']}")

    if result["success"]:
        agent_state = state.get_agent(role) or AgentState(role)
        # Only mutate state on an actual spawn — `boot_agent` can return
        # action="skip" (e.g., another boot already in flight) without
        # replacing the running process. Match start_all's spawn guard so a
        # racing skip-result does not clobber a healthy agent's state.
        if result["action"] == "spawn":
            agent_state.status = "starting"
            agent_state.intent = AgentState.INTENT_RUNNING
            agent_state.intent_set_at = None  # #4792 Phase 1
            agent_state.boot_time = time.time()
            agent_state.terminal_pid = result.get("terminal_pid")
            # #8695: spawning a fresh agent → bootup-complete must be re-asserted
            # by the new process before we'll dispatch any events to it.
            agent_state.bootup_complete = False
        state.set_agent(role, agent_state)
        state.save_state()

    status_code = 200 if result["success"] else 500
    return JSONResponse(status_code=status_code, content=result)


@app.get("/agents/{role}/health")
async def get_agent_health(role: str):
    """Agent health endpoint — process status, last cycle, phase, context pressure (#4966)."""
    _validate_role(role)
    state.update_health()
    agent = state.get_agent(role)

    result = {
        "role": role,
        "alive": False,
        "status": "unknown",
        "last_cycle": None,
        "current_phase": None,
        "context_pressure": None,
    }

    if agent:
        result["alive"] = agent.status == "running"
        result["status"] = agent.status

    # Read current-state file for phase
    state_file = SQUIDSQUAD_DIR / role / "current-state"
    try:
        result["current_phase"] = state_file.read_text(encoding="utf-8").strip()
    except (OSError, FileNotFoundError):
        pass

    # Read context-pressure file
    ctx_file = SQUIDSQUAD_DIR / role / "context-pressure"
    try:
        result["context_pressure"] = int(ctx_file.read_text(encoding="utf-8").strip())
    except (OSError, FileNotFoundError, ValueError):
        pass

    return result


@app.get("/agents/{role}/config")
async def get_agent_config(role: str):
    """Agent config sync state (#4966)."""
    _validate_role(role)

    result = {"role": role}

    # Read config.md for agent-relevant settings
    try:
        import config as cfg
        result["branch_workflow"] = cfg.get_field("branch-workflow") == "yes"
        result["pr_flow"] = cfg.get_field("pr-flow") == "yes"
        result["interval_minutes"] = int(cfg.get_field("interval") or "30")
        result["version"] = cfg.get_field("version")
    except Exception:
        result["error"] = "Could not read config"

    return result


# ---------------------------------------------------------------------------
# Event bus helpers (#4709 Phase 2)
# ---------------------------------------------------------------------------

def _update_agent_from_event(event: dict):
    """Update AgentState fields from a received event (#7630 P-4 thread safety)."""
    role = event.get("role")
    event_type = event.get("event_type")
    payload = event.get("payload", {})
    cycle_number = event.get("cycle_number")

    with state._lock:
        agent = state.agents.get(role)
        if agent is None:
            agent = AgentState(role)
            state.agents[role] = agent

        if event_type == "cycle-start":
            if cycle_number is not None:
                agent.current_cycle = cycle_number
            agent.last_cycle_start = event.get("timestamp")
        elif event_type == "cycle-end":
            agent.last_cycle_end = event.get("timestamp")
            agent.last_cycle_type = payload.get("cycle_type")
        elif event_type == "phase-change":
            agent.current_phase = payload.get("phase")


def _log_event(event: dict):
    """Print an event to the harness console in compact format."""
    ts = time.strftime("%H:%M:%S")
    role = event.get("role", "?")
    event_type = event.get("event_type", "?")
    payload = event.get("payload", {})
    cycle_number = event.get("cycle_number")

    # Build detail string based on event type
    detail = ""
    if cycle_number is not None:
        detail = f"#{cycle_number}"
    if event_type == "cycle-end":
        cycle_type = payload.get("cycle_type", "")
        summary = payload.get("summary", "")
        if cycle_type:
            detail += f" ({cycle_type})"
        if summary:
            detail += f" — {summary[:60]}"
    elif event_type == "git-commit":
        msg = payload.get("message", "")
        files = payload.get("files_changed", "")
        if msg:
            detail = f'"{msg[:40]}"'
        if files:
            detail += f" ({files} files)"
    elif event_type == "git-pull":
        detail = payload.get("result", "")
    elif event_type == "git-push":
        detail = payload.get("branch", "")
    elif event_type == "pr-create":
        detail = f"PR #{payload.get('pr_number', '?')}"
    elif event_type == "pr-merge":
        detail = f"PR #{payload.get('pr_number', '?')}"
    elif event_type == "branch-checkout":
        detail = payload.get("branch", "")
    elif event_type == "status-transition":
        issue = payload.get("issue_number", "?")
        from_s = payload.get("from", "?")
        to_s = payload.get("to", "?")
        detail = f"#{issue} {from_s} → {to_s}"
    elif event_type == "tracker-comment":
        preview = payload.get("comment_preview", "")
        detail = f"#{payload.get('issue_number', '?')} \"{preview[:40]}\""
    elif event_type == "phase-change":
        detail = payload.get("phase", "")

    print(f"[{ts}] {role:<6} {event_type:<18} {detail}", flush=True)


# ---------------------------------------------------------------------------
# Event bus endpoints (#4709 Phase 2)
# ---------------------------------------------------------------------------

@app.post("/events")
async def receive_event(request: Request):
    """Receive an event from an agent mechanical script.

    Stores in bounded stream, updates AgentState, logs to console.
    """
    body = await request.json()

    # Validate minimal fields
    event_type = body.get("event_type")
    role = body.get("role")
    if not event_type or not role:
        raise HTTPException(status_code=400, detail="event_type and role are required")

    # Stamp received_at for ordering (#5622)
    body["received_at"] = time.time()

    # Store in stream (with disk persistence via lifecycle manager)
    event_lifecycle.append(body)

    # Bootup-complete is informational only (#8914). The harness records the
    # flag on AgentState and exposes it via GET /agents/{role}; it does NOT
    # gate or queue events per-role. CONTEXT.md §2 + §5.2 lock the harness as
    # a pure broadcast pipe — no tracker observation, no dispatch logic.
    if event_type == "bootup-complete" and role:
        # Mutate under state._lock to avoid racing with the health poller's
        # auto-reboot path (which sets bootup_complete=False under the same
        # lock when it detects death).
        with state._lock:
            agent = state.agents.get(role)
            if agent is None:
                agent = AgentState(role)
                state.agents[role] = agent
            agent.bootup_complete = True
        state.save_state()
        _log(f"{role}: bootup-complete — event dispatch unlocked")

    # Ack processing (#7630 2-2): if event is an ack, process the lifecycle closure
    if event_type == "ack":
        ack_event_id = body.get("payload", {}).get("event_id")
        if ack_event_id and role:
            acked = event_lifecycle.ack(ack_event_id, role)
            if acked:
                _log(f"Event {ack_event_id} acked by {role}")
            # If ack references stop-requested, treat as shutdown confirmation.
            # The ack only confirms an already-requested stop — it must not
            # reset `intent_set_at` (which would extend the 60s force-kill
            # window indefinitely under repeated acks per CONTEXT-4792.md
            # §3.3 Q7). Also only fires when the agent is still in STOPPING:
            # any subsequent operator action (RUNNING / RESTARTING / STOPPED)
            # supersedes this ack, which is now stale.
            if body.get("payload", {}).get("result") == "stop-confirmed":
                with state._lock:
                    agent = state.agents.get(role)
                    if agent and agent.intent == AgentState.INTENT_STOPPING:
                        # Intent already STOPPING and intent_set_at already
                        # recorded at request time — nothing to update here.
                        # The save_state below is a no-op for these fields
                        # but kept for parity with other ack paths.
                        pass
                state.save_state()

    # Update AgentState from event
    _update_agent_from_event(body)

    # Log to console
    _log_event(body)

    return {"status": "ok"}


@app.get("/events")
async def get_events(
    limit: int = 100,
    since: str = None,
    role: str = None,
    event_type: str = None,
):
    """Retrieve events from the stream with filtering (#5622).

    Query params:
        since: event ID — return events after this ID
        role: filter by emitting role
        event_type: filter by event type (comma-separated for multiple)
        limit: max events to return (default 100)
    """
    if since:
        events = event_stream.get_since(since, limit=limit * 3)  # over-fetch before filtering
    else:
        events = event_stream.get_recent(limit * 3)

    # Apply filters
    if role:
        events = [e for e in events if e.get("role") == role]
    if event_type:
        types = set(event_type.split(","))
        events = [e for e in events if e.get("event_type") in types]

    # Apply limit after filtering
    events = events[-limit:] if len(events) > limit else events

    return {"events": events, "total": len(event_stream)}


@app.get("/events/for/{role}")
async def get_events_for_role(
    role: str,
    limit: int = 50,
    since: str = None,
):
    """Get events targeted at a specific role (#7630 Phase 4).

    Returns events where payload.target_role matches the given role,
    OR events with event_type in the role's reacts-to list.
    Marks returned events as dispatched in EventLifecycleManager.

    This is the primary endpoint for event-driven agents using Monitor tool.
    """
    _validate_role(role)

    # No per-role gating here (#8914). The harness is a pure broadcast pipe;
    # `bootup_complete` is informational only, exposed via GET /agents/{role}
    # but never consulted for event delivery. CONTEXT.md §5.2.

    # Get relevant event types for this role from config
    try:
        from config import get_event_filters_for_role
        relevant_types = get_event_filters_for_role(role)
    except (ImportError, Exception):
        relevant_types = None

    # Fetch events from stream
    if since:
        events = event_stream.get_since(since, limit=limit * 3)
    else:
        events = event_stream.get_recent(limit * 3)

    # Filter: events targeted at this role OR matching the role's reaction types
    filtered = []
    for e in events:
        target = e.get("payload", {}).get("target_role", "")
        etype = e.get("event_type", "")
        if target == role:
            filtered.append(e)
        elif relevant_types and etype in relevant_types:
            filtered.append(e)

    filtered = filtered[-limit:] if len(filtered) > limit else filtered

    # Mark dispatched in lifecycle manager
    for e in filtered:
        eid = e.get("id")
        if eid:
            event_lifecycle.dispatch(eid, role, e)

    return {"events": filtered, "total": len(filtered)}


@app.post("/events/{event_id}/complete")
async def complete_event(event_id: str, request: Request):
    """Mark an event as completed by the processing agent (#7630 Phase 4).

    Called by agents after they finish processing an event. The harness:
    1. Marks the event as acked in EventLifecycleManager
    2. Executes any mechanical side effects (status transitions, commits)
    3. Returns success/failure

    Request body:
        role: str — the agent role completing the event
        status: str — "success" or "failure"
        summary: str — brief description of what was done
        transitions: list — optional status transitions to execute
        comments: list — optional tracker comments to post
        commit_message: str — optional commit message for git commit
    """
    body = await request.json()
    role = body.get("role")
    if not role:
        raise HTTPException(status_code=400, detail="role is required")

    # Ack the event in lifecycle manager
    acked = event_lifecycle.ack(event_id, role)
    if not acked:
        # Event not in-flight — may have timed out or already been acked
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=410,
            content={"status": "gone", "detail": f"Event {event_id} not in-flight for {role}"},
        )

    _log(f"Event {event_id} completed by {role}: {body.get('summary', 'no summary')}")

    # Execute mechanical side effects
    errors = []

    # Status transitions
    for transition in body.get("transitions", []):
        try:
            _execute_transition(transition)
        except Exception as ex:
            errors.append(f"transition error: {ex}")

    # Tracker comments
    for comment in body.get("comments", []):
        try:
            _execute_comment(comment)
        except Exception as ex:
            errors.append(f"comment error: {ex}")

    return {
        "status": "ok" if not errors else "partial",
        "event_id": event_id,
        "errors": errors,
    }


@app.get("/events/in-flight/{role}")
async def get_in_flight_events(role: str):
    """Get in-flight event IDs for a role (#7630 P-3)."""
    _validate_role(role)
    return {"role": role, "in_flight": event_lifecycle.get_in_flight(role)}


# Status priority/severity rank for /human/queue ordering (high → low).
_HUMAN_QUEUE_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _parse_iso_to_epoch(iso_str):
    """Parse an ISO timestamp returned by `gh` into epoch seconds.

    Returns `float('inf')` on failure so items with unknown/unparseable
    timestamps sort LAST in ascending order — they should not appear at the
    head of "oldest first" rankings (#8704 review fix R2).
    """
    if not iso_str:
        return float("inf")
    try:
        from datetime import datetime, timezone
        # gh returns "2026-05-18T12:34:56Z" or with offset; normalize.
        s = iso_str.rstrip("Z")
        s = s.split(".")[0]
        # Try parse without timezone first.
        try:
            dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            # Try with offset (e.g. "+00:00")
            dt = datetime.fromisoformat(iso_str.rstrip("Z"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return float("inf")


def _gh_list_pending_human_issues():
    """Query GitHub for issues in any pending-human-* status.

    Returns a list of raw `gh issue list` JSON dicts. Empty list on any error
    so the endpoint never crashes the harness.
    """
    statuses = ("status:pending-human-review", "status:pending-human-setup")
    seen = {}
    for status in statuses:
        try:
            result = subprocess.run(
                ["gh", "issue", "list",
                 "--label", f"squidsquad,{status}",
                 "--state", "open",
                 "--json", "number,title,labels,updatedAt,url",
                 "--limit", "100"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", check=False, cwd=str(REPO_ROOT),
            )
            if result.returncode != 0:
                continue
            try:
                issues = json.loads(result.stdout) or []
            except json.JSONDecodeError:
                continue
            for issue in issues:
                num = issue.get("number")
                if num is not None and num not in seen:
                    seen[num] = issue
        except Exception:
            # Best-effort — never block the endpoint on `gh` failure.
            continue
    return list(seen.values())


def _summarize_pending_human(issue):
    """Compress a `gh issue list` row to the shape returned by /human/queue."""
    labels = {l.get("name", "") for l in issue.get("labels", [])}
    status = next(
        (l[len("status:"):] for l in labels if l.startswith("status:pending-human-")),
        "pending-human-unknown",
    )
    role = next(
        (l[len("role:"):] for l in labels if l.startswith("role:")),
        None,
    )
    severity = next(
        (l[len("severity:"):] for l in labels if l.startswith("severity:")),
        None,
    )
    priority = next(
        (l[len("priority:"):] for l in labels if l.startswith("priority:")),
        None,
    )
    return {
        "number": issue.get("number"),
        "title": issue.get("title", ""),
        "status": status,
        "role": role,
        "priority": priority or severity,
        "updated_at": issue.get("updatedAt", ""),
        "url": issue.get("url", ""),
    }


@app.get("/human/queue")
async def get_human_queue():
    """Items awaiting human action (#8704).

    Treats the human as another role assignee. Returns issues in any
    `status:pending-human-*` (currently `pending-human-review` and
    `pending-human-setup`) ordered by priority (high → low) then age
    (oldest first — longest-waiting bubbles up).

    Future TUIs / web UIs poll this on their own refresh loop (similar to
    the status line refactor in #8700).
    """
    raw = _gh_list_pending_human_issues()
    # #8704 review fix R1: defend against unexpected gh JSON shape (e.g.
    # `labels` as a string instead of a list). Skip rows that fail to
    # summarize rather than 500-ing the endpoint.
    items = []
    for issue in raw:
        try:
            items.append(_summarize_pending_human(issue))
        except Exception:
            continue

    def _sort_key(item):
        prio_rank = _HUMAN_QUEUE_PRIORITY_RANK.get(item.get("priority"), 99)
        # Older items sort first → use updated_at ascending.
        ts = _parse_iso_to_epoch(item.get("updated_at"))
        return (prio_rank, ts)

    items.sort(key=_sort_key)
    return {
        "count": len(items),
        "items": items,
    }


@app.get("/events/lifecycle")
async def get_event_lifecycle():
    """Event lifecycle overview — stream size, in-flight per role, persistence state (#7630 2-7)."""
    in_flight = {}
    try:
        roles = boot_remote._get_all_roles()
        for role in roles:
            ids = event_lifecycle.get_in_flight(role)
            if ids:
                in_flight[role] = ids
    except (SystemExit, Exception):
        pass
    return {
        "stream_size": len(event_stream),
        "in_flight": in_flight,
        "persisted": EVENT_STATE_FILE.exists(),
    }


@app.post("/agents/{role}/stop")
async def stop_agent(role: str):
    """Graceful stop — set intent=stopping (#4966). cycle_post queries API for intent."""
    _validate_role(role)

    # Set intent in memory — harness won't reboot after agent exits
    # cycle_post.py queries GET /agents/{role} and reads intent (#4966).
    # Only record `intent_set_at` on the transition INTO STOPPING; a repeat
    # stop request on an already-STOPPING agent must NOT extend the 60s
    # force-kill window (CONTEXT-4792.md §3.3 Q7).
    agent_state = state.get_agent(role) or AgentState(role)
    if agent_state.intent != AgentState.INTENT_STOPPING:
        agent_state.intent = AgentState.INTENT_STOPPING
        agent_state.intent_set_at = time.time()  # #4792 Phase 1
    state.set_agent(role, agent_state)
    state.save_state()

    _log(f"Stopped {role} (intent=stopping)")

    return {"role": role, "action": "stop", "message": "Stop requested"}


@app.post("/agents/{role}/restart")
async def restart_agent(role: str):
    """Restart agent. If idle, kill immediately and let auto-reboot fire (#8689).
    If mid-cycle, just set intent=restarting and let the agent exit cleanly at
    its next cycle boundary (#4966 graceful-restart behavior preserved)."""
    _validate_role(role)

    _log(f"Restarting {role}...")

    # Set intent — harness will auto-reboot when agent exits
    # cycle_post.py queries GET /agents/{role} and reads intent (#4966).
    # Only record `intent_set_at` on the transition INTO RESTARTING; a repeat
    # restart on an already-RESTARTING agent must NOT extend the 60s
    # force-kill window (CONTEXT-4792.md §3.3 Q7).
    agent_state = state.get_agent(role) or AgentState(role)
    if agent_state.intent != AgentState.INTENT_RESTARTING:
        agent_state.intent = AgentState.INTENT_RESTARTING
        agent_state.intent_set_at = time.time()  # #4792 Phase 1
    # #8695: restart will respawn the process → new boot must re-assert
    # bootup-complete before events flow again.
    agent_state.bootup_complete = False
    state.set_agent(role, agent_state)
    state.save_state()

    # #4792: stop is now expressed via harness intent — no sentinel to clean.
    clone_path = boot_remote._get_clone_path(role)
    clone_path_p = Path(clone_path)

    # #8689: if the agent is idle between cycles, kill the claude process
    # right now so the auto-reboot path (running periodic health-poll already
    # watches for is_dead + intent=restarting) fires within seconds instead
    # of waiting up to a full /loop interval (e.g. 30 minutes). For active
    # cycles, fall back to the graceful queued behavior.
    current_state = ""
    state_file = clone_path_p / ".squidsquad" / role / "current-state"
    try:
        current_state = state_file.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        pass

    immediate = current_state.startswith("idle")
    killed_pid = None
    if immediate:
        claude_pid, alive = reboot_agent._read_claude_pid(clone_path_p, role)
        if alive and claude_pid:
            _log(f"  {role}: idle — killing PID {claude_pid} for immediate reboot")
            try:
                reboot_agent._kill_process(claude_pid)
                killed_pid = claude_pid
            except Exception as e:
                _log(f"  {role}: WARNING — kill failed: {e}")
                immediate = False
        else:
            # Already dead — the auto-reboot loop will pick it up next tick.
            immediate = False

    if immediate:
        _log(f"  {role}: restart requested (idle path — killed PID {killed_pid})")
        return {
            "role": role,
            "action": "restart",
            "success": True,
            "immediate": True,
            "killed_pid": killed_pid,
            "message": "Restart requested — agent was idle, killed and will be auto-rebooted",
        }

    _log(f"  {role}: restart requested (intent=restarting)")
    return {
        "role": role,
        "action": "restart",
        "success": True,
        "immediate": False,
        "message": "Restart requested — agent will exit after current cycle and reboot",
    }


@app.post("/shutdown", status_code=202)
async def shutdown():
    """Stop all agents, then exit harness. Only stops agents that are running.

    Returns 202 Accepted immediately. Shutdown work runs in a background thread
    to avoid blocking the async event loop (time.sleep in async = blocked responses).
    """
    _log("Shutdown requested — starting background shutdown...")

    def _do_shutdown():
        """Background thread: stop agents, clean port file, exit."""
        roles = boot_remote._get_all_roles()

        running_roles = []
        for role in roles:
            # Use intent to check if already stopping (#4949)
            agent = state.get_agent(role)
            if agent and agent.intent == AgentState.INTENT_STOPPING:
                _log(f"  {role}: skip (already stopping)")
                continue
            needs_boot, _, _ = boot_remote._needs_boot(role)
            if needs_boot:
                _log(f"  {role}: skip (not running)")
                continue
            running_roles.append(role)

        if running_roles:
            _log(f"Stopping running agents: {', '.join(running_roles)}")
            for role in running_roles:
                clone_path = boot_remote._get_clone_path(role)
                # Set intent — cycle_post.py queries API for intent (#4966).
                # Only stamp intent_set_at on the transition INTO STOPPING so a
                # repeat /shutdown call does not extend the 60s force-kill clock.
                agent = state.get_agent(role) or AgentState(role, clone_path)
                if agent.intent != AgentState.INTENT_STOPPING:
                    agent.intent = AgentState.INTENT_STOPPING
                    agent.intent_set_at = time.time()  # #4792 Phase 1
                state.set_agent(role, agent)
            state.save_state()

            _log("Waiting for agents to idle (max 30s)...")
            for _ in range(6):
                all_idle = True
                for role in running_roles:
                    state_file = SQUIDSQUAD_DIR / role / "current-state"
                    try:
                        content = state_file.read_text(encoding="utf-8").strip()
                        if not content.startswith("idle"):
                            all_idle = False
                            break
                    except (OSError, FileNotFoundError):
                        pass
                if all_idle:
                    break
                time.sleep(5)

            for role in running_roles:
                clone_path = boot_remote._get_clone_path(role)
                claude_pid, alive = reboot_agent._read_claude_pid(Path(clone_path), role)
                if alive and claude_pid:
                    _log(f"  Killing {role} (PID {claude_pid})...")
                    reboot_agent._kill_process(claude_pid)
        else:
            _log("No running agents to stop.")

        for attempt in range(3):
            try:
                if HARNESS_PORT_FILE.exists():
                    HARNESS_PORT_FILE.unlink()
                    _log("Port discovery file deleted.")
                break
            except OSError as e:
                _log(f"WARNING: Could not delete port file (attempt {attempt + 1}/3): {e}")
                time.sleep(0.5)

        _log("Harness exiting.")
        time.sleep(1)
        os._exit(0)

    threading.Thread(target=_do_shutdown, daemon=True, name="shutdown").start()

    return {"status": "shutting_down", "message": "Shutdown initiated. Harness will exit shortly."}


# ---------------------------------------------------------------------------
# POST /merge — agent requests harness to merge a PR (#6126)
# ---------------------------------------------------------------------------

def _execute_transition(transition: dict):
    """Execute a status transition via tracker.py (#7630 Phase 4 closure side effect)."""
    number = transition.get("number")
    from_status = transition.get("from")
    to_status = transition.get("to")
    role = transition.get("role", "skill-lead")
    if not all([number, from_status, to_status]):
        raise ValueError(f"Incomplete transition: {transition}")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "tracker.py"), "transition",
         str(number), from_status, to_status, "--role", role],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tracker.py transition failed: {result.stderr.strip()}")


def _execute_comment(comment: dict):
    """Execute a tracker comment via tracker.py (#7630 Phase 4 closure side effect)."""
    number = comment.get("number")
    role = comment.get("role", "skill-lead")
    message = comment.get("message")
    if not all([number, message]):
        raise ValueError(f"Incomplete comment: {comment}")
    # Length guard: reject oversized or null-byte messages
    if len(message) > 4096 or "\x00" in message:
        raise ValueError(f"Message too long or contains null bytes (len={len(message)})")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "tracker.py"), "comment",
         str(number), "--role", role, "--message", message],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tracker.py comment failed: {result.stderr.strip()}")


def _emit_event(event_type, role, payload=None, **extra):
    """Emit an event into the harness event stream.

    Used by harness-owned operations (merge, compose) to emit events
    without going through the HTTP /events endpoint.
    """
    event = {
        "id": os.urandom(4).hex(),
        "event_type": event_type,
        "role": role,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": payload or {},
        "received_at": time.time(),
    }
    event.update(extra)
    event_lifecycle.append(event)
    _log_event(event)


def _get_pr_files(pr_number):
    """Get the list of files changed in a PR via gh CLI."""
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "files"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        return [f.get("path", "") for f in data.get("files", [])]
    except (json.JSONDecodeError, KeyError):
        return None


def _get_pr_branch(pr_number):
    """Get the head branch name of a PR."""
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "headRefName"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        return ""
    try:
        return json.loads(result.stdout).get("headRefName", "")
    except (json.JSONDecodeError, KeyError):
        return ""


def _parse_issue_from_branch(branch):
    """Extract issue number from branch name (e.g. squidsquad/skill/42 → 42)."""
    parts = branch.split("/")
    if len(parts) >= 2 and parts[-1].isdigit():
        return int(parts[-1])
    return None


@app.post("/merge", status_code=202)
async def merge_pr(request: Request):
    """Merge a PR asynchronously. Returns 202 Accepted immediately.

    Agents POST here instead of calling git_ops.py pr-merge directly.
    Harness executes merge, checks for references/ changes, runs compose
    if needed, and emits pr-merged + compose-completed events (#6126).

    Request body: {"pr_number": int, "branch": str, "role": str}
    """
    body = await request.json()
    pr_number = body.get("pr_number")
    branch = body.get("branch", "")
    role = body.get("role", "unknown")

    if not pr_number:
        raise HTTPException(status_code=400, detail="pr_number is required")

    _log(f"Merge requested: PR #{pr_number} by {role}")

    # Emit request-merge for audit trail
    _emit_event("request-merge", role, payload={
        "pr_number": str(pr_number),
        "branch": branch,
        "role": role,
    })

    def _do_merge():
        """Background thread: merge PR, detect references/ changes, compose."""
        try:
            # Import git_ops for the merge function
            import git_ops

            # Get files changed before merge (for compose detection)
            files_changed = _get_pr_files(pr_number) or []
            if not branch:
                actual_branch = _get_pr_branch(pr_number)
            else:
                actual_branch = branch
            issue_number = _parse_issue_from_branch(actual_branch)

            # Execute merge
            success, message = git_ops.pr_merge(pr_number)

            already_merged = message == "already merged"

            # Emit pr-merged event
            _emit_event("pr-merged", "harness", payload={
                "pr_number": str(pr_number),
                "branch": actual_branch,
                "issue_number": str(issue_number) if issue_number else "",
                "files_changed": files_changed,
                "success": success,
                "already_merged": already_merged,
                "error": "" if success else message,
                "requesting_role": role,
            })

            if not success:
                _log(f"Merge failed for PR #{pr_number}: {message}")
                return

            if already_merged:
                _log(f"PR #{pr_number} was already merged")
                return

            # Check if references/ files were changed
            refs_changed = any(f.startswith("references/") for f in files_changed)

            if refs_changed:
                _log(f"PR #{pr_number} touched references/ — running compose...")
                compose_result = subprocess.run(
                    [sys.executable, str(SCRIPT_DIR / "compose.py"), "deploy-all"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    check=False, cwd=str(REPO_ROOT),
                )
                compose_success = compose_result.returncode == 0
                compose_error = "" if compose_success else compose_result.stderr.strip()[:500]

                _emit_event("compose-completed", "harness", payload={
                    "success": compose_success,
                    "error": compose_error,
                    "trigger_pr": str(pr_number),
                })

                if compose_success:
                    _log(f"Compose completed successfully after PR #{pr_number}")
                    # AC-10: Reboot affected agents after compose
                    _reboot_affected_agents(pr_number, files_changed)
                else:
                    _log(f"WARNING: Compose failed after PR #{pr_number}: {compose_error[:100]}")
            else:
                _log(f"PR #{pr_number} merged — no references/ changes, skipping compose")

        except Exception as e:
            _log(f"ERROR in merge thread: {e}")
            _emit_event("pr-merged", "harness", payload={
                "pr_number": str(pr_number),
                "branch": branch,
                "issue_number": "",
                "files_changed": [],
                "success": False,
                "error": str(e),
                "requesting_role": role,
            })

    threading.Thread(target=_do_merge, daemon=True, name=f"merge-{pr_number}").start()

    return {"status": "accepted", "message": f"Merge of PR #{pr_number} initiated."}


def _reboot_affected_agents(pr_number, files_changed):
    """Reboot agents whose CLAUDE.md or SOUL.md changed after compose (#6126 AC-10).

    Checks which agents' composed output was updated and reboots only those.
    """
    affected_roles = set()
    for f in files_changed:
        # Check if the changed file is a role template or sub-skill
        # that would affect composed output
        if f.startswith("references/roles/") or f.startswith("references/sub-skills/"):
            # All roles could be affected — check which composed files actually changed
            break
    else:
        # No role templates or sub-skills changed — check composed output directly
        return

    # Check which composed CLAUDE.md/SOUL.md files were modified by compose
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        return

    for line in result.stdout.strip().splitlines():
        line = line.strip()
        # Match .squidsquad/<role>/CLAUDE.md or SOUL.md
        if line.startswith(".squidsquad/") and (line.endswith("/CLAUDE.md") or line.endswith("/SOUL.md")):
            parts = line.split("/")
            if len(parts) >= 3:
                role = parts[1]
                affected_roles.add(role)

    if not affected_roles:
        _log(f"Compose after PR #{pr_number}: no agent templates changed — no reboots needed")
        return

    _log(f"Compose after PR #{pr_number}: rebooting affected agents: {', '.join(sorted(affected_roles))}")
    for role in affected_roles:
        agent = state.get_agent(role)
        if agent and agent.intent == AgentState.INTENT_RUNNING:
            agent.intent = AgentState.INTENT_RESTARTING
            agent.intent_set_at = time.time()  # #4792 Phase 1
            # #8695: match the other three restart paths — close the window
            # where events would still dispatch after we've marked the agent
            # for restart but before its process actually dies.
            agent.bootup_complete = False
            state.set_agent(role, agent)
    state.save_state()


# ---------------------------------------------------------------------------
# Port management
# ---------------------------------------------------------------------------

def find_free_port(default: int = DEFAULT_PORT) -> int:
    """Find an available port, preferring the default."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", default))
        s.close()
        return default
    except OSError:
        s.close()
        # Find any free port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port


def _read_config_port() -> int:
    """Read harness port from config.md or env var."""
    # Env var takes priority
    env_port = os.environ.get("SQUIDSQUAD_HARNESS_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass

    # Try config.md
    try:
        import config as cfg
        val = cfg._parse_field(cfg._read_config(), "Harness", "Port")
        if val:
            return int(val)
    except (SystemExit, ValueError, Exception):
        pass

    return DEFAULT_PORT


# ---------------------------------------------------------------------------
# Console banner
# ---------------------------------------------------------------------------

def _print_banner(port: int):
    """Print the harness startup banner."""
    print()
    print("  ▗▄▖")
    print("  ▟█ █▙")
    print(" ▐█• •█▌")
    print("███████")
    print("▐█████▌")
    print(" ▐▌▐▌▐▌")
    print()
    print("S Q U I D S Q U A D   H A R N E S S")
    print(f"Port: {port} | API: http://localhost:{port}/status")
    print(f"PID: {os.getpid()} | Ctrl+C to stop")
    print("─" * 50)
    print()


# ---------------------------------------------------------------------------
# External activity detector (#7630 2-4)
# ---------------------------------------------------------------------------

class ExternalActivityDetector:
    """Polls GitHub for external changes and emits assigned-to events (#7630 2-4).

    Runs as a daemon thread. Detects new/updated issues with status:approved
    or status:open that are assigned to agent roles. Filters out SquidSquad's
    own changes by checking recent comment authors against agent role names.
    Deduplicates by tracking previously emitted issue numbers.
    """

    AGENT_ROLES = {"skill", "pm", "qa", "dm"}

    def __init__(self, poll_interval: int = 60):
        self._poll_interval = poll_interval
        self._running = False
        self._thread = None
        self._last_check_epoch = 0.0  # epoch seconds — avoids ISO string comparison
        self._emitted_issues: dict[int, None] = {}  # ordered dedup: issues already emitted
        # Lock guards _emitted_issues against concurrent mutation. The
        # detector's own poller thread is the only writer now that #8914
        # removed TrackerHandoffDispatcher, but the lock stays — the
        # compound eviction (next(iter) + del) still needs serialization
        # if another thread is ever added.
        self._emitted_lock = threading.Lock()

    def is_emitted(self, issue_num):
        """Thread-safe membership check on _emitted_issues."""
        with self._emitted_lock:
            return issue_num in self._emitted_issues

    def mark_emitted(self, issue_num):
        """Thread-safe insert + bounded eviction on _emitted_issues (#8694)."""
        with self._emitted_lock:
            self._emitted_issues[issue_num] = None
            while len(self._emitted_issues) > 500:
                oldest = next(iter(self._emitted_issues))
                del self._emitted_issues[oldest]

    def start(self):
        """Start the detector daemon thread."""
        if self._running:
            return
        self._running = True
        self._last_check_epoch = time.time()
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="activity-detector"
        )
        self._thread.start()
        _log("External activity detector started")

    def stop(self):
        """Signal the detector to stop (daemon thread dies with process)."""
        self._running = False

    def _poll_loop(self):
        time.sleep(10)  # initial delay — let harness finish startup
        while self._running:
            try:
                self._check_for_changes()
            except Exception as e:
                _log(f"Activity detector error: {e}")
            time.sleep(self._poll_interval)

    @staticmethod
    def _parse_iso_epoch(iso_str: str) -> float:
        """Parse ISO 8601 timestamp to epoch seconds. Handles sub-second precision."""
        # Strip trailing Z and any sub-second part for consistent parsing
        clean = iso_str.rstrip("Z").split(".")[0]
        try:
            from datetime import datetime, timezone
            dt = datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except (ValueError, AttributeError):
            return 0.0

    def _is_agent_update(self, issue: dict) -> bool:
        """Check if the most recent comment was from a SquidSquad agent."""
        # gh returns comments in the issue JSON if requested — but we only
        # have labels and updatedAt. Check if the title starts with agent prefixes.
        title = issue.get("title", "")
        return title.startswith(("ISSUE:", "TASK:"))  # all agent-filed issues have these prefixes

    def _check_for_changes(self):
        """Poll GitHub for actionable changes since last check."""
        result = subprocess.run(
            ["gh", "issue", "list", "--label", "squidsquad",
             "--state", "open", "--json",
             "number,title,labels,updatedAt",
             "--limit", "50"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return

        try:
            issues = json.loads(result.stdout)
        except json.JSONDecodeError:
            return

        check_time = time.time()

        for issue in issues:
            issue_num = issue.get("number", 0)

            # Dedup: skip issues already emitted (thread-safe via #8694)
            if self.is_emitted(issue_num):
                continue

            # Skip agent-filed issues to prevent self-triggering loops
            if self._is_agent_update(issue):
                continue

            # Time filter: only process issues updated since last check
            updated_epoch = self._parse_iso_epoch(issue.get("updatedAt", ""))
            if updated_epoch <= self._last_check_epoch:
                continue

            labels = {l.get("name", "") for l in issue.get("labels", [])}

            # Only emit for actionable statuses
            if not (labels & {"status:approved", "status:open"}):
                continue

            # Determine target role (first role label sorted; multi-role emits for first only)
            role_labels = sorted(l for l in labels if l.startswith("role:"))
            if not role_labels:
                continue
            target_role = role_labels[0].replace("role:", "")

            # Emit assigned-to event
            _emit_event("assigned-to", "harness", payload={
                "issue_number": str(issue_num),
                "title": issue.get("title", ""),
                "target_role": target_role,
                "event_context": f"Issue #{issue_num} updated",
            })
            self.mark_emitted(issue_num)

        self._last_check_epoch = check_time
        # Eviction now happens inside mark_emitted() under _emitted_lock.


# Global detector instance
activity_detector = ExternalActivityDetector()


# TrackerHandoffDispatcher was removed in #8914. CONTEXT.md §2 locks the
# harness as a pure broadcast pipe with no tracker observation, no dispatch
# logic, and no per-role queue knowledge. Tracker handoff handling lives in
# the agents themselves — they consult the forge via tracker.py work-queue
# when they wake.


# ---------------------------------------------------------------------------
# Ctrl+C escalation (#4966)
# ---------------------------------------------------------------------------

class CtrlCHandler:
    """Three-stage Ctrl+C escalation for graceful shutdown (#4966).

    1st Ctrl+C: graceful stop (set all agents intent=stopping, wait for cycle end)
    2nd Ctrl+C within 5s: warn about force exit
    3rd Ctrl+C: exit harness immediately (agents survive in their terminals)
    """

    def __init__(self):
        self._press_count = 0
        self._last_press = 0.0
        self._shutting_down = False

    def handle(self, signum, frame):
        now = time.time()

        # Reset counter if >5s since last press
        if now - self._last_press > 5:
            self._press_count = 0
        self._last_press = now
        self._press_count += 1

        if self._press_count == 1:
            self._graceful_stop()
        elif self._press_count == 2:
            _log("⚠️  Press Ctrl+C again to FORCE KILL all agents.")
        else:
            self._force_kill()

    def _graceful_stop(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        _log("Graceful shutdown — setting all agents to stopping...")

        roles = []
        try:
            roles = boot_remote._get_all_roles()
        except Exception:
            pass

        for role in roles:
            agent = state.get_agent(role)
            if agent and agent.status == "running":
                # Only stamp intent_set_at on the transition INTO STOPPING; a
                # second Ctrl+C must not extend the 60s force-kill clock.
                if agent.intent != AgentState.INTENT_STOPPING:
                    agent.intent = AgentState.INTENT_STOPPING
                    agent.intent_set_at = time.time()  # #4792 Phase 1
                state.set_agent(role, agent)
                _log(f"  {role}: intent=stopping")
        state.save_state()

        _log("Agents will exit after current cycle. Ctrl+C again to force.")
        # Let uvicorn handle the actual shutdown
        raise KeyboardInterrupt

    def _force_kill(self):
        _log("Force exit — harness stopping. Agents survive in their terminals.")
        # Agents run in independent terminal windows — they survive harness exit.
        # On harness restart, crash recovery via .harness-state.json resumes monitoring.
        try:
            HARNESS_PORT_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        os._exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SquidSquad Harness — agent lifecycle manager")
    parser.add_argument("--port", type=int, default=None, help=f"Listen port (default: {DEFAULT_PORT})")

    args = parser.parse_args()

    # Determine port
    desired_port = args.port or _read_config_port()
    actual_port = find_free_port(desired_port)

    if actual_port != desired_port:
        print(f"Port {desired_port} in use — using {actual_port}")

    state.port = actual_port
    _print_banner(actual_port)

    # Install Ctrl+C escalation handler (#4966)
    ctrl_c = CtrlCHandler()
    signal.signal(signal.SIGINT, ctrl_c.handle)

    # Run uvicorn in a daemon thread so the main thread stays available
    # for signal handling. On Windows, signal handlers set via
    # signal.signal() only fire in the main thread — if uvicorn.run()
    # blocks the main thread, Ctrl+C is never delivered to our handler.
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=actual_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True, name="uvicorn")
    server_thread.start()

    try:
        # Main thread waits — signal.signal handler fires here on Ctrl+C
        while server_thread.is_alive():
            server_thread.join(timeout=1.0)
    except KeyboardInterrupt:
        _log("Harness stopped.")
        server.should_exit = True
        server_thread.join(timeout=5)
    finally:
        # Ensure port file cleanup
        try:
            HARNESS_PORT_FILE.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
