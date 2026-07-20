"""Tests for references/scripts/tracker.py — core tracker functions.

Covers functions not tested by test_tracker_authority.py (which focuses on
role-based transition authority).
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker
import tc_coverage


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


@pytest.fixture(autouse=True)
def _stub_repo_labels(monkeypatch):
    """#13465: create_issue/create_task now consult the repo label taxonomy via
    _repo_labels() (a cached `gh label list`). Stub it to a stable default so the
    create tests never hit real `gh`, stay order-independent (no leaked module
    cache), and see no extra _run_list call — leaving calls[0] the create call."""
    tracker._REPO_LABELS_CACHE = None
    # Pre-#6274.3 reality: the repo defines only the OLD-form role labels. The
    # NEW-form labels (role:verifier/role:worker) do NOT exist yet — modelling
    # them here would mask the #13465 drop path for any dual-role create test.
    monkeypatch.setattr(
        tracker, "_repo_labels",
        lambda: {"role:skill", "role:dm", "role:pm", "role:qa", "role:designer"},
    )
    yield
    tracker._REPO_LABELS_CACHE = None


class TestCheckGh:
    def test_success(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout="ok"),
        )
        assert tracker.check_gh() is True

    def test_failure(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(returncode=1),
        )
        assert tracker.check_gh() is False


class TestCheckGhWriteProbe13574:
    """#13574: check_gh must also verify WRITE capability. A read-only auth
    downgrade (#13570) passes the read check and boots the whole team clean
    while every transition/label/push fails. Only a definitive
    `.permissions.push == false` blocks boot; an inconclusive probe warns and
    falls back to the read check (fail-open on uncertainty)."""

    def _arm(self, monkeypatch, probe_result):
        """Read check (via _run_list) passes; the write probe (via
        _run_list_timeout — a DIFFERENT function, mock both or the real gh
        runs) returns probe_result."""
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                            lambda cmd, **kw: _mock_result(stdout="ok"))
        monkeypatch.setattr(tracker, "_run_list_timeout",
                            lambda cmd, timeout, **kw: probe_result)

    def test_push_true_passes_silently(self, monkeypatch, capsys):
        self._arm(monkeypatch, _mock_result(stdout="true\n"))
        assert tracker.check_gh() is True
        assert "13574" not in capsys.readouterr().err

    def test_push_false_fails_loudly_with_remediation(self, monkeypatch, capsys):
        self._arm(monkeypatch, _mock_result(stdout="false\n"))
        assert tracker.check_gh() is False
        err = capsys.readouterr().err
        assert "WRITE" in err and "#13570" in err
        assert "Remediation" in err

    def test_probe_timeout_is_fail_open_with_warning(self, monkeypatch, capsys):
        # #13574 DS F1: a stalled connection must not hang or brick the boot —
        # _run_list_timeout converts TimeoutExpired to rc=124, which lands in
        # the inconclusive (warn + pass) branch.
        self._arm(monkeypatch,
                  _mock_result(returncode=124, stderr="TIMEOUT after 15s"))
        assert tracker.check_gh() is True
        assert "inconclusive" in capsys.readouterr().err

    def test_probe_error_is_fail_open_with_warning(self, monkeypatch, capsys):
        self._arm(monkeypatch, _mock_result(returncode=1))
        assert tracker.check_gh() is True
        assert "inconclusive" in capsys.readouterr().err

    def test_unexpected_output_is_fail_open_with_warning(self, monkeypatch,
                                                         capsys):
        self._arm(monkeypatch, _mock_result(stdout="null\n"))
        assert tracker.check_gh() is True
        assert "inconclusive" in capsys.readouterr().err

    def test_timeout_helper_converts_timeout_to_rc124(self, monkeypatch):
        # The helper itself: TimeoutExpired -> fake rc=124 result, no raise.
        import subprocess as sp

        def boom(*a, **kw):
            raise sp.TimeoutExpired(cmd=a[0], timeout=kw.get("timeout"))

        monkeypatch.setattr(tracker.subprocess, "run", boom)
        res = tracker._run_list_timeout(["gh", "api", "x"], timeout=1)
        assert res.returncode == 124
        assert "TIMEOUT" in res.stderr


class TestListIssues:
    def test_returns_issues(self, monkeypatch):
        issues = [{"number": 1, "title": "test", "labels": []}]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(issues)),
        )
        result = tracker.list_issues("skill")
        assert len(result) == 1
        assert result[0]["number"] == 1

    def test_with_status_filter(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.list_issues("skill", status="approved")
        # Should include status:approved in labels
        label_arg = calls[0][calls[0].index("--label") + 1]
        assert "status:approved" in label_arg

    def test_gh_failure_returns_empty(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(returncode=1, stderr="error"),
        )
        result = tracker.list_issues("skill")
        assert result == []


class TestListByLabels:
    def test_returns_issues(self, monkeypatch):
        issues = [{"number": 42, "title": "test"}]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(issues)),
        )
        result = tracker.list_by_labels("type:issue,role:skill")
        assert len(result) == 1

    def test_uses_adapter_when_available(self, monkeypatch):
        adapter = MagicMock()
        adapter.list_issues.return_value = [{"number": 1}]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        result = tracker.list_by_labels("type:issue,role:skill")
        adapter.list_issues.assert_called_once()
        assert len(result) == 1

    def test_state_parameter_passed_to_gh(self, monkeypatch):
        """list_by_labels passes --state parameter to gh CLI (#6222)."""
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.list_by_labels("status:pending-ship", state="all")
        assert any("--state" in cmd and "all" in cmd for cmd in calls)

    def test_state_defaults_to_open(self, monkeypatch):
        """list_by_labels defaults to --state open (#6222)."""
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.list_by_labels("status:pending-ship")
        assert any("--state" in cmd and "open" in cmd for cmd in calls)

    def test_state_parameter_passed_to_adapter(self, monkeypatch):
        """list_by_labels passes state to forge adapter (#6222)."""
        adapter = MagicMock()
        adapter.list_issues.return_value = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        tracker.list_by_labels("status:pending-ship", state="all")
        adapter.list_issues.assert_called_once_with(
            labels=["status:pending-ship"], state="all",
            limit=tracker._OPEN_ISSUE_LIST_LIMIT
        )


class TestListAllOpen:
    def test_returns_issues(self, monkeypatch):
        issues = [{"number": 1}, {"number": 2}]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(issues)),
        )
        result = tracker.list_all_open()
        assert len(result) == 2


