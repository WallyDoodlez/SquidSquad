"""Tests for references/scripts/triage.py (#470).

Validates deterministic QA-rejected item detection:
  - Comment role parsing from various formats
  - Feedback detection logic (newer QA/PM comment after last own comment)
  - Edge cases: no comments, no feedback, already addressed
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import triage


class TestParseCommentRole:
    """Test _parse_comment_role extracts roles from comment bodies."""

    def test_simple_role(self):
        assert triage._parse_comment_role("**pm**: some message") == "pm"

    def test_role_with_alias(self):
        assert triage._parse_comment_role("**pm (pm)**: QA round 2") == "pm"

    def test_role_with_lead_suffix(self):
        assert triage._parse_comment_role("**skill-lead**: Fixed.") == "skill"

    def test_role_with_alias_and_lead(self):
        # "skill-lead (Ralph)" -> strip alias -> "skill-lead" -> strip -lead -> "skill"
        assert triage._parse_comment_role("**skill-lead (Ralph)**: Done.") == "skill"

    def test_qa_role(self):
        assert triage._parse_comment_role("**qa**: Verified.") == "qa"

    def test_dm_role(self):
        assert triage._parse_comment_role("**dm (dm)**: Shipped.") == "dm"

    def test_no_role_prefix(self):
        assert triage._parse_comment_role("Just a plain comment") is None

    def test_empty_string(self):
        assert triage._parse_comment_role("") is None

    def test_malformed_bold(self):
        assert triage._parse_comment_role("**unclosed bold") is None


class TestQaFeedbackRoles:
    """Verify QA_FEEDBACK_ROLES contains the right roles."""

    def test_pm_is_feedback_role(self):
        assert "pm" in triage.QA_FEEDBACK_ROLES

    def test_qa_is_feedback_role(self):
        assert "qa" in triage.QA_FEEDBACK_ROLES

    def test_skill_is_not_feedback_role(self):
        assert "skill" not in triage.QA_FEEDBACK_ROLES

    def test_dm_is_not_feedback_role(self):
        assert "dm" not in triage.QA_FEEDBACK_ROLES


class TestTriageScript:
    """Test that triage.py is importable and has the right interface."""

    def test_module_has_find_qa_rejected(self):
        assert hasattr(triage, "find_qa_rejected")
        assert callable(triage.find_qa_rejected)

    def test_module_has_main(self):
        assert hasattr(triage, "main")

    def test_parse_comment_role_is_exported(self):
        assert hasattr(triage, "_parse_comment_role")


class TestTriageLiveSmoke:
    """Live smoke test against the real repo (requires gh CLI)."""

    def test_qa_rejected_returns_list(self):
        """triage.py qa-rejected skill returns a list (may be empty)."""
        result = triage.find_qa_rejected("skill")
        assert isinstance(result, list)
        # Each item should have the expected keys
        for item in result:
            assert "number" in item
            assert "title" in item
            assert "feedback_from" in item
            assert "feedback_at" in item
            assert "feedback_summary" in item

    def test_qa_rejected_nonexistent_role_returns_empty(self):
        """A role with no in-progress items returns empty list."""
        result = triage.find_qa_rejected("nonexistent_role_xyz")
        assert result == []


class TestFindQaRejectedErrorIsolation:
    """#4051 regression: single-issue gh failure must not abort the scan."""

    def test_gh_failure_on_one_issue_does_not_abort(self):
        """If _gh raises RuntimeError for one issue, other issues still process."""
        from unittest.mock import patch

        # Mock _gh: first list call succeeds with 2 items,
        # first view call fails, second view call succeeds
        call_count = 0

        def mock_gh(*args):
            nonlocal call_count
            call_count += 1
            if args[0] == "issue" and args[1] == "list":
                return json.dumps([
                    {"number": 9991, "title": "Item A"},
                    {"number": 9992, "title": "Item B"},
                ])
            if args[0] == "issue" and args[1] == "view":
                if str(args[2]) == "9991":
                    raise RuntimeError("gh failed for 9991")
                # 9992 returns no comments — no feedback match
                return json.dumps({"comments": []})
            return ""

        with patch.object(triage, "_gh", side_effect=mock_gh):
            result = triage.find_qa_rejected("skill")

        # Should NOT raise — the RuntimeError for 9991 is caught
        assert isinstance(result, list)
        # 9992 had no feedback, so result is empty — but crucially no crash
        assert result == []


# ---------------------------------------------------------------------------
# _parse_timestamp (#8081)
# ---------------------------------------------------------------------------

class TestParseTimestamp:
    """Tests for _parse_timestamp — safe ISO 8601 comparison."""

    def test_z_suffix(self):
        dt = triage._parse_timestamp("2026-05-15T08:00:00Z")
        assert dt is not None
        assert dt.hour == 8

    def test_offset_format(self):
        dt = triage._parse_timestamp("2026-05-15T08:00:00+00:00")
        assert dt is not None
        assert dt.hour == 8

    def test_no_timezone(self):
        dt = triage._parse_timestamp("2026-05-15T08:00:00")
        assert dt is not None
        assert dt.hour == 8

    def test_none_returns_none(self):
        assert triage._parse_timestamp(None) is None

    def test_empty_string_returns_none(self):
        assert triage._parse_timestamp("") is None

    def test_garbage_returns_none(self):
        assert triage._parse_timestamp("not-a-date") is None

    def test_z_and_offset_compare_equal(self):
        """#8081 regression: Z and +00:00 must compare as same time."""
        dt_z = triage._parse_timestamp("2026-05-15T08:00:00Z")
        dt_offset = triage._parse_timestamp("2026-05-15T08:00:00+00:00")
        # Both should be non-None and represent the same point in time
        assert dt_z is not None
        assert dt_offset is not None
        # Strip tzinfo for naive comparison (both are UTC)
        assert dt_z.replace(tzinfo=None) == dt_offset.replace(tzinfo=None)

    def test_ordering_works(self):
        """Parsed timestamps support < > comparison."""
        earlier = triage._parse_timestamp("2026-05-15T07:00:00Z")
        later = triage._parse_timestamp("2026-05-15T09:00:00Z")
        assert earlier < later
