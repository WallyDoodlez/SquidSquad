"""Regression tests for #13660 — list_issues()/list_by_labels()/list_all_open()
in references/scripts/tracker.py shared the #13555/#13602 gh --limit 50
truncation class. list_all_open() was hard-capped at 50 while the live
open-issue count reached 150 (gh orders newest-first, so the OLDEST 100 open
issues -- mostly the status:pending backlog -- were silently invisible).
list_issues()/list_by_labels() carried the identical cap, latent only because
current role/status-filtered counts stay under 50.

Fix (per #13555's precedent): raise the shared limit to 500
(_OPEN_ISSUE_LIST_LIMIT) and warn via _warn_if_capped() when a result hits the
cap, so a silently-truncated result becomes self-diagnosing instead of
invisible.
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


class TestWarnIfCapped:
    def test_warns_when_at_cap(self, capsys):
        tracker._warn_if_capped([{"number": i} for i in range(5)], 5, "list_issues")
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "list_issues" in err
        assert "#13660" in err

    def test_no_warning_under_cap(self, capsys):
        tracker._warn_if_capped([{"number": 1}], 5, "list_issues")
        err = capsys.readouterr().err
        assert err == ""

    def test_no_warning_on_empty(self, capsys):
        tracker._warn_if_capped([], 5, "list_all_open")
        err = capsys.readouterr().err
        assert err == ""


class TestListIssuesLimit13660:
    def test_gh_cli_uses_raised_limit(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.list_issues("skill")
        limit_arg = calls[0][calls[0].index("--limit") + 1]
        assert limit_arg == str(tracker._OPEN_ISSUE_LIST_LIMIT)
        assert tracker._OPEN_ISSUE_LIST_LIMIT > 50

    def test_adapter_passed_raised_limit(self, monkeypatch):
        adapter = MagicMock()
        adapter.list_issues.return_value = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        tracker.list_issues("skill")
        _, kwargs = adapter.list_issues.call_args
        assert kwargs["limit"] == tracker._OPEN_ISSUE_LIST_LIMIT

    def test_warns_on_capped_result(self, monkeypatch, capsys):
        issues = [{"number": i, "title": "t", "labels": []}
                  for i in range(tracker._OPEN_ISSUE_LIST_LIMIT)]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(issues)),
        )
        tracker.list_issues("skill")
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "#13660" in err

    def test_no_warning_under_cap(self, monkeypatch, capsys):
        issues = [{"number": 1, "title": "t", "labels": []}]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(issues)),
        )
        tracker.list_issues("skill")
        err = capsys.readouterr().err
        assert "WARNING" not in err


class TestListByLabelsLimit13660:
    def test_gh_cli_uses_raised_limit(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.list_by_labels("type:issue,role:skill")
        limit_arg = calls[0][calls[0].index("--limit") + 1]
        assert limit_arg == str(tracker._OPEN_ISSUE_LIST_LIMIT)

    def test_adapter_passed_raised_limit(self, monkeypatch):
        adapter = MagicMock()
        adapter.list_issues.return_value = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        tracker.list_by_labels("type:issue,role:skill")
        _, kwargs = adapter.list_issues.call_args
        assert kwargs["limit"] == tracker._OPEN_ISSUE_LIST_LIMIT

    def test_warns_on_capped_result(self, monkeypatch, capsys):
        issues = [{"number": i} for i in range(tracker._OPEN_ISSUE_LIST_LIMIT)]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(issues)),
        )
        tracker.list_by_labels("type:issue,role:skill")
        err = capsys.readouterr().err
        assert "WARNING" in err


class TestListAllOpenLimit13660:
    def test_gh_cli_uses_raised_limit(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return _mock_result(stdout="[]")

        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list", fake_run)
        tracker.list_all_open()
        limit_arg = calls[0][calls[0].index("--limit") + 1]
        assert limit_arg == str(tracker._OPEN_ISSUE_LIST_LIMIT)

    def test_adapter_passed_raised_limit(self, monkeypatch):
        adapter = MagicMock()
        adapter.list_issues.return_value = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        tracker.list_all_open()
        _, kwargs = adapter.list_issues.call_args
        assert kwargs["limit"] == tracker._OPEN_ISSUE_LIST_LIMIT

    def test_warns_on_capped_result(self, monkeypatch, capsys):
        issues = [{"number": i} for i in range(tracker._OPEN_ISSUE_LIST_LIMIT)]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(issues)),
        )
        tracker.list_all_open()
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "list_all_open" in err

    def test_no_warning_under_cap(self, monkeypatch, capsys):
        issues = [{"number": 1}, {"number": 2}]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(
            tracker, "_run_list",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(issues)),
        )
        tracker.list_all_open()
        err = capsys.readouterr().err
        assert "WARNING" not in err
