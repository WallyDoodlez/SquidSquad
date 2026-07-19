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


def _fake_run_no_stash_activity(calls):
    """A `git_ops._run` fake (string-command form) for the `_stash_top_ref`/
    `git stash -q` calls #13819's fast-forward stash-guard makes. Simulates
    a perpetually clean tree: `_stash_top_ref()` always returns the same
    (empty) value, so `stashed` computes False and no pop is ever attempted
    -- the behavior the pre-#13819 tests implicitly assumed."""
    def side_effect(cmd, check=False):
        calls.append(cmd)
        if "refs/stash" in cmd:
            return _mk(1, "")  # no stash ref exists -- never changes
        if cmd.strip() == "git stash -q":
            return _mk(0)  # no-op stash on a clean tree
        return _mk(1)

    return side_effect


def _fake_run_creates_and_pops_stash(calls, *, pop_rc=0):
    """A `git_ops._run` fake simulating a REAL uncommitted change: the first
    `_stash_top_ref()` call (pre-stash) sees no stash, `git stash -q`
    creates one (dirty tree), the second `_stash_top_ref()` call (post-
    stash) sees it -- so `stashed` computes True and `_safe_stash_pop()`'s
    `git stash pop` is expected to fire."""
    state = {"stash_sha": "", "stash_calls": 0}

    def side_effect(cmd, check=False):
        calls.append(cmd)
        if "refs/stash" in cmd:
            state["stash_calls"] += 1
            return _mk(0 if state["stash_sha"] else 1, state["stash_sha"])
        if cmd.strip() == "git stash -q":
            state["stash_sha"] = "c" * 40
            return _mk(0)
        if cmd.strip() == "git stash pop":
            if pop_rc == 0:
                state["stash_sha"] = ""
            return _mk(pop_rc)
        if cmd.strip() == "git stash drop":
            state["stash_sha"] = ""
            return _mk(0)
        return _mk(1)

    return side_effect


class TestSyncLocalBranchToOrigin:
    @patch("git_ops._run")
    @patch("git_ops._run_list")
    def test_behind_fast_forwards(self, mock_rl, mock_r):
        """Local behind origin -> a --ff-only merge onto origin/<branch> fires."""
        side_effect, calls = _dispatch(origin_exists=True, behind=True)
        mock_rl.side_effect = side_effect
        mock_r.side_effect = _fake_run_no_stash_activity([])
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

    @patch("git_ops._run")
    @patch("git_ops._run_list")
    def test_ff_failure_exits(self, mock_rl, mock_r):
        """A fast-forward that git refuses -> non-zero exit."""
        side_effect, calls = _dispatch(origin_exists=True, behind=True, ff_rc=1)
        mock_rl.side_effect = side_effect
        mock_r.side_effect = _fake_run_no_stash_activity([])
        with pytest.raises(SystemExit) as exc:
            git_ops._sync_local_branch_to_origin(BRANCH)
        assert exc.value.code == 1


