"""Regression tests for the #12720 thread-leak guard (tests/conftest.py).

Root cause of #12720: tests/test_harness.py::test_post_shutdown_returns_202
POSTed /shutdown to the in-process app; the handler's `shutdown` DAEMON
thread sleeps then calls os._exit(0). The test's os._exit patch reverted the
instant the POST returned, so ~1s later the REAL os._exit(0) fired from the
daemon thread and hard-killed the pytest process (exit 0, no summary). The
conftest guard fails LOUDLY when a test leaves such a thread alive instead of
letting it silently arm a delayed process kill.

These lock the guard's classification logic so a future edit can't silently
neuter it (the guard catches its own regressions only if it still works).
"""

import threading
import time

import conftest  # tests/conftest.py — on sys.path during the run (#11394 gate)


def _baseline():
    return {t.ident for t in threading.enumerate()}


def test_nondaemon_leak_is_flagged():
    base = _baseline()
    stop = threading.Event()
    t = threading.Thread(target=stop.wait, name="probe-nondaemon", daemon=False)
    t.start()
    try:
        leaked = conftest._guard_leaked_threads(base)
        assert any(x.name == "probe-nondaemon" for x in leaked), (
            "a non-daemon thread spawned during a test must be flagged"
        )
    finally:
        stop.set()
        t.join(timeout=5)


def test_benign_daemon_thread_is_tolerated():
    base = _baseline()
    stop = threading.Event()
    t = threading.Thread(target=stop.wait, name="probe-benign-daemon", daemon=True)
    t.start()
    try:
        leaked = conftest._guard_leaked_threads(base)
        assert not any(x.name == "probe-benign-daemon" for x in leaked), (
            "a benign daemon thread (library worker) must NOT be flagged"
        )
    finally:
        stop.set()
        t.join(timeout=5)


def test_dangerous_named_daemon_is_flagged():
    """The actual #12720 masker is a DAEMON thread named `shutdown` that calls
    os._exit — it MUST be flagged even though it is a daemon."""
    base = _baseline()
    stop = threading.Event()
    t = threading.Thread(target=stop.wait, name="shutdown", daemon=True)
    t.start()
    try:
        leaked = conftest._guard_leaked_threads(base)
        assert any(x.name == "shutdown" for x in leaked), (
            "the harness `shutdown` daemon thread (os._exit caller) must be "
            "flagged even as a daemon"
        )
    finally:
        stop.set()
        t.join(timeout=5)


def test_allowlisted_thread_is_tolerated():
    base = _baseline()
    stop = threading.Event()
    name = next(iter(conftest._GUARD_ALLOWED_THREAD_NAMES))
    t = threading.Thread(target=stop.wait, name=name, daemon=False)
    t.start()
    try:
        leaked = conftest._guard_leaked_threads(base)
        assert not any(x.name == name for x in leaked), (
            f"allowlisted thread {name!r} (per-class fixture server) must NOT "
            f"be flagged even when non-daemon"
        )
    finally:
        stop.set()
        t.join(timeout=5)


def test_preexisting_thread_not_flagged():
    """Only threads that appear DURING the test count; a thread already alive
    at baseline (another test's fixture, the main thread) is never flagged."""
    stop = threading.Event()
    t = threading.Thread(target=stop.wait, name="probe-preexisting", daemon=False)
    t.start()
    try:
        # baseline captured AFTER the thread exists → it is part of the baseline
        base = _baseline()
        leaked = conftest._guard_leaked_threads(base)
        assert not any(x.name == "probe-preexisting" for x in leaked)
    finally:
        stop.set()
        t.join(timeout=5)


def test_dead_thread_not_flagged():
    base = _baseline()
    t = threading.Thread(target=lambda: None, name="probe-shortlived", daemon=False)
    t.start()
    t.join(timeout=5)
    # give the interpreter a beat to mark it not-alive
    for _ in range(50):
        if not t.is_alive():
            break
        time.sleep(0.01)
    leaked = conftest._guard_leaked_threads(base)
    assert not any(x.name == "probe-shortlived" for x in leaked), (
        "a thread that has finished must not be flagged as a live leak"
    )
