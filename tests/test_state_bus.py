"""Tests for references/scripts/state_bus.py — state branch worktree management."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import state_bus


class TestReadBranchConfig:
    def test_reads_from_config(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text(
            "## Git Branches\n\n"
            "- **Working Branch**: dev\n"
            "- **State Branch**: agent-state\n"
        )
        with patch.object(state_bus, "CONFIG_MD", config):
            working, state = state_bus._read_branch_config()
        assert working == "dev"
        assert state == "agent-state"

    def test_defaults_when_missing(self, tmp_path):
        with patch.object(state_bus, "CONFIG_MD", tmp_path / "missing"):
            working, state = state_bus._read_branch_config()
        assert working == "stag"
        assert state == "squid-squad"

    def test_defaults_when_no_section(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("## Project\n\n- **Name**: test\n")
        with patch.object(state_bus, "CONFIG_MD", config):
            working, state = state_bus._read_branch_config()
        assert working == "stag"
        assert state == "squid-squad"


class TestWorktreeExists:
    def test_true_when_git_present(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            assert state_bus._worktree_exists() is True

    def test_false_when_missing(self, tmp_path):
        with patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"):
            assert state_bus._worktree_exists() is False

    def test_false_when_no_git(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            assert state_bus._worktree_exists() is False


class TestReadFile:
    def test_reads_existing_file(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        (wt / "test.txt").write_text("hello")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            content = state_bus.read_file("test.txt")
        assert content == "hello"

    def test_returns_none_for_missing(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            assert state_bus.read_file("missing.txt") is None

    def test_returns_none_when_no_worktree(self, tmp_path):
        with patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"):
            assert state_bus.read_file("test.txt") is None


class TestWriteFile:
    def test_writes_file(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            result = state_bus.write_file("test.txt", "content")
        assert result is True
        assert (wt / "test.txt").read_text() == "content"

    def test_creates_subdirs(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            result = state_bus.write_file("sub/dir/file.txt", "nested")
        assert result is True
        assert (wt / "sub" / "dir" / "file.txt").read_text() == "nested"

    def test_fails_when_no_worktree(self, tmp_path):
        with patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"):
            assert state_bus.write_file("test.txt", "x") is False


class TestStatus:
    def test_outputs_json(self, tmp_path, capsys):
        config = tmp_path / "config.md"
        config.write_text(
            "## Git Branches\n\n"
            "- **Working Branch**: dev\n"
            "- **State Branch**: my-state\n"
        )
        with patch.object(state_bus, "CONFIG_MD", config), \
             patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"):
            code = state_bus.status()
        assert code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["state_branch"] == "my-state"
        assert output["worktree_exists"] is False


class TestInitBranchRecovery:
    """Regression tests for #3290 — init() must restore original branch on failure."""

    @patch.object(state_bus, "_state_branch_exists", return_value=False)
    @patch.object(state_bus, "_worktree_exists", return_value=True)
    def test_captures_original_branch(self, mock_wt, mock_exists):
        """#3290: init() captures current branch before orphan checkout."""
        calls = []

        def fake_run(cmd, check=True, cwd=None):
            calls.append(cmd)
            result = MagicMock()
            result.returncode = 0
            result.stdout = "main\n"
            if "checkout" in cmd and "--orphan" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return result

        import subprocess
        with patch.object(state_bus, "_run", side_effect=fake_run), \
             patch.object(state_bus, "REPO_ROOT", Path("/tmp/fake")):
            try:
                state_bus.init()
            except Exception:
                pass

        # First call should be rev-parse to capture current branch
        assert any("rev-parse" in str(c) for c in calls), \
            "init() must capture current branch via rev-parse before orphan checkout"

    @patch.object(state_bus, "_state_branch_exists", return_value=False)
    @patch.object(state_bus, "_worktree_exists", return_value=True)
    def test_restores_branch_on_failure(self, mock_wt, mock_exists):
        """#3290: init() restores original branch even when orphan checkout fails."""
        checkout_targets = []

        def fake_run(cmd, check=True, cwd=None):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "my-feature\n"
            if "checkout" in cmd and "--orphan" not in cmd and "rev-parse" not in str(cmd):
                checkout_targets.append(cmd[-1] if cmd else None)
            if "commit" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return result

        import subprocess
        with patch.object(state_bus, "_run", side_effect=fake_run), \
             patch.object(state_bus, "REPO_ROOT", Path("/tmp/fake")):
            try:
                state_bus.init()
            except Exception:
                pass

        # Should attempt to checkout the original branch in finally
        assert "my-feature" in checkout_targets, \
            "init() must restore original branch (my-feature) in finally block"

    def test_no_hardcoded_main_fallback(self):
        """#3290: init() should not have a hardcoded 'main' fallback."""
        import inspect
        source = inspect.getsource(state_bus.init)
        # The old code had: _run(["git", "checkout", "main"], check=False)
        # The new code uses _read_branch_config() for the fallback
        assert '"main"' not in source or "_read_branch_config" in source, \
            "init() should use _read_branch_config() for fallback, not hardcoded 'main'"


