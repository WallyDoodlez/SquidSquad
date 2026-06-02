"""Tests for references/scripts/l4_file_watcher.py (#10682, PRD-E E3).

Strategy: every test exercises the **pure-function** surface (path
classification, alias filtering, per-alias recompose, event emission)
with stub ``run_compose`` callables and a list-collecting ``emit_event``
sink. The ``watchdog`` library is NOT required to be installed for
the unit suite — only ``start_watcher`` imports it (lazily), and we
don't exercise that path here.

AC6 mandates tests for:
  (a) write to project file -> recompose runs for matching aliases,
      event emitted
  (b) multiple writes batched (debounce)
  (c) unrelated file change (e.g., temp file) -> no compose

Plus AC5 failure-mode coverage: compose failure -> compose-failed
event (NOT restart-required); per-alias independence on failure.
"""

import sys
import threading
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_file_watcher as lfw  # noqa: E402


# A representative registry: 3 aliases bound to 2 role-classes (pm twice,
# dm once). Used across multiple tests to verify role-class filtering.
_REGISTRY = {
    "pm": ("pm", None),
    "pm-mobile": ("pm", "ios"),
    "dm-skill": ("dm", "skill"),
    "worker-skill": ("worker", "skill"),
}


def _ok_compose(alias):
    return True, f"deployed {alias}\n", ""


def _fail_compose(alias):
    return False, "", f"compose failed for {alias}: missing manifest"


class _EventSink:
    """List-collecting emit_event stub. Matches the harness signature."""

    def __init__(self):
        self.events = []

    def __call__(self, event_type, role, payload=None, **extra):
        self.events.append({
            "event_type": event_type,
            "role": role,
            "payload": payload or {},
            **extra,
        })


# ---------------------------------------------------------------------------
# role_class_from_path
# ---------------------------------------------------------------------------


class TestRoleClassFromPath:
    """AC6(c) — unrelated changes must NOT classify as role-class events."""

    def test_pm_md_classifies_as_pm(self, tmp_path):
        target = tmp_path / ".squidsquad" / "project" / "pm.md"
        target.parent.mkdir(parents=True)
        target.write_text("# pm L4\n")
        assert lfw.role_class_from_path(target, repo_root=tmp_path) == "pm"

    def test_subdirectory_file_ignored(self, tmp_path):
        # .squidsquad/project/subdir/pm.md is NOT a watched role-class.
        target = tmp_path / ".squidsquad" / "project" / "sub" / "pm.md"
        target.parent.mkdir(parents=True)
        target.write_text("# nope\n")
        assert lfw.role_class_from_path(target, repo_root=tmp_path) is None

    def test_dotfile_temp_ignored(self, tmp_path):
        # Editor swap files (e.g. .pm.md.swp) and dotfiles must not trigger.
        target = tmp_path / ".squidsquad" / "project" / ".pm.md"
        target.parent.mkdir(parents=True)
        target.write_text("# swap\n")
        assert lfw.role_class_from_path(target, repo_root=tmp_path) is None

    def test_non_md_extension_ignored(self, tmp_path):
        target = tmp_path / ".squidsquad" / "project" / "pm.txt"
        target.parent.mkdir(parents=True)
        target.write_text("# wrong ext\n")
        assert lfw.role_class_from_path(target, repo_root=tmp_path) is None

    def test_path_outside_repo_ignored(self, tmp_path):
        # A path that doesn't sit under repo_root must not classify.
        other_repo = tmp_path / "other"
        outside = other_repo / ".squidsquad" / "project" / "pm.md"
        outside.parent.mkdir(parents=True)
        outside.write_text("# elsewhere\n")
        assert lfw.role_class_from_path(
            outside, repo_root=tmp_path) is None


# ---------------------------------------------------------------------------
# compute_affected_aliases
# ---------------------------------------------------------------------------


class TestComputeAffectedAliases:

    def test_filters_to_role_class(self):
        # pm role-class -> two aliases (pm + pm-mobile).
        out = lfw.compute_affected_aliases("pm", _REGISTRY)
        assert out == ["pm", "pm-mobile"]

    def test_single_alias_role_class(self):
        out = lfw.compute_affected_aliases("dm", _REGISTRY)
        assert out == ["dm-skill"]

    def test_unknown_role_class_returns_empty(self):
        out = lfw.compute_affected_aliases("verifier", _REGISTRY)
        assert out == []


# ---------------------------------------------------------------------------
# recompose_for_role_class — success + failure modes
# ---------------------------------------------------------------------------


