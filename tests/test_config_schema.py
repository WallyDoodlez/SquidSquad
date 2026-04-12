"""Unit tests for config.py schema-aware agent parsing (#328 Phase H).

Phase H teaches config.py two things:
  1. To detect whether a config.md is legacy (v1) or the new Q-new17
     schema (v2) via the top-level `Architecture Version` field.
  2. To parse the `## Agents` section for both schemas, returning a
     single canonical shape callers can use regardless of which format
     the file was written in.

These tests exercise both parsers in isolation — no disk writes, no
real `.squidsquad/config.md` read. Each test passes a canned text
blob through `config._parse_agents_v1/v2` or `config.get_agents`.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import config  # noqa: E402


# ---------------------------------------------------------------------------
# Canned fixtures
# ---------------------------------------------------------------------------


V1_MINIMAL = """\
# SquidSquad Config

- **SquidSquad Version**: 0.15.0
- **Tracker**: github-issues
- **Architecture Version**: 1

## Agents

- **Dev Agents**: skill
- **PM/QA**: always present
- **DM**: present

## Aliases

- **skill**: skill
- **pm**: pm
- **dm**: dm
- **qa**: qa

## Test Commands

- **skill Tests**: python tests/run_tests.py
- **E2E Tests**: (none)
"""


V1_NO_DM = """\
# SquidSquad Config

- **Architecture Version**: 1

## Agents

- **Dev Agents**: be, fe
- **PM/QA**: always present

## Aliases

- **be**: backend
- **fe**: frontend
- **pm**: peggy

## Test Commands

- **be Tests**: pytest tests/be
- **fe Tests**: npm test
"""


V1_NO_DEV_ROLES = """\
# SquidSquad Config

- **Architecture Version**: 1

## Agents

- **PM/QA**: always present
- **DM**: present
"""


V1_NO_ARCH_VERSION = """\
# SquidSquad Config

## Agents

- **Dev Agents**: skill
- **PM/QA**: always present
"""


V2_FULL = """\
# SquidSquad Config

- **SquidSquad Version**: 0.16.0
- **Tracker**: github-issues
- **Architecture Version**: 2

## Project

- **Name**: demo
- **Repo**: github.com/x/y

## Preset

- **Id**: software-dev

## Agents

- **pm**: peggy
  - role: pm
- **designer**: designer
  - role: designer
  - iteration_mode: hitl
  - setup:
    - install_optional: yes
- **be**: be
  - role: dev
  - variant: be
  - stack: "FastAPI + Python 3.11 + pytest"
  - test_command: "pytest tests/be"
- **fe**: fe
  - role: dev
  - variant: fe
  - stack: "Next.js + TypeScript + jest"
  - test_command: "npm test"
- **qa**: qa
  - role: qa
- **dm**: dm
  - role: dm

## Tools

- **designer.tool**: (unset — PM will configure on first use)
- **dm.tool**: local_delivery

## Loop

- **Interval Minutes**: 10
- **Context Threshold**: 70

## Flags

- **Improvement Scan**: yes
- **Pr Flow**: no
"""


V2_DESIGN_PRESET = """\
# SquidSquad Config

- **Architecture Version**: 2

## Agents

- **pm**: peggy
  - role: pm
- **designer**: designer
  - role: designer
  - iteration_mode: hitl
- **dm**: dm
  - role: dm
