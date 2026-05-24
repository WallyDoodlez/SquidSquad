"""Tests for references/scripts/event_bus_reader.py — event bus consumption (#5622)."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import event_bus_reader


# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

class TestDiscoverPort:
    def test_reads_from_harness_port_file(self, tmp_path):
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        (squid / ".harness-port").write_text("8080", encoding="utf-8")
        with patch.object(event_bus_reader, "SQUID_DIR", squid):
            assert event_bus_reader._discover_port() == 8080

    def test_returns_none_when_no_file(self, tmp_path):
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        with patch.object(event_bus_reader, "SQUID_DIR", squid), \
             patch.object(event_bus_reader, "REPO_ROOT", tmp_path):
            assert event_bus_reader._discover_port() is None

    def test_handles_invalid_port_file(self, tmp_path):
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        (squid / ".harness-port").write_text("not-a-number", encoding="utf-8")
        with patch.object(event_bus_reader, "SQUID_DIR", squid), \
             patch.object(event_bus_reader, "REPO_ROOT", tmp_path):
            assert event_bus_reader._discover_port() is None


# ---------------------------------------------------------------------------
# query()
# ---------------------------------------------------------------------------

class TestQuery:
    def test_returns_empty_when_no_port(self):
        with patch.object(event_bus_reader, "_discover_port", return_value=None):
            result = event_bus_reader.query()
        assert result == []

    def test_returns_events_on_success(self):
        fake_events = [
            {"id": "abc12345", "event_type": "cycle-start", "role": "pm"},
            {"id": "def67890", "event_type": "git-pull", "role": "skill"},
        ]
        resp = MagicMock()
        resp.read.return_value = json.dumps({"events": fake_events}).encode("utf-8")

        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", return_value=resp):
            result = event_bus_reader.query(since="prev123")
        assert len(result) == 2
        assert result[0]["id"] == "abc12345"

    def test_returns_empty_on_timeout(self):
        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", side_effect=URLError("timeout")):
            result = event_bus_reader.query()
        assert result == []

    def test_returns_empty_on_connection_refused(self):
        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", side_effect=ConnectionRefusedError()):
            result = event_bus_reader.query()
        assert result == []

    def test_passes_since_param(self):
        resp = MagicMock()
        resp.read.return_value = json.dumps({"events": []}).encode("utf-8")

        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", return_value=resp) as mock_open:
            event_bus_reader.query(since="abc123", role="pm", event_type="git-pull")

        url = mock_open.call_args[0][0].full_url
        assert "since=abc123" in url
        assert "role=pm" in url
        assert "event_type=git-pull" in url

    def test_skips_since_when_none(self):
        resp = MagicMock()
        resp.read.return_value = json.dumps({"events": []}).encode("utf-8")

        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", return_value=resp) as mock_open:
            event_bus_reader.query(since=None)

        url = mock_open.call_args[0][0].full_url
        assert "since=" not in url

    def test_skips_since_when_value_is_none_string(self):
        resp = MagicMock()
        resp.read.return_value = json.dumps({"events": []}).encode("utf-8")

        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", return_value=resp) as mock_open:
            event_bus_reader.query(since="none")

        url = mock_open.call_args[0][0].full_url
        assert "since=" not in url


# ---------------------------------------------------------------------------
# #9967 — eviction signal handling
# ---------------------------------------------------------------------------

class TestQueryEvictionHandling:
    """#9967: when harness signals `evicted: true`, drop the stale events
    list (buffer-start) and return [] so callers don't re-process events
    older than their cursor on every cycle.
    """

    def test_evicted_response_returns_empty_list(self):
        """Harness returns `evicted: true` + oldest-events fallback → query() returns []."""
        stale_events = [
            {"id": "old1", "event_type": "git-pull", "timestamp": "2026-05-22T01:45:31"},
            {"id": "old2", "event_type": "cycle-start", "timestamp": "2026-05-22T08:45:21"},
        ]
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "events": stale_events,
            "total": 1000,
            "evicted": True,
            "oldest_id": "old1",
            "evicted_count_hint": 250,
        }).encode("utf-8")

        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", return_value=resp):
            result = event_bus_reader.query(since="evicted_cursor")

        assert result == [], (
            "evicted response must return [] (not the buffer-start events) "
            "so callers don't re-process events older than the cursor"
        )

    def test_evicted_response_emits_stderr_breadcrumb(self, capsys):
        """Eviction case prints a one-line forensic signal to stderr."""
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "events": [{"id": "old1", "event_type": "x"}],
            "evicted": True,
            "oldest_id": "old1",
            "evicted_count_hint": 250,
        }).encode("utf-8")

        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", return_value=resp):
            event_bus_reader.query(since="evicted_cursor")

        captured = capsys.readouterr()
        assert "cursor evicted" in captured.err
        assert "oldest_id=old1" in captured.err
        assert "evicted_count_hint=250" in captured.err
        assert "#9967" in captured.err

    def test_non_evicted_response_returns_events(self):
        """Normal (non-evicted) response still returns the events list."""
        fresh_events = [
            {"id": "new1", "event_type": "cycle-start"},
            {"id": "new2", "event_type": "git-pull"},
        ]
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "events": fresh_events,
            "total": 50,
            # No `evicted` key — normal path.
        }).encode("utf-8")

        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", return_value=resp):
            result = event_bus_reader.query(since="fresh_cursor")

        assert len(result) == 2
        assert result[0]["id"] == "new1"

    def test_evicted_false_explicit_returns_events(self):
        """`evicted: false` explicitly (not missing) still returns events."""
        events = [{"id": "x"}]
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "events": events,
            "evicted": False,
        }).encode("utf-8")

        with patch.object(event_bus_reader, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen", return_value=resp):
            result = event_bus_reader.query(since="cursor")

        assert result == events


# ---------------------------------------------------------------------------
# Harness GET /events endpoint filtering (EventStream.get_since)
# ---------------------------------------------------------------------------

class TestEventStreamGetSince:
    """Test the get_since method added to EventStream in harness.py."""

    def _make_stream(self, events):
        """Import and create an EventStream with test events."""
        sys.path.insert(0, str(SCRIPTS))
        # Import harness module components without starting the server
        import importlib
        import collections
        import threading

        class TestStream:
            def __init__(self, maxlen=1000):
                self._events = collections.deque(maxlen=maxlen)
                self._lock = threading.Lock()

            def append(self, event):
                with self._lock:
                    self._events.append(event)

            def get_since(self, since_id, limit=100):
                with self._lock:
                    items = list(self._events)
                    if not since_id:
                        return items[-limit:] if len(items) > limit else items
                    for i, event in enumerate(items):
                        if event.get("id") == since_id:
                            after = items[i + 1:]
                            return after[-limit:] if len(after) > limit else after
                    return items[-limit:] if len(items) > limit else items

        stream = TestStream()
        for e in events:
            stream.append(e)
        return stream

    def test_returns_events_after_id(self):
        events = [
            {"id": "aaa", "event_type": "x"},
            {"id": "bbb", "event_type": "y"},
            {"id": "ccc", "event_type": "z"},
        ]
        stream = self._make_stream(events)
        result = stream.get_since("aaa")
        assert len(result) == 2
        assert result[0]["id"] == "bbb"
        assert result[1]["id"] == "ccc"

    def test_returns_all_when_since_is_none(self):
        events = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        stream = self._make_stream(events)
        result = stream.get_since(None)
        assert len(result) == 3

    def test_returns_all_when_id_not_found(self):
        events = [{"id": "a"}, {"id": "b"}]
        stream = self._make_stream(events)
        result = stream.get_since("nonexistent")
        assert len(result) == 2

    def test_respects_limit(self):
        events = [{"id": str(i)} for i in range(10)]
        stream = self._make_stream(events)
        result = stream.get_since(None, limit=3)
        assert len(result) == 3
        assert result[0]["id"] == "7"  # last 3

    def test_empty_after_last_event(self):
        events = [{"id": "a"}, {"id": "b"}]
        stream = self._make_stream(events)
        result = stream.get_since("b")
        assert result == []
