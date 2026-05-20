"""Tests for #9357 — EventLifecycleManager.load() lock-guarded idempotency.

Before #9357 the ``_loaded`` flag was read and written without holding
``self._lock``. Single-threaded use was fine (today the only caller is
``_deferred_init`` on the harness lifespan thread), but a future
refactor that fanned ``load()`` out across multiple threads could let
both threads pass the early-return guard, run the event-loading loop
twice, and double-append events into ``EventStream`` — inflating
``_total_emitted_count`` (the #9331 lifetime counter).

The fix wraps the check-and-set in ``self._lock``, claiming
``_loaded = True`` BEFORE any state mutation so a concurrent caller
observes True and returns immediately.

These tests pin both the source-level invariant and the runtime
behavior under thread contention.
"""

import importlib.util
import json
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"


def _load_module(name: str, source: Path):
    spec = importlib.util.spec_from_file_location(name, source)
    if not (spec and spec.loader):
        raise ImportError(f"cannot build spec for {source}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _harness = _load_module("_harness_for_9357", SCRIPTS / "harness.py")
    HARNESS_AVAILABLE = True
except Exception as _e:
    print(
        f"[test_9357] harness import failed: {type(_e).__name__}: {_e}",
        file=sys.stderr,
    )
    HARNESS_AVAILABLE = False
    _harness = None  # type: ignore


@unittest.skipUnless(HARNESS_AVAILABLE, "harness module not importable")
class TestLoadIdempotencyGuardLockProtected(unittest.TestCase):
    """``EventLifecycleManager.load()`` must hold ``self._lock`` when
    reading or writing the ``_loaded`` flag (#9357)."""

    def setUp(self):
        # Use a temp state file so the test doesn't touch the real
        # `.event-state.json`.
        import tempfile
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
        )
        # Seed a small state file so the load path exercises the
        # full body, not just the missing-file fast path.
        payload = {
            "events": [
                {"id": "ev1", "event_type": "status-transition", "role": "skill",
                 "timestamp": 1.0, "payload": {}},
                {"id": "ev2", "event_type": "status-transition", "role": "skill",
                 "timestamp": 2.0, "payload": {}},
                {"id": "ev3", "event_type": "status-transition", "role": "skill",
                 "timestamp": 3.0, "payload": {}},
            ],
            "in_flight": {},
            "dispatched": {},
            "dispatch_times": {},
            "retry_counts": {},
        }
        self.tmp.write(json.dumps(payload))
        self.tmp.close()
        self.state_path = Path(self.tmp.name)

        self._patch = mock.patch.object(_harness, "EVENT_STATE_FILE", self.state_path)
        self._patch.start()

        self.stream = _harness.EventStream(maxlen=1000)
        self.mgr = _harness.EventLifecycleManager(self.stream)

    def tearDown(self):
        self._patch.stop()
        try:
            self.state_path.unlink()
        except FileNotFoundError:
            pass

    def test_single_load_appends_events_once(self):
        """Sanity check: a single load() call appends the seeded
        events exactly once."""
        self.mgr.load()
        self.assertEqual(len(self.stream), 3)
        self.assertEqual(self.stream._total_emitted_count, 3)

    def test_second_load_is_silent_noop(self):
        """Calling load() twice from one thread is the idempotency
        contract — second call returns immediately, no re-append."""
        self.mgr.load()
        self.mgr.load()
        # Still exactly 3 events; counter not double-incremented.
        self.assertEqual(len(self.stream), 3)
        self.assertEqual(self.stream._total_emitted_count, 3)

    def test_concurrent_load_double_dispatch_does_not_double_append(self):
        """The real regression: spawn N threads all calling load()
        simultaneously. With the #9357 lock-guarded claim, exactly one
        thread runs the body; the others return immediately. Stream
        contents must reflect a single load, not N loads."""
        barrier = threading.Barrier(8)
        errors = []

        def worker():
            try:
                barrier.wait()  # release all threads at once
                self.mgr.load()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(errors, [], msg=f"workers raised: {errors}")
        # If the guard were broken, multiple workers would each append
        # the seeded 3 events into the stream.
        self.assertEqual(
            len(self.stream), 3,
            msg=f"event stream has {len(self.stream)} events after "
                f"concurrent load — expected 3. The _loaded guard was "
                f"not lock-protected and multiple workers double-appended.",
        )
        self.assertEqual(
            self.stream._total_emitted_count, 3,
            msg="lifetime emit counter was inflated by concurrent "
                "double-load — #9331's hint computation would be wrong.",
        )

    def test_loaded_flag_set_before_body_runs(self):
        """The fix claims `_loaded = True` BEFORE the body runs (read +
        parse + state mutation), so a concurrent caller observes True
        immediately and returns. Verify by patching the file read to
        block on an event; while it's blocked, a second thread's
        load() must return without doing any work."""
        body_started = threading.Event()
        body_may_continue = threading.Event()

        original_read = Path.read_text

        def slow_read_text(self, *args, **kwargs):
            # Only stall when the code under test reads the event-state
            # file; other Path.read_text callers (unrelated mocks,
            # logging, etc.) pass straight through to the real method.
            if str(self) == str(_harness.EVENT_STATE_FILE):
                body_started.set()
                body_may_continue.wait(timeout=5)
            return original_read(self, *args, **kwargs)

        results = {"second_caller_returned": False}

        def first_caller():
            with mock.patch.object(Path, "read_text", slow_read_text):
                self.mgr.load()

        def second_caller():
            body_started.wait(timeout=5)
            # First caller is now blocked inside the body (after
            # claiming _loaded=True). Our load() call must return
            # immediately without doing any disk I/O.
            t0 = time.monotonic()
            self.mgr.load()
            elapsed = time.monotonic() - t0
            results["elapsed"] = elapsed
            results["second_caller_returned"] = True
            # Release the first caller so it can finish.
            body_may_continue.set()

        t1 = threading.Thread(target=first_caller)
        t2 = threading.Thread(target=second_caller)
        t1.start()
        t2.start()
        t2.join(timeout=10)
        t1.join(timeout=10)

        self.assertTrue(
            results["second_caller_returned"],
            msg="second concurrent load() did not return — the lock "
                "claim is not freeing the second caller, suggesting "
                "the guard still serializes the entire body.",
        )
        self.assertLess(
            results.get("elapsed", 99), 1.0,
            msg=f"second load() took {results.get('elapsed')}s — should "
                f"have been ~immediate (the claim path exits before "
                f"the slow body). Implies the lock is held through "
                f"the body, defeating the purpose of the claim.",
        )


