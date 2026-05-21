"""Tests for references/scripts/config.py — get/set operations, parsing, schema detection."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config

SAMPLE_CONFIG = """# SquidSquad Config

- **SquidSquad Version**: 0.17.0
- **Tracker**: github-issues
- **Architecture Version**: 1

## Agents

- **Dev Agents**: qa, skill
- **PM**: always present
- **QA**: always present
- **DM**: present

## Aliases

- **skill**: skill
- **pm**: pm
- **dm**: dm
- **qa**: qa
- **designer**: designer

## Project

- **Name**: TestProject
- **Repo**: github.com/test/repo
- **Intent Description**: (not set)

## Test Commands

- **skill Tests**: python tests/run_tests.py
- **E2E Tests**: (none)

## Git Branches

- **Working Branch**: main
- **State Branch**: squid-squad
- **Branch Pattern**: squidsquad/task/{number}

## Iteration Interval

- **Minutes**: 30

## Context Pressure

- **Threshold**: 70

## Auto Merge

- **Enabled**: yes

## PR Flow

- **Enabled**: no

## Improvement Scanning

- **Enabled**: yes

## Vault Optimize

- **Enabled**: yes
- **Threshold**: 20

## Vault Remember

- **Enabled**: yes
- **Writes Per Cycle**: 2
- **BRIEFING Token Budget**: 2000
- **Confidence Decay Days**: 60

## Cycle Runner

- **Enabled**: yes

## Agent Compose

- **Enabled**: no

## Diagnostics

- **Enabled**: yes
- **Upstream Reporting**: ask

## Model Routing

- **Default Model**: claude
- **Research Model**: deepseek-v4-pro
- **Discussion Prep Model**: claude
- **Test Plan Model**: claude
- **QA Execution Model**: claude
- **Comprehension Model**: claude
- **Improvement Scan Model**: claude
- **Fallback Model**: claude
- **API Timeout Seconds**: 120

## Forge Backend

- **Provider**: github
- **Endpoint**: https://api.github.com
- **Owner**: test-owner
- **Repo**: test-repo

## Mandatory Human Approval

- **Enabled**: yes

## Auto Versioning

- **Ship Threshold**: 10
- **Shipped Since Last Bump**: 5

## Harness

