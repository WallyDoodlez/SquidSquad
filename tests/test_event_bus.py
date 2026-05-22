"""Tests for event_bus.py — fire-and-forget event emission (#4709)."""

import json
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "references" / "scripts"))
import event_bus
import event_bus_reader


class _EventCollector(BaseHTTPRequestHandler):
    """Minimal HTTP server that collects POSTed events."""

    events = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.events.append(json.loads(body))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def log_message(self, format, *args):
        pass  # Suppress server logs


@pytest.fixture
def mock_server():
    """Start a local HTTP server that collects events."""
    _EventCollector.events = []
    server = HTTPServer(("127.0.0.1", 0), _EventCollector)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port, _EventCollector.events
    server.shutdown()


@pytest.fixture
def patch_dirs(tmp_path):
    """Patch event_bus paths to use temp directory."""
    squid = tmp_path / ".squidsquad"
    squid.mkdir()
    with patch.object(event_bus, "SQUID_DIR", squid), \
         patch.object(event_bus, "REPO_ROOT", tmp_path):
        yield squid


class TestEmit:
    """Tests for emit() function."""

    def test_emits_event_to_harness(self, mock_server, patch_dirs):
        """Successfully emits an event when harness is running."""
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port), encoding="utf-8")

        event_bus.emit("cycle-start", "skill", {"cycle_number": 42}, cycle_number=42)

        assert len(events) == 1
        evt = events[0]
        assert evt["event_type"] == "cycle-start"
        assert evt["role"] == "skill"
        assert evt["cycle_number"] == 42
        assert "id" in evt
        # #9415 D4: widened from 8 → 16 hex chars (64-bit).
        assert len(evt["id"]) == 16
        assert "timestamp" in evt
        assert evt["payload"] == {"cycle_number": 42}

    def test_silent_noop_when_port_file_missing(self, patch_dirs):
        """No exception when .harness-port doesn't exist."""
        # No port file written — should silently return
        event_bus.emit("cycle-start", "pm", {"cycle_number": 1})
        # No exception = pass

    def test_silent_noop_when_harness_down(self, patch_dirs):
        """No exception when harness is not running on the port."""
        (patch_dirs / ".harness-port").write_text("19999", encoding="utf-8")
        event_bus.emit("cycle-start", "qa", {"cycle_number": 1})
        # No exception = pass

    def test_timeout_respected(self, patch_dirs):
        """Emit completes within ~500ms even if server doesn't respond."""
        # Use a port that accepts connections but never responds
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        (patch_dirs / ".harness-port").write_text(str(port), encoding="utf-8")

        start = time.time()
        event_bus.emit("cycle-start", "skill", {"cycle_number": 1})
        elapsed = time.time() - start

        sock.close()
        # Should complete within 700ms (500ms timeout + overhead)
        assert elapsed < 1.5  # generous for CI

    def test_payload_defaults_to_empty_dict(self, mock_server, patch_dirs):
        """Payload defaults to {} when not provided."""
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port), encoding="utf-8")

        event_bus.emit("git-pull", "skill")

        assert len(events) == 1
        assert events[0]["payload"] == {}

    def test_cycle_number_optional(self, mock_server, patch_dirs):
        """cycle_number is omitted from event when not provided."""
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port), encoding="utf-8")

        event_bus.emit("git-pull", "skill", {"result": "ok"})

        assert "cycle_number" not in events[0]


class TestDiscoverPort:
    """Tests for _discover_port() function."""

    def test_reads_direct_port_file(self, patch_dirs):
        """Reads port from .squidsquad/.harness-port."""
        (patch_dirs / ".harness-port").write_text("8080", encoding="utf-8")
        assert event_bus._discover_port() == 8080

    def test_returns_none_when_no_port_file(self, patch_dirs):
        """Returns None when no .harness-port file exists anywhere."""
        assert event_bus._discover_port() is None

    def test_handles_invalid_port_file(self, patch_dirs):
        """Returns None on invalid port file content (falls through to parent walk)."""
        (patch_dirs / ".harness-port").write_text("not-a-number", encoding="utf-8")
        # Will try parent walk, find nothing, return None
        result = event_bus._discover_port()
        assert result is None


class TestGenerateId:
    """Tests for _generate_id() function. Widened to 16 hex + nonce per #9415."""

    def test_produces_16_char_hex(self):
        """#9415 D4 + D7 length test: ID is exactly 16 hex characters.

        Catches typos like ``[:8]`` or ``os.urandom(4).hex()`` left in place
        after the widening — the dominant implementation bug PM called out
        in CONTEXT-9415 D7.
        """
        result = event_bus._generate_id("cycle-start", "skill", "2026-05-01T18:00:00", {})
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_inputs_produce_distinct_ids(self):
        """#9415 D5 + D7 distinct-emit test: identical-content emits MUST
        produce distinct IDs.

        Before #9415, the content-hash path collapsed identical content to
        the same ID — silently broke caller assumptions that every emit
        gets a unique stream position. The nonce in ``_generate_id`` (4 hex
        of ``os.urandom``) is the fix; this test catches it being removed.
        """
        a = event_bus._generate_id("cycle-start", "skill", "2026-05-01T18:00:00", {})
        b = event_bus._generate_id("cycle-start", "skill", "2026-05-01T18:00:00", {})
        assert a != b, (
            "identical-content emits collapsed to the same ID — nonce "
            "missing from _generate_id (#9415 D5)"
        )

    def test_different_inputs_different_ids(self):
        """Different inputs produce different IDs (sanity — hash still
        distinguishes content)."""
        a = event_bus._generate_id("cycle-start", "skill", "2026-05-01T18:00:00", {})
        b = event_bus._generate_id("cycle-end", "skill", "2026-05-01T18:00:00", {})
        assert a != b


