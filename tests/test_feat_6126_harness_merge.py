"""Tests for #6126 — Harness owns PR merge + compose.

Tests cover:
- POST /merge endpoint helpers (_get_pr_files, _get_pr_branch, _parse_issue_from_branch, _emit_event)
- cycle_pre.py mechanical reactions for pr-merged (success gate, reactive pull)
- Event catalog updates (pr-merged, compose-completed, request-merge)
- Template updates (QA, DM, PM)
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

REPO_ROOT = SCRIPTS.parent.parent


# ---------------------------------------------------------------------------
# Harness helpers
# ---------------------------------------------------------------------------


class TestParseIssueFromBranch:
    """Test _parse_issue_from_branch helper."""

    def setup_method(self):
        # Import from harness module at test time
        sys.path.insert(0, str(SCRIPTS))

    def test_standard_branch(self):
        from harness import _parse_issue_from_branch
        assert _parse_issue_from_branch("squidsquad/skill/42") == 42

    def test_task_branch(self):
        from harness import _parse_issue_from_branch
        assert _parse_issue_from_branch("squidsquad/task/6126") == 6126

    def test_no_number(self):
        from harness import _parse_issue_from_branch
        assert _parse_issue_from_branch("main") is None

    def test_empty_string(self):
        from harness import _parse_issue_from_branch
        assert _parse_issue_from_branch("") is None

    def test_non_digit_suffix(self):
        from harness import _parse_issue_from_branch
        assert _parse_issue_from_branch("squidsquad/skill/abc") is None

    def test_single_segment_number(self):
        from harness import _parse_issue_from_branch
        # "feature/42" has 2 parts, last is digit
        assert _parse_issue_from_branch("feature/42") == 42


class TestEmitEvent:
    """Test _emit_event helper."""

    def test_emits_to_stream(self):
        from harness import _emit_event, event_stream
        initial_len = len(event_stream)
        _emit_event("test-event", "test-role", payload={"key": "value"})
        assert len(event_stream) == initial_len + 1
        events = event_stream.get_all()
        last = events[-1]
        assert last["event_type"] == "test-event"
        assert last["role"] == "test-role"
        assert last["payload"]["key"] == "value"
        assert "id" in last
        assert "timestamp" in last
        assert "received_at" in last


class TestGetPrFiles:
    """Test _get_pr_files helper."""

    @patch("harness.subprocess.run")
    def test_returns_file_list(self, mock_run):
        from harness import _get_pr_files
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"files": [
                {"path": "references/scripts/harness.py"},
                {"path": "tests/test_harness.py"},
            ]}),
        )
        result = _get_pr_files(42)
        assert result == ["references/scripts/harness.py", "tests/test_harness.py"]

    @patch("harness.subprocess.run")
    def test_returns_none_on_failure(self, mock_run):
        from harness import _get_pr_files
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = _get_pr_files(99999)
        assert result is None

    @patch("harness.subprocess.run")
    def test_returns_none_on_invalid_json(self, mock_run):
        from harness import _get_pr_files
        mock_run.return_value = MagicMock(returncode=0, stdout="not json")
        result = _get_pr_files(42)
        assert result is None


class TestGetPrBranch:
    """Test _get_pr_branch helper."""

    @patch("harness.subprocess.run")
    def test_returns_branch_name(self, mock_run):
        from harness import _get_pr_branch
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"headRefName": "squidsquad/skill/42"}),
        )
        result = _get_pr_branch(42)
        assert result == "squidsquad/skill/42"

    @patch("harness.subprocess.run")
    def test_returns_empty_on_failure(self, mock_run):
        from harness import _get_pr_branch
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = _get_pr_branch(99999)
        assert result == ""


# ---------------------------------------------------------------------------
# cycle_pre.py mechanical reactions
# ---------------------------------------------------------------------------


class TestMechanicalReactionsPrMerged:
    """Test cycle_pre._run_mechanical_reactions for pr-merged events (#6126)."""

    def setup_method(self):
        import cycle_pre
        self.run_reactions = cycle_pre._run_mechanical_reactions

    def test_pm_gets_pr_merge_detected_on_success(self):
        """PM should get pr-merge-detected reaction on successful pr-merged event."""
        events = [{
            "id": "abc12345",
            "event_type": "pr-merged",
            "role": "harness",
            "payload": {
                "pr_number": "42",
                "issue_number": "42",
                "success": True,
            },
        }]
        reactions = self.run_reactions(events, "pm")
        types = [r["type"] for r in reactions]
        assert "pr-merge-detected" in types
        detected = [r for r in reactions if r["type"] == "pr-merge-detected"][0]
        assert detected["pr_number"] == "42"
        assert detected["issue_number"] == "42"

    def test_pm_no_pr_merge_detected_on_failure(self):
        """PM should NOT get pr-merge-detected when pr-merged has success:false (CQ-3 fix)."""
        events = [{
            "id": "abc12345",
            "event_type": "pr-merged",
            "role": "harness",
            "payload": {
                "pr_number": "42",
                "issue_number": "42",
                "success": False,
                "error": "merge conflict",
            },
        }]
        reactions = self.run_reactions(events, "pm")
        types = [r["type"] for r in reactions]
        assert "pr-merge-detected" not in types

    def test_skill_gets_reactive_pull_on_success(self):
        """Non-PM agents get reactive-pull-needed on successful pr-merged (#6126 AC-9)."""
        events = [{
            "id": "abc12345",
            "event_type": "pr-merged",
            "role": "harness",
            "payload": {
                "pr_number": "42",
                "issue_number": "42",
                "success": True,
            },
        }]
        reactions = self.run_reactions(events, "skill")
        types = [r["type"] for r in reactions]
        assert "reactive-pull-needed" in types

    def test_skill_no_reactive_pull_on_failure(self):
        """Non-PM agents should NOT get reactive-pull on failed merge."""
        events = [{
            "id": "abc12345",
            "event_type": "pr-merged",
            "role": "harness",
            "payload": {
                "pr_number": "42",
                "issue_number": "42",
                "success": False,
            },
        }]
        reactions = self.run_reactions(events, "skill")
        types = [r["type"] for r in reactions]
        assert "reactive-pull-needed" not in types

    def test_self_emitted_events_skipped(self):
        """Events from the same role are skipped to prevent loops."""
        events = [{
            "id": "abc12345",
            "event_type": "pr-merged",
            "role": "pm",
            "payload": {"pr_number": "42", "issue_number": "42", "success": True},
        }]
        reactions = self.run_reactions(events, "pm")
        assert len(reactions) == 0

    def test_pm_no_reactive_pull(self):
        """PM should NOT get reactive-pull-needed (PM pulls separately)."""
        events = [{
            "id": "abc12345",
            "event_type": "pr-merged",
            "role": "harness",
            "payload": {"pr_number": "42", "issue_number": "42", "success": True},
        }]
        reactions = self.run_reactions(events, "pm")
        types = [r["type"] for r in reactions]
        assert "reactive-pull-needed" not in types


class TestRoleEventTypes:
    """Test _ROLE_EVENT_TYPES includes new event types (#6126 AC-7)."""

    def test_pm_has_pr_merged(self):
        from cycle_pre import _ROLE_EVENT_TYPES
        assert "pr-merged" in _ROLE_EVENT_TYPES["pm"]

    def test_pm_has_compose_completed(self):
        from cycle_pre import _ROLE_EVENT_TYPES
        assert "compose-completed" in _ROLE_EVENT_TYPES["pm"]

    def test_qa_has_pr_merged(self):
        from cycle_pre import _ROLE_EVENT_TYPES
        assert "pr-merged" in _ROLE_EVENT_TYPES["qa"]

    def test_skill_has_pr_merged(self):
        from cycle_pre import _ROLE_EVENT_TYPES
        assert "pr-merged" in _ROLE_EVENT_TYPES["skill"]

    def test_dm_has_pr_merged(self):
        from cycle_pre import _ROLE_EVENT_TYPES
        assert "pr-merged" in _ROLE_EVENT_TYPES["dm"]

    def test_all_roles_have_compose_completed(self):
        from cycle_pre import _ROLE_EVENT_TYPES
        for role in ("pm", "qa", "skill", "dm"):
            assert "compose-completed" in _ROLE_EVENT_TYPES[role], f"{role} missing compose-completed"


# ---------------------------------------------------------------------------
# Event catalog
# ---------------------------------------------------------------------------


class TestEventCatalogNewEvents:
    """Test event catalog includes new #6126 event types."""

    def test_pr_merged_in_emitted(self):
        import event_catalog
        assert "pr-merged" in event_catalog.EMITTED
        assert event_catalog.get_tier("pr-merged") == "emitted"

    def test_compose_completed_in_emitted(self):
        import event_catalog
        assert "compose-completed" in event_catalog.EMITTED
        assert event_catalog.get_tier("compose-completed") == "emitted"

    def test_request_merge_in_recognized(self):
        import event_catalog
        assert "request-merge" in event_catalog.RECOGNIZED
        assert event_catalog.get_tier("request-merge") == "recognized"

    def test_pr_merged_payload_fields(self):
        import event_catalog
        fields = event_catalog.EMITTED["pr-merged"]["payload_fields"]
        assert "pr_number" in fields
        assert "branch" in fields
        assert "issue_number" in fields
        assert "files_changed" in fields
        assert "success" in fields

    def test_compose_completed_payload_fields(self):
        import event_catalog
        fields = event_catalog.EMITTED["compose-completed"]["payload_fields"]
        assert "success" in fields
        assert "trigger_pr" in fields


# ---------------------------------------------------------------------------
# Template updates — static checks
# ---------------------------------------------------------------------------


class TestTemplateUpdates:
    """Verify template files were updated correctly."""

    def test_qa_verification_no_git_ops_pr_merge(self):
        """verifier verification.md should not reference git_ops.py pr-merge (#6126 AC-5)."""
        path = REPO_ROOT / "references" / "sub-skills" / "roles" / "verifier" / "verification.md"
        content = path.read_text(encoding="utf-8")
        assert "git_ops.py pr-merge" not in content

    def test_qa_verification_has_post_merge(self):
        """verifier verification.md should reference POST /merge."""
        path = REPO_ROOT / "references" / "sub-skills" / "roles" / "verifier" / "verification.md"
        content = path.read_text(encoding="utf-8")
        assert "POST" in content and "/merge" in content

    def test_dm_delivery_no_git_ops_pr_merge(self):
        """DM delivery-packaging.md should not reference git_ops.py pr-merge (#6126 AC-5)."""
        path = REPO_ROOT / "references" / "sub-skills" / "roles" / "dm" / "delivery-packaging.md"
        content = path.read_text(encoding="utf-8")
        assert "git_ops.py pr-merge" not in content

    def test_dm_delivery_has_post_merge(self):
        """DM delivery-packaging.md should reference POST /merge."""
        path = REPO_ROOT / "references" / "sub-skills" / "roles" / "dm" / "delivery-packaging.md"
        content = path.read_text(encoding="utf-8")
        assert "POST" in content and "/merge" in content

    def test_pm_post_merge_recompose_deleted(self):
        """PM post-merge-recompose.md should be deleted (#6126 AC-6)."""
        path = REPO_ROOT / "references" / "sub-skills" / "roles" / "pm" / "post-merge-recompose.md"
        assert not path.exists()

    def test_pm_includes_no_post_merge_recompose(self):
        """PM includes.yml should not reference post-merge-recompose (#6126 AC-6)."""
        path = REPO_ROOT / "references" / "roles" / "pm" / "includes.yml"
        content = path.read_text(encoding="utf-8")
        assert "post-merge-recompose" not in content

    def test_pm_instructions_no_post_merge_recompose(self):
        """PM instructions.md should not include post-merge-recompose (#6126 AC-6)."""
        path = REPO_ROOT / "references" / "roles" / "pm" / "instructions.md"
        content = path.read_text(encoding="utf-8")
        assert "post-merge-recompose" not in content


class TestGitOpsNoEmit:
    """Verify git_ops.py pr_merge() no longer emits pr-merge event (#6126 AC-8)."""

    def test_no_emit_pr_merge_in_pr_merge_function(self):
        """git_ops.py should not have _emit('pr-merge') calls."""
        path = REPO_ROOT / "references" / "scripts" / "git_ops.py"
        content = path.read_text(encoding="utf-8")
        # The function body should not contain _emit("pr-merge"
        # But may contain comments referencing it
        lines = content.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if '_emit("pr-merge"' in stripped and not stripped.startswith("#"):
                assert False, f"Line {i+1} still has _emit('pr-merge'): {stripped}"


class TestEventReactionsTable:
    """Verify event-reactions.md includes new event types."""

    def test_pr_merged_in_table(self):
        path = REPO_ROOT / "references" / "sub-skills" / "common" / "event-reactions.md"
        content = path.read_text(encoding="utf-8")
        assert "pr-merged" in content

    def test_compose_completed_in_table(self):
        path = REPO_ROOT / "references" / "sub-skills" / "common" / "event-reactions.md"
        content = path.read_text(encoding="utf-8")
        assert "compose-completed" in content

    def test_request_merge_in_table(self):
        path = REPO_ROOT / "references" / "sub-skills" / "common" / "event-reactions.md"
        content = path.read_text(encoding="utf-8")
        assert "request-merge" in content
