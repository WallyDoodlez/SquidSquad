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
            labels=["status:pending-ship"], state="all", limit=50
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

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="https://github.com/org/repo/issues/51\n")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.create_task("feat", "body", "skill", "medium", reporter="skill-lead")
        body_idx = calls[0].index("--body") + 1
        assert "**Reported By**: skill-lead" in calls[0][body_idx]


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
