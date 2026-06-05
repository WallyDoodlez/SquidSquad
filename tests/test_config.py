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


# ---------------------------------------------------------------------------
# get_field — public API (#4879)
# ---------------------------------------------------------------------------

class TestGetField:
    """Test config.get_field() directly instead of duplicate regex."""

    SAMPLE_CONFIG = (
        "# Config\n\n"
        "- **SquidSquad Version**: 0.31.0\n\n"
        "## Project\n\n"
        "- **Name**: TestProject\n"
        "- **Repo**: test/repo\n\n"
        "## Iteration Interval\n\n"
        "- **Minutes**: 30\n\n"
        "## PR Flow\n\n"
        "- **Enabled**: yes\n\n"
        "## Improvement Scanning\n\n"
        "- **Enabled**: no\n\n"
        "## Aliases\n\n"
        "- **skill**: SkillBot\n"
        "- **pm**: PMBot\n"
    )

    def test_get_known_field(self, tmp_path):
        """get_field returns correct value for a FIELD_MAP short name."""
        f = tmp_path / "config.md"
        f.write_text(self.SAMPLE_CONFIG, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_field("version") == "0.31.0"

    def test_get_section_scoped_field(self, tmp_path):
        """get_field resolves section-scoped fields correctly."""
        f = tmp_path / "config.md"
        f.write_text(self.SAMPLE_CONFIG, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_field("project-name") == "TestProject"
            assert config.get_field("interval") == "30"

    def test_get_disambiguates_enabled_fields(self, tmp_path):
        """get_field returns the correct 'Enabled' for the right section."""
        f = tmp_path / "config.md"
        f.write_text(self.SAMPLE_CONFIG, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_field("pr-flow") == "yes"
            assert config.get_field("improvement-scanning") == "no"

    def test_get_unknown_field_exits(self, tmp_path):
        """get_field exits with code 1 when field not found."""
        f = tmp_path / "config.md"
        f.write_text(self.SAMPLE_CONFIG, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            with pytest.raises(SystemExit):
                config.get_field("nonexistent-field")

    def test_get_raw_field_name(self, tmp_path):
        """get_field falls back to raw field name search when not in FIELD_MAP."""
        f = tmp_path / "config.md"
        f.write_text(self.SAMPLE_CONFIG, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_field("Repo") == "test/repo"


# ---------------------------------------------------------------------------
# Improvement Scan Cool-Down field default (#11091)
# ---------------------------------------------------------------------------

class TestImprovementScanCoolDownDefault:
    """#11091 — `improvement-scan-cool-down` falls back to '30' when absent."""

    def test_default_when_field_absent(self, tmp_path):
        # Section exists with only Enabled; cool-down field omitted (pre-#11091 install)
        text = (
            "## Improvement Scanning\n\n"
            "- **Enabled**: yes\n"
        )
        f = tmp_path / "config.md"
        f.write_text(text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_field("improvement-scan-cool-down") == "30"

    def test_default_when_section_absent(self, tmp_path):
        # Entire section missing (truly minimal install)
        f = tmp_path / "config.md"
        f.write_text("# Config\n\n- **SquidSquad Version**: 0.0.0\n", encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_field("improvement-scan-cool-down") == "30"

    def test_explicit_value_overrides_default(self, tmp_path):
        text = (
            "## Improvement Scanning\n\n"
            "- **Enabled**: yes\n"
            "- **Improvement Scan Cool-Down**: 45\n"
        )
        f = tmp_path / "config.md"
        f.write_text(text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_field("improvement-scan-cool-down") == "45"

    def test_field_in_defaults_registry(self):
        # Lock the contract — _FIELD_DEFAULTS must carry the cool-down key
        assert config._FIELD_DEFAULTS["improvement-scan-cool-down"] == "30"


# ---------------------------------------------------------------------------
# set_field — happy path (#4879)
# ---------------------------------------------------------------------------

class TestSetFieldHappyPath:
    """Test set_field actually writes the new value correctly."""

    def test_set_sectionless_field(self, tmp_path):
        """set_field updates a top-level field."""
        config_text = (
            "# Config\n\n"
            "- **SquidSquad Version**: 0.28.0\n\n"
            "## Agents\n\n"
            "- **Dev Agents**: skill\n"
        )
        f = tmp_path / "config.md"
        f.write_text(config_text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            result = config.set_field("version", "0.29.0")
        assert result == "0.29.0"
        content = f.read_text(encoding="utf-8")
        assert "0.29.0" in content
        assert "0.28.0" not in content

    def test_set_section_scoped_field(self, tmp_path):
        """set_field updates a field within the correct section."""
        config_text = (
            "# Config\n\n"
            "## Iteration Interval\n\n"
            "- **Minutes**: 30\n\n"
            "## PR Flow\n\n"
            "- **Enabled**: yes\n"
        )
        f = tmp_path / "config.md"
        f.write_text(config_text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            config.set_field("interval", "45")
        content = f.read_text(encoding="utf-8")
        assert "- **Minutes**: 45" in content
        # PR Flow Enabled should be unchanged
        assert "- **Enabled**: yes" in content

    def test_set_field_not_found_exits(self, tmp_path):
        """set_field exits when the field doesn't exist in config."""
        f = tmp_path / "config.md"
        f.write_text("# Config\n\n- **Other**: value\n", encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            with pytest.raises(SystemExit):
                config.set_field("version", "1.0.0")


# ---------------------------------------------------------------------------
# get_alias (#4879)
# ---------------------------------------------------------------------------

class TestGetAlias:
    """Test config.get_alias() with and without alias values."""

    def test_alias_present(self, tmp_path):
        """get_alias returns the configured alias."""
        config_text = (
            "# Config\n\n"
            "## Aliases\n\n"
            "- **skill**: SkillBot\n"
            "- **pm**: PMBot\n"
        )
        f = tmp_path / "config.md"
        f.write_text(config_text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_alias("skill") == "SkillBot"
            assert config.get_alias("pm") == "PMBot"

    def test_alias_missing_falls_back(self, tmp_path):
        """get_alias returns bare role name when no alias configured."""
        config_text = "# Config\n\n## Aliases\n\n"
        f = tmp_path / "config.md"
        f.write_text(config_text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_alias("skill") == "skill"

    def test_alias_unknown_role(self, tmp_path):
        """get_alias for a role not in FIELD_MAP returns bare role name."""
        config_text = "# Config\n\n"
        f = tmp_path / "config.md"
        f.write_text(config_text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            assert config.get_alias("unknown-role") == "unknown-role"


# ---------------------------------------------------------------------------
# detect_schema_version (#4879)
# ---------------------------------------------------------------------------

class TestDetectSchemaVersion:
    """Test config.detect_schema_version()."""

    def test_v1_explicit(self):
        text = "- **Architecture Version**: 1\n"
        assert config.detect_schema_version(text) == 1

    def test_v2_explicit(self):
        text = "- **Architecture Version**: 2\n"
        assert config.detect_schema_version(text) == 2

    def test_missing_field_defaults_v1(self):
        text = "# Config\n\n- **Version**: 0.31.0\n"
        assert config.detect_schema_version(text) == 1

    def test_non_integer_defaults_v1(self):
        text = "- **Architecture Version**: beta\n"
        assert config.detect_schema_version(text) == 1

    def test_v3_returns_v2(self):
        """Values >= 2 are treated as v2."""
        text = "- **Architecture Version**: 3\n"
        assert config.detect_schema_version(text) == 2


# ---------------------------------------------------------------------------
# _parse_sections (#4879)
# ---------------------------------------------------------------------------

class TestParseSections:
    """Test internal section parsing for correctness."""

    def test_splits_sections(self):
        text = (
            "preamble\n"
            "## Section A\n"
            "content a\n"
            "## Section B\n"
            "content b\n"
        )
        sections = config._parse_sections(text)
        assert "Section A" in sections
        assert "Section B" in sections
        assert "content a" in sections["Section A"]
        assert "content b" in sections["Section B"]

    def test_preamble_in_empty_key(self):
        text = "top level\n## First\ndata\n"
        sections = config._parse_sections(text)
        assert "top level" in sections[""]

    def test_heading_whitespace_stripped(self):
        text = "## Padded Section  \ndata\n"
        sections = config._parse_sections(text)
        assert "Padded Section" in sections


# ---------------------------------------------------------------------------
# dump_all (#4879)
# ---------------------------------------------------------------------------

class TestDumpAll:
    """Test config.dump_all() returns parsed fields."""

    def test_returns_dict(self, tmp_path):
        config_text = (
            "# Config\n\n"
            "- **SquidSquad Version**: 0.31.0\n\n"
            "## Iteration Interval\n\n"
            "- **Minutes**: 30\n"
        )
        f = tmp_path / "config.md"
        f.write_text(config_text, encoding="utf-8")
        with patch.object(config, "CONFIG_PATH", f):
            result = config.dump_all()
        assert isinstance(result, dict)
        assert result["version"] == "0.31.0"
        assert result["interval"] == "30"
