"""Tests for references/scripts/git_ops.py — mocked subprocess, no real git."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Allow import from references/scripts/
SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


# ---------------------------------------------------------------------------
# _run / _run_list subprocess timeout (#13262)
# ---------------------------------------------------------------------------

class TestRunTimeout:
    def test_run_passes_default_timeout(self):
        with patch("git_ops.subprocess.run") as sp:
            sp.return_value = _mock_result()
            git_ops._run("git status", check=False)
        assert sp.call_args.kwargs["timeout"] == git_ops.DEFAULT_GIT_TIMEOUT

    def test_run_list_passes_default_timeout(self):
        with patch("git_ops.subprocess.run") as sp:
            sp.return_value = _mock_result()
            git_ops._run_list(["git", "status"], check=False)
        assert sp.call_args.kwargs["timeout"] == git_ops.DEFAULT_GIT_TIMEOUT

    def test_per_call_timeout_override(self):
        with patch("git_ops.subprocess.run") as sp:
            sp.return_value = _mock_result()
            git_ops._run("git status", check=False, timeout=7)
        assert sp.call_args.kwargs["timeout"] == 7

    def test_env_override_respected(self, monkeypatch):
        monkeypatch.setenv("SQUIDSQUAD_GIT_TIMEOUT", "42")
        assert git_ops._git_timeout() == 42

    def test_env_override_ignored_when_invalid(self, monkeypatch):
        monkeypatch.setenv("SQUIDSQUAD_GIT_TIMEOUT", "not-an-int")
        assert git_ops._git_timeout() == git_ops.DEFAULT_GIT_TIMEOUT
        monkeypatch.setenv("SQUIDSQUAD_GIT_TIMEOUT", "0")  # non-positive → ignore
        assert git_ops._git_timeout() == git_ops.DEFAULT_GIT_TIMEOUT

    def test_timeout_check_false_returns_nonzero_result(self):
        """A hung git with check=False must fail fast into the existing
        non-zero recovery path, NOT raise (#13262)."""
        with patch("git_ops.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("git pull", 300)):
            res = git_ops._run("git pull", check=False)
        assert res.returncode == 124
        assert "timed out" in res.stderr

    def test_timeout_check_true_raises_called_process_error(self):
        """With check=True the timeout mirrors subprocess's check-failure
        contract (raises CalledProcessError) so check=True callers' expectations
        hold."""
        with patch("git_ops.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("git pull", 300)):
            with pytest.raises(subprocess.CalledProcessError) as ei:
                git_ops._run("git pull", check=True)
        assert ei.value.returncode == 124

    def test_run_list_timeout_check_false_returns_nonzero(self):
        with patch("git_ops.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(["git", "pull"], 300)):
            res = git_ops._run_list(["git", "pull"], check=False)
        assert res.returncode == 124
        assert "timed out" in res.stderr

    def test_run_list_timeout_check_true_raises(self):
        """Symmetry with _run: _run_list + check=True + timeout raises."""
        with patch("git_ops.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(["git", "fetch"], 300)):
            with pytest.raises(subprocess.CalledProcessError) as ei:
                git_ops._run_list(["git", "fetch"], check=True)
        assert ei.value.returncode == 124

    def test_commit_routes_through_run_list_with_timeout(self):
        """#13262: commit() must go through the timeout-protected _run_list (not a
        raw subprocess.run), so a hung commit / pre-commit hook fails fast."""
        with patch("git_ops._run_list") as rl, patch("git_ops._get_alias",
                                                      return_value="skill"):
            rl.return_value = _mock_result(returncode=0)
            git_ops.commit("skill", "msg")
        assert rl.called
        assert rl.call_args[0][0][:2] == ["git", "commit"]


# ---------------------------------------------------------------------------
# _log_diagnostic subprocess timeout (#13279 — last unguarded git_ops subprocess)
# ---------------------------------------------------------------------------

class TestLogDiagnosticTimeout:
    def test_log_diagnostic_passes_default_timeout(self):
        """#13279: the fire-and-forget _log_diagnostic subprocess.run must carry a
        timeout= so a hung diagnostics.py can't block the calling thread (some
        callers run under the #13211 _ENSURE_MAIN_LOCK). Completes #13262."""
        with patch("git_ops.subprocess.run") as sp:
            sp.return_value = _mock_result()
            git_ops._log_diagnostic("warning", "boom")
        assert sp.call_args.kwargs["timeout"] == git_ops.DEFAULT_GIT_TIMEOUT

    def test_log_diagnostic_honors_env_timeout_override(self, monkeypatch):
        """The timeout resolves through _git_timeout(), so the env override applies."""
        monkeypatch.setenv("SQUIDSQUAD_GIT_TIMEOUT", "11")
        with patch("git_ops.subprocess.run") as sp:
            sp.return_value = _mock_result()
            git_ops._log_diagnostic("error", "boom")
        assert sp.call_args.kwargs["timeout"] == 11

    def test_log_diagnostic_swallows_timeout_expired(self):
        """A hung diagnostics.py (TimeoutExpired) must be swallowed by the existing
        except — _log_diagnostic stays fire-and-forget and never crashes the caller."""
        with patch("git_ops.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("diagnostics.py", 300)):
            # must not raise
            git_ops._log_diagnostic("error", "boom")


# ---------------------------------------------------------------------------
# pull()
# ---------------------------------------------------------------------------

class TestPull:
    @patch("git_ops._run")
    def test_clean_pull(self, mock_run):
        mock_run.return_value = _mock_result()
        assert git_ops.pull() is True
        mock_run.assert_called_once()

    @patch("git_ops._run")
    def test_first_pull_is_no_rebase(self, mock_run):
        """#13267: the FIRST pull must be pinned to `git pull --no-rebase` (never
        a bare pull that could rebase under pull.rebase=true and leave a REBASE
        state the #13261 recovery can't clear)."""
        mock_run.return_value = _mock_result()
        git_ops.pull()
        assert mock_run.call_args_list[0][0][0] == "git pull --no-rebase"

    @patch("git_ops._run")
    def test_pull_stash_pop(self, mock_run):
        """Dirty tree → stash CREATES an entry (refs/stash changes), pull, pop."""
        mock_run.side_effect = [
            _mock_result(returncode=1),          # pull fails
            _mock_result(returncode=1),          # _stash_top_ref pre: no refs/stash → ""
            _mock_result(),                      # git stash
            _mock_result(stdout="newsha"),       # _stash_top_ref post: new stash → "newsha"
            _mock_result(),                      # pull (retry)
            _mock_result(),                      # _safe_stash_pop: git stash pop (clean)
        ]
        assert git_ops.pull() is True
        assert mock_run.call_count == 6
        assert any(c[0][0] == "git stash pop" for c in mock_run.call_args_list)

    @patch("git_ops._run")
    def test_pull_clean_tree_does_not_pop_preexisting_stash(self, mock_run):
        """#13167 ROOT-CAUSE: on a clean tree `git stash` is a no-op (refs/stash
        UNCHANGED). The pop MUST be skipped — otherwise a PRE-EXISTING ancient
        stash is applied, writing conflict markers tree-wide and breaking
        compose. Asserts NO `git stash pop` (and no `_safe_stash_pop` machinery)
        runs when the stash created nothing."""
        mock_run.side_effect = [
            _mock_result(returncode=1),          # pull fails
            _mock_result(stdout="oldsha"),       # _stash_top_ref pre: pre-existing stash
            _mock_result(),                      # git stash (no-op on clean tree)
            _mock_result(stdout="oldsha"),       # _stash_top_ref post: UNCHANGED → stashed=False
            _mock_result(),                      # pull (retry) succeeds
        ]
        assert git_ops.pull() is True
        calls = [c[0][0] for c in mock_run.call_args_list]
        assert "git stash pop" not in calls, "must NOT pop a pre-existing stash on a clean tree"
        assert mock_run.call_count == 5  # no pop call

    @patch("git_ops._run")
    def test_pull_clean_tree_pull_fail_does_not_pop_preexisting(self, mock_run):
        """#13167: even on the pull-fail branch, a no-op stash must not pop a
        pre-existing stash (the raw-pop-on-failure path was a culprit too)."""
        mock_run.side_effect = [
            _mock_result(returncode=1),          # pull fails
            _mock_result(stdout="oldsha"),       # pre
            _mock_result(),                      # git stash (no-op)
            _mock_result(stdout="oldsha"),       # post: unchanged → stashed=False
            _mock_result(returncode=1),          # pull retry ALSO fails
            _mock_result(returncode=1),          # #13261: git merge --abort (no merge → no-op)
        ]
        assert git_ops.pull() is False
        calls = [c[0][0] for c in mock_run.call_args_list]
        assert "git stash pop" not in calls

    @patch("git_ops._run")
    def test_pull_retry_fail_aborts_merge_before_pop(self, mock_run):
        """#13261: a genuine-divergence conflict on the retry pull leaves the
        clone MERGING (MERGE_HEAD + conflict markers). pull() MUST `git merge
        --abort` BEFORE restoring our stash — otherwise _safe_stash_pop misreads
        the merge's unmerged paths as a stash-pop conflict and DROPS our stash,
        and a lingering MERGE_HEAD breaks the next clean-tree op. Mirrors the
        deploy-path fix in _safe_pull_in_clone (#13215)."""
        mock_run.side_effect = [
            _mock_result(returncode=1),          # pull fails
            _mock_result(returncode=1),          # _stash_top_ref pre → ""
            _mock_result(),                      # git stash (creates entry)
            _mock_result(stdout="newsha"),       # _stash_top_ref post → stashed=True
            _mock_result(returncode=1),          # pull retry FAILS (left MERGING)
            _mock_result(),                      # git merge --abort
            _mock_result(),                      # _safe_stash_pop: git stash pop (clean)
        ]
        assert git_ops.pull() is False
        calls = [c[0][0] for c in mock_run.call_args_list]
        assert "git merge --abort" in calls, "must abort the in-progress merge"
        assert "git stash pop" in calls, "must restore our genuinely-created stash"
        assert calls.index("git merge --abort") < calls.index("git stash pop"), \
            "merge --abort MUST precede stash pop so the pop sees a clean tree"
        # #13261: the retry must be a MERGE pull so `git merge --abort` is the
        # correct cleanup verb (never a rebase, which the abort cannot clear).
        assert "git pull --no-rebase" in calls, "retry pull must be pinned to merge"

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_pull_stash_pop_conflict(self, mock_run, mock_run_list):
        """Stash pop conflict → conflicted paths restored to HEAD + stash
        dropped, still returns True (#4829 + #13045)."""
        mock_run.side_effect = [
            _mock_result(returncode=1),                       # pull fails
            _mock_result(returncode=1),                       # _stash_top_ref pre → ""
            _mock_result(),                                   # stash
            _mock_result(stdout="newsha"),                    # _stash_top_ref post → stashed
            _mock_result(),                                   # pull (retry)
            _mock_result(returncode=1),                       # stash pop conflict
            _mock_result(stdout=".squidsquad/config.md\n"),   # diff --diff-filter=U
            _mock_result(),                                   # stash drop
        ]
        mock_run_list.return_value = _mock_result()           # checkout HEAD -- path
        assert git_ops.pull() is True

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_pull_stash_pop_conflict_drops_stash(self, mock_run, mock_run_list):
        """Regression #4829: a conflicted stash pop must still call git stash
        drop (no stash-entry leak)."""
        mock_run.side_effect = [
            _mock_result(returncode=1),                       # pull fails
            _mock_result(returncode=1),                       # _stash_top_ref pre
            _mock_result(),                                   # stash
            _mock_result(stdout="newsha"),                    # _stash_top_ref post
            _mock_result(),                                   # pull (retry)
            _mock_result(returncode=1),                       # stash pop conflict
            _mock_result(stdout=".squidsquad/config.md\n"),   # diff --diff-filter=U
            _mock_result(),                                   # stash drop
        ]
        mock_run_list.return_value = _mock_result()
        git_ops.pull()
        assert any(c[0][0] == "git stash drop" for c in mock_run.call_args_list), \
            "conflicted pop must drop the retained stash"

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_pull_stash_pop_conflict_restores_conflicted_paths_to_head(
            self, mock_run, mock_run_list):
        """#13045: a conflicted stash pop must restore every unmerged path to
        the pulled HEAD (removing the `<<<<<<<` markers git wrote) — NOT just
        drop the stash. Asserts `git checkout HEAD -- <path>` is issued for the
        conflicted config.md so compose never sees a corrupt file."""
        mock_run.side_effect = [
            _mock_result(returncode=1),                       # pull fails
            _mock_result(returncode=1),                       # _stash_top_ref pre
            _mock_result(),                                   # stash
            _mock_result(stdout="newsha"),                    # _stash_top_ref post
            _mock_result(),                                   # pull (retry)
            _mock_result(returncode=1),                       # stash pop conflict
            _mock_result(stdout=".squidsquad/config.md\nreferences/x.py\n"),  # diff -U
            _mock_result(),                                   # stash drop
        ]
        mock_run_list.return_value = _mock_result()
        git_ops.pull()
        checkouts = [c[0][0] for c in mock_run_list.call_args_list]
        assert ["git", "checkout", "HEAD", "--", ".squidsquad/config.md"] in checkouts
        assert ["git", "checkout", "HEAD", "--", "references/x.py"] in checkouts


class TestStashTopRef:
    @patch("git_ops._run")
    def test_returns_sha_when_stash_exists(self, mock_run):
        mock_run.return_value = _mock_result(stdout="abc123\n", returncode=0)
        assert git_ops._stash_top_ref() == "abc123"

    @patch("git_ops._run")
    def test_returns_empty_when_no_stash(self, mock_run):
        # `git rev-parse --quiet --verify refs/stash` exits non-zero when there
        # is no stash ref — must map to "" (not a spurious ref).
        mock_run.return_value = _mock_result(stdout="", returncode=1)
        assert git_ops._stash_top_ref() == ""


# ---------------------------------------------------------------------------
# add_all()
# ---------------------------------------------------------------------------

class TestAddAll:
    @patch("git_ops._run")
    def test_stages_all(self, mock_run):
        mock_run.return_value = _mock_result()
        git_ops.add_all()
        mock_run.assert_called_once_with("git add -A")


# ---------------------------------------------------------------------------
# commit()
# ---------------------------------------------------------------------------

class TestCommit:
    @patch("subprocess.run")
    def test_successful_commit(self, mock_run):
        mock_run.return_value = _mock_result(stdout="[main abc1234] skill: msg")
        assert git_ops.commit("skill", "test message") is True
        args = mock_run.call_args
        assert args[0][0][0] == "git"
        assert args[0][0][1] == "commit"
        # Check message contains role prefix
        msg = args[0][0][3]
        assert msg.startswith("skill: test message")
        assert "Co-Authored-By:" in msg

    @patch("subprocess.run")
    def test_nothing_to_commit(self, mock_run):
        mock_run.return_value = _mock_result(
            stdout="nothing to commit, working tree clean",
            returncode=1,
        )
        assert git_ops.commit("skill", "msg") is False

    @patch("subprocess.run")
    def test_commit_error(self, mock_run):
        mock_run.return_value = _mock_result(
            stderr="fatal: some error", returncode=1,
        )
        assert git_ops.commit("skill", "msg") is False


# ---------------------------------------------------------------------------
# push()
# ---------------------------------------------------------------------------

class TestPush:
    @patch("git_ops._run")
    @patch("git_ops._git_push")
    def test_successful_push(self, mock_git_push, mock_run):
        mock_git_push.return_value = _mock_result()
        mock_run.return_value = _mock_result(stdout="main\n")  # branch --show-current
        assert git_ops.push() is True

    @patch("git_ops._run")
    @patch("git_ops._git_push")
    def test_push_failure(self, mock_git_push, mock_run):
        mock_git_push.return_value = _mock_result(stderr="rejected", returncode=1)
        assert git_ops.push() is False


# ---------------------------------------------------------------------------
# pull/push role propagation (#5782)
# ---------------------------------------------------------------------------

class TestPullEmitsRole:
    @patch("git_ops._emit")
    @patch("git_ops._run")
    def test_pull_emits_role(self, mock_run, mock_emit):
        """pull(role='pm') passes role to _emit()."""
        mock_run.return_value = _mock_result()
        git_ops.pull(role="pm")
        mock_emit.assert_called()
        _, kwargs = mock_emit.call_args
        assert kwargs.get("role") == "pm"

    @patch("git_ops._emit")
    @patch("git_ops._run")
    def test_pull_without_role_backward_compat(self, mock_run, mock_emit):
        """pull() without role still works (role=None passed to _emit)."""
        mock_run.return_value = _mock_result()
        git_ops.pull()
        mock_emit.assert_called()
        _, kwargs = mock_emit.call_args
        assert kwargs.get("role") is None


class TestPushEmitsRole:
    @patch("git_ops._emit")
    @patch("git_ops._run")
    @patch("git_ops._git_push")
    def test_push_emits_role(self, mock_git_push, mock_run, mock_emit):
        """push(role='skill') passes role to _emit()."""
        mock_git_push.return_value = _mock_result()
        mock_run.return_value = _mock_result(stdout="main\n")
        git_ops.push(role="skill")
        mock_emit.assert_called()
        _, kwargs = mock_emit.call_args
        assert kwargs.get("role") == "skill"

    @patch("git_ops._emit")
    @patch("git_ops._run")
    @patch("git_ops._git_push")
    def test_push_without_role_backward_compat(self, mock_git_push, mock_run, mock_emit):
        """push() without role still works (role=None passed to _emit)."""
        mock_git_push.return_value = _mock_result()
        mock_run.return_value = _mock_result(stdout="main\n")
        git_ops.push()
        mock_emit.assert_called()
        _, kwargs = mock_emit.call_args
        assert kwargs.get("role") is None


# ---------------------------------------------------------------------------
# commit_push()
# ---------------------------------------------------------------------------

class TestCommitPush:
    @patch("git_ops.push", return_value=True)
    @patch("git_ops.commit", return_value=True)
    @patch("git_ops.add_all")
    def test_full_workflow(self, mock_add, mock_commit, mock_push):
        assert git_ops.commit_push("skill", "msg") is True
        mock_add.assert_called_once()
        mock_commit.assert_called_once_with("skill", "msg")
        mock_push.assert_called_once()

    @patch("git_ops.push")
    @patch("git_ops.commit", return_value=False)
    @patch("git_ops.add_all")
    def test_nothing_to_commit_skips_push(self, mock_add, mock_commit, mock_push):
        assert git_ops.commit_push("skill", "msg") is False
        mock_push.assert_not_called()


# ---------------------------------------------------------------------------
# has_changes()
# ---------------------------------------------------------------------------

class TestHasChanges:
    @patch("git_ops._run")
    def test_dirty_tree(self, mock_run):
        mock_run.return_value = _mock_result(stdout=" M some/file.py\n")
        assert git_ops.has_changes() is True

    @patch("git_ops._run")
    def test_clean_tree(self, mock_run):
        mock_run.return_value = _mock_result(stdout="")
        assert git_ops.has_changes() is False


# ---------------------------------------------------------------------------
# last_hash()
# ---------------------------------------------------------------------------

class TestLastHash:
    @patch("git_ops._run")
    def test_returns_hash(self, mock_run):
        mock_run.return_value = _mock_result(stdout="abc1234\n")
        assert git_ops.last_hash() == "abc1234"


# ---------------------------------------------------------------------------
# branch_create() / branch_switch()
# ---------------------------------------------------------------------------

class TestBranching:
    @patch("git_ops._run_list")
    def test_branch_create(self, mock_run):
        mock_run.return_value = _mock_result()
        git_ops.branch_create("feature/test")
        mock_run.assert_called_once_with(["git", "checkout", "-b", "feature/test"])

    @patch("git_ops._run_list")
    def test_branch_switch(self, mock_run):
        mock_run.return_value = _mock_result()
        git_ops.branch_switch("main")
        mock_run.assert_called_once_with(["git", "checkout", "main"])

    @patch("git_ops._run_list")
    def test_branch_create_failure(self, mock_run):
        """branch_create raises on git failure (check=True default)."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, "git")
        with pytest.raises(CalledProcessError):
            git_ops.branch_create("bad/branch")

    @patch("git_ops._run_list")
    def test_branch_switch_failure(self, mock_run):
        """branch_switch raises on git failure (check=True default)."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, "git")
        with pytest.raises(CalledProcessError):
            git_ops.branch_switch("nonexistent")


# ---------------------------------------------------------------------------
# pr_create()
# ---------------------------------------------------------------------------

class TestPrCreate:
    @patch("git_ops._run_list")
    def test_successful_pr(self, mock_run):
        mock_run.return_value = _mock_result(
            stdout="https://github.com/org/repo/pull/42\n"
        )
        url = git_ops.pr_create("title", "body")
        assert url == "https://github.com/org/repo/pull/42"

    @patch("git_ops._run_list")
    def test_pr_failure(self, mock_run):
        mock_run.return_value = _mock_result(
            stderr="error", returncode=1,
        )
        assert git_ops.pr_create("title", "body") is None


# ---------------------------------------------------------------------------
# _get_alias()
# ---------------------------------------------------------------------------

class TestPrMerge:
    @pytest.fixture(autouse=True)
    def _safe_behind(self):
        # #13271: default the behind-count guard to "current" (0) so the existing
        # merge-flow tests below exercise the merge path unchanged; the dedicated
        # guard tests re-patch _pr_behind_by to a high value to assert the refusal.
        # #13285: stub the post-merge scope-audit to a no-op so it does not consume
        # the per-test _run_list mock sequence (the audit has its own tests in
        # TestScopeAudit13285).
        with patch("git_ops._pr_behind_by", return_value=0), \
                patch("git_ops._post_merge_scope_audit"):
            yield

    @patch("git_ops._run_list")
    def test_successful_squash_merge(self, mock_run):
        # Calls: 1) check state, 2) merge, 3) branch name lookup, 4) ship transition
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stdout=""),
            _mock_result(stdout='{"headRefName": "squidsquad/skill/42"}'),
            _mock_result(stdout="#42: status:pending-ship -> status:shipped"),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is True
        assert msg == "merged"
        # Verify squash merge was called
        merge_call = mock_run.call_args_list[1]
        assert "--squash" in merge_call[0][0]
        assert "--delete-branch" in merge_call[0][0]

    @patch("git_ops._run_list")
    def test_merge_extracts_linked_issue_from_branch(self, mock_run):
        """pr-merge extracts linked issue number from branch name."""
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stdout=""),  # merge succeeds
            _mock_result(stdout='{"headRefName": "squidsquad/skill/99"}'),
        ]
        success, msg = git_ops.pr_merge(99)
        assert success is True
        assert msg == "merged"
        # 3rd call fetches branch name to extract issue number
        branch_call = mock_run.call_args_list[2]
        assert "headRefName" in str(branch_call)

    @patch("git_ops._run_list")
    def test_already_merged(self, mock_run):
        mock_run.return_value = _mock_result(stdout='{"state": "MERGED"}')
        success, msg = git_ops.pr_merge(42)
        assert success is True
        assert msg == "already merged"
        # Should only call once (state check), no merge attempt
        assert mock_run.call_count == 1

    @patch("git_ops._run_list")
    def test_closed_without_merge(self, mock_run):
        mock_run.return_value = _mock_result(stdout='{"state": "CLOSED"}')
        success, msg = git_ops.pr_merge(42)
        assert success is False
        assert "closed" in msg.lower()

    @patch("git_ops._run_list")
    def test_merge_conflict(self, mock_run):
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stderr="not mergeable: merge conflict", returncode=1),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is False
        assert "merge conflict" in msg

    @patch("git_ops._run_list")
    def test_unexpected_failure(self, mock_run):
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stderr="permission denied", returncode=1),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is False
        assert "merge failed" in msg

    @patch("git_ops._run_list")
    def test_custom_strategy(self, mock_run):
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stdout=""),
            _mock_result(stdout='{"headRefName": "feature"}'),
        ]
        git_ops.pr_merge(42, strategy="rebase")
        merge_call = mock_run.call_args_list[1]
        assert "--rebase" in merge_call[0][0]

    # --- #10540: "Base branch was modified" batch-ship race retry ---

    @patch("git_ops._run_list")
    def test_base_modified_retries_then_succeeds(self, mock_run):
        """The transient batch-ship race is retried and succeeds once the base
        settles — distinct from a terminal failure."""
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),                       # state check
            _mock_result(stderr="GraphQL: Base branch was modified. Review and try the merge again.", returncode=1),  # attempt 1
            _mock_result(stderr="GraphQL: Base branch was modified.", returncode=1),  # attempt 2
            _mock_result(stdout=""),                                        # attempt 3 — success
            _mock_result(stdout='{"headRefName": "squidsquad/skill/42"}'),  # branch lookup
        ]
        success, msg = git_ops.pr_merge(42, _base_retry_delay=0)
        assert success is True
        assert msg == "merged"
        # 1 state check + 3 merge attempts + 1 branch lookup = 5 calls
        assert mock_run.call_count == 5

    @patch("git_ops._run_list")
    def test_base_modified_exhausts_retries(self, mock_run):
        """If the race never clears within the retry budget, it fails as a
        merge-failed (not silently, not as a conflict)."""
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
        ] + [
            _mock_result(stderr="GraphQL: Base branch was modified.", returncode=1)
            for _ in range(4)  # _max_base_retries=3 → 4 attempts (initial + 3 retries)
        ]
        success, msg = git_ops.pr_merge(42, _max_base_retries=3, _base_retry_delay=0)
        assert success is False
        assert "merge failed" in msg
        assert "Base branch was modified" in msg
        # 1 state check + 4 merge attempts = 5 calls (no branch lookup on failure)
        assert mock_run.call_count == 5

    @patch("git_ops._run_list")
    def test_real_conflict_is_terminal_not_retried(self, mock_run):
        """A real merge conflict must NOT be retried (it routes back for rebase)
        — only ONE merge attempt, even though retries are available."""
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stderr="failed to merge: merge conflict between base and head", returncode=1),
        ]
        success, msg = git_ops.pr_merge(42, _max_base_retries=3, _base_retry_delay=0)
        assert success is False
        assert msg == "merge conflict"
        # 1 state check + exactly 1 merge attempt (no retry)
        assert mock_run.call_count == 2

    @patch("git_ops._run_list")
    def test_base_modified_then_real_conflict(self, mock_run):
        """A retry can surface a real conflict (base moved into a true conflict)
        — once it does, it's terminal, not retried further."""
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stderr="GraphQL: Base branch was modified.", returncode=1),  # race
            _mock_result(stderr="not mergeable: merge conflict", returncode=1),        # now a real conflict
        ]
        success, msg = git_ops.pr_merge(42, _max_base_retries=3, _base_retry_delay=0)
        assert success is False
        assert msg == "merge conflict"
        assert mock_run.call_count == 3  # state + race attempt + conflict attempt

    @patch("git_ops._run_list")
    def test_state_check_fails_still_attempts_merge(self, mock_run):
        # State check fails (non-zero), merge succeeds, branch lookup
        mock_run.side_effect = [
            _mock_result(returncode=1, stderr="not found"),
            _mock_result(stdout=""),
            _mock_result(stdout='{"headRefName": "feature"}'),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is True
        assert msg == "merged"


    @patch("git_ops._run_list")
    def test_forge_adapter_routing(self, mock_run):
        """When forge provider is non-GitHub, pr_merge uses the adapter."""
        mock_adapter = MagicMock()
        mock_adapter.view_pr.return_value = {"state": "OPEN"}
        mock_adapter.merge_pr.return_value = (True, "merged")

        mock_config = {"provider": "forgejo", "endpoint": "http://localhost:3000"}

        with patch.dict("sys.modules", {
            "forge_adapter": MagicMock(
                get_adapter=MagicMock(return_value=mock_adapter),
                _read_forge_config=MagicMock(return_value=mock_config),
            ),
        }):
            # Need to re-import to pick up the mock
            success, msg = git_ops.pr_merge(42)

        assert success is True
        assert msg == "merged"
        mock_adapter.view_pr.assert_called_once_with(42)
        mock_adapter.merge_pr.assert_called_once_with(42, "squash")
        # gh CLI should NOT be called when adapter handles it
        mock_run.assert_not_called()

    # --- #13271: behind-count merge guard (SEV-1 stale-tree prevention) ---

    @patch("git_ops._run_list")
    def test_far_behind_squash_is_refused(self, mock_run):
        """A squash of a branch FAR behind base is refused (fail-safe) BEFORE any
        merge call — preventing the #13271 stale-tree mass-revert."""
        with patch("git_ops._pr_behind_by", return_value=154), \
             patch("git_ops._merge_max_behind", return_value=50):
            mock_run.side_effect = [_mock_result(stdout='{"state": "OPEN"}')]
            success, msg = git_ops.pr_merge(42)
        assert success is False
        assert "behind" in msg
        # state check only — NO merge attempt (call_count==1 proves no `gh pr merge`).
        assert mock_run.call_count == 1

    @patch("git_ops._run_list")
    def test_within_threshold_proceeds(self, mock_run):
        """A branch within the behind threshold merges normally."""
        with patch("git_ops._pr_behind_by", return_value=3), \
             patch("git_ops._merge_max_behind", return_value=50):
            mock_run.side_effect = [
                _mock_result(stdout='{"state": "OPEN"}'),
                _mock_result(stdout=""),  # merge
                _mock_result(stdout='{"headRefName": "squidsquad/skill/42"}'),
            ]
            success, msg = git_ops.pr_merge(42)
        assert success is True

    @patch("git_ops._run_list")
    def test_undeterminable_behind_fails_open(self, mock_run):
        """If the behind-count can't be determined (gh/API hiccup → None), the
        guard fails OPEN (merge proceeds) — it must not wedge all shipping."""
        with patch("git_ops._pr_behind_by", return_value=None):
            mock_run.side_effect = [
                _mock_result(stdout='{"state": "OPEN"}'),
                _mock_result(stdout=""),  # merge
                _mock_result(stdout='{"headRefName": "squidsquad/skill/42"}'),
            ]
            success, msg = git_ops.pr_merge(42)
        assert success is True

    @patch("git_ops._run_list")
    def test_far_behind_non_squash_not_guarded(self, mock_run):
        """The guard is squash-specific — a real merge commit preserves base
        history, so a behind branch is not refused for strategy=merge."""
        with patch("git_ops._pr_behind_by", return_value=999):
            mock_run.side_effect = [
                _mock_result(stdout='{"state": "OPEN"}'),
                _mock_result(stdout=""),  # merge
                _mock_result(stdout='{"headRefName": "feature"}'),
            ]
            success, _ = git_ops.pr_merge(42, strategy="merge")
        assert success is True

    def test_merge_max_behind_env_override(self, monkeypatch):
        monkeypatch.setenv("SQUIDSQUAD_MERGE_MAX_BEHIND", "7")
        assert git_ops._merge_max_behind() == 7
        monkeypatch.setenv("SQUIDSQUAD_MERGE_MAX_BEHIND", "bad")
        assert git_ops._merge_max_behind() == git_ops.MERGE_MAX_BEHIND_DEFAULT


class TestPrBehindBy:
    """#13271: _pr_behind_by — kept OUT of TestPrMerge (whose autouse fixture
    patches _pr_behind_by) so these exercise the real function."""

    @patch("git_ops._run_list")
    def test_pr_behind_by_parses_compare_api(self, mock_run):
        """_pr_behind_by reads behind_by from the compare API after resolving the
        PR's base/head refs."""
        mock_run.side_effect = [
            _mock_result(stdout='{"baseRefName": "main", "headRefName": "squidsquad/task/42"}'),
            _mock_result(stdout="154\n"),  # gh api .behind_by
        ]
        assert git_ops._pr_behind_by(42) == 154

    @patch("git_ops._run_list")
    def test_pr_behind_by_none_on_api_failure(self, mock_run):
        mock_run.side_effect = [
            _mock_result(stdout='{"baseRefName": "main", "headRefName": "x"}'),
            _mock_result(returncode=1, stderr="api error"),
        ]
        assert git_ops._pr_behind_by(42) is None

    @patch("git_ops._run_list")
    def test_pr_behind_by_none_on_bad_refs_json(self, mock_run):
        mock_run.side_effect = [_mock_result(stdout="not json", returncode=0)]
        assert git_ops._pr_behind_by(42) is None

    @patch("git_ops._run_list")
    def test_pr_behind_by_none_when_refs_view_fails(self, mock_run):
        """First `gh pr view` call non-zero (refs lookup failed) → None (fail-open)."""
        mock_run.side_effect = [_mock_result(returncode=1, stderr="not found")]
        assert git_ops._pr_behind_by(42) is None

    @patch("git_ops._run_list")
    def test_pr_behind_by_none_on_non_integer_behind(self, mock_run):
        """A malformed compare response (e.g. `null`) → ValueError → None."""
        mock_run.side_effect = [
            _mock_result(stdout='{"baseRefName": "main", "headRefName": "x"}'),
            _mock_result(stdout="null\n"),  # not an int
        ]
        assert git_ops._pr_behind_by(42) is None


class TestNoNonAsciiInPrintStatements:
    """Regression test for #3800: UnicodeEncodeError on Windows cp1252 console."""

    def test_print_statements_are_ascii_safe(self):
        """All print() calls in git_ops.py must use only ASCII characters."""
        source_path = SCRIPTS / "git_ops.py"
        with open(source_path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if "print(" in line:
                    for col, ch in enumerate(line):
                        assert ord(ch) <= 127, (
                            f"Non-ASCII char U+{ord(ch):04X} at line {lineno}, col {col} "
                            f"in print statement: {line.rstrip()}"
                        )

    def test_stdout_encoding_safety_net(self):
        """git_ops.py reconfigures stdout to handle UTF-8 on non-UTF-8 consoles."""
        source_path = SCRIPTS / "git_ops.py"
        content = source_path.read_text(encoding="utf-8")
        assert "TextIOWrapper" in content, (
            "git_ops.py should reconfigure stdout via TextIOWrapper for encoding safety"
        )


class TestGetAlias:
    def test_fallback_to_role(self):
        """When config module unavailable, returns role name."""
        # _get_alias catches all exceptions and falls back to role
        with patch.dict("sys.modules", {"config": None}):
            result = git_ops._get_alias("skill")
            assert result == "skill"


# ---------------------------------------------------------------------------
# _parse_args()
# ---------------------------------------------------------------------------

class TestParseArgs:
    def test_help_exits(self):
        with patch.object(sys, "argv", ["git_ops.py", "--help"]):
            with pytest.raises(SystemExit):
                git_ops._parse_args()

    def test_dash_h_exits(self):
        # -h at the subcommand position prints usage and exits (#13433).
        with patch.object(sys, "argv", ["git_ops.py", "-h"]):
            with pytest.raises(SystemExit) as exc:
                git_ops._parse_args()
        assert exc.value.code == 0

    def test_no_args_exits(self):
        with patch.object(sys, "argv", ["git_ops.py"]):
            with pytest.raises(SystemExit):
                git_ops._parse_args()

    def test_parses_command(self):
        with patch.object(sys, "argv", ["git_ops.py", "pull"]):
            cmd, rest = git_ops._parse_args()
            assert cmd == "pull"
            assert rest == []

    def test_parses_command_with_args(self):
        with patch.object(sys, "argv", ["git_ops.py", "commit", "skill", "msg"]):
            cmd, rest = git_ops._parse_args()
            assert cmd == "commit"
            assert rest == ["skill", "msg"]


# ---------------------------------------------------------------------------
# pr-merge dispatch arg guard (#13433)
# ---------------------------------------------------------------------------

class TestPrMergeArgGuard:
    """`pr-merge` must validate the PR number BEFORE any side effect. Previously
    `pr-merge --help` (and other non-numeric first args) reached pr_merge(), which
    runs a real squash-merge + post-merge compose — dirtying the tree and printing
    a false 'PR #--help merged (squash)'. These tests assert pr_merge is never
    invoked with a bogus PR number."""

    def _run_main(self, argv, monkeypatch):
        spy = MagicMock(return_value=(True, "ok"))
        monkeypatch.setattr(git_ops, "pr_merge", spy)
        # Keep the dispatch hermetic — main() self-heals git hooks otherwise.
        monkeypatch.setattr(git_ops, "_ensure_hooks_installed", lambda: None)
        monkeypatch.setattr(sys, "argv", ["git_ops.py"] + argv)
        with pytest.raises(SystemExit) as exc:
            git_ops.main()
        return spy, exc.value.code

    def test_help_does_not_merge(self, monkeypatch):
        spy, code = self._run_main(["pr-merge", "--help"], monkeypatch)
        spy.assert_not_called()
        assert code == 0  # help is a successful request

    def test_dash_h_does_not_merge(self, monkeypatch):
        spy, code = self._run_main(["pr-merge", "-h"], monkeypatch)
        spy.assert_not_called()
        assert code == 0

    def test_missing_number_is_usage_error(self, monkeypatch):
        spy, code = self._run_main(["pr-merge"], monkeypatch)
        spy.assert_not_called()
        assert code == 1  # missing required arg

    def test_non_numeric_is_rejected(self, monkeypatch):
        spy, code = self._run_main(["pr-merge", "notanumber"], monkeypatch)
        spy.assert_not_called()
        assert code == 2  # invalid usage, distinct from a merge failure (1)

    def test_flag_in_number_position_is_rejected(self, monkeypatch):
        # `pr-merge --strategy squash` (forgot the number) must NOT merge.
        spy, code = self._run_main(["pr-merge", "--strategy", "squash"], monkeypatch)
        spy.assert_not_called()
        assert code == 2

    def test_valid_number_merges(self, monkeypatch):
        spy, code = self._run_main(["pr-merge", "13523"], monkeypatch)
        spy.assert_called_once_with("13523", "squash")
        assert code == 0

    def test_valid_number_honors_strategy(self, monkeypatch):
        spy, code = self._run_main(["pr-merge", "13523", "--strategy", "merge"], monkeypatch)
        spy.assert_called_once_with("13523", "merge")
        assert code == 0


# ---------------------------------------------------------------------------
# _is_state_file()
# ---------------------------------------------------------------------------

class TestIsStateFile:
    def test_squidsquad_files(self):
        assert git_ops._is_state_file(".squidsquad/skill/working-state.md") is True
        assert git_ops._is_state_file(".squidsquad/pm/planning/CONTEXT.md") is True

    def test_claude_files(self):
        assert git_ops._is_state_file(".claude/scheduled_tasks.lock") is True
        assert git_ops._is_state_file(".claude/settings.local.json") is True

    def test_code_files(self):
        assert git_ops._is_state_file("references/scripts/git_ops.py") is False
        assert git_ops._is_state_file("tests/test_git_ops.py") is False
        assert git_ops._is_state_file("src/main.py") is False


# ---------------------------------------------------------------------------
# commit_code()
# ---------------------------------------------------------------------------

class TestCommitCode:
    @patch("git_ops._git_push")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("subprocess.run")
    def test_splits_code_from_state(self, mock_subproc, mock_run, mock_run_list, mock_git_push):
        """commit_code only stages non-.squidsquad/ files."""
        # git status --porcelain: XY<space>path (3 chars prefix)
        mock_run.side_effect = [
            _mock_result(stdout=" M references/scripts/git_ops.py\n M .squidsquad/skill/working-state.md\n"),
            _mock_result(stdout="squidsquad/skill/375\n"),  # current branch
            _mock_result(stdout="main\n"),  # branch --show-current after switch back
        ]
        # rev-parse --verify (branch exists)
        mock_run_list.side_effect = [
            _mock_result(returncode=0),  # branch exists
            _mock_result(),  # git checkout branch
            _mock_result(),  # git add (code file)
            _mock_result(),  # git checkout config.md revert (#7491)
            _mock_result(),  # git checkout main
        ]
        # push now routes through _git_push (#9890)
        mock_git_push.return_value = _mock_result()
        # git commit
        mock_subproc.return_value = _mock_result(stdout="1 file changed")

        result = git_ops.commit_code("skill", "squidsquad/skill/375", "test")
        assert result is True

        # Verify only the code file was staged (not .squidsquad/)
        add_calls = [c for c in mock_run_list.call_args_list if c[0][0][0:2] == ["git", "add"]]
        assert len(add_calls) == 1
        assert add_calls[0][0][0][2] == "references/scripts/git_ops.py"

    @patch("git_ops._git_push")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("subprocess.run")
    def test_reverts_config_md_before_commit(self, mock_subproc, mock_run, mock_run_list, mock_git_push):
        """#7491: commit_code reverts config.md to working branch version."""
        mock_run.side_effect = [
            _mock_result(stdout=" M references/scripts/harness.py\n"),
            _mock_result(stdout="squidsquad/task/7491\n"),
            _mock_result(stdout="main\n"),
        ]
        mock_run_list.side_effect = [
            _mock_result(returncode=0),  # branch exists
            _mock_result(),  # git checkout branch
            _mock_result(),  # git add (code file)
            _mock_result(),  # git checkout config.md revert
            _mock_result(),  # git checkout main
        ]
        mock_git_push.return_value = _mock_result()
        mock_subproc.return_value = _mock_result(stdout="1 file changed")

        git_ops.commit_code("skill", "squidsquad/task/7491", "test fix")

        # Find the config.md revert call
        checkout_calls = [
            c for c in mock_run_list.call_args_list
            if len(c[0][0]) >= 4 and c[0][0][1] == "checkout"
            and ".squidsquad/config.md" in c[0][0]
        ]
        assert len(checkout_calls) == 1, \
            "commit_code must revert config.md to working branch (#7491)"

    @patch("git_ops._run")
    def test_no_code_changes_returns_false(self, mock_run):
        """commit_code returns False when only .squidsquad/ files changed."""
        mock_run.return_value = _mock_result(stdout=" M .squidsquad/skill/working-state.md\n")
        assert git_ops.commit_code("skill", "squidsquad/skill/375", "test") is False

    @patch("git_ops._run")
    def test_excludes_claude_state_files(self, mock_run):
        """commit_code excludes .claude/ state files from feature branches."""
        mock_run.return_value = _mock_result(
            stdout=" M .claude/scheduled_tasks.lock\n M .squidsquad/skill/working-state.md\n"
        )
        assert git_ops.commit_code("skill", "squidsquad/skill/375", "test") is False

    @patch("git_ops._run")
    def test_no_changes_returns_false(self, mock_run):
        mock_run.return_value = _mock_result(stdout="")
        assert git_ops.commit_code("skill", "squidsquad/skill/375", "test") is False


# ---------------------------------------------------------------------------
# commit_state()
# ---------------------------------------------------------------------------

class TestCommitState:
    @patch("git_ops._git_push")
    @patch("git_ops._run")
    @patch("git_ops._run_list")
    @patch("subprocess.run")
    def test_only_stages_squidsquad_files(self, mock_subproc, mock_run_list, mock_run, mock_git_push):
        """commit_state only stages .squidsquad/ files on main."""
        mock_run.side_effect = [
            _mock_result(stdout=" M references/scripts/git_ops.py\n M .squidsquad/skill/working-state.md\n"),
            _mock_result(stdout="main\n"),  # current branch
        ]
        mock_run_list.return_value = _mock_result()  # git add
        mock_git_push.return_value = _mock_result()  # state push (#9890)
        mock_subproc.return_value = _mock_result(stdout="1 file changed")

        result = git_ops.commit_state("skill", "state update")
        assert result is True

        add_calls = [c for c in mock_run_list.call_args_list if c[0][0][0:2] == ["git", "add"]]
        assert len(add_calls) == 1
        assert add_calls[0][0][0][2] == ".squidsquad/skill/working-state.md"

    @patch("git_ops._run")
    def test_errors_if_not_on_main(self, mock_run):
        """commit_state returns False if not on main branch."""
        mock_run.side_effect = [
            _mock_result(stdout=" M .squidsquad/skill/working-state.md\n"),
            _mock_result(stdout="squidsquad/skill/375\n"),  # not on main
        ]
        assert git_ops.commit_state("skill", "state update") is False

    @patch("git_ops._run")
    def test_no_state_changes_returns_false(self, mock_run):
        mock_run.return_value = _mock_result(stdout=" M references/scripts/git_ops.py\n")
        assert git_ops.commit_state("skill", "state update") is False


# ---------------------------------------------------------------------------
# commit_role_scoped() — #8691
# ---------------------------------------------------------------------------


class TestRoleOwnedPatterns:
    """Per-role commit-domain allowlists."""

    def test_common_patterns_present_for_every_role(self):
        for role in ("pm", "qa", "dm", "skill"):
            pats = git_ops._role_owned_patterns(role)
            assert f".squidsquad/{role}/" in pats
            assert ".squidsquad/.event-state.json" in pats
            assert ".squidsquad/vault/" in pats

    def test_backlog_cache_not_in_allowlist(self):
        """#11065: `.squidsquad/.backlog-cache` is gitignored and must NOT
        appear in any role's commit-domain allowlist. Tracked-and-allowlisted
        was the merge-spiral root cause behind #11042's PR #11048."""
        for role in ("pm", "qa", "dm", "skill"):
            pats = git_ops._role_owned_patterns(role)
            assert ".squidsquad/.backlog-cache" not in pats, (
                f"{role}: .backlog-cache resurrected in allowlist — "
                f"merge-spiral pattern will return"
            )

    def test_pm_extras(self):
        pats = git_ops._role_owned_patterns("pm")
        assert ".squidsquad/config.md" in pats
        assert ".squidsquad/project/" in pats

    def test_dm_extras(self):
        pats = git_ops._role_owned_patterns("dm")
        assert "README.md" in pats
        assert "CHANGELOG.md" in pats
        assert "docs/" in pats
        # #9474: DM also owns SKILL.md (doc-improvement-loop) and
        # co-owns .squidsquad/config.md (ship-counter + flag toggles).
        # Pre-#9474 these were treated as foreign and left dirty.
        assert "SKILL.md" in pats
        assert ".squidsquad/config.md" in pats

    def test_qa_extras(self):
        """#13212: qa (verifier) owns tests/comprehension/ — it authors the
        comprehension regression specs (#9184) and must be able to stage them
        in its own post-cycle commit (they live outside .squidsquad/, so they
        matched no pattern before and were left untracked as 'foreign')."""
        pats = git_ops._role_owned_patterns("qa")
        assert "tests/comprehension/" in pats
        # QA must still NOT pick up config or delivery docs / SKILL.md —
        # the new extra does not loosen the rest of the boundary.
        assert ".squidsquad/config.md" not in pats
        assert "README.md" not in pats
        assert "SKILL.md" not in pats

    def test_comprehension_specs_are_qa_only(self):
        """#13212: only the verifier authors comprehension specs — the
        tests/comprehension/ ownership must NOT bleed into other roles (else a
        non-verifier cycle could stage a half-written spec)."""
        for role in ("pm", "dm", "skill"):
            assert "tests/comprehension/" not in git_ops._role_owned_patterns(role), (
                f"{role} must not own tests/comprehension/ (#13212 — verifier-only)"
            )

    def test_pm_does_not_pick_up_dm_extras(self):
        """#9474: PM and DM co-own .squidsquad/config.md, but PM must
        NOT inherit DM's SKILL.md ownership (skill owns its own file
        through the branch+PR workflow). Sanity check on the pattern
        boundary between PM and DM."""
        pats = git_ops._role_owned_patterns("pm")
        assert "SKILL.md" not in pats
        assert "README.md" not in pats
        assert "CHANGELOG.md" not in pats


class TestPathMatches:
    def test_prefix_match(self):
        assert git_ops._path_matches(".squidsquad/pm/working-state.md", [".squidsquad/pm/"])
        assert git_ops._path_matches("docs/foo/bar.md", ["docs/"])

    def test_exact_match(self):
        assert git_ops._path_matches("README.md", ["README.md"])
        assert not git_ops._path_matches("README.md.bak", ["README.md"])

    def test_no_match(self):
        assert not git_ops._path_matches("references/scripts/foo.py", [".squidsquad/pm/"])


class TestCommitRoleScoped:
    """#8691: cycle commits must not bundle foreign files."""

    @patch("git_ops.push", return_value=True)
    @patch("git_ops.commit", return_value=True)
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_pm_stages_only_own_files_skips_foreign(
        self, mock_run, mock_run_list, mock_working_branch,
        mock_commit, mock_push, capsys,
    ):
        """The exact scenario from the bug report: PM commit + foreign code/tests."""
        # #11083: commit_role_scoped now checks current branch first; mock the
        # branch-show-current call to return the working branch, and the
        # porcelain status call to return the file list.
        def _run_side(cmd, *a, **kw):
            if "branch --show-current" in cmd:
                return _mock_result(stdout="main\n")
            return _mock_result(stdout=(
                " M .squidsquad/pm/working-state.md\n"
                " M .squidsquad/.backlog-cache\n"
                " M .squidsquad/skill/CLAUDE.md\n"
                " M references/scripts/thin_launcher.py\n"
                " M tests/test_thin_launcher.py\n"
            ))
        mock_run.side_effect = _run_side
        mock_run_list.return_value = _mock_result()

        result = git_ops.commit_role_scoped("pm", "cycle 1494")
        assert result is True

        add_calls = [c for c in mock_run_list.call_args_list
                     if c[0][0][:2] == ["git", "add"]]
        staged = [c[0][0][-1] for c in add_calls]
        assert ".squidsquad/pm/working-state.md" in staged
        # #11065: .backlog-cache no longer staged — it's gitignored, not in
        # the allowlist, and explicitly skipped per the new contract.
        assert ".squidsquad/.backlog-cache" not in staged
        assert ".squidsquad/skill/CLAUDE.md" not in staged
        assert "references/scripts/thin_launcher.py" not in staged
        assert "tests/test_thin_launcher.py" not in staged

        err = capsys.readouterr().err
        assert "outside 'pm' domain" in err
        assert "references/scripts/thin_launcher.py" in err
        assert ".squidsquad/skill/CLAUDE.md" in err
        # #11065: .backlog-cache should also be listed as skipped.
        assert ".squidsquad/.backlog-cache" in err

    @patch("git_ops.push", return_value=True)
    @patch("git_ops.commit", return_value=True)
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_skips_when_not_on_working_branch(
        self, mock_run, mock_run_list, mock_working_branch,
        mock_commit, mock_push, capsys,
    ):
        """#11083: when the current branch is a feature branch (not the
        configured working branch), commit_role_scoped refuses to stage any
        files. This prevents PM's cycle commits from landing on a sibling
        agent's feature branch during a task-begin/task-end checkout race
        — the root cause of PR #11080's BRIEFING.md merge-spiral.
        """
        def _run_side(cmd, *a, **kw):
            if "branch --show-current" in cmd:
                # Simulate a feature branch checkout (e.g., skill's task-begin)
                return _mock_result(stdout="squidsquad/skill/11044-pollution\n")
            return _mock_result(stdout=" M .squidsquad/pm/working-state.md\n")
        mock_run.side_effect = _run_side
        mock_run_list.return_value = _mock_result()

        result = git_ops.commit_role_scoped("pm", "cycle 9999")

        # No commit attempted, no files staged.
        assert result is False
        assert mock_commit.call_count == 0
        assert mock_push.call_count == 0
        add_calls = [c for c in mock_run_list.call_args_list
                     if c[0][0][:2] == ["git", "add"]]
        assert add_calls == []

        err = capsys.readouterr().err
        assert "not the configured working branch" in err
        assert "squidsquad/skill/11044-pollution" in err
        assert "#11083" in err

    @patch("git_ops.push", return_value=True)
    @patch("git_ops.commit", return_value=True)
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_dm_can_stage_readme_and_changelog(
        self, mock_run, mock_run_list, mock_working_branch,
        mock_commit, mock_push,
    ):
        def _run_side(cmd, *a, **kw):
            if "branch --show-current" in cmd:
                return _mock_result(stdout="main\n")
            return _mock_result(stdout=(
                " M README.md\n"
                " M CHANGELOG.md\n"
                " M docs/release-notes.md\n"
                " M .squidsquad/dm/working-state.md\n"
            ))
        mock_run.side_effect = _run_side
        mock_run_list.return_value = _mock_result()

        result = git_ops.commit_role_scoped("dm", "delivery cycle")
        assert result is True

        staged = [c[0][0][-1] for c in mock_run_list.call_args_list
                  if c[0][0][:2] == ["git", "add"]]
        assert "README.md" in staged
        assert "CHANGELOG.md" in staged
        assert "docs/release-notes.md" in staged
        assert ".squidsquad/dm/working-state.md" in staged

    @patch("git_ops.push", return_value=True)
    @patch("git_ops.commit", return_value=True)
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_dm_stages_skill_md_and_config_md(
        self, mock_run, mock_run_list, mock_working_branch,
        mock_commit, mock_push,
    ):
        """#9474 regression: DM's cycle commit must include SKILL.md
        (doc-improvement-loop) and .squidsquad/config.md (Shipped Since
        Last Bump counter + feature-flag toggles). Before the fix these
        files were treated as foreign and either rotted in the working
        tree across cycles or got overwritten by sibling commits."""
        def _run_side(cmd, *a, **kw):
            if "branch --show-current" in cmd:
                return _mock_result(stdout="main\n")
            return _mock_result(stdout=(
                " M SKILL.md\n"
                " M .squidsquad/config.md\n"
                " M .squidsquad/dm/working-state.md\n"
            ))
        mock_run.side_effect = _run_side
        mock_run_list.return_value = _mock_result()

        result = git_ops.commit_role_scoped("dm", "dm: ship #9474 + counter")
        assert result is True

        staged = [c[0][0][-1] for c in mock_run_list.call_args_list
                  if c[0][0][:2] == ["git", "add"]]
        assert "SKILL.md" in staged, (
            "DM cycle commit must stage SKILL.md when dirty — "
            "doc-improvement-loop fixes were silently rotting "
            "in the working tree before #9474."
        )
        assert ".squidsquad/config.md" in staged, (
            "DM cycle commit must stage .squidsquad/config.md when "
            "dirty — the Shipped Since Last Bump counter was being "
            "silently dropped before #9474."
        )
        assert ".squidsquad/dm/working-state.md" in staged

        # Ensure the role kwarg propagates to the push call — without
        # it the git-push event would be emitted with role=None and
        # the audit trail would lose the DM attribution. Tightening
        # this assertion was the deepseek R1 finding on this PR.
        mock_push.assert_called_once_with(role="dm")

    @patch("git_ops.commit", return_value=True)
    @patch("git_ops.push", return_value=True)
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_qa_cannot_stage_config_md(
        self, mock_run, mock_run_list, mock_working_branch,
        mock_push, mock_commit, capsys,
    ):
        """QA must not pick up PM-domain config.md changes."""
        def _run_side(cmd, *a, **kw):
            if "branch --show-current" in cmd:
                return _mock_result(stdout="main\n")
            return _mock_result(stdout=(
                " M .squidsquad/qa/working-state.md\n"
                " M .squidsquad/config.md\n"
            ))
        mock_run.side_effect = _run_side
        mock_run_list.return_value = _mock_result()

        git_ops.commit_role_scoped("qa", "qa cycle")

        staged = [c[0][0][-1] for c in mock_run_list.call_args_list
                  if c[0][0][:2] == ["git", "add"]]
        assert ".squidsquad/qa/working-state.md" in staged
        assert ".squidsquad/config.md" not in staged
        assert ".squidsquad/config.md" in capsys.readouterr().err

    @patch("git_ops.commit", return_value=True)
    @patch("git_ops.push", return_value=True)
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_qa_stages_untracked_comprehension_spec_13212(
        self, mock_run, mock_run_list, mock_working_branch,
        mock_push, mock_commit, capsys,
    ):
        """#13212: the exact bug — an UNTRACKED comprehension spec (porcelain
        '??') authored by the verifier must be staged by its post-cycle commit,
        not classified foreign and left to rot until a manual recovery commit."""
        def _run_side(cmd, *a, **kw):
            if "branch --show-current" in cmd:
                return _mock_result(stdout="main\n")
            return _mock_result(stdout=(
                " M .squidsquad/qa/working-state.md\n"
                "?? tests/comprehension/13250_spec.json\n"
            ))
        mock_run.side_effect = _run_side
        mock_run_list.return_value = _mock_result()

        result = git_ops.commit_role_scoped("qa", "qa cycle")

        staged = [c[0][0][-1] for c in mock_run_list.call_args_list
                  if c[0][0][:2] == ["git", "add"]]
        assert "tests/comprehension/13250_spec.json" in staged, (
            "qa post-cycle must stage untracked comprehension specs (#13212) — "
            "they were silently left foreign before this fix"
        )
        assert ".squidsquad/qa/working-state.md" in staged
        # not left in the foreign-skip warning
        assert "tests/comprehension/13250_spec.json" not in capsys.readouterr().err
        assert result is True

    @patch("git_ops._run")
    def test_returns_false_when_no_own_files(self, mock_run, capsys):
        """Only foreign files → nothing to commit, push not attempted."""
        mock_run.return_value = _mock_result(stdout=" M references/scripts/foo.py\n")
        with patch("git_ops.commit") as mock_commit, \
             patch("git_ops.push") as mock_push:
            result = git_ops.commit_role_scoped("pm", "msg")
        assert result is False
        mock_commit.assert_not_called()
        mock_push.assert_not_called()

    @patch("git_ops._run")
    def test_empty_status_returns_false(self, mock_run):
        mock_run.return_value = _mock_result(stdout="")
        assert git_ops.commit_role_scoped("pm", "msg") is False

    @patch("git_ops.push", return_value=True)
    @patch("git_ops.commit", return_value=False)
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_commit_failure_short_circuits_push(
        self, mock_run, mock_run_list, mock_commit, mock_push
    ):
        mock_run.return_value = _mock_result(stdout=" M .squidsquad/pm/foo.md\n")
        mock_run_list.return_value = _mock_result()
        assert git_ops.commit_role_scoped("pm", "msg") is False
        mock_push.assert_not_called()

    @patch("git_ops.push", return_value=True)
    @patch("git_ops.commit", return_value=True)
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_warning_truncates_long_foreign_list(
        self, mock_run, mock_run_list, mock_working_branch,
        mock_commit, mock_push, capsys,
    ):
        # 25 foreign files; warning should mention "... and 5 more"
        lines = [" M .squidsquad/pm/own.md"]
        lines += [f" M references/scripts/foreign_{i}.py" for i in range(25)]
        def _run_side(cmd, *a, **kw):
            if "branch --show-current" in cmd:
                return _mock_result(stdout="main\n")
            return _mock_result(stdout="\n".join(lines) + "\n")
        mock_run.side_effect = _run_side
        mock_run_list.return_value = _mock_result()

        git_ops.commit_role_scoped("pm", "msg")
        err = capsys.readouterr().err
        assert "and 5 more" in err


# ---------------------------------------------------------------------------
# branch_exists() / branch_delete() / current_branch()
# ---------------------------------------------------------------------------

class TestBranchUtilities:
    @patch("git_ops._run_list")
    def test_branch_exists_local(self, mock_run):
        mock_run.return_value = _mock_result(returncode=0)
        assert git_ops.branch_exists("squidsquad/skill/375") is True

    @patch("git_ops._run_list")
    def test_branch_not_exists(self, mock_run):
        mock_run.return_value = _mock_result(returncode=1)
        assert git_ops.branch_exists("nonexistent") is False

    @patch("git_ops._run_list")
    def test_branch_delete_success(self, mock_run):
        mock_run.return_value = _mock_result()
        assert git_ops.branch_delete("squidsquad/skill/375") is True

    @patch("git_ops._run")
    def test_current_branch(self, mock_run):
        mock_run.return_value = _mock_result(stdout="main\n")
        assert git_ops.current_branch() == "main"


# ---------------------------------------------------------------------------
# _get_working_branch (#2671 regression)
# ---------------------------------------------------------------------------

class TestGetWorkingBranch:
    def test_reads_config_working_branch(self):
        """_get_working_branch imports get_field (not nonexistent 'get')."""
        with patch.dict("sys.modules", {"config": MagicMock()}):
            import importlib
            importlib.reload(git_ops)
            # Mock get_field to return a custom branch
            with patch("config.get_field", return_value="develop"):
                result = git_ops._get_working_branch()
            assert result == "develop"

    def test_falls_back_to_main_on_import_error(self):
        """Falls back to 'main' if config module unavailable."""
        with patch.dict("sys.modules", {"config": None}):
            import importlib
            importlib.reload(git_ops)
            result = git_ops._get_working_branch()
        assert result == "main"

    def test_falls_back_to_main_on_empty_value(self):
        """Falls back to 'main' if config returns empty string."""
        with patch.dict("sys.modules", {"config": MagicMock()}):
            import importlib
            importlib.reload(git_ops)
            with patch("config.get_field", return_value=""):
                result = git_ops._get_working_branch()
            assert result == "main"


# ---------------------------------------------------------------------------
# #5444 regression: commit_code returns False on push failure
# ---------------------------------------------------------------------------

class TestCommitCodePushFailure:
    """#5444: commit_code must return False when push fails."""

    @patch("git_ops._get_alias", return_value="skill")
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._git_push")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("subprocess.run")
    def test_returns_false_on_push_failure(
        self, mock_subproc, mock_run, mock_run_list, mock_git_push,
        mock_safe_checkout, mock_gwb, mock_alias
    ):
        # git status shows code file changed
        mock_run.side_effect = [
            _mock_result(stdout=" M src/app.py\n"),  # status --porcelain
            _mock_result(stdout="squidsquad/task/100\n"),  # branch --show-current
        ]
        mock_subproc.return_value = _mock_result()  # (legacy: commit no longer here)
        # #13262: the commit now routes through _run_list too — use return_value
        # so the add / config-revert / commit calls all succeed regardless of count.
        mock_run_list.return_value = _mock_result()
        # push now routed through _git_push (#9890) and FAILS here
        mock_git_push.return_value = _mock_result(returncode=1, stderr="push rejected")
        result = git_ops.commit_code("skill", "squidsquad/task/100", "test")
        assert result is False

    @patch("git_ops._get_alias", return_value="skill")
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._git_push")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("subprocess.run")
    def test_returns_true_on_push_success(
        self, mock_subproc, mock_run, mock_run_list, mock_git_push,
        mock_safe_checkout, mock_gwb, mock_alias
    ):
        mock_run.side_effect = [
            _mock_result(stdout=" M src/app.py\n"),  # status
            _mock_result(stdout="squidsquad/task/100\n"),  # branch
        ]
        mock_subproc.return_value = _mock_result()  # (legacy: commit no longer here)
        # #13262: commit routes through _run_list now → any-count success.
        mock_run_list.return_value = _mock_result()
        mock_git_push.return_value = _mock_result()  # push succeeds (#9890)
        result = git_ops.commit_code("skill", "squidsquad/task/100", "test")
        assert result is True


# ---------------------------------------------------------------------------
# #3341 regression: commit_code/commit_state use _get_working_branch()
# ---------------------------------------------------------------------------

class TestCommitCodeUsesWorkingBranch:
    @patch("git_ops._get_working_branch", return_value="develop")
    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._git_push")
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("subprocess.run")
    def test_commit_code_switches_back_to_working_branch(
        self, mock_subproc, mock_run, mock_run_list, mock_git_push,
        mock_safe_checkout, mock_gwb
    ):
        """commit_code returns to _get_working_branch(), not hardcoded 'main'."""
        mock_run.side_effect = [
            _mock_result(stdout=" M src/app.py\n"),  # git status --porcelain
            _mock_result(stdout="develop\n"),  # current branch
        ]
        # #13262: commit routes through _run_list now (one more call); use
        # return_value so add / checkout / rev-parse / commit all succeed (rc0).
        mock_run_list.return_value = _mock_result(returncode=0)
        mock_git_push.return_value = _mock_result()  # push (#9890)
        mock_subproc.return_value = _mock_result(stdout="1 file changed")

        result = git_ops.commit_code("skill", "squidsquad/skill/3341", "test fix")
        assert result is True

        # Last _safe_checkout call should be to "develop", not "main"
        last_checkout = mock_safe_checkout.call_args_list[-1]
        assert last_checkout[0][0] == "develop"

    @patch("git_ops._get_working_branch", return_value="develop")
    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._run")
    def test_commit_code_error_path_uses_working_branch(
        self, mock_run, mock_safe_checkout, mock_gwb
    ):
        """commit_code error paths also return to working branch, not 'main'."""
        mock_run.return_value = _mock_result(stdout=" M .squidsquad/state.md\n")
        result = git_ops.commit_code("skill", "squidsquad/skill/3341", "test")
        assert result is False
        # No _safe_checkout calls expected when there are no code files


class TestCommitStateUsesWorkingBranch:
    @patch("git_ops._get_working_branch", return_value="develop")
    @patch("git_ops._run")
    def test_commit_state_checks_working_branch(self, mock_run, mock_gwb):
        """commit_state rejects commits when not on the configured working branch."""
        mock_run.side_effect = [
            _mock_result(stdout=" M .squidsquad/skill/working-state.md\n"),
            _mock_result(stdout="squidsquad/skill/3341\n"),  # not on develop
        ]
        result = git_ops.commit_state("skill", "state update")
        assert result is False

    @patch("git_ops._get_working_branch", return_value="develop")
    @patch("git_ops._git_push")
    @patch("git_ops._run")
    @patch("git_ops._run_list")
    @patch("subprocess.run")
    def test_commit_state_succeeds_on_working_branch(
        self, mock_subproc, mock_run_list, mock_run, mock_git_push, mock_gwb
    ):
        """commit_state succeeds when on the configured working branch."""
        mock_run.side_effect = [
            _mock_result(stdout=" M .squidsquad/skill/working-state.md\n"),
            _mock_result(stdout="develop\n"),  # on working branch
        ]
        mock_run_list.return_value = _mock_result()  # git add
        mock_git_push.return_value = _mock_result()  # state push (#9890)
        mock_subproc.return_value = _mock_result(stdout="1 file changed")

        result = git_ops.commit_state("skill", "state update")
        assert result is True


# ---------------------------------------------------------------------------
# _safe_checkout (#4362)
# ---------------------------------------------------------------------------

class TestSafeCheckout:
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_stash_pop_on_failure_restores_original(self, mock_run, mock_run_list):
        """On checkout failure after stash, pop restores original branch (#4362)."""
        mock_run.side_effect = [
            _mock_result(stdout="main\n"),      # git branch --show-current
            _mock_result(returncode=1),          # _stash_top_ref pre → ""
            _mock_result(),                      # git stash -q
            _mock_result(stdout="newsha"),       # _stash_top_ref post → stashed=True
            _mock_result(),                      # git stash pop -q (restore)
        ]
        # First checkout fails, second (after stash) also fails
        mock_run_list.side_effect = [
            _mock_result(returncode=1, stderr="error"),  # direct checkout
            _mock_result(returncode=1, stderr="error"),  # stash+checkout
        ]

        result = git_ops._safe_checkout("feature-branch")
        assert result is False
        # Stash pop must be called to restore original state
        pop_calls = [c for c in mock_run.call_args_list
                     if "stash pop" in str(c)]
        assert len(pop_calls) == 1

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_clean_checkout_failure_does_not_pop_preexisting(self, mock_run, mock_run_list):
        """#13167: if checkout fails for a NON-dirty reason, `git stash -q` is a
        no-op (refs/stash unchanged) and the recovery pop MUST be skipped — never
        pop a pre-existing ancient stash."""
        mock_run.side_effect = [
            _mock_result(stdout="main\n"),      # branch --show-current
            _mock_result(stdout="oldsha"),       # _stash_top_ref pre: pre-existing stash
            _mock_result(),                      # git stash -q (no-op)
            _mock_result(stdout="oldsha"),       # _stash_top_ref post: UNCHANGED → stashed=False
        ]
        mock_run_list.side_effect = [
            _mock_result(returncode=1, stderr="no such branch"),  # direct checkout fails
            _mock_result(returncode=1, stderr="no such branch"),  # stash+checkout fails
        ]
        result = git_ops._safe_checkout("feature-branch")
        assert result is False
        pop_calls = [c for c in mock_run.call_args_list if "stash pop" in str(c)]
        assert not pop_calls, "must NOT pop a pre-existing stash when our stash was a no-op"

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_stash_pop_on_success_applies_to_target(self, mock_run, mock_run_list):
        """On checkout success after stash, pop applies on target branch."""
        mock_run.side_effect = [
            _mock_result(stdout="main\n"),      # git branch --show-current
            _mock_result(returncode=1),          # _stash_top_ref pre → ""
            _mock_result(),                      # git stash -q
            _mock_result(stdout="newsha"),       # _stash_top_ref post → stashed=True
            _mock_result(),                      # git stash pop -q
        ]
        mock_run_list.side_effect = [
            _mock_result(returncode=1, stderr="error"),  # direct checkout fails
            _mock_result(returncode=0),                   # stash+checkout succeeds
        ]

        result = git_ops._safe_checkout("feature-branch")
        assert result is True

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_checkout_success_then_pop_conflict_resolves_to_head(
            self, mock_run, mock_run_list):
        """#13045: if the pop on the target branch conflicts, _safe_checkout
        must NOT leave `<<<<<<<` markers — the conflicted paths are restored to
        HEAD and the stash dropped (via _safe_stash_pop)."""
        mock_run.side_effect = [
            _mock_result(stdout="main\n"),                    # branch --show-current
            _mock_result(returncode=1),                       # _stash_top_ref pre → ""
            _mock_result(),                                   # git stash -q
            _mock_result(stdout="newsha"),                    # _stash_top_ref post → stashed=True
            _mock_result(returncode=1),                       # stash pop conflict
            _mock_result(stdout=".squidsquad/config.md\n"),   # diff --diff-filter=U
            _mock_result(),                                   # stash drop
        ]
        mock_run_list.side_effect = [
            _mock_result(returncode=1, stderr="error"),       # direct checkout fails
            _mock_result(returncode=0),                       # stash+checkout succeeds
            _mock_result(),                                   # checkout HEAD -- config.md
        ]
        result = git_ops._safe_checkout("feature-branch")
        assert result is True
        checkouts = [c[0][0] for c in mock_run_list.call_args_list]
        assert ["git", "checkout", "HEAD", "--", ".squidsquad/config.md"] in checkouts
        assert any(c[0][0] == "git stash drop" for c in mock_run.call_args_list)


# ---------------------------------------------------------------------------
# _safe_stash_pop (#13045)
# ---------------------------------------------------------------------------

class TestSafeStashPop:
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_clean_pop_returns_true_no_drop(self, mock_run, mock_run_list):
        """A clean pop returns True and does NOT drop (the stash is consumed)."""
        mock_run.side_effect = [_mock_result()]               # git stash pop (ok)
        assert git_ops._safe_stash_pop() is True
        assert not any("stash drop" in str(c) for c in mock_run.call_args_list)
        mock_run_list.assert_not_called()

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_conflict_restores_to_head_and_drops(self, mock_run, mock_run_list):
        """A conflicted pop restores unmerged paths to HEAD then drops (#13045)."""
        mock_run.side_effect = [
            _mock_result(returncode=1),                       # pop conflict
            _mock_result(stdout=".squidsquad/config.md\n"),   # diff --diff-filter=U
            _mock_result(),                                   # stash drop
        ]
        mock_run_list.return_value = _mock_result()
        assert git_ops._safe_stash_pop() is False
        mock_run_list.assert_called_once_with(
            ["git", "checkout", "HEAD", "--", ".squidsquad/config.md"], check=False)
        assert any(c[0][0] == "git stash drop" for c in mock_run.call_args_list)

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_non_conflict_pop_failure_does_not_drop(self, mock_run, mock_run_list):
        """#13045 DS Finding 1: a pop that fails WITHOUT conflicts (no stash /
        unrelated error → empty unmerged set) must NOT drop a possibly-unapplied
        stash. No checkout, no drop, returns False."""
        mock_run.side_effect = [
            _mock_result(returncode=1),                       # pop fails
            _mock_result(stdout=""),                          # diff: no unmerged paths
        ]
        assert git_ops._safe_stash_pop() is False
        mock_run_list.assert_not_called()
        assert not any("stash drop" in str(c) for c in mock_run.call_args_list)


# ---------------------------------------------------------------------------
# .gitignore volatile file coverage — regression #4829
# ---------------------------------------------------------------------------

class TestGitignoreVolatileFiles:
    """Regression #4829: volatile files must be covered by .gitignore patterns."""

    VOLATILE_PATTERNS = [
        ".squidsquad/.backlog-cache",
        ".squidsquad/.event-state.json",
        ".squidsquad/*/.claude-pid",
        ".squidsquad/*/.health",
        ".squidsquad/*/.booting",
        ".squidsquad/scan-index.db",
        ".claude/scheduled_tasks.lock",
    ]

    def test_gitignore_covers_volatile_files(self):
        """All volatile file patterns must appear in .gitignore."""
        gitignore_path = Path(__file__).resolve().parent.parent / ".gitignore"
        content = gitignore_path.read_text(encoding="utf-8")
        for pattern in self.VOLATILE_PATTERNS:
            assert pattern in content, (
                f".gitignore missing pattern for volatile file: {pattern}"
            )

    def test_volatile_files_not_tracked(self):
        """Volatile files must not be in git index (git ls-files)."""
        import subprocess
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        tracked = result.stdout.strip().splitlines()
        volatile_names = [".backlog-cache", ".event-state.json",
                          ".claude-pid", ".health", ".booting",
                          "scan-index.db", "scheduled_tasks.lock"]
        for name in volatile_names:
            matches = [f for f in tracked if name in f]
            assert matches == [], (
                f"Volatile file(s) still tracked in git index: {matches}"
            )


class TestGitattributesMergeStrategies:
    """#5469: .gitattributes merge strategies for state files."""

    def test_gitattributes_exists(self):
        gitattr = Path(__file__).resolve().parent.parent / ".gitattributes"
        assert gitattr.exists(), ".gitattributes missing from repo root"

    def test_union_merge_for_append_only(self):
        content = (Path(__file__).resolve().parent.parent / ".gitattributes").read_text()
        assert "iterations/*.md merge=union" in content
        assert "scan-history.md merge=union" in content

    def test_ours_merge_for_overwrite_files(self):
        content = (Path(__file__).resolve().parent.parent / ".gitattributes").read_text()
        assert "working-state.md merge=ours" in content
        # #12823: the ship counter (the only field that needed ours-wins) moved
        # to its own file; config.md itself no longer carries merge=ours.
        assert ".squidsquad/.ship-counter merge=ours" in content
        rule_lines = [ln.strip() for ln in content.splitlines()
                      if ln.strip().startswith(".squidsquad/config.md")]
        assert all("merge=ours" not in ln for ln in rule_lines)

    def test_vault_briefing_merge_ours(self):
        """#5674: BRIEFING.md uses merge=ours (last writer wins)."""
        content = (Path(__file__).resolve().parent.parent / ".gitattributes").read_text()
        assert "vault/BRIEFING.md merge=ours" in content

    def test_vault_notes_merge_union(self):
        """#5674: vault galaxy/areas/projects use merge=union (append-friendly)."""
        content = (Path(__file__).resolve().parent.parent / ".gitattributes").read_text()
        assert "vault/galaxy/*.md merge=union" in content
        assert "vault/areas/*.md merge=union" in content
        assert "vault/projects/*.md merge=union" in content


# ---------------------------------------------------------------------------
# task_begin — regression #4942
# ---------------------------------------------------------------------------

def _task_begin_config(field):
    """Mock config.get_field for task_begin tests."""
    if field == "branch-workflow":
        return "yes"
    if field == "branch-pattern":
        return "squidsquad/{role}/{number}"
    return ""


class TestTaskBegin:
    """task_begin should create branch if missing, not error out."""

    @patch("git_ops._auto_resolve_state_conflicts", return_value=([], []))
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._run_list")
    def test_checks_out_existing_local_branch(self, mock_run_list, mock_checkout, mock_gwb, mock_resolve):
        """Existing local branch is checked out normally."""
        # rev-parse succeeds (branch exists locally)
        mock_run_list.return_value = _mock_result(returncode=0)
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=_task_begin_config):
            git_ops.task_begin("skill", "100")
        mock_checkout.assert_called_once_with("squidsquad/skill/100")

    @patch("git_ops._auto_resolve_state_conflicts", return_value=([], []))
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    def test_creates_branch_when_missing(self, mock_run_list, mock_gwb, mock_resolve):
        """Branch not found locally or on remote — creates from origin/main (#5444)."""
        mock_run_list.side_effect = [
            _mock_result(returncode=1),  # rev-parse local — not found
            _mock_result(returncode=0),  # git fetch origin branch (#5013)
            _mock_result(returncode=1),  # rev-parse remote — not found
            _mock_result(returncode=0),  # git fetch origin main (#5444)
            _mock_result(returncode=0),  # rev-parse origin/main (#5444)
            _mock_result(returncode=0),  # git checkout -b from origin/main
        ]
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=_task_begin_config):
            git_ops.task_begin("skill", "200")
        # Sixth call should be branch creation from origin/main
        create_call = mock_run_list.call_args_list[5]
        assert create_call[0][0] == ["git", "checkout", "-b", "squidsquad/skill/200", "origin/main"]

    @patch("git_ops._auto_resolve_state_conflicts", return_value=([], []))
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    def test_checks_out_remote_branch(self, mock_run_list, mock_gwb, mock_resolve):
        """Branch exists on remote only — checks out and tracks."""
        mock_run_list.side_effect = [
            _mock_result(returncode=1),  # rev-parse local — not found
            _mock_result(returncode=0),  # git fetch origin (#5013)
            _mock_result(returncode=0),  # rev-parse remote — found
            _mock_result(returncode=0),  # checkout -b from origin
        ]
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=_task_begin_config):
            git_ops.task_begin("skill", "300")
        checkout_call = mock_run_list.call_args_list[3]
        assert "origin/squidsquad/skill/300" in checkout_call[0][0]

    @patch("git_ops._auto_resolve_state_conflicts", return_value=([], []))
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    def test_fetches_before_remote_check(self, mock_run_list, mock_gwb, mock_resolve):
        """Regression #5013: task-begin must fetch before checking remote refs."""
        mock_run_list.side_effect = [
            _mock_result(returncode=1),  # rev-parse local — not found
            _mock_result(returncode=0),  # git fetch origin
            _mock_result(returncode=0),  # rev-parse remote — found after fetch
            _mock_result(returncode=0),  # checkout -b from origin
        ]
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=_task_begin_config):
            git_ops.task_begin("skill", "500")
        # Second call should be git fetch
        fetch_call = mock_run_list.call_args_list[1]
        assert "fetch" in fetch_call[0][0]
        assert "origin" in fetch_call[0][0]

    @patch("git_ops._auto_resolve_state_conflicts", return_value=([], []))
    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._run_list")
    def test_uses_configured_branch_pattern(self, mock_run_list, mock_checkout, mock_gwb, mock_resolve):
        """Regression #5040: task-begin uses branch-pattern from config."""
        mock_run_list.return_value = _mock_result(returncode=0)

        def custom_config(field):
            if field == "branch-workflow":
                return "yes"
            if field == "branch-pattern":
                return "squidsquad/task/{number}"
            return ""

        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=custom_config):
            git_ops.task_begin("skill", "5040")
        mock_checkout.assert_called_once_with("squidsquad/task/5040")