class TestSyncLocalBranchToOriginStashGuard13819:
    """#13819: the fast-forward merge previously had no stash protection,
    unlike _safe_checkout() -- uncommitted local changes to a file the
    fast-forward also touches made `git merge --ff-only` refuse outright
    ("Your local changes ... would be overwritten by merge"), aborting
    task-begin hard with no auto-recovery. Routine mid-cycle state for an
    event-mode agent (this is the verifier re-verification path)."""

    @patch("git_ops._run")
    @patch("git_ops._run_list")
    def test_dirty_tree_stashes_before_and_pops_after_successful_ff(self, mock_rl, mock_r):
        calls = []
        rl_side_effect, rl_calls = _dispatch(origin_exists=True, behind=True, ff_rc=0)
        mock_rl.side_effect = rl_side_effect
        mock_r.side_effect = _fake_run_creates_and_pops_stash(calls)
        git_ops._sync_local_branch_to_origin(BRANCH)
        assert any(c.strip() == "git stash -q" for c in calls), \
            "expected a stash attempt before the fast-forward"
        assert any(c.strip() == "git stash pop" for c in calls), \
            "expected the created stash to be popped back after the fast-forward"
        # The merge itself still fires normally.
        assert [c for c in rl_calls if "merge" in c and "--ff-only" in c]

    @patch("git_ops._run")
    @patch("git_ops._run_list")
    def test_clean_tree_never_pops_a_preexisting_stash(self, mock_rl, mock_r):
        """#13167-safety carried into the new guard: a no-op `git stash -q`
        on a clean tree must never lead to popping an unrelated, pre-
        existing stash entry."""
        calls = []
        rl_side_effect, rl_calls = _dispatch(origin_exists=True, behind=True, ff_rc=0)
        mock_rl.side_effect = rl_side_effect
        mock_r.side_effect = _fake_run_no_stash_activity(calls)
        git_ops._sync_local_branch_to_origin(BRANCH)
        assert any(c.strip() == "git stash -q" for c in calls)
        assert not any(c.strip() == "git stash pop" for c in calls), \
            "clean-tree no-op stash must never be popped"

    @patch("git_ops._run")
    @patch("git_ops._run_list")
    def test_ff_still_fails_after_stash_restores_work_before_exit(self, mock_rl, mock_r):
        """Even when the fast-forward fails for a reason stashing didn't fix,
        the caller's uncommitted work must be restored (popped back) before
        task-begin exits -- never left stranded in the stash."""
        calls = []
        rl_side_effect, rl_calls = _dispatch(origin_exists=True, behind=True, ff_rc=1)
        mock_rl.side_effect = rl_side_effect
        mock_r.side_effect = _fake_run_creates_and_pops_stash(calls)
        with pytest.raises(SystemExit) as exc:
            git_ops._sync_local_branch_to_origin(BRANCH)
        assert exc.value.code == 1
        assert any(c.strip() == "git stash pop" for c in calls), \
            "stashed work must be restored even when the ff-only merge still fails"


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


# ===========================================================================
# #13819 real-git end-to-end reproduction — throwaway temp repos, no mocking.
# The mocked TestSyncLocalBranchToOriginStashGuard13819 tests above verify the
# exact stash-before/pop-after call sequence; this proves the fix against
# actual `git merge --ff-only` refusing a dirty tree, the real symptom #13819
# reported.
# ===========================================================================

import subprocess  # noqa: E402


def _git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {r.stderr}")
    return r


def _init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@t.io")
    _git(path, "config", "user.name", "t")
    _git(path, "config", "commit.gpgsign", "false")
    return path


def _commit(cwd, fname, content, msg):
    (Path(cwd) / fname).write_text(content)
    _git(cwd, "add", fname)
    _git(cwd, "commit", "-m", msg)
    return _git(cwd, "rev-parse", "HEAD").stdout.strip()


def _run_sync_real(repo, branch=BRANCH):
    """Invoke the REAL git_ops._sync_local_branch_to_origin (no mocking) in a
    subprocess whose module-global REPO_ROOT is pinned to the temp repo --
    mirrors tests/test_feat_13373_task_begin_local_sync_qa.py's pattern."""
    driver = (
        f"import sys; sys.path.insert(0, r'{SCRIPTS}'); "
        f"import git_ops; from pathlib import Path; "
        f"git_ops.REPO_ROOT = Path(r'{repo}'); "
        f"git_ops._sync_local_branch_to_origin(r'{branch}')"
    )
    return subprocess.run(
        [sys.executable, "-c", driver], cwd=str(repo), capture_output=True, text=True,
    )