class TestRecomposeForRoleClass:

    def test_success_emits_restart_required(self):
        results = lfw.recompose_for_role_class(
            "dm", _REGISTRY, run_compose=_ok_compose)
        assert len(results) == 1
        r = results[0]
        assert r.alias == "dm-skill"
        assert r.succeeded is True
        assert r.event_context == "restart-required"
        assert r.payload == {"reason": "l4-recompose"}

    def test_failure_emits_compose_failed_not_restart(self):
        # AC5: compose failure -> compose-failed event, NEVER restart-required.
        results = lfw.recompose_for_role_class(
            "pm", _REGISTRY, run_compose=_fail_compose)
        contexts = [r.event_context for r in results]
        assert "restart-required" not in contexts
        assert all(c == "compose-failed" for c in contexts)
        assert all(r.succeeded is False for r in results)
        assert all("missing manifest" in r.payload["stderr"]
                   for r in results)

    def test_failure_in_one_alias_does_not_halt_others(self):
        # Stub: pm fails, pm-mobile succeeds.
        def mixed(alias):
            if alias == "pm":
                return False, "", "pm broke"
            return True, f"deployed {alias}\n", ""
        results = lfw.recompose_for_role_class(
            "pm", _REGISTRY, run_compose=mixed)
        assert len(results) == 2
        by_alias = {r.alias: r for r in results}
        assert by_alias["pm"].event_context == "compose-failed"
        assert by_alias["pm-mobile"].event_context == "restart-required"

    def test_runner_raise_is_treated_as_failure(self):
        def boom(alias):
            raise RuntimeError("subprocess unavailable")
        results = lfw.recompose_for_role_class(
            "pm", _REGISTRY, run_compose=boom)
        assert all(r.event_context == "compose-failed" for r in results)
        assert all("subprocess unavailable" in r.payload["stderr"]
                   for r in results)


# ---------------------------------------------------------------------------
# emit_results — wire to a harness-shaped emit_event
# ---------------------------------------------------------------------------


class TestEmitResults:

    def test_success_event_carries_target_alias_and_context(self):
        sink = _EventSink()
        results = lfw.recompose_for_role_class(
            "dm", _REGISTRY, run_compose=_ok_compose)
        lfw.emit_results(results, emit_event=sink)
        assert len(sink.events) == 1
        e = sink.events[0]
        assert e["event_type"] == "assigned-to"
        assert e["role"] == "harness"
        assert e["payload"]["target_alias"] == "dm-skill"
        assert e["payload"]["event_context"] == "restart-required"
        assert e["payload"]["reason"] == "l4-recompose"

    def test_failure_event_uses_compose_failed_context(self):
        sink = _EventSink()
        results = lfw.recompose_for_role_class(
            "pm", _REGISTRY, run_compose=_fail_compose)
        lfw.emit_results(results, emit_event=sink)
        # Both pm aliases failed -> two compose-failed events.
        assert len(sink.events) == 2
        assert all(e["payload"]["event_context"] == "compose-failed"
                   for e in sink.events)
        # And NO restart-required event for these failed aliases.
        contexts = [e["payload"]["event_context"] for e in sink.events]
        assert "restart-required" not in contexts


# ---------------------------------------------------------------------------
# recompose_path — end-to-end with path filtering
# ---------------------------------------------------------------------------


class TestRecomposePath:
    """AC6(a) — write to project file triggers recompose + event.
    AC6(c) — unrelated paths produce no events.
    """

    def test_pm_md_write_triggers_emit(self, tmp_path):
        sink = _EventSink()
        target = tmp_path / ".squidsquad" / "project" / "pm.md"
        target.parent.mkdir(parents=True)
        target.write_text("# pm\n")
        results = lfw.recompose_path(
            target,
            repo_root=tmp_path,
            registry=_REGISTRY,
            emit_event=sink,
            run_compose=_ok_compose,
        )
        assert [r.alias for r in results] == ["pm", "pm-mobile"]
        assert {e["payload"]["target_alias"] for e in sink.events} == {
            "pm", "pm-mobile",
        }
        assert {e["payload"]["event_context"] for e in sink.events} == {
            "restart-required",
        }

    def test_unrelated_file_produces_no_compose_no_events(self, tmp_path):
        sink = _EventSink()
        calls = []

        def tracking(alias):
            calls.append(alias)
            return True, "", ""

        target = tmp_path / ".squidsquad" / "project" / "README.md"
        target.parent.mkdir(parents=True)
        target.write_text("# nope\n")
        # README.md does parse to a role-class string per the
        # `<name>.md` rule. So this test uses a dotfile to exercise the
        # AC6(c) "temp file ignored" path.
        target.unlink()
        swap = target.parent / ".pm.md.swp"
        swap.write_text("swap\n")
        results = lfw.recompose_path(
            swap,
            repo_root=tmp_path,
            registry=_REGISTRY,
            emit_event=sink,
            run_compose=tracking,
        )
        assert results == []
        assert calls == []
        assert sink.events == []


