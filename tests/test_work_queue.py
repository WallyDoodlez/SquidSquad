"""Tests for tracker.py work-queue — priority ordering."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker


def _make_item(number, title, type_label, priority_label, status_label):
    """Build a mock gh issue list item with labels."""
    labels = [
        {"name": f"type:{type_label}", "description": "", "color": ""},
        {"name": f"status:{status_label}", "description": "", "color": ""},
        {"name": "role:skill", "description": "", "color": ""},
    ]
    if type_label == "issue":
        labels.append({"name": f"severity:{priority_label}", "description": "", "color": ""})
    else:
        labels.append({"name": f"priority:{priority_label}", "description": "", "color": ""})
    return {"number": number, "title": title, "labels": labels}


def _mock_gh_result(items):
    """Create a mock subprocess result with items as JSON."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = json.dumps(items)
    result.stderr = ""
    return result


class TestWorkQueueOrdering:
    def test_in_progress_first(self, capsys):
        items = [
            _make_item(1, "approved task", "task", "high", "approved"),
            _make_item(2, "in-progress task", "task", "low", "in-progress"),
        ]
        with patch.object(tracker, "_run_list", return_value=_mock_gh_result(items)):
            queue = tracker.work_queue("skill")
        assert queue[0]["number"] == 2  # in-progress first

    def test_issues_before_tasks_at_same_priority(self, capsys):
        items = [
            _make_item(1, "approved task", "task", "high", "approved"),
            _make_item(2, "approved issue", "issue", "high", "approved"),
        ]
        with patch.object(tracker, "_run_list", return_value=_mock_gh_result(items)):
            queue = tracker.work_queue("skill")
        assert queue[0]["number"] == 2  # issue before task

    def test_high_before_low_priority(self, capsys):
        items = [
            _make_item(1, "low issue", "issue", "low", "approved"),
            _make_item(2, "high issue", "issue", "high", "approved"),
        ]
        with patch.object(tracker, "_run_list", return_value=_mock_gh_result(items)):
            queue = tracker.work_queue("skill")
        assert queue[0]["number"] == 2  # high first

    def test_approved_before_open(self, capsys):
        items = [
            _make_item(1, "open issue", "issue", "high", "open"),
            _make_item(2, "approved issue", "issue", "high", "approved"),
        ]
        with patch.object(tracker, "_run_list", return_value=_mock_gh_result(items)):
            queue = tracker.work_queue("skill")
        assert queue[0]["number"] == 2  # approved first

    def test_skips_non_actionable_statuses(self, capsys):
        items = [
            _make_item(1, "pending-test", "issue", "high", "pending-test"),
            _make_item(2, "pending-ship", "task", "high", "pending-ship"),
            _make_item(3, "approved issue", "issue", "high", "approved"),
        ]
        with patch.object(tracker, "_run_list", return_value=_mock_gh_result(items)):
            queue = tracker.work_queue("skill")
        assert len(queue) == 1
        assert queue[0]["number"] == 3

    def test_full_priority_ordering(self, capsys):
        items = [
            _make_item(1, "open low issue", "issue", "low", "open"),
            _make_item(2, "approved low task", "task", "low", "approved"),
            _make_item(3, "approved high issue", "issue", "high", "approved"),
            _make_item(4, "in-progress medium task", "task", "medium", "in-progress"),
            _make_item(5, "approved medium issue", "issue", "medium", "approved"),
        ]
        with patch.object(tracker, "_run_list", return_value=_mock_gh_result(items)):
            queue = tracker.work_queue("skill")
        expected_order = [4, 3, 5, 2, 1]
        assert [q["number"] for q in queue] == expected_order

    def test_empty_result(self, capsys):
        with patch.object(tracker, "_run_list", return_value=_mock_gh_result([])):
            queue = tracker.work_queue("skill")
        assert queue == []

    def test_gh_failure(self, capsys):
        result = MagicMock()
        result.returncode = 1
        result.stderr = "network error"
        result.stdout = ""
        with patch.object(tracker, "_run_list", return_value=result):
            queue = tracker.work_queue("skill")
        assert queue == []
