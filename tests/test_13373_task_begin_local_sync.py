"""Regression tests for #13373 — task_begin local-branch path must sync to origin.

The local-branch-exists path in git_ops.task_begin() previously checked out the
local ref with NO fetch/compare, so a stale local ref (the normal re-verification
case: the worker pushed the fix commit after a round-1 bounce and this clone's ref
lags origin) got verified without the fix commit. _sync_local_branch_to_origin()
fast-forwards when behind, keeps local when ahead/absent, and fails loudly on
divergence — never checking out an unsynced tip.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops

BRANCH = "squidsquad/task/13373"
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
    """Build a _run_list side_effect + call log for _sync_local_branch_to_origin."""
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
            # cmd == [git, merge-base, --is-ancestor, A, B]
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


class TestSyncLocalBranchToOrigin:
    @patch("git_ops._run_list")
    def test_behind_fast_forwards(self, mock_rl):
        """Local behind origin -> a --ff-only merge onto origin/<branch> fires."""
        side_effect, calls = _dispatch(origin_exists=True, behind=True)
        mock_rl.side_effect = side_effect
        git_ops._sync_local_branch_to_origin(BRANCH)
        ff = [c for c in calls if "merge" in c and "--ff-only" in c]
        assert len(ff) == 1
        assert f"origin/{BRANCH}" in ff[0]

    @patch("git_ops._run_list")
    def test_diverged_exits_with_both_shas(self, mock_rl, capsys):
        """Diverged -> non-zero exit, both SHAs in stderr, and NO merge attempted."""
        side_effect, calls = _dispatch(origin_exists=True, behind=False, ahead=False)
        mock_rl.side_effect = side_effect
        with pytest.raises(SystemExit) as exc:
            git_ops._sync_local_branch_to_origin(BRANCH)
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert LOCAL[:9] in err
        assert ORIGIN[:9] in err
        assert "DIVERGED" in err
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run_list")
    def test_ahead_keeps_local_no_merge(self, mock_rl):
        """Local ahead of origin (unpushed work) -> no merge, no exit."""
        side_effect, calls = _dispatch(origin_exists=True, behind=False, ahead=True)
        mock_rl.side_effect = side_effect
        git_ops._sync_local_branch_to_origin(BRANCH)  # returns normally
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run_list")
    def test_origin_absent_noop(self, mock_rl):
        """origin/<branch> never pushed -> no compare, no merge."""
        side_effect, calls = _dispatch(origin_exists=False)
        mock_rl.side_effect = side_effect
        git_ops._sync_local_branch_to_origin(BRANCH)
        assert not [c for c in calls if "merge-base" in c]
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run_list")
    def test_in_sync_noop(self, mock_rl):
        """local == origin -> no compare, no merge."""
        side_effect, calls = _dispatch(origin_exists=True, origin_sha=LOCAL,
                                       local_sha=LOCAL)
        mock_rl.side_effect = side_effect
        git_ops._sync_local_branch_to_origin(BRANCH)
        assert not [c for c in calls if "merge-base" in c]
        assert not [c for c in calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run_list")
    def test_ff_failure_exits(self, mock_rl):
        """A fast-forward that git refuses (e.g. dirty tree) -> non-zero exit."""
        side_effect, calls = _dispatch(origin_exists=True, behind=True, ff_rc=1)
        mock_rl.side_effect = side_effect
        with pytest.raises(SystemExit) as exc:
            git_ops._sync_local_branch_to_origin(BRANCH)
        assert exc.value.code == 1


class TestTaskBeginCallsSync:
    @patch("git_ops._sync_local_branch_to_origin")
    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._run_list")
    def test_local_path_syncs_to_origin(self, mock_rl, mock_checkout, mock_sync):
        """task_begin's local-branch-exists path invokes the origin sync (#13373)."""
        def side_effect(cmd, check=False):
            r = MagicMock()
            r.returncode = 0 if ("rev-parse" in cmd and "refs/heads/" in str(cmd)) else 1
            return r
        mock_rl.side_effect = side_effect
        with patch("config.get_field", return_value=None):
            git_ops.task_begin("skill", "13373")
        mock_sync.assert_called_once_with(BRANCH)
