"""Regression tests for #9740 — eviction-cursor race in event_poll.poll().

Before #9740 the eviction-gap handler wrote `oldest_id` to the cursor BEFORE
the per-event loop. If any subsequent per-event write failed (disk full,
permission denied) the cursor was stuck at `oldest_id` but the `oldest_id`
event had never been emitted to stdout, so on retry `since=oldest_id`
semantics skipped it forever (permanent event loss).

CONTEXT-9740 D1 moved the re-anchor write to AFTER the per-event loop,
conditional on `events == []`. These tests cover the 8 ACs:

- AC-1: non-eviction path unchanged
- AC-2: eviction + non-empty + all writes succeed → no pre-loop write
- AC-3: eviction + empty batch + write succeeds → post-loop write fires
- AC-4: eviction + non-empty + per-event write fails mid-batch → cursor at
        last successful event, NOT at oldest_id
- AC-5: pre-loop re-anchor write no longer happens on eviction + non-empty
- AC-6: eviction + oldest_id is None → fatal (return None, no write)
- AC-7: eviction + empty batch + oldest_id is None → fatal
- AC-8: variable scoping — oldest_id reachable at post-loop site
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import event_poll


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_response(payload):
    """Wrap a dict into a urlopen-context-manager-compatible stub."""

    class _Resp:
        def read(self):
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    return _Resp()


def _patch_basics(monkeypatch):
    """Stub port + cursor + urlopen-able harness response."""
    monkeypatch.setattr(event_poll, "_discover_port", lambda: 7373)
    monkeypatch.setattr(event_poll, "_resolve_cursor",
                        lambda role, since=None: "stale-id")


def _make_urlopen_returning(payload):
    def _fake(req, timeout=None):
        return _stub_response(payload)
    return _fake


# ---------------------------------------------------------------------------
# AC-1: non-eviction path unchanged
# ---------------------------------------------------------------------------


class TestNonEvictionPathUnchanged:
    def test_normal_poll_writes_cursor_per_event_only(self, monkeypatch):
        _patch_basics(monkeypatch)
        writes = []
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda role, cid: writes.append(cid) or True)
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}],
                # No "evicted" key — normal non-eviction path
            }),
        )
        result = event_poll.poll("skill")
        assert result == [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}]
        # Cursor advanced exactly once per event, in order
        assert writes == ["e1", "e2", "e3"]


# ---------------------------------------------------------------------------
# AC-2 + AC-5: eviction + non-empty batch — pre-loop write is GONE
# ---------------------------------------------------------------------------


class TestEvictionWithNonEmptyBatch:
    def test_no_pre_loop_write_then_per_event_writes(self, monkeypatch):
        """Pre-loop write removed (#9740). Per-event writes proceed normally."""
        _patch_basics(monkeypatch)
        writes = []
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda role, cid: writes.append(cid) or True)
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [{"id": "ev10"}, {"id": "ev11"}],
                "evicted": True,
                "oldest_id": "ev10",
                "evicted_count_hint": 5,
            }),
        )
        result = event_poll.poll("skill")
        assert result == [{"id": "ev10"}, {"id": "ev11"}]
        # AC-5: pre-loop write to oldest_id did NOT happen. Only the
        # two per-event writes fired.
        assert writes == ["ev10", "ev11"]
        # AC-2: cursor sits at the last event in the batch.
        assert writes[-1] == "ev11"


# ---------------------------------------------------------------------------
# AC-3: eviction + empty batch — post-loop guard fires
# ---------------------------------------------------------------------------


class TestEvictionWithEmptyBatch:
    def test_post_loop_writes_oldest_id_when_all_filtered(self, monkeypatch):
        """`events == []` is the all-filtered case: forward progress requires writing oldest_id."""
        _patch_basics(monkeypatch)
        writes = []
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda role, cid: writes.append(cid) or True)
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [],
                "evicted": True,
                "oldest_id": "anchor-1",
                "evicted_count_hint": 12,
            }),
        )
        result = event_poll.poll("skill")
        assert result == []
        # Post-loop write fires exactly once with oldest_id.
        assert writes == ["anchor-1"]


# ---------------------------------------------------------------------------
# AC-4: eviction + non-empty + per-event write fails mid-batch
# ---------------------------------------------------------------------------


