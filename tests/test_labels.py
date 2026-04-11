"""Static analysis: Verify label taxonomy consistency.

Checks that labels defined in CLAUDE.md match what exists on GitHub
and that label references in code use valid label names.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT, SQUIDSQUAD_DIR

# Labels defined in the tracker-protocol label taxonomy
EXPECTED_TYPE_LABELS = {"type:bug", "type:feature"}
EXPECTED_PRIORITY_LABELS = {"priority:high", "priority:medium", "priority:low"}
EXPECTED_STATUS_LABELS = {
    "status:open", "status:pending", "status:planning", "status:planned",
    "status:approved", "status:in-progress", "status:pending-test",
    "status:pending-ship", "status:shipped",
    # #328 Phase E additive labels (Q-new4/Q7/Q-new11). `status:pending`
    # is NOT yet removed — Phase I will rename it to `pending-human-approval`
    # in a bounded migration on this repo.
    "status:pending-human-approval",
    "status:pending-human-review",
    "status:pending-human-setup",
}
EXPECTED_ROLE_LABELS = {
    "role:skill", "role:fe", "role:be", "role:pm", "role:qa",
    "role:designer", "role:dm",
}
EXPECTED_DESIGN_LABELS = {"design:needed", "design:in-progress", "design:complete"}
EXPECTED_SEVERITY_LABELS = {"severity:high", "severity:medium", "severity:low"}
EXPECTED_SPECIAL_LABELS = {"squidsquad", "improvement-scan"}

ALL_KNOWN_LABELS = (
    EXPECTED_TYPE_LABELS | EXPECTED_PRIORITY_LABELS | EXPECTED_STATUS_LABELS
    | EXPECTED_ROLE_LABELS | EXPECTED_DESIGN_LABELS | EXPECTED_SEVERITY_LABELS
    | EXPECTED_SPECIAL_LABELS | {"squidsquad-test"}  # test harness label
)


def _get_repo_labels():
    """Fetch all labels from the GitHub repo."""
    result = subprocess.run(
        "gh label list --json name --limit 200",
        shell=True, capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        pytest.skip("Cannot reach GitHub API")
    return {item["name"] for item in json.loads(result.stdout)}


class TestLabelTaxonomy:
    """Verify all expected labels exist on GitHub."""

    @pytest.fixture(autouse=True, scope="class")
    def _repo_labels(self, request):
        request.cls.repo_labels = _get_repo_labels()

    def test_type_labels_exist(self):
        missing = EXPECTED_TYPE_LABELS - self.repo_labels
        assert not missing, f"Missing type labels on repo: {missing}"

    def test_priority_labels_exist(self):
        missing = EXPECTED_PRIORITY_LABELS - self.repo_labels
        assert not missing, f"Missing priority labels: {missing}"

    def test_status_labels_exist(self):
        missing = EXPECTED_STATUS_LABELS - self.repo_labels
        assert not missing, f"Missing status labels: {missing}"

    def test_role_labels_exist(self):
        # Only check roles that are actually configured
        config = (SQUIDSQUAD_DIR / "config.md").read_text(encoding="utf-8")
        required = {"role:pm"}  # PM always present
        if "skill" in config:
            required.add("role:skill")
        missing = required - self.repo_labels
        assert not missing, f"Missing role labels for configured agents: {missing}"

    def test_severity_labels_exist(self):
        missing = EXPECTED_SEVERITY_LABELS - self.repo_labels
        assert not missing, f"Missing severity labels: {missing}"

    def test_special_labels_exist(self):
        missing = EXPECTED_SPECIAL_LABELS - self.repo_labels
        assert not missing, f"Missing special labels: {missing}"


class TestLabelReferences:
    """Verify label strings used in CLAUDE.md are from the known taxonomy."""

    def test_claude_md_label_references(self, skill_claude_md):
        # Extract label strings from gh commands in CLAUDE.md
        label_refs = set()
        for match in re.finditer(r'--label\s+"([^"]+)"', skill_claude_md):
            for label in match.group(1).split(","):
                label = label.strip()
                # Skip template placeholders like [level], [target-role], [OTHER_ROLE]
                if "[" in label:
                    continue
                label_refs.add(label)

        unknown = label_refs - ALL_KNOWN_LABELS
        assert not unknown, f"CLAUDE.md references unknown labels: {unknown}"