# ---------------------------------------------------------------------------
# _auto_resolve_state_conflicts() — #8653
# ---------------------------------------------------------------------------


def _ls_files_output(*paths):
    """Build mock `git ls-files --unmerged` output with one stage line per path."""
    return "\n".join(f"100644 0000000000000000000000000000000000000000 2\t{p}" for p in paths)


class TestAutoResolveStateConflicts:
    """#8653: auto-resolve unmerged state files; bail on code conflicts."""

    @patch("git_ops._run_list")
    def test_no_unmerged_returns_empty(self, mock_run_list):
        """Clean index — both lists are empty, no checkout/add calls."""
        mock_run_list.return_value = _mock_result(returncode=0, stdout="")
        resolved, unresolved = git_ops._auto_resolve_state_conflicts()
        assert resolved == []
        assert unresolved == []
        assert mock_run_list.call_count == 1  # only ls-files

    @patch("git_ops._run_list")
    def test_state_file_resolved_with_theirs(self, mock_run_list):
        """A .squidsquad/ state file is resolved via checkout --theirs + add."""
        mock_run_list.side_effect = [
            _mock_result(returncode=0, stdout=_ls_files_output(".squidsquad/.backlog-cache")),
            _mock_result(returncode=0),  # checkout --theirs
            _mock_result(returncode=0),  # git add
        ]
        resolved, unresolved = git_ops._auto_resolve_state_conflicts()
        assert resolved == [".squidsquad/.backlog-cache"]
        assert unresolved == []
        # Verify --theirs is used and `--` separator is present (avoids ambiguity)
        checkout_args = mock_run_list.call_args_list[1][0][0]
        assert "--theirs" in checkout_args
        assert "--" in checkout_args
        assert checkout_args[-1] == ".squidsquad/.backlog-cache"

    @patch("git_ops._run_list")
    def test_claude_state_file_resolved(self, mock_run_list):
        """A .claude/ state file is also treated as state and resolved."""
        mock_run_list.side_effect = [
            _mock_result(returncode=0, stdout=_ls_files_output(".claude/scheduled_tasks.lock")),
            _mock_result(returncode=0),
            _mock_result(returncode=0),
        ]
        resolved, unresolved = git_ops._auto_resolve_state_conflicts()
        assert resolved == [".claude/scheduled_tasks.lock"]
        assert unresolved == []

    @patch("git_ops._run_list")
    def test_code_file_left_unresolved(self, mock_run_list):
        """Non-state code files are reported as unresolved, never auto-resolved."""
        mock_run_list.return_value = _mock_result(
            returncode=0, stdout=_ls_files_output("references/scripts/git_ops.py")
        )
        resolved, unresolved = git_ops._auto_resolve_state_conflicts()
        assert resolved == []
        assert unresolved == ["references/scripts/git_ops.py"]
        # Only ls-files should have been called — no checkout/add attempt
        assert mock_run_list.call_count == 1

    @patch("git_ops._run_list")
    def test_mixed_state_and_code(self, mock_run_list):
        """State files resolve; code file is reported separately."""
        mock_run_list.side_effect = [
            _mock_result(returncode=0, stdout=_ls_files_output(
                ".squidsquad/.event-state.json",
                "references/scripts/harness.py",
            )),
            _mock_result(returncode=0),  # checkout --theirs state
            _mock_result(returncode=0),  # git add state
        ]
        resolved, unresolved = git_ops._auto_resolve_state_conflicts()
        assert resolved == [".squidsquad/.event-state.json"]
        assert unresolved == ["references/scripts/harness.py"]

    @patch("git_ops._run_list")
    def test_deduplicates_multi_stage_entries(self, mock_run_list):
        """ls-files emits one line per stage; we resolve each path once."""
        # Two stages (2 + 3) for the same path
        stages = "\n".join([
            "100644 aaa 2\t.squidsquad/.backlog-cache",
            "100644 bbb 3\t.squidsquad/.backlog-cache",
        ])
        mock_run_list.side_effect = [
            _mock_result(returncode=0, stdout=stages),
            _mock_result(returncode=0),
            _mock_result(returncode=0),
        ]
        resolved, unresolved = git_ops._auto_resolve_state_conflicts()
        assert resolved == [".squidsquad/.backlog-cache"]
        # ls-files + 1 checkout + 1 add — not 2 of each
        assert mock_run_list.call_count == 3

    @patch("git_ops._run_list")
    def test_checkout_failure_falls_to_unresolved(self, mock_run_list):
        """If checkout --theirs fails, the path lands in unresolved (no silent loss)."""
        mock_run_list.side_effect = [
            _mock_result(returncode=0, stdout=_ls_files_output(".squidsquad/state.json")),
            _mock_result(returncode=1),  # checkout failed
            _mock_result(returncode=0),  # add (irrelevant after checkout failure, but called)
        ]
        resolved, unresolved = git_ops._auto_resolve_state_conflicts()
        assert resolved == []
        assert unresolved == [".squidsquad/state.json"]


