"""Tests for #9742 — event_poll.py --wait retry ceiling.

Before #9742, ``poll()`` retried transient connection failures forever, so a
sustained harness loss left Monitor wedged indefinitely and prevented the
harness auto-reboot path from kicking in. #9742 caps consecutive transient
failures at ``_WAIT_MAX_CONSECUTIVE_FAILURES`` (10) for ``--wait`` mode while
preserving the existing unlimited-retry behavior for single-shot mode.
"""

import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import event_poll


@pytest.fixture
def stub_port(monkeypatch):
    monkeypatch.setattr(event_poll, "_discover_port", lambda: 7373)


class TestRetryCeiling:
    """``poll(max_consecutive_failures=N)`` returns None after N transient errors."""

    def test_returns_none_after_max_consecutive_failures(self, monkeypatch, stub_port):
        """10 transient errors in a row ⇒ poll returns None."""
        sleeps = []
        boom = urllib.error.URLError("connection refused")

        def fake_urlopen(req, timeout=None):
            raise boom

        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake_urlopen)
        result = event_poll.poll(
            "skill", sleep=sleeps.append, max_consecutive_failures=10
        )
        assert result is None
        # 10 failed attempts → 9 sleeps between them (no sleep after the
        # final ceiling-trigger attempt because we return immediately).
        assert len(sleeps) == 9

    def test_single_success_resets_counter(self, monkeypatch, stub_port):
        """A successful poll between transient errors does NOT trip the ceiling."""
        # 9 failures, then success, then 9 more failures → poll() succeeds twice.
        boom = urllib.error.URLError("connection refused")
        responses = [boom] * 9 + [_make_ok_response()]

        call_count = {"n": 0}

        def fake_urlopen(req, timeout=None):
            call_count["n"] += 1
            r = responses[call_count["n"] - 1]
            if isinstance(r, Exception):
                raise r
            return r

        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake_urlopen)
        events, _ = event_poll.poll(
            "skill", sleep=lambda _: None, max_consecutive_failures=10
        )
        # 9 failures + 1 success = 10 calls; 9 retries < 10 = ceiling not hit.
        assert events == []
        assert call_count["n"] == 10

    def test_default_unlimited_retries_preserved(self, monkeypatch, stub_port):
        """``max_consecutive_failures=None`` (default) preserves pre-#9742 behavior."""
        boom = urllib.error.URLError("boom")
        # Generate 20 failures then a success — without a ceiling poll() must
        # ride all 20 retries through to the success.
        responses = [boom] * 20 + [_make_ok_response()]
        call_count = {"n": 0}

        def fake_urlopen(req, timeout=None):
            call_count["n"] += 1
            r = responses[call_count["n"] - 1]
            if isinstance(r, Exception):
                raise r
            return r

        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake_urlopen)
        events, _ = event_poll.poll("skill", sleep=lambda _: None)  # no ceiling
        assert events == []
        assert call_count["n"] == 21  # 20 failures + 1 success

    def test_ceiling_value_constant(self):
        """``_WAIT_MAX_CONSECUTIVE_FAILURES`` is 10 per CONTEXT-9742 D2."""
        assert event_poll._WAIT_MAX_CONSECUTIVE_FAILURES == 10

    def test_ceiling_message_includes_failure_count(self, monkeypatch, stub_port, capsys):
        boom = urllib.error.URLError("connection refused")
        monkeypatch.setattr(event_poll.urllib.request, "urlopen",
                            lambda req, timeout=None: (_ for _ in ()).throw(boom))
        result = event_poll.poll("skill", sleep=lambda _: None,
                                 max_consecutive_failures=10)
        assert result is None
        err = capsys.readouterr().err
        assert "10 consecutive" in err
        assert "giving up" in err

    def test_non_retryable_error_returns_none_immediately(self, monkeypatch, stub_port):
        """A 4xx HTTP error is not retryable — return None before reaching the ceiling."""
        not_retryable = urllib.error.HTTPError(
            "http://x", 404, "Not Found", {}, None,
        )

        def fake_urlopen(req, timeout=None):
            raise not_retryable

        sleeps = []
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake_urlopen)
        result = event_poll.poll(
            "skill", sleep=sleeps.append, max_consecutive_failures=10
        )
        assert result is None
        # Non-retryable: zero retries, zero sleeps.
        assert sleeps == []


class TestMainWaitModePassesCeiling:
    """``main()`` in --wait mode passes the ceiling so sustained outages exit."""

    def test_wait_mode_passes_max_consecutive_failures(self, monkeypatch, tmp_path):
        captured_kwargs = {}

        def fake_poll(role, **kwargs):
            captured_kwargs.update(kwargs)
            # Return None so main() exits without looping.
            return None

        monkeypatch.setattr(event_poll, "poll", fake_poll)
        with pytest.raises(SystemExit) as exc:
            event_poll.main(["skill", "--wait", "5"])
        assert exc.value.code == 2
        assert captured_kwargs.get("max_consecutive_failures") == 10

    def test_single_shot_mode_does_not_pass_ceiling(self, monkeypatch):
        """Single-shot mode uses the default (unlimited) behavior."""
        captured_kwargs = {}

        def fake_poll(role, **kwargs):
            captured_kwargs.update(kwargs)
            return [], ""

        monkeypatch.setattr(event_poll, "poll", fake_poll)
        with pytest.raises(SystemExit) as exc:
            event_poll.main(["skill"])  # no --wait
        # No events → exit 1; with events would be 0.
        assert exc.value.code == 1
        # Single-shot must NOT pass the ceiling — preserves pre-#9742 behavior.
        assert "max_consecutive_failures" not in captured_kwargs


def _make_ok_response():
    """Build a urlopen context manager returning an empty events payload."""
    resp = MagicMock()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=None)
    resp.read = MagicMock(return_value=b'{"events": [], "evicted": false}')
    return resp