# ---------------------------------------------------------------------------
# Debounce — coalesce multiple writes into one recompose
# ---------------------------------------------------------------------------


class TestDebounce:
    """AC6(b) — multiple writes within the window collapse to one fire."""

    def test_burst_coalesces_to_single_fire(self):
        fired = []
        ev = threading.Event()

        def cb(key):
            fired.append(key)
            ev.set()

        # Use a short window to keep test fast.
        debouncer = lfw._Debouncer(0.1, cb)
        for _ in range(5):
            debouncer.schedule("pm")
        # Wait for the timer to fire.
        ev.wait(timeout=2.0)
        # Give the timer a moment to coalesce, then assert.
        assert fired == ["pm"]

    def test_distinct_keys_fire_independently(self):
        fired = []
        ev_pm = threading.Event()
        ev_dm = threading.Event()

        def cb(key):
            fired.append(key)
            if key == "pm":
                ev_pm.set()
            elif key == "dm":
                ev_dm.set()

        debouncer = lfw._Debouncer(0.1, cb)
        debouncer.schedule("pm")
        debouncer.schedule("dm")
        ev_pm.wait(timeout=2.0)
        ev_dm.wait(timeout=2.0)
        assert sorted(fired) == ["dm", "pm"]

    def test_flush_cancels_pending_without_firing(self):
        fired = []
        debouncer = lfw._Debouncer(5.0, fired.append)  # long window
        debouncer.schedule("pm")
        debouncer.flush()
        time.sleep(0.05)  # give any rogue timer a chance to fire
        assert fired == []

    def test_stale_timer_after_reschedule_does_not_double_fire(self):
        # DS-E3 review F1 regression: simulate the race where a timer
        # has already entered _fire (acquired its slot in the timer
        # thread pool) before a new schedule() call replaces the
        # stored timer. With the generation-counter guard the stale
        # call must drop without invoking the callback.
        fired = []
        debouncer = lfw._Debouncer(60.0, fired.append)  # long window

        # Schedule once -> generation 1 is stored.
        debouncer.schedule("pm")
        with debouncer._lock:
            gen1, timer1 = debouncer._timers["pm"]
        timer1.cancel()  # stop the real timer; we'll drive _fire manually.

        # Schedule again -> generation 2 replaces it.
        debouncer.schedule("pm")
        with debouncer._lock:
            gen2, timer2 = debouncer._timers["pm"]
        timer2.cancel()

        # Now simulate generation-1's _fire firing after generation 2
        # is stored. Must be a no-op.
        debouncer._fire("pm", gen1)
        assert fired == [], (
            "stale timer should not invoke callback when a newer "
            "generation has replaced it"
        )
        # The current generation is still stored — flush + re-schedule
        # leaves a clean state.
        assert "pm" in debouncer._timers
        debouncer.flush()
        assert debouncer._timers == {}


# ---------------------------------------------------------------------------
# make_change_callback — wiring with registry_provider freshness
# ---------------------------------------------------------------------------


class TestChangeCallback:

    def test_registry_read_per_change_call(self, tmp_path):
        sink = _EventSink()
        registries = [{"pm": ("pm", None)}, _REGISTRY]
        provider_calls = []

        def provider():
            idx = len(provider_calls)
            provider_calls.append(idx)
            return registries[idx]

        cb = lfw.make_change_callback(
            repo_root=tmp_path,
            registry_provider=provider,
            emit_event=sink,
            run_compose=_ok_compose,
        )
        cb("pm")  # registries[0]: 1 pm alias -> 1 event
        cb("pm")  # registries[1]: 2 pm aliases -> 2 events
        assert len(provider_calls) == 2
        # Per-call alias projection asserts the ORDER of registry
        # consumption -- not just the total count, so a future re-order
        # bug can't pass by symmetric coincidence (DS-E3 review F2).
        first_call_aliases = [
            e["payload"]["target_alias"] for e in sink.events[:1]
        ]
        second_call_aliases = sorted(
            e["payload"]["target_alias"] for e in sink.events[1:]
        )
        assert first_call_aliases == ["pm"]
        assert second_call_aliases == ["pm", "pm-mobile"]

    def test_registry_failure_emits_pm_compose_failed(self, tmp_path):
        sink = _EventSink()

        def boom():
            raise RuntimeError("config.md missing")

        cb = lfw.make_change_callback(
            repo_root=tmp_path,
            registry_provider=boom,
            emit_event=sink,
            run_compose=_ok_compose,
        )
        cb("pm")
        assert len(sink.events) == 1
        e = sink.events[0]
        assert e["payload"]["target_alias"] == "pm"
        assert e["payload"]["event_context"] == "compose-failed"
        assert "config.md missing" in e["payload"]["stderr"]