class TestCreateIssue:
    def test_creates_with_correct_labels(self, monkeypatch):
        # #13370: create_issue routes the body via _run_gh_with_body (stdin); the
        # title/label stay in the cmd argv.
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result(stdout="https://github.com/org/repo/issues/99\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        number = tracker.create_issue("test bug", "body", "skill", "high", "pm-lead")
        assert number == 99
        cmd = calls[0][0]
        label_arg = cmd[cmd.index("--label") + 1]
        assert "type:issue" in label_arg
        assert "severity:high" in label_arg
        assert "role:skill" in label_arg
        assert "status:open" in label_arg

    def test_strips_duplicate_prefix(self, monkeypatch):
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result(stdout="https://github.com/org/repo/issues/1\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        tracker.create_issue("ISSUE: already prefixed", "body", "skill", "low")
        cmd = calls[0][0]
        title_arg = cmd[cmd.index("--title") + 1]
        assert title_arg == "ISSUE: already prefixed"
        assert not title_arg.startswith("ISSUE: ISSUE:")

    def test_extra_label_appended_13743(self, monkeypatch):
        """#13743: create_issue must be able to tag an extra label (e.g.
        improvement-scan) alongside the fixed type/severity/role/status set."""
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result(stdout="https://github.com/org/repo/issues/1\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        tracker.create_issue("test", "body", "skill", "low",
                              extra_label="improvement-scan")
        cmd = calls[0][0]
        label_arg = cmd[cmd.index("--label") + 1]
        assert "improvement-scan" in label_arg.split(",")

    def test_no_extra_label_by_default(self, monkeypatch):
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result(stdout="https://github.com/org/repo/issues/1\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        tracker.create_issue("test", "body", "skill", "low")
        cmd = calls[0][0]
        label_arg = cmd[cmd.index("--label") + 1]
        assert "improvement-scan" not in label_arg.split(",")

    def test_extra_label_via_forge_adapter(self, monkeypatch):
        adapter_calls = []

        class FakeAdapter:
            def create_issue(self, title, body, labels=None):
                adapter_calls.append({"labels": labels})
                return {"number": 1, "url": "http://forge/issues/1"}

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: FakeAdapter())
        tracker.create_issue("test", "body", "skill", "low",
                              extra_label="improvement-scan")
        assert "improvement-scan" in adapter_calls[0]["labels"]


class TestCreateTask:
    def test_creates_with_pending_status(self, monkeypatch):
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result(stdout="https://github.com/org/repo/issues/50\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        number = tracker.create_task("new feature", "body", "skill", "medium")
        assert number == 50
        cmd = calls[0][0]
        label_arg = cmd[cmd.index("--label") + 1]
        assert "type:task" in label_arg
        assert "status:pending" in label_arg


    def test_create_task_forge_adapter_path(self, monkeypatch):
        """#6848: create_task must use forge adapter when available."""
        adapter_calls = []

        class FakeAdapter:
            def create_issue(self, title, body, labels=None):
                adapter_calls.append({"title": title, "body": body, "labels": labels})
                return {"number": 99, "url": "http://forge/issues/99"}

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: FakeAdapter())
        number = tracker.create_task("new feat", "body text", "skill", "high", reporter="skill-lead")
        assert number == 99
        assert len(adapter_calls) == 1
        assert "TASK:" in adapter_calls[0]["title"]
        assert "type:task" in adapter_calls[0]["labels"]

    def test_create_task_includes_reporter(self, monkeypatch):
        """#6848: create_task should include reporter in body when provided."""
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result(stdout="https://github.com/org/repo/issues/51\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        tracker.create_task("feat", "body", "skill", "medium", reporter="skill-lead")
        # #13370: the reporter-annotated body is now passed as the stdin body arg.
        assert "**Reported By**: skill-lead" in calls[0][1]

    def test_extra_label_appended_13743(self, monkeypatch):
        """#13743: create_task mirrors create_issue's extra_label passthrough."""
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result(stdout="https://github.com/org/repo/issues/52\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        tracker.create_task("feat", "body", "skill", "low",
                             extra_label="improvement-scan")
        cmd = calls[0][0]
        label_arg = cmd[cmd.index("--label") + 1]
        assert "improvement-scan" in label_arg.split(",")

    def test_no_extra_label_by_default(self, monkeypatch):
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result(stdout="https://github.com/org/repo/issues/53\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        tracker.create_task("feat", "body", "skill", "low")
        cmd = calls[0][0]
        label_arg = cmd[cmd.index("--label") + 1]
        assert "improvement-scan" not in label_arg.split(",")

    def test_extra_label_via_forge_adapter(self, monkeypatch):
        adapter_calls = []

        class FakeAdapter:
            def create_issue(self, title, body, labels=None):
                adapter_calls.append({"labels": labels})
                return {"number": 54, "url": "http://forge/issues/54"}

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: FakeAdapter())
        tracker.create_task("feat", "body", "skill", "low",
                             extra_label="improvement-scan")
        assert "improvement-scan" in adapter_calls[0]["labels"]


class TestCommentNoRedundantImport:
    """#6849: comment() must use module-level re, not import re as _re."""

    def test_no_local_re_import(self):
        import inspect
        source = inspect.getsource(tracker.comment)
        assert "import re as _re" not in source, (
            "#6849: comment() should use module-level re, not import re as _re"
        )


class TestComment:
    def test_adds_comment(self, monkeypatch):
        # #13370: comment() routes the body via _run_gh_with_body (stdin).
        calls = []

        def fake_gwb(cmd, body, **kw):
            calls.append((cmd, body))
            return _mock_result()

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_gh_with_body", fake_gwb)
        tracker.comment(42, "skill-lead", "test message")
        assert any("comment" in c for c, _ in calls)
        body = calls[0][1]
        assert "**skill-lead**:" in body
        assert "test message" in body


class TestGetLabels:
    def test_returns_label_names(self, monkeypatch):
        data = {"labels": [{"name": "type:issue"}, {"name": "role:skill"}]}
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(data)),
        )
        labels = tracker.get_labels(42)
        assert "type:issue" in labels
        assert "role:skill" in labels


class TestGetState:
    def test_returns_state(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout='{"state": "OPEN"}'),
        )
        state = tracker.get_state(42)
        assert state == "OPEN"

    def test_closed_state(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout='{"state": "CLOSED"}'),
        )
        state = tracker.get_state(42)
        assert state == "CLOSED"

    def test_adapter_returns_state(self, monkeypatch):
        adapter = MagicMock()
        adapter.view_issue.return_value = {"state": "CLOSED"}
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        state = tracker.get_state(42)
        assert state == "CLOSED"

    def test_adapter_missing_state_returns_unknown(self, monkeypatch):
        """Regression: #8268 — missing state field should return UNKNOWN, not OPEN."""
        adapter = MagicMock()
        adapter.view_issue.return_value = {"title": "some issue"}
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        state = tracker.get_state(42)
        assert state == "UNKNOWN"

    def test_adapter_empty_state_returns_unknown(self, monkeypatch):
        """Empty string state treated as UNKNOWN (#8268)."""
        adapter = MagicMock()
        adapter.view_issue.return_value = {"state": ""}
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        state = tracker.get_state(42)
        assert state == "UNKNOWN"

    def test_adapter_no_data_returns_unknown(self, monkeypatch):
        adapter = MagicMock()
        adapter.view_issue.return_value = None
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        state = tracker.get_state(42)
        assert state == "UNKNOWN"