@unittest.skipUnless(HARNESS_AVAILABLE, "harness module not importable")
class TestLoadStaticInvariant(unittest.TestCase):
    """Static check against the source: the ``_loaded`` check-and-set
    must happen inside a ``with self._lock:`` block. Catches regressions
    where a refactor moves the check back out of the lock."""

    def test_loaded_check_is_inside_lock(self):
        source = (SCRIPTS / "harness.py").read_text(encoding="utf-8")

        # Locate the load() function body.
        marker = "    def load(self):"
        idx = source.find(marker)
        self.assertGreaterEqual(idx, 0, msg="EventLifecycleManager.load() not found")

        # Read forward until the next top-level def or class boundary.
        sig_end = source.find("\n", idx) + 1
        next_def = source.find("\n    def ", sig_end)
        next_class = source.find("\nclass ", sig_end)
        end_candidates = [n for n in (next_def, next_class) if n > 0]
        end = min(end_candidates) if end_candidates else len(source)
        body = source[sig_end:end]

        # The very first non-comment, non-docstring, non-blank line of
        # logic must be `with self._lock:` so the _loaded check is
        # under the lock. Walk forward past the docstring (triple-quoted)
        # and any leading comments to find the first executable line.
        lines = body.splitlines()
        in_docstring = False
        first_logic = None
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if s.startswith('"""') or s.startswith("'''"):
                # Toggle docstring; handle one-liners.
                quote = s[:3]
                if s.count(quote) >= 2 and len(s) > 3:
                    continue  # single-line docstring
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if s.startswith("#"):
                continue
            first_logic = s
            break

        self.assertIsNotNone(first_logic, msg="no executable line in load() body")
        self.assertTrue(
            first_logic.startswith("with self._lock"),
            msg=(
                f"load()'s first executable line is {first_logic!r} — "
                f"must be `with self._lock:` so the _loaded check-and-set "
                f"is lock-protected (#9357). If you refactored, ensure "
                f"the new shape still claims _loaded atomically."
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