"""


# ---------------------------------------------------------------------------
# Schema detection
# ---------------------------------------------------------------------------


class TestDetectSchemaVersion:
    def test_explicit_v1(self):
        assert config.detect_schema_version(V1_MINIMAL) == 1

    def test_explicit_v2(self):
        assert config.detect_schema_version(V2_FULL) == 2

    def test_missing_field_defaults_to_v1(self):
        assert config.detect_schema_version(V1_NO_ARCH_VERSION) == 1

    @pytest.mark.parametrize("raw", [
        "# not a version",
        "garbage",
        "",
    ])
    def test_malformed_field_defaults_to_v1(self, raw):
        text = f"- **Architecture Version**: {raw}\n"
        assert config.detect_schema_version(text) == 1

    def test_v3_reads_as_v2(self):
        """Future schemas clamp upward — v2+ parser will be used."""
        text = "- **Architecture Version**: 3\n## Agents\n\n- **pm**: pm\n  - role: pm\n"
        assert config.detect_schema_version(text) == 2


# ---------------------------------------------------------------------------
# v1 parser
# ---------------------------------------------------------------------------


class TestParseAgentsV1:
    def test_single_dev_role_with_pm_qa_dm(self):
        agents = config._parse_agents_v1(V1_MINIMAL)
        by_id = {a["id"]: a for a in agents}
        assert set(by_id) == {"pm", "skill", "qa", "dm"}

        # pm first, always present
        assert by_id["pm"]["role"] == "pm"
        assert by_id["pm"]["alias"] == "pm"

        # skill is the dev role
        assert by_id["skill"]["role"] == "dev"
        assert by_id["skill"]["alias"] == "skill"
        assert by_id["skill"]["test_command"] == "python tests/run_tests.py"

        # qa implied because Dev Agents is non-empty + PM/QA always present
        assert by_id["qa"]["role"] == "qa"

        # dm because `**DM**: present`
        assert by_id["dm"]["role"] == "dm"

    def test_multiple_dev_roles_no_dm(self):
        agents = config._parse_agents_v1(V1_NO_DM)
        by_id = {a["id"]: a for a in agents}
        assert set(by_id) == {"pm", "be", "fe", "qa"}
        assert by_id["be"]["alias"] == "backend"
        assert by_id["fe"]["alias"] == "frontend"
        assert by_id["pm"]["alias"] == "peggy"
        assert by_id["be"]["test_command"] == "pytest tests/be"
        assert by_id["fe"]["test_command"] == "npm test"
        assert "dm" not in by_id

    def test_no_dev_roles(self):
        """A config with only infrastructure roles still returns pm + dm."""
        agents = config._parse_agents_v1(V1_NO_DEV_ROLES)
        by_id = {a["id"]: a for a in agents}
        assert "pm" in by_id
        assert "dm" in by_id
        # QA is NOT added when there are no dev roles
        assert "qa" not in by_id

    def test_get_agents_uses_v1_path(self):
        agents = config.get_agents(V1_MINIMAL)
        assert any(a["id"] == "skill" for a in agents)

    def test_v1_test_command_missing_field_is_omitted(self):
        text = V1_MINIMAL.replace(
            "- **skill Tests**: python tests/run_tests.py", ""
        )
        agents = config._parse_agents_v1(text)
        skill = next(a for a in agents if a["id"] == "skill")
        assert "test_command" not in skill


# ---------------------------------------------------------------------------
# v2 parser
# ---------------------------------------------------------------------------


class TestParseAgentsV2:
    def test_full_software_dev_install(self):
        agents = config._parse_agents_v2(V2_FULL)
        ids = [a["id"] for a in agents]
        assert ids == ["pm", "designer", "be", "fe", "qa", "dm"]

    def test_simple_agent_entry(self):
        agents = config._parse_agents_v2(V2_FULL)
        pm = next(a for a in agents if a["id"] == "pm")
        assert pm == {"id": "pm", "alias": "peggy", "role": "pm"}

    def test_agent_with_iteration_mode_and_setup_block(self):
        agents = config._parse_agents_v2(V2_FULL)
        designer = next(a for a in agents if a["id"] == "designer")
        assert designer["role"] == "designer"
        assert designer["iteration_mode"] == "hitl"
        assert designer["setup"] == {"install_optional": "yes"}

    def test_dev_agent_with_quoted_stack_and_test_command(self):
        agents = config._parse_agents_v2(V2_FULL)
        be = next(a for a in agents if a["id"] == "be")
        assert be["role"] == "dev"
        assert be["variant"] == "be"
        # The quotes from Q-new17 formatting must be stripped
        assert be["stack"] == "FastAPI + Python 3.11 + pytest"
        assert be["test_command"] == "pytest tests/be"

    def test_multiple_dev_agents_do_not_leak_fields(self):
        """be and fe must each get their own stack/test_command."""
        agents = config._parse_agents_v2(V2_FULL)
        be = next(a for a in agents if a["id"] == "be")
        fe = next(a for a in agents if a["id"] == "fe")
        assert be["stack"] == "FastAPI + Python 3.11 + pytest"
        assert fe["stack"] == "Next.js + TypeScript + jest"
        assert be["test_command"] != fe["test_command"]

    def test_alias_defaults_to_id_when_same(self):
        agents = config._parse_agents_v2(V2_FULL)
        fe = next(a for a in agents if a["id"] == "fe")
        assert fe["alias"] == "fe"

    def test_design_preset_only_three_agents(self):
        agents = config._parse_agents_v2(V2_DESIGN_PRESET)
        ids = [a["id"] for a in agents]
        assert ids == ["pm", "designer", "dm"]

    def test_empty_agents_section(self):
        text = "- **Architecture Version**: 2\n## Agents\n\n"
        agents = config._parse_agents_v2(text)
        assert agents == []

    def test_setup_block_with_multiple_fields(self):
        text = (
            "- **Architecture Version**: 2\n"
            "## Agents\n\n"
            "- **pm**: peggy\n"
            "  - role: pm\n"
            "  - setup:\n"
            "    - alpha: one\n"
            "    - beta: two\n"
        )
        agents = config._parse_agents_v2(text)
        assert agents[0]["setup"] == {"alpha": "one", "beta": "two"}

    def test_setup_block_closes_on_next_top_level_entry(self):
        """A `- **next**: agent` line must exit the setup block."""
        text = (
            "- **Architecture Version**: 2\n"
            "## Agents\n\n"
            "- **pm**: peggy\n"
            "  - role: pm\n"
            "  - setup:\n"
            "    - alpha: one\n"
            "- **dm**: dm\n"
            "  - role: dm\n"
        )
        agents = config._parse_agents_v2(text)
        by_id = {a["id"]: a for a in agents}
        assert by_id["pm"]["setup"] == {"alpha": "one"}
        assert "setup" not in by_id["dm"]


# ---------------------------------------------------------------------------
# get_agents — the schema-picking entry point
# ---------------------------------------------------------------------------


class TestGetAgents:
    def test_v1_path(self):
        agents = config.get_agents(V1_MINIMAL)
        assert any(a["id"] == "skill" for a in agents)

    def test_v2_path(self):
        agents = config.get_agents(V2_FULL)
        assert any(a["id"] == "designer" for a in agents)
        assert any(a.get("variant") == "be" for a in agents)

    def test_missing_schema_defaults_to_v1(self):
        agents = config.get_agents(V1_NO_ARCH_VERSION)
        assert any(a["id"] == "skill" for a in agents)

    def test_v2_reads_same_canonical_shape_as_v1(self):
        """Both schemas return lists of dicts with at least id/role/alias."""
        for text in (V1_MINIMAL, V2_FULL):
            for agent in config.get_agents(text):
                assert "id" in agent and isinstance(agent["id"], str)
                assert "role" in agent and isinstance(agent["role"], str)
                assert "alias" in agent and isinstance(agent["alias"], str)


# ---------------------------------------------------------------------------
# Round-trip with wizard.build_config_md
# ---------------------------------------------------------------------------


class TestWizardRoundTrip:
    """The writer and the reader must agree on the v2 format."""

    def test_minimal_design_preset_round_trip(self):
        import wizard
        spec = {
            "squidsquad_version": "0.16.0",
            "project": {"name": "demo", "repo": "github.com/x/y"},
            "preset": "design",
            "agents": [
                {"id": "pm", "alias": "peggy", "role": "pm"},
                {
                    "id": "designer",
                    "alias": "designer",
                    "role": "designer",
                    "iteration_mode": "hitl",
                },
                {"id": "dm", "alias": "dm", "role": "dm"},
            ],
            "tools": {"dm.tool": "local_delivery"},
            "loop": {"interval_minutes": 10, "context_threshold": 70},
            "flags": {},
        }
        text = wizard.build_config_md(spec)
        assert config.detect_schema_version(text) == 2
        agents = config.get_agents(text)
        ids = [a["id"] for a in agents]
        assert ids == ["pm", "designer", "dm"]
        designer = next(a for a in agents if a["id"] == "designer")
        assert designer["iteration_mode"] == "hitl"

    def test_full_software_dev_round_trip(self):
        import wizard
        spec = {
            "squidsquad_version": "0.16.0",
            "project": {"name": "demo", "repo": "github.com/x/y"},
            "preset": "software-dev",
            "agents": [
                {"id": "pm", "alias": "peggy", "role": "pm"},
                {
                    "id": "be",
                    "alias": "be",
                    "role": "dev",
                    "variant": "be",
                    "stack": "FastAPI + Python 3.11 + pytest",
                    "test_command": "pytest tests/be",
                },
                {
                    "id": "fe",
                    "alias": "fe",
                    "role": "dev",
                    "variant": "fe",
                    "stack": "Next.js + TypeScript + jest",
                    "test_command": "npm test",
                },
                {"id": "qa", "alias": "qa", "role": "qa"},
                {"id": "dm", "alias": "dm", "role": "dm"},
            ],
            "tools": {},
            "loop": {"interval_minutes": 10, "context_threshold": 70},
            "flags": {"pr_flow": False},
        }
        text = wizard.build_config_md(spec)
        agents = config.get_agents(text)
        be = next(a for a in agents if a["id"] == "be")
        fe = next(a for a in agents if a["id"] == "fe")
        assert be["variant"] == "be"
        assert fe["variant"] == "fe"
        # Quoted values must round-trip losslessly
        assert be["stack"] == "FastAPI + Python 3.11 + pytest"
        assert fe["test_command"] == "npm test"


# ---------------------------------------------------------------------------
# compose.py — _list_known_role_identities + _get_entry_file_for_role
# ---------------------------------------------------------------------------


class TestComposeKnownRoles:
    def test_list_known_identities_reads_real_registry(self):
        import compose
        ids = compose._list_known_role_identities()
        # Every shipped role manifest should be in the result
        assert {"pm", "dm", "designer", "dev", "qa"} <= ids

    def test_get_entry_file_for_shipped_role(self):
        import compose
        for role in ("pm", "dm", "designer", "dev", "qa"):
            assert compose._get_entry_file_for_role(role) == role

    def test_dev_variants_resolve_to_dev(self):
        import compose
        for variant in ("skill", "be", "fe", "fullstack", "worker"):
            assert compose._get_entry_file_for_role(variant) == "dev"

    def test_no_longer_hardcodes_known_roles_set(self):
        """Regression guard: #328 Phase H removed the hardcoded set."""
        text = (REPO_ROOT / "references" / "scripts" / "compose.py").read_text(
            encoding="utf-8"
        )
        # The old literal set-of-role-names must not reappear
        assert 'known_roles = {"pm", "dm", "qa", "designer", "dev"}' not in text