class TestGetLabelsStateCliFallbackFailClosed13132:
    """#13132: get_labels / get_state CLI-fallback paths must fail closed
    (no raw traceback) on gh non-zero exit, empty stdout, or malformed exit-0
    JSON — mirroring the adapter paths and _get_issue_role_labels."""

    def _cli(self, monkeypatch, result):
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", lambda cmd, **kw: result)

    def test_get_labels_nonzero_returns_empty(self, monkeypatch):
        self._cli(monkeypatch, _mock_result(returncode=1, stderr="boom"))
        assert tracker.get_labels(42) == []

    def test_get_labels_empty_stdout_returns_empty(self, monkeypatch):
        self._cli(monkeypatch, _mock_result(stdout="", returncode=0))
        assert tracker.get_labels(42) == []

    def test_get_labels_malformed_json_returns_empty(self, monkeypatch):
        self._cli(monkeypatch, _mock_result(stdout="not json{", returncode=0))
        assert tracker.get_labels(42) == []

    def test_get_labels_drops_nameless_label_objects(self, monkeypatch):
        # DS-review fold: a label dict missing "name" must be dropped, not
        # injected as "" (matches _get_issue_*_labels filtering).
        data = {"labels": [{"name": "role:skill"}, {}, {"name": "squidsquad"}]}
        self._cli(monkeypatch, _mock_result(stdout=json.dumps(data), returncode=0))
        assert tracker.get_labels(42) == ["role:skill", "squidsquad"]

    def test_get_state_nonzero_returns_unknown(self, monkeypatch):
        self._cli(monkeypatch, _mock_result(returncode=1, stderr="boom"))
        assert tracker.get_state(42) == "UNKNOWN"

    def test_get_state_empty_stdout_returns_unknown(self, monkeypatch):
        self._cli(monkeypatch, _mock_result(stdout="", returncode=0))
        assert tracker.get_state(42) == "UNKNOWN"

    def test_get_state_malformed_json_returns_unknown(self, monkeypatch):
        self._cli(monkeypatch, _mock_result(stdout="<html>500</html>", returncode=0))
        assert tracker.get_state(42) == "UNKNOWN"

    def test_get_state_missing_state_key_returns_unknown(self, monkeypatch):
        # exit-0 JSON without a "state" field previously raised KeyError.
        self._cli(monkeypatch, _mock_result(stdout='{"title": "x"}', returncode=0))
        assert tracker.get_state(42) == "UNKNOWN"