class TestTaskBeginConflictHandling:
    """#8653: task_begin auto-resolves state conflicts and bails on code conflicts."""

    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._run_list")
    @patch("git_ops._auto_resolve_state_conflicts")
    def test_auto_resolves_state_then_proceeds(
        self, mock_resolve, mock_run_list, mock_checkout, mock_gwb, capsys
    ):
        """State files were unmerged; task_begin reports and continues."""
        mock_resolve.return_value = ([".squidsquad/.backlog-cache"], [])
        mock_run_list.return_value = _mock_result(returncode=0)  # local rev-parse ok
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=_task_begin_config):
            git_ops.task_begin("skill", "100")
        out = capsys.readouterr().out
        assert "auto-resolved" in out
        assert ".squidsquad/.backlog-cache" in out
        mock_checkout.assert_called_once()

    @patch("git_ops._get_working_branch", return_value="main")
    @patch("git_ops._run_list")
    @patch("git_ops._auto_resolve_state_conflicts")
    def test_bails_when_code_conflict_present(
        self, mock_resolve, mock_run_list, mock_gwb, capsys
    ):
        """Code conflicts cause task_begin to exit(1) with a clear message."""
        mock_resolve.return_value = ([], ["references/scripts/harness.py"])
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=_task_begin_config):
            with pytest.raises(SystemExit) as exc:
                git_ops.task_begin("skill", "100")
            assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "unresolved conflicts" in err
        assert "references/scripts/harness.py" in err
        # Should not have attempted any git operations beyond the resolve probe
        mock_run_list.assert_not_called()


