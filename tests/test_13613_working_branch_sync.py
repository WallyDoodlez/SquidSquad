"""Regression tests for #13613 — commit_code()'s post-commit checkout back to
the working branch (e.g. main) previously never pulled, so local `main`
silently drifted further behind origin/main with every commit_code
round-trip in a session, unnoticed until an incidental symptom (a
comprehension-staleness false-positive) surfaced it.

_sync_working_branch_to_origin() fast-forwards local `working` to origin
when behind. Unlike _sync_local_branch_to_origin (#13373, used for feature
branches in task_begin), it runs AFTER a feature-branch commit has already
succeeded, so it must NEVER exit the process — it silently no-ops on
divergence, an unpushed local commit, or a network hiccup (fail-open,
never force-overwrite local main).
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


def _dispatch(*, origin_exists=True, behind=False, ahead=False, ff_rc=0,
              origin_sha=ORIGIN, local_sha=LOCAL):
    """Build a _run_list side_effect + call log for _sync_working_branch_to_origin."""
    calls = []

    def side_effect(cmd, check=False):
        calls.append(cmd)
        s = str(cmd)
        if cmd[:2] == ["git", "fetch"]:
            return _mk(0)
        if "rev-parse" in cmd and "refs/remotes/" in s:
            return _mk(0 if origin_exists else 1, origin_sha + "\n")
        if "rev-parse" in cmd and "refs/heads/" in s:
            return _mk(0, local_sha + "\n")
        if "merge-base" in cmd:
            a = cmd[3]
            if a == local_sha:   # is local an ancestor of origin? -> behind
                return _mk(0 if behind else 1)
            if a == origin_sha:  # is origin an ancestor of local? -> ahead
                return _mk(0 if ahead else 1)
            return _mk(1)
        if "merge" in cmd and "--ff-only" in cmd:
            return _mk(ff_rc, stderr="ff failed" if ff_rc else "")
        return _mk(1)

    return side_effect, calls


class TestSyncWorkingBranchToOrigin:
    @patch("git_ops._run", return_value=_mk(0, WORKING + "\n"))
    @patch("git_ops._run_list")
    def test_behind_fast_forwards(self, mock_rl, mock_run):
        """Local behind origin -> a --ff-only merge onto origin/<working> fires."""
        side_effect, calls = _dispatch(origin_exists=True, behind=True)
        mock_rl.side_effect = side_effect
        git_ops._sync_working_branch_to_origin(WORKING)
        ff = [c for c in calls if "merge" in c and "--ff-only" in c]
        assert len(ff) == 1
        assert f"origin/{WORKING}" in ff[0]

    @patch("git_ops._run", return_value=_mk(0, WORKING + "\n"))
    @patch("git_ops._run_list")
    def test_diverged_never_exits_never_merges(self, mock_rl, mock_run):
        """Diverged -> no SystemExit (unlike task_begin's sync), no merge attempted."""
        side_effect, calls = _dispatch(origin_exists=True, behind=False, ahead=False)
        mock_rl.side_effect = side_effect
        git_ops._sync_working_branch_to_origin(WORKING)  # must not raise
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run", return_value=_mk(0, WORKING + "\n"))
    @patch("git_ops._run_list")
    def test_ahead_keeps_local_no_merge(self, mock_rl, mock_run):
        """Local ahead of origin (unpushed work) -> no merge."""
        side_effect, calls = _dispatch(origin_exists=True, behind=False, ahead=True)
        mock_rl.side_effect = side_effect
        git_ops._sync_working_branch_to_origin(WORKING)
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run", return_value=_mk(0, WORKING + "\n"))
    @patch("git_ops._run_list")
    def test_origin_absent_noop(self, mock_rl, mock_run):
        """origin/<working> unreachable (e.g. network hiccup) -> no compare, no merge."""
        side_effect, calls = _dispatch(origin_exists=False)
        mock_rl.side_effect = side_effect
        git_ops._sync_working_branch_to_origin(WORKING)
        assert not [c for c in calls if "merge-base" in c]
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run", return_value=_mk(0, WORKING + "\n"))
    @patch("git_ops._run_list")
    def test_in_sync_noop(self, mock_rl, mock_run):
        """local == origin -> no compare, no merge."""
        side_effect, calls = _dispatch(origin_exists=True, origin_sha=LOCAL,
                                       local_sha=LOCAL)
        mock_rl.side_effect = side_effect
        git_ops._sync_working_branch_to_origin(WORKING)
        assert not [c for c in calls if "merge-base" in c]
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run", return_value=_mk(0, WORKING + "\n"))
    @patch("git_ops._run_list")
    def test_ff_failure_warns_never_exits(self, mock_rl, mock_run, capsys):
        """A fast-forward git refuses (e.g. dirty tree) -> WARNING, no SystemExit."""
        side_effect, calls = _dispatch(origin_exists=True, behind=True, ff_rc=1)
        mock_rl.side_effect = side_effect
        git_ops._sync_working_branch_to_origin(WORKING)  # must not raise
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "#13613" in err

    @patch("git_ops._run", return_value=_mk(0, "squidsquad/task/9999\n"))
    @patch("git_ops._run_list")
    def test_switched_away_before_call_skips_merge(self, mock_rl, mock_run):
        """Current branch isn't `working` anymore -> never merge onto the wrong branch."""
        side_effect, calls = _dispatch(origin_exists=True, behind=True)
        mock_rl.side_effect = side_effect
        git_ops._sync_working_branch_to_origin(WORKING)
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]


