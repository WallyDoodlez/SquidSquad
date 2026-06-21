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
import traceback
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure script dir is importable
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
REPO_ROOT = SCRIPT_DIR.parent.parent


def _resolve_squidsquad_dir() -> Path:
    """#9398: honor SQUIDSQUAD_DIR env var so isolated test harnesses
    can run in a tmpdir without overwriting the live .harness-port
    file (which would cause every other SquidSquad process to route
    to the test harness on its next port discovery).

    Default unchanged for production callers — value is identical to
    the previous module-level constant when the env var is unset.

    Handles three foot-guns flagged by Sonnet code review of #9614:
    - Empty string falls back to the default (not interpreted as cwd).
    - Trailing whitespace is stripped (a frequent `export
      SQUIDSQUAD_DIR=$tmp ` typo).
    - Leading ``~`` is expanded (``~/sq-test`` becomes the user's
      home). Relative paths are NOT resolve()d — caller decides if
      absoluteness matters (resolve() requires the path to exist,
      which it may not yet for first-time test setup).
    """
    raw = (os.environ.get("SQUIDSQUAD_DIR") or "").strip()
    if not raw:
        return REPO_ROOT / ".squidsquad"
    return Path(raw).expanduser()


SQUIDSQUAD_DIR = _resolve_squidsquad_dir()
HARNESS_PORT_FILE = SQUIDSQUAD_DIR / ".harness-port"

DEFAULT_PORT = 7373
# #12825: dedicated exit code that signals the supervised launcher
# (restart-harness.bat / .sh) to RELAUNCH the harness, vs a clean exit 0 (do not
# relaunch). Mirrors the agent self-restart exit-42 convention (HARNESS-ARCH
# §7.4) — the wrapper owns harness lifecycle the way the harness owns agent
# lifecycle. POST /restart triggers this exit; the one-shot launcher ignores it
# (harness simply ends) so the behavior degrades gracefully without the wrapper.
HARNESS_RESTART_EXIT_CODE = 42
# #12825 DS-F2: /shutdown and /restart each spawn a teardown thread that ends in
# os._exit() with a different code (0 vs 42). Two concurrent teardown requests
# would race to os._exit() — last writer wins the exit code, so the wrapper
# might relaunch a harness an operator meant to stop (or vice-versa). This
# lock+flag makes "begin teardown" a single-winner gate; the loser gets 409.
_teardown_lock = threading.Lock()
_teardown_in_progress = False


def _begin_teardown() -> bool:
    """Atomically claim the single teardown slot. Returns True for the first
    caller (it should proceed), False if a teardown is already underway."""
    global _teardown_in_progress
    with _teardown_lock:
        if _teardown_in_progress:
            return False
        _teardown_in_progress = True
        return True


HEALTH_POLL_INTERVAL = 5  # seconds
# PRD-E E3 (#10682): cadence of the L4-write file-watcher supervisor.
# The watchdog Observer runs as its own thread; this interval governs
# how quickly the supervisor notices a crashed Observer and respawns it.
L4_WATCHER_SUPERVISE_INTERVAL = 5  # seconds
# #4792 Phase 1 (Q7): seconds after intent flip to STOPPING/RESTARTING before
# the harness force-kills the claude PID. The cooperative path (cycle_post
# exit 42 → /quit → process exits) typically wins in under 5s; this safety
# net catches the case where the agent never reaches a cycle boundary or
# /quit hangs (CONTEXT-4792.md §3.3 Q7).
FORCE_KILL_TIMEOUT_SECONDS = 60
HARNESS_STATE_FILE = SQUIDSQUAD_DIR / ".harness-state.json"

# #12244 P2 — crash-loop / session-limit backoff. A spawn that dies within
# FAST_DEATH_WINDOW_SECONDS of (re)spawn counts as a "fast death". After
# FAST_DEATH_THRESHOLD consecutive fast deaths the auto-reboot path stops tight-
# looping and applies exponential backoff (capped) before the next respawn,
# surfacing a paused status instead of silently burning quota. This is timing-
# based and cause-agnostic — it catches the Claude session/usage-limit exit-1
# loop (the #12244 trigger) AND any other fast-crash cause (stale lock, bad
# compose) without parsing claude's terminal output (which thin_launcher does
# not capture). A spawn that survives past the window resets the counter
# (genuine recovery). A one-off crash (first fast death, or a long-lived agent
# that finally dies) reboots immediately as before.
FAST_DEATH_WINDOW_SECONDS = 60
FAST_DEATH_THRESHOLD = 3
CRASH_BACKOFF_BASE_SECONDS = 30
CRASH_BACKOFF_CAP_SECONDS = 1800  # 30m — a sane ceiling, not infinite

# #12409 — SLOW reboot-loop breaker (frequency-based), complementing the #12244
# fast-death (lifetime) breaker above. #12244 only trips on >=FAST_DEATH_THRESHOLD
# deaths that each lived <FAST_DEATH_WINDOW_SECONDS; a loop where each session
# lives LONGER than that window (qa's incident: 4 auto-reboots in ~18min, each
# >60s apart) keeps resetting consecutive_fast_deaths, so #12244 never engages
# and the agent churns freely. This breaker is lifetime-agnostic: if an agent is
# auto-rebooted >=SLOW_LOOP_THRESHOLD times within SLOW_LOOP_WINDOW_SECONDS, it
# backs off (same capped-exponential machinery + crash-looping status) instead
# of rebooting again. The two breakers compose — fast-death takes precedence; a
# slow loop that escapes it is caught here. Cause-agnostic, same as #12244.
SLOW_LOOP_WINDOW_SECONDS = 900  # 15m sliding window
SLOW_LOOP_THRESHOLD = 3         # reboots within the window before backing off

# #12458 (#12271 slice c) — pause-aware liveness guard. Agent silence / a dead
# PID is treated as death ONLY when no hook explains it. Each "explained pause"
# carries a STALENESS CEILING so a stuck/never-cleared flag can never mask a
# genuine death forever (the AC4 contract: past the ceiling, the agent is
# wedged and the normal death path resumes). The ceilings are generous —
# set above the longest LEGITIMATE duration of each state.
#   tool_call_max — longest legit single tool call (full test suite, slow
#     build, long subagent). PreToolUse sets an in-flight deadline; PostToolUse
#     clears it. Within the deadline a silent/dead agent is "running a tool",
#     past it (still no PostToolUse) it is wedged.
TOOL_CALL_MAX_SECONDS = 900          # 15m hard ceiling for one tool call
#   compacting — Claude Code summarising context in place (PreCompact, cleared
#     by PostCompact). Bounded so a crash mid-compaction still reboots.
COMPACTING_MAX_SECONDS = 300         # 5m
#   waiting — blocked on a human/permission/idle prompt (Notification). Cleared
#     by the next activity heartbeat. Bounded generously: a truly-waiting agent
#     stays alive (it still heartbeats nothing, but it is not dead); a crashed
#     agent whose stale "waiting" flag was never cleared falls through after
#     the ceiling so the normal death path can reboot it.
WAITING_MAX_SECONDS = 1800           # 30m
#   StopFailure causes that mean "throttled, not faulty" → back off rather than
#     immediately respawn (a tight respawn would re-hit the same limit). Folds
#     into the #12244 backoff. Other causes (auth/billing) are surfaced but do
#     NOT auto-backoff (they need operator action, not a wait).
STOP_FAILURE_BACKOFF_CAUSES = frozenset({"rate_limit", "overloaded"})
STOP_FAILURE_RECENT_SECONDS = 180    # a StopFailure older than this is stale
#   #12271 slice d — dispatch-relative activity grace. After work is dispatched
#     to an agent (an assigned-to nudge), a healthy agent emits an activity
#     heartbeat within this window (it wakes, reads the forge, makes tool calls
#     → PostToolUse). Past the window with NO heartbeat since the dispatch AND
#     no pause signal = wedged/zombie (the #10855 inert-boot catch). Generous so
#     a slow first tool call (covered separately by the in-flight pause once
#     PreToolUse fires) or model latency never false-positives; tunable from the
#     shadow-mode divergence data this slice gathers.
ACTIVITY_GRACE_SECONDS = 600         # 10m
#   #13179 (#12271 Slice A) — boot-completion grace. A not-yet-booted agent
#     (bootup_complete=False) is legitimately mid-boot only for so long; past
#     this window with no bootup-complete it is a wedged boot, not a slow one
#     (the #12271 qa incident sat bootup_complete=False ~54m at intent=deploying).
#     Bounds the otherwise-unbounded "booting" escape in progress_liveness so a
#     never-completing boot reads wedged in the SHADOW verdict (does NOT drive
#     reboot until the #12492 cutover). Generous so a slow first boot never
#     false-positives; tunable from the same shadow-mode divergence data.
BOOT_GRACE_SECONDS = 600             # 10m

# #9242: Diagnostic escape hatch. When True (set by `main()` from
# `--no-auto-start` or `SQUIDSQUAD_HARNESS_NO_AUTO_START=1`), the
# deferred-init thread skips the auto-spawn-all-agents block. Lets
# operators isolate the auto-start path from HTTP wedges during
# diagnosis: boot harness, confirm `curl /status` works, then start
# agents manually via `POST /agents/{role}/start`.
_NO_AUTO_START = False

# #10538: Sibling escape hatch for the HEALTH-POLLER auto-reboot path
# (lines ~341). When True (set by `main()` from `--no-auto-reboot` or
# `SQUIDSQUAD_HARNESS_NO_AUTO_REBOOT=1`), the poller still observes
# agent death and updates state, but does NOT call `boot_agent(role)`
# to spawn a replacement. Use when the operator wants the harness to
# coordinate already-running agents without second-guessing context-
# pressure restarts or fighting the three-claude-populations problem
# (HARNESS-ARCH §14) during a harness restart.
_NO_AUTO_REBOOT = False

# PRD-E E5 (#10684): operator escape hatch for the E1 boot/restart
# freshness gate. When True (set by ``main()`` from
# ``--no-freshness-check`` or ``SQUIDSQUAD_HARNESS_NO_FRESHNESS_CHECK=1``),
# the lifespan SKIPS ``compose_freshness.check_and_repair`` entirely
# and proceeds straight to deferred-init. Use ONLY for emergency boots
# where the operator already knows the compose set is correct and
# needs the harness up before the (potentially slow) compose subprocess
# can run. The flag does NOT bypass the spawn-refusal contract — if a
# previous boot persisted ``compose_freshness_failed=True``, that's
# still honored. Operators bypassing the check are responsible for
# verifying source freshness themselves.
_NO_FRESHNESS_CHECK = False

