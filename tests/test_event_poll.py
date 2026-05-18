"""Unit tests for event_poll.py — agent's event-stream listener (#8915).

Backed by TEST-PLAN-8694.md §3 (Unit Tests). Each test name encodes the
behavior tested. The harness, port discovery, and filesystem are all
stubbed; no test reaches real network or touches the repo's
`.squidsquad/` tree.
"""

import io
import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import event_poll  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubResponse:
    def __init__(self, body):
        self._body = body.encode("utf-8") if isinstance(body, str) else body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _make_urlopen(events_seq, status_seq=None):
    """Return a fake urlopen that yields the next response per call.

    `events_seq` items can be:
      - a list[dict]            → 200 with {"events": [...]}
      - an exception instance   → raised
      - a callable              → called (allows custom assertions on req)
    """
    calls = {"n": 0, "urls": [], "timeouts": []}
    seq = list(events_seq)

    def _fake(req, timeout=None):
        calls["n"] += 1
        calls["urls"].append(req.full_url)
        calls["timeouts"].append(timeout)
        item = seq.pop(0) if seq else []
        if isinstance(item, BaseException):
            raise item
        if callable(item):
            return item(req)
        body = json.dumps({"events": item})
        return _StubResponse(body)

    return _fake, calls


@pytest.fixture
def stub_port(monkeypatch):
    monkeypatch.setattr(event_poll, "_discover_port", lambda: 9999)
    return 9999


@pytest.fixture
def stub_cursor(monkeypatch):
    """Default: no cursor in working-state (so _resolve_cursor returns '')."""
    monkeypatch.setattr(event_poll, "_read_cursor_from_working_state",
                        lambda role: "")
    return None


@pytest.fixture
def captured_cursor_writes(monkeypatch):
    writes = []

    def _record(role, cursor):
        writes.append((role, cursor))
        return True

    monkeypatch.setattr(event_poll, "_write_cursor_atomic", _record)
    return writes


@pytest.fixture
def no_sleep():
    def _noop(_):
        pass
    return _noop


# ---------------------------------------------------------------------------
# §3.1 — cursor parsing
# ---------------------------------------------------------------------------