- **Enabled**: yes
- **Port**: 7373
"""


class TestParseSections:
    def test_parses_sections(self):
        sections = config._parse_sections(SAMPLE_CONFIG)
        assert "Agents" in sections
        assert "Project" in sections
        assert "PR Flow" in sections

    def test_content_before_first_heading(self):
        sections = config._parse_sections(SAMPLE_CONFIG)
        assert "SquidSquad Version" in sections[""]

    def test_empty_text(self):
        sections = config._parse_sections("")
        assert sections == {"": ""}


class TestParseFieldInText:
    def test_finds_field(self):
        text = "- **Name**: TestProject\n- **Repo**: github.com/test\n"
        assert config._parse_field_in_text(text, "Name") == "TestProject"

    def test_missing_field(self):
        text = "- **Name**: TestProject\n"
        assert config._parse_field_in_text(text, "Missing") is None

    def test_field_with_special_chars(self):
        text = "- **skill Tests**: python tests/run_tests.py\n"
        assert config._parse_field_in_text(text, "skill Tests") == "python tests/run_tests.py"


class TestParseField:
    def test_scoped_to_section(self):
        val = config._parse_field(SAMPLE_CONFIG, "Project", "Name")
        assert val == "TestProject"

    def test_wrong_section(self):
        val = config._parse_field(SAMPLE_CONFIG, "Agents", "Name")
        assert val is None

    def test_no_section_searches_all(self):
        val = config._parse_field(SAMPLE_CONFIG, None, "SquidSquad Version")
        assert val == "0.17.0"


class TestGetField:
    def _setup_config(self, tmp_path):
        cfg = tmp_path / "config.md"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")
        return cfg

    def test_get_by_short_name(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            val = config.get_field("interval")
        assert val == "30"

    def test_get_project_name(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            val = config.get_field("project-name")
        assert val == "TestProject"

    def test_get_pr_flow(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            val = config.get_field("pr-flow")
        assert val == "no"

    def test_get_shipped_since_bump(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            val = config.get_field("shipped-since-bump")
        assert val == "5"

    def test_missing_field_exits(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            with pytest.raises(SystemExit):
                config.get_field("nonexistent-field-xyz")

    def test_missing_config_exits(self, tmp_path):
        with patch.object(config, "CONFIG_PATH", tmp_path / "missing.md"):
            with pytest.raises(SystemExit):
                config.get_field("version")


class TestSetField:
    def _setup_config(self, tmp_path):
        cfg = tmp_path / "config.md"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")
        return cfg

    def test_set_interval(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            config.set_field("interval", "45")
            val = config.get_field("interval")
        assert val == "45"

    def test_set_shipped_since_bump(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            config.set_field("shipped-since-bump", "10")
            val = config.get_field("shipped-since-bump")
        assert val == "10"

    def test_set_preserves_other_fields(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            config.set_field("interval", "99")
            # Other fields unchanged
            assert config.get_field("project-name") == "TestProject"
            assert config.get_field("pr-flow") == "no"

    def test_set_missing_field_exits(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            with pytest.raises(SystemExit):
                config.set_field("nonexistent-field-xyz", "value")


class TestGetAlias:
    def _setup_config(self, tmp_path):
        cfg = tmp_path / "config.md"
        cfg.write_text(SAMPLE_CONFIG, encoding="utf-8")
        return cfg

    def test_returns_alias(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            assert config.get_alias("skill") == "skill"

    def test_falls_back_to_role_name(self, tmp_path):
        cfg = self._setup_config(tmp_path)
        with patch.object(config, "CONFIG_PATH", cfg):
            assert config.get_alias("unknown_role") == "unknown_role"


class TestDetectSchemaVersion:
    def test_v1(self):
        assert config.detect_schema_version(SAMPLE_CONFIG) == 1

    def test_v2(self):
        text = SAMPLE_CONFIG.replace("Architecture Version**: 1", "Architecture Version**: 2")
        assert config.detect_schema_version(text) == 2

    def test_missing_field_defaults_v1(self):
        text = "# Config\n\n- **Name**: Test\n"
        assert config.detect_schema_version(text) == 1

    def test_malformed_value_defaults_v1(self):
        text = "- **Architecture Version**: abc\n"
        assert config.detect_schema_version(text) == 1


class TestFieldMapCoverage:
    """#5366: All FIELD_MAP entries must resolve against SAMPLE_CONFIG."""

    @pytest.mark.parametrize("key", sorted(config.FIELD_MAP.keys()))
    def test_field_map_entry_resolves(self, key):
        """Every FIELD_MAP key must find its section+field in SAMPLE_CONFIG."""
        section, field = config.FIELD_MAP[key]
        value = config._parse_field(SAMPLE_CONFIG, section, field)
        assert value is not None, (
            f"FIELD_MAP['{key}'] → section='{section}', field='{field}' "
            f"not found in SAMPLE_CONFIG. Update the fixture."
        )


# ---------------------------------------------------------------------------
# #7285: sync_agents regression test
# ---------------------------------------------------------------------------


class TestSyncAgents:
    """Regression test for sync_agents() — must not raise NameError (#7285)."""

    def test_sync_agents_no_name_error(self, tmp_path):
        """sync_agents() must not reference undefined variables."""
        sqdir = tmp_path / ".squidsquad"
        # Create skill + pm + dm + qa with CLAUDE.md
        for role in ("skill", "pm", "dm", "qa"):
            (sqdir / role).mkdir(parents=True)
            (sqdir / role / "CLAUDE.md").write_text("# test", encoding="utf-8")
        # Create config.md
        (sqdir / "config.md").write_text(SAMPLE_CONFIG, encoding="utf-8")

        with patch.object(config, "REPO_ROOT", tmp_path), \
             patch.object(config, "CONFIG_PATH", sqdir / "config.md"):
            roles = config.sync_agents()

        assert "skill" in roles
        assert "pm" in roles
        assert "dm" in roles
        assert "qa" in roles

    def test_sync_agents_without_dm(self, tmp_path):
        """sync_agents() handles missing DM gracefully."""
        sqdir = tmp_path / ".squidsquad"
        for role in ("skill", "pm"):
            (sqdir / role).mkdir(parents=True)
            (sqdir / role / "CLAUDE.md").write_text("# test", encoding="utf-8")
        (sqdir / "config.md").write_text(SAMPLE_CONFIG, encoding="utf-8")

        with patch.object(config, "REPO_ROOT", tmp_path), \
             patch.object(config, "CONFIG_PATH", sqdir / "config.md"):
            roles = config.sync_agents()

        assert "skill" in roles
        assert "pm" in roles
        assert "dm" not in roles