class TestCheckUnreadFeedbackFailClosed13132:
    """#13132 Finding 2: _check_unread_feedback must return the fail-closed
    sentinel on a malformed exit-0 response, not raise JSONDecodeError."""

    _SENTINEL = [("unknown (API error)", "unknown")]

    def test_malformed_exit0_returns_sentinel(self, monkeypatch):
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout="not json{", returncode=0),
        )
        assert tracker._check_unread_feedback(42, "skill") == self._SENTINEL

    def test_nonzero_still_returns_sentinel(self, monkeypatch):
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(returncode=1),
        )
        assert tracker._check_unread_feedback(42, "skill") == self._SENTINEL

    def test_valid_no_comments_returns_empty(self, monkeypatch):
        # Happy path still works: valid JSON, no comments → no unread feedback.
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout='{"comments": []}', returncode=0),
        )
        assert tracker._check_unread_feedback(42, "skill") == []


class TestCloseIssue:
    def test_calls_close(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result()

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.close_issue(42)
        assert any("close" in c for c in calls)


class TestParseArgs:
    def test_basic_command(self):
        with patch("sys.argv", ["tracker.py", "check-gh"]):
            cmd, pos, opts = tracker._parse_args()
        assert cmd == "check-gh"

    def test_with_options(self):
        with patch("sys.argv", ["tracker.py", "create-issue",
                                "--title", "test", "--role", "skill"]):
            cmd, pos, opts = tracker._parse_args()
        assert cmd == "create-issue"
        assert opts["title"] == "test"
        assert opts["role"] == "skill"

    def test_positional_args(self):
        with patch("sys.argv", ["tracker.py", "transition", "42",
                                "open", "in-progress", "--role", "skill-lead"]):
            cmd, pos, opts = tracker._parse_args()
        assert cmd == "transition"
        assert "42" in pos
        assert opts["role"] == "skill-lead"


# ---------------------------------------------------------------------------
# work_queue (#2344)
# ---------------------------------------------------------------------------


def _make_gh_item(number, title, status, item_type, priority=None, severity=None):
    """Build a fake gh issue list item with labels."""
    labels = [
        {"name": f"status:{status}"},
        {"name": f"type:{item_type}"},
        {"name": "role:skill"},
    ]
    if severity:
        labels.append({"name": f"severity:{severity}"})
    if priority:
        labels.append({"name": f"priority:{priority}"})
    return {"number": number, "title": title, "labels": labels}


class TestWorkQueue:
    """work_queue() returns prioritized work list for agent (#2344)."""

    def test_empty_queue(self, monkeypatch):
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout="[]"))
        result = tracker.work_queue("skill")
        assert result == []

    def test_single_item(self, monkeypatch):
        items = [_make_gh_item(42, "Fix bug", "approved", "issue", severity="high")]
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout=json.dumps(items)))
        result = tracker.work_queue("skill")
        assert len(result) == 1
        assert result[0]["number"] == 42

    def test_in_progress_first(self, monkeypatch):
        items = [
            _make_gh_item(10, "Approved task", "approved", "task", priority="high"),
            _make_gh_item(20, "In progress", "in-progress", "issue", severity="low"),
        ]
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout=json.dumps(items)))
        result = tracker.work_queue("skill")
        assert result[0]["number"] == 20  # in-progress first

    def test_severity_ordering(self, monkeypatch):
        items = [
            _make_gh_item(1, "Low bug", "approved", "issue", severity="low"),
            _make_gh_item(2, "High bug", "approved", "issue", severity="high"),
            _make_gh_item(3, "Med bug", "approved", "issue", severity="medium"),
        ]
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout=json.dumps(items)))
        result = tracker.work_queue("skill")
        assert [r["number"] for r in result] == [2, 3, 1]

    def test_issues_before_tasks(self, monkeypatch):
        items = [
            _make_gh_item(10, "Task", "approved", "task", priority="high"),
            _make_gh_item(20, "Issue", "approved", "issue", severity="high"),
        ]
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout=json.dumps(items)))
        result = tracker.work_queue("skill")
        assert result[0]["number"] == 20  # issue before task

    def test_skips_non_actionable_statuses(self, monkeypatch):
        items = [
            _make_gh_item(1, "Pending", "pending", "task", priority="high"),
            _make_gh_item(2, "Shipped", "shipped", "task", priority="high"),
            _make_gh_item(3, "Approved", "approved", "task", priority="medium"),
        ]
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout=json.dumps(items)))
        result = tracker.work_queue("skill")
        assert len(result) == 1
        assert result[0]["number"] == 3

    def test_mixed_queue_full_ordering(self, monkeypatch):
        items = [
            _make_gh_item(1, "Open low issue", "open", "issue", severity="low"),
            _make_gh_item(2, "Approved med task", "approved", "task", priority="medium"),
            _make_gh_item(3, "In-progress issue", "in-progress", "issue", severity="medium"),
            _make_gh_item(4, "Approved high issue", "approved", "issue", severity="high"),
        ]
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout=json.dumps(items)))
        result = tracker.work_queue("skill")
        # Order: in-progress(3), approved issue high(4), approved task med(2), open issue low(1)
        assert [r["number"] for r in result] == [3, 4, 2, 1]

    def test_gh_failure_returns_empty(self, monkeypatch):
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(returncode=1, stderr="error"))
        result = tracker.work_queue("skill")
        assert result == []

    def test_return_path_reassigned_ticket_surfaces_to_originator_12800(self, monkeypatch):
        """#12800 AC5: the human-handoff return path is async — a human is not
        on the event bus. The ticket keeps its `role:<originator>` label while
        parked at pending-human-* (EAD routes those by role-class, not label),
        so once it is re-assigned back (status → in-progress, role unchanged)
        it surfaces in the originator's work_queue and resumes on the next
        wake. No assigned-to is needed for the originator — the forge queue is
        the resume mechanism."""
        items = [_make_gh_item(77, "Resumed after human answer", "in-progress",
                               "task", priority="high")]
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout=json.dumps(items)))
        result = tracker.work_queue("skill")
        assert [r["number"] for r in result] == [77]
        assert result[0]["status"] == "in-progress"


