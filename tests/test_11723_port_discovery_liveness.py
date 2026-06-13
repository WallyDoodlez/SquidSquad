"""Tests for #11723 — liveness-aware harness port discovery.

A test harness distributes its ephemeral port into real clones via
`harness._deferred_init`; after it dies, that dead port lingers in the clone's
`.harness-port`. The pre-#11723 discovery trusted the file blindly, so a dead
port stranded the agent in loop mode (boot probe fails) or killed a live
event-mode Monitor (event_poll polls the dead port and exits) — the root cause
of #11586.

The fix: `_discover_port` (and the cycle_pre/cycle_post mirrors) now returns the
first candidate that is actually LISTENING, skipping a dead port-file value and
falling through to the default. These tests pin that behavior on
event_poll._discover_port (the representative copy).
"""

import socket
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import event_poll  # noqa: E402


def _free_dead_port():
    """Bind then close a socket → its port is now free (nothing listening)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _LiveServer:
    """Context manager: a listening TCP socket on 127.0.0.1, yields its port."""

    def __enter__(self):
        self._s = socket.socket()
        self._s.bind(("127.0.0.1", 0))
        self._s.listen(1)
        return self._s.getsockname()[1]

    def __exit__(self, *_):
        self._s.close()


# --- _port_is_live -------------------------------------------------------

def test_port_is_live_true_for_listening_port():
    with _LiveServer() as port:
        assert event_poll._port_is_live(port) is True


def test_port_is_live_false_for_dead_port():
    assert event_poll._port_is_live(_free_dead_port()) is False


def test_port_is_live_false_for_garbage():
    assert event_poll._port_is_live("not-a-port") is False
    assert event_poll._port_is_live(None) is False


# --- _discover_port ------------------------------------------------------

def _isolate(monkeypatch, tmp_path, file_port):
    """Point SQUID_DIR at an isolated tmp dir (optionally with a .harness-port)
    and REPO_ROOT at a deep tmp path so the parent-walk finds nothing real."""
    squid = tmp_path / "squid"
    squid.mkdir()
    if file_port is not None:
        (squid / ".harness-port").write_text(str(file_port), encoding="utf-8")
    monkeypatch.setattr(event_poll, "SQUID_DIR", squid)
    # deep, parentless-of-.squidsquad repo root so the 5-level walk is inert
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    monkeypatch.setattr(event_poll, "REPO_ROOT", deep)


def test_discover_returns_live_file_port(monkeypatch, tmp_path):
    with _LiveServer() as port:
        _isolate(monkeypatch, tmp_path, file_port=port)
        assert event_poll._discover_port() == port


def test_discover_skips_dead_file_port_and_falls_to_live_default(monkeypatch, tmp_path):
    """THE FIX: a dead .harness-port is skipped; discovery falls through to the
    (live) default instead of stranding the agent."""
    with _LiveServer() as live_default:
        _isolate(monkeypatch, tmp_path, file_port=_free_dead_port())
        monkeypatch.setattr(event_poll, "_HARNESS_DEFAULT_PORT", live_default)
        assert event_poll._discover_port() == live_default


def test_discover_returns_default_when_nothing_listening(monkeypatch, tmp_path):
    """Harness genuinely down: dead file-port + dead default → return the
    default so the caller's own probe fails cleanly and selects loop mode."""
    dead_default = _free_dead_port()
    _isolate(monkeypatch, tmp_path, file_port=_free_dead_port())
    monkeypatch.setattr(event_poll, "_HARNESS_DEFAULT_PORT", dead_default)
    assert event_poll._discover_port() == dead_default


def test_discover_missing_file_uses_live_default(monkeypatch, tmp_path):
    """No .harness-port at all → use the (live) default, unchanged from #11601."""
    with _LiveServer() as live_default:
        _isolate(monkeypatch, tmp_path, file_port=None)
        monkeypatch.setattr(event_poll, "_HARNESS_DEFAULT_PORT", live_default)
        assert event_poll._discover_port() == live_default