class TestCheckoutAndSyncWorking:
    @patch("git_ops._sync_working_branch_to_origin")
    @patch("git_ops._safe_checkout", return_value=True)
    def test_checks_out_then_syncs(self, mock_checkout, mock_sync):
        git_ops._checkout_and_sync_working(WORKING)
        mock_checkout.assert_called_once_with(WORKING)
        mock_sync.assert_called_once_with(WORKING)


class TestCommitCodeSyncsWorkingBranch:
    """commit_code()'s post-commit return-to-working calls use the syncing
    wrapper, not bare _safe_checkout, on every return path (#13613)."""

    @patch("git_ops._get_working_branch", return_value=WORKING)
    @patch("git_ops._checkout_and_sync_working")
    @patch("git_ops._git_push")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("subprocess.run")
    def test_success_path_syncs(
        self, mock_subproc, mock_run, mock_run_list, mock_git_push,
        mock_sync_checkout, mock_gwb
    ):
        mock_run.side_effect = [
            _mk(0, " M src/app.py\n"),
            _mk(0, WORKING + "\n"),
        ]
        mock_run_list.return_value = _mk(0)
        mock_git_push.return_value = _mk(0)
        mock_subproc.return_value = _mk(0, "1 file changed")

        result = git_ops.commit_code("skill", "squidsquad/task/13613", "test fix")
        assert result is True
        mock_sync_checkout.assert_called_once_with(WORKING)

    @patch("git_ops._get_working_branch", return_value=WORKING)
    @patch("git_ops._checkout_and_sync_working")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("subprocess.run")
    def test_push_failure_path_syncs(
        self, mock_subproc, mock_run, mock_run_list, mock_sync_checkout, mock_gwb
    ):
        mock_run.side_effect = [
            _mk(0, " M src/app.py\n"),
            _mk(0, WORKING + "\n"),
        ]
        mock_run_list.return_value = _mk(0)
        mock_subproc.return_value = _mk(0, "1 file changed")

        with patch("git_ops._git_push", return_value=_mk(1, stderr="push failed")):
            result = git_ops.commit_code("skill", "squidsquad/task/13613", "test fix")
        assert result is False
        mock_sync_checkout.assert_called_once_with(WORKING)

    @patch("git_ops._get_working_branch", return_value=WORKING)
    @patch("git_ops._checkout_and_sync_working")
    @patch("git_ops._run")
    def test_no_code_changes_path_does_not_sync(
        self, mock_run, mock_sync_checkout, mock_gwb
    ):
        """Nothing-to-commit-at-all short-circuit never touches the branch."""
        mock_run.return_value = _mk(0, " M .squidsquad/state.md\n")
        result = git_ops.commit_code("skill", "squidsquad/task/13613", "test")
        assert result is False
        mock_sync_checkout.assert_not_called()