# ---------------------------------------------------------------------------
# #2693 regression: pending-review label consistency
# ---------------------------------------------------------------------------

class TestLabelConsistency:
    """All statuses referenced in LEGAL_TRANSITIONS and ROLE_AUTHORITY
    must exist in STATUS_LABELS (resolvable via CLI short-form)."""

    def test_all_transition_statuses_in_status_labels(self):
        """Every status label in LEGAL_TRANSITIONS must be resolvable."""
        valid_labels = set(tracker.STATUS_LABELS.values())
        for src, targets in tracker.LEGAL_TRANSITIONS.items():
            assert src in valid_labels, \
                f"LEGAL_TRANSITIONS source {src!r} not in STATUS_LABELS"
            for tgt in targets:
                assert tgt in valid_labels, \
                    f"LEGAL_TRANSITIONS target {tgt!r} (from {src!r}) not in STATUS_LABELS"

    def test_all_authority_statuses_in_status_labels(self):
        """Every status label in ROLE_AUTHORITY must be resolvable."""
        valid_labels = set(tracker.STATUS_LABELS.values())
        for (src, tgt), _roles in tracker.ROLE_AUTHORITY.items():
            assert src in valid_labels, \
                f"ROLE_AUTHORITY source {src!r} not in STATUS_LABELS"
            assert tgt in valid_labels, \
                f"ROLE_AUTHORITY target {tgt!r} not in STATUS_LABELS"

    def test_no_pending_review_without_human(self):
        """#2693: status:pending-review should not exist — only status:pending-human-review."""
        all_labels = set(tracker.STATUS_LABELS.values())
        assert "status:pending-review" not in all_labels
        assert "status:pending-human-review" in all_labels


