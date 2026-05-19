"""Unit tests for the harness eviction signal (#9331).

Two layers:

- ``EventStream.get_since_with_eviction`` returns an eviction marker
  when the caller's cursor predates the retained window. The marker
  carries ``oldest_id`` (safe re-anchor) and ``evicted_count_hint``
  (coarse operator-forensic estimate of how many events the cursor
  has missed). Normal cases — cursor found, or no cursor passed —
  return ``(events, None)``.

- ``event_poll.py`` consumes the ``evicted``/``oldest_id``/
  ``evicted_count_hint`` keys on the response payload, emits exactly
  one stderr warning per response naming the anchor + hint, and then
  proceeds with normal event processing (the first event in the
  payload IS ``oldest_id``, so cursor advancement happens implicitly).

Unblocks: #8999 §4.4 IT-EvictionGap.
"""

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"


def _load_module(name: str, source: Path):
    """Load a module under a unique name to dodge sys.modules collisions."""
    spec = importlib.util.spec_from_file_location(name, source)
    if not (spec and spec.loader):
        raise ImportError(f"cannot build spec for {source}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _harness = _load_module("_harness_for_eviction", SCRIPTS / "harness.py")
    EventStream = _harness.EventStream
    HARNESS_AVAILABLE = True
except Exception as _e:
    print(
        f"[test_eviction_signal] harness import failed: "
        f"{type(_e).__name__}: {_e}",
        file=sys.stderr,
    )
    HARNESS_AVAILABLE = False
    EventStream = None  # type: ignore


try:
    _ep = _load_module("_event_poll_for_eviction", SCRIPTS / "event_poll.py")
    EVENT_POLL_AVAILABLE = True
except Exception as _e:
    print(
        f"[test_eviction_signal] event_poll import failed: "
        f"{type(_e).__name__}: {_e}",
        file=sys.stderr,
    )
    EVENT_POLL_AVAILABLE = False
    _ep = None


def _ev(eid: str, **extra) -> dict:
    out = {"id": eid, "event_type": "status-transition", "role": "skill"}
    out.update(extra)
    return out


# ---------------------------------------------------------------------------
# EventStream.get_since_with_eviction
# ---------------------------------------------------------------------------


@unittest.skipUnless(HARNESS_AVAILABLE, "harness module not importable")
class TestGetSinceWithEvictionMarker(unittest.TestCase):
    """Behavioral matrix for the eviction-aware getter."""

    def test_no_cursor_returns_no_marker(self):
        stream = EventStream(maxlen=10)
        for i in range(5):
            stream.append(_ev(f"e{i}"))

        events, marker = stream.get_since_with_eviction(None, limit=100)
        self.assertEqual([e["id"] for e in events], [f"e{i}" for i in range(5)])
        self.assertIsNone(marker)

    def test_cursor_in_deque_returns_no_marker(self):
        """Normal case: cursor still in retained window."""
        stream = EventStream(maxlen=10)
        for i in range(5):
            stream.append(_ev(f"e{i}"))

        events, marker = stream.get_since_with_eviction("e1", limit=100)
        self.assertEqual([e["id"] for e in events], ["e2", "e3", "e4"])
        self.assertIsNone(marker)

    def test_cursor_in_deque_returns_oldest_first_when_truncated(self):
        """When the cursor is found but the events-after-cursor count
        exceeds ``limit``, the returned slice must be the OLDEST
        ``limit`` events after the cursor — same skim-then-advance
        contract as the evicted branch. Returning newest-first would
        silently drop the gap between cursor and (head − limit) and
        cause the agent to jump ahead.
        """
        stream = EventStream(maxlen=50)
        for i in range(20):
            stream.append(_ev(f"e{i:02d}"))

        events, marker = stream.get_since_with_eviction("e05", limit=3)
        self.assertEqual(
            [e["id"] for e in events], ["e06", "e07", "e08"],
            msg="cursor-found branch must return oldest events after "
                "the cursor when truncated by limit; otherwise the "
                "agent jumps to the latest and silently drops the gap.",
        )
        self.assertIsNone(marker)

    def test_cursor_evicted_returns_marker_with_oldest_id(self):
        """Cursor predates the retained window — marker names the
        anchor + how many events have rolled off."""
        stream = EventStream(maxlen=5)
        # Emit 12 events; only the last 5 (e7..e11) stay retained.
        for i in range(12):
            stream.append(_ev(f"e{i}"))

        events, marker = stream.get_since_with_eviction("e1", limit=100)
        self.assertEqual(
            [e["id"] for e in events],
            ["e7", "e8", "e9", "e10", "e11"],
        )
        self.assertIsNotNone(marker)
        assert marker is not None  # narrow for type checker
        self.assertEqual(marker["oldest_id"], "e7")
        # 12 emitted − 5 retained = 7 evicted.
        self.assertEqual(marker["evicted_count_hint"], 7)

    def test_empty_deque_with_evicted_cursor_has_none_oldest_id(self):
        """Degenerate: harness cold-start with stale cursor → no anchor."""
        stream = EventStream(maxlen=10)

        events, marker = stream.get_since_with_eviction("stale", limit=100)
        self.assertEqual(events, [])
        self.assertIsNotNone(marker)
        assert marker is not None
        self.assertIsNone(marker["oldest_id"])
        self.assertEqual(marker["evicted_count_hint"], 0)

    def test_cursor_at_head_returns_empty_no_marker(self):
        """Cursor IS the most recent event — empty, no marker."""
        stream = EventStream(maxlen=10)
        for i in range(3):
            stream.append(_ev(f"e{i}"))

        events, marker = stream.get_since_with_eviction("e2", limit=100)
        self.assertEqual(events, [])
        self.assertIsNone(marker)

    def test_evicted_events_returned_oldest_first(self):
        """When cursor is evicted, the returned slice MUST be oldest-first
        — the agent skims through the gap rather than jumping to the
        latest event and silently dropping the in-between."""
        stream = EventStream(maxlen=20)
        for i in range(20):
            stream.append(_ev(f"e{i:02d}"))

        events, marker = stream.get_since_with_eviction(
            "evicted-stale", limit=5
        )
        self.assertEqual(
            [e["id"] for e in events],
            ["e00", "e01", "e02", "e03", "e04"],
            msg="skim-then-advance: expected oldest 5 after eviction",
        )
        self.assertIsNotNone(marker)

    def test_total_emitted_count_increments_on_append(self):
        stream = EventStream(maxlen=3)
        self.assertEqual(stream._total_emitted_count, 0)
        for i in range(7):
            stream.append(_ev(f"e{i}"))
        self.assertEqual(stream._total_emitted_count, 7)
        self.assertEqual(len(stream), 3)

    def test_legacy_get_since_wrapper_drops_marker(self):
        """Back-compat: ``get_since`` still returns only the list."""
        stream = EventStream(maxlen=5)
        for i in range(10):
            stream.append(_ev(f"e{i}"))

        events = stream.get_since("stale", limit=100)
        self.assertEqual(
            [e["id"] for e in events],
            ["e5", "e6", "e7", "e8", "e9"],
        )


# ---------------------------------------------------------------------------
# event_poll.py — eviction warning + cursor advance
# ---------------------------------------------------------------------------


@unittest.skipUnless(EVENT_POLL_AVAILABLE, "event_poll module not importable")
class TestEventPollEvictionWarning(unittest.TestCase):
    """``poll()`` must emit a single stderr warning when the response
    carries ``evicted: true``, then process events normally."""

    def setUp(self):
        # Patch port discovery so poll() doesn't try to read a real
        # .harness-port file (which may or may not exist in CI).
        self._port_patch = mock.patch.object(_ep, "_discover_port",
                                             return_value=4321)
        self._port_patch.start()
        self.addCleanup(self._port_patch.stop)

        # Patch cursor read/write to in-memory state for determinism.
        self._stored_cursor = ""

        def _read_cursor(role, since_arg=None):
            if since_arg is not None:
                return str(since_arg)
            return self._stored_cursor

        def _write_cursor(role, value):
            self._stored_cursor = str(value)
            return True

        self._read_patch = mock.patch.object(_ep, "_resolve_cursor",
                                             side_effect=_read_cursor)
        self._write_patch = mock.patch.object(_ep, "_write_cursor_atomic",
                                              side_effect=_write_cursor)
        self._read_patch.start()
        self._write_patch.start()
        self.addCleanup(self._read_patch.stop)
        self.addCleanup(self._write_patch.stop)

    def _run_poll_with_payload(self, payload: dict) -> tuple[str, str, list]:
        """Drive poll() with a single fake harness response.

        Returns (stdout, stderr, events_emitted) for assertions.
        """
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        emitted = []

        def fake_fetch(url, timeout):
            return payload, False, None

        with mock.patch.object(_ep, "_fetch_once", side_effect=fake_fetch), \
             mock.patch("sys.stdout", captured_stdout), \
             mock.patch("sys.stderr", captured_stderr):
            result = _ep.poll("skill", since="stale-cursor", limit=10)
            if result is not None:
                emitted = list(result)
        return captured_stdout.getvalue(), captured_stderr.getvalue(), emitted

    def test_eviction_warning_matches_locked_format(self):
        """CONTEXT-9331 §4 locks the stderr warning text so QA's
        grep-based assertions remain stable. Any reword must update
        both this test AND CONTEXT-9331 §4."""
        payload = {
            "events": [
                {"id": "e7", "event_type": "status-transition", "role": "skill"},
                {"id": "e8", "event_type": "status-transition", "role": "skill"},
            ],
            "total": 2,
            "evicted": True,
            "oldest_id": "e7",
            "evicted_count_hint": 42,
        }
        stdout, stderr, emitted = self._run_poll_with_payload(payload)

        expected_line = (
            "[event_poll] EVICTION: cursor predates retained window — "
            "advancing to e7, ~42 events evicted"
        )
        self.assertIn(
            expected_line, stderr,
            msg=f"stderr did not contain the locked warning line.\n"
                f"got: {stderr!r}\nexpected substring: {expected_line!r}",
        )
        # Exactly one warning per response, not once per event.
        self.assertEqual(stderr.count("EVICTION"), 1)

        # Events still flow through stdout normally.
        self.assertEqual([e["id"] for e in emitted], ["e7", "e8"])
        # Cursor advanced past last event in the batch.
        self.assertEqual(self._stored_cursor, "e8")

    def test_no_warning_when_payload_lacks_evicted_flag(self):
        """Normal response — no warning, no spurious noise on stderr."""
        payload = {
            "events": [
                {"id": "a1", "event_type": "status-transition", "role": "skill"},
            ],
            "total": 1,
        }
        stdout, stderr, emitted = self._run_poll_with_payload(payload)

        self.assertNotIn("EVICTION", stderr)
        self.assertEqual([e["id"] for e in emitted], ["a1"])
        self.assertEqual(self._stored_cursor, "a1")

    def test_no_warning_when_evicted_explicitly_false(self):
        """``evicted: false`` is treated the same as the field being
        absent — no warning."""
        payload = {
            "events": [
                {"id": "b1", "event_type": "status-transition", "role": "skill"},
            ],
            "total": 1,
            "evicted": False,
        }
        stdout, stderr, emitted = self._run_poll_with_payload(payload)
        self.assertNotIn("EVICTION", stderr)

    def test_eviction_with_empty_events_still_warns(self):
        """Harness deque empty + stale cursor → warn but no cursor
        advance (no anchor available). Operator can see the harness
        is degraded; the warning repeats on subsequent polls until
        events start flowing again."""
        payload = {
            "events": [],
            "total": 0,
            "evicted": True,
            "oldest_id": None,
            "evicted_count_hint": 0,
        }
        stdout, stderr, emitted = self._run_poll_with_payload(payload)
        self.assertIn("EVICTION", stderr)
        self.assertEqual(emitted, [])
        # Cursor unchanged — nothing to advance to.
        self.assertEqual(self._stored_cursor, "")

    def test_eviction_re_anchors_when_role_filter_drops_all_events(self):
        """`/events/for/{role}` can return ``evicted: true`` with an
        empty events list when the role filter strips every event in
        the batch — even though the deque is non-empty and
        ``oldest_id`` is set. Without re-anchoring, the cursor stays
        on the stale id and the warning loops forever. The fix:
        advance the cursor to ``oldest_id`` up front whenever the
        eviction signal is present and an anchor is available, so
        forward progress is guaranteed regardless of whether the
        filter kept any events."""
        payload = {
            "events": [],
            "total": 0,
            "evicted": True,
            "oldest_id": "anchor-id",
            "evicted_count_hint": 17,
        }
        stdout, stderr, emitted = self._run_poll_with_payload(payload)
        self.assertIn("EVICTION", stderr)
        self.assertEqual(emitted, [])
        # Cursor re-anchored to oldest_id even though no events flowed.
        self.assertEqual(
            self._stored_cursor, "anchor-id",
            msg="cursor must advance to oldest_id when role filter "
                "drops every event — otherwise the agent loops on the "
                "same stale cursor and the warning never clears.",
        )

    def test_eviction_re_anchor_then_events_advance_cursor_further(self):
        """When events DO survive the role filter, the up-front
        re-anchor to ``oldest_id`` is followed by normal per-event
        cursor advance. Final cursor = last event id, not
        ``oldest_id``."""
        payload = {
            "events": [
                {"id": "later-1", "event_type": "status-transition", "role": "skill"},
                {"id": "later-2", "event_type": "status-transition", "role": "skill"},
            ],
            "total": 2,
            "evicted": True,
            "oldest_id": "anchor-id",
            "evicted_count_hint": 9,
        }
        stdout, stderr, emitted = self._run_poll_with_payload(payload)
        self.assertEqual([e["id"] for e in emitted], ["later-1", "later-2"])
        self.assertEqual(self._stored_cursor, "later-2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