import boot_remote
import health_check
import process_utils
import reboot_agent

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, Response
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
                 "last_cycle_end", "last_cycle_type", "bootup_complete",
                 # #12244 P2 — crash-loop / session-limit backoff
                 "last_spawn_at", "consecutive_fast_deaths",
                 "reboot_blocked_until",
                 # #12409 — frequency-based slow-loop breaker (reboot timestamps)
                 "reboot_history",
                 # #12418 — last SessionEnd hook reason (graceful-exit signal)
                 "last_session_end",
                 # #12443 — activity heartbeat (progress-based liveness)
                 "last_activity_at", "last_activity",
                 # #12458 — pause-aware liveness guard (explained-silence state)
                 "in_flight_until", "waiting_since", "compacting_since",
                 "last_stop_failure",
                 # #12271 slice d — dispatch reference for progress-liveness
                 "last_dispatch_at")

    # Intent values:
    #   "running"    — agent should be alive; auto-reboot on death (#4949)
    #   "stopping"   — graceful stop requested; do NOT reboot after death
    #   "restarting" — graceful restart; reboot after death
    #   "stopped"    — agent died as requested; terminal state
    INTENT_RUNNING = "running"
    INTENT_STOPPING = "stopping"
    INTENT_RESTARTING = "restarting"
    INTENT_STOPPED = "stopped"
    # #12912 (deploy-signal recompose model): a coordinated deploy halt. Set the
    # moment the harness emits a deploy-signal (AGENT-RUNTIME §5.2 intent-
    # sequencing rule), BEFORE the agent halts and its PID dies — so the health
    # poller does not misread the deploy-halt death as a crash and auto-respawn
    # it out of order (AC9). The deploy sequence (HARNESS-ARCH §7.1) owns the
    # respawn; it resets intent → RUNNING after the fresh PID boots.
    INTENT_DEPLOYING = "deploying"

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
        # #12244 P2 — crash-loop backoff bookkeeping. last_spawn_at is stamped
        # on every (re)spawn so the poller can measure how long the process
        # lived; consecutive_fast_deaths counts back-to-back fast deaths;
        # reboot_blocked_until holds off the next respawn while backing off.
        self.last_spawn_at = None
        self.consecutive_fast_deaths = 0
        self.reboot_blocked_until = None
        # #12409 — auto-reboot timestamps (epoch) within the sliding
        # SLOW_LOOP_WINDOW_SECONDS, for the frequency-based slow-loop breaker.
        # Pruned to the window on every record/read; persisted across restarts.
        self.reboot_history = []
        # #12418 — last SessionEnd hook report: {"reason": <stop_reason>,
        # "at": <epoch>}, or None if no SessionEnd seen since boot. The
        # PRESENCE of an entry stamped after last_spawn_at means the agent
        # exited GRACEFULLY (a hook ran); its ABSENCE before a dead PID means
        # a crash. The reboot decision (update_health) keys off that to avoid
        # counting graceful exits toward the #12244 crash-loop streak.
        self.last_session_end = None
        # #12443 — activity heartbeat (HARNESS-ARCH §15.1). last_activity_at is
        # the epoch of the most recent heartbeat (a PostToolUse / PostToolUse-
        # Failure command hook, or a cycle_post emit); last_activity carries the
        # enriched context ({at, event, tool, phase}, §15.2) for display. A
        # working loop emits these continuously; a wedged loop stops, so silence
        # — evaluated relative to dispatched work — is the death signal.
        # OBSERVATIONAL ONLY this slice (#12443): recorded + exposed, does NOT
        # yet drive the reboot decision (that is #12271 slice d).
        self.last_activity_at = None
        self.last_activity = None
        # #12458 — pause-aware liveness guard (HARNESS-ARCH §15.1). Each field
        # is an "explained silence" set by a hook and consumed by the reboot
        # decision via active_pause(); each has a staleness ceiling so a never-
        # cleared flag cannot mask a genuine death forever (AC4/AC5).
        #   in_flight_until — epoch deadline (PreToolUse set: now+tool_call_max;
        #     PostToolUse/PostToolUseFailure clear). now < deadline → mid-call.
        #   waiting_since — epoch a Notification (permission/idle prompt) fired;
        #     cleared by the next activity heartbeat. Agent blocked on input.
        #   compacting_since — epoch PreCompact fired (PostCompact clears).
        #   last_stop_failure — {"cause": <str>, "at": <epoch>}; a recent
        #     rate_limit/overloaded means "throttled" → back off, not respawn.
        self.in_flight_until = None
        self.waiting_since = None
        self.compacting_since = None
        self.last_stop_failure = None
        # #12271 slice d — epoch of the last work dispatched to this agent (an
        # assigned-to nudge emitted by the ExternalActivityDetector). The
        # progress-liveness check measures activity-heartbeat silence RELATIVE to
        # this (HARNESS-ARCH §15.1: liveness is dispatch-relative, not a pure
        # timer) so a legitimately idle agent — nothing dispatched — is never
        # judged dead. None until the first dispatch.
        self.last_dispatch_at = None

    def reset_session_telemetry(self):
        """Clear per-session activity + pause telemetry on a fresh (re)spawn.

        #13113: the spawn paths already reset claude_pid / bootup_complete /
        last_session_end / last_dispatch_at, but left these per-session fields
        carrying the OLD session's values across the PID boundary. A respawned
        record then showed the dead session's last_activity_at (frozen at the
        pre-kill timestamp) until the new session landed its first heartbeat —
        making a healthy fresh agent read as wedged, and (via a stale
        in_flight_until) holding off death-detection in active_pause(). Reset
        them to their fresh-AgentState defaults so a respawned record is
        indistinguishable from a first boot.

        Scope: only the per-session activity/pause telemetry. Crash-loop and
        backoff bookkeeping (last_spawn_at, consecutive_fast_deaths,
        reboot_history, reboot_blocked_until, last_stop_failure) is meant to
        PERSIST across respawns by design and is deliberately not touched here.
        """
        self.last_activity_at = None
        self.last_activity = None
        self.in_flight_until = None
        self.waiting_since = None
        self.compacting_since = None

    def active_pause(self, now):
        """#12458 — return a short reason string if a hook currently explains
        this agent's silence/death (so the reboot decision should HOLD OFF), or
        None if nothing explains it (→ treat as a candidate death).

        Each branch is bounded by its staleness ceiling: an explained pause only
        suppresses reboot for as long as that state could LEGITIMATELY last —
        past the ceiling the flag is treated as stale and ignored, so a crash
        that left a flag set still reboots once the ceiling elapses (AC4/AC5).
        Order is by confidence: an in-flight tool call is the strongest signal.
        """
        # DS-REVIEW-12458-guard F2: bound the in-flight hold by the SAME ceiling
        # the deadline was set with, so a stale/never-cleared deadline or a
        # backward clock step (NTP) can't hold the reboot longer than one
        # legitimate tool call. The deadline must be in the future (diff > 0) but
        # not by more than tool_call_max — the clock-skew guard the other
        # branches get via `0 <= age < MAX`, expressed here on the deadline.
        if (self.in_flight_until is not None
                and 0 < self.in_flight_until - now <= TOOL_CALL_MAX_SECONDS):
            return "in-flight"
        if (self.compacting_since is not None
                and 0 <= now - self.compacting_since < COMPACTING_MAX_SECONDS):
            return "compacting"
        if (self.waiting_since is not None
                and 0 <= now - self.waiting_since < WAITING_MAX_SECONDS):
            return "waiting"
        return None

    def stopfailure_backoff_due(self, now):
        """#12458 (AC3d) — True if the most recent StopFailure is a recent
        throttle (rate_limit/overloaded), meaning a dead agent should BACK OFF
        rather than respawn immediately (an immediate respawn would re-hit the
        same limit). Stale or non-throttle causes (auth/billing) return False —
        those need operator action, surfaced elsewhere, not an auto-wait."""
        sf = self.last_stop_failure
        if not isinstance(sf, dict):
            return False
        cause = sf.get("cause")
        at = sf.get("at") or 0
        return (cause in STOP_FAILURE_BACKOFF_CAUSES
                and 0 <= now - at < STOP_FAILURE_RECENT_SECONDS)

    def _prune_reboot_history(self, now):
        """#12409 — drop reboot timestamps older than SLOW_LOOP_WINDOW_SECONDS."""
        cutoff = now - SLOW_LOOP_WINDOW_SECONDS
        self.reboot_history = [t for t in self.reboot_history if t >= cutoff]

    def record_reboot(self, now):
        """#12409 — record an auto-reboot for the frequency-based slow-loop
        breaker, pruning to the sliding window."""
        self.reboot_history.append(now)
        self._prune_reboot_history(now)

    def recent_reboot_count(self, now):
        """#12409 — count of auto-reboots within SLOW_LOOP_WINDOW_SECONDS (prunes
        as a side effect so a stable agent's history empties over time)."""
        self._prune_reboot_history(now)
        return len(self.reboot_history)

    def progress_liveness(self, now):
        """#12271 slice d — progress-based liveness verdict (HARNESS-ARCH §15.1).

        Returns (alive: bool, reason: str) derived from PROGRESS signals
        (activity heartbeat + pause guard + dispatch reference) instead of PID
        existence. "Dead" = work was dispatched, the grace window elapsed, NO
        activity heartbeat has landed since that dispatch, and no hook explains
        the silence. This catches the zombie PID-liveness cannot: an alive
        process doing zero work (#10855 / #10440).

        SHADOW / OBSERVATIONAL this slice — computed and logged alongside the PID
        decision to validate divergence; it does NOT yet drive the reboot. The
        cutover (making this authoritative + demoting PID to teardown-only) is a
        later, separately-reviewed step once the shadow data confirms no false
        positives (killing a live agent) or false negatives (missing a death).

        THREAD-SAFETY (DS-c1 F2): this reads several fields that other daemon
        threads write under ``state._lock`` (the EAD writes ``last_dispatch_at``;
        the activity/pause hooks write ``last_activity_at`` and the pause flags).
        The verdict is a compound read across those fields, so callers MUST hold
        ``state._lock`` for a consistent snapshot. The intended call site
        (``update_health``) already holds it when it reads agent state for the
        PID check, so wiring this in there satisfies the contract for free.
        """
        # A not-yet-booted agent has no heartbeat baseline — within a generous
        # boot-grace it may legitimately be mid-boot, so treat it as alive. But
        # the escape is BOUNDED (#13179 / #12271 Slice A): a boot that never
        # completes is a wedge, not a slow boot (the qa incident sat
        # bootup_complete=False ~54m). Age it from the most recent spawn
        # (last_spawn_at; fall back to boot_time) — past BOOT_GRACE_SECONDS with
        # no bootup-complete it reads wedged. If we have no spawn reference we
        # cannot age it, so stay conservative and report booting (never
        # false-positive a death we cannot time). Shadow-only: this changes the
        # logged verdict, not the reboot decision (cutover is #12492).
        if not self.bootup_complete:
            boot_ref = (self.last_spawn_at
                        if self.last_spawn_at is not None else self.boot_time)
            if boot_ref is not None and now - boot_ref > BOOT_GRACE_SECONDS:
                return False, "wedged-boot-timeout"
            return True, "booting"
        # An explained pause (in-flight tool call / compacting / waiting) means
        # the silence is accounted for — alive. Reuses the slice-c guard so the
        # two liveness models share one definition of "explained silence".
        pause = self.active_pause(now)
        if pause is not None:
            return True, pause
        # No work dispatched → legitimately idle → never a false-positive death.
        if self.last_dispatch_at is None:
            return True, "idle-no-dispatch"
        # Within the post-dispatch grace window → too early to call it wedged.
        if now - self.last_dispatch_at <= ACTIVITY_GRACE_SECONDS:
            return True, "dispatch-grace"
        # Activity heartbeat landed at/after the dispatch → the agent acted on
        # the work → alive.
        if (self.last_activity_at is not None
                and self.last_activity_at >= self.last_dispatch_at):
            return True, "active"
        # Dispatched, grace elapsed, no activity since, nothing explains it →
        # wedged / zombie.
        return False, "wedged-no-activity-since-dispatch"

    def should_advance_dispatch(self):
        """#12271 slice d — whether an incoming dispatch should (re)stamp
        last_dispatch_at (the progress-liveness grace clock).

        Advance ONLY when the agent is RUNNING (DS-c1 F4: never stamp a
        stopped/stopping agent) AND has caught up on prior dispatched work —
        there's no prior dispatch, or the agent acted since it
        (last_activity_at >= last_dispatch_at). A re-nudge of STILL-UNACTED work
        (DS-c1 F1) returns False so the original dispatch clock keeps aging out;
        otherwise a handoff re-emit (#12442, same 600s cadence as the grace)
        would reset the clock forever and a wedged agent could never read dead.
        """
        if self.intent != self.INTENT_RUNNING:
            return False
        ld = self.last_dispatch_at
        la = self.last_activity_at
        return ld is None or (la is not None and la >= ld)

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
            # #12244 P2
            "last_spawn_at": self.last_spawn_at,
            "consecutive_fast_deaths": self.consecutive_fast_deaths,
            "reboot_blocked_until": self.reboot_blocked_until,
            # #12409 — slow-loop breaker reboot timestamps
            "reboot_history": list(self.reboot_history),
            # #12418 — last SessionEnd hook reason (graceful-exit signal)
            "last_session_end": self.last_session_end,
            # #12443 — activity heartbeat (progress-based liveness)
            "last_activity_at": self.last_activity_at,
            "last_activity": self.last_activity,
            # #12458 — pause-aware liveness guard state
            "in_flight_until": self.in_flight_until,
            "waiting_since": self.waiting_since,
            "compacting_since": self.compacting_since,
            "last_stop_failure": self.last_stop_failure,
            # #12271 slice d — dispatch reference for progress-liveness
            "last_dispatch_at": self.last_dispatch_at,
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
        # #10681 (PRD-E E2): SHA256 hex of the composed source tree taken
        # at the end of the last successful compose. E1's boot-time
        # freshness check compares the live checksum against this; drift
        # triggers a recompose + checksum refresh. None means "no compose
        # has succeeded under this harness yet" — E1 treats it as drift
        # and runs compose unconditionally on first boot.
        self.last_compose_checksum = None
        self._lock = threading.Lock()
        self._poller_running = False
        self._poller_thread = None
        # PRD-E E3 (#10682) — L4-write file-watch supervisor state.
        # The watchdog Observer runs as its own thread; the supervisor
        # loop here checks aliveness and restarts on death per AC5.
        self._l4_watcher_running = False
        self._l4_watcher_thread = None
        self._l4_observer = None
        self._l4_debouncer = None
        # PRD-E E1 (#10680) / E5 (#10684) — boot-time freshness gate.
        # Set to True by the lifespan freshness-check block when
        # ``compose_freshness.check_and_repair`` returns
        # ``status="failed"``. The deferred-init thread, the HTTP
        # ``/agents/*/start`` endpoints, and the health-poller auto-
        # reboot loop all read this flag to refuse spawning. Per E5
        # AC2 the flag is persisted to ``.harness-state.json`` so it
        # survives harness restart — a prior failure stays in effect
        # until the operator fixes the source set + restarts.
        self.compose_freshness_failed = False
        # #12912 S5: set True by the boot freshness DETECT-only check when the
        # compose source drifted (or no checksum is stored). _deferred_init reads
        # it after auto-start and emits deploy-signals so each clone recomposes
        # pull-first — the harness never runs compose.py deploy-all locally at
        # boot (HARNESS-ARCH §10 step 1b retired). Boot-scoped: not persisted.
        self._boot_deploy_drift = False

    def get_agent(self, role: str) -> AgentState | None:
        with self._lock:
            return self.agents.get(role)

    def set_agent(self, role: str, state: AgentState):
        with self._lock:
            self.agents[role] = state

    def all_agents(self) -> list[dict]:
        with self._lock:
            return [a.to_dict() for a in self.agents.values()]

    # #10681 (PRD-E E2): atomic accessors for last_compose_checksum.
    # E1 (the boot-time freshness check) calls these; tests pin the
    # under-lock contract so a future refactor that splits the lock
    # cannot silently break read/write coordination.

    def get_last_compose_checksum(self) -> str | None:
        """Return the persisted SHA256 hex (64 chars) or None if absent."""
        with self._lock:
            return self.last_compose_checksum

    def set_last_compose_checksum(self, checksum: str | None) -> None:
        """Update the in-memory checksum. Does not flush to disk on its
        own — caller pairs with ``save_state()`` to persist atomically."""
        with self._lock:
            self.last_compose_checksum = checksum

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

                # Direct PID check (#4966) — primary health detection.
                # #12294: trust a PID only if it is alive AND its image is
                # actually claude (image-verified liveness). A recycled PID now
                # owned by an unrelated process must not read as "agent alive"
                # (AC3), and a possibly-stale .claude-pid must be reconciled
                # against the real process, not blindly trusted (AC1). Where the
                # image can't be determined, is_claude_process_alive falls back
                # to plain liveness so a live agent is never mis-reclaimed (AC2).
                pid = agent.claude_pid
                alive = False
                pid_changed = False
                # The image-verify helpers are total (never raise), but this is
                # the fleet-wide health poll — guard the whole resolution block
                # so any unforeseen fault degrades THIS agent to "treat as dead"
                # rather than aborting liveness for every remaining role
                # (DS-12294-c3 Finding 1). file_pid is captured once and reused
                # by the write-back to avoid a second .claude-pid read
                # (DS-12294-c3 Finding 3).
                file_pid = None
                file_read = False
                try:
                    if pid:
                        alive = process_utils.is_claude_process_alive(pid)

                    # If no stored PID or it didn't image-verify, reconcile from
                    # the .claude-pid file — image-verified, so a stale (dead) or
                    # recycled (live non-claude) holder is reclaimed rather than
                    # adopted.
                    if not alive:
                        file_pid, _ = reboot_agent._read_claude_pid(clone_path, role)
                        file_read = True
                        if file_pid and process_utils.is_claude_process_alive(file_pid):
                            pid = file_pid
                            alive = True
                            if agent.claude_pid != pid:
                                pid_changed = True
                            agent.claude_pid = pid
                            state_changed = True

                    # #12294 (C) write-back: when we hold an image-verified live
                    # claude PID for a RUNNING agent, keep .claude-pid in sync
                    # with the harness's in-memory truth so a *subsequent*
                    # restart isn't blind to this agent (the missing/stale-file
                    # observation that motivated this issue). Gated on
                    # intent=RUNNING so we never race thin_launcher's spawn-time
                    # write during a restart/deploy (DS-12294-c3 Finding 5);
                    # only writes when the file is missing or divergent;
                    # best-effort.
                    if alive and pid and agent.intent == AgentState.INTENT_RUNNING:
                        if not file_read:
                            file_pid, _ = reboot_agent._read_claude_pid(clone_path, role)
                        if file_pid != pid:
                            reboot_agent.write_claude_pid(clone_path, role, pid)
                except Exception as e:
                    _log(f"{role}: liveness resolution error — {e!r}; "
                         f"treating as dead this poll")
                    alive = False
                    pid_changed = False

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

                # #12271 slice d — SHADOW divergence logging (OBSERVATIONAL).
                # `alive` above is the PID-based verdict. Compute the progress-
                # based verdict alongside it and log where they DISAGREE — this
                # gathers the validation data the cutover needs before PID-
                # liveness is removed: a PID-alive / progress-dead divergence is
                # a candidate ZOMBIE (an inert process — the #10855/#10440 case
                # we want to start catching); a PID-dead / progress-alive one is
                # a candidate FALSE REBOOT the progress model would have avoided.
                # Reads run under self._lock (held here), satisfying progress_
                # liveness()'s snapshot contract. This does NOT change `alive` or
                # the reboot decision — the cutover (making progress authoritative
                # + demoting PID to teardown-only) is the separate next step,
                # gated on this shadow data showing no false positives/negatives.
                prog_alive, prog_reason = agent.progress_liveness(time.time())
                if prog_alive != alive:
                    _kind = ("candidate-zombie" if alive and not prog_alive
                             else "candidate-false-reboot-avoided")
                    _log(
                        f"{role}: LIVENESS DIVERGENCE — PID says "
                        f"{'alive' if alive else 'dead'}, progress says "
                        f"{'alive' if prog_alive else 'dead'} ({prog_reason}) "
                        f"[shadow #12271-d: {_kind}]"
                    )

                # #4792 Phase 1 (Q7) — 60s force-kill safety net.
                # If the agent has been STOPPING/RESTARTING for longer than
                # the timeout AND the claude PID is still alive, the
                # cooperative shutdown path (cycle_post exit 42 → /quit) has
                # not completed; kill the PID directly so the operator's
                # intent eventually wins. CONTEXT-4792.md §3.3. Idempotent:
                # the kill races against the cooperative exit and we re-check
                # on the next poll either way.
                # #11538: skip when pid_changed — a NEW claude PID means the
                # old process already died and the agent rebooted, so the
                # STOPPING/RESTARTING intent has been fulfilled. intent_set_at
                # still references the OLD process's clock; force-killing the
                # freshly-booted replacement for that stale timer is wrong (the
                # RESTARTING→RUNNING reset just below clears the intent on this
                # same poll).
                # #10538 (gap-fix): defense in depth. Under no-auto-reboot a
                # RESTARTING force-kill would tear down a working agent that
                # cannot respawn, so skip it (the two paths above should already
                # prevent intent=restarting being set, but a stale on-disk
                # intent from before the hatch was armed must not leak through).
                # STOPPING force-kill is preserved — an explicit operator stop
                # legitimately wants the process dead even with reboots off.
                _no_reboot_restart = (
                    _NO_AUTO_REBOOT
                    and agent.intent == AgentState.INTENT_RESTARTING
                )
                if alive and pid and not pid_changed and agent.intent in (
                    AgentState.INTENT_STOPPING, AgentState.INTENT_RESTARTING,
                ) and not _no_reboot_restart and agent.intent_set_at is not None and (
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
                    # #12244 P2 — a spawn that has been alive past the fast-death
                    # window is a genuine recovery: clear the crash-loop streak
                    # and any pending backoff so a later isolated death reboots
                    # immediately instead of inheriting a stale backoff.
                    if (agent.consecutive_fast_deaths > 0
                            and agent.last_spawn_at is not None
                            and (time.time() - agent.last_spawn_at)
                            >= FAST_DEATH_WINDOW_SECONDS):
                        _log(f"{role}: survived "
                             f">{FAST_DEATH_WINDOW_SECONDS}s — clearing "
                             f"crash-loop streak "
                             f"({agent.consecutive_fast_deaths}->0)")
                        agent.consecutive_fast_deaths = 0
                        agent.reboot_blocked_until = None
                        state_changed = True
                    # #11538: only clear a RESTARTING intent once a NEW claude
                    # PID has appeared (pid_changed) — i.e. the old process
                    # actually died and the agent rebooted. Resetting whenever
                    # the SAME PID is merely alive silently undoes an in-flight
                    # restart within one health poll (HEALTH_POLL_INTERVAL=5s)
                    # AND disarms the 60s force-kill safety net, so a wedged /
                    # non-cycling agent could never be restarted OR force-killed
                    # via the documented endpoint. Mirrors the STOPPING branch.
                    if agent.intent in (
                        AgentState.INTENT_RESTARTING,
                        AgentState.INTENT_DEPLOYING,
                    ) and pid_changed:
                        # #12912: a fresh PID under intent=deploying means the
                        # deploy sequence respawned the agent — settle back to
                        # running exactly like a restart (the deploy sequence
                        # also sets RUNNING explicitly; this is the defensive
                        # health-poll mirror).
                        prev_intent = agent.intent
                        agent.intent = AgentState.INTENT_RUNNING
                        agent.intent_set_at = None  # #4792 Phase 1
                        state_changed = True
                        _log(f"{role}: alive with new PID ({prev_intent} complete), reset to running (#11538/#12912)")
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
                elif agent.status in ("crash-looping", "paused"):
                    # #12244 P2: a dead agent waiting out its backoff normally
                    # KEEPS the "crash-looping" status (preserved like
                    # "starting") so the resume branch below recognises it and
                    # operators see the real reason — instead of being
                    # relabelled "unknown" on the next poll. #12458: "paused"
                    # (an explained-silence HOLD) is preserved the same way and
                    # has its own resume branch below. BUT an operator stop wins
                    # over either hold: when intent is STOPPING/STOPPED, abandon
                    # the wait and settle to "stopped" so the STOPPING
                    # fulfillment below can finish it (otherwise a held agent +
                    # /stop would wedge forever — neither is_dead nor the resume
                    # branch fire for STOPPING intent).
                    if agent.intent in (
                        AgentState.INTENT_STOPPING, AgentState.INTENT_STOPPED
                    ):
                        agent.status = "stopped"
                        agent.reboot_blocked_until = None
                        state_changed = True
                elif agent.status != "starting":
                    # #4792: stop is now expressed via intent (INTENT_STOPPING
                    # → INTENT_STOPPED), not a sentinel file.
                    if agent.intent in (
                        AgentState.INTENT_STOPPING, AgentState.INTENT_STOPPED
                    ):
                        agent.status = "stopped"
                    elif agent.intent == AgentState.INTENT_DEPLOYING:
                        # #12912 (HARNESS-ARCH §7.1.1 / §7.4): a death while
                        # intent=deploying is normally the EXPECTED deploy-halt
                        # exit — the deploy sequence owns the respawn — so settle
                        # to "deploying" (not is_dead below) and suppress the
                        # crash-respawn path (AC9).
                        # DS-12912 iter-3 Finding 2: BUT if the agent has been dead
                        # at intent=deploying longer than the deploy window (it
                        # crashed BEFORE emitting ack-stop, or the deploy thread
                        # hung/died), the deploy will never complete and nothing
                        # else will respawn it. Treat it as a crashed running agent
                        # so the normal auto-reboot path respawns it on its
                        # existing committed CLAUDE.md (next poll: "running" → dead
                        # → "stalled" → reboot; mirrors the load_state recovery).
                        _deploy_age = (
                            time.time() - agent.intent_set_at
                            if agent.intent_set_at is not None else None
                        )
                        if (_deploy_age is not None
                                and _deploy_age > _DEPLOY_WINDOW_SECONDS):
                            _log(f"{role}: dead at intent=deploying for "
                                 f"{_deploy_age:.0f}s (> {_DEPLOY_WINDOW_SECONDS}s "
                                 f"deploy window) — deploy never completed; "
                                 f"recovering via auto-respawn")
                            agent.intent = AgentState.INTENT_RUNNING
                            agent.intent_set_at = None
                            agent.status = "running"
                        else:
                            agent.status = "deploying"
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
                now = time.time()

                # #12458 (#12271 slice c) — pause-aware guard. A death candidate
                # is a FRESH death (PID died this poll) OR a previously-HELD
                # "paused" agent still not alive. If a hook explains the silence
                # (active_pause: mid-tool-call / compacting / waiting, each
                # bounded by its staleness ceiling), HOLD instead of rebooting —
                # re-evaluated every poll, released the moment the ceiling
                # elapses (active_pause → None), after which the unexplained
                # silence runs the normal death/backoff path. AC5: a genuine
                # death with NO pause signal is unaffected (active_pause returns
                # None immediately, so death_candidate falls straight through to
                # the confirmed-death branch exactly as before #12458).
                fresh_death = is_dead and was_alive
                held = agent.status == "paused" and not alive
                death_candidate = (fresh_death or held) and should_reboot
                pause_reason = agent.active_pause(now) if death_candidate else None

                if death_candidate and pause_reason is not None:
                    # Explained silence → HOLD reboot (mirrors the crash-looping
                    # hold: "paused" is preserved across polls by the status
                    # block above and re-evaluated here each poll). DS-REVIEW-
                    # 12458-guard F1: signal a change ONLY on the initial
                    # transition into "paused" — the status block preserves the
                    # hold silently thereafter, so re-asserting the same values
                    # every 5s poll would churn save_state for no change (the
                    # crash-looping hold doesn't either).
                    if agent.status != "paused":
                        _log(
                            f"{role}: dead/silent PID but '{pause_reason}' hook "
                            f"active — holding off reboot (explained pause, "
                            f"#12458)"
                        )
                        agent.status = "paused"
                        agent.claude_pid = None
                        agent.bootup_complete = False
                        state_changed = True
                elif death_candidate and _NO_AUTO_REBOOT:
                    # #10538: observe-but-don't-respawn. State stays
                    # honest (PID cleared, bootup gate reset) so the
                    # next operator-driven `POST /agents/{role}/start`
                    # behaves the same as a normal fresh spawn.
                    _log(
                        f"[no-auto-reboot] {role} died; "
                        f"intent={agent.intent}; not respawning per "
                        f"SQUIDSQUAD_HARNESS_NO_AUTO_REBOOT"
                    )
                    agent.claude_pid = None
                    agent.bootup_complete = False
                    state_changed = True
                elif death_candidate and agent.stopfailure_backoff_due(now):
                    # #12458 AC3d — the death coincides with a recent throttle
                    # (rate_limit / overloaded). Respawning immediately would
                    # re-hit the same limit, so back off via the crash-loop
                    # timer — NOT a tight respawn. Reuses the crash-looping
                    # resume path below.
                    #
                    # DS-REVIEW-12458-guard F3: only COUNT it toward the crash
                    # streak when the exit was NOT graceful — a cooperative exit
                    # (SessionEnd after this spawn) that merely coincides with a
                    # stale throttle must not accumulate the #12244 streak (the
                    # #12418 AC4 contract). We still apply the backoff either way
                    # (don't re-hit the limit), but a graceful exit doesn't
                    # escalate the streak.
                    se = agent.last_session_end
                    se_at = (se.get("at") or 0) if isinstance(se, dict) else 0
                    graceful = bool(
                        agent.last_spawn_at is not None
                        and se_at >= agent.last_spawn_at
                    )
                    if not graceful:
                        agent.consecutive_fast_deaths += 1
                    over = max(0, agent.consecutive_fast_deaths
                               - FAST_DEATH_THRESHOLD)
                    backoff = min(
                        CRASH_BACKOFF_BASE_SECONDS * (2 ** over),
                        CRASH_BACKOFF_CAP_SECONDS,
                    )
                    agent.reboot_blocked_until = now + backoff
                    agent.status = "crash-looping"
                    agent.claude_pid = None
                    agent.bootup_complete = False
                    state_changed = True
                    sf = agent.last_stop_failure or {}
                    _log(
                        f"{role}: StopFailure cause={sf.get('cause')!r} "
                        f"(throttle) — backing off {backoff:.0f}s before respawn "
                        f"rather than re-hitting the limit (#12458)."
                    )
                elif death_candidate:
                    # #12244 P2 — crash-loop / session-limit backoff. Count
                    # back-to-back fast deaths; once they cross the
                    # threshold, hold off the respawn (exponential, capped)
                    # and surface a paused status instead of tight-looping
                    # and burning quota.
                    lifetime = (
                        now - agent.last_spawn_at
                        if agent.last_spawn_at is not None else None
                    )
                    # #12418 AC4 — graceful-vs-crash. A GRACEFUL exit (a
                    # SessionEnd hook fired AFTER this spawn) is not a crash:
                    # it must not accumulate the #12244 crash-loop streak, so
                    # a legitimate cooperative restart is never throttled as
                    # if it were a quota/startup crash. A CRASH (dead PID
                    # with NO SessionEnd since last_spawn_at — the hook
                    # couldn't run) still counts toward the streak → backoff.
                    # The stale-SessionEnd case is handled by the
                    # `>= last_spawn_at` guard: a prior spawn's SessionEnd
                    # predates this spawn and reads as a crash. Augments the
                    # PID path (AC6) — the respawn action itself is unchanged.
                    se = agent.last_session_end
                    # DS-REVIEW-12418-C F1: use `(se.get("at") or 0)` — a
                    # `{"at": null}` from a hand-edited/corrupt state file
                    # makes `.get("at", 0)` return None, and `None >= float`
                    # raises TypeError, aborting the whole health poll.
                    se_at = (se.get("at") or 0) if isinstance(se, dict) else 0
                    graceful = bool(
                        agent.last_spawn_at is not None
                        and se_at >= agent.last_spawn_at
                    )
                    if graceful:
                        # #12418 AC4: a graceful exit is NOT a crash — do NOT
                        # increment the streak. We deliberately do NOT reset
                        # it to 0 either (DS-REVIEW-12418-C F2): a misbehaving
                        # agent that POSTs SessionEnd then crashes must not be
                        # able to ZERO accumulated real crashes and escape the
                        # breaker. The legitimate reset is the survived-window
                        # path above. (Residual: a pure SessionEnd-spammer can
                        # still keep the streak from growing — a full
                        # termination-correlation guard is a #12271 liveness
                        # hardening follow-up; natural crash loops don't POST
                        # SessionEnd, so the #12244 protection is intact.)
                        _log(
                            f"{role}: graceful exit (SessionEnd "
                            f"reason={se.get('reason')!r}) — not counted as "
                            f"a crash (streak stays "
                            f"{agent.consecutive_fast_deaths}) (#12418)"
                        )
                    elif (lifetime is not None
                            and lifetime < FAST_DEATH_WINDOW_SECONDS):
                        agent.consecutive_fast_deaths += 1
                    else:
                        # Lived long enough (or no spawn record) — not a
                        # crash loop; a one-off death reboots immediately.
                        agent.consecutive_fast_deaths = 0

                    if (agent.consecutive_fast_deaths
                            >= FAST_DEATH_THRESHOLD):
                        over = (agent.consecutive_fast_deaths
                                - FAST_DEATH_THRESHOLD)
                        backoff = min(
                            CRASH_BACKOFF_BASE_SECONDS * (2 ** over),
                            CRASH_BACKOFF_CAP_SECONDS,
                        )
                        agent.reboot_blocked_until = now + backoff
                        agent.status = "crash-looping"
                        agent.claude_pid = None
                        agent.bootup_complete = False
                        state_changed = True
                        _log(
                            f"{role}: {agent.consecutive_fast_deaths} "
                            f"consecutive fast deaths "
                            f"(<{FAST_DEATH_WINDOW_SECONDS}s each) — "
                            f"backing off {backoff:.0f}s before respawn "
                            f"(status=crash-looping). Likely a Claude "
                            f"session/usage limit or a startup crash; not "
                            f"hammering the respawn."
                        )
                    elif agent.recent_reboot_count(now) >= SLOW_LOOP_THRESHOLD:
                        # #12409 — frequency-based slow-loop breaker. The
                        # fast-death streak above reset (this death lived long
                        # enough), but the agent has still been auto-rebooted
                        # SLOW_LOOP_THRESHOLD+ times within
                        # SLOW_LOOP_WINDOW_SECONDS — a SLOW reboot loop #12244
                        # cannot see. Back off (capped exponential keyed on how
                        # far over the threshold we are) instead of rebooting,
                        # reusing the crash-looping status + reboot_blocked_until
                        # machinery so the resume path below wakes it.
                        recent = agent.recent_reboot_count(now)
                        over = recent - SLOW_LOOP_THRESHOLD
                        backoff = min(
                            CRASH_BACKOFF_BASE_SECONDS * (2 ** over),
                            CRASH_BACKOFF_CAP_SECONDS,
                        )
                        agent.reboot_blocked_until = now + backoff
                        agent.status = "crash-looping"
                        agent.claude_pid = None
                        agent.bootup_complete = False
                        state_changed = True
                        _log(
                            f"{role}: {recent} auto-reboots within "
                            f"{SLOW_LOOP_WINDOW_SECONDS}s — slow reboot-loop "
                            f"breaker (#12409) backing off {backoff:.0f}s "
                            f"(status=crash-looping). Each session outlived the "
                            f"#12244 fast-death window, so this frequency breaker "
                            f"is what catches it."
                        )
                    else:
                        reboot_roles.append(role)
                        agent.status = "starting"
                        agent.claude_pid = None  # Clear stale PID
                        # #8695: the replacement process needs to re-emit
                        # bootup-complete before we'll dispatch events to it.
                        agent.bootup_complete = False
                        state_changed = True

                # #12244 P2 — resume from crash-loop backoff once the window
                # elapses. A paused ("crash-looping") agent is not is_dead and
                # was not prev-running, so the branch above won't re-fire — this
                # is its dedicated wake path. The fast-death streak is kept (so a
                # still-failing agent backs off longer next time); it only
                # resets once a respawn survives the window (the alive branch).
                elif (agent.status == "crash-looping" and not alive
                        and should_reboot
                        and agent.reboot_blocked_until is not None
                        and time.time() >= agent.reboot_blocked_until):
                    reboot_roles.append(role)
                    agent.status = "starting"
                    agent.claude_pid = None
                    agent.bootup_complete = False
                    agent.reboot_blocked_until = None
                    state_changed = True
                    _log(
                        f"{role}: crash-loop backoff elapsed — retrying "
                        f"respawn (streak still "
                        f"{agent.consecutive_fast_deaths}; resets after a "
                        f"spawn survives >{FAST_DEATH_WINDOW_SECONDS}s)."
                    )

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
            # PRD-E E1 (#10680) / DS-10680 F4: respect the freshness
            # gate. If the E1 check failed at boot, every spawn path
            # (auto-start, HTTP endpoints, AND this auto-reboot loop)
            # must refuse. The operator has to fix the source + restart
            # the harness — re-spawning an agent against a broken
            # compose set is exactly the "degraded boot" AC4 forbids.
            if self.compose_freshness_failed:
                _log(
                    f"[compose-freshness-failed] {role} died but not "
                    f"respawning — E1 gate is red, operator must fix "
                    f"source + restart harness"
                )
                continue
            _log(f"Auto-rebooting {role} (was running, intent={self.agents[role].intent})")
            try:
                result = boot_remote.boot_agent(role)
                # DS-12409 F1: gate on action=="spawn", not success alone. A
                # success=True/action="skip" (agent came back alive in a race, or
                # a concurrent boot holds the .booting sentinel) means NO process
                # was spawned — stamping last_spawn_at / recording a reboot /
                # clearing the SessionEnd signal would corrupt the fast-death
                # lifetime and inflate the #12409 slow-loop count for a reboot
                # that did not happen. Matches the other three spawn paths
                # (start_team / start_all / deploy respawn).
                if result.get("success") and result.get("action") == "spawn":
                    with self._lock:
                        agent = self.agents.get(role)
                        if agent:
                            agent.terminal_pid = result.get("terminal_pid")
                            # #12244 P2 — stamp the (re)spawn time so the next
                            # death's lifetime is measured from here; this is
                            # what makes the fast-death streak accumulate across
                            # auto-reboots (boot_time is not refreshed here).
                            agent.last_spawn_at = time.time()
                            # #12409 — record this auto-reboot for the
                            # frequency-based slow-loop breaker (lifetime-agnostic,
                            # complements last_spawn_at's fast-death timing).
                            agent.record_reboot(time.time())
                            # #12418 F3 — clear the prior lifecycle's SessionEnd
                            # so only a hook from THIS spawn can mark the next
                            # death graceful (closes the delayed-hook race).
                            agent.last_session_end = None
                            # #12271 slice d (DS-c1 F4) — clear the dispatch
                            # reference so a respawn starts with a clean activity
                            # baseline (a stale last_dispatch_at from before the
                            # death must not make the fresh agent read wedged).
                            agent.last_dispatch_at = None
                            # #13113 — same rationale for the per-session activity
                            # + pause telemetry: a stale last_activity_at / pause
                            # flag from the dead session must not survive into the
                            # fresh record (frozen-telemetry masquerade).
                            agent.reset_session_telemetry()
                elif result.get("action") == "error":
                    # #11640: boot_agent refused (e.g. unregistered/missing
                    # clone). Never spawned in REPO_ROOT — surface the refusal
                    # and mark the agent error so the operator sees it instead
                    # of an endlessly re-attempting silent reboot.
                    _log(f"Auto-reboot of {role} REFUSED: {result.get('message')}")
                    with self._lock:
                        agent = self.agents.get(role)
                        if agent:
                            agent.status = "error"
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

    # ----- PRD-E E3 (#10682): L4-write file-watch lifecycle -------------

    def start_l4_watcher(self):
        """Start the L4-write file-watch supervisor thread.

        The supervisor checks the watchdog Observer's aliveness on every
        tick and (re-)spawns it via ``l4_file_watcher.start_watcher``
        whenever the Observer is missing or dead — per AC5's
        "file-watch crashes -> harness logs + restarts the watcher"
        rule. ``watchdog`` import failure degrades gracefully: the
        supervisor logs once and exits; the rest of the harness keeps
        running so a missing optional dep doesn't take the harness down.
        """
        if self._l4_watcher_running:
            return
        self._l4_watcher_running = True
        self._l4_watcher_thread = threading.Thread(
            target=self._l4_watcher_loop,
            daemon=True,
            name="l4-watcher-supervisor",
        )
        self._l4_watcher_thread.start()

    def stop_l4_watcher(self):
        """Signal the supervisor to exit and tear down the Observer.

        The supervisor loop sees the flag flip on its next tick, stops
        the Observer, joins it (5s timeout), and flushes the debouncer
        so no pending fire callbacks run after shutdown.
        """
        self._l4_watcher_running = False
        observer = self._l4_observer
        debouncer = self._l4_debouncer
        self._l4_observer = None
        self._l4_debouncer = None
        if observer is not None:
            try:
                observer.stop()
                observer.join(timeout=5)
            except Exception as e:
                _log(f"L4 file-watcher stop raised (ignored): {e}")
        if debouncer is not None:
            try:
                debouncer.flush()
            except Exception:
                pass

    def _l4_watcher_loop(self):
        """Survive-and-restart supervisor for the L4-write file-watcher.

        Tightly mirrors ``_poll_loop``: tick the supervise helper on a
        fixed cadence and swallow exceptions so a transient fault never
        kills the supervisor thread itself.
        """
        # Lazy import inside the thread body — keeps harness import
        # cost off the critical boot path and surfaces a clean log
        # when watchdog is missing instead of crashing at module load.
        try:
            import l4_file_watcher as _lfw
        except Exception as e:
            _log(
                f"L4 file-watcher supervisor disabled: cannot import "
                f"l4_file_watcher ({e!r})"
            )
            self._l4_watcher_running = False
            return

        import config as _cfg  # parse_aliases_registry lives here.

        def starter():
            return _lfw.start_watcher(
                repo_root=REPO_ROOT,
                registry_provider=_cfg.parse_aliases_registry,
                emit_event=_emit_event,
            )

        while self._l4_watcher_running:
            try:
                self._supervise_l4_once(starter)
            except Exception as e:
                _log(f"L4 file-watcher supervisor tick raised (ignored): {e}")
            time.sleep(L4_WATCHER_SUPERVISE_INTERVAL)

    def _supervise_l4_once(self, starter):
        """Single supervisor tick — testable without ``watchdog``.

        Behavior:
        - Observer absent (first tick or after a crash) -> call
          ``starter()`` to (re-)spawn. The starter returns
          ``(observer, debouncer)``. On success store the pair; on
          exception log + leave state unset (next tick retries).
        - Observer present and ``is_alive()`` is True -> no-op.
        - Observer present and ``is_alive()`` is False -> AC5 crash
          path: log, clear stored handles, and call ``starter()`` to
          respawn on this same tick. A flush on the stale debouncer
          prevents leftover timers from firing into the new observer.

        Returns the action taken as a string (``"started"`` /
        ``"running"`` / ``"restarted"`` / ``"start-failed"``) so the
        regression test can assert the right branch fired without
        depending on the watchdog Observer's internals.
        """
        observer = self._l4_observer
        action = "running"
        needs_start = observer is None
        if observer is not None and not observer.is_alive():
            _log("L4 file-watcher Observer died — respawning.")
            if self._l4_debouncer is not None:
                try:
                    self._l4_debouncer.flush()
                except Exception:
                    pass
            self._l4_observer = None
            self._l4_debouncer = None
            needs_start = True
            action = "restarted"
        if needs_start:
            try:
                new_observer, new_debouncer = starter()
            except Exception as e:
                # #11403 AC3: surface the remediation in plain text (str, not
                # repr) and name the operator impact, so a missing `watchdog`
                # dependency is actionable rather than buried in a traceback
                # repr. The harness still degrades gracefully (returns
                # "start-failed"); only L4 auto-recompose is disabled.
                _log(f"WARNING: L4 file-watcher start failed — PRD-E E3 "
                     f"auto-recompose on L4 edits is DISABLED this run. {e}")
                return "start-failed"
            self._l4_observer = new_observer
            self._l4_debouncer = new_debouncer
            if action != "restarted":
                action = "started"
                _log(
                    f"L4 file-watcher started, watching "
                    f"{REPO_ROOT / '.squidsquad' / 'project'}"
                )
        return action

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
                # #10681: E1 reads this on boot to detect source-tree drift.
                # Persisted at the top level (not per-agent) since the
                # checksum spans the whole compose-input set.
                "last_compose_checksum": self.last_compose_checksum,
                # PRD-E E5 (#10684) / DS-10684 F1: persist the failure
                # flag so a `--no-freshness-check` restart after a prior
                # failure still sees the failure and refuses to spawn.
                # Legacy state files without the key default to False
                # on read (see load_state).
                "compose_freshness_failed": self.compose_freshness_failed,
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
                        # #12244 P2: persist crash-loop backoff state so a
                        # harness restart mid-backoff doesn't reset the streak
                        # and immediately re-enter a tight respawn loop.
                        "last_spawn_at": a.last_spawn_at,
                        "consecutive_fast_deaths": a.consecutive_fast_deaths,
                        "reboot_blocked_until": a.reboot_blocked_until,
                        # #12409 — persist the slow-loop reboot history so a
                        # harness restart mid-loop doesn't reset the frequency
                        # breaker and re-enter a slow respawn loop.
                        "reboot_history": list(a.reboot_history),
                        # #12418 — persist last SessionEnd reason so the
                        # graceful-vs-crash signal survives a harness restart.
                        "last_session_end": a.last_session_end,
                        # #12443 — persist activity heartbeat (throttled writer;
                        # see /hooks/activity). Survives a harness restart so the
                        # last-known activity isn't lost on recovery.
                        "last_activity_at": a.last_activity_at,
                        "last_activity": a.last_activity,
                        # #12458 — persist pause state so a harness restart
                        # mid-pause doesn't immediately false-reboot a paused
                        # agent (the ceilings still bound any stale flag).
                        "in_flight_until": a.in_flight_until,
                        "waiting_since": a.waiting_since,
                        "compacting_since": a.compacting_since,
                        "last_stop_failure": a.last_stop_failure,
                        # #12271 slice d — persist dispatch reference so a
                        # harness restart preserves the activity baseline.
                        "last_dispatch_at": a.last_dispatch_at,
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
            # #10681 (E2): legacy state files lack this field; treat as None
            # (which E1 reads as drift on first boot, triggering compose).
            # An explicit null in the file is also honored.
            self.last_compose_checksum = state_data.get("last_compose_checksum")
            # PRD-E E5 (#10684) / DS-10684 F1: restore the failure flag
            # so a prior failed boot stays in effect across restart.
            # Legacy state files default safely to False.
            self.compose_freshness_failed = bool(
                state_data.get("compose_freshness_failed", False)
            )
            for role, agent_data in state_data.get("agents", {}).items():
                if role not in self.agents:
                    self.agents[role] = AgentState(
                        role, agent_data.get("clone_path", "")
                    )
                agent = self.agents[role]
                agent.intent = agent_data.get("intent", AgentState.INTENT_RUNNING)
                # #12244 P0 — a RESTARTING intent does NOT survive a harness
                # restart. "restart in progress" is a transient state owned by
                # the harness session that issued it; resurrecting it across a
                # restart force-kills (the 60s safety net below) a HEALTHY agent
                # whose claude.exe outlived the harness — its restored
                # intent_set_at predates the restart and is already past the
                # timeout, so the first health poll kills it, then auto-reboots
                # it (the operator-reported "working agent killed + respawned,
                # repeatedly" loop). Reset to RUNNING: a still-dead agent is
                # auto-rebooted anyway (RUNNING is in should_reboot); a live one
                # is left alone. A genuinely-wanted restart can be re-requested
                # against THIS harness. STOPPING is deliberately NOT reset — an
                # explicit operator stop MUST survive a harness restart.
                # #12912: INTENT_DEPLOYING is reset the same way — a deploy in
                # progress is owned by the harness session that emitted the
                # deploy-signal. If the harness restarted mid-deploy the sequence
                # was interrupted; reset to RUNNING so the agent respawns on its
                # existing committed CLAUDE.md. The deploy did not advance
                # last_compose_checksum, so drift stays detectable and a future
                # deploy-signal re-triggers.
                if agent.intent in (
                    AgentState.INTENT_RESTARTING,
                    AgentState.INTENT_DEPLOYING,
                ):
                    agent.intent = AgentState.INTENT_RUNNING
                    agent.intent_set_at = None
                # #4792 Phase 1 — two-case migration per CONTEXT-4792.md §5.1,
                # now STOPPING-only (RESTARTING handled above). Distinguish an
                # absent key from an explicit null: an explicit null is honored
                # (case b "load as-is"); only an absent key seeds (case a):
                #   (a) legacy state file: intent STOPPING, `intent_set_at` key
                #       ABSENT → seed time.time() so the force-kill clock starts
                #       now rather than firing immediately on a stale intent.
                #   (b) present state file: load as-is (None when RUNNING/
                #       STOPPED, or a float when STOPPING).
                elif "intent_set_at" not in agent_data and (
                    agent.intent == AgentState.INTENT_STOPPING
                ):
                    agent.intent_set_at = time.time()
                else:
                    agent.intent_set_at = agent_data.get("intent_set_at")
                agent.boot_time = agent_data.get("boot_time")
                agent.claude_pid = agent_data.get("claude_pid")
                agent.terminal_pid = agent_data.get("terminal_pid")
                # DS-12912 iter-2 Finding 5: restore `status` (save_state persists
                # it but load_state historically dropped it, so every agent came
                # back as "unknown" — never in is_dead — and a dead-before-restart
                # agent was never auto-rebooted). Restoring it lets the health
                # poller recover: a restored "running" agent whose PID is dead
                # settles to "stalled" (was_alive=True) and respawns; the
                # crash-looping / paused resume branches also need their status
                # back. Defaults to "unknown" for legacy/fresh state files.
                agent.status = agent_data.get("status", "unknown")
                # #12912: an interrupted mid-deploy (status="deploying") restored
                # after a harness restart had its intent reset to RUNNING above;
                # settle the status to "running" so the dead PID is treated as a
                # crashed running agent and respawned on its existing committed
                # CLAUDE.md. The deploy did not complete (checksum unadvanced), so
                # a future deploy-signal re-triggers.
                if agent.status == "deploying":
                    agent.status = "running"
                # #8695: restore so already-running agents stay ungated after
                # a harness restart. Defaults to False for older state files.
                agent.bootup_complete = agent_data.get("bootup_complete", False)
                # #12244 P2 — restore crash-loop backoff state (defaults safe
                # for older state files / fresh agents).
                agent.last_spawn_at = agent_data.get("last_spawn_at")
                agent.consecutive_fast_deaths = agent_data.get(
                    "consecutive_fast_deaths", 0) or 0
                agent.reboot_blocked_until = agent_data.get("reboot_blocked_until")
                # #12409 — restore the slow-loop reboot history (defaults [] for
                # older state files / fresh agents). Coerce to a list of numbers
                # defensively against a hand-edited/corrupt state file.
                _rh = agent_data.get("reboot_history") or []
                agent.reboot_history = [t for t in _rh
                                        if isinstance(t, (int, float))]
                # #12418 — restore last SessionEnd reason (defaults None for
                # older state files / fresh agents).
                agent.last_session_end = agent_data.get("last_session_end")
                # #12443 — restore activity heartbeat (defaults None for older
                # state files / fresh agents).
                agent.last_activity_at = agent_data.get("last_activity_at")
                agent.last_activity = agent_data.get("last_activity")
                # #12458 — restore pause state (defaults None for older state
                # files / fresh agents).
                agent.in_flight_until = agent_data.get("in_flight_until")
                agent.waiting_since = agent_data.get("waiting_since")
                agent.compacting_since = agent_data.get("compacting_since")
                agent.last_stop_failure = agent_data.get("last_stop_failure")
                # #12271 slice d — restore dispatch reference (None for older
                # state files / fresh agents).
                agent.last_dispatch_at = agent_data.get("last_dispatch_at")

        _log(f"Restored state for {len(state_data.get('agents', {}))} agents from state file")


# ---------------------------------------------------------------------------
# Event stream (#4709 Phase 2)
# ---------------------------------------------------------------------------

class EventStream:
    """Bounded event stream — thread-safe deque with max 1000 events."""

    def __init__(self, maxlen=1000):
        self._events = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()
        # Lifetime emit counter for the eviction-signal hint (#9331).
        # Increments on every `append`; never decrements when the deque
        # rolls. After the deque is full, the difference from
        # `len(self._events)` = number of events evicted from the
        # retained window over the harness's lifetime.
        self._total_emitted_count = 0

    def append(self, event: dict):
        with self._lock:
            self._events.append(event)
            self._total_emitted_count += 1

    def get_all(self) -> list[dict]:
        with self._lock:
            return list(self._events)

    def get_recent(self, n: int = 50) -> list[dict]:
        with self._lock:
            items = list(self._events)
            return items[-n:] if len(items) > n else items

    def get_since(self, since_id: str, limit: int = 100) -> list[dict]:
        """Return events after the given ID. If ID not found, return oldest available.

        Single-return-value wrapper around
        :meth:`get_since_with_eviction` — drops the eviction marker.
        Ordering follows the skim-then-advance contract
        (CONTEXT-8694 §2): **oldest-first when ``since_id`` is set**
        (so the agent walks the gap event-by-event), newest-first
        otherwise. This is the same ordering change PR #9320 ships
        for the §4.10 long-cursor-lag scenario; #9331 inherits it
        because the eviction-aware getter must return oldest-first
        for re-anchor to make sense. Callers that need the eviction
        marker should use :meth:`get_since_with_eviction` directly.
        """
        events, _ = self.get_since_with_eviction(since_id, limit)
        return events

    def get_since_with_eviction(
        self, since_id: str, limit: int = 100,
    ):
        """Return ``(events, eviction_marker)``.

        ``eviction_marker`` is ``None`` for the normal case — cursor
        was found in the retained window, or no cursor was passed.
        When the caller supplies a ``since_id`` that is **not** in the
        deque, the marker becomes::

            {
                "oldest_id": <str>,
                "evicted_count_hint": <int>,
            }

        - ``oldest_id`` is the id of the oldest event still retained
          (the cursor's safe re-anchor point). The marker is emitted
          ONLY when the deque is non-empty, so ``oldest_id`` is always
          a real id — never ``None``. When the cursor predates the
          window but the deque is EMPTY (no anchor possible), the
          marker is suppressed and ``(events, None)`` is returned
          instead (a benign empty result), so the harness never emits
          the self-contradictory ``evicted`` + empty + no-anchor triple
          that trips event_poll's fatal guard (#12837).
        - ``evicted_count_hint`` is a coarse upper bound on the number
          of events that have been pushed out of the retained window
          since boot (lifetime emits − currently retained). Operators
          log this for forensics; exact precision is not required
          (#9331).

        The events list itself follows the same skim-then-advance
        contract as before (CONTEXT-8694 §2): oldest-first when
        ``since`` is set, newest-first otherwise. With ``since``
        present, returning newest-first would silently drop the gap
        between cursor and (head − limit).
        """
        with self._lock:
            items = list(self._events)
            if not since_id:
                events = items[-limit:] if len(items) > limit else items
                return events, None
            for i, event in enumerate(items):
                if event.get("id") == since_id:
                    after = items[i + 1:]
                    events = after[:limit] if len(after) > limit else after
                    return events, None
            # Cursor predates the retained window — emit the eviction
            # signal so the agent can log + advance to a known anchor
            # instead of silently moving past the gap.
            #
            # #12837: when the deque is EMPTY there is no anchor to advance
            # to, so building a marker here would yield the self-contradictory
            # triple ``evicted:true`` + ``events:[]`` + ``oldest_id:None``.
            # That is exactly the "harness contract violation" event_poll's
            # fatal guard (event_poll.py:304) refuses — it returns None and the
            # agent's Monitor exits 2, taking down the event listener (#9742).
            # A stale cursor against an empty (cold-start / fully-churned) deque
            # is a benign "nothing to deliver", NOT an unrecoverable gap: return
            # an empty result with NO marker. When a real event later lands, the
            # next poll re-enters this path with a non-empty deque and a valid
            # ``oldest_id``, and the agent re-anchors normally — no events lost.
            if not items:
                return [], None
            events = items[:limit] if len(items) > limit else items
            oldest_id = items[0].get("id")
            evicted_count_hint = max(
                0, self._total_emitted_count - len(items)
            )
            marker = {
                "oldest_id": oldest_id,
                "evicted_count_hint": evicted_count_hint,
            }
            return events, marker

    def __len__(self):
        with self._lock:
            return len(self._events)

    def has_event(self, event_id: str) -> bool:
        """Return True if any event in the deque has id matching ``event_id``.

        Used by the ack-cursor handler to reject advancing the cursor past an
        evicted event (#9873-A D8). O(n) scan under ``self._lock``; deque is
        bounded at ``maxlen=1000`` so cost is acceptable at current ack
        frequency. Caller holds ``EventLifecycleManager._lock`` already per
        the outer→inner ordering (#9873-A §4 audit).
        """
        if not event_id:
            return False
        with self._lock:
            for event in self._events:
                if event.get("id") == event_id:
                    return True
        return False

    def find_positions(self, target_id, cursor_id):
        """Return ``(target_pos, cursor_pos)`` indices in the deque for both
        ids in a single O(n) pass. ``-1`` means "not in deque".

        Used by the ack-cursor regression check (#9873-A D15 / AC-17). Event
        IDs are random 16-hex with no lexicographic ordering — deque insertion
        order is the only reliable monotonic signal. Single pass keeps the
        regression check at the same O(n) cost as the eviction check.

        Pass ``None`` for an id to skip its lookup (returns ``-1`` for that
        slot). Caller is expected to hold ``EventLifecycleManager._lock``
        already; this method acquires ``EventStream._lock`` inside.
        """
        t_pos, c_pos = -1, -1
        if not target_id and not cursor_id:
            return t_pos, c_pos
        with self._lock:
            for i, event in enumerate(self._events):
                eid = event.get("id")
                if target_id and eid == target_id:
                    t_pos = i
                if cursor_id and eid == cursor_id:
                    c_pos = i
                if (target_id is None or t_pos >= 0) and (
                    cursor_id is None or c_pos >= 0
                ):
                    break
        return t_pos, c_pos


EVENT_STATE_FILE = SQUIDSQUAD_DIR / ".event-state.json"


class EventLifecycleManager:
    """Manages the event stream's disk persistence and per-role cursors.

    Wraps EventStream with:
    - Disk persistence: events survive harness restarts (.event-state.json)
    - Per-role consumer cursors (#9873-A), advanced via ``ack-cursor``.

    #11165 (#11092 Decision 2): the dispatch / ack / in-flight tracking
    machinery was removed under pull-only — the harness only nudges and
    agents poll the forge + advance the cursor themselves.
    """

    def __init__(self, stream: EventStream):
        self._stream = stream
        self._lock = threading.Lock()
        # #9873-A: per-role consumer cursor. Populated by ack-cursor handler.
        # Persisted under "cursors" key in .event-state.json.
        self._cursors: dict[str, str] = {}
        self._loaded = False

    def append(self, event: dict):
        """Store event in stream and persist to disk."""
        self._stream.append(event)
        self._persist()

    def get_cursor(self, role: str):
        """Return the current cursor event_id for ``role``, or ``None`` if no
        cursor exists yet (first boot, or role has never sent ack-cursor).

        Lock-free read per #9873-A R2 D5 / AC-3: CPython ``dict.get()`` is
        atomic at the interpreter level. A momentarily stale-by-microseconds
        value is acceptable; cursor updates are infrequent. Holding
        ``threading.Lock`` here would block the asyncio event loop on the
        ``GET /events/cursor/{role}`` endpoint — exactly the H6 hazard the
        design mitigates.
        """
        return self._cursors.get(role)

    def advance_cursor(self, role: str, event_id: str):
        """Advance the cursor for ``role`` to ``event_id``. Called from the
        ack-cursor handler (off the asyncio loop via ``asyncio.to_thread``).

        Reject (no-op) when:
        - the event_id is no longer in the deque (FIFO-evicted) — D8 / AC-8 /
          AC-16. Eviction check via ``EventStream.has_event``.
        - the event_id appears earlier in the deque than the current cursor —
          D15 / AC-17. Out-of-order ack delivery would silently regress the
          cursor; deque insertion order is the only reliable monotonic signal
          since event IDs are random 16-hex with no lexicographic ordering
          (RESEARCH-9873-A §9 Q3).

        Lock ordering (#9873-A §4 / AC-19): this method acquires
        ``EventLifecycleManager._lock`` (outer) before calling
        ``EventStream.has_event`` / ``EventStream.find_positions`` which
        acquire ``EventStream._lock`` (inner). The established ordering is
        confirmed by the existing ``_persist()`` path (``self._lock`` →
        ``self._stream.get_recent(200)``). No code path acquires the inner
        lock before the outer lock — verified by audit during -A implementation.

        Returns one of:
        - ``"advanced"`` — cursor was advanced and persisted
        - ``"evicted"`` — event_id no longer in deque, cursor unchanged
        - ``"regression"`` — event_id earlier than current cursor, cursor unchanged
        - ``"noop"`` — empty role/event_id (defensive; no-op without logging)
        """
        if not role or not event_id:
            return "noop"
        with self._lock:
            # Eviction check inside the lock (#9902 F1 / AC-19): doing it
            # outside lets the deque mutate between has_event and the
            # cursor mutation below, which could (a) misclassify eviction
            # as regression, or (b) advance the cursor to an already-evicted
            # event_id — directly violating D8.
            if not self._stream.has_event(event_id):
                return "evicted"
            current = self._cursors.get(role)
            if current is not None and current != event_id:
                # Regression detection: only meaningful when both ids are in
                # the deque. find_positions returns -1 for ids not present.
                target_pos, cursor_pos = self._stream.find_positions(
                    event_id, current
                )
                # #9902 F1: if target was evicted between has_event and here
                # (eviction can happen via concurrent emit even with the
                # outer lock — has_event acquires the inner EventStream
                # lock, which is released before find_positions reacquires
                # it), return "evicted" not "advanced".
                if target_pos < 0:
                    return "evicted"
                if cursor_pos >= 0 and target_pos < cursor_pos:
                    return "regression"
            self._cursors[role] = event_id
        # Persist outside the lock — _persist() re-acquires self._lock
        # internally (matches the existing ack()/dispatch() discipline).
        # Last-write-wins on concurrent advances is acceptable; cursor
        # state is recoverable from event history on next boot.
        self._persist()
        return "advanced"

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
                # #9873-A: per-role consumer cursors. Pre-migration state
                # files lack this key — load() uses .get("cursors", {}).
                "cursors": dict(self._cursors),
            }
            try:
                tmp = EVENT_STATE_FILE.with_suffix(".tmp")
                tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
                tmp.replace(EVENT_STATE_FILE)
            except OSError:
                pass  # Best-effort — don't crash harness on persist failure

    def load(self):
        """Restore event state from disk on harness restart. Idempotent.

        Thread-safety (#9357): the ``_loaded`` check-and-set is wrapped
        in ``self._lock`` so concurrent callers cannot both pass the
        idempotency guard and double-load the event stream. Once a
        thread claims the load (sets ``_loaded=True``), any concurrent
        caller observes True and returns immediately — matching the
        existing semantics where any prior load attempt (including
        missing-file or parse-error fast paths) marks the manager as
        loaded so the next call is a silent no-op.

        Today ``load()`` is only called from ``_deferred_init`` on the
        lifespan thread, but the guard is the only defense against a
        future refactor that fans the call out across multiple threads
        (which would otherwise re-append events into ``EventStream``
        and inflate ``_total_emitted_count`` introduced in #9331).
        """
        # Claim the load atomically. Mark _loaded BEFORE doing any work
        # so a concurrent caller can't slip in between the check and the
        # state mutations below. If we crash mid-load, the existing
        # fast-path semantics (set _loaded=True on missing file or parse
        # error → next call returns silently) are preserved.
        with self._lock:
            if self._loaded:
                return
            self._loaded = True

        if not EVENT_STATE_FILE.exists():
            return
        try:
            raw = EVENT_STATE_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError):
            return

        # Restore cursors under lock, then load events outside to maintain
        # consistent lock ordering: self._lock → EventStream._lock.
        # #11165: the in-flight/dispatch state was deleted under pull-only;
        # old state files that still carry those keys are silently ignored.
        events_to_load = data.get("events", [])
        with self._lock:
            # #9873-A AC-1 / R2 F5: backward-compat — pre-migration state
            # files have no "cursors" key. data.get(..., {}) prevents a
            # KeyError that would crash harness boot on existing deployments.
            self._cursors = {
                r: str(eid) for r, eid in data.get("cursors", {}).items()
                if isinstance(eid, str) and eid
            }
        # Append events outside self._lock (acquires EventStream._lock)
        for event in events_to_load:
            self._stream.append(event)

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

        event_lifecycle.load()
        activity_detector.start()
        _log(f"Event state loaded: {len(event_stream)} events in stream")

        # E1 check + state.load_state() ran SYNCHRONOUSLY in lifespan
        # before yield (per DS-10680 review F3 — the TOCTOU race fix).
        # Spawn paths beyond auto-start (HTTP /agents/*/start, the
        # health poller's auto-reboot) read ``state.compose_freshness_failed``
        # directly so they enforce the same refusal.
        if state.compose_freshness_failed:
            _log(
                "Auto-start skipped — compose freshness check failed. "
                "Operator: fix the source issue + restart the harness."
            )
            return

        # Skip initial update_health() — it's slow on Windows (tasklist per agent).
        # The health poller will pick up state within HEALTH_POLL_INTERVAL seconds.

        # Auto-start all agents on harness boot — gated by #9242 escape
        # hatch so operators can isolate the auto-start path from HTTP
        # wedges during diagnosis.
        if _NO_AUTO_START:
            _log(
                "Auto-start skipped (#9242 --no-auto-start). Start "
                "agents manually with `POST /agents/{role}/start` "
                "or `squidsquad start <role>`."
            )
            return
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
                        agent_state.last_spawn_at = time.time()  # #12244 P2
                        agent_state.last_session_end = None  # #12418 F3
                        agent_state.last_dispatch_at = None  # #12271 slice d (DS-c1 F4)
                        agent_state.reset_session_telemetry()  # #13113
                        agent_state.terminal_pid = result.get("terminal_pid")
                    state.set_agent(role, agent_state)
            state.save_state()
            # #12912 S5: if boot detected compose-source drift, emit deploy-signals
            # to the freshly-spawned agents so each recomposes pull-first (§10 step
            # 1b). Safe to emit now even though agents are still booting — the
            # harness holds their events until status=ready and the deploy-signal is
            # delivered in the agent's boot drain (§8.2).
            if getattr(state, "_boot_deploy_drift", False):
                _emit_boot_deploy_signals()
                state._boot_deploy_drift = False
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

    # PRD-E E1 (#10680): boot-time freshness check (Layer 1 — primary
    # gate). Runs SYNCHRONOUSLY in lifespan BEFORE yield so the server
    # never accepts spawn requests while the gate is still deciding
    # (per DS-10680 review F3). On failure, ``state.compose_freshness_failed``
    # blocks every spawn path: ``_deferred_init`` auto-start short-
    # circuits, HTTP ``/agents/{role}/start`` returns 503, and the
    # health poller's auto-reboot loop also gates on the flag.
    _log("Loading saved state...")
    state.load_state()
    if _NO_FRESHNESS_CHECK:
        # PRD-E E5 (#10684) AC3: operator escape hatch for emergency
        # boots. Logs ONCE so the bypass surfaces in the audit trail.
        _log(
            "compose freshness check SKIPPED — `--no-freshness-check` "
            "or `SQUIDSQUAD_HARNESS_NO_FRESHNESS_CHECK=1` is set. "
            "Operator is responsible for source-tree freshness."
        )
        _freshness = None
    else:
        try:
            import compose_freshness as _cf
            # #12912 S5 (HARNESS-ARCH §10 step 1b retired): DETECT-ONLY. The boot
            # path no longer runs compose.py deploy-all locally — local compose
            # has no guarantee the source tree is current (the clone may be behind
            # origin/main), the root cause of the stale-source revert. On drift we
            # emit deploy-signals (after spawn) so each clone recomposes pull-first.
            _freshness = _cf.check_and_repair(
                repo_root=REPO_ROOT,
                stored_checksum=state.get_last_compose_checksum(),
                detect_only=True,
            )
        except Exception as e:  # noqa: BLE001 — defensive against import bugs
            _log(
                f"WARNING: compose_freshness check raised {e!r}; proceeding "
                f"without the E1 gate (degraded boot)"
            )
            _freshness = None
    if _freshness is not None:
        # Detect-only never composes, so it never returns "failed"/"repaired".
        # The legacy boot-compose spawn-refusal gate is retired — compose failures
        # now surface per-clone as deploy-error events (§11) — so clear any stale
        # persisted flag that would otherwise block auto-start forever.
        state.compose_freshness_failed = False
        if _freshness.status == "drift":
            state._boot_deploy_drift = True
            state.save_state()
            _log(
                f"compose freshness: {_freshness.diagnostic} — deploy-signals "
                f"will be emitted after agent spawn (no local compose)"
            )
        else:  # clean
            _log(
                f"compose freshness: clean (checksum "
                f"{_freshness.new_checksum[:12]}...)"
            )

    threading.Thread(target=_deferred_init, daemon=True, name="deferred-init").start()
    state.start_poller()
    # PRD-E E3 (#10682): L4-write file-watch supervisor. Starts after
    # the health poller so the order matches their wake-cadence
    # priorities (poller is the canonical liveness signal; the
    # file-watcher is best-effort and may degrade if watchdog is missing).
    state.start_l4_watcher()

    yield

    # Shutdown
    _log("Shutting down...")
    state.stop_l4_watcher()
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