# _is_branch_workflow_enabled removed in #9478 — branch+PR is the only mode.


# ---------------------------------------------------------------------------
# #9999 regression: ship-gate squash-merge false-positive
# ---------------------------------------------------------------------------

class TestCheckMergedPr:
    """`_check_merged_pr` is the GitHub-PR-state second opinion that
    rescues the ship gate from false-positive ancestry blocks on
    squash-merges (#9999)."""

    def test_returns_pr_when_branch_matches_merged_pr(self, monkeypatch):
        prs = [{
            "number": 9997,
            "headRefName": "squidsquad/task/9967",
            "url": "https://github.com/example/repo/pull/9997",
        }]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(prs)),
        )
        result = tracker._check_merged_pr(9967)
        assert result == (9997, "https://github.com/example/repo/pull/9997")

    def test_returns_none_when_no_merged_pr(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout="[]"),
        )
        assert tracker._check_merged_pr(9967) is None

    def test_returns_none_when_pr_branch_mismatches_issue_number(self, monkeypatch):
        # A merged PR exists, but for a different issue number — must
        # not falsely satisfy the gate for #9967.
        prs = [{
            "number": 9998,
            "headRefName": "squidsquad/task/1234",
            "url": "https://github.com/example/repo/pull/9998",
        }]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(prs)),
        )
        assert tracker._check_merged_pr(9967) is None

    def test_returns_none_on_gh_failure(self, monkeypatch):
        # Network / auth error → returns None so the caller falls
        # through to the existing ancestry block (safe default).
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(returncode=1, stderr="error"),
        )
        assert tracker._check_merged_pr(9967) is None

    def test_returns_none_on_malformed_gh_output(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout="not valid json"),
        )
        assert tracker._check_merged_pr(9967) is None

    def test_queries_for_merged_state(self, monkeypatch):
        """The query must filter for state=merged, not open or all —
        only merged PRs prove the code is on the working branch."""
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker._check_merged_pr(9967)
        assert calls, "expected gh pr list to be invoked"
        cmd = calls[0]
        # state must be merged
        state_idx = cmd.index("--state")
        assert cmd[state_idx + 1] == "merged"

    # --- DS 9999 F2: forge-adapter path coverage ---

    def test_adapter_path_happy_path(self, monkeypatch):
        """When a forge adapter is configured (e.g. Forgejo), the
        adapter path must invoke list_prs(state='merged') and return
        the matching branch's PR. DS 9999 F1 regression: the call must
        NOT pass a broken `search=` substring that would discard all
        results client-side."""
        adapter = MagicMock()
        adapter.list_prs.return_value = [
            {"number": 9997,
             "headRefName": "squidsquad/task/9967",
             "url": "https://forge.example/owner/repo/pulls/9997"},
        ]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        result = tracker._check_merged_pr(9967)
        assert result == (9997, "https://forge.example/owner/repo/pulls/9997")
        adapter.list_prs.assert_called_once_with(state="merged")

    def test_adapter_path_returns_none_when_exception(self, monkeypatch):
        """If the adapter raises (network, auth, schema mismatch), the
        check must return None so the existing ancestry block stays in
        force — safe default, no regression of the ship gate."""
        adapter = MagicMock()
        adapter.list_prs.side_effect = RuntimeError("forge unreachable")
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        assert tracker._check_merged_pr(9967) is None


