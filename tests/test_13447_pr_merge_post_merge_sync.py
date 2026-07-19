"""Regression tests for #13447 — on a successful squash-merge, a
verifier/DM clone was left with two problems:

1. compose.py's file-watcher can leave composed outputs
   (.squidsquad/<role>/CLAUDE.md, CLAUDE.linked.md) locally MODIFIED,
   which aborts the clone's next `git checkout` with "local changes
   would be overwritten".
2. pr_merge() never fast-forwarded local `working` (main) to origin after
   the server-side merge, so it silently drifted behind — same failure
   class as #13613, but a different call site (pr_merge, not commit_code).

_revert_composed_state_contamination() reverts any dirty CLAUDE.md /
CLAUDE.linked.md to the working-branch version (mirrors the existing
config.md revert, #7491). _checkout_and_ff_working_after_merge() returns
to `working` and fast-forwards it, fail-open throughout (a merge that
already succeeded on GitHub must never be reported as a failure over a
best-effort local sync step).
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops

WORKING = "main"
LOCAL = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
ORIGIN = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _mk(rc=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = rc
    m.stdout = stdout
    m.stderr = stderr
    return m


class TestRevertComposedStateContamination:
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_reverts_dirty_claude_md(self, mock_run, mock_rl):
        mock_run.return_value = _mk(0, " M .squidsquad/pm/CLAUDE.md\n")
        git_ops._revert_composed_state_contamination(WORKING)
        calls = [c.args[0] for c in mock_rl.call_args_list]
        assert ["git", "checkout", WORKING, "--", ".squidsquad/pm/CLAUDE.md"] in calls

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_reverts_dirty_claude_linked_md(self, mock_run, mock_rl):
        mock_run.return_value = _mk(0, " M .squidsquad/skill/CLAUDE.linked.md\n")
        git_ops._revert_composed_state_contamination(WORKING)
        calls = [c.args[0] for c in mock_rl.call_args_list]
        assert ["git", "checkout", WORKING, "--",
                ".squidsquad/skill/CLAUDE.linked.md"] in calls

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_reverts_multiple_roles(self, mock_run, mock_rl):
        mock_run.return_value = _mk(
            0,
            " M .squidsquad/pm/CLAUDE.md\n"
            " M .squidsquad/qa/CLAUDE.linked.md\n"
            " M .squidsquad/dm/CLAUDE.md\n",
        )
        git_ops._revert_composed_state_contamination(WORKING)
        calls = [c.args[0] for c in mock_rl.call_args_list]
        assert len(calls) == 3

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_leaves_unrelated_dirty_files_alone(self, mock_run, mock_rl):
        """Only composed CLAUDE.md/CLAUDE.linked.md are reverted -- never
        working-state.md or other legitimately-dirty state."""
        mock_run.return_value = _mk(
            0,
            " M .squidsquad/pm/CLAUDE.md\n"
            " M .squidsquad/pm/working-state.md\n"
            " M references/scripts/harness.py\n",
        )
        git_ops._revert_composed_state_contamination(WORKING)
        calls = [c.args[0] for c in mock_rl.call_args_list]
        assert len(calls) == 1
        assert calls[0][-1] == ".squidsquad/pm/CLAUDE.md"

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_clean_tree_noop(self, mock_run, mock_rl):
        mock_run.return_value = _mk(0, "")
        git_ops._revert_composed_state_contamination(WORKING)
        mock_rl.assert_not_called()


class TestCheckoutAndFfWorkingAfterMerge:
    @patch("git_ops._run_list")
    @patch("git_ops._safe_checkout", return_value=True)
    def test_behind_fast_forwards(self, mock_checkout, mock_rl):
        def side_effect(cmd, check=False):
            s = str(cmd)
            if cmd[:2] == ["git", "fetch"]:
                return _mk(0)
            if "rev-parse" in cmd and "refs/remotes/" in s:
                return _mk(0, ORIGIN + "\n")
            if "rev-parse" in cmd and "refs/heads/" in s:
                return _mk(0, LOCAL + "\n")
            if "merge-base" in cmd:
                return _mk(0 if cmd[3] == LOCAL else 1)
            if "merge" in cmd and "--ff-only" in cmd:
                return _mk(0)
            return _mk(1)
        mock_rl.side_effect = side_effect
        git_ops._checkout_and_ff_working_after_merge(WORKING)
        mock_checkout.assert_called_once_with(WORKING)
        ff_calls = [c.args[0] for c in mock_rl.call_args_list
                    if "merge" in c.args[0] and "--ff-only" in c.args[0]]
        assert len(ff_calls) == 1

    @patch("git_ops._run_list")
    @patch("git_ops._safe_checkout", return_value=False)
    def test_checkout_failure_never_raises(self, mock_checkout, mock_rl):
        git_ops._checkout_and_ff_working_after_merge(WORKING)  # must not raise
        mock_rl.assert_not_called()

    @patch("git_ops._run_list")
    @patch("git_ops._safe_checkout", return_value=True)
    def test_diverged_never_raises_never_merges(self, mock_checkout, mock_rl):
        def side_effect(cmd, check=False):
            s = str(cmd)
            if cmd[:2] == ["git", "fetch"]:
                return _mk(0)
            if "rev-parse" in cmd and "refs/remotes/" in s:
                return _mk(0, ORIGIN + "\n")
            if "rev-parse" in cmd and "refs/heads/" in s:
                return _mk(0, LOCAL + "\n")
            if "merge-base" in cmd:
                return _mk(1)  # neither is an ancestor -> diverged
            return _mk(1)
        mock_rl.side_effect = side_effect
        git_ops._checkout_and_ff_working_after_merge(WORKING)  # must not raise
        ff_calls = [c.args[0] for c in mock_rl.call_args_list
                    if "merge" in c.args[0] and "--ff-only" in c.args[0]]
        assert not ff_calls

    @patch("git_ops._run_list")
    @patch("git_ops._safe_checkout", return_value=True)
    def test_ff_failure_warns_never_raises(self, mock_checkout, mock_rl, capsys):
        def side_effect(cmd, check=False):
            s = str(cmd)
            if cmd[:2] == ["git", "fetch"]:
                return _mk(0)
            if "rev-parse" in cmd and "refs/remotes/" in s:
                return _mk(0, ORIGIN + "\n")
            if "rev-parse" in cmd and "refs/heads/" in s:
                return _mk(0, LOCAL + "\n")
            if "merge-base" in cmd:
                return _mk(0 if cmd[3] == LOCAL else 1)
            if "merge" in cmd and "--ff-only" in cmd:
                return _mk(1, stderr="ff failed")
            return _mk(1)
        mock_rl.side_effect = side_effect
        git_ops._checkout_and_ff_working_after_merge(WORKING)  # must not raise
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "#13447" in err

    @patch("git_ops._run_list")
    @patch("git_ops._safe_checkout", return_value=True)
    def test_origin_unreachable_noop(self, mock_checkout, mock_rl):
        mock_rl.return_value = _mk(1)  # rev-parse --verify remotes fails
        git_ops._checkout_and_ff_working_after_merge(WORKING)  # must not raise


class TestPrMergePostMergeSync13447:
    """pr_merge()'s success path invokes both the contamination revert and
    the working-branch checkout+sync, in that order."""

    @pytest.fixture(autouse=True)
    def _safe_behind(self):
        with patch("git_ops._pr_behind_by", return_value=0), \
                patch("git_ops._pr_state_scope_violations", return_value=[]), \
                patch("git_ops._post_merge_scope_audit"), \
                patch("git_ops._neutralize_pr_body_before_merge",
                      return_value=(None, None)):
            yield

    @patch("git_ops._get_working_branch", return_value=WORKING)
    @patch("git_ops._checkout_and_ff_working_after_merge")
    @patch("git_ops._revert_composed_state_contamination")
    @patch("git_ops._run_list")
    def test_success_path_reverts_then_syncs(
        self, mock_rl, mock_revert, mock_sync, mock_gwb
    ):
        mock_rl.side_effect = [
            _mk(0, '{"state": "OPEN"}'),
            _mk(0, ""),
            _mk(0, '{"headRefName": "squidsquad/skill/13447"}'),
        ]
        success, msg = git_ops.pr_merge(13447)
        assert success is True
        mock_revert.assert_called_once_with(WORKING)
        mock_sync.assert_called_once_with(WORKING)

    @patch("git_ops._get_working_branch", return_value=WORKING)
    @patch("git_ops._checkout_and_ff_working_after_merge")
    @patch("git_ops._revert_composed_state_contamination")
    @patch("git_ops._run_list")
    def test_failed_merge_never_syncs(
        self, mock_rl, mock_revert, mock_sync, mock_gwb
    ):
        mock_rl.side_effect = [
            _mk(0, '{"state": "OPEN"}'),
            _mk(1, stderr="permission denied"),
        ]
        success, msg = git_ops.pr_merge(13447)
        assert success is False
        mock_revert.assert_not_called()
        mock_sync.assert_not_called()

    @patch("git_ops._get_working_branch", return_value=WORKING)
    @patch("git_ops._checkout_and_ff_working_after_merge")
    @patch("git_ops._revert_composed_state_contamination")
    @patch("git_ops._run_list")
    def test_already_merged_never_syncs(
        self, mock_rl, mock_revert, mock_sync, mock_gwb
    ):
        mock_rl.return_value = _mk(0, '{"state": "MERGED"}')
        success, msg = git_ops.pr_merge(13447)
        assert success is True
        assert msg == "already merged"
        mock_revert.assert_not_called()
        mock_sync.assert_not_called()