# ---------------------------------------------------------------------------
# Error capture (#12824) — persist unhandled-exception tracebacks to disk.
#
# The #12824 assigned-to 500 transient could not be root-caused: the traceback
# went only to the harness terminal stdout, which was lost by the time the bug
# was investigated. These helpers write method+path+traceback to a persisted
# log so the NEXT 500 (or any swallowed internal hiccup) is diagnosable.
# ---------------------------------------------------------------------------


# Bound the error log so a recurring fault can't fill the disk (#12824
# DS-review F3): .squidsquad/ lives inside the repo checkout, so exhaustion
# would break ALL harness persistence (state saves, event persistence, port
# file). Single-file rotation caps total at ~2× this threshold.
_HARNESS_ERROR_LOG_MAX_BYTES = 1_000_000


def _harness_error_log_path() -> Path:
    """Path to the persisted harness error log. Resolved per-call so test
    isolation (SQUIDSQUAD_DIR override) is honored and the helper is patchable."""
    return SQUIDSQUAD_DIR / "harness-errors.log"


def _persist_harness_error(context: str) -> None:
    """Append the *current* exception's traceback to the harness error log.

    Call from inside an ``except`` block — ``traceback.format_exc()`` captures
    the active exception. ``context`` describes where it fired (method+path, or
    the swallowed-work site). Best-effort: any failure writing the log is
    itself swallowed so the error-logger can never mask the original fault.
    """
    tb = traceback.format_exc()
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry = f"\n===== {ts} {context} =====\n{tb}\n"
    try:
        log_path = _harness_error_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Rotate before append if the log has grown past the cap (DS-review F3).
        try:
            if (log_path.exists()
                    and log_path.stat().st_size > _HARNESS_ERROR_LOG_MAX_BYTES):
                log_path.replace(log_path.with_name(log_path.name + ".1"))
        except OSError:
            # Rotation is best-effort — fall through to the append regardless.
            pass
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(entry)
    except Exception:
        # Never let the error-logger itself raise — it runs on the failure path.
        pass