class TestIsStateFile:
    """#3664: is_state_file classifies paths correctly."""

    def test_iterations_is_state(self):
        assert state_bus.is_state_file("skill/iterations/iter-1.md") is True

    def test_working_state_is_state(self):
        assert state_bus.is_state_file("pm/working-state.md") is True

    def test_scan_history_is_state(self):
        assert state_bus.is_state_file("skill/scan-history.md") is True

    def test_diagnostics_is_state(self):
        assert state_bus.is_state_file("diagnostics/diagnostic.jsonl") is True

    def test_config_is_not_state(self):
        assert state_bus.is_state_file("config.md") is False

    def test_claude_md_is_not_state(self):
        assert state_bus.is_state_file("skill/CLAUDE.md") is False

    def test_vault_is_not_state(self):
        assert state_bus.is_state_file("vault/galaxy/decision-foo.md") is False

    def test_planning_is_not_state(self):
        assert state_bus.is_state_file("pm/planning/FEAT-PM-123-CONTEXT.md") is False

    def test_iterations_dir_no_trailing_slash(self):
        """#3664 QA fix: bare dir path without trailing slash must match."""
        assert state_bus.is_state_file("skill/iterations") is True

    def test_diagnostics_dir_no_trailing_slash(self):
        """#3664 QA fix: bare dir path without trailing slash must match."""
        assert state_bus.is_state_file("diagnostics") is True


class TestStatePath:
    """#3664: state_path resolves to worktree for state files, .squidsquad/ for others."""

    def test_state_file_with_worktree(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt), \
             patch.object(state_bus, "REPO_ROOT", tmp_path):
            result = state_bus.state_path("skill/iterations/iter-1.md")
        assert str(wt) in str(result)

    def test_non_state_file_stays_on_main(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt), \
             patch.object(state_bus, "REPO_ROOT", tmp_path):
            result = state_bus.state_path("config.md")
        assert ".squidsquad" in str(result)
        assert str(wt) not in str(result)

    def test_state_file_without_worktree_falls_back(self, tmp_path):
        with patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"), \
             patch.object(state_bus, "REPO_ROOT", tmp_path):
            result = state_bus.state_path("skill/iterations/iter-1.md")
        assert ".squidsquad" in str(result)


class TestCLI:
    def test_help(self):
        sys.argv = ["state_bus.py", "--help"]
        code = state_bus.main()
        assert code == 0

    def test_unknown_command(self):
        sys.argv = ["state_bus.py", "badcmd"]
        code = state_bus.main()
        assert code == 2


# ---------------------------------------------------------------------------
# #7589: commit_and_push must detect failed git commit
# ---------------------------------------------------------------------------

class TestCommitAndPushFailedCommit:
    """#7589: commit_and_push returns False when git commit fails."""

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_returns_false_on_commit_failure(self, mock_run, mock_config, mock_wt):
        """Failed git commit should return False, not proceed to push."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),     # git add -A
            MagicMock(stdout=" M file.md\n", returncode=0),  # git status --porcelain
            MagicMock(stdout="", stderr="error: hook rejected", returncode=1),  # git commit FAILS
        ]
        result = state_bus.commit_and_push("test msg", role="skill")
        assert result is False
        # Push should NOT have been called (only 3 _run calls, not 4+)
        assert mock_run.call_count == 3

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_returns_true_on_commit_success(self, mock_run, mock_config, mock_wt):
        """Successful commit + push returns True."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),     # git add -A
            MagicMock(stdout=" M file.md\n", returncode=0),  # git status --porcelain
            MagicMock(stdout="", stderr="", returncode=0),  # git commit succeeds
            MagicMock(stdout="", returncode=0),     # git push succeeds
        ]
        result = state_bus.commit_and_push("test msg", role="skill")
        assert result is True


# ---------------------------------------------------------------------------
# #9930 — credential helper override + timeout + --rebase pull
# ---------------------------------------------------------------------------