# ---------------------------------------------------------------------------
# Harness supervisor — survive-and-restart loop (AC5, QA route-back on
# PR #10746). The supervise tick is factored into
# ``HarnessState._supervise_l4_once`` so the regression test can drive
# it without spinning up FastAPI or watchdog.
# ---------------------------------------------------------------------------


class _FakeObserver:
    """Minimal watchdog.Observer stand-in: ``is_alive`` + ``stop`` +
    ``join``. Used by the supervisor regression test so it doesn't
    depend on watchdog being installed."""

    def __init__(self, *, alive=True):
        self._alive = alive
        self.stopped = False
        self.joined = False

    def is_alive(self):
        return self._alive

    def stop(self):
        self.stopped = True
        self._alive = False

    def join(self, timeout=None):
        self.joined = True


class _FakeDebouncer:
    def __init__(self):
        self.flush_calls = 0

    def flush(self):
        self.flush_calls += 1


def _fresh_harness_state():
    try:
        import harness  # noqa: F401
    except Exception:
        pytest.skip("harness module unavailable (likely missing fastapi)")
    return harness.HarnessState()


class TestHarnessSupervisor:
    """AC5 — when the file-watch Observer dies, the harness logs +
    restarts the watcher (QA route-back on PR #10746)."""

    def test_first_tick_spawns_observer(self):
        state = _fresh_harness_state()
        observers = []

        def starter():
            obs = _FakeObserver(alive=True)
            deb = _FakeDebouncer()
            observers.append(obs)
            return obs, deb

        action = state._supervise_l4_once(starter)
        assert action == "started"
        assert state._l4_observer is observers[0]
        assert state._l4_debouncer is not None
        assert len(observers) == 1

    def test_live_observer_is_no_op(self):
        state = _fresh_harness_state()
        starter_calls = []

        def starter():
            starter_calls.append(True)
            return _FakeObserver(alive=True), _FakeDebouncer()

        state._supervise_l4_once(starter)
        action = state._supervise_l4_once(starter)
        assert action == "running"
        assert len(starter_calls) == 1

    def test_dead_observer_is_respawned(self):
        # AC5 regression. QA route-back on PR #10746 named this as the
        # specific gap: "include a regression test that crashes the
        # Observer (e.g., raise inside the handler) and asserts the
        # harness re-spawns it."
        state = _fresh_harness_state()
        spawned = []

        def starter():
            obs = _FakeObserver(alive=True)
            spawned.append(obs)
            return obs, _FakeDebouncer()

        state._supervise_l4_once(starter)
        first = state._l4_observer

        # Kill the Observer to simulate a crash.
        first._alive = False

        action = state._supervise_l4_once(starter)
        assert action == "restarted"
        assert state._l4_observer is spawned[-1]
        assert state._l4_observer is not first
        assert len(spawned) == 2

    def test_start_failure_logs_and_retries_next_tick(self):
        state = _fresh_harness_state()
        attempts = []

        def starter():
            attempts.append(True)
            if len(attempts) == 1:
                raise RuntimeError("watchdog missing")
            return _FakeObserver(alive=True), _FakeDebouncer()

        action1 = state._supervise_l4_once(starter)
        assert action1 == "start-failed"
        assert state._l4_observer is None

        action2 = state._supervise_l4_once(starter)
        assert action2 == "started"
        assert state._l4_observer is not None
        assert len(attempts) == 2

    def test_stale_debouncer_flushed_on_respawn(self):
        state = _fresh_harness_state()
        observers = []

        def starter():
            obs = _FakeObserver(alive=True)
            deb = _FakeDebouncer()
            observers.append((obs, deb))
            return obs, deb

        state._supervise_l4_once(starter)
        stale_debouncer = state._l4_debouncer
        observers[0][0]._alive = False
        state._supervise_l4_once(starter)
        assert stale_debouncer.flush_calls == 1


class TestHarnessLifespanWiring:
    """Static-grep gate: the lifespan must reach start_l4_watcher() +
    stop_l4_watcher() — defining the methods is not enough."""

    def test_lifespan_calls_start_and_stop(self):
        src = (SCRIPTS / "harness.py").read_text(encoding="utf-8")
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        assert "state.start_l4_watcher()" in block, (
            "lifespan must call state.start_l4_watcher() on boot"
        )
        assert "state.stop_l4_watcher()" in block, (
            "lifespan must call state.stop_l4_watcher() on shutdown"
        )