@app.exception_handler(Exception)
async def _capture_unhandled_exception(request: Request, exc: Exception):
    """Global 500 handler (#12824): persist the traceback, then return the
    standard 500 contract.

    Starlette routes ``HTTPException`` (the intentional 400/404/503 raises)
    through ``ServerErrorMiddleware``'s sibling ``ExceptionMiddleware``, so this
    handler only fires on genuinely-unhandled exceptions — the 500s we want
    diagnosable. The ``isinstance`` re-raise below is defensive belt-and-braces
    (DS-review F1): it makes the "4xx are unaffected" invariant explicit and
    robust even if that middleware split ever changes. The response body matches
    Starlette's default ``ServerErrorMiddleware`` 500 so no caller contract
    changes; the only added behavior is the on-disk traceback.
    """
    if isinstance(exc, HTTPException):
        # Intentional 4xx/503 — let Starlette render the real status. (Currently
        # unreachable here; see docstring.)
        raise exc
    _persist_harness_error(
        f"{request.method} {request.url.path} :: "
        f"{type(exc).__name__}: {exc}"
    )
    _log(
        f"500 on {request.method} {request.url.path}: "
        f"{type(exc).__name__}: {exc} (traceback → harness-errors.log)"
    )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


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
    """Harness + all agent health.

    #9481: no inline update_health() call. The previous implementation
    ran ``state.update_health()`` synchronously on the asyncio event
    loop; on Windows it shells out to ``tasklist`` per agent under
    ``state._lock`` and blocks for 10–20s on a cold cache, producing
    the cycle-1500 HTTP wedge (kernel accepts, dispatcher frozen,
    CloseWait pile-up). The background health poller already refreshes
    agent state every ``HEALTH_POLL_INTERVAL`` seconds — that is the
    authoritative freshness budget for /status, and operators get a
    millisecond response instead of a timeout.
    """
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
    """List agents with state.

    #9665: no inline update_health() call (extends #9481). On warm
    Windows runs the call exceeds 30s even off the event loop, which
    timed out callers like the #9398 real-subprocess tests. The
    background health poller (HEALTH_POLL_INTERVAL) is the
    authoritative freshness budget for this endpoint.
    """
    return {"agents": state.all_agents()}


@app.post("/agents/all/start")
async def start_all():
    """Spawn all configured agents."""
    # PRD-E E1 (#10680) / DS-10680 F1: the E1 spawn-refusal contract
    # applies to every spawn path, not just _deferred_init's auto-
    # start. Reject HTTP-driven spawns while the freshness gate is
    # red so the operator can't bypass the gate with a manual POST.
    if state.compose_freshness_failed:
        raise HTTPException(
            status_code=503,
            detail=(
                "Compose freshness check failed — agents cannot be "
                "spawned. Fix the source issue and restart the harness."
            ),
        )
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
                agent_state.last_spawn_at = time.time()  # #12244 P2
                agent_state.last_session_end = None  # #12418 F3
                agent_state.last_dispatch_at = None  # #12271 slice d (DS-c1 F4)
                agent_state.reset_session_telemetry()  # #13113
                agent_state.terminal_pid = result.get("terminal_pid")
            state.set_agent(role, agent_state)

    # #9242: disk write off the asyncio event loop.
    await asyncio.to_thread(state.save_state)
    return {"results": results}


@app.post("/agents/all/stop")
async def stop_all():
    """Stop all agents gracefully (#4966). Sets intent via API — no sentinel files."""
    roles = boot_remote._get_all_roles()
    _log(f"Stopping all agents: {', '.join(roles)}")

    results = []
    for role in roles:
        # #11640: an unregistered / missing clone now raises rather than
        # resolving to REPO_ROOT. Stopping such a role is a no-op (it can't
        # be running in a clone we refuse to resolve) — skip it instead of
        # 500-ing the whole endpoint.
        try:
            clone_path = boot_remote._get_clone_path(role)
        except boot_remote.CloneResolutionError as e:
            results.append({"role": role, "action": "skip", "success": True,
                            "message": f"skip (clone unresolved: {e})"})
            _log(f"  {role}: skip (clone unresolved — {e})")
            continue

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

    # #9242: disk write off the asyncio event loop.
    await asyncio.to_thread(state.save_state)
    return {"results": results}


@app.get("/agents/{role}")
async def get_agent(role: str):
    """Get single agent state.

    #9665: no inline update_health() call (extends #9481). See
    list_agents — same freshness rationale.
    """
    _validate_role(role)
    agent = state.get_agent(role)
    if agent is None:
        return {"role": role, "status": "unknown", "message": "No health data yet"}
    return agent.to_dict()


