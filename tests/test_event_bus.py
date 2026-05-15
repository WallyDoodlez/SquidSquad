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
        assert len(evt["id"]) == 8
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
    """Tests for _generate_id() function."""

    def test_produces_8_char_hex(self):
        """ID is exactly 8 hex characters."""
        result = event_bus._generate_id("cycle-start", "skill", "2026-05-01T18:00:00", {})
        assert len(result) == 8
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        """Same inputs produce same ID."""
        a = event_bus._generate_id("cycle-start", "skill", "2026-05-01T18:00:00", {})
        b = event_bus._generate_id("cycle-start", "skill", "2026-05-01T18:00:00", {})
        assert a == b

    def test_different_inputs_different_ids(self):
        """Different inputs produce different IDs."""
        a = event_bus._generate_id("cycle-start", "skill", "2026-05-01T18:00:00", {})
        b = event_bus._generate_id("cycle-end", "skill", "2026-05-01T18:00:00", {})
        assert a != b


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
