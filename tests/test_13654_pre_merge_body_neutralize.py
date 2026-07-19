"""Regression test for #13654 — PR closing-keyword auto-close bypassing DM's
ship gate recurred at scale post-#13371. #13371's guard neutralizes closing
keywords inside pr_create(), but that guard is bypassed entirely by a bare
`gh pr create` call — the documented-but-unenforced anti-pattern
pr-protocol.md already warns against ("git_ops.py pr-create lock vs bare gh
pr create"). Proven live: 12 issues auto-closed by GitHub at merge time,
stranding them outside DM's pending-ship gate (no CHANGELOG entry, no
ship-comment, no ship-counter increment).

The fix adds a second, unconditional checkpoint: pr_merge() now neutralizes
any closing keyword still live in the PR body immediately before merging,
regardless of how the PR was created. Unlike pr_create()'s guard, this one
cannot be bypassed by skipping the "canonical" creation path — it is the
last sanctioned checkpoint before GitHub's own merge-time auto-close fires.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


def _mk(rc=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = rc
    m.stdout = stdout
    m.stderr = stderr
    return m


class TestNeutralizePrBodyBeforeMerge:
    @patch("git_ops._run_list")
    def test_unneutralized_keyword_gets_edited(self, mock_rl):
        def side_effect(cmd, check=False):
            if cmd[:3] == ["gh", "pr", "view"]:
                return _mk(0, json.dumps({"body": "Summary.\nFixes #13531"}))
            if cmd[:3] == ["gh", "api", "-X"]:
                return _mk(0)
            return _mk(1)
        mock_rl.side_effect = side_effect

        git_ops._neutralize_pr_body_before_merge(13624)

        edit_calls = [c.args[0] for c in mock_rl.call_args_list
                      if c.args[0][:3] == ["gh", "api", "-X"]]
        assert len(edit_calls) == 1
        # #13654 verifier round 2: gh pr edit unconditionally fails in this
        # environment (old gh CLI querying a GraphQL field GitHub removed);
        # the REST PATCH endpoint via `gh api` is the live-confirmed
        # working path. Must never regress back to `gh pr edit`.
        assert edit_calls[0][:4] == ["gh", "api", "-X", "PATCH"]
        assert "pulls/13624" in edit_calls[0][4]
        body_arg = edit_calls[0][edit_calls[0].index("-f") + 1]
        assert "Fixes #13531" not in body_arg
        assert "Addresses #13531" in body_arg

    @patch("git_ops._run_list")
    def test_never_calls_gh_pr_edit(self, mock_rl):
        """The specific command whose live failure caused the #13654 round-2
        rejection must never be invoked again."""
        def side_effect(cmd, check=False):
            if cmd[:3] == ["gh", "pr", "view"]:
                return _mk(0, json.dumps({"body": "Fixes #1"}))
            return _mk(0)
        mock_rl.side_effect = side_effect

        git_ops._neutralize_pr_body_before_merge(13624)

        pr_edit_calls = [c.args[0] for c in mock_rl.call_args_list
                          if c.args[0][:3] == ["gh", "pr", "edit"]]
        assert not pr_edit_calls

    @patch("git_ops._run_list")
    def test_already_clean_body_no_edit_call(self, mock_rl):
        def side_effect(cmd, check=False):
            if cmd[:3] == ["gh", "pr", "view"]:
                return _mk(0, json.dumps({"body": "Summary.\nAddresses #13531"}))
            return _mk(1)
        mock_rl.side_effect = side_effect

        git_ops._neutralize_pr_body_before_merge(13624)

        edit_calls = [c.args[0] for c in mock_rl.call_args_list
                      if c.args[0][:3] == ["gh", "api", "-X"]]
        assert not edit_calls

    @patch("git_ops._run_list")
    def test_view_failure_never_raises_no_edit_call(self, mock_rl):
        mock_rl.return_value = _mk(1, stderr="not found")
        git_ops._neutralize_pr_body_before_merge(13624)  # must not raise
        edit_calls = [c.args[0] for c in mock_rl.call_args_list
                      if c.args[0][:3] == ["gh", "api", "-X"]]
        assert not edit_calls

    @patch("git_ops._run_list")
    def test_malformed_json_never_raises_no_edit_call(self, mock_rl):
        def side_effect(cmd, check=False):
            if cmd[:3] == ["gh", "pr", "view"]:
                return _mk(0, "not json")
            return _mk(1)
        mock_rl.side_effect = side_effect

        git_ops._neutralize_pr_body_before_merge(13624)  # must not raise
        edit_calls = [c.args[0] for c in mock_rl.call_args_list
                      if c.args[0][:3] == ["gh", "api", "-X"]]
        assert not edit_calls

    @patch("git_ops._run_list")
    def test_edit_failure_warns_never_raises(self, mock_rl, capsys):
        def side_effect(cmd, check=False):
            if cmd[:3] == ["gh", "pr", "view"]:
                return _mk(0, json.dumps({"body": "Fixes #1"}))
            if cmd[:3] == ["gh", "api", "-X"]:
                return _mk(1, stderr="edit failed")
            return _mk(1)
        mock_rl.side_effect = side_effect

        git_ops._neutralize_pr_body_before_merge(13624)  # must not raise
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "#13654" in err


class TestPrMergeCallsNeutralizeBeforeMerging:
    @pytest.fixture(autouse=True)
    def _safe_behind(self):
        with patch("git_ops._pr_behind_by", return_value=0), \
                patch("git_ops._pr_state_scope_violations", return_value=[]), \
                patch("git_ops._post_merge_scope_audit"), \
                patch("git_ops._revert_composed_state_contamination"), \
                patch("git_ops._checkout_and_ff_working_after_merge"):
            yield

    @patch("git_ops._neutralize_pr_body_before_merge", return_value=(None, None))
    @patch("git_ops._run_list")
    def test_success_path_neutralizes_before_merge_call(self, mock_rl, mock_neutralize):
        calls = []

        def side_effect(cmd, check=False):
            calls.append(("neutralize" if mock_neutralize.called else "other", cmd))
            if cmd[:3] == ["gh", "pr", "view"] and "state,isDraft" in cmd:
                return _mk(0, json.dumps({"state": "OPEN", "isDraft": False}))
            if cmd[:3] == ["gh", "pr", "merge"]:
                return _mk(0)
            return _mk(0, json.dumps({"headRefName": "squidsquad/skill/13654"}))

        mock_rl.side_effect = side_effect
        success, msg = git_ops.pr_merge(13654)
        assert success is True
        mock_neutralize.assert_called_once_with(13654)

    @patch("git_ops._neutralize_pr_body_before_merge", return_value=(None, None))
    @patch("git_ops._run_list")
    def test_already_merged_skips_neutralize(self, mock_rl, mock_neutralize):
        mock_rl.return_value = _mk(0, json.dumps({"state": "MERGED"}))
        success, msg = git_ops.pr_merge(13654)
        assert success is True
        mock_neutralize.assert_not_called()

    @patch("git_ops._neutralize_pr_body_before_merge", return_value=(None, None))
    @patch("git_ops._run_list")
    def test_neutralize_runs_before_state_scope_and_behind_guards(
        self, mock_rl, mock_neutralize
    ):
        """Neutralize the body even on a PR that gets refused by a later
        guard -- the keyword must never survive to a human's manual retry."""
        with patch("git_ops._pr_state_scope_violations",
                    return_value=["config.md"]):
            mock_rl.return_value = _mk(0, json.dumps(
                {"state": "OPEN", "isDraft": False}))
            success, msg = git_ops.pr_merge(13654)
        assert success is False
        mock_neutralize.assert_called_once_with(13654)