# --- DS 9999 F3: integration test for the full ship-transition path ---

class TestTransitionShipGateSquashMerge:
    """End-to-end test for the squash-merge ship-gate rescue (#9999).

    Exercises `transition()` with the wiring around the
    `_check_unmerged_branch` / `_check_merged_pr` interplay: when
    ancestry reports a hit AND a merged PR exists, the transition
    must succeed (not call sys.exit). A regression in the wiring
    (e.g. missing the `if merged_pr:` branch) would be caught here.
    """

    def _stub_transition_environment(self, monkeypatch):
        """Stub everything except the unmerged-branch / merged-PR
        guards so we can isolate the squash-merge rescue logic.

        `pending-ship -> shipped` doesn't trip the unread-feedback or
        TC-coverage guards (neither is in `_GUARDED_TRANSITIONS` for
        that pair), so only the unmerged-PR check and the side-effect
        calls (label edit, close, log) need stubbing.
        """
        monkeypatch.setattr(tracker, "_check_unmerged_pr",
                            lambda *a, **kw: None)
        # No forge adapter — gh CLI path.
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        # All gh CLI calls succeed silently (label edit, close).
        monkeypatch.setattr(tracker, "_run_list",
                            lambda *a, **kw: _mock_result(stdout="ok"))
        # Stub the diagnostics subprocess so it can't spawn diagnostics.py.
        monkeypatch.setattr(tracker, "_log_diagnostic",
                            lambda *a, **kw: None)

    def test_ship_allowed_when_squash_merged(self, monkeypatch):
        """Branch ancestry says unmerged; forge PR state says MERGED →
        transition must NOT call sys.exit. Locks the squash-merge
        rescue wiring against accidental removal."""
        self._stub_transition_environment(monkeypatch)
        monkeypatch.setattr(
            tracker, "_check_unmerged_branch",
            lambda n: ("squidsquad/task/9967", 1),
        )
        monkeypatch.setattr(
            tracker, "_check_merged_pr",
            lambda n: (9997, "https://example.com/x/y/pull/9997"),
        )

        try:
            tracker.transition(9967, "pending-ship", "shipped",
                               role="dm-lead", force=False)
        except SystemExit:
            pytest.fail("ship gate falsely blocked a squash-merged PR")

    def test_ship_blocked_when_branch_unmerged_and_no_merged_pr(
            self, monkeypatch, capsys):
        """Branch ancestry says unmerged AND no merged PR found →
        transition must block (sys.exit 1). Guards against the
        rescue widening too far (i.e., approving any ancestry hit)."""
        self._stub_transition_environment(monkeypatch)
        monkeypatch.setattr(
            tracker, "_check_unmerged_branch",
            lambda n: ("squidsquad/task/9967", 1),
        )
        monkeypatch.setattr(tracker, "_check_merged_pr", lambda n: None)

        with pytest.raises(SystemExit) as exc_info:
            tracker.transition(9967, "pending-ship", "shipped",
                               role="dm-lead", force=False)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.err
        assert "not merged to the working branch" in captured.err


class TestHardenStdio13185:
    """#13185: tracker.py CLI stdout/stderr must be crash-proof on a console
    whose encoding can't represent a printed char (Windows cp1252 has no glyph
    for U+2192). The crash hit a SUCCESS print after the side effect (the wake
    emit) had landed → false-failure exit 1 + double-emit risk."""

    def _cp1252_stream(self):
        # A TextIOWrapper over bytes using strict cp1252 — mimics the Windows
        # console that triggered the crash.
        import io
        return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="")

    def test_regression_cp1252_arrow_crashes_without_hardening(self):
        """Baseline repro: the original U+2192 success line raises on a strict
        cp1252 stream — the exact UnicodeEncodeError #13185 reported."""
        s = self._cp1252_stream()
        with pytest.raises(UnicodeEncodeError):
            s.write("work-assign → skill")  # the pre-fix decorative char

    def test_hardening_makes_cp1252_unencodable_char_not_raise(self):
        """After the _harden_stdio reconfigure, the SAME unencodable char no
        longer crashes — it is backslash-escaped instead."""
        s = self._cp1252_stream()
        s.reconfigure(errors="backslashreplace")
        s.write("work-assign → skill")  # must NOT raise
        s.flush()
        assert s.errors == "backslashreplace"

    def test_harden_stdio_sets_backslashreplace(self):
        s = self._cp1252_stream()
        with patch.object(tracker.sys, "stdout", s), \
             patch.object(tracker.sys, "stderr", self._cp1252_stream()):
            tracker._harden_stdio()
            assert tracker.sys.stdout.errors == "backslashreplace"
            assert tracker.sys.stderr.errors == "backslashreplace"

    def test_harden_stdio_safe_when_stream_not_reconfigurable(self):
        """Best-effort: a stream without reconfigure() (e.g. a captured/replaced
        stream) is left as-is, no raise."""
        class _NoReconfigure:
            pass
        with patch.object(tracker.sys, "stdout", _NoReconfigure()), \
             patch.object(tracker.sys, "stderr", _NoReconfigure()):
            tracker._harden_stdio()  # must not raise

    def test_work_assign_success_line_is_ascii(self):
        """Guard against reintroducing a decorative non-ASCII char in the
        work-assign success print (the reported crash site)."""
        import inspect
        src = inspect.getsource(tracker.work_assign)
        assert "→" not in src, "work-assign success print must stay ASCII (#13185)"
        assert "work-assign ->" in src


