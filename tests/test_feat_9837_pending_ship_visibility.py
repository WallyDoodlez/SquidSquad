"""Tests for #9837 — list_issues must surface closed-but-labeled items.

Before #9837 the helper hard-coded ``state="open"`` AND filtered by
``role:<role>`` for every query, including ``--status pending-ship``. Two
things made this wrong for DM:

1. PR auto-close fires "Closes #N" when the merge lands, flipping the issue
   to CLOSED while the ``status:pending-ship`` label survives. DM's query
   missed all those items because of ``--state open``.
2. ``role:<role>`` is the dev owner who authored the work. DM is the
   universal shipper — every pending-ship item is DM's regardless of which
   dev role authored it. Adding ``role:dm`` excluded the role:skill /
   role:qa items DM actually needed to see.

The fix drops BOTH filters when the status is one of the terminal-adjacent
statuses ``pending-ship`` and ``shipped`` (universal-shipper statuses).
Other statuses keep both filters.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker


def _mock_result(stdout="[]", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


class TestUniversalShipperStatuses:
    """pending-ship and shipped use state=all and drop the role filter."""

    def test_pending_ship_uses_state_all_in_gh_path(self, monkeypatch):
        calls = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                            lambda cmd, **kw: calls.append(cmd) or _mock_result())
        tracker.list_issues("dm", status="pending-ship")
        cmd = calls[0]
        assert cmd[cmd.index("--state") + 1] == "all"

    def test_pending_ship_drops_role_filter_in_gh_path(self, monkeypatch):
        calls = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                            lambda cmd, **kw: calls.append(cmd) or _mock_result())
        tracker.list_issues("dm", status="pending-ship")
        label_arg = calls[0][calls[0].index("--label") + 1]
        assert "role:dm" not in label_arg
        assert "role:skill" not in label_arg
        assert "status:pending-ship" in label_arg

    def test_shipped_uses_state_all_in_gh_path(self, monkeypatch):
        calls = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                            lambda cmd, **kw: calls.append(cmd) or _mock_result())
        tracker.list_issues("dm", status="shipped")
        cmd = calls[0]
        assert cmd[cmd.index("--state") + 1] == "all"

    def test_shipped_drops_role_filter_in_gh_path(self, monkeypatch):
        calls = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                            lambda cmd, **kw: calls.append(cmd) or _mock_result())
        tracker.list_issues("dm", status="shipped")
        label_arg = calls[0][calls[0].index("--label") + 1]
        assert "role:" not in label_arg

    def test_pending_ship_uses_state_all_in_adapter_path(self, monkeypatch):
        adapter = MagicMock()
        adapter.list_issues.return_value = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: adapter)
        tracker.list_issues("dm", status="pending-ship")
        _, kwargs = adapter.list_issues.call_args
        assert kwargs["state"] == "all"
        labels = kwargs["labels"]
        assert not any("role:" in lbl for lbl in labels)
        assert "status:pending-ship" in labels


class TestNonUniversalStatusesUnchanged:
    """approved, in-progress, pending-test, etc. keep state=open AND role filter."""

    @pytest.mark.parametrize("status", [
        "approved", "in-progress", "pending-test", "planning", "planned",
        "open", "pending",
    ])
    def test_status_keeps_state_open_and_role_filter(self, monkeypatch, status):
        calls = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                            lambda cmd, **kw: calls.append(cmd) or _mock_result())
        tracker.list_issues("skill", status=status)
        cmd = calls[0]
        assert cmd[cmd.index("--state") + 1] == "open"
        label_arg = cmd[cmd.index("--label") + 1]
        assert "role:skill" in label_arg

    def test_no_status_filter_keeps_state_open_and_role_filter(self, monkeypatch):
        """list-tasks <role> with no --status uses state=open and role filter."""
        calls = []
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                            lambda cmd, **kw: calls.append(cmd) or _mock_result())
        tracker.list_issues("skill")
        cmd = calls[0]
        assert cmd[cmd.index("--state") + 1] == "open"
        assert "role:skill" in cmd[cmd.index("--label") + 1]


class TestDmReproducer:
    """Reproduces the issue body's specific failure scenario."""

    def test_dm_pending_ship_query_returns_role_skill_items(self, monkeypatch):
        """DM's query MUST surface role:skill / role:qa pending-ship items."""
        items = [
            {
                "number": 9744, "title": "TASK: ...",
                "labels": [{"name": "role:skill"}, {"name": "status:pending-ship"}],
            },
            {
                "number": 9743, "title": "TASK: ...",
                "labels": [{"name": "role:qa"}, {"name": "status:pending-ship"}],
            },
        ]
        monkeypatch.setattr(tracker, "_get_forge_adapter", lambda: None)
        monkeypatch.setattr(tracker, "_run_list",
                            lambda cmd, **kw: _mock_result(stdout=json.dumps(items)))
        result = tracker.list_issues("dm", issue_type="task", status="pending-ship")
        # Pre-#9837: would have returned [] because gh filter excluded
        # role:skill items when called with role=dm.
        assert len(result) == 2
        assert {r["number"] for r in result} == {9744, 9743}