# ---------------------------------------------------------------------------
# get_branch_name() — #8533
# ---------------------------------------------------------------------------

class TestGetBranchName:
    """#8533: get_branch_name test coverage."""

    def test_default_pattern(self):
        """Default pattern produces squidsquad/task/{number}."""
        fake_config = MagicMock()
        fake_config.get_field = MagicMock(return_value="")
        with patch.dict("sys.modules", {"config": fake_config}):
            result = git_ops.get_branch_name("skill", "42")
        assert result == "squidsquad/task/42"

    def test_custom_pattern_with_role(self):
        """Custom pattern with {role} placeholder substitutes correctly."""
        fake_config = MagicMock()
        fake_config.get_field = MagicMock(return_value="squidsquad/{role}/{number}")
        with patch.dict("sys.modules", {"config": fake_config}):
            result = git_ops.get_branch_name("skill", "99")
        assert result == "squidsquad/skill/99"

    def test_custom_pattern_number_only(self):
        """Pattern with only {number} placeholder works."""
        fake_config = MagicMock()
        fake_config.get_field = MagicMock(return_value="feature/{number}")
        with patch.dict("sys.modules", {"config": fake_config}):
            result = git_ops.get_branch_name("pm", "123")
        assert result == "feature/123"

    def test_graceful_fallback_on_import_error(self):
        """Falls back to default when config import fails."""
        def fail_import(name, *args, **kwargs):
            if name == "config":
                raise ImportError("no config")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fail_import):
            result = git_ops.get_branch_name("skill", "55")
        assert result == "squidsquad/task/55"

    def test_graceful_fallback_on_system_exit(self):
        """Falls back to default when config.get_field raises SystemExit."""
        fake_config = MagicMock()
        fake_config.get_field = MagicMock(side_effect=SystemExit(1))
        with patch.dict("sys.modules", {"config": fake_config}):
            result = git_ops.get_branch_name("skill", "77")
        assert result == "squidsquad/task/77"


