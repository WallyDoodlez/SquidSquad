"""Regression test for #13552 — verification.md Step 5a's `gh pr review
[PR] --approve` is undocumented tribal knowledge that it reliably fails
with GraphQL "Can not approve your own pull request" in single-GH-identity
installs (every agent clone shares one gh auth). A fresh verifier hitting
this for the first time would see a hard failure on a documented mandatory
step and might treat it as broken tooling instead of an expected,
harmless, environment-specific no-op.

The fix adds a note directly after the approve command explaining the
failure is expected/non-blocking and that gh pr ready + harness /merge
proceed regardless.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFICATION_FILE = (
    REPO_ROOT / "references" / "sub-skills" / "roles" / "verifier" / "verification.md"
)
# #13565: the approve command + its self-approve-failure note moved to this
# cold-path file, reached via a pointer in verification.md's Step 5.
VERIFICATION_SHIP_FLOW = (
    REPO_ROOT / "references" / "sub-skills" / "roles" / "verifier" / "verification-ship-flow.md"
)


@pytest.fixture
def verification_text():
    assert VERIFICATION_FILE.exists(), f"verification.md missing: {VERIFICATION_FILE}"
    assert VERIFICATION_SHIP_FLOW.exists(), f"verification-ship-flow.md missing: {VERIFICATION_SHIP_FLOW}"
    return (VERIFICATION_FILE.read_text(encoding="utf-8")
            + "\n" + VERIFICATION_SHIP_FLOW.read_text(encoding="utf-8"))


class TestSelfApproveFailureDocumented:
    def test_note_present_near_approve_command(self, verification_text):
        idx = verification_text.index("gh pr review")
        section = verification_text[idx:idx + 800]
        assert "Can not approve your own pull request" in section

    def test_note_marks_failure_expected_and_nonblocking(self, verification_text):
        idx = verification_text.index("Can not approve your own pull request")
        section = verification_text[idx:idx + 400]
        assert "expected" in section.lower()
        assert "non-blocking" in section.lower() or "not blocking" in section.lower()

    def test_note_tells_verifier_to_proceed_regardless(self, verification_text):
        idx = verification_text.index("Can not approve your own pull request")
        section = verification_text[idx:idx + 400]
        assert "proceed" in section.lower()

    def test_note_references_issue_13552(self, verification_text):
        idx = verification_text.index("Can not approve your own pull request")
        section = verification_text[max(0, idx - 200):idx + 400]
        assert "13552" in section

    def test_approve_command_itself_unchanged(self, verification_text):
        # The fix documents around the command; it must not alter the
        # command itself (still the correct gh invocation to attempt).
        assert 'gh pr review [PR_NUMBER] --approve --body "Verifier verified' in verification_text