class TestFastForwardStashGuardRealGit13819:
    def test_dirty_tree_on_the_ff_touched_file_no_longer_aborts(self, tmp_path):
        """The exact #13819 symptom: local is behind, AND has an uncommitted
        change to the SAME file the incoming fast-forward also touches (on a
        DIFFERENT line, so the stash-pop's 3-way merge auto-resolves cleanly
        -- a same-line collision is a genuine merge conflict and out of
        scope here; _safe_stash_pop()'s existing, already-accepted design
        for that case is to keep HEAD's version, see #13045). Pre-fix,
        `git merge --ff-only` refuses outright (it treats any uncommitted
        change to a file the incoming commit also touches as a checkout-
        blocking conflict, regardless of which lines) and task-begin aborts
        with sys.exit(1). Post-fix, the change is stashed, the fast-forward
        proceeds, and the uncommitted change is restored on top."""
        # A file wide enough that a change to the top and a change to the
        # bottom fall into separate, non-overlapping 3-way-merge hunks
        # (git's default diff context is 3 lines).
        pad = "\n".join(f"pad{i}" for i in range(10))
        base_text = f"top\n{pad}\nbottom\n"
        seed = _init_repo(tmp_path / "seed")
        _commit(seed, "f.txt", base_text, "base")
        _git(seed, "branch", "-M", BRANCH)
        origin = tmp_path / "origin.git"
        _git(tmp_path, "clone", "--bare", "-q", str(seed), str(origin))
        local = tmp_path / "local"
        _git(tmp_path, "clone", "-q", str(origin), str(local))
        _git(local, "config", "user.email", "t@t.io")
        _git(local, "config", "user.name", "t")
        _git(local, "config", "commit.gpgsign", "false")
        _git(local, "checkout", "-q", BRANCH)

        # Advance origin via a second clone (the "worker pushed a round-2 fix"
        # case #13819 describes) -- touches f.txt's TOP line only.
        pusher = tmp_path / "pusher"
        _git(tmp_path, "clone", "-q", str(origin), str(pusher))
        _git(pusher, "config", "user.email", "t@t.io")
        _git(pusher, "config", "user.name", "t")
        _git(pusher, "config", "commit.gpgsign", "false")
        _git(pusher, "checkout", "-q", BRANCH)
        origin_head = _commit(
            pusher, "f.txt", f"top-fixed\n{pad}\nbottom\n", "the fix commit",
        )
        _git(pusher, "push", "-q", "origin", BRANCH)

        # Local is still at base (behind) AND has an uncommitted change to
        # the SAME file's BOTTOM line -- routine mid-cycle agent state (an
        # in-flight edit to a file the incoming fix happens to also touch,
        # far enough away in the file that the two edits don't overlap).
        (local / "f.txt").write_text(f"top\n{pad}\nbottom-uncommitted-local-edit\n")

        result = _run_sync_real(local)
        assert result.returncode == 0, (
            f"task-begin must not abort on a dirty tree (#13819): {result.stderr}"
        )
        assert _git(local, "rev-parse", "HEAD").stdout.strip() == origin_head, \
            "did not fast-forward to origin head"
        restored = (local / "f.txt").read_text()
        assert "top-fixed" in restored, "fast-forward's own change is missing"
        assert "bottom-uncommitted-local-edit" in restored, \
            "uncommitted local change was not restored after the fast-forward"

    def test_clean_tree_leaves_preexisting_unrelated_stash_alone(self, tmp_path):
        """#13167-safety against real git: an unrelated pre-existing stash
        entry must survive a clean-tree fast-forward untouched."""
        seed = _init_repo(tmp_path / "seed")
        _commit(seed, "f.txt", "base\n", "base")
        _git(seed, "branch", "-M", BRANCH)
        origin = tmp_path / "origin.git"
        _git(tmp_path, "clone", "--bare", "-q", str(seed), str(origin))
        local = tmp_path / "local"
        _git(tmp_path, "clone", "-q", str(origin), str(local))
        _git(local, "config", "user.email", "t@t.io")
        _git(local, "config", "user.name", "t")
        _git(local, "config", "commit.gpgsign", "false")
        _git(local, "checkout", "-q", BRANCH)

        pusher = tmp_path / "pusher"
        _git(tmp_path, "clone", "-q", str(origin), str(pusher))
        _git(pusher, "config", "user.email", "t@t.io")
        _git(pusher, "config", "user.name", "t")
        _git(pusher, "config", "commit.gpgsign", "false")
        _git(pusher, "checkout", "-q", BRANCH)
        origin_head = _commit(pusher, "f.txt", "base\nfix\n", "the fix commit")
        _git(pusher, "push", "-q", "origin", BRANCH)

        # A pre-existing, UNRELATED stash entry (e.g. left over from an
        # earlier, unrelated interruption) -- must never be touched.
        (local / "unrelated.txt").write_text("unrelated stashed work\n")
        _git(local, "add", "unrelated.txt")
        _git(local, "stash", "push", "-q", "-m", "pre-existing unrelated stash")
        stash_before = _git(local, "stash", "list").stdout

        result = _run_sync_real(local)
        assert result.returncode == 0, result.stderr
        assert _git(local, "rev-parse", "HEAD").stdout.strip() == origin_head

        stash_after = _git(local, "stash", "list").stdout
        assert stash_after == stash_before, \
            "a clean-tree fast-forward must never touch a pre-existing unrelated stash"