class TestTransitionTcCoverageGateScope13838:
    """#13838: the TC-coverage gate (transition() step 4) only ACTIVATES
    when tc_coverage._discover_files() finds a TEST-PLAN. Task-flow items
    author one (AC-derived TCs); type:issue bug-fix verifications never do
    (verification-issue-flow.md gates them with its own regression-test +
    full-suite requirements instead). No TEST-PLAN found must remain a
    structural no-op forever, not an accidental gap that later "hardens"
    into blocking every type:issue ship."""

    def _stub_transition_environment(self, monkeypatch):
        monkeypatch.setattr(tracker, "_check_unread_feedback", lambda *a, **kw: [])
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                             lambda *a, **kw: _mock_result(stdout="ok"))
        monkeypatch.setattr(tracker, "_get_issue_status_labels",
                             lambda n: {"status:pending-test"})
        monkeypatch.setattr(tracker, "_convert_draft_pr_to_ready", lambda n: None)
        monkeypatch.setattr(tracker, "_log_diagnostic", lambda *a, **kw: None)

    def test_no_test_plan_never_blocks_pending_ship(self, monkeypatch):
        """No TEST-PLAN discovered (the type:issue case) -> transition
        succeeds, no SystemExit. Locks the documented, by-design no-op."""
        self._stub_transition_environment(monkeypatch)
        monkeypatch.setattr(tc_coverage, "_discover_files", lambda n: (None, None))
        try:
            tracker.transition(13838, "pending-test", "pending-ship",
                                role="verifier-lead", force=False)
        except SystemExit:
            pytest.fail(
                "TC coverage gate must never block when no TEST-PLAN exists (#13838)"
            )

    def test_coverage_failure_still_blocks_when_test_plan_exists(
        self, monkeypatch, tmp_path
    ):
        """A TEST-PLAN DOES exist (task-flow) and coverage fails -> the gate
        still blocks, unaffected by the #13838 scoping clarification."""
        self._stub_transition_environment(monkeypatch)
        tp = tmp_path / "TEST-PLAN-13838.md"
        qr = tmp_path / "QA-RESULTS-13838.md"
        tp.write_text("dummy", encoding="utf-8")
        qr.write_text("dummy", encoding="utf-8")
        monkeypatch.setattr(tc_coverage, "_discover_files", lambda n: (tp, qr))
        monkeypatch.setattr(tc_coverage, "check_coverage", lambda *a, **kw: 1)
        with pytest.raises(SystemExit) as exc_info:
            tracker.transition(13838, "pending-test", "pending-ship",
                                role="verifier-lead", force=False)
        assert exc_info.value.code == 1

    def test_missing_qa_results_with_test_plan_still_blocks(
        self, monkeypatch, tmp_path
    ):
        """A TEST-PLAN exists but QA-RESULTS doesn't (task-flow, incomplete)
        -> still blocks, distinct from the no-TEST-PLAN-at-all no-op case."""
        self._stub_transition_environment(monkeypatch)
        tp = tmp_path / "TEST-PLAN-13838.md"
        tp.write_text("dummy", encoding="utf-8")
        monkeypatch.setattr(tc_coverage, "_discover_files", lambda n: (tp, None))
        with pytest.raises(SystemExit) as exc_info:
            tracker.transition(13838, "pending-test", "pending-ship",
                                role="verifier-lead", force=False)
        assert exc_info.value.code == 1
