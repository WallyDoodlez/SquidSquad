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
# pull()
# ---------------------------------------------------------------------------

class TestPull:
    @patch("git_ops._run")
    def test_clean_pull(self, mock_run):
        mock_run.return_value = _mock_result()
        assert git_ops.pull() is True
        mock_run.assert_called_once()

    @patch("git_ops._run")
    def test_pull_stash_pop(self, mock_run):
        """Dirty tree → stash, pull, pop succeeds."""
        mock_run.side_effect = [
            _mock_result(returncode=1),  # pull fails
            _mock_result(),              # stash
            _mock_result(),              # pull (retry)
            _mock_result(),              # stash pop
        ]
        assert git_ops.pull() is True
        assert mock_run.call_count == 4

    @patch("git_ops._run")
    def test_pull_stash_pop_conflict(self, mock_run):
        """Stash pop fails → stash dropped, still returns True (#4829)."""
        mock_run.side_effect = [
            _mock_result(returncode=1),  # pull fails
            _mock_result(),              # stash
            _mock_result(),              # pull (retry)
            _mock_result(returncode=1),  # stash pop fails
            _mock_result(),              # stash drop (#4829)
        ]
        assert git_ops.pull() is True
        assert mock_run.call_count == 5

    @patch("git_ops._run")
    def test_pull_stash_pop_conflict_drops_stash(self, mock_run):
        """Regression #4829: failed stash pop must call git stash drop."""
        mock_run.side_effect = [
            _mock_result(returncode=1),  # pull fails
            _mock_result(),              # stash
            _mock_result(),              # pull (retry)
            _mock_result(returncode=1),  # stash pop fails
            _mock_result(),              # stash drop
        ]
        git_ops.pull()
        drop_call = mock_run.call_args_list[4]
        assert drop_call[0][0] == "git stash drop"


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

    def test_qa_has_no_extras_beyond_common(self):
        pats = git_ops._role_owned_patterns("qa")
        # QA must NOT pick up config or delivery docs
        assert ".squidsquad/config.md" not in pats
        assert "README.md" not in pats
        # #9474 sanity check: QA also must NOT pick up SKILL.md —
        # the DM-extras additions don't bleed into other roles.
        assert "SKILL.md" not in pats

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
        mock_subproc.return_value = _mock_result()  # git commit succeeds
        mock_run_list.side_effect = [
            _mock_result(),  # git add
            _mock_result(),  # git checkout config.md revert (#7491)
        ]
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
        mock_subproc.return_value = _mock_result()  # commit
        mock_run_list.side_effect = [
            _mock_result(),  # git add
            _mock_result(),  # git checkout config.md revert (#7491)
        ]
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
        mock_run_list.side_effect = [
            _mock_result(returncode=0),  # rev-parse (branch exists)
            _mock_result(),  # git checkout
            _mock_result(),  # git add
            _mock_result(),  # git checkout config.md revert (#7491)
        ]
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
            _mock_result(),                      # git stash -q
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
    def test_stash_pop_on_success_applies_to_target(self, mock_run, mock_run_list):
        """On checkout success after stash, pop applies on target branch."""
        mock_run.side_effect = [
            _mock_result(stdout="main\n"),      # git branch --show-current
            _mock_result(),                      # git stash -q
            _mock_result(),                      # git stash pop -q
        ]
        mock_run_list.side_effect = [
            _mock_result(returncode=1, stderr="error"),  # direct checkout fails
            _mock_result(returncode=0),                   # stash+checkout succeeds
        ]

        result = git_ops._safe_checkout("feature-branch")
        assert result is True


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
        assert "config.md merge=ours" in content

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