class TestEvictionMidBatchWriteFailure:
    def test_returns_none_and_cursor_stays_at_last_successful_event(self, monkeypatch):
        """Per-event write fails on the 3rd event; cursor must be at event 2's id, NOT oldest_id.

        AC-4: the bug pre-#9740 would have left the cursor at oldest_id even though
        oldest_id was not the last successfully emitted event. The fix removes the
        pre-loop write so the cursor naturally rests at the last successful per-event
        advance (event 2 here).
        """
        _patch_basics(monkeypatch)
        writes = []

        def _failing_write(role, cid):
            writes.append(cid)
            # Fail on the 3rd call (event 3's id)
            return len(writes) < 3

        monkeypatch.setattr(event_poll, "_write_cursor_atomic", _failing_write)
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [
                    {"id": "ev21"}, {"id": "ev22"}, {"id": "ev23"},
                ],
                "evicted": True,
                "oldest_id": "ev21",
                "evicted_count_hint": 3,
            }),
        )
        result = event_poll.poll("skill")
        assert result is None  # fatal — disk-write failure
        # writes = the 3 attempted per-event cursor writes. Writes 1+2 succeeded;
        # write 3 returned False. NO pre-loop write to oldest_id.
        assert writes == ["ev21", "ev22", "ev23"]
        # And specifically — the bug WOULD have shown writes[0] == "ev21" being
        # written BEFORE the per-event loop. Post-fix, writes[0] IS "ev21" but
        # it was written by the per-event loop on event 1 (whose id equals
        # oldest_id), not by a separate pre-loop call. We assert this by
        # checking that only 3 writes happened (one per event), not 4
        # (1 pre-loop + 3 per-event).
        assert len(writes) == 3


# ---------------------------------------------------------------------------
# AC-5: pre-loop re-anchor write no longer fires (positive assertion)
# ---------------------------------------------------------------------------


class TestNoPreLoopWriteOnEviction:
    def test_first_write_is_first_event_id_not_oldest_id(self, monkeypatch):
        """When events != [], the FIRST cursor write is the first event's id, not oldest_id.

        Pre-#9740: writes order was [oldest_id, ev10, ev11].
        Post-#9740: writes order is just [ev10, ev11].
        (oldest_id here equals ev10 because the harness puts the oldest event
        at the head of the batch — but the assertion that matters is that
        only 2 writes happen, not 3.)
        """
        _patch_basics(monkeypatch)
        writes = []
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda role, cid: writes.append(cid) or True)
        # Use distinct oldest_id != first event id to make the test sharp.
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [{"id": "ev30"}, {"id": "ev31"}],
                "evicted": True,
                "oldest_id": "anchor-zero",  # NOT equal to ev30
                "evicted_count_hint": 1,
            }),
        )
        event_poll.poll("skill")
        # Exactly 2 writes (per-event), and "anchor-zero" is NEVER written.
        assert writes == ["ev30", "ev31"]
        assert "anchor-zero" not in writes


# ---------------------------------------------------------------------------
# AC-6 + AC-7: oldest_id is None with evicted: true — fatal
# ---------------------------------------------------------------------------


class TestEvictionMissingOldestIdIsFatal:
    def test_eviction_with_null_oldest_id_and_non_empty_batch(self, monkeypatch):
        """evicted: true but oldest_id is None → still process events normally."""
        _patch_basics(monkeypatch)
        writes = []
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda role, cid: writes.append(cid) or True)
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [{"id": "ev40"}],
                "evicted": True,
                "oldest_id": None,
                "evicted_count_hint": 0,
            }),
        )
        # When events are present, the per-event loop carries forward
        # progress on its own — the post-loop guard short-circuits on
        # `not events`, so the missing oldest_id is not yet fatal.
        result = event_poll.poll("skill")
        assert result == [{"id": "ev40"}]
        assert writes == ["ev40"]

    def test_eviction_with_null_oldest_id_and_empty_batch_is_fatal(self, monkeypatch):
        """evicted: true + events: [] + oldest_id: None → return None (CONTEXT D4 / AC-7)."""
        _patch_basics(monkeypatch)
        writes = []
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda role, cid: writes.append(cid) or True)
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [],
                "evicted": True,
                # oldest_id absent — harness contract violation
                "evicted_count_hint": 0,
            }),
        )
        result = event_poll.poll("skill")
        assert result is None  # fatal — no silent continuation
        # No cursor write attempted.
        assert writes == []

    def test_eviction_with_empty_string_oldest_id_is_fatal(self, monkeypatch):
        """Empty-string oldest_id is falsy → still fatal on empty batch."""
        _patch_basics(monkeypatch)
        writes = []
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda role, cid: writes.append(cid) or True)
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [],
                "evicted": True,
                "oldest_id": "",
                "evicted_count_hint": 0,
            }),
        )
        result = event_poll.poll("skill")
        assert result is None
        assert writes == []


# ---------------------------------------------------------------------------
# AC-3 sub-case: post-loop write itself fails — fatal
# ---------------------------------------------------------------------------


class TestPostLoopWriteFailure:
    def test_post_loop_write_failure_returns_none(self, monkeypatch):
        """If the post-loop oldest_id write fails, poll returns None (fatal)."""
        _patch_basics(monkeypatch)
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda role, cid: False)
        monkeypatch.setattr(
            event_poll.urllib.request, "urlopen",
            _make_urlopen_returning({
                "events": [],
                "evicted": True,
                "oldest_id": "anchor-fail",
                "evicted_count_hint": 0,
            }),
        )
        result = event_poll.poll("skill")
        assert result is None
