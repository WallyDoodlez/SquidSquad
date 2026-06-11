"""Unit tests for event_poll.py — agent's event-stream wake signal (#8915).

Model B (#11329): event_poll is a pure NUDGE emitter. It does NOT advance
the cursor (the agent owns ack-cursor) and does NOT emit event payloads —
it writes a single literal `NUDGE\n` per new batch. The harness, port
discovery, and filesystem are all stubbed; no test reaches real network or
touches the repo's `.squidsquad/` tree.
"""

import json
import sys
import urllib.error
from pathlib import Path

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
      - a dict                  → 200 with that exact body (for evicted etc.)
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
        if isinstance(item, dict):
            return _StubResponse(json.dumps(item))
        body = json.dumps({"events": item})
        return _StubResponse(body)

    return _fake, calls


@pytest.fixture
def stub_port(monkeypatch):
    monkeypatch.setattr(event_poll, "_discover_port", lambda: 9999)
    return 9999


@pytest.fixture
def no_sleep():
    def _noop(_):
        pass
    return _noop


def _nudge_lines(captured_out):
    return [ln for ln in captured_out.split("\n") if ln]


# ---------------------------------------------------------------------------
# Nudge emission — the core model-B contract
# ---------------------------------------------------------------------------


class TestNudgeEmission:
    def test_event_poll_emits_nudge_not_json(
        self, monkeypatch, stub_port, capsys, no_sleep,
    ):
        """A batch of events produces exactly ONE `NUDGE` line — never the
        event payloads (model B: the nudge carries no payload)."""
        events = [{"id": "e1", "n": 1}, {"id": "e2", "n": 2},
                  {"id": "e3", "n": 3}]
        fake, _ = _make_urlopen([events])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        lines = _nudge_lines(capsys.readouterr().out)
        assert lines == ["NUDGE"]
        # No event payload leaked to stdout.
        assert "e1" not in "".join(lines)

    def test_event_poll_one_nudge_per_batch_regardless_of_count(
        self, monkeypatch, stub_port, capsys, no_sleep,
    ):
        events = [{"id": f"e{i}"} for i in range(10)]
        fake, _ = _make_urlopen([events])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        assert _nudge_lines(capsys.readouterr().out) == ["NUDGE"]

    def test_event_poll_empty_response_yields_no_nudge(
        self, monkeypatch, stub_port, capsys, no_sleep,
    ):
        fake, _ = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events, next_since = event_poll.poll("skill", sleep=no_sleep)
        assert capsys.readouterr().out == ""
        assert events == []

    def test_nudge_is_flushed(
        self, monkeypatch, stub_port, no_sleep,
    ):
        import builtins
        captured_kwargs = []
        real_print = builtins.print

        def _spy(*args, **kwargs):
            captured_kwargs.append((args, kwargs.copy()))
            return real_print(*args, **kwargs)

        monkeypatch.setattr(builtins, "print", _spy)
        fake, _ = _make_urlopen([[{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        nudge_calls = [(a, kw) for a, kw in captured_kwargs
                       if a and a[0] == "NUDGE"
                       and kw.get("file") is not sys.stderr]
        assert len(nudge_calls) == 1
        assert nudge_calls[0][1].get("flush") is True


# ---------------------------------------------------------------------------
# Cursor independence — event_poll never touches the cursor
# ---------------------------------------------------------------------------


class TestEventPollDoesNotTouchCursor:
    """Model B: the harness owns the cursor (advanced by the agent's
    ack-cursor posts). event_poll must NOT write working-state.md, must NOT
    POST ack-cursor, and the cursor-writing helpers must no longer exist."""

    def test_no_cursor_write_helpers_remain(self):
        for gone in ("_write_cursor_atomic", "_read_cursor_from_working_state",
                     "_resolve_cursor", "_working_state_path",
                     "_CURSOR_LINE_PREFIX"):
            assert not hasattr(event_poll, gone), (
                f"event_poll.{gone} should be removed in the model-B migration"
            )

    def test_poll_does_not_write_working_state(
        self, monkeypatch, stub_port, tmp_path, no_sleep,
    ):
        squid = tmp_path / ".squidsquad"
        (squid / "skill").mkdir(parents=True)
        ws = squid / "skill" / "working-state.md"
        ws.write_text("# Working State\n\n- **Task**: none\n", encoding="utf-8")
        monkeypatch.setattr(event_poll, "SQUID_DIR", squid)
        before = ws.read_text(encoding="utf-8")

        fake, _ = _make_urlopen([[{"id": "e1"}, {"id": "e2"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)

        assert ws.read_text(encoding="utf-8") == before
        assert "Last Processed Event ID" not in ws.read_text(encoding="utf-8")

    def test_poll_makes_no_post_requests(
        self, monkeypatch, stub_port, no_sleep,
    ):
        """event_poll only ever issues GETs — the ack-cursor POST is the
        agent's job, not the poller's."""
        methods = []

        def _fake(req, timeout=None):
            methods.append(req.get_method())
            return _StubResponse(json.dumps({"events": [{"id": "e1"}]}))

        monkeypatch.setattr(event_poll.urllib.request, "urlopen", _fake)
        event_poll.poll("skill", sleep=no_sleep)
        assert methods == ["GET"]


# ---------------------------------------------------------------------------
# High-water-mark advancement (local, in-memory — NOT the cursor)
# ---------------------------------------------------------------------------


class TestHighWaterMark:
    def test_next_since_is_newest_event_id(
        self, monkeypatch, stub_port, no_sleep,
    ):
        fake, _ = _make_urlopen([[{"id": "e1"}, {"id": "e2"}, {"id": "e3"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        _, next_since = event_poll.poll("skill", sleep=no_sleep)
        assert next_since == "e3"

    def test_next_since_unchanged_when_no_events(
        self, monkeypatch, stub_port, no_sleep,
    ):
        fake, _ = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        _, next_since = event_poll.poll("skill", since="seed", sleep=no_sleep)
        assert next_since == "seed"

    def test_newest_id_skips_idless_trailing_events(self):
        events = [{"id": "e1"}, {"id": "e2"}, {"no_id": True}]
        assert event_poll._newest_id(events) == "e2"

    def test_newest_id_empty_when_no_anchorable_id(self):
        assert event_poll._newest_id([{"no_id": True}, "junk"]) == ""

    def test_wait_loop_advances_since_across_iterations(self, monkeypatch):
        """--wait passes the previous batch's hwm as the next `since`."""
        seen_since = []

        def _fake_poll(role, since=None, **kwargs):
            seen_since.append(since)
            if len(seen_since) == 1:
                return [{"id": "e1"}], "e1"
            if len(seen_since) == 2:
                return [{"id": "e9"}], "e9"
            return None  # terminate the loop deterministically

        monkeypatch.setattr(event_poll, "poll", _fake_poll)
        monkeypatch.setattr(event_poll.time, "sleep", lambda _: None)
        with pytest.raises(SystemExit):
            event_poll.main(["skill", "--wait", "5"])
        assert seen_since == [None, "e1", "e9"]


# ---------------------------------------------------------------------------
# Eviction — event_poll nudges; the AGENT recovers (model B)
# ---------------------------------------------------------------------------


class TestEviction:
    def test_eviction_empty_batch_still_nudges(
        self, monkeypatch, stub_port, capsys, no_sleep,
    ):
        body = {"events": [], "evicted": True, "oldest_id": "old99",
                "evicted_count_hint": 42}
        fake, _ = _make_urlopen([body])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events, next_since = event_poll.poll("skill", since="stale",
                                             sleep=no_sleep)
        out = capsys.readouterr()
        assert _nudge_lines(out.out) == ["NUDGE"]
        # hwm advances past the evicted gap so we don't re-nudge it forever.
        assert next_since == "old99"
        assert "EVICTION" in out.err

    def test_eviction_with_survivors_anchors_on_newest(
        self, monkeypatch, stub_port, capsys, no_sleep,
    ):
        body = {"events": [{"id": "s1"}, {"id": "s2"}], "evicted": True,
                "oldest_id": "old99", "evicted_count_hint": 5}
        fake, _ = _make_urlopen([body])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events, next_since = event_poll.poll("skill", sleep=no_sleep)
        assert _nudge_lines(capsys.readouterr().out) == ["NUDGE"]
        assert next_since == "s2"


# ---------------------------------------------------------------------------
# Retry & backoff math (unchanged from the pre-migration poller)
# ---------------------------------------------------------------------------


class TestRetryAndBackoff:
    def test_event_poll_backoff_doubles_until_cap(self):
        seq = [event_poll._backoff_seconds(i) for i in range(13)]
        assert seq == [1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300, 300, 300]

    def test_event_poll_backoff_resets_on_success(
        self, monkeypatch, stub_port,
    ):
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

    def test_event_poll_retries_on_5xx(self, monkeypatch, stub_port):
        sleeps = []
        http_500 = urllib.error.HTTPError(
            "http://x", 500, "boom", hdrs=None, fp=None,
        )
        http_503 = urllib.error.HTTPError(
            "http://x", 503, "boom", hdrs=None, fp=None,
        )
        fake, _ = _make_urlopen([http_500, http_503, [{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events, _ = event_poll.poll("skill", sleep=sleeps.append)
        assert sleeps == [1, 2]
        assert events and events[0]["id"] == "e1"

    def test_event_poll_retries_on_timeout(self, monkeypatch, stub_port):
        sleeps = []
        fake, _ = _make_urlopen([TimeoutError("slow"), [{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events, _ = event_poll.poll("skill", sleep=sleeps.append)
        assert sleeps == [1]
        assert events == [{"id": "e1"}]

    def test_event_poll_does_not_retry_on_4xx(
        self, monkeypatch, stub_port, capsys,
    ):
        sleeps = []
        http_404 = urllib.error.HTTPError(
            "http://x", 404, "nope", hdrs=None, fp=None,
        )
        fake, calls = _make_urlopen([http_404])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        result = event_poll.poll("skill", sleep=sleeps.append)
        assert result is None
        assert sleeps == []
        assert calls["n"] == 1
        assert "404" in capsys.readouterr().err

    def test_wait_ceiling_returns_none_after_max_failures(
        self, monkeypatch, stub_port,
    ):
        err = urllib.error.URLError("down")
        fake, _ = _make_urlopen([err] * 20)
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        result = event_poll.poll("skill", sleep=lambda _: None,
                                 max_consecutive_failures=10)
        assert result is None


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------


class TestTimeoutHandling:
    def test_event_poll_wait_flag_translates_to_http_timeout(
        self, monkeypatch, stub_port,
    ):
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", http_timeout=5.0, sleep=lambda _: None)
        assert calls["timeouts"][0] == 5.0

    def test_event_poll_default_http_timeout_is_two_seconds(
        self, monkeypatch, stub_port,
    ):
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=lambda _: None)
        assert calls["timeouts"][0] == event_poll._DEFAULT_HTTP_TIMEOUT == 2.0


# ---------------------------------------------------------------------------
# Since seeding + URL building
# ---------------------------------------------------------------------------


class TestSinceSeeding:
    def test_since_arg_seeds_first_poll(
        self, monkeypatch, stub_port, no_sleep,
    ):
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", since="42", target_mode=True, sleep=no_sleep)
        assert "since=42" in calls["urls"][0]

    def test_no_since_param_when_unset(
        self, monkeypatch, stub_port, no_sleep,
    ):
        fake, calls = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        event_poll.poll("skill", sleep=no_sleep)
        assert "since=" not in calls["urls"][0]


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
# Malformed payload resilience (unchanged behavior)
# ---------------------------------------------------------------------------


class TestMalformedHarnessPayload:
    def test_non_dict_event_skipped_but_batch_still_nudges(
        self, monkeypatch, stub_port, capsys, no_sleep,
    ):
        fake, _ = _make_urlopen([["not-a-dict", {"id": "e2"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events, next_since = event_poll.poll("skill", sleep=no_sleep)
        out = capsys.readouterr()
        assert _nudge_lines(out.out) == ["NUDGE"]
        assert "malformed event" in out.err
        assert events == [{"id": "e2"}]
        assert next_since == "e2"

    def test_events_field_not_a_list_is_fatal(
        self, monkeypatch, stub_port, capsys, no_sleep,
    ):
        def _bad_events(req):
            return _StubResponse(json.dumps({"events": None}))

        fake, _ = _make_urlopen([_bad_events])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        assert event_poll.poll("skill", sleep=no_sleep) is None
        assert "events" in capsys.readouterr().err

    def test_payload_not_dict_is_fatal(
        self, monkeypatch, stub_port, capsys, no_sleep,
    ):
        def _bad_payload(req):
            return _StubResponse(json.dumps(["not-a-dict"]))

        fake, _ = _make_urlopen([_bad_payload])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        assert event_poll.poll("skill", sleep=no_sleep) is None
        assert "harness payload not an object" in capsys.readouterr().err


class TestMidBodyConnectionDrop:
    def test_incomplete_read_is_retryable(self, monkeypatch, stub_port):
        import http.client
        sleeps = []
        boom = http.client.IncompleteRead(b"truncated")
        fake, _ = _make_urlopen([boom, [{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        events, _ = event_poll.poll("skill", sleep=sleeps.append)
        assert sleeps == [1]
        assert events == [{"id": "e1"}]


# ---------------------------------------------------------------------------
# --wait validation + single-shot exit codes
# ---------------------------------------------------------------------------


class TestWaitValidation:
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


class TestSingleShotExitCodes:
    def test_single_shot_exit_zero_when_events(self, monkeypatch, stub_port):
        fake, _ = _make_urlopen([[{"id": "e1"}]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        with pytest.raises(SystemExit) as exc:
            event_poll.main(["skill"])
        assert exc.value.code == 0

    def test_single_shot_exit_one_when_empty(self, monkeypatch, stub_port):
        fake, _ = _make_urlopen([[]])
        monkeypatch.setattr(event_poll.urllib.request, "urlopen", fake)
        with pytest.raises(SystemExit) as exc:
            event_poll.main(["skill"])
        assert exc.value.code == 1

    def test_single_shot_exit_two_on_fatal(self, monkeypatch):
        monkeypatch.setattr(event_poll, "_discover_port", lambda: None)
        with pytest.raises(SystemExit) as exc:
            event_poll.main(["skill"])
        assert exc.value.code == 2