@app.post("/agents/{role}/start")
async def start_agent(role: str):
    """Spawn an agent in a visible terminal."""
    _validate_role(role)

    # PRD-E E1 (#10680) / DS-10680 F1: per-role spawn endpoint must
    # honor the E1 gate too. Same 503 + message as /agents/all/start.
    if state.compose_freshness_failed:
        raise HTTPException(
            status_code=503,
            detail=(
                "Compose freshness check failed — agents cannot be "
                "spawned. Fix the source issue and restart the harness."
            ),
        )

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
            agent_state.last_spawn_at = time.time()  # #12244 P2
            agent_state.last_session_end = None  # #12418 F3
            agent_state.last_dispatch_at = None  # #12271 slice d (DS-c1 F4)
            agent_state.reset_session_telemetry()  # #13113
            agent_state.terminal_pid = result.get("terminal_pid")
            # #8695: spawning a fresh agent → bootup-complete must be re-asserted
            # by the new process before we'll dispatch any events to it.
            agent_state.bootup_complete = False
        state.set_agent(role, agent_state)
        # #9242: disk write off the asyncio event loop.
        await asyncio.to_thread(state.save_state)
    elif result.get("action") == "error":
        # #11640: boot_agent refused to spawn (e.g. unregistered/missing
        # clone). No process started in REPO_ROOT — mark the agent error so
        # the failed start is visible, not silently retried.
        agent_state = state.get_agent(role) or AgentState(role)
        agent_state.status = "error"
        state.set_agent(role, agent_state)
        await asyncio.to_thread(state.save_state)

    status_code = 200 if result["success"] else 500
    return JSONResponse(status_code=status_code, content=result)


@app.get("/agents/{role}/health")
async def get_agent_health(role: str):
    """Agent health endpoint — process status, last cycle, phase, context pressure (#4966).

    #9665: no inline update_health() call (extends #9481). See
    list_agents — same freshness rationale.
    """
    _validate_role(role)
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

    # Read config.md for agent-relevant settings.
    # #9478 D2: `branch_workflow` field removed from response; branch+PR
    # is the only mode, no toggle to expose.
    try:
        import config as cfg
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
# Agent observability hooks (#12418 / HARNESS-ARCH §16) — native Claude Code
# `type: http` hooks POST their payload here directly (no shell wrapper).
# ---------------------------------------------------------------------------

@app.post("/hooks/session-end")
async def hook_session_end(request: Request):
    """#12418 — receive a Claude Code `SessionEnd` hook for an agent session.

    The git-tracked `.claude/settings.json` wires ONE native `type: http`
    SessionEnd hook shared by every clone; it carries the agent's role in an
    ``X-Agent-Role`` header interpolated from the ``$SQUIDSQUAD_ROLE`` env var
    (set per-clone at spawn — thin_launcher / direct-spawn). Claude Code POSTs
    the SessionEnd payload here (``{hook_event_name, session_id, stop_reason,
    ...}``). We record the ``stop_reason`` + arrival time on AgentState — the
    PRESENCE of a record stamped after ``last_spawn_at`` means the agent exited
    GRACEFULLY (a hook ran); its ABSENCE before a dead PID means a crash. The
    reboot decision (§7.4 / update_health) keys off that (#12418 AC4).

    Fail-open contract (HARNESS-ARCH §16.3): this endpoint ALWAYS returns 200
    quickly. A hook must never block or fail the agent's teardown, so we never
    raise — a malformed body, missing/unknown role, or write hiccup still
    answers 200.
    """
    role = (request.headers.get("X-Agent-Role") or "").strip()
    # DS-REVIEW-12418-A F5: if $SQUIDSQUAD_ROLE was unset at spawn, Claude Code
    # sends the literal "${SQUIDSQUAD_ROLE}". Treat an uninterpolated token as
    # no-role rather than an unknown-role drop, so logs stay honest.
    if role.startswith("${"):
        role = ""
    try:
        body = await request.json()
    except Exception:
        body = {}
    reason = (isinstance(body, dict) and body.get("stop_reason")) or "unknown"

    if not role:
        _log(f"SessionEnd hook DROPPED — no X-Agent-Role header (reason={reason!r})")
        return JSONResponse(status_code=200, content={"ok": False, "dropped": "no-role"})

    # Defense-in-depth (mirrors receive_event #9242): ignore unknown roles so a
    # stray hook can't seed a ghost agent — but STILL 200 (fail-open).
    try:
        allowed = set(boot_remote._get_all_roles()) | {"pm"}
    except (SystemExit, Exception):
        allowed = None
    if allowed is not None and role not in allowed:
        _log(f"SessionEnd hook DROPPED unknown role={role!r} (reason={reason!r})")
        return JSONResponse(status_code=200, content={"ok": False, "dropped": "unknown-role"})

    with state._lock:
        agent = state.agents.get(role)
        if agent is None:
            agent = AgentState(role)
            state.agents[role] = agent
        agent.last_session_end = {"reason": reason, "at": time.time()}
    # Persist off the event loop; swallow any error (fail-open).
    try:
        await asyncio.to_thread(state.save_state)
    except Exception as e:  # pragma: no cover — defensive
        _log(f"{role}: SessionEnd save_state failed (non-fatal): {e}")
    _log(f"{role}: SessionEnd reason={reason!r} recorded (#12418)")
    return JSONResponse(status_code=200, content={"ok": True})


# #12443 — activity-heartbeat persistence throttle. These hooks fire on EVERY
# tool call, so we update the in-memory AgentState immediately (that is what
# GET /agents/{role} reads) but rate-limit the state-FILE write: a heartbeat
# only persists to disk if the last persist was at least this many seconds ago.
# Disk staleness up to this window is harmless — last_activity_at matters for
# live liveness (in-memory), and persistence only backstops a harness restart.
_ACTIVITY_SAVE_THROTTLE_SECONDS = 30
_last_activity_save_at = 0.0


@app.post("/hooks/activity")
async def hook_activity(request: Request):
    """#12443 — receive an agent activity heartbeat (HARNESS-ARCH §15.1).

    Emitted by the per-clone `PostToolUse` / `PostToolUseFailure` async command
    hooks (every tool call) and by `cycle_post` (every completed cycle). The
    heartbeat proves the agent's real loop is PROGRESSING — a wedged loop stops
    making tool calls and completing cycles, so the heartbeat stops. We record
    `last_activity_at` (+ enriched {event, tool, phase}) per agent; the reboot
    decision does NOT yet consume it (observational this slice — #12271 d).

    Role rides the `X-Agent-Role` header (same contract as /hooks/session-end).

    Fail-open contract (§16.3): ALWAYS 200, never blocks or raises. Disk
    persistence is throttled (`_ACTIVITY_SAVE_THROTTLE_SECONDS`) since these
    fire per tool call — the in-memory value that GET /agents/{role} reads is
    always current; only the state-file write is rate-limited.
    """
    global _last_activity_save_at
    role = (request.headers.get("X-Agent-Role") or "").strip()
    # Mirror /hooks/session-end F5: an uninterpolated token = no-role.
    if role.startswith("${"):
        role = ""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}

    if not role:
        # Log the DROP paths (DS-REVIEW-12443-harness F1): these fire only on a
        # MISCONFIGURED header, so a healthy agent never logs here — a steady
        # stream is the diagnostic signal that the X-Agent-Role wiring is wrong
        # (distinguishes "no heartbeats" from "heartbeats silently dropped").
        # The SUCCESS path is logged only at the throttle cadence below (it
        # fires per tool call — logging each would be spam).
        _log("Activity hook DROPPED — no X-Agent-Role header")
        return JSONResponse(status_code=200, content={"ok": False, "dropped": "no-role"})

    # Defense-in-depth (mirrors /hooks/session-end + receive_event #9242): drop
    # unknown roles so a stray hook can't seed a ghost agent — but STILL 200.
    try:
        allowed = set(boot_remote._get_all_roles()) | {"pm"}
    except (SystemExit, Exception):
        allowed = None
    if allowed is not None and role not in allowed:
        _log(f"Activity hook DROPPED unknown role={role!r}")
        return JSONResponse(status_code=200, content={"ok": False, "dropped": "unknown-role"})

    now = time.time()
    activity = {
        "at": now,
        "event": body.get("event") or body.get("hook_event_name"),
        "tool": body.get("tool") or body.get("tool_name"),
        "phase": body.get("phase"),
    }
    should_save = False
    with state._lock:
        agent = state.agents.get(role)
        if agent is None:
            agent = AgentState(role)
            state.agents[role] = agent
        agent.last_activity_at = now
        agent.last_activity = activity
        # #12458 — manage the in-flight tool-call window (pause guard). A
        # PreToolUse opens it (deadline now + tool_call_max so a long tool call
        # isn't mistaken for a wedge); a Post* closes it. A real TOOL-CALL event
        # also clears a stale 'waiting' — the agent is demonstrably executing,
        # so it is no longer blocked on a prompt. DS-REVIEW-12458-plumbing F2:
        # scope the waiting-clear to the three tool-use events, NOT every
        # activity — a cycle_post heartbeat (or any non-tool event) is a weaker
        # signal and a late one from a prior cycle could otherwise race a fresh
        # Notification and prematurely clear a legitimate wait.
        ev = activity["event"]
        if ev == "PreToolUse":
            agent.in_flight_until = now + TOOL_CALL_MAX_SECONDS
            agent.waiting_since = None
        elif ev in ("PostToolUse", "PostToolUseFailure"):
            agent.in_flight_until = None
            agent.waiting_since = None
        if now - _last_activity_save_at >= _ACTIVITY_SAVE_THROTTLE_SECONDS:
            _last_activity_save_at = now
            should_save = True
    if should_save:
        # Throttled success log (DS-REVIEW-12443-harness F1): a low-noise
        # "still alive" breadcrumb at the persistence cadence (~once/30s per
        # agent), NOT per tool call. Confirms heartbeats are arriving + being
        # recorded without flooding the log.
        _log(f"{role}: activity recorded ({activity.get('event')}, #12443)")
        try:
            await asyncio.to_thread(state.save_state)
        except Exception as e:  # pragma: no cover — defensive
            _log(f"{role}: activity save_state failed (non-fatal): {e}")
    return JSONResponse(status_code=200, content={"ok": True})


@app.post("/hooks/pause")
async def hook_pause(request: Request):
    """#12458 (#12271 slice c) — receive a pause-explaining lifecycle hook so
    the reboot decision (update_health) holds off while the silence is
    explained (HARNESS-ARCH §15.1). Low-frequency relative to /hooks/activity,
    so these are native http hooks (a brief block is acceptable) and the write
    is NOT throttled.

    Dispatches on the hook event:
      - Notification   → waiting_since = now   (blocked on a prompt/idle/input)
      - PreCompact     → compacting_since = now (summarising context in place)
      - PostCompact    → compacting_since = None (compaction done)
      - StopFailure    → last_stop_failure = {cause, at}; a recent
        rate_limit/overloaded makes a subsequent death back off (AC3d). The
        cause is read best-effort from several candidate fields; an
        unrecognised cause records 'unknown', which does NOT trigger backoff
        (safe default: the normal reboot path runs, today's behavior).

    Role rides the X-Agent-Role header (same contract as /hooks/session-end).
    Fail-open: ALWAYS 200, never blocks or raises.
    """
    role = (request.headers.get("X-Agent-Role") or "").strip()
    if role.startswith("${"):
        role = ""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}

    if not role:
        _log("Pause hook DROPPED — no X-Agent-Role header")
        return JSONResponse(status_code=200, content={"ok": False, "dropped": "no-role"})
    try:
        allowed = set(boot_remote._get_all_roles()) | {"pm"}
    except (SystemExit, Exception):
        allowed = None
    if allowed is not None and role not in allowed:
        _log(f"Pause hook DROPPED unknown role={role!r}")
        return JSONResponse(status_code=200, content={"ok": False, "dropped": "unknown-role"})

    event = body.get("event") or body.get("hook_event_name") or ""
    now = time.time()
    with state._lock:
        agent = state.agents.get(role)
        if agent is None:
            agent = AgentState(role)
            state.agents[role] = agent
        if event == "Notification":
            agent.waiting_since = now
        elif event == "PreCompact":
            agent.compacting_since = now
        elif event == "PostCompact":
            agent.compacting_since = None
        elif event == "StopFailure":
            # Best-effort cause extraction — the exact StopFailure payload field
            # is config/version dependent; an unknown cause is the safe default
            # (no backoff → normal reboot path, unchanged behavior). DS-REVIEW-
            # 12458-plumbing F5: `matcher` is the hook TRIGGER pattern, not the
            # stop reason — excluded so a future named matcher can't be
            # mistaken for the cause.
            cause = (body.get("cause") or body.get("reason")
                     or body.get("stop_reason") or "unknown")
            agent.last_stop_failure = {"cause": cause, "at": now}
        else:
            _log(f"{role}: pause hook unrecognised event={event!r} — ignored")
            return JSONResponse(status_code=200,
                                content={"ok": False, "dropped": "unknown-event"})
    _log(f"{role}: pause hook {event} recorded (#12458)")
    try:
        await asyncio.to_thread(state.save_state)
    except Exception as e:  # pragma: no cover — defensive
        _log(f"{role}: pause save_state failed (non-fatal): {e}")
    return JSONResponse(status_code=200, content={"ok": True})


# ---------------------------------------------------------------------------
# Event bus endpoints (#4709 Phase 2)
# ---------------------------------------------------------------------------

@app.post("/events")
async def receive_event(request: Request):
    """Receive an event from an agent mechanical script.

    Stores in bounded stream, updates AgentState, logs to console.

    Response contract (#11404):
    - Missing ``event_type`` or ``role`` → ``400`` (hard reject).
    - ``role`` not in the install's registered aliases (+ ``pm``) → ``204 No
      Content``. This is an INTENTIONAL silent fire-and-forget drop (#9242):
      the event is NOT stored, yet the caller still sees a 2xx. The internal
      ``_emit_event`` path bypasses this guard, so production emits are
      unaffected; a direct HTTP caller with a bad role is dropped on purpose
      to keep malformed roles out of ``.event-state.json``.
    - Otherwise stored with ``200``. If the body omits ``id``, one is
      auto-assigned (#11404 AC1) so the event cannot be silently skipped by
      id-tracking consumers (``event_poll`` skips id-less events).
    """
    # #13156: fail CLOSED on a malformed body. stdlib json.loads (strict=True,
    # used by Starlette's request.json()) raises JSONDecodeError on a raw
    # (unescaped) control character in a string field — e.g. a hand-built /
    # curl body or an emit path that serializes multi-line text without
    # JSON-escaping. Unguarded, that propagated to the global handler as a 500
    # (47x in harness-errors.log, a fixed-position retry loop). Reject cleanly
    # with 400 instead so the bad event is dropped, not crashed-on. (ValueError
    # covers JSONDecodeError + UnicodeDecodeError, both ValueError subclasses.)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError) as e:
        _log(f"DROPPED malformed event body (400): {e}")
        raise HTTPException(status_code=400, detail=f"malformed JSON body: {e}")

    # Validate minimal fields
    event_type = body.get("event_type")
    role = body.get("role")
    if not event_type or not role:
        raise HTTPException(status_code=400, detail="event_type and role are required")

    # #9242: reject unknown roles at the ingestion boundary. Prior to
    # this guard, events with role="unknown" (emitted by git_ops.py
    # before the source fix) were persisted into .event-state.json AND
    # created ghost agent entries in .harness-state.json — both
    # contributors to the HTTP-wedge cascade. Defense in depth: even
    # after the git_ops.py:90 source fix, any future regression that
    # produces a malformed role is dropped at the boundary instead of
    # corrupting state.
    try:
        allowed_roles = set(boot_remote._get_all_roles()) | {"pm"}
    except (SystemExit, Exception):
        # Config unreadable — fall open rather than reject everything.
        # The original symptom (HTTP wedge) is worse than letting one
        # weird event through during a misconfigured boot.
        allowed_roles = None
    if allowed_roles is not None and role not in allowed_roles:
        _log(
            f"DROPPED event with unknown role={role!r} "
            f"(type={event_type!r}); allowed={sorted(allowed_roles)}"
        )
        # 204 No Content — caller succeeds (emit is fire-and-forget per
        # event_bus.emit's contract) but we don't store the event.
        # MUST be body-less: a 204 carrying a JSON body (the old
        # `JSONResponse(status_code=204, content={})`) makes h11 raise
        # `LocalProtocolError: Too much data for declared Content-Length` on the
        # real uvicorn server — h11 forbids a body on 204, so the 2-byte `{}`
        # overruns the (zero) allowed length, poisoning the keep-alive
        # connection and stalling subsequent event delivery (#12574).
        return Response(status_code=204)

    # Stamp received_at for ordering (#5622)
    body["received_at"] = time.time()

    # #11404 AC1: auto-assign an id when the caller omits one. event_poll and
    # every consumer skip id-less events (the cursor cannot track them), so an
    # id-less POST would be stored at 200 yet silently never delivered. Match
    # the 16-hex shape _emit_event uses (#9415 D4) so both append paths produce
    # the same id width.
    if not body.get("id"):
        body["id"] = os.urandom(8).hex()

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
        # #9242: disk write off the asyncio event loop — receive_event is
        # POSTed on every emit, so this is the hottest path.
        await asyncio.to_thread(state.save_state)
        _log(f"{role}: bootup-complete — event dispatch unlocked")

    # Ack processing (#9873-A): the previous single ``ack`` event type is
    # split into ``ack-cursor`` (advance consumer cursor) and ``ack-stop``
    # (preserve stop-confirmed branch). D6 locks the split. The old
    # dispatch-side ``event_lifecycle.ack()`` / in-flight tracker was deleted
    # outright under pull-only (#11165 / #11092 D2); only cursor advancement
    # remains.
    if event_type == "ack-cursor":
        # #9902 F4: guard against payload being present-but-not-dict (e.g.
        # a string from a malformed POST). The default `{}` only triggers
        # on missing key, not on wrong type — without the isinstance check
        # `.get("event_id")` would AttributeError → 500.
        ack_payload = body.get("payload")
        if not isinstance(ack_payload, dict):
            ack_payload = {}
        ack_event_id = ack_payload.get("event_id")
        if ack_event_id and role:
            # D4 / AC-9: cursor advance + persist runs off the asyncio loop.
            # advance_cursor takes EventLifecycleManager._lock (outer) and
            # then EventStream._lock (inner) — see §4 audit / AC-19.
            result = await asyncio.to_thread(
                event_lifecycle.advance_cursor, role, ack_event_id
            )
            if result == "advanced":
                _log(f"Event {ack_event_id} cursor-advanced by {role}")
            elif result == "evicted":
                # AC-8 / AC-16: silent reject + debug log.
                _log(
                    f"ack-cursor rejected: event_id={ack_event_id} not in "
                    f"retained deque for role={role} (evicted)"
                )
            elif result == "regression":
                # AC-17: out-of-order ack delivery — cursor unchanged.
                _log(
                    f"ack-cursor regression rejected: event_id={ack_event_id} "
                    f"earlier than current cursor for role={role}"
                )
    elif event_type == "ack-stop":
        # Repurposed branch — preserves the existing stop-confirmed behavior
        # at the previous L1547-1557 verbatim per D6. AC-12 guards no
        # regression in the stop-confirmation flow. Payload field name is
        # ``event_id`` (consistent with ack-cursor, locked by D6/D10).
        # #9902 F4: guard against non-dict payload (see ack-cursor branch).
        ack_payload = body.get("payload")
        if not isinstance(ack_payload, dict):
            ack_payload = {}
        ack_event_id = ack_payload.get("event_id")
        if ack_event_id and role:
            _log(f"Event {ack_event_id} ack-stop from {role}")
            # If ack references stop-requested, treat as shutdown confirmation.
            # The ack only confirms an already-requested stop — it must not
            # reset `intent_set_at` (which would extend the 60s force-kill
            # window indefinitely under repeated acks per CONTEXT-4792.md
            # §3.3 Q7). Also only fires when the agent is still in STOPPING:
            # any subsequent operator action (RUNNING / RESTARTING / STOPPED)
            # supersedes this ack, which is now stale.
            #
            # #13148: the stop-path ack-stop result enum is SETTLED to
            # 'checkpointed' | 'aborted' | 'drained' (AGENT-RUNTIME §10 Q11,
            # closed 2026-05-30). This branch previously keyed on the obsolete
            # 'stop-confirmed' (NOT in the enum) — so a correctly-emitted stop
            # ack would have silently missed it. Recognize the settled values:
            # 'checkpointed'/'drained' = clean stop; 'aborted' = graceful stop
            # FAILED → the existing 60s force-kill net is the escalation (logged
            # for visibility). No agent-side emitter exists yet (event_bus
            # .ack_stop has no callers); wiring one is the follow-on — this
            # aligns the handler so it works correctly when that lands.
            _stop_result = ack_payload.get("result")
            if _stop_result in ("checkpointed", "aborted", "drained"):
                if _stop_result == "aborted":
                    _log(f"{role}: ack-stop result=aborted (graceful stop FAILED)"
                         f" — 60s force-kill net will escalate")
                with state._lock:
                    agent = state.agents.get(role)
                    if agent and agent.intent == AgentState.INTENT_STOPPING:
                        # Intent already STOPPING and intent_set_at already
                        # recorded at request time — do NOT reset it (would
                        # extend the 60s window). The save_state below is a
                        # no-op for these fields but kept for parity with
                        # other ack paths.
                        pass
                # #9242: disk write off the asyncio event loop.
                await asyncio.to_thread(state.save_state)
            elif ack_payload.get("result") == "deploy-halted":
                # #12912 (HARNESS-ARCH §7.1 / §7.4 / AGENT-RUNTIME §5.2): the
                # agent finished its current atomic unit and halted on a
                # deploy-signal. Intent was set to DEPLOYING at emit time
                # (intent-sequencing, AC9), so the imminent PID death is NOT
                # auto-respawned by the health poller. Record the halt and hand
                # off to the pull-first deploy sequence (ensure-main → pull →
                # compose deploy <alias> → commit → push → respawn), which runs
                # off the asyncio loop (S4).
                with state._lock:
                    agent = state.agents.get(role)
                    if agent:
                        if agent.intent != AgentState.INTENT_DEPLOYING:
                            # Defensive: the emit side (S3) sets DEPLOYING; keep
                            # the invariant even if a deploy-halted ack races the
                            # emit-side intent write. On the boot-drift path the
                            # emit side does NOT pre-set intent (pid_changed reset
                            # race), so THIS is where DEPLOYING is established —
                            # synchronously, before the agent's PID death is polled
                            # (the agent exits only after emitting this ack-stop),
                            # which is the intent-sequencing guarantee on the boot
                            # path (DS-12912 Finding 4).
                            agent.intent = AgentState.INTENT_DEPLOYING
                            agent.intent_set_at = time.time()
                        agent.status = "deploying"
                        # DS-12912 Finding 3 (HARNESS-ARCH §7.3): arm a respawn-
                        # suppression window across the git/compose deploy as
                        # defense-in-depth (status="deploying" already keeps it out
                        # of is_dead; the deploy sequence respawns explicitly and
                        # clears this).
                        agent.reboot_blocked_until = time.time() + _DEPLOY_WINDOW_SECONDS
                await asyncio.to_thread(state.save_state)
                _log(f"{role}: deploy-halted — handing off to deploy sequence")
                # #12912 S4: run the pull-first per-clone deploy sequence off the
                # asyncio loop. The thread serializes on _deploy_lock so multiple
                # affected clones deploy sequentially (AC8), avoiding push races.
                # The deploy-signal's event_id (ack_event_id, set by the agent per
                # event-mode-contract Case E) is passed so the harness can advance
                # the agent's cursor past the deploy-signal before respawn —
                # without which the respawned agent re-fetches and re-halts on it
                # (DS-12912 Finding 1 / AC4 infinite-loop guard).
                threading.Thread(
                    target=_run_deploy_sequence, args=(role, ack_event_id),
                    daemon=True, name=f"deploy-{role}",
                ).start()

    # Update AgentState from event.
    # #12824: fail-soft. The event_lifecycle.append above is the
    # routing-critical work (it is what wakes event-mode agents); this
    # post-append bookkeeping is non-critical. A throw here must NOT 500 the
    # emission path — assigned-to nudges and EAD handoff routing ride this same
    # path, and a 500 on it silently breaks waking dormant agents (#12824).
    # Swallow + persist the traceback (so the next occurrence is diagnosable)
    # rather than failing the request.
    try:
        _update_agent_from_event(body)
    except Exception:
        _persist_harness_error(
            f"POST /events post-append _update_agent_from_event "
            f"(type={event_type!r}, role={role!r})"
        )
        _log(
            f"post-append _update_agent_from_event failed for "
            f"type={event_type!r} role={role!r} — swallowed (see harness-errors.log)"
        )

    # Log to console
    try:
        _log_event(body)
    except Exception:
        _persist_harness_error(
            f"POST /events post-append _log_event "
            f"(type={event_type!r}, role={role!r})"
        )
        _log(
            f"post-append _log_event failed for type={event_type!r} "
            f"role={role!r} — swallowed (see harness-errors.log)"
        )

    return {"status": "ok"}