class TestPushHardening9930:
    """#9930: commit_and_push must (a) bypass credential.helper=manager
    via `gh auth git-credential`, (b) bound every git op with a timeout
    so a wedged helper can't hang the cycle, and (c) use `pull --rebase`
    instead of default-merge so retry divergence keeps history linear.
    """

    def test_default_git_timeout_is_bounded(self):
        """The default must be a positive finite value — not None."""
        assert isinstance(state_bus.DEFAULT_GIT_TIMEOUT, (int, float))
        assert 0 < state_bus.DEFAULT_GIT_TIMEOUT <= 600

    def test_run_returns_124_on_timeout(self):
        """`_run` must catch TimeoutExpired and return CompletedProcess
        with returncode=124 — never raise — so existing
        `if result.returncode != 0` paths degrade gracefully.
        """
        import subprocess
        with patch.object(state_bus.subprocess, "run") as mock_sp:
            mock_sp.side_effect = subprocess.TimeoutExpired(
                cmd=["git", "push"], timeout=1
            )
            result = state_bus._run(["git", "push"], check=False, timeout=1)
        assert result.returncode == 124
        assert "TIMEOUT" in result.stderr

    def test_run_passes_timeout_to_subprocess(self):
        """`_run` forwards `timeout` to subprocess.run when set."""
        import subprocess
        captured = {}

        def fake_sp(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch.object(state_bus.subprocess, "run", side_effect=fake_sp):
            state_bus._run(["git", "status"], check=False, timeout=42)
        assert captured.get("timeout") == 42

    def test_run_default_timeout_is_none_for_backcompat(self):
        """`_run` without explicit timeout passes ``None`` — the
        constructor signature change must NOT alter the behavior of
        existing call sites that didn't ask for a bound."""
        import subprocess
        captured = {}

        def fake_sp(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch.object(state_bus.subprocess, "run", side_effect=fake_sp):
            state_bus._run(["git", "status"], check=False)
        assert captured.get("timeout") is None

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_push_uses_gh_credential_override(self, mock_run, mock_config, mock_wt):
        """The push command must include `-c credential.helper=!gh auth
        git-credential` so credential.helper=manager (which hangs
        silently on Windows) is bypassed for this network op.
        """
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
            MagicMock(stdout="", returncode=0),                 # push (success)
        ]
        state_bus.commit_and_push("msg", role="skill")
        # The 4th call is the push — inspect its command list.
        push_call = mock_run.call_args_list[3]
        cmd = push_call.args[0]
        assert "credential.helper=!gh auth git-credential" in cmd, (
            f"push command missing credential override: {cmd}"
        )
        assert "push" in cmd and "origin" in cmd

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_push_bounded_by_default_timeout(self, mock_run, mock_config, mock_wt):
        """Push call must pass `timeout=DEFAULT_GIT_TIMEOUT` so a
        wedged credential helper can't hang indefinitely (the original
        #9930 symptom)."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
            MagicMock(stdout="", returncode=0),                 # push
        ]
        state_bus.commit_and_push("msg", role="skill")
        push_call = mock_run.call_args_list[3]
        assert push_call.kwargs.get("timeout") == state_bus.DEFAULT_GIT_TIMEOUT

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_retry_pull_uses_rebase(self, mock_run, mock_config, mock_wt):
        """On push failure, the retry pull must use `--rebase` (not the
        default merge) so divergent state-branch history stays linear
        instead of accumulating `Merge branch 'squid-squad'` commits.
        """
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
            MagicMock(stdout="", returncode=1),                 # push FAILS
            MagicMock(stdout="", returncode=0),                 # pull --rebase
            MagicMock(stdout="", returncode=0),                 # push retry SUCCEEDS
        ]
        state_bus.commit_and_push("msg", role="skill")
        # 5th call should be the pull --rebase.
        pull_call = mock_run.call_args_list[4]
        cmd = pull_call.args[0]
        assert "pull" in cmd
        assert "--rebase" in cmd, f"retry pull missing --rebase: {cmd}"

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_retry_pull_uses_credential_override(self, mock_run, mock_config, mock_wt):
        """The retry pull is also a network op — it must use the same
        credential override or it'd wedge on the same helper as push."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
            MagicMock(stdout="", returncode=1),                 # push FAILS
            MagicMock(stdout="", returncode=0),                 # pull --rebase
            MagicMock(stdout="", returncode=0),                 # push retry
        ]
        state_bus.commit_and_push("msg", role="skill")
        pull_call = mock_run.call_args_list[4]
        cmd = pull_call.args[0]
        assert "credential.helper=!gh auth git-credential" in cmd

    def test_run_preserves_stdout_on_timeout(self):
        """#9930 DS review F3: TimeoutExpired handler must preserve
        partial stdout (a pre-push hook may print diagnostics before
        the hang). Earlier the handler dropped it unconditionally."""
        import subprocess
        with patch.object(state_bus.subprocess, "run") as mock_sp:
            mock_sp.side_effect = subprocess.TimeoutExpired(
                cmd=["git", "push"],
                timeout=1,
                output="some stdout from a pre-push hook",
                stderr="partial stderr",
            )
            result = state_bus._run(["git", "push"], check=False, timeout=1)
        assert result.stdout == "some stdout from a pre-push hook", (
            "TimeoutExpired stdout was dropped — should be preserved"
        )
        assert "partial stderr" in result.stderr
        assert "TIMEOUT" in result.stderr

    def test_run_handles_none_streams_on_timeout(self):
        """#9930 DS review F4: with text=True, e.stdout / e.stderr are
        str | None, never bytes. The handler must accept None for either
        stream without crashing (e.g., child killed before any output).
        """
        import subprocess
        with patch.object(state_bus.subprocess, "run") as mock_sp:
            mock_sp.side_effect = subprocess.TimeoutExpired(
                cmd=["git", "push"], timeout=1, output=None, stderr=None,
            )
            result = state_bus._run(["git", "push"], check=False, timeout=1)
        assert result.returncode == 124
        assert result.stdout == ""
        assert "TIMEOUT" in result.stderr

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_pull_timeout_triggers_remote_prune(self, mock_run, mock_config, mock_wt):
        """#9930 DS review F1: if `pull --rebase` times out (rc=124),
        the child `git fetch` may have left tmp packfiles / a
        FETCH_HEAD.lock. `rebase --abort` only cleans rebase state; we
        also need `git remote prune origin` to clear stale fetch state
        before the next push attempt."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
            MagicMock(stdout="", returncode=1),                 # push FAILS
            MagicMock(stdout="", returncode=124),               # pull TIMEOUT
            MagicMock(stdout="", returncode=0),                 # rebase --abort
            MagicMock(stdout="", returncode=0),                 # remote prune origin
            MagicMock(stdout="", returncode=0),                 # push retry SUCCEEDS
        ]
        state_bus.commit_and_push("msg", role="skill")
        prune_seen = any(
            "prune" in (c.args[0] if c.args else [])
            and "origin" in (c.args[0] if c.args else [])
            for c in mock_run.call_args_list
        )
        assert prune_seen, (
            f"Expected `git remote prune origin` after pull timeout (rc=124), "
            f"saw: {[c.args[0] for c in mock_run.call_args_list]}"
        )

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_pull_non_timeout_failure_does_not_prune(self, mock_run, mock_config, mock_wt):
        """The prune is specifically for timeout cleanup. A normal
        rebase conflict (rc=1, not 124) should NOT trigger a prune —
        that would waste a 120s budget on every conflict retry."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
            MagicMock(stdout="", returncode=1),                 # push FAILS
            MagicMock(stdout="", returncode=1),                 # pull rc=1 (NOT 124)
            MagicMock(stdout="", returncode=0),                 # rebase --abort
            MagicMock(stdout="", returncode=0),                 # push retry
        ]
        state_bus.commit_and_push("msg", role="skill")
        prune_seen = any(
            "prune" in (c.args[0] if c.args else [])
            for c in mock_run.call_args_list
        )
        assert not prune_seen, (
            f"`git remote prune` should ONLY fire on pull timeout (rc=124), "
            f"not on normal conflict failures. Saw: "
            f"{[c.args[0] for c in mock_run.call_args_list]}"
        )

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_rebase_abort_on_pull_failure(self, mock_run, mock_config, mock_wt):
        """If the retry `pull --rebase` itself fails (e.g., real
        conflict), the loop must `git rebase --abort` so the worktree
        is left clean for the next attempt — leaving a half-rebased
        state was part of the #9930 'leaked state across attempts' bug.
        """
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
            MagicMock(stdout="", returncode=1),                 # push FAILS (1)
            MagicMock(stdout="", returncode=1),                 # pull --rebase FAILS
            MagicMock(stdout="", returncode=0),                 # rebase --abort
            MagicMock(stdout="", returncode=0),                 # push retry SUCCEEDS (2)
        ]
        state_bus.commit_and_push("msg", role="skill")
        # Check that one of the calls is `git rebase --abort`.
        abort_seen = any(
            (lambda cmd: "--abort" in cmd and "rebase" in cmd)(
                c.args[0] if c.args else []
            )
            for c in mock_run.call_args_list
        )
        assert abort_seen, (
            f"Expected `git rebase --abort` after failed pull --rebase, "
            f"saw: {[c.args[0] for c in mock_run.call_args_list]}"
        )