# ---------------------------------------------------------------------------
# _gh_credential_helper_available() and _git_push() (#9890)
# ---------------------------------------------------------------------------

class TestGhCredentialHelperAvailable:
    def setup_method(self):
        # Reset cache before each test (module-level cache leaks across tests).
        git_ops._GH_AVAILABLE_CACHE = None

    @patch("git_ops.subprocess.run")
    def test_returns_true_when_gh_authenticated(self, mock_run):
        mock_run.return_value = _mock_result(returncode=0)
        assert git_ops._gh_credential_helper_available() is True
        call_args = mock_run.call_args[0][0]
        assert call_args[:3] == ["gh", "auth", "status"]

    @patch("git_ops.subprocess.run")
    def test_returns_false_when_gh_unauthenticated(self, mock_run):
        mock_run.return_value = _mock_result(returncode=1, stderr="not logged in")
        assert git_ops._gh_credential_helper_available() is False

    @patch("git_ops.subprocess.run", side_effect=FileNotFoundError("gh"))
    def test_returns_false_when_gh_missing(self, mock_run):
        assert git_ops._gh_credential_helper_available() is False

    @patch("git_ops.subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 10))
    def test_returns_false_when_gh_hangs(self, mock_run):
        """A wedged `gh auth status` should not propagate the timeout."""
        assert git_ops._gh_credential_helper_available() is False

    @patch("git_ops.subprocess.run")
    def test_caches_result(self, mock_run):
        """Second call should not re-invoke subprocess."""
        mock_run.return_value = _mock_result(returncode=0)
        git_ops._gh_credential_helper_available()
        git_ops._gh_credential_helper_available()
        git_ops._gh_credential_helper_available()
        assert mock_run.call_count == 1


class TestGitPush:
    def setup_method(self):
        git_ops._GH_AVAILABLE_CACHE = None

    @patch("git_ops._gh_credential_helper_available", return_value=True)
    @patch("git_ops.subprocess.run")
    def test_prepends_credential_override_when_gh_available(self, mock_run, _mock_gh):
        mock_run.return_value = _mock_result()
        git_ops._git_push(["-u", "origin", "squidsquad/task/9890"])
        cmd = mock_run.call_args[0][0]
        # Must inject -c flags BEFORE "push" subcommand.
        assert cmd[0] == "git"
        push_idx = cmd.index("push")
        injected = cmd[1:push_idx]
        assert "-c" in injected
        assert "credential.helper=" in injected
        assert "credential.helper=!gh auth git-credential" in injected
        # User args preserved after "push".
        assert cmd[push_idx + 1:] == ["-u", "origin", "squidsquad/task/9890"]

    @patch("git_ops._gh_credential_helper_available", return_value=False)
    @patch("git_ops.subprocess.run")
    def test_uses_plain_push_when_gh_unavailable(self, mock_run, _mock_gh):
        mock_run.return_value = _mock_result()
        git_ops._git_push(["origin", "--delete", "branch-x"])
        cmd = mock_run.call_args[0][0]
        # No -c override flags when gh isn't available.
        assert cmd == ["git", "push", "origin", "--delete", "branch-x"]

    @patch("git_ops._gh_credential_helper_available", return_value=False)
    @patch("git_ops.subprocess.run")
    def test_passes_timeout_to_subprocess(self, mock_run, _mock_gh):
        mock_run.return_value = _mock_result()
        git_ops._git_push([], timeout=42)
        assert mock_run.call_args.kwargs.get("timeout") == 42

    @patch("git_ops._gh_credential_helper_available", return_value=False)
    @patch("git_ops.subprocess.run")
    def test_default_timeout_is_60(self, mock_run, _mock_gh):
        mock_run.return_value = _mock_result()
        git_ops._git_push([])
        assert mock_run.call_args.kwargs.get("timeout") == 60

    @patch("git_ops._gh_credential_helper_available", return_value=False)
    @patch("git_ops.subprocess.run",
           side_effect=subprocess.TimeoutExpired("git push", 60))
    def test_timeout_returns_synthetic_failure(self, _mock_run, _mock_gh):
        result = git_ops._git_push([], timeout=60)
        assert result.returncode == 124
        assert "timed out" in result.stderr
        assert "9890" in result.stderr  # references the issue in the message

    @patch("git_ops._gh_credential_helper_available", return_value=False)
    @patch("git_ops.subprocess.run")
    def test_empty_args_produces_bare_push(self, mock_run, _mock_gh):
        mock_run.return_value = _mock_result()
        git_ops._git_push([])
        cmd = mock_run.call_args[0][0]
        assert cmd == ["git", "push"]


class TestCheckRealConflict11511:
    """#11511: deterministic ground truth for whether a PR's CONFLICTING flag
    is a REAL conflict or a cosmetic flap (GitHub honors no user .gitattributes
    merge driver server-side). Runs `git merge-tree --write-tree` both ways;
    a real conflict in either direction is a real conflict.
    """

    @patch("git_ops._run_list")
    def test_clean_returns_true(self, mock_run):
        # rev-parse base, rev-parse head, merge-tree both ways — all clean
        mock_run.side_effect = [
            _mock_result(returncode=0),   # rev-parse base
            _mock_result(returncode=0),   # rev-parse head
            _mock_result(returncode=0),   # merge-tree base head
            _mock_result(returncode=0),   # merge-tree head base
        ]
        assert git_ops.check_real_conflict("origin/main", "origin/feat") is True

    @patch("git_ops._run_list")
    def test_real_conflict_returns_false(self, mock_run):
        mock_run.side_effect = [
            _mock_result(returncode=0),   # rev-parse base
            _mock_result(returncode=0),   # rev-parse head
            _mock_result(stdout="CONFLICT (content): Merge conflict in foo.py",
                         returncode=1),   # merge-tree base head
            _mock_result(returncode=0),   # merge-tree head base
        ]
        assert git_ops.check_real_conflict("origin/main", "origin/feat") is False

    @patch("git_ops._run_list")
    def test_conflict_in_either_direction_is_conflict(self, mock_run):
        # First direction clean, reverse direction conflicts — still a conflict.
        mock_run.side_effect = [
            _mock_result(returncode=0),   # rev-parse base
            _mock_result(returncode=0),   # rev-parse head
            _mock_result(returncode=0),   # merge-tree base head (clean)
            _mock_result(stdout="CONFLICT (content): Merge conflict in bar.py",
                         returncode=1),   # merge-tree head base
        ]
        assert git_ops.check_real_conflict("origin/main", "origin/feat") is False

    @patch("git_ops._run_list")
    def test_unresolvable_ref_returns_none(self, mock_run):
        # rev-parse of the base ref fails -> short-circuit, no merge-tree runs.
        mock_run.side_effect = [_mock_result(returncode=128)]  # rev-parse base fails
        assert git_ops.check_real_conflict("origin/nope", "origin/feat") is None
        assert mock_run.call_count == 1   # short-circuited before head/merge-tree


class TestGuardStagedState11511:
    """#11511 Part 2: the pre-commit guard that keeps transient state off
    feature branches even on the raw-git path (POLLING mode / branch races).
    FAIL-OPEN — it only ever unstages state files, never blocks a commit.
    """

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("git_ops._get_working_branch", return_value="main")
    def test_on_working_branch_is_noop(self, _wb, mock_run, mock_run_list):
        mock_run.return_value = _mock_result(stdout="main\n")  # current branch
        assert git_ops.guard_staged_state() == []
        # No diff/reset attempted when already on the working branch.
        mock_run_list.assert_not_called()

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("git_ops._get_working_branch", return_value="main")
    def test_detached_head_is_noop(self, _wb, mock_run, mock_run_list):
        mock_run.return_value = _mock_result(stdout="\n")  # empty = detached/unknown
        assert git_ops.guard_staged_state() == []
        mock_run_list.assert_not_called()

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("git_ops._get_working_branch", return_value="main")
    def test_branch_lookup_is_fail_open(self, _wb, mock_run, mock_run_list):
        # The branch-current probe must run with check=False so a failing git
        # (corrupt HEAD, perms) can't raise mid-commit and break fail-open.
        mock_run.return_value = _mock_result(stdout="\n")
        git_ops.guard_staged_state()
        assert mock_run.call_count == 1
        assert mock_run.call_args.kwargs.get("check") is False

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("git_ops._get_working_branch", return_value="main")
    def test_branch_lookup_failure_is_fail_open(self, _wb, mock_run, mock_run_list):
        # Behavioral fail-open: a *failing* `git branch --show-current` (corrupt
        # HEAD -> returncode 128, empty stdout) must return [] without raising
        # and without attempting any diff/reset -- not just pass check=False.
        mock_run.return_value = _mock_result(returncode=128, stdout="")
        assert git_ops.guard_staged_state() == []
        mock_run_list.assert_not_called()

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("git_ops._get_working_branch", return_value="main")
    def test_feature_branch_unstages_state_files(self, _wb, mock_run, mock_run_list):
        mock_run.return_value = _mock_result(stdout="squidsquad/task/11511\n")
        # diff --cached lists both code and state; only state should be unstaged.
        mock_run_list.side_effect = [
            _mock_result(stdout="references/scripts/git_ops.py\n"
                                ".squidsquad/skill/working-state.md\n"
                                ".claude/scheduled_tasks.json\n"),  # diff --cached
            _mock_result(returncode=0),  # reset working-state.md
            _mock_result(returncode=0),  # reset scheduled_tasks.json
        ]
        unstaged = git_ops.guard_staged_state()
        assert unstaged == [".squidsquad/skill/working-state.md",
                            ".claude/scheduled_tasks.json"]
        # One diff call + one reset per state file; code file left staged.
        reset_calls = [c for c in mock_run_list.call_args_list
                       if c.args[0][:2] == ["git", "reset"]]
        assert len(reset_calls) == 2
        reset_paths = [c.args[0][-1] for c in reset_calls]
        assert "references/scripts/git_ops.py" not in reset_paths

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("git_ops._get_working_branch", return_value="main")
    def test_feature_branch_code_only_is_noop(self, _wb, mock_run, mock_run_list):
        mock_run.return_value = _mock_result(stdout="squidsquad/task/11511\n")
        mock_run_list.return_value = _mock_result(
            stdout="references/scripts/git_ops.py\ntests/test_git_ops.py\n")
        assert git_ops.guard_staged_state() == []
        # Only the diff ran; nothing to reset.
        assert mock_run_list.call_count == 1


class TestInstallHooks11511:
    """#11511 Part 2: activation of the pre-commit guard via core.hooksPath.
    Idempotent; never clobbers a foreign hooksPath value.
    """

    def _make_hook(self, tmp_path):
        hook_dir = tmp_path / git_ops._HOOKS_DIR_REL
        hook_dir.mkdir(parents=True)
        (hook_dir / "pre-commit").write_text("#!/bin/sh\nexit 0\n")

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_missing_hook_returns_false(self, mock_run, mock_run_list, tmp_path, monkeypatch):
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)  # no hook created
        assert git_ops.install_hooks() is False
        mock_run_list.assert_not_called()

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_sets_hookspath_when_unset(self, mock_run, mock_run_list, tmp_path, monkeypatch):
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)
        self._make_hook(tmp_path)
        mock_run.return_value = _mock_result(stdout="\n")  # core.hooksPath unset
        mock_run_list.return_value = _mock_result(returncode=0)  # config write OK
        assert git_ops.install_hooks() is True
        set_calls = [c for c in mock_run_list.call_args_list
                     if c.args[0][:3] == ["git", "config", "core.hooksPath"]]
        assert len(set_calls) == 1
        assert set_calls[0].args[0][-1] == git_ops._HOOKS_DIR_REL

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_idempotent_when_already_ours(self, mock_run, mock_run_list, tmp_path, monkeypatch):
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)
        self._make_hook(tmp_path)
        mock_run.return_value = _mock_result(stdout=git_ops._HOOKS_DIR_REL + "\n")
        assert git_ops.install_hooks() is True
        # Already ours -> no re-set of core.hooksPath.
        set_calls = [c for c in mock_run_list.call_args_list
                     if c.args[0][:3] == ["git", "config", "core.hooksPath"]]
        assert not set_calls

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_foreign_hookspath_not_clobbered(self, mock_run, mock_run_list, tmp_path, monkeypatch):
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)
        self._make_hook(tmp_path)
        mock_run.return_value = _mock_result(stdout=".husky\n")  # user's own hooks
        assert git_ops.install_hooks() is False
        set_calls = [c for c in mock_run_list.call_args_list
                     if c.args[0][:3] == ["git", "config", "core.hooksPath"]]
        assert not set_calls  # left the foreign value alone

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_returns_false_when_config_write_fails(self, mock_run, mock_run_list, tmp_path, monkeypatch):
        # Contract: "Returns True if the guard is active after the call." A
        # failed `git config core.hooksPath` write (read-only .git/config) must
        # report False, not claim activation that never took.
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)
        self._make_hook(tmp_path)
        mock_run.return_value = _mock_result(stdout="\n")  # core.hooksPath unset
        mock_run_list.return_value = _mock_result(returncode=1)  # write fails
        assert git_ops.install_hooks() is False

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_chmod_failure_returns_false_on_posix(
        self, mock_run, mock_run_list, tmp_path, monkeypatch
    ):
        # On POSIX git only fires a hook with the exec bit set. If chmod fails
        # the guard is installed but won't run -> report False, not a false
        # "active" (#11511 DS re-review Finding 1).
        import os
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)
        self._make_hook(tmp_path)
        mock_run.return_value = _mock_result(stdout="\n")  # core.hooksPath unset
        mock_run_list.return_value = _mock_result(returncode=0)  # config write OK
        monkeypatch.setattr(os, "name", "posix")
        monkeypatch.setattr(os, "chmod", lambda *a, **k: (_ for _ in ()).throw(OSError("noexec")))
        assert git_ops.install_hooks() is False

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_chmod_failure_benign_on_windows(
        self, mock_run, mock_run_list, tmp_path, monkeypatch
    ):
        # On Windows git ignores the exec bit (the shim runs via sh), so a chmod
        # failure is benign and the guard is still active -> True.
        import os
        monkeypatch.setattr(git_ops, "REPO_ROOT", tmp_path)
        self._make_hook(tmp_path)
        mock_run.return_value = _mock_result(stdout="\n")
        mock_run_list.return_value = _mock_result(returncode=0)
        monkeypatch.setattr(os, "name", "nt")
        monkeypatch.setattr(os, "chmod", lambda *a, **k: (_ for _ in ()).throw(OSError("denied")))
        assert git_ops.install_hooks() is True