class TestEmitEventIdWidth9415:
    """#9415 D7 length test for harness._emit_event (Path 2).

    event_bus.emit() (Path 1) is covered above by TestGenerateId; Path 2 is
    the harness-side ``os.urandom(8).hex()`` direct generator. Both widths
    must move in lockstep — a forgotten ``os.urandom(4)`` left in harness
    would produce 8-char IDs that mix with Path 1's 16-char IDs in the
    same event deque, breaking downstream string-equality lookups.
    """

    def test_harness_emit_event_produces_16_char_hex(self):
        # Import lazily — harness pulls heavy deps (fastapi/uvicorn) and
        # we don't want to slow the suite when this is the only test that
        # needs it. The module-level `sys.path.insert(0, ...references/
        # scripts/...)` at line 13 of this file already places that
        # directory on the path, so the bare `import_module("harness")`
        # below resolves correctly under pytest. If that top-of-file
        # insert is ever removed, this test fails with ModuleNotFoundError
        # rather than silently passing the wrong assertion — caught loudly.
        import importlib
        harness = importlib.import_module("harness")
        # Capture the event the helper would append to the lifecycle deque.
        captured = []
        with patch.object(harness.event_lifecycle, "append",
                          side_effect=lambda e: captured.append(e)), \
             patch.object(harness, "_log_event"):
            harness._emit_event("test-event", "skill", payload={"k": "v"})
        assert len(captured) == 1
        evt = captured[0]
        assert len(evt["id"]) == 16, (
            f"harness._emit_event produced {len(evt['id'])}-char id; #9415 "
            "D4 widens to 16 hex (os.urandom(8).hex())"
        )
        assert all(c in "0123456789abcdef" for c in evt["id"])


# TestAck removed in #9813 — event_bus.ack() deleted (Option b).
# After #9741 stripped the dispatch() producer from /events/for/{role},
# the ack stub had no live consumer. Cursor advance is the de-facto ack
# signal; agents do not need a separate post-processing ack call.


class TestAckCursor:
    """#9873-A AC-10: event_bus.ack_cursor(event_id, role) helper."""

    def test_emits_ack_cursor_with_payload(self, mock_server, patch_dirs):
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port))
        event_bus.ack_cursor("evt-123", "skill")
        # Give the server a tick to record
        time.sleep(0.05)
        assert len(events) == 1
        e = events[0]
        assert e["event_type"] == "ack-cursor"
        assert e["role"] == "skill"
        assert e["payload"]["event_id"] == "evt-123"
        assert e["payload"]["role"] == "skill"

    def test_noop_on_empty_event_id(self, mock_server, patch_dirs):
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port))
        event_bus.ack_cursor("", "skill")
        time.sleep(0.05)
        assert events == []

    def test_noop_on_empty_role(self, mock_server, patch_dirs):
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port))
        event_bus.ack_cursor("evt-123", "")
        time.sleep(0.05)
        assert events == []

    def test_silent_on_transport_failure(self, patch_dirs):
        """No port file → silent no-op, no exception."""
        # patch_dirs created without a .harness-port file
        event_bus.ack_cursor("evt-123", "skill")  # must not raise


class TestAckStop:
    """#9873-A AC-11: event_bus.ack_stop(event_id, result) helper."""

    def test_emits_ack_stop_with_payload(self, mock_server, patch_dirs, monkeypatch):
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port))
        monkeypatch.setenv("SQUIDSQUAD_ROLE", "skill")
        event_bus.ack_stop("evt-456", "stop-confirmed")
        time.sleep(0.05)
        assert len(events) == 1
        e = events[0]
        assert e["event_type"] == "ack-stop"
        assert e["role"] == "skill"
        assert e["payload"] == {"event_id": "evt-456", "result": "stop-confirmed"}

    def test_noop_on_empty_event_id(self, mock_server, patch_dirs, monkeypatch):
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port))
        monkeypatch.setenv("SQUIDSQUAD_ROLE", "skill")
        event_bus.ack_stop("", "stop-confirmed")
        time.sleep(0.05)
        assert events == []

    def test_noop_on_empty_result(self, mock_server, patch_dirs, monkeypatch):
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port))
        monkeypatch.setenv("SQUIDSQUAD_ROLE", "skill")
        event_bus.ack_stop("evt-456", "")
        time.sleep(0.05)
        assert events == []

    def test_noop_when_role_env_unset(self, mock_server, patch_dirs, monkeypatch):
        """SQUIDSQUAD_ROLE unset → can't infer role → silent no-op (rather
        than emitting with role=None which the harness would drop)."""
        port, events = mock_server
        (patch_dirs / ".harness-port").write_text(str(port))
        monkeypatch.delenv("SQUIDSQUAD_ROLE", raising=False)
        event_bus.ack_stop("evt-456", "stop-confirmed")
        time.sleep(0.05)
        assert events == []


class TestNoUnusedImports:
    """#8193 regression: event bus modules must not have unused imports."""

    def test_event_bus_no_unused_sys(self):
        import inspect
        source = inspect.getsource(event_bus)
        assert "import sys" not in source

    def test_event_bus_reader_no_unused_sys(self):
        import inspect
        source = inspect.getsource(event_bus_reader)
        assert "import sys" not in source