# ---------------------------------------------------------------------------
# #9934 — divergence diagnostic after retry exhaustion
# ---------------------------------------------------------------------------


class TestDivergenceDiagnostic9934:
    """#9934 (follow-up to #9930): when the retry loop exhausts all 3
    attempts because of a real content conflict (push fails, pull --rebase
    keeps failing in the same way), emit a structured diagnostic so the
    operator can manually recover — don't just print the generic
    'failed after 3 attempts' warning and disappear.
    """

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_exhausted_loop_prints_divergence_counts(self, mock_run, mock_config, mock_wt, capsys):
        """After 3 attempts fail, the diagnostic must include both
        local-ahead and origin-ahead commit counts so the operator can
        tell a 1-commit race from a 1000-commit drift."""
        # 3 attempts, each: push fail + pull fail + abort.
        # Then 2 rev-list calls for the divergence summary.
        per_attempt = [
            MagicMock(stdout="", returncode=1),     # push FAILS
            MagicMock(stdout="", stderr="CONFLICT (content) ...", returncode=1),  # pull --rebase FAILS
            MagicMock(stdout="", returncode=0),     # rebase --abort
        ]
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
        ] + per_attempt * 3 + [
            MagicMock(stdout="2\n", returncode=0),              # rev-list local ahead
            MagicMock(stdout="1110\n", returncode=0),           # rev-list origin ahead
        ]
        result = state_bus.commit_and_push("msg", role="skill")
        assert result is False
        captured = capsys.readouterr()
        stderr = captured.err
        assert "WARNING: State push failed after 3 attempts" in stderr
        # Divergence counts must appear so operator knows the scale.
        assert "local is 2 ahead" in stderr
        assert "origin is 1110 ahead" in stderr
        # And the manual recovery command must be visible.
        assert "git fetch origin squid-squad" in stderr
        assert "git reset --hard origin/squid-squad" in stderr

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_diagnostic_flags_content_conflict(self, mock_run, mock_config, mock_wt, capsys):
        """If the last pull stderr mentioned CONFLICT, the diagnostic
        must say so explicitly — operators reading scrollback shouldn't
        have to dig for the actual failure mode."""
        per_attempt = [
            MagicMock(stdout="", returncode=1),
            MagicMock(stdout="",
                      stderr="CONFLICT (content): Merge conflict in qa/working-state.md",
                      returncode=1),
            MagicMock(stdout="", returncode=0),
        ]
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout=" M file.md\n", returncode=0),
            MagicMock(stdout="", stderr="", returncode=0),
        ] + per_attempt * 3 + [
            MagicMock(stdout="0\n", returncode=0),
            MagicMock(stdout="1\n", returncode=0),
        ]
        state_bus.commit_and_push("msg", role="skill")
        stderr = capsys.readouterr().err
        assert "real content conflict" in stderr.lower()

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_diagnostic_skipped_on_success(self, mock_run, mock_config, mock_wt, capsys):
        """The divergence diagnostic must NOT print when the push
        eventually succeeds — only after the loop truly exhausts."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),                 # add -A
            MagicMock(stdout=" M file.md\n", returncode=0),     # status
            MagicMock(stdout="", stderr="", returncode=0),      # commit
            MagicMock(stdout="", returncode=0),                 # push SUCCEEDS first try
        ]
        result = state_bus.commit_and_push("msg", role="skill")
        assert result is True
        stderr = capsys.readouterr().err
        assert "divergence" not in stderr.lower()
        assert "manual recovery" not in stderr.lower()

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_diagnostic_tolerates_rev_list_failure(self, mock_run, mock_config, mock_wt, capsys):
        """The diagnostic is best-effort: if the rev-list calls
        themselves fail (e.g., origin ref missing), the function must
        not raise — the primary 'failed after 3 attempts' warning is
        already on stderr, and the loss of divergence counts is
        recoverable noise, not a crash worth propagating.
        """
        per_attempt = [
            MagicMock(stdout="", returncode=1),
            MagicMock(stdout="", stderr="", returncode=1),
            MagicMock(stdout="", returncode=0),
        ]
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout=" M file.md\n", returncode=0),
            MagicMock(stdout="", stderr="", returncode=0),
        ] + per_attempt * 3 + [
            MagicMock(stdout="", stderr="fatal: bad revision", returncode=128),
            MagicMock(stdout="", stderr="fatal: bad revision", returncode=128),
        ]
        # Must not raise.
        result = state_bus.commit_and_push("msg", role="skill")
        assert result is False
        stderr = capsys.readouterr().err
        # Primary warning still printed; divergence line uses '?' for
        # the missing counts.
        assert "WARNING: State push failed after 3 attempts" in stderr
        assert "local is ? ahead" in stderr or "origin is ? ahead" in stderr
