"""Regression test for #13551 — worker branches routinely appended new test
classes to the same shared test file's tail (e.g. test_git_ops.py), and two
independent branches forked in quick succession off the same file each
appended after the same anchor point (commonly the last class in the
file). Neither branch has seen the other's insertion, so the merge reports
mergeable=CONFLICTING/DIRTY purely from insertion-position collision — not
from any real code conflict. Verifier catches it and rejects back to
in-progress, costing a full verify-reject-rebase-reverify round trip.

The fix documents the preventive convention: prefer a new dedicated test
file per issue over appending to a shared file's tail.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GIT_COMMIT_FILE = REPO_ROOT / "references" / "sub-skills" / "common" / "git-commit.md"


@pytest.fixture
def git_commit_text():
    assert GIT_COMMIT_FILE.exists(), f"git-commit.md missing: {GIT_COMMIT_FILE}"
    return GIT_COMMIT_FILE.read_text(encoding="utf-8")


class TestTestFilePlacementGuidance13551:
    def test_dedicated_file_preference_documented(self, git_commit_text):
        assert "dedicated" in git_commit_text.lower()
        assert "test_<issue-number>" in git_commit_text or "test_<issue" in git_commit_text

    def test_explains_the_conflict_mechanism(self, git_commit_text):
        idx = git_commit_text.index("#13551")
        section = git_commit_text[idx:idx + 1200]
        assert "conflicting" in section.lower() or "conflict" in section.lower()
        assert "anchor" in section.lower()

    def test_names_example_shared_files(self, git_commit_text):
        idx = git_commit_text.index("#13551")
        section = git_commit_text[idx:idx + 1200]
        assert "test_git_ops.py" in section
        assert "test_harness.py" in section

    def test_carve_out_for_tightly_scoped_extension_present(self, git_commit_text):
        idx = git_commit_text.index("#13551")
        section = git_commit_text[idx:idx + 1200]
        assert "tightly" in section.lower() or "existing coverage" in section.lower()