class TestHookShippedExecutable11511:
    """#11511 DS re-review2: the pre-commit hook must be tracked with the
    executable mode (100755). On POSIX git only fires a hook whose exec bit is
    set, and `git checkout`/`pull` restore a tracked file to its RECORDED mode.
    If the hook were tracked 100644, a later checkout would silently drop the
    exec bit and the guard would stop firing -- the self-heal noops when
    core.hooksPath is already ours, so nothing would restore it. Tracking the
    hook 100755 fixes the exec bit at the source so it survives every checkout.
    This is a repo invariant, so it reads the real git index (not a mock).
    """

    def test_hook_tracked_executable(self):
        import subprocess
        out = subprocess.run(
            ["git", "ls-files", "-s", "--", "references/git-hooks/pre-commit"],
            cwd=str(git_ops.REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert out.returncode == 0, out.stderr
        line = out.stdout.strip()
        assert line, "pre-commit hook is not tracked in git"
        mode = line.split()[0]
        assert mode == "100755", (
            f"pre-commit hook tracked as mode {mode}, expected 100755 "
            f"(POSIX needs the exec bit or git silently skips the guard)"
        )


class TestEnsureHooksInstalled11511:
    """#11511 DS re-review Finding 4: the self-heal path installs our guard when
    core.hooksPath is unset, but respects a foreign value SILENTLY (no per-
    invocation WARNING -- each git_ops call is a fresh process, so a warn-once
    flag can't help). The explicit `install-hooks` command still warns.
    """

    @patch("git_ops.install_hooks")
    @patch("git_ops._run")
    def test_installs_when_unset(self, mock_run, mock_install):
        mock_run.return_value = _mock_result(stdout="\n")  # hooksPath unset
        git_ops._ensure_hooks_installed()
        mock_install.assert_called_once()

    @patch("git_ops.install_hooks")
    @patch("git_ops._run")
    def test_noop_when_already_ours(self, mock_run, mock_install):
        mock_run.return_value = _mock_result(stdout=git_ops._HOOKS_DIR_REL + "\n")
        git_ops._ensure_hooks_installed()
        mock_install.assert_not_called()

    @patch("git_ops.install_hooks")
    @patch("git_ops._run")
    def test_silent_skip_on_foreign(self, mock_run, mock_install):
        # Foreign hooksPath -> do NOT call install_hooks (which would warn every
        # invocation). Respect the operator's config silently.
        mock_run.return_value = _mock_result(stdout=".husky\n")
        git_ops._ensure_hooks_installed()
        mock_install.assert_not_called()


class TestEnsureHooksDispatch11511:
    """#11511 Part 2: main() self-heals hooks on every invocation EXCEPT the
    guard (called mid-commit) and install-hooks (which installs explicitly --
    self-healing first would double the foreign-hooksPath WARNING).
    """

    @patch("git_ops.install_hooks", return_value=True)
    @patch("git_ops._ensure_hooks_installed")
    def test_install_hooks_cmd_skips_self_heal(self, mock_ensure, mock_install, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["git_ops.py", "install-hooks"])
        with pytest.raises(SystemExit):
            git_ops.main()
        mock_ensure.assert_not_called()   # no duplicate self-heal pass
        mock_install.assert_called_once()  # explicit dispatch still installs

    @patch("git_ops.guard_staged_state")
    @patch("git_ops._ensure_hooks_installed")
    def test_guard_cmd_skips_self_heal(self, mock_ensure, _mock_guard, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["git_ops.py", "guard-staged-state"])
        with pytest.raises(SystemExit):
            git_ops.main()
        mock_ensure.assert_not_called()

    @patch("git_ops.has_changes")
    @patch("git_ops._ensure_hooks_installed")
    def test_other_cmd_self_heals(self, mock_ensure, _mock_has, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["git_ops.py", "has-changes"])
        git_ops.main()
        mock_ensure.assert_called_once()


class TestEnsureMainAndPullSerialized13211:
    """#13211: ensure_main_and_pull single-flights its checkout+pull via the
    module-level _ENSURE_MAIN_LOCK so concurrent in-process callers (the L4
    watcher freshen bursts AND the post-merge deploy-all path) cannot collide on
    `.git/index.lock`. #13197 first added this serialization in the watcher; this
    hoists it to the shared implementation so every caller is covered."""

    def test_lock_is_a_threading_lock(self):
        import threading
        assert isinstance(git_ops._ENSURE_MAIN_LOCK, type(threading.Lock()))

    def test_contract_preserved_on_main_synced(self):
        """Behaviour unchanged for the happy path: on main + pull ok -> (True,
        'on-main-synced'). The lock wrap must not alter the return contract."""
        with patch.object(git_ops, "_run") as mrun, \
             patch.object(git_ops, "pull", return_value=True):
            mrun.return_value = MagicMock(returncode=0, stdout="main\n", stderr="")
            ok, detail = git_ops.ensure_main_and_pull(role="harness")
        assert ok is True
        assert detail == "on-main-synced"

    def test_pull_failure_still_reported(self):
        """The lock must not swallow a pull failure."""
        with patch.object(git_ops, "_run") as mrun, \
             patch.object(git_ops, "pull", return_value=False):
            mrun.return_value = MagicMock(returncode=0, stdout="main\n", stderr="")
            ok, detail = git_ops.ensure_main_and_pull(role="harness")
        assert ok is False
        assert detail == "pull-failed"

    def test_concurrent_calls_are_serialized(self):
        """N threads calling ensure_main_and_pull directly must never run the
        underlying git op concurrently — max in-flight stays 1."""
        import threading
        import time as _time
        state = {"now": 0, "max": 0}
        guard = threading.Lock()
        N = 11
        barrier = threading.Barrier(N)

        def fake_pull(role=None):
            try:
                barrier.wait(timeout=0.5)  # serialized -> never fills -> times out
            except threading.BrokenBarrierError:
                pass
            with guard:
                state["now"] += 1
                state["max"] = max(state["max"], state["now"])
            _time.sleep(0.02)
            with guard:
                state["now"] -= 1
            return True

        def fake_run(cmd, check=False):
            return MagicMock(returncode=0, stdout="main\n", stderr="")

        with patch.object(git_ops, "_run", side_effect=fake_run), \
             patch.object(git_ops, "pull", side_effect=fake_pull):
            threads = [threading.Thread(
                target=lambda: git_ops.ensure_main_and_pull("harness"))
                for _ in range(N)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert state["max"] == 1, (
            f"ensure_main_and_pull ran {state['max']}-way concurrent — "
            f"_ENSURE_MAIN_LOCK is not serializing (#13211)"
        )


# ---------------------------------------------------------------------------
# #13285 — post-merge scope-audit + (opt-in) auto-revert
# ---------------------------------------------------------------------------

class TestScopeAudit13285:
    def test_violations_are_deleted_minus_declared(self):
        with patch.object(git_ops, "_pr_declared_files",
                          return_value={"a.py", "b.py"}), \
             patch.object(git_ops, "_merge_deleted_files",
                          return_value={"a.py", "config.md",
                                        ".squidsquad/pm/CLAUDE.md"}):
            v = git_ops._scope_audit_violations(1, "sha")
        # a.py was declared (a legit deletion); the other two are out-of-scope.
        assert v == [".squidsquad/pm/CLAUDE.md", "config.md"]

    def test_clean_merge_no_violations(self):
        with patch.object(git_ops, "_pr_declared_files",
                          return_value={"a.py", "b.py"}), \
             patch.object(git_ops, "_merge_deleted_files",
                          return_value={"a.py"}):  # only a declared deletion
            assert git_ops._scope_audit_violations(1, "sha") == []

    def test_fail_safe_when_declared_unknown(self):
        """gh failure → declared None → audit returns None (caller won't revert)."""
        with patch.object(git_ops, "_pr_declared_files", return_value=None), \
             patch.object(git_ops, "_merge_deleted_files", return_value={"x"}):
            assert git_ops._scope_audit_violations(1, "sha") is None

    def test_fail_safe_when_deleted_unknown(self):
        with patch.object(git_ops, "_pr_declared_files", return_value={"a"}), \
             patch.object(git_ops, "_merge_deleted_files", return_value=None):
            assert git_ops._scope_audit_violations(1, "sha") is None

    def test_auto_revert_flag_default_off(self, monkeypatch):
        monkeypatch.delenv("SQUIDSQUAD_MERGE_AUTO_REVERT", raising=False)
        assert git_ops._merge_auto_revert_enabled() is False

    def test_auto_revert_flag_on(self, monkeypatch):
        monkeypatch.setenv("SQUIDSQUAD_MERGE_AUTO_REVERT", "1")
        assert git_ops._merge_auto_revert_enabled() is True

    def test_audit_clean_merge_emits_nothing(self):
        with patch.object(git_ops, "_run_list", return_value=_mock_result()), \
             patch.object(git_ops, "_merge_commit_sha", return_value="sha123"), \
             patch.object(git_ops, "_scope_audit_violations", return_value=[]), \
             patch.object(git_ops, "_emit_scope_incident") as emit, \
             patch.object(git_ops, "_auto_revert_merge") as revert:
            git_ops._post_merge_scope_audit(1, "42")
        emit.assert_not_called()
        revert.assert_not_called()

    def test_audit_violation_emits_incident_no_revert_when_off(self, monkeypatch):
        monkeypatch.delenv("SQUIDSQUAD_MERGE_AUTO_REVERT", raising=False)
        with patch.object(git_ops, "_run_list", return_value=_mock_result()), \
             patch.object(git_ops, "_merge_commit_sha", return_value="sha123"), \
             patch.object(git_ops, "_scope_audit_violations",
                          return_value=["config.md", ".squidsquad/pm/CLAUDE.md"]), \
             patch.object(git_ops, "_emit_scope_incident") as emit, \
             patch.object(git_ops, "_auto_revert_merge") as revert:
            git_ops._post_merge_scope_audit(1, "42")
        emit.assert_called_once()
        revert.assert_not_called()  # default OFF → detect+alert only

    def test_audit_violation_auto_reverts_when_on(self, monkeypatch):
        monkeypatch.setenv("SQUIDSQUAD_MERGE_AUTO_REVERT", "1")
        with patch.object(git_ops, "_run_list", return_value=_mock_result()), \
             patch.object(git_ops, "_merge_commit_sha", return_value="sha123"), \
             patch.object(git_ops, "_scope_audit_violations",
                          return_value=["config.md"]), \
             patch.object(git_ops, "_emit_scope_incident"), \
             patch.object(git_ops, "_auto_revert_merge") as revert:
            git_ops._post_merge_scope_audit(1, "42")
        revert.assert_called_once_with("sha123", 1)

    def test_audit_fail_safe_no_revert_on_inconclusive(self, monkeypatch):
        monkeypatch.setenv("SQUIDSQUAD_MERGE_AUTO_REVERT", "1")
        with patch.object(git_ops, "_run_list", return_value=_mock_result()), \
             patch.object(git_ops, "_merge_commit_sha", return_value="sha123"), \
             patch.object(git_ops, "_scope_audit_violations", return_value=None), \
             patch.object(git_ops, "_emit_scope_incident") as emit, \
             patch.object(git_ops, "_auto_revert_merge") as revert:
            git_ops._post_merge_scope_audit(1, "42")
        emit.assert_not_called()
        revert.assert_not_called()  # None = uncertainty → never revert

    def test_audit_never_raises(self):
        """A fault anywhere in the audit must not break the merge flow."""
        with patch.object(git_ops, "_run_list",
                          side_effect=RuntimeError("boom")):
            # must not raise
            git_ops._post_merge_scope_audit(1, "42")

    def test_auto_revert_is_non_destructive_revert_then_push(self):
        calls = []

        def rec(args, **kw):
            calls.append(args)
            return _mock_result()

        with patch.object(git_ops, "_safe_checkout", return_value=True), \
             patch.object(git_ops, "_run_list", side_effect=rec):
            git_ops._auto_revert_merge("sha123", 1)
        # git revert --no-edit (NOT reset/force), then push.
        assert ["git", "revert", "--no-edit", "sha123"] in calls
        assert any(c[:3] == ["git", "push", "origin"] for c in calls)
        assert not any("--force" in c or "reset" in c for c in calls)

    def test_rename_old_path_not_a_violation(self):
        """A dissimilar rename shows as D(old)+A(new); gh declares BOTH paths, so
        the deleted old path is in `declared` and is NOT a false violation."""
        with patch.object(git_ops, "_pr_declared_files",
                          return_value={"old_name.py", "new_name.py"}), \
             patch.object(git_ops, "_merge_deleted_files",
                          return_value={"old_name.py"}):
            assert git_ops._scope_audit_violations(1, "sha") == []

    def test_merge_commit_sha_null_is_unresolved(self):
        """gh prints literal 'null' before the merge commit is recorded -> None
        (fail-safe), not the string 'null'."""
        with patch.object(git_ops, "_run_list",
                          return_value=_mock_result(stdout="null\n")):
            assert git_ops._merge_commit_sha(1) is None

    def test_auto_revert_aborts_when_checkout_fails(self):
        """_safe_checkout False -> no revert, no push (cannot safely act)."""
        with patch.object(git_ops, "_safe_checkout", return_value=False), \
             patch.object(git_ops, "_run_list") as rl:
            git_ops._auto_revert_merge("sha123", 1)
        rl.assert_not_called()

    def test_auto_revert_push_failure_undoes_local_revert(self):
        """A failed push must reset the local revert commit so the next pull can't
        silently fuse it into main without review."""
        def rl(args, **kw):
            if args[:2] == ["git", "push"]:
                return _mock_result(returncode=1, stderr="non-fast-forward")
            return _mock_result()

        with patch.object(git_ops, "_safe_checkout", return_value=True), \
             patch.object(git_ops, "_run_list", side_effect=rl) as rl_mock:
            git_ops._auto_revert_merge("sha123", 1)
        called = [c.args[0] for c in rl_mock.call_args_list]
        assert ["git", "reset", "--keep", "HEAD~1"] in called

    def test_auto_revert_aborts_on_revert_failure(self):
        def rl(args, **kw):
            if args[:2] == ["git", "revert"] and "--abort" not in args:
                return _mock_result(returncode=1, stderr="conflict")
            return _mock_result()

        with patch.object(git_ops, "_safe_checkout", return_value=True), \
             patch.object(git_ops, "_run_list", side_effect=rl) as rl_mock:
            git_ops._auto_revert_merge("sha123", 1)
        # On a failed revert it must `git revert --abort` and NOT push.
        called = [c.args[0] for c in rl_mock.call_args_list]
        assert ["git", "revert", "--abort"] in called
        assert not any(c[:2] == ["git", "push"] for c in called)


# ---------------------------------------------------------------------------
# #13454 — a DRAFT PR reaching pending-test hit the verifier auto-merge lane
# with a raw GraphQL "Pull Request is still a draft" error (and gh's mergeable
# probe reports MERGEABLE/CLEAN, so nothing warned first). pr_merge now reads
# isDraft and self-heals via pr_ready before merging.
# ---------------------------------------------------------------------------

class TestPrMergeDraftSelfHeal:
    @pytest.fixture(autouse=True)
    def _safe_behind(self):
        with patch("git_ops._pr_behind_by", return_value=0), \
                patch("git_ops._post_merge_scope_audit"):
            yield

    @patch("git_ops.pr_ready", return_value=True)
    @patch("git_ops._run_list")
    def test_draft_pr_readied_then_merged(self, mock_run, mock_ready):
        # state probe reports a draft; pr_ready succeeds; merge proceeds.
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN", "isDraft": true}'),
            _mock_result(stdout=""),  # merge succeeds
            _mock_result(stdout='{"headRefName": "squidsquad/skill/42"}'),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is True
        assert msg == "merged"
        mock_ready.assert_called_once_with(42)
        # The state probe requests isDraft.
        assert "state,isDraft" in mock_run.call_args_list[0][0][0]

    @patch("git_ops.pr_ready", return_value=False)
    @patch("git_ops._run_list")
    def test_draft_ready_failure_refuses_without_merge(self, mock_run, mock_ready):
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN", "isDraft": true}'),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is False
        assert msg == "PR is a draft"
        mock_ready.assert_called_once_with(42)
        # Merge must NOT be attempted — only the state probe ran.
        assert mock_run.call_count == 1

    @patch("git_ops.pr_ready")
    @patch("git_ops._run_list")
    def test_non_draft_pr_does_not_call_ready(self, mock_run, mock_ready):
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN", "isDraft": false}'),
            _mock_result(stdout=""),
            _mock_result(stdout='{"headRefName": "squidsquad/skill/42"}'),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is True
        mock_ready.assert_not_called()

    @patch("git_ops.pr_ready")
    @patch("git_ops._run_list")
    def test_absent_isdraft_field_treated_as_non_draft(self, mock_run, mock_ready):
        # Backward-compat: a state probe response without isDraft (older gh /
        # existing test fixtures) must not trip the self-heal.
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stdout=""),
            _mock_result(stdout='{"headRefName": "squidsquad/skill/42"}'),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is True
        mock_ready.assert_not_called()


# ---------------------------------------------------------------------------
# #13371 — pr_create neutralizes GitHub closing keywords in the PR body so a
# stray "Fixes #N" cannot auto-close the issue at squash-merge and bypass the
# pending-ship -> shipped DM gate (ship counter + changelog + recorded verdict).
# ---------------------------------------------------------------------------

class TestNeutralizeClosingKeywords:
    def test_fixes_hash_rewritten(self):
        assert git_ops._neutralize_closing_keywords("Fixes #123") == "Addresses #123"

    def test_all_keyword_variants_rewritten(self):
        for kw in ("close", "closes", "closed", "fix", "fixes", "fixed",
                   "resolve", "resolves", "resolved"):
            out = git_ops._neutralize_closing_keywords(f"{kw} #7")
            assert out == "Addresses #7", f"{kw!r} not neutralized: {out!r}"

    def test_case_insensitive(self):
        assert git_ops._neutralize_closing_keywords("FIXES #1") == "Addresses #1"
        assert git_ops._neutralize_closing_keywords("Resolves #2") == "Addresses #2"

    def test_colon_separator_preserved(self):
        assert git_ops._neutralize_closing_keywords("Closes: #45") == "Addresses: #45"

    def test_cross_repo_reference(self):
        assert (git_ops._neutralize_closing_keywords("Fixes owner/repo#12")
                == "Addresses owner/repo#12")

    def test_issue_url_reference(self):
        body = "Fixes https://github.com/WallyDoodlez/SquidSquad/issues/34"
        assert (git_ops._neutralize_closing_keywords(body)
                == "Addresses https://github.com/WallyDoodlez/SquidSquad/issues/34")

    def test_multiple_occurrences_all_rewritten(self):
        assert (git_ops._neutralize_closing_keywords("Fixes #1, closes #2")
                == "Addresses #1, Addresses #2")

    def test_non_closing_reference_untouched(self):
        for body in ("Cross-ref #12", "Addresses #12", "See #12", "Part of #12"):
            assert git_ops._neutralize_closing_keywords(body) == body

    def test_subword_keywords_not_matched(self):
        # \b anchors: these contain a keyword as a substring but are not one.
        for body in ("prefix #1", "hotfixes #2", "affixes #3", "postfixed #4"):
            assert git_ops._neutralize_closing_keywords(body) == body, body

    def test_keyword_without_immediate_reference_untouched(self):
        # GitHub only closes when the ref directly follows the keyword.
        body = "This fixes the bug described in #5 nicely."
        assert git_ops._neutralize_closing_keywords(body) == body

    def test_empty_and_none_passthrough(self):
        assert git_ops._neutralize_closing_keywords("") == ""
        assert git_ops._neutralize_closing_keywords(None) is None

    def test_bare_reference_no_space_untouched(self):
        # No separator -> GitHub does not close -> leave alone.
        assert git_ops._neutralize_closing_keywords("fix#1") == "fix#1"


class TestPrCreateNeutralizesBody:
    def test_body_neutralized_before_gh(self):
        captured = {}

        def fake_run_list(cmd, **kwargs):
            captured["cmd"] = cmd
            return _mock_result(stdout="https://github.com/o/r/pull/99")

        with patch.object(git_ops, "_get_working_branch", return_value="main"), \
             patch.object(git_ops, "_run_list", side_effect=fake_run_list), \
             patch.object(git_ops, "_run",
                          return_value=_mock_result(stdout="squidsquad/task/13371")), \
             patch.object(git_ops, "_emit"):
            git_ops.pr_create("skill: #13371 title", "Body text.\nFixes #13335")

        cmd = captured["cmd"]
        body_arg = cmd[cmd.index("--body") + 1]
        assert "Fixes #13335" not in body_arg
        assert "Addresses #13335" in body_arg
