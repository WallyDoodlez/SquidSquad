"""Static analysis: Verify config.md has required fields and valid values."""

import re
import pytest

from conftest import SQUIDSQUAD_DIR


def _extract_field(text, field_name):
    """Extract a markdown field value like '- **Name**: value'."""
    match = re.search(rf'[-*]\s*\*\*{re.escape(field_name)}\*\*:\s*(.+)', text)
    return match.group(1).strip() if match else None


class TestConfigRequired:
    """Verify all required config fields are present and valid."""

    @pytest.fixture(autouse=True, scope="class")
    def _load(self, request):
        path = SQUIDSQUAD_DIR / "config.md"
        assert path.exists(), "config.md missing"
        request.cls.config = path.read_text(encoding="utf-8")

    def test_has_version(self):
        val = _extract_field(self.config, "SquidSquad Version")
        assert val, "Missing 'SquidSquad Version' field"
        assert re.match(r'\d+\.\d+\.\d+', val), f"Invalid version format: {val}"

    def test_has_tracker(self):
        val = _extract_field(self.config, "Tracker")
        assert val, "Missing 'Tracker' field"
        assert val in {"github-issues", "markdown"}, f"Unknown tracker type: {val}"

    def test_has_dev_agents(self):
        val = _extract_field(self.config, "Dev Agents")
        assert val, "Missing 'Dev Agents' field"

    def test_has_project_name(self):
        val = _extract_field(self.config, "Name")
        assert val, "Missing project 'Name' field"

    def test_has_iteration_interval(self):
        val = _extract_field(self.config, "Minutes")
        assert val, "Missing iteration interval 'Minutes' field"
        assert val.isdigit() and int(val) > 0, f"Invalid interval: {val}"

    def test_has_context_threshold(self):
        val = _extract_field(self.config, "Threshold")
        assert val, "Missing context pressure 'Threshold' field"
        assert val.isdigit(), f"Invalid threshold: {val}"

    def test_has_skill_tests(self):
        val = _extract_field(self.config, "skill Tests")
        assert val, "Missing 'skill Tests' field in config.md"

    def test_has_pr_flow(self):
        assert "## PR Flow" in self.config, "Missing '## PR Flow' section"
        # Extract Enabled within the PR Flow section
        pr_section = self.config.split("## PR Flow")[1].split("##")[0]
        val = _extract_field(pr_section, "Enabled")
        assert val is not None, "Missing 'Enabled' field in PR Flow section"

    def test_has_improvement_scanning(self):
        assert "## Improvement Scanning" in self.config, "Missing '## Improvement Scanning' section"
        scan_section = self.config.split("## Improvement Scanning")[1].split("##")[0]
        val = _extract_field(scan_section, "Enabled")
        assert val is not None, "Missing 'Enabled' field in Improvement Scanning section"
