"""Regression tests for #1229 — triage.py json.loads error handling.

Verifies that malformed JSON output from the gh CLI does not crash the
triage script. Both the issue list and issue detail parsing must handle
JSONDecodeError gracefully.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import triage


class TestTriageJsonMalformed:
    """#1229: Malformed JSON from gh CLI must not crash triage."""

    @patch.object(triage, "_gh")
    def test_malformed_issue_list_returns_empty(self, mock_gh):
        """#1229: Garbled JSON from 'gh issue list' should return empty list."""
        mock_gh.return_value = "not valid json {[}"
        result = triage.find_qa_rejected("skill")
        assert result == []

    @patch.object(triage, "_gh")
    def test_empty_string_returns_empty(self, mock_gh):
        """#1229: Empty string from 'gh issue list' should return empty list."""
        mock_gh.return_value = ""
        result = triage.find_qa_rejected("skill")
        assert result == []

    @patch.object(triage, "_gh")
    def test_malformed_issue_detail_skips_item(self, mock_gh):
        """#1229: Garbled JSON from 'gh issue view' should skip that item."""
        def gh_side_effect(*args):
            if "issue" in args and "list" in args:
                return json.dumps([
                    {"number": 100, "title": "Test issue"},
                    {"number": 101, "title": "Another issue"},
                ])
            if "issue" in args and "view" in args:
                if "100" in args:
                    return "broken json output!!"
                if "101" in args:
                    return json.dumps({
                        "comments": []
                    })
            return "[]"

        mock_gh.side_effect = gh_side_effect
        result = triage.find_qa_rejected("skill")
        # Issue 100 had bad JSON, should be skipped; issue 101 has no comments
        assert result == []

    @patch.object(triage, "_gh")
    def test_valid_json_processes_normally(self, mock_gh):
        """#1229: Valid JSON should be processed without errors."""
        def gh_side_effect(*args):
            if "issue" in args and "list" in args:
                return json.dumps([
                    {"number": 200, "title": "Feature X"},
                ])
            if "issue" in args and "view" in args:
                return json.dumps({
                    "comments": [
                        {
                            "body": "**pm**: Needs rework on error handling",
                            "createdAt": "2026-04-19T10:00:00Z",
                        }
                    ]
                })
            return "[]"

        mock_gh.side_effect = gh_side_effect
        result = triage.find_qa_rejected("skill")
        assert len(result) == 1
        assert result[0]["number"] == 200
        assert result[0]["feedback_from"] == "pm"

    @patch.object(triage, "_gh")
    def test_gh_cli_raises_runtime_error(self, mock_gh):
        """#1229: RuntimeError from _gh propagates to caller for handling."""
        mock_gh.side_effect = RuntimeError("gh command failed: authentication required")
        with pytest.raises(RuntimeError, match="gh command failed"):
            triage.find_qa_rejected("skill")

    @patch.object(triage, "_gh")
    def test_html_response_doesnt_crash(self, mock_gh):
        """#1229: HTML error page from gh CLI should not crash."""
        mock_gh.return_value = "<html><body>502 Bad Gateway</body></html>"
        result = triage.find_qa_rejected("skill")
        assert result == []

    @patch.object(triage, "_gh")
    def test_partial_json_doesnt_crash(self, mock_gh):
        """#1229: Truncated JSON should not crash."""
        mock_gh.return_value = '[{"number": 1, "title": "trunc'
        result = triage.find_qa_rejected("skill")
        assert result == []


class TestParseCommentRole:
    """#1229: _parse_comment_role helper for extracting role from comment body."""

    def test_simple_role(self):
        """#1229: Standard role prefix parses correctly."""
        assert triage._parse_comment_role("**pm**: Looks good") == "pm"

    def test_role_with_alias(self):
        """#1229: Role with parenthetical alias strips alias."""
        assert triage._parse_comment_role("**pm (pm)**: Feedback here") == "pm"

    def test_lead_suffix_stripped(self):
        """#1229: '-lead' suffix is removed from role name."""
        assert triage._parse_comment_role("**skill-lead**: Done") == "skill"

    def test_no_role_prefix(self):
        """#1229: Plain text body returns None."""
        assert triage._parse_comment_role("Just a normal comment") is None