@app.post("/work/assign")
async def work_assign(request: Request):
    """Manual wake-injection primitive (#12495).

    Emits an ``assigned-to`` event to ``target_alias`` **without** a status
    transition — the distinguishing feature versus ``tracker.py transition``.
    This is the sanctioned BACKUP / babysitting path for waking a stuck-but-
    alive agent (PM duty) or surfacing a process concern to PM, for when the
    PRIMARY wake paths (self-wake #12506, never-stop #12853, EAD on forge-state
    change) don't fire. It is NOT the default routing mechanism: transition-
    driven handoffs are routed by the ExternalActivityDetector off forge state
    (AGENT-RUNTIME §8.3), not through this endpoint.

    Deliberately does **not** rewrite the ``role:*`` label: a manual re-nudge
    targets work the agent already owns (or pings PM), so ownership is
    unchanged. (The aspirational "universal router that rewrites labels on every
    call" §8.3 design is NOT what this implements — see the #12495 changelog.)

    Response contract (matches HARNESS-ARCH §4.3):
    - ``200`` ``{"status": "ok", "event_id": ...}`` — assigned-to emitted.
    - ``404`` — ``target_alias`` not in the install's registered aliases.
    - ``400`` — malformed body, missing ``target_alias``, or self-assign
      (``target_alias == X-Squidsquad-Alias``; structural anti-loop invariant).

    Check order: malformed-body → missing-target → self-assign (400) →
    alias-existence (404). Self-assign is checked before existence so a
    self-targeted call returns the terse 400 rather than a 404 that would
    echo the full known-alias registry. If the config is unreadable the
    existence check falls OPEN (same posture as POST /events' unknown-role
    guard — a broken-config wedge is worse than letting one event through).

    Authority: the harness enforces only alias-existence + the self-assign
    invariant — NOT class-from-class permissions (decision-class-vs-alias-
    routing-model, 2026-05-25). Who *should* call it (PM babysitting; any agent
    escalating a process concern to PM) is process discipline documented in
    §8.3, not a harness gate.
    """
    # Fail CLOSED on a malformed body, same guard as POST /events (#13156).
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError) as e:
        _log(f"DROPPED malformed /work/assign body (400): {e}")
        raise HTTPException(status_code=400, detail=f"malformed JSON body: {e}")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")

    target_alias = body.get("target_alias")
    if not target_alias:
        raise HTTPException(status_code=400, detail="target_alias is required")

    # Self-assign invariant: an agent may not assign work to itself (structural
    # anti-loop, not a permission check). The caller's identity is the
    # X-Squidsquad-Alias request header; absent header → caller unidentified,
    # invariant un-checkable, so it is skipped (the tracker.py CLI always sets
    # it). EAD does not use this HTTP path, so no __ead__ sentinel is needed.
    emitter_alias = request.headers.get("X-Squidsquad-Alias")
    if emitter_alias and emitter_alias == target_alias:
        raise HTTPException(
            status_code=400,
            detail=f"self-assign forbidden: target_alias == emitter ({target_alias})",
        )

    # Alias-existence validation (the harness's one routing check).
    try:
        allowed_roles = set(boot_remote._get_all_roles()) | {"pm"}
    except (SystemExit, Exception):
        # Config unreadable — fall open rather than reject (same posture as
        # POST /events' unknown-role guard).
        allowed_roles = None
    if allowed_roles is not None and target_alias not in allowed_roles:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown alias",
                "target_alias": target_alias,
                "known_aliases": sorted(allowed_roles),
            },
        )

    # Build the assigned-to payload. issue_number / event_context / payload are
    # all optional for a manual wake; event_context defaults to "work-assign".
    issue_number = body.get("issue_number")
    event_context = body.get("event_context") or "work-assign"
    extra_payload = body.get("payload")
    payload = {
        "target_alias": target_alias,
        "event_context": event_context,
    }
    if issue_number is not None:
        payload["issue_number"] = str(issue_number)
    if isinstance(extra_payload, dict):
        # Caller-supplied payload fields ride through (e.g. title, concern).
        # Reserved keys above win to keep the event shape coherent.
        for k, v in extra_payload.items():
            payload.setdefault(k, v)

    event = _emit_event("assigned-to", "harness", payload=payload)
    _log(
        f"/work/assign → {target_alias}"
        f"{f' (issue #{issue_number})' if issue_number is not None else ''}"
        f" context={event_context!r} by={emitter_alias or '?'}"
    )
    return {"status": "ok", "event_id": event["id"]}


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
    eviction = None
    if since:
        # Over-fetch by *3 so post-filter still has enough rows to fill
        # the limit. Eviction marker piggybacks on this call (#9331).
        events, eviction = event_stream.get_since_with_eviction(
            since, limit=limit * 3
        )
    else:
        events = event_stream.get_recent(limit * 3)

    # Apply filters
    if role:
        events = [e for e in events if e.get("role") == role]
    if event_type:
        types = set(event_type.split(","))
        events = [e for e in events if e.get("event_type") in types]

    # Apply limit after filtering. With `since`, the agent wants the
    # OLDEST events after the cursor (skim-then-advance, CONTEXT-8694
    # §2) — slicing `[-limit:]` would silently drop the gap between
    # cursor and (head − limit). Without `since`, keep newest-first for
    # callers that want recent activity.
    if since:
        events = events[:limit] if len(events) > limit else events
    else:
        events = events[-limit:] if len(events) > limit else events

    response = {"events": events, "total": len(event_stream)}
    if eviction is not None:
        # Eviction signal (#9331) — present only when the caller's
        # cursor predates the retained window. Agents log this and
        # advance to `oldest_id` instead of silently moving on.
        response["evicted"] = True
        response["oldest_id"] = eviction["oldest_id"]
        response["evicted_count_hint"] = eviction["evicted_count_hint"]
    return response


