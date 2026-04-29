"""Static analysis: Verify config.md has required fields and valid values."""

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config
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

    def test_has_auto_merge(self):
        assert "## Auto Merge" in self.config, "Missing '## Auto Merge' section"
        am_section = self.config.split("## Auto Merge")[1].split("##")[0]
        val = _extract_field(am_section, "Enabled")
        assert val is not None, "Missing 'Enabled' field in Auto Merge section"
        assert val.lower() in ("yes", "no"), f"Auto Merge Enabled must be yes/no, got: {val}"

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


# ---------------------------------------------------------------------------
# #4092 regression: set_field guards
# ---------------------------------------------------------------------------

class TestSetFieldGuards:
    """set_field must not silently no-op on empty sections or duplicate."""

    def test_empty_section_exits(self, tmp_path):
        """set_field exits with error when the target section is empty."""

        # Config with an empty section
        config_text = (
            "# Config\n\n"
            "## Auto Merge\n\n"
            "## Git Protocol\n\n"
            "- **Always**: yes\n"
        )
        config_file = tmp_path / "config.md"
        config_file.write_text(config_text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", config_file):
            with pytest.raises(SystemExit):
                config.set_field("auto-merge", "no")

    def test_replace_limited_to_first_occurrence(self, tmp_path):
        """set_field replaces only the first matching section (count=1)."""

        config_text = (
            "# Config\n\n"
            "- **SquidSquad Version**: 0.28.0\n\n"
            "## Agents\n\n"
            "- **Dev Agents**: skill\n\n"
            "## Iteration Interval\n\n"
            "- **Minutes**: 30\n"
        )
        config_file = tmp_path / "config.md"
        config_file.write_text(config_text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", config_file):
            config.set_field("version", "0.29.0")
        result = config_file.read_text(encoding="utf-8")
        assert result.count("0.29.0") == 1
        assert result.count("0.28.0") == 0
