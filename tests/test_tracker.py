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


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


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
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="https://github.com/org/repo/issues/99\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        number = tracker.create_issue("test bug", "body", "skill", "high", "pm-lead")
        assert number == 99
        # Verify labels include type:issue, severity:high, role:skill
        label_arg = calls[0][calls[0].index("--label") + 1]
        assert "type:issue" in label_arg
        assert "severity:high" in label_arg
        assert "role:skill" in label_arg
        assert "status:open" in label_arg

    def test_strips_duplicate_prefix(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="https://github.com/org/repo/issues/1\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.create_issue("ISSUE: already prefixed", "body", "skill", "low")
        title_arg = calls[0][calls[0].index("--title") + 1]
        assert title_arg == "ISSUE: already prefixed"
        assert not title_arg.startswith("ISSUE: ISSUE:")


class TestCreateTask:
    def test_creates_with_pending_status(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="https://github.com/org/repo/issues/50\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        number = tracker.create_task("new feature", "body", "skill", "medium")
        assert number == 50
        label_arg = calls[0][calls[0].index("--label") + 1]
        assert "type:task" in label_arg
        assert "status:pending" in label_arg


class TestComment:
    def test_adds_comment(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result()

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.comment(42, "skill-lead", "test message")
        assert any("comment" in c for c in calls)
        body_idx = calls[0].index("--body") + 1
        assert "**skill-lead**:" in calls[0][body_idx]
        assert "test message" in calls[0][body_idx]


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