@app.get("/events/for/{role}")
async def get_events_for_role(
    role: str,
    limit: int = 50,
    since: str = None,
):
    """Get events targeted at a specific role (#7630 Phase 4).

    Returns events where payload.target_alias matches the given role,
    OR events with event_type in the role's reacts-to list.
    Marks returned events as dispatched in EventLifecycleManager.

    This is the primary endpoint for event-driven agents using Monitor tool.

    Field-name note: per AGENT-RUNTIME.md §8, the canonical wire-format
    field is ``target_alias`` (the per-agent alias from
    ``.squidsquad/config.md`` ``## Aliases``, NOT the role-class noun).
    The pre-#6274 legacy field name ``target_role`` was unified into
    ``target_alias`` in polish-session Iter 63 (#11331).
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

    # Fetch events from stream. Eviction marker piggybacks when `since`
    # is provided and the cursor predates the retained window (#9331).
    eviction = None
    if since:
        events, eviction = event_stream.get_since_with_eviction(
            since, limit=limit * 3
        )
    else:
        events = event_stream.get_recent(limit * 3)

    # Filter: events targeted at this role OR matching the role's reaction types
    filtered = []
    for e in events:
        target = e.get("payload", {}).get("target_alias", "")
        etype = e.get("event_type", "")
        if target == role:
            filtered.append(e)
        elif relevant_types and etype in relevant_types:
            filtered.append(e)

    # Same skim-then-advance rule as GET /events: oldest-first when the
    # caller advances a cursor, newest-first otherwise.
    if since:
        filtered = filtered[:limit] if len(filtered) > limit else filtered
    else:
        filtered = filtered[-limit:] if len(filtered) > limit else filtered

    # #9741: dispatch() call stripped — endpoint is a pure filtered-read
    # with no lifecycle side effects. The agent-side ack stub
    # (event_bus.ack) was also removed in #9813 since it had no live
    # producer after this. Cursor advance in event_poll.py is the
    # de-facto ack signal. Before this change, dispatching here was
    # accumulating in-flight entries that always timed out, producing
    # log spam and growing .event-state.json indefinitely.

    response = {"events": filtered, "total": len(filtered)}
    if eviction is not None:
        response["evicted"] = True
        response["oldest_id"] = eviction["oldest_id"]
        response["evicted_count_hint"] = eviction["evicted_count_hint"]
    return response


@app.get("/events/cursor/{role}")
async def get_events_cursor(role: str):
    """Return the current consumer cursor for ``role`` (#9873-A AC-3 / AC-4).

    Lock-free dict read per R2 D5: CPython ``dict.get()`` is atomic at the
    interpreter level. Acquiring ``EventLifecycleManager._lock`` here would
    block the asyncio event loop, defeating the H6 mitigation that wraps
    the write-side persist in ``asyncio.to_thread``.

    Returns ``{"cursor": null, "role": "<role>"}`` when no cursor exists for
    the role (first boot, or role has never sent ``ack-cursor``) — D7 locks
    null as the absent value. Otherwise returns the persisted cursor.

    Status is 200 always — no 404 for missing cursors. ``_validate_role``
    still raises 404 for genuinely unknown roles (consistent with the other
    role-scoped endpoints).
    """
    _validate_role(role)
    return {"cursor": event_lifecycle.get_cursor(role), "role": role}


@app.post("/events/{event_id}/complete")
async def complete_event(event_id: str, request: Request):
    """REMOVED (#11165 / #11092 Decision 2 — pull-only).

    The dispatch/ack lifecycle this endpoint drove was deleted: under
    pull-only the harness only nudges, and agents poll the forge + advance
    the cursor via ``ack-cursor`` (AGENT-RUNTIME §2/§7). Retained as a
    410 Gone shell so any stale caller fails loudly rather than silently.
    """
    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=410,
        content={
            "status": "gone",
            "detail": "POST /events/{id}/complete removed under pull-only "
                      "(#11165) — agents advance the cursor via ack-cursor.",
        },
    )


# GET /events/in-flight/{role} removed (#11165 / #11092 Decision 2): in-flight
# dispatch tracking no longer exists under pull-only, and no caller invoked
# the route (caller survey 2026-06-11).


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
    """Event lifecycle overview — stream size + persistence state (#7630 2-7).

    The ``in_flight`` field was dropped (#11165 / #11092 Decision 2): under
    pull-only there is no dispatch in-flight tracking.
    """
    return {
        "stream_size": len(event_stream),
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
    # #9242: disk write off the asyncio event loop.
    await asyncio.to_thread(state.save_state)

    _log(f"Stopped {role} (intent=stopping)")

    return {"role": role, "action": "stop", "message": "Stop requested"}


@app.post("/agents/{role}/restart")
async def restart_agent(role: str):
    """Restart agent. If idle, kill immediately and let auto-reboot fire (#8689).
    If mid-cycle, just set intent=restarting and let the agent exit cleanly at
    its next cycle boundary (#4966 graceful-restart behavior preserved)."""
    _validate_role(role)

    # #10538 (gap-fix): when auto-reboot is disabled there is NO respawn path,
    # so a "restart" degenerates into kill-with-no-recovery — the force-kill
    # safety net tears down a live, working agent that then stays dead. That is
    # strictly worse than the churn the hatch was meant to stop. Honor the
    # operator directive "no ability at all for the harness to reboot" by
    # refusing the restart outright. Operators wanting a true restart under this
    # mode must use explicit /stop then /start.
    if _NO_AUTO_REBOOT:
        _log(f"  {role}: restart refused — SQUIDSQUAD_HARNESS_NO_AUTO_REBOOT "
             f"active (no respawn possible; agent left running)")
        return {
            "role": role,
            "action": "restart",
            "success": False,
            "message": "Restart refused — no-auto-reboot active; agent left "
                       "running. Use /stop then /start for an explicit cycle.",
        }

    _log(f"Restarting {role}...")

    # #11640: resolve the clone path BEFORE mutating any state. An
    # unregistered / missing clone now raises rather than resolving to
    # REPO_ROOT — refuse the restart up front so we never set
    # intent=restarting (which would arm the auto-reboot loop to refuse
    # spawn anyway) for a role we can't safely place.
    try:
        clone_path = boot_remote._get_clone_path(role)
    except boot_remote.CloneResolutionError as e:
        _log(f"  {role}: restart refused — clone resolution failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"role": role, "action": "restart", "success": False,
                     "message": f"clone resolution failed — refusing to "
                                f"restart: {e}"},
        )
    clone_path_p = Path(clone_path)

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
    # #9242: disk write off the asyncio event loop.
    await asyncio.to_thread(state.save_state)

    # #4792: stop is now expressed via harness intent — no sentinel to clean.

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


def _teardown_and_exit(exit_code, delete_port_file):
    """Stop all running agents, optionally clean the port file, then exit the
    harness process with ``exit_code`` (#12825).

    Shared by ``/shutdown`` (exit 0, delete port file — the harness is gone) and
    ``/restart`` (exit ``HARNESS_RESTART_EXIT_CODE``, keep the port file — the
    supervised launcher relaunches on the same port and the new harness rewrites
    it at boot). Runs in a background daemon thread so the async event loop is
    never blocked by the agent-idle wait / sleeps.
    """
    roles = boot_remote._get_all_roles()

    running_roles = []
    for role in roles:
        # Use intent to check if already stopping (#4949)
        agent = state.get_agent(role)
        if agent and agent.intent == AgentState.INTENT_STOPPING:
            _log(f"  {role}: skip (already stopping)")
            continue
        # #11640: _needs_boot resolves the clone and now raises for an
        # unregistered / missing one. Such a role cannot be running in a
        # clone we refuse to resolve — skip it rather than crashing the
        # teardown thread.
        try:
            needs_boot, _, _ = boot_remote._needs_boot(role)
        except boot_remote.CloneResolutionError as e:
            _log(f"  {role}: skip (clone unresolved — {e})")
            continue
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
            # repeat call does not extend the 60s force-kill clock.
            agent = state.get_agent(role) or AgentState(role, clone_path)
            if agent.intent != AgentState.INTENT_STOPPING:
                agent.intent = AgentState.INTENT_STOPPING
                agent.intent_set_at = time.time()  # #4792 Phase 1
            state.set_agent(role, agent)
        # NOTE: this `state.save_state()` runs inside the sync teardown daemon
        # thread (see threading.Thread in the endpoints below), NOT on the
        # asyncio event loop, so it is intentionally NOT wrapped in
        # `asyncio.to_thread`.
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

    # #12825: only the permanent shutdown removes the port file. On restart the
    # supervised launcher relaunches immediately and the new harness rewrites
    # the port file at boot — deleting it would open a needless discovery gap.
    if delete_port_file:
        for attempt in range(3):
            try:
                if HARNESS_PORT_FILE.exists():
                    HARNESS_PORT_FILE.unlink()
                    _log("Port discovery file deleted.")
                break
            except OSError as e:
                _log(f"WARNING: Could not delete port file (attempt {attempt + 1}/3): {e}")
                time.sleep(0.5)

    _log(f"Harness exiting (code {exit_code}).")
    time.sleep(1)
    os._exit(exit_code)


@app.post("/shutdown", status_code=202)
async def shutdown():
    """Stop all agents, then exit harness (code 0 — permanent; not relaunched).

    Returns 202 Accepted immediately. Teardown runs in a background thread to
    avoid blocking the async event loop (time.sleep in async = blocked responses).
    """
    if not _begin_teardown():
        raise HTTPException(status_code=409, detail="Teardown already in progress.")
    _log("Shutdown requested — starting background shutdown...")
    threading.Thread(
        target=_teardown_and_exit, args=(0, True),
        daemon=True, name="shutdown",
    ).start()
    return {"status": "shutting_down", "message": "Shutdown initiated. Harness will exit shortly."}


@app.post("/restart", status_code=202)
async def restart():
    """Restart the harness (#12825): stop all agents cleanly, then exit with
    ``HARNESS_RESTART_EXIT_CODE`` so the supervised launcher relaunches it.

    Distinct from ``/shutdown`` (which exits 0 and is NOT relaunched). This is
    the agent-callable harness-restart trigger — the requesting agent's own
    session ends with the harness and respawns fresh under the relaunched one.
    Under the one-shot launcher (no wrapper) the harness simply exits and is not
    relaunched; the wrapper is what makes restart self-healing.
    """
    if not _begin_teardown():
        raise HTTPException(status_code=409, detail="Teardown already in progress.")
    _log(f"Restart requested — tearing down for relaunch (exit "
         f"{HARNESS_RESTART_EXIT_CODE})...")
    threading.Thread(
        target=_teardown_and_exit, args=(HARNESS_RESTART_EXIT_CODE, False),
        daemon=True, name="restart",
    ).start()
    return {"status": "restarting",
            "message": "Restart initiated. Harness will exit with the restart "
                       "code; the supervised launcher will relaunch it."}


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
        # #9415 D4: widen from os.urandom(4)→(8), 8→16 hex (64-bit). The
        # event_bus content-hash path was widened in lockstep so both ID
        # producers now emit the same width.
        "id": os.urandom(8).hex(),
        "event_type": event_type,
        "role": role,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": payload or {},
        "received_at": time.time(),
    }
    event.update(extra)
    event_lifecycle.append(event)
    _log_event(event)
    # #12495: return the emitted event so HTTP callers (e.g. POST /work/assign)
    # can report the generated event_id. Existing callers ignore the return.
    return event


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
                # #12906 (Phase 1 of #12895): the PR was merged on the
                # remote — the local clone must be put on main + pulled
                # BEFORE deploy-all, or compose regenerates every
                # CLAUDE.md from pre-merge (stale) source and pushes that
                # revert fleet-wide. If the clone can't be freshened,
                # abort the recompose so agents keep last-known-good
                # composed output until a later recompose succeeds.
                fresh_ok, fresh_detail = git_ops.ensure_main_and_pull("harness")
                if not fresh_ok:
                    _log(f"WARNING: aborting compose after PR #{pr_number} — "
                         f"could not freshen source ({fresh_detail}). Agents "
                         f"keep current CLAUDE.md until next recompose.")
                    _emit_event("compose-completed", "harness", payload={
                        "success": False,
                        "error": f"freshen-source-failed: {fresh_detail}",
                        "trigger_pr": str(pr_number),
                    })
                    return
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
    # #10538 (gap-fix): the no-auto-reboot hatch must also suppress the
    # compose-affected restart path. Otherwise a recompose silently flips
    # intent=restarting → the force-kill net tears the agent down with no
    # respawn. Same reasoning as restart_agent's refusal above.
    if _NO_AUTO_REBOOT:
        _log("[no-auto-reboot] compose-affected restart skipped per "
             "SQUIDSQUAD_HARNESS_NO_AUTO_REBOOT")
        return
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

    # #12912 (HARNESS-ARCH §7.6): _reboot_affected_agents is the deploy-signal
    # EMITTER. It does NOT recompose-and-restart directly any more. For each
    # affected alias it sets intent=DEPLOYING (intent-sequencing, AC9 — committed
    # BEFORE the agent can possibly respond, so the deploy-halt death is never
    # misread as a crash) and emits a deploy-signal. The agent halts at its next
    # between-task on-main boundary and emits ack-stop(result=deploy-halted),
    # whereupon the per-clone pull-first deploy sequence runs (§7.1 / S4).
    # Emitting only on actual post-compose alias drift (the git-diff scope above)
    # is what closes #12397 (no spurious restart on a no-op recompose).
    # NB: bootup_complete is deliberately left TRUE — unlike the restart paths,
    # the agent MUST still receive this deploy-signal off the event bus to halt
    # cooperatively; suppressing dispatch would strand the signal undelivered.
    _log(f"Compose after PR #{pr_number}: emitting deploy-signal to affected "
         f"agents: {', '.join(sorted(affected_roles))}")
    for role in sorted(affected_roles):
        agent = state.get_agent(role)
        # DS-12912 iter-3 Finding 1: only signal agents that are actually ALIVE.
        # A crash-looping / paused / dead agent still carries intent=RUNNING;
        # flipping it to DEPLOYING would lock it out of the crash-loop resume
        # path (which needs should_reboot, excluding DEPLOYING) — a permanent
        # wedge until harness restart. A non-running affected agent picks up the
        # new CLAUDE.md when it next recovers/boots (a residual drift re-triggers
        # a deploy-signal on the next boot drift-check).
        if (agent and agent.intent == AgentState.INTENT_RUNNING
                and agent.status == "running"):
            agent.intent = AgentState.INTENT_DEPLOYING
            agent.intent_set_at = time.time()
            state.set_agent(role, agent)
            state.save_state()  # commit intent BEFORE emit (sequencing)
            _emit_event("deploy-signal", "harness", payload={
                "target_alias": role,
                "event_type": "deploy-signal",
                "event_context": "deploy-signal",
            })


# ---------------------------------------------------------------------------
# #12912 (HARNESS-ARCH §7.1 / §7.6 / §11): per-clone pull-first deploy sequence
# ---------------------------------------------------------------------------

# Serializes per-clone deploys so concurrent deploy-halts never race a push to
# the shared origin/main ref (AC8 / design §3 decision 5). Each deploy-halt ack
# spawns a thread that acquires this lock, so the deploys run one clone at a time
# (deploy A → pull/compose/commit/push/restart A → then B …).
_deploy_lock = threading.Lock()

_DEPLOY_COMPOSED_FILES = ("CLAUDE.md", "SOUL.md", "CLAUDE.linked.md")
# Respawn-suppression window armed when a deploy-halt ack arrives (HARNESS-ARCH
# §7.3). Generous — covers ensure-main → pull → compose → commit → push. The
# deploy sequence respawns explicitly and clears it well before this elapses.
_DEPLOY_WINDOW_SECONDS = 300

# #13077: how long the deploy respawn waits for the deploy-halted agent's OWN
# claude process to be reaped by the OS AFTER the harness force-kills it (the
# agent cannot self-/quit, so the harness terminates it actively — see
# _respawn_agent_process). boot_agent's singleton guard refuses to spawn over a
# live process, so we confirm the killed PID is gone before booting its
# replacement. Kept SHORT because a force-kill is near-instant — this only
# covers OS reap latency. Still alive after this window means the force-kill
# itself failed (permission / un-killable) → abort fast rather than block the
# serialized _deploy_lock for long (DS-13032-B F3: a full fix moves the respawn
# outside _deploy_lock so the wait never blocks other clones' deploys — tracked
# follow-up).
_DEPLOY_RESPAWN_PID_WAIT_S = 10


def _await_pid_death(pid, timeout_s, poll_s=0.5):
    """Poll until ``pid`` is no longer alive, up to ``timeout_s`` (#13032).

    Returns True if the process died within the window, False if still alive at
    the deadline. Runs in the deploy daemon thread (off the asyncio loop), so a
    blocking sleep is fine. Uses plain liveness (``boot_remote._is_process_alive``):
    we are observing a KNOWN PID disappear, which is safe regardless of PID
    recycling — we never force-kill on this signal (an image-verified force-kill
    auto-recovery is a #12294-dependent follow-up)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not boot_remote._is_process_alive(pid):
            return True
        time.sleep(poll_s)
    return not boot_remote._is_process_alive(pid)


def _respawn_agent_process(role):
    """Explicitly respawn a deploy-halted agent's claude process (DS-12912
    Finding 2). The agent's old claude PID is typically still ALIVE — it halted
    on the deploy-signal but an LLM cannot self-/quit (#13077) — so we force-kill
    it and confirm death before booting. After a deploy its status is "deploying"
    — which is NOT in the health poller's is_dead set, so the poller will NEVER
    auto-respawn it. We therefore boot it directly and stamp fresh-spawn state,
    mirroring the auto-start path.

    Returns True iff the respawn succeeded — a fresh process was spawned OR the
    agent was already alive (boot_agent action="skip"); i.e. the agent is now
    alive/recovering. Returns False only when boot_agent raised or reported
    success=False (DS-12912 iter-3 Finding 4: the return feeds `respawn_ok` in
    the deploy-error event, whose useful meaning to the operator is "is the agent
    recovered" — not the narrower "was a brand-new PID spawned").

    On ANY non-spawn outcome — boot_agent raised, returned success=False, or
    returned a non-"spawn" action — the agent MUST NOT be left at
    status="deploying" (it would be permanently stuck: not is_dead, never
    auto-respawned — DS-12912 iter-2 Findings 1+2). We settle a failure to
    "error" (which IS in is_dead) with intent=RUNNING so it is honest and
    surfaced, and a success-without-spawn to "starting"."""
    agent = state.get_agent(role) or AgentState(role)

    # #13077: actively terminate the deploy-halted agent's OWN claude process
    # before booting its replacement. The #13032 code WAITED for a cooperative
    # self-exit ("the agent /quits itself per Case E"), but an LLM agent CANNOT
    # execute /quit — it can only stop emitting output (operator-confirmed,
    # inline 2026-06-21: "agent cannot kill itself, it doesnt work. so the
    # harness has to act"). The old process therefore never exits on its own, so
    # the passive wait always timed out to status=error and deploy-halt →
    # recompose → respawn never completed. The deploy path also gets NO help from
    # the 60s force-kill safety net (that net only fires on intent STOPPING /
    # RESTARTING; a deploy-halted agent sits at status="deploying"), so this is
    # the one respawn path that must force-kill the old process itself.
    #
    # Force-kill the old process tree (reaps the Monitor-spawned event_poll
    # sidecar too, #12363), then CONFIRM death before booting — boot_agent's
    # singleton guard refuses to spawn over a live PID, which would no-op the
    # respawn and strand the agent on the stale pre-recompose CLAUDE.md (the
    # original #13032 failure mode). _DEPLOY_RESPAWN_PID_WAIT_S now bounds the
    # post-kill OS-reap confirm (force-kill is near-instant), not a self-exit.
    old_pid = agent.claude_pid
    if old_pid and boot_remote._is_process_alive(old_pid):
        _log(f"{role}: deploy respawn — force-killing deploy-halted claude PID "
             f"{old_pid} (agent cannot self-/quit, #13077)")
        try:
            reboot_agent._kill_process(old_pid)
        except Exception as e:
            _log(f"{role}: deploy respawn force-kill of PID {old_pid} raised "
                 f"{type(e).__name__}: {e}")
        if not _await_pid_death(old_pid, _DEPLOY_RESPAWN_PID_WAIT_S):
            agent.status = "error"
            agent.intent = AgentState.INTENT_RUNNING
            agent.intent_set_at = None
            agent.reboot_blocked_until = None
            agent.bootup_complete = False
            state.set_agent(role, agent)
            state.save_state()
            _log(f"{role}: deploy respawn ABORTED — claude PID {old_pid} still "
                 f"alive {_DEPLOY_RESPAWN_PID_WAIT_S}s after force-kill — "
                 f"left status=error")
            # The deploy-error emit is owned by the caller (DS-13032-B F1:
            # avoids a double-emit when called from _deploy_recover_and_respawn,
            # which emits its own stage failure).
            return False

    agent.reboot_blocked_until = None
    agent.intent = AgentState.INTENT_RUNNING
    agent.intent_set_at = None
    agent.bootup_complete = False
    try:
        result = boot_remote.boot_agent(role)
    except Exception as e:
        agent.status = "error"          # is_dead → honest, not a "deploying" wedge
        agent.claude_pid = None
        state.set_agent(role, agent)
        state.save_state()
        _log(f"{role}: deploy respawn boot_agent raised "
             f"{type(e).__name__}: {e} — left status=error")
        return False
    spawned = bool(result.get("success") and result.get("action") == "spawn")
    if spawned:
        agent.status = "starting"
        agent.boot_time = time.time()
        agent.last_spawn_at = time.time()
        agent.last_session_end = None
        agent.last_dispatch_at = None
        agent.reset_session_telemetry()  # #13113
        agent.terminal_pid = result.get("terminal_pid")
        state.set_agent(role, agent)
        state.save_state()
        _log(f"{role}: deploy respawn — spawn OK")
        return True

    # #13032: success-without-spawn (action="skip" — boot_agent found the agent
    # STILL ALIVE) is unexpected here: we already waited for the old PID to die,
    # so a skip means a stale .claude-pid or a race produced a live process we
    # did NOT just spawn. Do NOT silently settle it to running on the old
    # instructions (the original #13032 no-op) — fail honest + surface it.
    agent.status = "error"
    agent.claude_pid = None
    state.set_agent(role, agent)
    state.save_state()
    detail = (f"boot_agent returned action={result.get('action')!r} "
              f"success={result.get('success')!r} after PID-death wait: "
              f"{result.get('message')}")
    _log(f"{role}: deploy respawn FAILED — {detail}")
    # deploy-error emit owned by the caller (DS-13032-B F1).
    return False


def _emit_boot_deploy_signals():
    """#12912 S5 (HARNESS-ARCH §10 step 1b): on boot drift, emit a deploy-signal
    to each running agent so it recomposes pull-first — the harness never composes
    deploy-all locally at boot.

    Unlike the post-merge emitter (_reboot_affected_agents), intent is NOT pre-set
    to DEPLOYING here: a just-spawned agent's first health poll resets a DEPLOYING
    intent back to RUNNING on pid_changed, so pre-setting at boot is futile. The
    ack-stop(result=deploy-halted) handler sets DEPLOYING when the agent actually
    halts — before its PID dies — which is the intent-sequencing guarantee on the
    boot path. A no-op deploy (committed output already current — the common case
    at boot) is a clean success, so emitting to every alias on drift is safe; at
    boot the affected set is unknown without composing, and composing is exactly
    what we are retiring. Called once per harness boot (from _deferred_init), so
    post-deploy respawns never re-trigger it."""
    if _NO_AUTO_REBOOT:
        _log("[no-auto-reboot] boot deploy-signal emit skipped")
        return
    signaled = []
    for role in boot_remote._get_all_roles():
        agent = state.get_agent(role)
        if agent and agent.intent == AgentState.INTENT_RUNNING:
            _emit_event("deploy-signal", "harness", payload={
                "target_alias": role,
                "event_type": "deploy-signal",
                "event_context": "deploy-signal",
            })
            signaled.append(role)
    if signaled:
        _log(f"Boot drift: emitted deploy-signal to {', '.join(signaled)} "
             f"(pull-first per-clone deploy; no local boot compose)")


def _git_in_clone(clone_path, args, timeout=120):
    """Run a git command inside a specific agent clone (the harness operating on
    another clone is new machinery — design §0). Returns the CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, cwd=str(clone_path), timeout=timeout,
    )


def _bump_compose_checksum(clone_path):
    """Advance last_compose_checksum to the just-deployed source state (§7.6).
    Best-effort: a checksum-compute failure must not fail an otherwise-good
    deploy (the worst case is one redundant future deploy-signal)."""
    try:
        import compose_freshness as _cf
        checksum = _cf.compute_compose_checksum(clone_path)
        state.set_last_compose_checksum(checksum)
        state.save_state()
    except Exception as e:
        _log(f"deploy: checksum update skipped ({type(e).__name__}: {e})")


def _respawn_after_deploy(role):
    """Successful deploy: respawn the halted agent against the freshly-committed
    CLAUDE.md. The old PID is typically still alive (halted but not exited — an
    LLM cannot self-/quit, #13077) and status is "deploying" (not in is_dead), so
    the health poller will not do it — respawn explicitly via
    _respawn_agent_process, which force-kills the old process and boots the
    replacement (DS-12912 Finding 2).

    #13032 (DS-13032-B F1/F2): this success path owns the deploy-error emit for a
    respawn failure. Previously a respawn that no-op'd here was SILENT (the agent
    kept running stale instructions); now any respawn failure — agent didn't exit,
    boot_agent raised, or boot no-op'd — surfaces a single deploy-error to pm."""
    _log(f"{role}: deploy complete — respawning on fresh CLAUDE.md")
    if not _respawn_agent_process(role):
        _emit_event("deploy-error", "pm", payload={
            "target_alias": "pm",
            "event_context": "deploy-error",
            "failed_role": role,
            "stage": "respawn",
            "detail": (f"{role}: deploy succeeded but the respawn failed (agent "
                       f"did not exit on the deploy-halt /quit, boot raised, or "
                       f"boot no-op'd) — see harness log; the agent may still be "
                       f"on the stale pre-recompose CLAUDE.md"),
            "respawn_ok": False,
        })


def _deploy_recover_and_respawn(role, stage, detail):
    """§11 failure recovery: respawn the agent on its EXISTING committed
    CLAUDE.md, file a deploy-error event to pm, and do NOT advance the compose
    checksum (drift stays detectable and re-triggers a future deploy-signal).
    The respawn is explicit for the same reason as the success path (Finding 2)."""
    _log(f"{role}: deploy FAILED at {stage}: {detail} — respawning on existing "
         f"CLAUDE.md, filing deploy-error to pm (checksum NOT advanced)")
    respawn_ok = _respawn_agent_process(role)
    # DS-12912 iter-2 Finding 3: report the real respawn outcome so the operator
    # is not misdirected by a "respawned" claim when the respawn itself failed.
    _emit_event("deploy-error", "pm", payload={
        "target_alias": "pm",
        "event_context": "deploy-error",
        "failed_role": role,
        "stage": stage,
        "detail": str(detail)[:500],
        "respawn_ok": respawn_ok,
    })


def _stage_composed_outputs(clone_path, alias):
    """Stage ONLY the alias's composed outputs (CLAUDE.md / SOUL.md /
    CLAUDE.linked.md) — never the whole .squidsquad/<alias>/ dir, which also
    holds working-state and other per-cycle churn. Returns True if anything was
    staged. NB: per-alias `compose.py deploy` does NOT write .claude/settings.json
    (AC11 / #12519) — that stays an installer-managed artifact, out of scope."""
    staged_any = False
    for fn in _DEPLOY_COMPOSED_FILES:
        rel = f".squidsquad/{alias}/{fn}"
        if (clone_path / rel).exists():
            add = _git_in_clone(clone_path, ["add", "--", rel])
            if add.returncode == 0:
                staged_any = True
    return staged_any


def _run_deploy_sequence(role, deploy_signal_event_id=None):
    """Pull-first per-clone deploy on a deploy-halted agent (HARNESS-ARCH §7.1).

    ensure-main → pull → compose.py deploy <alias> → commit → push → respawn,
    serialized across clones by _deploy_lock (AC8). Failure at any step routes to
    §11 recovery (respawn on existing CLAUDE.md, deploy-error to pm, checksum
    unchanged). Runs in a daemon thread, off the asyncio loop.
    """
    with _deploy_lock:
        # DS-12912 Finding 1 / AC4 (infinite-loop guard): the agent did NOT
        # ack-cursor the deploy-signal — the harness owns advancing past it.
        # Do it up front so the cursor moves past the signal regardless of
        # whether the deploy succeeds or hits §11 recovery; otherwise the
        # respawned agent's boot drain re-fetches the deploy-signal, re-halts,
        # and loops (deploy → respawn → re-halt → deploy …). A future drift
        # still re-triggers via a NEW deploy-signal (checksum is only advanced
        # on success), so advancing the cursor here loses nothing.
        if deploy_signal_event_id:
            # DS-12912 iter-2 Finding 4: a silent advance failure reintroduces the
            # re-halt loop (the respawned agent re-fetches the signal). The normal
            # return values are all safe — "advanced" (moved past it), "regression"
            # (cursor already past it), "evicted" (signal no longer in the deque,
            # so unreachable anyway). Only an exception is concerning; retry once,
            # then log loudly so the loop risk is visible rather than silent.
            for _attempt in range(2):
                try:
                    outcome = event_lifecycle.advance_cursor(
                        role, deploy_signal_event_id)
                    _log(f"{role}: advanced cursor past deploy-signal "
                         f"{deploy_signal_event_id} ({outcome})")
                    break
                except Exception as e:
                    if _attempt == 1:
                        _log(f"{role}: WARNING deploy-signal cursor advance failed "
                             f"after retry ({type(e).__name__}: {e}) — respawned "
                             f"agent may re-halt on the stale signal")
                    else:
                        _log(f"{role}: deploy-signal cursor advance raised "
                             f"{type(e).__name__}: {e} — retrying once")
        try:
            clone_path = Path(boot_remote._get_clone_path(role))
        except Exception as e:
            _deploy_recover_and_respawn(role, "clone-resolve", e)
            return
        import config as _cfg
        alias = _cfg.get_alias(role) or role
        scripts = clone_path / "references" / "scripts"

        try:
            # 1. ensure-main + MERGE pull (never rebase). A prior deploy whose
            #    push was rejected leaves this clone with an unpushed compose
            #    commit; if origin/main has since advanced, the branch is
            #    DIVERGED — `git pull --ff-only` would FATAL on every such deploy
            #    (#13158, recurring `deploy-error stage=pull`). `--no-rebase`
            #    merges the divergence instead (consistent with the team's
            #    always-merge-never-rebase rule + the #12526 launcher fix);
            #    `--no-edit` keeps it non-interactive. A genuine merge CONFLICT
            #    still fails the pull → §11 recovery (the rare case the old
            #    --ff-only conflated with benign divergence).
            co = _git_in_clone(clone_path, ["checkout", "main"])
            if co.returncode != 0:
                _deploy_recover_and_respawn(role, "checkout-main", co.stderr.strip()[:300])
                return
            pull = _git_in_clone(clone_path, ["pull", "--no-rebase", "--no-edit", "origin", "main"])
            if pull.returncode != 0:
                _deploy_recover_and_respawn(role, "pull", pull.stderr.strip()[:300])
                return

            # 2. compose the alias using the CLONE's own compose.py (so its repo
            #    root is the clone). Bad source / parse error → §11.
            comp = subprocess.run(
                [sys.executable, str(scripts / "compose.py"), "deploy", alias],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                check=False, cwd=str(clone_path), timeout=300,
            )
            if comp.returncode != 0:
                _deploy_recover_and_respawn(role, "compose", comp.stderr.strip()[:300])
                return

            # 3. commit + push the composed output. A no-op recompose (output
            #    already current) is a clean, idempotent success — skip to respawn.
            if not _stage_composed_outputs(clone_path, alias):
                _bump_compose_checksum(clone_path)
                _respawn_after_deploy(role)
                return
            commit = _git_in_clone(
                clone_path,
                ["commit", "-m",
                 f"deploy: recompose {alias} CLAUDE.md (#12912 deploy-signal)"],
            )
            if commit.returncode != 0:
                _deploy_recover_and_respawn(role, "commit", commit.stderr.strip()[:300])
                return
            push = _git_in_clone(clone_path, ["push", "origin", "main"])
            if push.returncode != 0:
                # DS-12912 iter-3 Finding 3: no retry loop. A rejected push means
                # origin/main advanced (a concurrent clone pushed) and this clone
                # now holds an unpushed local compose commit (diverged). We do NOT
                # retry-in-place; the sequential _deploy_lock makes genuine
                # concurrent pushes rare, and §11 recovery handles it cleanly:
                # respawn on the existing CLAUDE.md + file deploy-error; the
                # unadvanced checksum re-triggers a fresh deploy-signal whose
                # merge-pull (#13158, step 1) reconciles the divergence next pass.
                _deploy_recover_and_respawn(role, "push", push.stderr.strip()[:300])
                return

            # 4. success — advance the checksum, then respawn on fresh output.
            _bump_compose_checksum(clone_path)
            _respawn_after_deploy(role)
        except subprocess.TimeoutExpired as e:
            _deploy_recover_and_respawn(role, "timeout", e)
        except Exception as e:
            _deploy_recover_and_respawn(role, "unexpected", e)


# ---------------------------------------------------------------------------
# Port management
# ---------------------------------------------------------------------------

def find_free_port(default: int = DEFAULT_PORT) -> int:
    """Find an available port, preferring the default.

    When ``default`` is 0 the OS assigns an ephemeral port; this returns the
    actually-bound port number (not 0) so a caller that opts into ephemeral
    binding via ``--port 0`` (the integration test harness) gets the real
    number to advertise in its ``.harness-port`` file (#12820).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", default))
        actual = s.getsockname()[1]
        s.close()
        return actual
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


def _probe_harness_status(port: int, timeout: float = 2.0) -> bool:
    """Return True iff a live SquidSquad harness answers ``GET /status`` on ``port``.

    The production singleton path (#12820) uses this to tell apart:
    - a LIVE harness already holding the canonical port → refuse to start, so
      a second harness can never bind an ephemeral port and poison every
      clone's ``.harness-port`` file (the root cause of #12820); and
    - a stale socket / TIME_WAIT slot left by a just-exited harness mid-restart
      → safe to reclaim the canonical port (uvicorn's ``SO_REUSEADDR`` bind
      rebinds a TIME_WAIT slot cleanly).

    A ``200`` from some unrelated server that lacks the harness-shaped
    ``harness`` key reads as "not a harness" (False) — better to try to claim
    our reserved port than refuse to boot for an unrelated squatter.
    """
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/status", timeout=timeout
        ) as resp:
            if resp.status != 200:
                return False
            body = json.loads(resp.read().decode("utf-8"))
            return isinstance(body, dict) and "harness" in body
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _resolve_listen_port(explicit_port) -> int:
    """Resolve the port the harness listens on, or refuse to start (#12820).

    ``explicit_port`` is ``args.port`` — ``None`` when no ``--port`` was passed.

    - **Explicit** (including ``--port 0``): legacy ``find_free_port`` behavior,
      ephemeral fallback allowed. This is the integration test harness path
      (``real_harness`` passes ``--port 0``); it self-writes its port into an
      isolated tmp ``.harness-port`` and never touches real clones.
    - **None** (production singleton): probe the canonical port. A live harness
      there → ``SystemExit(1)`` (refuse — never bind an ephemeral port and
      poison clone ``.harness-port`` files). Otherwise claim the canonical port;
      uvicorn's ``SO_REUSEADDR`` bind reclaims a TIME_WAIT slot left by a
      just-exited harness during a supervised restart.

    Returns the resolved port. Raises ``SystemExit(1)`` on refuse-to-start.
    """
    if explicit_port is not None:
        actual = find_free_port(explicit_port)
        if actual != explicit_port and explicit_port != 0:
            print(f"Port {explicit_port} in use — using {actual}")
        return actual

    desired = _read_config_port()
    if _probe_harness_status(desired):
        print(
            f"A SquidSquad harness is already running and responding on "
            f"127.0.0.1:{desired}. Refusing to start a second instance — a "
            f"second harness would bind an ephemeral port and poison every "
            f"clone's .harness-port file, forcing the team into polling "
            f"fallback (#12820). Use the running harness, or stop it first."
        )
        sys.exit(1)
    # Free, or a stale/TIME_WAIT slot from a just-exited harness (restart):
    # claim the canonical port. uvicorn's bind sets SO_REUSEADDR so a
    # TIME_WAIT slot rebinds cleanly. A genuinely live *non-harness* squatter
    # on the reserved canonical port is an operator configuration error: on
    # Unix uvicorn's bind then fails loudly (EADDRINUSE — SO_REUSEADDR only
    # bypasses TIME_WAIT, not a live listener); on Windows SO_REUSEADDR may
    # permit a duplicate bind, but the /status probe above already rules out a
    # live *harness* peer, which is the case that actually matters for #12820.
    return desired


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

# #12342: sentinel distinguishing "issue never seen" from "issue last seen at
# status=None" in ExternalActivityDetector._emitted_issues.get(...).
_UNSEEN = object()


class ExternalActivityDetector:
    """Polls GitHub for external changes and emits assigned-to events (#7630 2-4).

    Runs as a daemon thread. Detects new/updated issues and routes work to the
    right alias by status (#12342):

    - ``status:approved`` / ``status:open`` → the issue's ``role:*`` worker alias
    - ``status:pending-test``               → the install's **verifier** alias
    - ``status:pending-ship``               → the install's **dm** alias

    Without the pending-test/pending-ship routes (the pre-#12342 behavior),
    event-mode QA and DM starved: the EAD only ever emitted for worker statuses,
    so verification/delivery work produced no wake event.

    Dedup records ONE entry per issue — its last observed status — and emits
    only when the current status differs from that record (#12342). Keying by
    issue number alone (pre-#12342) meant an issue emitted at most one
    assigned-to in its whole lifecycle; a naive ``(issue_num, status)`` set
    instead permanently suppressed re-entry to a status, starving QA on every
    re-verification after a reject (DS-REVIEW-12342 Finding 1). Recording the
    intermediate (unmapped) ``in-progress`` lets a back-transition
    ``pending-test -> in-progress -> pending-test`` re-emit correctly.
    """

    # #6274: qa→verifier per D5. AGENT_ROLES is currently unused (issue
    # filtering is done via role-labels on the issue itself, not against
    # this set), but the constant documents the canonical mandatory team.
    # Flipping in lockstep with config.py:486/591 and cycle_pre.py:1037.
    AGENT_ROLES = {"skill", "pm", "verifier", "dm"}

    # #12342: status → routing target. ("label", None) routes to the issue's
    # own role:* worker alias; ("role_class", <class>) routes to the install's
    # alias for that role-class (resolved via config.parse_aliases_registry).
    # Statuses absent from this map (in-progress, planned, pending, planning)
    # intentionally emit nothing — the owning agent is already on it or a human
    # gate applies. shipped is closed, so the --state open query never sees it.
    _STATUS_ROUTING = {
        "status:open": ("label", None),
        "status:approved": ("label", None),
        "status:pending-test": ("role_class", "verifier"),
        "status:pending-ship": ("role_class", "dm"),
        # #12800: human-needed handoffs route to the install's `human`-class
        # alias (AGENT-RUNTIME §8.3; was pm). Resolved via
        # config.parse_aliases_registry; falls back to the bare class name
        # `human` if no human alias is registered. An assigned-to <human>
        # event is appended for forge/audit correctness — the human is not on
        # the event bus and reads it on the forge (or inline), per §3.1.
        "status:pending-human-review": ("role_class", "human"),
        "status:pending-human-setup": ("role_class", "human"),
    }

    # #12442: terminal HANDOFF statuses route to a *different* agent than the
    # one who built the item (verifier / dm), so delivery depends ENTIRELY on
    # the single assigned-to nudge reaching that (often event-mode) agent. A
    # worker status (approved/open) routes to a worker presumed already looping
    # on its own queue; a handoff status has no such backstop. If the one nudge
    # is lost — dm busy mid-cycle, a cursor gap, ack-without-action, or the item
    # was already at this status when the detector (re)started so its updatedAt
    # is in the past and the time filter skips it forever — the item starves
    # indefinitely (observed: #12418 sat pending-ship 48 min until PM hand-
    # injected a wake event). So for these two statuses ONLY we RE-EMIT the
    # assigned-to nudge on a bounded cadence, bypassing the updatedAt time
    # filter, until the status changes (which removes the item from the
    # open+pending query and ends the re-emit). Idempotent: assigned-to is a
    # wake nudge — a redundant one just makes the agent re-check its queue.
    _HANDOFF_REEMIT_SECONDS = 600  # re-nudge stuck handoff work every 10 min

    def __init__(self, poll_interval: int = 60):
        self._poll_interval = poll_interval
        self._running = False
        self._thread = None
        self._last_check_epoch = 0.0  # epoch seconds — avoids ISO string comparison
        # #12342: one entry per issue — issue_num → the LAST status this issue
        # was observed at (the status we emitted for, or an unmapped status we
        # recorded as we passed through it). We emit only when the observed
        # status differs from the recorded one, so:
        #   - a comment that bumps updatedAt without changing status → no
        #     re-emit (status unchanged), and
        #   - a back-transition pending-test → in-progress → pending-test
        #     DOES re-emit, because the intermediate in-progress is recorded
        #     and the second pending-test differs from it.
        # The earlier (issue_num, status) tuple-set permanently suppressed
        # re-entry to a status (DS-REVIEW-12342 Finding 1: QA starved on every
        # re-verification after a reject). One entry/issue also keeps the 500
        # eviction cap at 500 *issues* rather than ~125 (Finding 5).
        self._emitted_issues: dict = {}
        # #12442: issue_num → epoch of the LAST assigned-to we emitted for this
        # issue while it sat at a terminal handoff status (pending-test/
        # pending-ship). Drives the re-emit cadence: re-nudge only once the
        # interval since the last emit has elapsed. Separate from
        # _emitted_issues (which records *status* for change-detection) because
        # re-emit is time-gated, not change-gated. Guarded by _emitted_lock.
        self._handoff_emit_at: dict = {}
        # Lock guards _emitted_issues against concurrent mutation. The
        # detector's own poller thread is the only writer now that #8914
        # removed TrackerHandoffDispatcher, but the lock stays — the
        # compound eviction (next(iter) + del) still needs serialization
        # if another thread is ever added.
        self._emitted_lock = threading.Lock()

    def is_emitted(self, issue_num, status=None):
        """True iff the LAST recorded status for ``issue_num`` equals
        ``status`` (#12342) — i.e. we already emitted/observed this exact
        status and nothing has changed since. An unseen issue is never
        'emitted'."""
        with self._emitted_lock:
            return self._emitted_issues.get(issue_num, _UNSEEN) == status

    def mark_emitted(self, issue_num, status=None):
        """Record ``status`` as the last observed status for ``issue_num``
        (#8694 thread-safe + bounded eviction; #12342 one entry/issue)."""
        with self._emitted_lock:
            # Refresh recency: delete+reinsert so the FIFO eviction order
            # tracks last-touch, not first-insert (an issue actively cycling
            # statuses should not be evicted ahead of a stale one).
            self._emitted_issues.pop(issue_num, None)
            self._emitted_issues[issue_num] = status
            while len(self._emitted_issues) > 500:
                oldest = next(iter(self._emitted_issues))
                del self._emitted_issues[oldest]

    def _handoff_due(self, issue_num, now):
        """True iff a handoff re-emit for ``issue_num`` is due (#12442) — i.e.
        we have never emitted a handoff nudge for it, or the last one was at
        least ``_HANDOFF_REEMIT_SECONDS`` ago. The fresh-transition path emits
        immediately and seeds the timer; this only governs the *re*-emit."""
        with self._emitted_lock:
            last = self._handoff_emit_at.get(issue_num)
        return last is None or (now - last) >= self._HANDOFF_REEMIT_SECONDS

    def _mark_handoff_emit(self, issue_num, now):
        """Record ``now`` as the last handoff-emit time for ``issue_num``
        (#12442; bounded + recency-ordered, mirroring mark_emitted)."""
        with self._emitted_lock:
            self._handoff_emit_at.pop(issue_num, None)
            self._handoff_emit_at[issue_num] = now
            while len(self._handoff_emit_at) > 500:
                oldest = next(iter(self._handoff_emit_at))
                del self._handoff_emit_at[oldest]

    @staticmethod
    def _alias_for_role_class(role_class):
        """Resolve the install's alias for a role-class (#12342).

        Reads the ``## Aliases`` registry via config.parse_aliases_registry()
        ({alias: (role_class, l3_domain)}) and returns the first alias whose
        role-class matches. Singleton installs have exactly one verifier and
        one dm. Falls back to the role-class name itself (a valid bare alias in
        singleton installs: verifier→verifier, dm→dm) if config is unreadable.
        """
        try:
            import config as _cfg
            registry = _cfg.parse_aliases_registry()
            for alias, rc_tuple in registry.items():
                rc = rc_tuple[0] if isinstance(rc_tuple, (list, tuple)) else rc_tuple
                if rc == role_class:
                    return alias
        except Exception:
            pass
        return role_class

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

    # #12342: `_is_agent_update` removed. Its implementation
    # (`title.startswith(("ISSUE:","TASK:"))`) matched EVERY SquidSquad issue
    # — every issue title carries one of those prefixes — so it skipped all
    # issues and the EAD emitted nothing. Loop-prevention against
    # comment-bumped updatedAt is now handled correctly by the per-(issue,
    # status) dedup in `_check_for_changes`.

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

        # #12800: the #12442 re-emit cadence is a backstop for handoff work
        # dispatched to an *agent* on the event bus (verifier/dm) that may be
        # busy. Non-agent role-classes (`human`) are not on the bus and never
        # consume the nudge, so they must emit once (forge/audit) but never
        # re-emit. Resolve the agent role-class set once per poll.
        try:
            import config as _cfg_handoff
            _agent_role_classes = _cfg_handoff.AGENT_ROLE_CLASSES
        except Exception:
            _agent_role_classes = frozenset({"pm", "worker", "verifier", "dm"})

        for issue in issues:
            issue_num = issue.get("number", 0)
            labels = {l.get("name", "") for l in issue.get("labels", [])}

            # The issue's current status label (exactly one expected).
            status = next((l for l in labels if l.startswith("status:")), None)
            if status is None:
                continue

            # Status → routing target (#12342). Unmapped statuses (in-progress,
            # planned, pending, planning) emit nothing.
            routing = self._STATUS_ROUTING.get(status)
            # is_handoff: routes to a *different* agent than the builder
            # (verifier/dm). These get the #12442 re-emit cadence. #12800:
            # non-agent role-classes (`human`) route via role_class but are NOT
            # on the bus — exclude them so they emit once and never re-nudge.
            is_handoff = (
                bool(routing)
                and routing[0] == "role_class"
                and routing[1] in _agent_role_classes
            )

            # Change-detection (#12342): has the status changed since we last
            # recorded it for this issue? A different status will re-record
            # below, so a back-transition (pending-test → in-progress →
            # pending-test) correctly re-emits — see DS-REVIEW-12342 Finding 1.
            fresh_status = not self.is_emitted(issue_num, status)

            # Time filter (#12342): a status transition bumps updatedAt, so a
            # freshly-transitioned issue passes; a bare comment that does NOT
            # change status is absorbed by the dedup. NOTE (#12442): the
            # re-emit path below deliberately does NOT consult this — a stuck
            # handoff item's updatedAt is in the past, which is exactly why the
            # single-emit design starved it.
            updated_epoch = self._parse_iso_epoch(issue.get("updatedAt", ""))
            updated_recently = updated_epoch > self._last_check_epoch

            # A fresh transition into a routed status — the fast path.
            fresh_transition = routing is not None and fresh_status and updated_recently
            # A re-nudge for handoff work that is STILL unclaimed (#12442):
            # the status has not changed (not a fresh transition) but the
            # re-emit interval has elapsed. Bypasses the time filter on purpose.
            reemit_due = (
                is_handoff
                and not fresh_transition
                and self._handoff_due(issue_num, check_time)
            )

            if not (fresh_transition or reemit_due):
                # No emit this poll. Still record a freshly-observed status
                # change (passing the time filter) so a later re-entry to a
                # routed status differs from it and re-emits (DS-12342 F1) —
                # this covers unmapped statuses (in-progress, planned, ...).
                # Comment-bumped re-observations of an already-routed status
                # never reach this clause: they have fresh_status=False (the
                # status was recorded on the prior emit), which also keeps them
                # out of fresh_transition — the dedup, not this clause, silences
                # them.
                if fresh_status and updated_recently:
                    self.mark_emitted(issue_num, status)
                continue

            kind, role_class = routing
            if kind == "label":
                # Worker statuses (approved/open) route to the issue's own
                # role:* alias. In single-instance teams the value following
                # `role:` is the alias; in multi-instance teams the `role:*`
                # label carries the routed alias (set by PM at planned→approved;
                # the harness does NOT rewrite role:* — the "universal router"
                # /work/assign label-rewrite design was never built, see #12495).
                # Either way the extracted string IS the alias. NOTE (#12342 /
                # DS Finding 3): a multi-role issue wakes only the alphabetically
                # first role:* alias — single-worker-per-issue is the assumed
                # model; multi-role fan-out is out of scope and pre-dates this
                # change.
                role_labels = sorted(l for l in labels if l.startswith("role:"))
                if not role_labels:
                    continue
                target_alias = role_labels[0].replace("role:", "")
            else:
                # pending-test → verifier, pending-ship → dm (#12342). These do
                # NOT route to the issue's role:* label (that is the worker who
                # built it); they route to the install's verifier/dm alias.
                target_alias = self._alias_for_role_class(role_class)
                if not target_alias:
                    continue

            # #12271 slice d — stamp the dispatch reference for progress-based
            # liveness BEFORE emitting (DS-c1 F3: an emit failure must not leave
            # the dispatch invisible to liveness; check_time is a past epoch, so
            # the agent's later activity heartbeat still reads as >= it).
            # An assigned-to is work dispatched to target_alias; progress_
            # liveness() measures heartbeat silence relative to this.
            #
            # ADVANCE ONLY WHEN THE AGENT HAS CAUGHT UP on prior dispatched work
            # (DS-c1 F1): a handoff re-emit (#12442) of STILL-UNACTED work must
            # NOT reset the grace — _HANDOFF_REEMIT_SECONDS (600) == ACTIVITY_
            # GRACE_SECONDS (600), so resetting on every re-nudge would keep a
            # wedged verifier/dm perpetually in "dispatch-grace" and it could
            # never read "wedged". Only stamp when there's no prior dispatch, or
            # the agent acted since it (last_activity_at >= last_dispatch_at);
            # an unacted re-nudge leaves the original dispatch clock aging out.
            # Guard on RUNNING intent (DS-c1 F4): never stamp a stopped/stopping
            # agent. OBSERVATIONAL — does not yet drive the reboot decision.
            with state._lock:
                _disp_agent = state.agents.get(target_alias)
                if (_disp_agent is not None
                        and _disp_agent.should_advance_dispatch()):
                    _disp_agent.last_dispatch_at = check_time
            # Emit assigned-to event
            _emit_event("assigned-to", "harness", payload={
                "issue_number": str(issue_num),
                "title": issue.get("title", ""),
                "target_alias": target_alias,
                "event_context": f"Issue #{issue_num} {status.replace('status:', '')}",
            })
            self.mark_emitted(issue_num, status)
            # #12442: seed/refresh the re-emit timer so a stuck handoff item is
            # re-nudged only after _HANDOFF_REEMIT_SECONDS, not every poll.
            if is_handoff:
                self._mark_handoff_emit(issue_num, check_time)

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

def _build_uvicorn_config(app_, host, port, log_level="warning"):
    """Build the harness's uvicorn Config (#11587).

    ``loop="none"`` is load-bearing on Windows. uvicorn's default
    ``loop="auto"`` resolves (no uvloop on Windows) to
    ``uvicorn.loops.asyncio.asyncio_loop_factory``, which HARD-CODES
    ``asyncio.ProactorEventLoop`` on win32 — it bypasses the process
    event-loop policy entirely. So the ``WindowsSelectorEventLoopPolicy`` set
    in ``main()`` (#9562) never reaches the server loop that actually runs in
    the uvicorn daemon thread, and the ProactorEventLoop ConnectionResetError
    (WinError 10054) recurs (#11587).

    ``loop="none"`` makes uvicorn pass ``loop_factory=None`` to ``asyncio.run``,
    which creates the loop via ``asyncio.new_event_loop()`` — and THAT respects
    the policy, yielding a SelectorEventLoop. Verified against uvicorn 0.41.0
    (``Config(loop="none").get_loop_factory() is None``). Cross-platform safe:
    on Linux the policy default is already SelectorEventLoop, so ``loop="none"``
    changes nothing there.
    """
    return uvicorn.Config(
        app_,
        host=host,
        port=port,
        log_level=log_level,
        loop="none",
    )


def main():
    # On Windows, the default ProactorEventLoop's cleanup path
    # (_ProactorBasePipeTransport._call_connection_lost) does not handle
    # ConnectionResetError gracefully — when a client (uvicorn keepalive,
    # curl probe, agent poll) resets the connection, the loop tries to
    # shutdown the socket, hits WinError 10054, and raises uncaught,
    # wedging the HTTP layer (#9562). SelectorEventLoop has no such bug.
    # Harness uses sync subprocess.run/Popen everywhere (no
    # asyncio.create_subprocess_exec), so the Selector trade-off is null.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import argparse

    parser = argparse.ArgumentParser(description="SquidSquad Harness — agent lifecycle manager")
    parser.add_argument("--port", type=int, default=None, help=f"Listen port (default: {DEFAULT_PORT})")
    parser.add_argument(
        "--no-auto-start",
        action="store_true",
        help=(
            "Skip the deferred-init auto-start of all agents (#9242). "
            "Boot harness in a clean state with HTTP server up but no "
            "agents spawned. Use `POST /agents/{role}/start` (or "
            "`squidsquad start <role>`) to start agents manually. "
            "Useful for isolating the auto-start path from HTTP wedges "
            "during diagnosis."
        ),
    )
    parser.add_argument(
        "--no-auto-reboot",
        action="store_true",
        help=(
            "Do not auto-respawn agents on observed death (#10538). The "
            "health poller still detects death and updates state, but "
            "`boot_agent(role)` is NOT invoked. Use when the operator "
            "wants manual control over context-pressure restarts or "
            "needs to coordinate already-running agents during a harness "
            "restart (three-claude-populations problem, HARNESS-ARCH §14). "
            "Honors `SQUIDSQUAD_HARNESS_NO_AUTO_REBOOT=1` too."
        ),
    )
    parser.add_argument(
        "--no-freshness-check",
        action="store_true",
        help=(
            "Skip the PRD-E E1 boot-time compose freshness check (#10684 / "
            "E5 escape hatch). The lifespan still loads state and gates "
            "spawn paths on a persisted `compose_freshness_failed=True`, "
            "but does NOT re-run `compose.py deploy-all`. Use ONLY for "
            "emergency boots where the operator already knows the compose "
            "set is correct and needs the harness up before the compose "
            "subprocess can run. Honors "
            "`SQUIDSQUAD_HARNESS_NO_FRESHNESS_CHECK=1` too."
        ),
    )

    args = parser.parse_args()

    # Module-level switch read by `_deferred_init` in the lifespan. Also
    # honors the `SQUIDSQUAD_HARNESS_NO_AUTO_START=1` env var so callers
    # that don't go through argparse (e.g. test harnesses, restart
    # scripts) can opt in too.
    global _NO_AUTO_START, _NO_AUTO_REBOOT, _NO_FRESHNESS_CHECK
    env_flag = os.environ.get("SQUIDSQUAD_HARNESS_NO_AUTO_START", "")
    _NO_AUTO_START = args.no_auto_start or env_flag.lower() in ("1", "true", "yes")
    env_reboot = os.environ.get("SQUIDSQUAD_HARNESS_NO_AUTO_REBOOT", "")
    _NO_AUTO_REBOOT = args.no_auto_reboot or env_reboot.lower() in ("1", "true", "yes")
    env_freshness = os.environ.get("SQUIDSQUAD_HARNESS_NO_FRESHNESS_CHECK", "")
    _NO_FRESHNESS_CHECK = (
        args.no_freshness_check
        or env_freshness.lower() in ("1", "true", "yes")
    )

    # Determine port (#12820 — see _resolve_listen_port). The production
    # singleton path (no --port) acquires the canonical port or refuses; it
    # never binds an ephemeral port, so it cannot poison clone .harness-port
    # files. An explicit --port (incl. --port 0) keeps the legacy
    # ephemeral-fallback behavior the integration test harness relies on.
    actual_port = _resolve_listen_port(args.port)

    state.port = actual_port
    _print_banner(actual_port)

    # Install Ctrl+C escalation handler (#4966)
    ctrl_c = CtrlCHandler()
    signal.signal(signal.SIGINT, ctrl_c.handle)

    # Run uvicorn in a daemon thread so the main thread stays available
    # for signal handling. On Windows, signal handlers set via
    # signal.signal() only fire in the main thread — if uvicorn.run()
    # blocks the main thread, Ctrl+C is never delivered to our handler.
    # #11587: loop="none" (set inside _build_uvicorn_config) is what makes the
    # #9562 WindowsSelectorEventLoopPolicy above actually govern the server loop
    # running in this daemon thread — otherwise uvicorn imposes a ProactorEventLoop.
    config = _build_uvicorn_config(app, host="127.0.0.1", port=actual_port)
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
