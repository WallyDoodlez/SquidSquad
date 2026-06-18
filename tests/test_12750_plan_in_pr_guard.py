"""Tests for the plan-in-PR guard exemption (#12750).

The #11511 pre-commit state guard (``git_ops.guard_staged_state``) strips every
staged ``.squidsquad/`` / ``.claude/`` file from a feature-branch commit so
transient state never pollutes a PR. Plan-in-PR (#12750) requires ONE narrow
carve-out: a task's plan body (``.squidsquad/<role>/planning/<n>-body.md``) is a
versioned deliverable committed as commit 1 of the task branch — it must ride the
branch into the PR rather than being stripped to main. These tests lock both the
classifier (``_is_plan_body``) and the guard's use of it.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


class TestIsPlanBodyClassifier:
    """`_is_plan_body` matches ONLY ``.squidsquad/<role>/planning/<n>-body.md``."""

    @pytest.mark.parametrize("path", [
        ".squidsquad/pm/planning/12750-body.md",
        ".squidsquad/skill/planning/9-body.md",
        ".squidsquad/web/planning/100000-body.md",
    ])
    def test_plan_bodies_match(self, path):
        assert git_ops._is_plan_body(path) is True

    @pytest.mark.parametrize("path", [
        # transient state siblings that MUST stay stripped (#11511)
        ".squidsquad/skill/working-state.md",
        ".squidsquad/skill/iterations/iter-5.md",
        ".squidsquad/vault/BRIEFING.md",
        # other planning artifacts are not the plan body
        ".squidsquad/pm/planning/FEAT-PM-001-RESEARCH.md",
        ".squidsquad/pm/planning/CONTEXT-12750.md",
        ".squidsquad/pm/planning/12750-liveness-map.md",
        # non-numeric stem
        ".squidsquad/pm/planning/draft-body.md",
        # wrong depth (no role segment / nested)
        ".squidsquad/planning/12-body.md",
        ".squidsquad/pm/planning/sub/12-body.md",
        # not under .squidsquad
        ".claude/settings.json",
        # ordinary code file
        "references/scripts/git_ops.py",
        "tests/test_12750_plan_in_pr_guard.py",
    ])
    def test_non_plan_bodies_do_not_match(self, path):
        assert git_ops._is_plan_body(path) is False

    def test_plan_body_is_still_a_state_file(self):
        """The plan body is still under .squidsquad/ — the carve-out lives in the
        guard, not in _is_state_file (which other consumers rely on)."""
        assert git_ops._is_state_file(".squidsquad/pm/planning/12750-body.md") is True


class TestGuardExemptsPlanBody:
    """`guard_staged_state` strips state on a feature branch but keeps the plan body."""

    def _run_guard(self, staged_paths):
        """Drive guard_staged_state on feature branch 'squidsquad/task/12750'
        with the given staged paths; return (unstaged_list, reset_calls)."""
        reset_calls = []

        def fake_run(cmd, check=True):
            # only call: `git branch --show-current`
            return _mock_result(stdout="squidsquad/task/12750\n")

        def fake_run_list(cmd, check=True):
            if cmd[:3] == ["git", "diff", "--cached"]:
                return _mock_result(stdout="\n".join(staged_paths) + "\n")
            if cmd[:2] == ["git", "reset"]:
                reset_calls.append(cmd[-1])  # the path arg
                return _mock_result()
            return _mock_result()

        with patch.object(git_ops, "_get_working_branch", return_value="main"), \
                patch.object(git_ops, "_run", side_effect=fake_run), \
                patch.object(git_ops, "_run_list", side_effect=fake_run_list):
            unstaged = git_ops.guard_staged_state()
        return unstaged, reset_calls

    def test_plan_body_survives_state_siblings_stripped(self):
        staged = [
            ".squidsquad/pm/planning/12750-body.md",   # keep
            ".squidsquad/skill/working-state.md",        # strip
            ".claude/settings.json",                     # strip
            "references/scripts/git_ops.py",             # code — never touched
        ]
        unstaged, reset_calls = self._run_guard(staged)
        assert ".squidsquad/pm/planning/12750-body.md" not in unstaged
        assert ".squidsquad/skill/working-state.md" in unstaged
        assert ".claude/settings.json" in unstaged
        assert "references/scripts/git_ops.py" not in unstaged
        # the plan body must NOT have been reset out of the index
        assert ".squidsquad/pm/planning/12750-body.md" not in reset_calls

    def test_only_plan_body_staged_is_a_noop(self):
        """A commit that stages only the plan body strips nothing (the whole
        point — PM's commit-1 of the plan goes through cleanly)."""
        unstaged, reset_calls = self._run_guard(
            [".squidsquad/pm/planning/12750-body.md"]
        )
        assert unstaged == []
        assert reset_calls == []

    def test_on_working_branch_is_noop(self):
        """Guard is a no-op on the working branch regardless of staged state."""
        def fake_run(cmd, check=True):
            return _mock_result(stdout="main\n")

        with patch.object(git_ops, "_get_working_branch", return_value="main"), \
                patch.object(git_ops, "_run", side_effect=fake_run), \
                patch.object(git_ops, "_run_list") as m_list:
            unstaged = git_ops.guard_staged_state()
        assert unstaged == []
        m_list.assert_not_called()