class TestCursorParsing:
    def test_event_poll_cursor_from_arg(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        no_sleep,
    ):
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", since="42", sleep=no_sleep)
        assert "since=42" in calls["urls"][0]
        assert "role=skill" in calls["urls"][0]

    def test_event_poll_cursor_from_working_state(
        self, monkeypatch, stub_port, captured_cursor_writes, no_sleep,
    ):
        monkeypatch.setattr(event_poll, "_read_cursor_from_working_state",
                            lambda role: "abc123")
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        assert "since=abc123" in calls["urls"][0]

    def test_event_poll_cursor_missing_defaults_to_zero(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        no_sleep, capsys,
    ):
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        # No `since=` param when cursor is empty
        assert "since=" not in calls["urls"][0]
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "skill" in captured.err

    def test_read_cursor_from_working_state_parses_line(self, tmp_path,
                                                        monkeypatch):
        squid = tmp_path / ".squidsquad"
        (squid / "skill").mkdir(parents=True)
        (squid / "skill" / "working-state.md").write_text(
            "# Working State\n\n- **Task**: none\n"
            "- **Last Processed Event ID**: 9d7c2489\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(event_poll, "SQUID_DIR", squid)
        assert event_poll._read_cursor_from_working_state("skill") == "9d7c2489"

    def test_read_cursor_from_working_state_returns_empty_when_missing(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(event_poll, "SQUID_DIR", tmp_path / ".squidsquad")
        assert event_poll._read_cursor_from_working_state("skill") == ""

    def test_read_cursor_handles_corrupted_utf8(self, tmp_path, monkeypatch):
        # Iter-4 review fix: a corrupted working-state.md (non-UTF-8 bytes)
        # must not crash poll() — return empty so default-zero path runs.
        squid = tmp_path / ".squidsquad"
        (squid / "skill").mkdir(parents=True)
        (squid / "skill" / "working-state.md").write_bytes(
            b"# Working State\n\xc3\x28 invalid utf-8\n"
        )
        monkeypatch.setattr(event_poll, "SQUID_DIR", squid)
        assert event_poll._read_cursor_from_working_state("skill") == ""


# ---------------------------------------------------------------------------
# §3.2 — retry & backoff math
# ---------------------------------------------------------------------------


class TestRetryAndBackoff:
    def test_event_poll_backoff_doubles_until_cap(self):
        seq = [event_poll._backoff_seconds(i) for i in range(13)]
        assert seq == [1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300, 300, 300]

    def test_event_poll_backoff_resets_on_success(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
    ):
        # Two separate poll() calls: first fails twice then succeeds; second
        # fails once then succeeds. Second-call's first sleep MUST be 1s (the
        # backoff counter is poll()-local, so it resets across calls).
        sleeps = []
        fake_err = urllib.error.URLError("boom")
        fake1, _ = _make_urlopen([fake_err, fake_err, []])
        fake2, _ = _make_urlopen([fake_err, []])

        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake1)
        event_poll.poll("skill", sleep=sleeps.append)
        first_call_sleeps = list(sleeps)
        sleeps.clear()

        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake2)
        event_poll.poll("skill", sleep=sleeps.append)
        assert first_call_sleeps == [1, 2]
        assert sleeps == [1]

    def test_event_poll_retries_on_5xx(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
    ):
        sleeps = []
        http_500 = urllib.error.HTTPError(
            "http://x", 500, "boom", hdrs=None, fp=None,
        )
        http_503 = urllib.error.HTTPError(
            "http://x", 503, "boom", hdrs=None, fp=None,
        )
        fake, _ = _make_urlopen([http_500, http_503, [{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events = event_poll.poll("skill", sleep=sleeps.append)
        assert sleeps == [1, 2]
        assert events and events[0]["id"] == "e1"

    def test_event_poll_retries_on_timeout(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
    ):
        sleeps = []
        fake, _ = _make_urlopen([TimeoutError("slow"), [{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events = event_poll.poll("skill", sleep=sleeps.append)
        assert sleeps == [1]
        assert events == [{"id": "e1"}]

    def test_event_poll_does_not_retry_on_4xx(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        capsys,
    ):
        sleeps = []
        http_404 = urllib.error.HTTPError(
            "http://x", 404, "nope", hdrs=None, fp=None,
        )
        fake, calls = _make_urlopen([http_404])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events = event_poll.poll("skill", sleep=sleeps.append)
        assert events is None
        assert sleeps == []
        assert calls["n"] == 1
        assert "404" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# §3.3 — JSON-line streaming
# ---------------------------------------------------------------------------


class TestJsonLineStreaming:
    def test_event_poll_one_json_line_per_event(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        capsys, no_sleep,
    ):
        events = [{"id": "e1", "n": 1}, {"id": "e2", "n": 2},
                  {"id": "e3", "n": 3}]
        fake, _ = _make_urlopen([events])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        captured = capsys.readouterr()
        lines = [ln for ln in captured.out.split("\n") if ln]
        assert len(lines) == 3
        parsed = [json.loads(ln) for ln in lines]
        assert parsed == events

    def test_event_poll_flushes_per_event(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        no_sleep,
    ):
        import builtins
        captured_kwargs = []
        real_print = builtins.print

        def _spy(*args, **kwargs):
            captured_kwargs.append(kwargs.copy())
            return real_print(*args, **kwargs)

        monkeypatch.setattr(builtins, "print", _spy)
        fake, _ = _make_urlopen([[{"id": "e1"}, {"id": "e2"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        # Stdout writes pass flush=True; stderr writes do not
        flush_calls = [kw for kw in captured_kwargs
                       if kw.get("flush") is True
                       and kw.get("file") is not sys.stderr]
        assert len(flush_calls) == 2

    def test_event_poll_empty_response_yields_no_lines(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        capsys, no_sleep,
    ):
        fake, _ = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        captured = capsys.readouterr()
        assert captured.out == ""


# ---------------------------------------------------------------------------
# §3.4 — timeout handling
# ---------------------------------------------------------------------------


class TestTimeoutHandling:
    def test_event_poll_wait_flag_translates_to_http_timeout(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
    ):
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", http_timeout=5.0, sleep=lambda _: None)
        assert calls["timeouts"][0] == 5.0

    def test_event_poll_default_http_timeout_is_two_seconds(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
    ):
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=lambda _: None)
        assert calls["timeouts"][0] == event_poll._DEFAULT_HTTP_TIMEOUT == 2.0


# ---------------------------------------------------------------------------
# §3.5 — cursor advancement semantics
# ---------------------------------------------------------------------------


class TestCursorAdvancement:
    def test_event_poll_atomic_cursor_write(self, tmp_path, monkeypatch):
        squid = tmp_path / ".squidsquad"
        (squid / "skill").mkdir(parents=True)
        ws = squid / "skill" / "working-state.md"
        ws.write_text(
            "- **Task**: none\n- **Last Processed Event ID**: old\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(event_poll, "SQUID_DIR", squid)

        seen_replace = {"called": False, "src": None, "dst": None}
        real_replace = Path.replace

        def _spy_replace(self, target):
            seen_replace["called"] = True
            seen_replace["src"] = str(self)
            seen_replace["dst"] = str(target)
            return real_replace(self, target)

        monkeypatch.setattr(Path, "replace", _spy_replace)
        event_poll._write_cursor_atomic("skill", "new-cursor")

        assert seen_replace["called"] is True
        assert seen_replace["src"].endswith(".md.tmp")
        assert seen_replace["dst"].endswith("working-state.md")
        # Final content has new cursor; old cursor replaced in place
        text = ws.read_text(encoding="utf-8")
        assert "Last Processed Event ID**: new-cursor" in text
        assert "old" not in text

    def test_atomic_cursor_write_appends_when_line_absent(self, tmp_path,
                                                          monkeypatch):
        squid = tmp_path / ".squidsquad"
        (squid / "skill").mkdir(parents=True)
        ws = squid / "skill" / "working-state.md"
        ws.write_text("# Working State\n\n- **Task**: none\n",
                      encoding="utf-8")
        monkeypatch.setattr(event_poll, "SQUID_DIR", squid)
        event_poll._write_cursor_atomic("skill", "fresh")
        text = ws.read_text(encoding="utf-8")
        assert "Last Processed Event ID**: fresh" in text

    def test_atomic_cursor_write_creates_file_when_missing(self, tmp_path,
                                                            monkeypatch):
        squid = tmp_path / ".squidsquad"
        monkeypatch.setattr(event_poll, "SQUID_DIR", squid)
        event_poll._write_cursor_atomic("skill", "brand-new")
        ws = squid / "skill" / "working-state.md"
        assert ws.exists()
        assert "Last Processed Event ID**: brand-new" in ws.read_text(
            encoding="utf-8")

    def test_event_poll_cursor_advances_per_event_not_per_batch(
        self, monkeypatch, stub_port, stub_cursor, no_sleep,
    ):
        import builtins
        ops = []

        def _record_write(role, cursor):
            ops.append(("write", cursor))
            return True

        def _record_print(*args, **kwargs):
            if kwargs.get("file") is sys.stderr:
                return
            line = args[0] if args else ""
            try:
                ops.append(("print", json.loads(line)["id"]))
            except (ValueError, KeyError, TypeError):
                pass

        monkeypatch.setattr(event_poll, "_write_cursor_atomic", _record_write)
        monkeypatch.setattr(builtins, "print", _record_print)
        fake, _ = _make_urlopen([[{"id": "e1"}, {"id": "e2"}, {"id": "e3"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)

        # write e1, print e1, write e2, print e2, write e3, print e3
        assert ops == [
            ("write", "e1"), ("print", "e1"),
            ("write", "e2"), ("print", "e2"),
            ("write", "e3"), ("print", "e3"),
        ]


# ---------------------------------------------------------------------------
# URL building + target mode
# ---------------------------------------------------------------------------


class TestUrlBuilding:
    def test_build_url_default_mode_includes_role_filter(self):
        url = event_poll._build_url(9999, "skill", "42", 50, target_mode=False)
        assert url.startswith("http://127.0.0.1:9999/events?")
        assert "role=skill" in url
        assert "since=42" in url
        assert "limit=50" in url

    def test_build_url_target_mode_uses_for_endpoint(self):
        url = event_poll._build_url(9999, "skill", "42", 50, target_mode=True)
        assert "/events/for/skill?" in url
        assert "since=42" in url
        # role filter not used in target mode (it's in the path)
        assert "role=" not in url

    def test_build_url_omits_since_when_empty(self):
        url = event_poll._build_url(9999, "skill", "", 50, target_mode=False)
        assert "since=" not in url


# ---------------------------------------------------------------------------
# Harness-unreachable handling
# ---------------------------------------------------------------------------


class TestHarnessUnreachable:
    def test_poll_returns_none_when_port_file_missing(self, monkeypatch,
                                                       capsys):
        monkeypatch.setattr(event_poll, "_discover_port", lambda: None)
        assert event_poll.poll("skill", sleep=lambda _: None) is None
        assert "port not found" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Review fixes — cursor-write failure handling + --wait validation
# ---------------------------------------------------------------------------


class TestCursorWriteFailureGatesEmission:
    """Review iter-1 finding 1: silent cursor-write failure caused
    re-delivery loops. Cursor write must (a) log to stderr and (b) gate
    the print so we don't act on an event whose cursor was lost."""

    def test_write_failure_returns_false_and_logs(self, monkeypatch, tmp_path,
                                                   capsys):
        monkeypatch.setattr(event_poll, "SQUID_DIR", tmp_path / ".squidsquad")

        def _boom(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", _boom)
        assert event_poll._write_cursor_atomic("skill", "x") is False
        assert "cursor write failed" in capsys.readouterr().err

    def test_poll_skips_print_when_cursor_write_fails(
        self, monkeypatch, stub_port, stub_cursor, capsys, no_sleep,
    ):
        import builtins
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda r, c: False)
        stdout_lines = []
        real_print = builtins.print

        def _spy(*args, **kwargs):
            if kwargs.get("file") is not sys.stderr:
                stdout_lines.append(args[0] if args else "")
            return real_print(*args, **kwargs)

        monkeypatch.setattr(builtins, "print", _spy)
        fake, _ = _make_urlopen([[{"id": "e1"}, {"id": "e2"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        # First event's cursor advance fails → no events printed at all
        assert stdout_lines == []

    def test_poll_returns_none_when_cursor_fails(
        self, monkeypatch, stub_port, stub_cursor, no_sleep,
    ):
        # Iter-2 review fix: persistent cursor-write failure must surface
        # as fatal (None) so the --wait loop exits with code 2 instead of
        # tight-looping forever at HTTP rate
        monkeypatch.setattr(event_poll, "_write_cursor_atomic",
                            lambda r, c: False)
        fake, _ = _make_urlopen([[{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        assert event_poll.poll("skill", sleep=no_sleep) is None


class TestEventWithoutId:
    """Iter-2 review fix: events missing an `id` cannot advance the cursor,
    so emitting them would cause infinite re-delivery on every poll."""

    def test_event_without_id_is_skipped_with_warning(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        capsys, no_sleep,
    ):
        fake, _ = _make_urlopen([[{"no_id_here": True},
                                  {"id": "e2", "n": 2}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        out = capsys.readouterr()
        lines = [ln for ln in out.out.split("\n") if ln]
        # Only the event with an id is emitted
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == "e2"
        # Warning about the skipped event landed on stderr
        assert "no id" in out.err
        # Cursor only advanced for the valid event
        assert captured_cursor_writes == [("skill", "e2")]

    def test_event_with_empty_id_is_skipped(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        capsys, no_sleep,
    ):
        fake, _ = _make_urlopen([[{"id": ""}, {"id": "e2"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        out = capsys.readouterr()
        lines = [ln for ln in out.out.split("\n") if ln]
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == "e2"
        assert captured_cursor_writes == [("skill", "e2")]


class TestMalformedHarnessPayload:
    """Iter-5 review fix: a malformed harness payload (events not a list, or
    individual events not dicts) must not crash the --wait loop."""

    def test_non_dict_event_is_skipped_with_warning(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        capsys, no_sleep,
    ):
        fake, _ = _make_urlopen([["not-a-dict", {"id": "e2"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        out = capsys.readouterr()
        lines = [ln for ln in out.out.split("\n") if ln]
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == "e2"
        assert "malformed event" in out.err

    def test_events_field_not_a_list_is_fatal(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        capsys, no_sleep,
    ):
        def _bad_events(req):
            return _StubResponse(json.dumps({"events": None}))

        fake, _ = _make_urlopen([_bad_events])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        assert event_poll.poll("skill", sleep=no_sleep) is None
        assert "events" in capsys.readouterr().err

    def test_payload_not_dict_is_fatal(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
        capsys, no_sleep,
    ):
        def _bad_payload(req):
            return _StubResponse(json.dumps(["not-a-dict"]))

        fake, _ = _make_urlopen([_bad_payload])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        assert event_poll.poll("skill", sleep=no_sleep) is None
        assert "harness payload not an object" in capsys.readouterr().err


class TestMidBodyConnectionDrop:
    """Iter-5 review fix: http.client.IncompleteRead (and other
    HTTPException subclasses) escaped the URLError/OSError except clauses
    and crashed the --wait loop. Must now be retried."""

    def test_incomplete_read_is_retryable(
        self, monkeypatch, stub_port, stub_cursor, captured_cursor_writes,
    ):
        import http.client
        sleeps = []
        boom = http.client.IncompleteRead(b"truncated")
        fake, _ = _make_urlopen([boom, [{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events = event_poll.poll("skill", sleep=sleeps.append)
        assert sleeps == [1]
        assert events == [{"id": "e1"}]


class TestSinceWithWaitOneShotSemantics:
    """Iter-3 review fix: in --wait mode, --since must apply only to the
    first iteration; subsequent iterations must read the advanced cursor
    from working-state.md or re-deliver the same events forever."""

    def test_since_resets_to_none_after_first_iteration(self, monkeypatch):
        # Patch poll() to capture the `since` arg and break out of the
        # loop after the second call.
        calls = []

        def _fake_poll(role, since=None, limit=50, target_mode=False,
                       http_timeout=None, sleep=None):
            calls.append(since)
            if len(calls) >= 2:
                # Returning None makes main() sys.exit(2), which we
                # catch below — terminates the test loop deterministically.
                return None
            return [{"id": "e1"}]

        monkeypatch.setattr(event_poll, "poll", _fake_poll)
        monkeypatch.setattr(event_poll.time, "sleep", lambda _: None)

        with pytest.raises(SystemExit):
            event_poll.main(["skill", "--since", "42", "--wait", "5"])

        # First iteration uses the explicit override; second sees None
        # (so poll() reads the advanced cursor from working-state.md).
        assert calls == ["42", None]


class TestWaitValidation:
    """Review iter-1 finding 2: negative --wait crashed time.sleep."""

    def test_main_rejects_zero_wait(self, capsys):
        with pytest.raises(SystemExit) as exc:
            event_poll.main(["skill", "--wait", "0"])
        assert exc.value.code == 2
        assert "must be positive" in capsys.readouterr().err

    def test_main_rejects_negative_wait(self, capsys):
        with pytest.raises(SystemExit) as exc:
            event_poll.main(["skill", "--wait", "-1"])
        assert exc.value.code == 2
        assert "must be positive" in capsys.readouterr().err
