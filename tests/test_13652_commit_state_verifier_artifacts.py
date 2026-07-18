"""Regression test for #13652 — commit_state() only staged files under
.squidsquad/, but verifier's own comprehension-spec artifacts
(tests/comprehension/<N>_spec.json + the shared .staleness-baseline.json)
live outside .squidsquad/. Neither commit_state() (main-only, .squidsquad/
prefix check) nor commit_code() (targets a feature branch -- the wrong
destination for a main-committed verification record) fit, forcing
verifier to fall back to the unsafe add-everything commit_push().

The fix extends commit_state()'s staging predicate to recognize
tests/comprehension/*.json as a qa/verifier-artifact class, scoped to the
qa role only (mirrors _role_owned_patterns' existing qa-only
tests/comprehension/ allowance for the sibling commit_role_scoped path).
"""

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


class TestIsVerifierComprehensionArtifact:
    def test_spec_file_matches(self):
        assert git_ops._is_verifier_comprehension_artifact(
            "tests/comprehension/13551_spec.json"
        )

    def test_staleness_baseline_matches(self):
        assert git_ops._is_verifier_comprehension_artifact(
            "tests/comprehension/.staleness-baseline.json"
        )

    def test_non_json_fixture_does_not_match(self):
        """8697_fixtures markdown snapshots are not verifier-authored specs."""
        assert not git_ops._is_verifier_comprehension_artifact(
            "tests/comprehension/8697_fixtures/skill_events_CLAUDE.md"
        )

    def test_unrelated_test_file_does_not_match(self):
        assert not git_ops._is_verifier_comprehension_artifact(
            "tests/test_git_ops.py"
        )

    def test_squidsquad_path_does_not_match(self):
        assert not git_ops._is_verifier_comprehension_artifact(
            ".squidsquad/qa/planning/QA-RESULTS-13551.md"
        )


class TestCommitStateVerifierArtifacts13652:
    @patch("git_ops._git_push")
    @patch("git_ops._run")
    @patch("git_ops._run_list")
    @patch("subprocess.run")
    def test_qa_role_stages_comprehension_spec(
        self, mock_subproc, mock_run_list, mock_run, mock_git_push
    ):
        mock_run.side_effect = [
            _mk(0, " M tests/comprehension/13551_spec.json\n"
                   " M .squidsquad/qa/planning/QA-RESULTS-13551.md\n"),
            _mk(0, "main\n"),
        ]
        mock_run_list.return_value = _mk(0)
        mock_git_push.return_value = _mk(0)
        mock_subproc.return_value = _mk(0, "1 file changed")

        result = git_ops.commit_state("qa", "record #13551 CQ spec")
        assert result is True

        add_calls = [c.args[0] for c in mock_run_list.call_args_list
                     if c.args[0][0:2] == ["git", "add"]]
        staged = {c[2] for c in add_calls}
        assert "tests/comprehension/13551_spec.json" in staged
        assert ".squidsquad/qa/planning/QA-RESULTS-13551.md" in staged

    @patch("git_ops._git_push")
    @patch("git_ops._run")
    @patch("git_ops._run_list")
    @patch("subprocess.run")
    def test_qa_role_stages_staleness_baseline(
        self, mock_subproc, mock_run_list, mock_run, mock_git_push
    ):
        mock_run.side_effect = [
            _mk(0, " M tests/comprehension/.staleness-baseline.json\n"),
            _mk(0, "main\n"),
        ]
        mock_run_list.return_value = _mk(0)
        mock_git_push.return_value = _mk(0)
        mock_subproc.return_value = _mk(0, "1 file changed")

        result = git_ops.commit_state("qa", "refresh baseline")
        assert result is True

    @patch("git_ops._run")
    def test_skill_role_does_not_get_the_qa_allowance(self, mock_run):
        """Scoped to qa only -- a skill-authored comprehension edit (which
        already has a fitting path via commit_code on a feature branch)
        must not silently land on main through commit_state."""
        mock_run.return_value = _mk(0, " M tests/comprehension/13551_spec.json\n")
        result = git_ops.commit_state("skill", "should not stage")
        assert result is False

    @patch("git_ops._run")
    def test_qa_role_still_ignores_unrelated_test_files(self, mock_run):
        mock_run.return_value = _mk(0, " M tests/test_git_ops.py\n")
        result = git_ops.commit_state("qa", "should not stage")
        assert result is False
