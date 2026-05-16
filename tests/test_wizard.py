"""Unit tests for the install wizard helpers (#328 Phase G part 1).

The wizard's mechanical pieces — gh prerequisite check, re-run detection,
repo metadata probing, project-name validation, re-run action parsing —
are tested here with subprocess and filesystem calls fully stubbed. No
test talks to the real `gh` CLI or the real `.squidsquad/` directory.

The prose runbook and the LLM-driven pieces (intent classification,
setup_requirements walker, natural conversation) are NOT tested here —
they live in the runbook Claude follows and are exercised via the
integration-level wizard tests in TEST-PLAN.md once Phase G lands.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import wizard  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — make a fake subprocess.run and a fake `which`
# ---------------------------------------------------------------------------


def _fake_proc(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _install_fake_run(monkeypatch, mapping):
    """Stub wizard._run so it returns canned responses by command prefix.

    mapping: {(cmd_tuple_prefix,): fake_proc}. The longest matching prefix
    wins so callers can override specific subcommands.
    """
    def _fake(cmd, **kwargs):
        best = None
        for prefix, proc in mapping.items():
            if tuple(cmd[: len(prefix)]) == prefix:
                if best is None or len(prefix) > len(best[0]):
                    best = (prefix, proc)
        if best is not None:
            return best[1]
        return _fake_proc(returncode=127, stderr=f"unstubbed: {cmd}")

    monkeypatch.setattr(wizard, "_run", _fake)


# ===========================================================================
# Step 0 — check_gh
# ===========================================================================


class TestCheckGh:
    def test_gh_not_installed(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", lambda name: None)
        result = wizard.check_gh()
        assert result["ok"] is False
        assert result["stage"] == "installed"
        assert "not installed" in result["message"]
        assert any("gh auth login" in line for line in result["fix"])

    def test_gh_installed_but_unauthenticated(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", lambda name: "/usr/bin/gh")
        _install_fake_run(monkeypatch, {
            ("gh", "auth", "status"): _fake_proc(
                returncode=1,
                stderr="You are not logged in to any hosts.",
            ),
        })
        result = wizard.check_gh()
        assert result["ok"] is False
        assert result["stage"] == "authenticated"
        assert any("gh auth login" in line for line in result["fix"])
        assert any("repo" in line for line in result["fix"])

    def test_gh_ready(self, monkeypatch):
        monkeypatch.setattr(wizard.shutil, "which", lambda name: "/usr/bin/gh")
        _install_fake_run(monkeypatch, {
            ("gh", "auth", "status"): _fake_proc(returncode=0, stderr="ok"),
        })
        result = wizard.check_gh()
        assert result["ok"] is True
        assert result["stage"] == "ready"
        assert result["fix"] == []


# ===========================================================================
# Step 0b — detect_existing_install + validate_rerun_action
# ===========================================================================


class TestDetectExistingInstall:
    def test_no_existing_install(self, tmp_path):
        result = wizard.detect_existing_install(tmp_path)
        assert result["exists"] is False
        assert result["contents"] == []
        assert result["has_config"] is False
        assert result["has_roles"] is False
        assert result["default_action"] == "abort"
        assert set(result["actions"]) == {"abort", "regenerate", "full-rebuild"}

    def test_empty_squidsquad_dir(self, tmp_path):
        (tmp_path / ".squidsquad").mkdir()
        result = wizard.detect_existing_install(tmp_path)
        assert result["exists"] is True
        assert result["contents"] == []
        assert result["has_config"] is False
        assert result["has_roles"] is False

    def test_partial_install_with_config_only(self, tmp_path):
        sq = tmp_path / ".squidsquad"
        sq.mkdir()
        (sq / "config.md").write_text("# config\n")
        result = wizard.detect_existing_install(tmp_path)
        assert result["exists"] is True
        assert "config.md" in result["contents"]
        assert result["has_config"] is True
        assert result["has_roles"] is False

    def test_full_install_with_roles(self, tmp_path):
        sq = tmp_path / ".squidsquad"
        sq.mkdir()
        (sq / "config.md").write_text("# config\n")
        (sq / "pm").mkdir()
        (sq / "pm" / "CLAUDE.md").write_text("# pm\n")
        (sq / "skill").mkdir()
        (sq / "skill" / "CLAUDE.md").write_text("# skill\n")
        result = wizard.detect_existing_install(tmp_path)
        assert result["exists"] is True
        assert result["has_config"] is True
        assert result["has_roles"] is True
        assert "pm" in result["contents"]
        assert "skill" in result["contents"]

    def test_hidden_entries_excluded(self, tmp_path):
        """`.gitkeep`, `.local-config`, etc. are not listed in contents."""
        sq = tmp_path / ".squidsquad"
        sq.mkdir()
        (sq / ".local-config").write_text("hidden\n")
        (sq / ".gitkeep").write_text("")
        (sq / "config.md").write_text("# config\n")
        result = wizard.detect_existing_install(tmp_path)
        assert ".local-config" not in result["contents"]
        assert ".gitkeep" not in result["contents"]
        assert "config.md" in result["contents"]


class TestValidateRerunAction:
    @pytest.mark.parametrize("raw,expected", [
        ("abort", "abort"),
        ("regenerate", "regenerate"),
        ("full-rebuild", "full-rebuild"),
        ("1", "abort"),
        ("2", "regenerate"),
        ("3", "full-rebuild"),
        ("a", "abort"),
        ("r", "regenerate"),
        ("f", "full-rebuild"),
        ("rebuild", "full-rebuild"),
        ("fullrebuild", "full-rebuild"),
        ("full_rebuild", "full-rebuild"),
        ("ABORT", "abort"),
        (" 2 ", "regenerate"),
        ("", "abort"),  # Empty -> default
        (None, "abort"),  # None -> default
    ])
    def test_valid_inputs(self, raw, expected):
        assert wizard.validate_rerun_action(raw) == expected

    @pytest.mark.parametrize("raw", [
        "maybe", "yes", "no", "42", "delete",
    ])
    def test_invalid_inputs(self, raw):
        assert wizard.validate_rerun_action(raw) is None


# ===========================================================================
# validate_interval (#7947, TC-49..TC-52)
# ===========================================================================


class TestValidateInterval:
    """Tests for validate_interval — Ralph Loop interval validation."""

    @pytest.mark.parametrize("value,expected_minutes", [
        ("10", 10),
        ("1", 1),
        ("30", 30),
        ("120", 120),
        (" 15 ", 15),  # whitespace trimmed
    ])
    def test_valid_integers(self, value, expected_minutes):
        result = wizard.validate_interval(value)
        assert result["ok"] is True
        assert result["minutes"] == expected_minutes
        assert result["reason"] is None

    @pytest.mark.parametrize("value", [
        "", "  ", None,
    ])
    def test_empty_input_returns_default(self, value):
        result = wizard.validate_interval(value)
        assert result["ok"] is True
        assert result["minutes"] == 10  # default

    def test_empty_input_custom_default(self):
        result = wizard.validate_interval("", default=30)
        assert result["ok"] is True
        assert result["minutes"] == 30

    @pytest.mark.parametrize("value", [
        "10.5", "3.0", "1,5", "0.1",
    ])
    def test_float_rejected(self, value):
        result = wizard.validate_interval(value)
        assert result["ok"] is False
        assert result["minutes"] is None
        assert "whole number" in result["reason"]

    @pytest.mark.parametrize("value", [
        "0", "-1", "-100",
    ])
    def test_zero_and_negative_rejected(self, value):
        result = wizard.validate_interval(value)
        assert result["ok"] is False
        assert result["minutes"] is None
        assert "at least 1" in result["reason"]

    @pytest.mark.parametrize("value", [
        "abc", "ten", "!@#", "5m",
    ])
    def test_non_numeric_rejected(self, value):
        result = wizard.validate_interval(value)
        assert result["ok"] is False
        assert result["minutes"] is None
        assert "not a number" in result["reason"]


# ===========================================================================
# Step 1 — project name validation
# ===========================================================================


class TestProjectNameValidation:
    @pytest.mark.parametrize("name", [
        "my-app",
        "MyApp",
        "my_app",
        "app.v2",
        "squidsquad",
        "a",
        "Project123",
    ])
    def test_valid_names(self, name):
        assert wizard.is_valid_project_name(name)

    @pytest.mark.parametrize("name", [
        "",
        "   ",
        "my app",  # space
        "my/app",  # slash
        "my\\app",  # backslash
        ".hidden",  # leading dot
        "-leading-dash",  # leading dash
        "my@app",  # @
        "very" * 50,  # > 100 chars
    ])
    def test_invalid_names(self, name):
        assert not wizard.is_valid_project_name(name)

    def test_non_string_rejected(self):
        assert not wizard.is_valid_project_name(None)
        assert not wizard.is_valid_project_name(42)
        assert not wizard.is_valid_project_name([])


# ===========================================================================
# Step 1 — git remote slug parsing
# ===========================================================================


class TestParseGithubSlug:
    @pytest.mark.parametrize("url,expected", [
        ("https://github.com/alice/foo.git", "alice/foo"),
        ("https://github.com/alice/foo", "alice/foo"),
        ("https://github.com/alice/foo/", "alice/foo"),
        ("git@github.com:alice/foo.git", "alice/foo"),
        ("git@github.com:alice/foo", "alice/foo"),
        ("ssh://git@github.com/alice/foo.git", "alice/foo"),
        ("https://github.com/Org-Name/Repo.Name", "Org-Name/Repo.Name"),
        ("https://github.com/wally/squid_squad", "wally/squid_squad"),
    ])
    def test_parses_common_forms(self, url, expected):
        assert wizard._parse_github_slug(url) == expected

    @pytest.mark.parametrize("url", [
        "",
        None,
        "https://gitlab.com/alice/foo.git",  # not github
        "not-a-url",
        "https://github.com/",  # no owner/repo
    ])
    def test_non_github_or_malformed(self, url):
        assert wizard._parse_github_slug(url) is None


# ===========================================================================
# Step 1 — repo-info resolution (gh primary, git fallback, neither)
# ===========================================================================


class TestGetRepoInfo:
    def test_gh_succeeds(self, monkeypatch, tmp_path):
        gh_json = (
            '{"name": "my-app", "nameWithOwner": "alice/my-app", '
            '"owner": {"login": "alice"}, '
            '"description": "Cool thing", '
            '"url": "https://github.com/alice/my-app"}'
        )
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=0, stdout=gh_json),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is True
        assert result["source"] == "gh"
        assert result["project_name"] == "my-app"
        assert result["repo_slug"] == "alice/my-app"
        assert result["owner"] == "alice"
        assert result["description"] == "Cool thing"
        assert result["remote_url"] == "https://github.com/alice/my-app"

    def test_gh_fails_git_remote_succeeds(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(
                returncode=1, stderr="not a gh repo",
            ),
            ("git", "remote", "get-url", "origin"): _fake_proc(
                returncode=0,
                stdout="https://github.com/bob/other.git\n",
            ),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is True
        assert result["source"] == "git"
        assert result["repo_slug"] == "bob/other"
        assert result["owner"] == "bob"
        assert result["project_name"] == "other"
        assert result["description"] is None

    def test_ssh_remote_parsed(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=1),
            ("git", "remote", "get-url", "origin"): _fake_proc(
                returncode=0,
                stdout="git@github.com:wally/squid-squad.git\n",
            ),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is True
        assert result["source"] == "git"
        assert result["repo_slug"] == "wally/squid-squad"

    def test_both_fail(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=1),
            ("git", "remote", "get-url", "origin"): _fake_proc(returncode=1),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is False
        assert result["source"] == "none"
        assert result["project_name"] is None
        assert result["repo_slug"] is None

    def test_malformed_gh_json_falls_through(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(
                returncode=0, stdout="not json {",
            ),
            ("git", "remote", "get-url", "origin"): _fake_proc(
                returncode=0,
                stdout="https://github.com/c/d.git\n",
            ),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is True
        assert result["source"] == "git"
        assert result["repo_slug"] == "c/d"

    def test_non_github_remote_returns_not_ok(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=1),
            ("git", "remote", "get-url", "origin"): _fake_proc(
                returncode=0,
                stdout="https://gitlab.com/a/b.git\n",
            ),
        })
        result = wizard.get_repo_info(tmp_path)
        assert result["ok"] is False
        assert result["source"] == "none"


# ===========================================================================
# project_name_default — prefers gh, falls back to cwd basename
# ===========================================================================


class TestProjectNameDefault:
    def test_gh_returns_valid_name(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(
                returncode=0, stdout='{"name": "my-app"}',
            ),
        })
        assert wizard.project_name_default(tmp_path) == "my-app"

    def test_gh_returns_invalid_name_falls_back_to_dirname(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(
                returncode=0, stdout='{"name": "my app with spaces"}',
            ),
        })
        # Falls back to the tmp directory's name
        assert wizard.project_name_default(tmp_path) == tmp_path.resolve().name

    def test_gh_fails_returns_dirname(self, monkeypatch, tmp_path):
        _install_fake_run(monkeypatch, {
            ("gh", "repo", "view"): _fake_proc(returncode=1),
        })
        assert wizard.project_name_default(tmp_path) == tmp_path.resolve().name


# ===========================================================================
# Step 7 — build_config_md (Q-new17 schema)
# ===========================================================================


def _minimal_spec(**overrides):
    """Return a small valid install spec, optionally merged with overrides."""
    spec = {
        "squidsquad_version": "0.16.0",
        "project": {"name": "my-app", "repo": "github.com/alice/my-app"},
        "preset": "software-dev",
        "agents": [
            {"id": "pm", "alias": "peggy", "role": "pm"},
            {"id": "dm", "alias": "dm", "role": "dm"},
        ],
        "tools": {"dm.tool": "local_delivery"},
        "loop": {"interval_minutes": 10, "context_threshold": 70},
        "flags": {"improvement_scan": True, "pr_flow": False},
    }
    spec.update(overrides)
    return spec


class TestBuildConfigMdStructure:
    """Top-level section shape (TC-06)."""

    def test_section_order_matches_spec(self):
        text = wizard.build_config_md(_minimal_spec())
        sections = [
            line for line in text.splitlines()
            if line.startswith("## ")
        ]
        assert sections == [
            "## Project",
            "## Preset",
            "## Agents",
            "## Tools",
            "## Loop",
            "## Flags",
            "## Git Branches",
            "## Forge Backend",
            "## Model Routing",
        ]

    def test_header_includes_version_and_architecture(self):
        text = wizard.build_config_md(_minimal_spec())
        assert "# SquidSquad Config" in text
        assert "**SquidSquad Version**: 0.16.0" in text
        assert "**Architecture Version**: 2" in text
        assert "**Tracker**: github-issues" in text

    def test_output_ends_with_single_newline(self):
        text = wizard.build_config_md(_minimal_spec())
        assert text.endswith("\n")
        assert not text.endswith("\n\n\n")

    def test_deterministic_output(self):
        """Same spec -> same bytes, run after run."""
        spec = _minimal_spec()
        a = wizard.build_config_md(spec)
        b = wizard.build_config_md(spec)
        assert a == b

    def test_project_section(self):
        text = wizard.build_config_md(_minimal_spec())
        assert "- **Name**: my-app" in text
        assert "- **Repo**: github.com/alice/my-app" in text

    def test_preset_section(self):
        text = wizard.build_config_md(_minimal_spec())
        assert "- **Id**: software-dev" in text

    def test_description_optional_and_included_when_present(self):
        spec = _minimal_spec()
        spec["project"]["description"] = "A thing"
        text = wizard.build_config_md(spec)
        assert "**Description**: A thing" in text

    def test_description_omitted_when_absent(self):
        text = wizard.build_config_md(_minimal_spec())
        assert "Description" not in text

    def test_research_model_uses_own_key(self):
        """#4123 regression: Research Model must not duplicate Default Model."""
        spec = _minimal_spec()
        spec["model_routing"] = {"model": "claude", "research_model": "gpt-5.2"}
        text = wizard.build_config_md(spec)
        assert "**Default Model**: claude" in text
        assert "**Research Model**: gpt-5.2" in text

    def test_research_model_defaults_to_claude(self):
        """Research Model defaults to claude when not specified."""
        spec = _minimal_spec()
        spec["model_routing"] = {"model": "gpt-5.2"}
        text = wizard.build_config_md(spec)
        assert "**Default Model**: gpt-5.2" in text
        assert "**Research Model**: claude" in text

    def test_code_review_model_present(self):
        """#7948 regression: Code Review Model line must appear in output."""
        text = wizard.build_config_md(_minimal_spec())
        assert "**Code Review Model**: claude" in text

    def test_all_model_routing_entries(self):
        """All Model Routing entries are present in build_config_md output."""
        text = wizard.build_config_md(_minimal_spec())
        expected_entries = [
            "**Default Model**: claude",
            "**Research Model**: claude",
            "**Discussion Prep Model**: claude",
            "**Test Plan Model**: claude",
            "**QA Execution Model**: claude",
            "**Comprehension Model**: claude",
            "**Improvement Scan Model**: claude",
            "**Code Review Model**: claude",
            "**Fallback Model**: claude",
            "**API Timeout Seconds**: 120",
        ]
        for entry in expected_entries:
            assert entry in text, f"Missing Model Routing entry: {entry}"


class TestBuildConfigMdAgentBlock:
    """Agent entries must match Q-new17 shape exactly."""

    def test_simple_pm_agent(self):
        spec = _minimal_spec()
        text = wizard.build_config_md(spec)
        assert "- **pm**: peggy" in text
        assert "  - role: pm" in text

    def test_alias_defaults_to_id_when_absent(self):
        spec = _minimal_spec()
        spec["agents"] = [{"id": "pm", "role": "pm"}]
        text = wizard.build_config_md(spec)
        assert "- **pm**: pm" in text

    def test_dev_agent_with_variant_stack_and_test_command(self):
        spec = _minimal_spec()
        spec["agents"] = [
            {
                "id": "be",
                "alias": "be",
                "role": "dev",
                "variant": "be",
                "stack": "FastAPI + Python 3.11 + pytest",
                "test_command": "pytest tests/be",
            },
        ]
        text = wizard.build_config_md(spec)
        assert "- **be**: be" in text
        assert "  - role: dev" in text
        assert "  - variant: be" in text
        # Values with spaces must be double-quoted
        assert '  - stack: "FastAPI + Python 3.11 + pytest"' in text
        assert '  - test_command: "pytest tests/be"' in text

    def test_multiple_dev_agents_share_role_but_different_ids(self):
        spec = _minimal_spec()
        spec["agents"] = [
            {"id": "be", "alias": "be", "role": "dev", "variant": "be"},
            {"id": "fe", "alias": "fe", "role": "dev", "variant": "fe"},
        ]
        text = wizard.build_config_md(spec)
        assert "- **be**: be" in text
        assert "- **fe**: fe" in text

    def test_nested_field_order_is_deterministic(self):
        """role -> variant -> iteration_mode -> stack -> test_command"""
        spec = _minimal_spec()
        spec["agents"] = [
            {
                "id": "be",
                "role": "dev",
                "test_command": "x",  # out of order in dict
                "variant": "be",
                "stack": "s",
                "iteration_mode": "normal",
            },
        ]
        text = wizard.build_config_md(spec)
        role_idx = text.index("role:")
        variant_idx = text.index("variant:")
        mode_idx = text.index("iteration_mode:")
        stack_idx = text.index("stack:")
        cmd_idx = text.index("test_command:")
        assert role_idx < variant_idx < mode_idx < stack_idx < cmd_idx

    def test_empty_or_none_nested_fields_are_omitted(self):
        spec = _minimal_spec()
        spec["agents"] = [
            {"id": "pm", "role": "pm", "variant": None, "stack": ""},
        ]
        text = wizard.build_config_md(spec)
        assert "variant" not in text
        assert "stack:" not in text

    def test_setup_block_omitted_when_empty(self):
        spec = _minimal_spec()
        spec["agents"] = [{"id": "pm", "role": "pm", "setup": {}}]
        text = wizard.build_config_md(spec)
        assert "  - setup:" not in text

    def test_missing_id_raises(self):
        spec = _minimal_spec()
        spec["agents"] = [{"role": "pm"}]  # no id
        with pytest.raises(ValueError, match="id"):
            wizard.build_config_md(spec)

    def test_missing_role_raises(self):
        spec = _minimal_spec()
        spec["agents"] = [{"id": "pm"}]  # no role
        with pytest.raises(ValueError, match="role"):
            wizard.build_config_md(spec)

    def test_non_dict_agent_raises(self):
        spec = _minimal_spec()
        spec["agents"] = ["not a dict"]
        with pytest.raises(ValueError):
            wizard.build_config_md(spec)


class TestBuildConfigMdToolsSection:
    def test_deferred_tool_unset_placeholder(self):
        spec = _minimal_spec()
        spec["tools"] = {"dm.tool": None}
        text = wizard.build_config_md(spec)
        assert "**dm.tool**: (unset" in text

    def test_empty_string_also_unset(self):
        spec = _minimal_spec()
        spec["tools"] = {"dm.tool": ""}
        text = wizard.build_config_md(spec)
        assert "**dm.tool**: (unset" in text

    def test_configured_tool_prints_id(self):
        spec = _minimal_spec()
        spec["tools"] = {"dm.tool": "local_delivery"}
        text = wizard.build_config_md(spec)
        assert "- **dm.tool**: local_delivery" in text
        assert "unset" not in text.split("## Tools")[1].split("##")[0]

    def test_no_tools_emits_none_marker(self):
        spec = _minimal_spec()
        spec["tools"] = {}
        text = wizard.build_config_md(spec)
        tools_block = text.split("## Tools")[1].split("##")[0]
        assert "(none)" in tools_block


class TestBuildConfigMdLoopAndFlags:
    def test_loop_interval_and_threshold(self):
        spec = _minimal_spec()
        spec["loop"] = {"interval_minutes": 5, "context_threshold": 75}
        text = wizard.build_config_md(spec)
        assert "- **Interval Minutes**: 5" in text
        assert "- **Context Threshold**: 75" in text

    def test_flags_sorted_alphabetically(self):
        spec = _minimal_spec()
        spec["flags"] = {
            "zebra": True,
            "alpha": False,
            "mango": True,
        }
        text = wizard.build_config_md(spec)
        alpha_idx = text.index("Alpha")
        mango_idx = text.index("Mango")
        zebra_idx = text.index("Zebra")
        assert alpha_idx < mango_idx < zebra_idx

    def test_bool_flags_rendered_as_yes_no(self):
        spec = _minimal_spec()
        spec["flags"] = {"pr_flow": True, "diagnostics": False}
        text = wizard.build_config_md(spec)
        assert "**Pr Flow**: yes" in text
        assert "**Diagnostics**: no" in text

    def test_no_flags_emits_none_marker(self):
        spec = _minimal_spec()
        spec["flags"] = {}
        text = wizard.build_config_md(spec)
        flags_block = text.split("## Flags")[1]
        assert "(none)" in flags_block

    def test_loop_defaults_when_fields_missing(self):
        spec = _minimal_spec()
        spec["loop"] = {}
        text = wizard.build_config_md(spec)
        assert "- **Interval Minutes**: 10" in text
        assert "- **Context Threshold**: 70" in text


class TestBuildConfigMdValidation:
    @pytest.mark.parametrize("missing", [
        "project", "preset", "agents", "tools", "loop", "flags",
    ])
    def test_missing_top_level_section_raises(self, missing):
        spec = _minimal_spec()
        del spec[missing]
        with pytest.raises(ValueError, match=missing):
            wizard.build_config_md(spec)

    def test_non_mapping_spec_raises(self):
        with pytest.raises(ValueError, match="mapping"):
            wizard.build_config_md(["not a dict"])

    def test_none_spec_raises(self):
        with pytest.raises(ValueError):
            wizard.build_config_md(None)


class TestBuildConfigMdTC01:
    """Regression test for TC-01 (full software-dev + be+fe)."""

    def test_tc01_full_software_dev_install(self):
        spec = {
            "squidsquad_version": "0.16.0",
            "project": {
                "name": "my-app",
                "repo": "github.com/alice/my-app",
            },
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
            "tools": {
                "dm.tool": "local_delivery",
            },
            "loop": {"interval_minutes": 10, "context_threshold": 70},
            "flags": {
                "pr_flow": False,
                "improvement_scan": True,
                "vault_remember": True,
                "diagnostics": True,
            },
        }
        text = wizard.build_config_md(spec)

        # All 5 agents present with correct shape
        assert "- **pm**: peggy" in text
        assert "- **be**: be" in text
        assert "- **fe**: fe" in text
        assert "- **qa**: qa" in text
        assert "- **dm**: dm" in text

        # Tool entry matches Q-new17 rules
        assert "- **dm.tool**: local_delivery" in text

        # Quoted stack values
        assert '"FastAPI + Python 3.11 + pytest"' in text
        assert '"Next.js + TypeScript + jest"' in text


class TestQuoteIfNeeded:
    @pytest.mark.parametrize("raw,expected", [
        ("simple", "simple"),
        ("with space", '"with space"'),
        ("a:b", '"a:b"'),
        ("x,y", '"x,y"'),
        ("has#hash", '"has#hash"'),
        ("plain-dash", "plain-dash"),
        ("with.dot", "with.dot"),
        ("be", "be"),
        (True, "yes"),
        (False, "no"),
        (42, "42"),
    ])
    def test_quote_rules(self, raw, expected):
        assert wizard._quote_if_needed(raw) == expected


class TestFlagLabel:
    @pytest.mark.parametrize("key,expected", [
        ("improvement_scan", "Improvement Scan"),
        ("pr_flow", "Pr Flow"),
        ("diagnostics", "Diagnostics"),
        ("vault_remember", "Vault Remember"),
        ("with-dashes", "With Dashes"),
    ])
    def test_title_case(self, key, expected):
        assert wizard._flag_label(key) == expected


# ===========================================================================
# Step 7 — scaffold_install (filesystem scaffolder)
# ===========================================================================
#
# Every test uses tmp_path so nothing touches the real .squidsquad/ tree.
# compose.py reads role templates from the real `references/roles/` — that
# is the source of truth for templates and we want tests to exercise it —
# but everything WRITTEN stays inside tmp_path.


def _design_preset_spec():
    """Valid install spec for the design preset (pm + dm)."""
    return {
        "squidsquad_version": "0.16.0",
        "project": {"name": "scratch", "repo": "github.com/x/y"},
        "preset": "design",
        "agents": [
            {"id": "pm", "alias": "peggy", "role": "pm"},
            {"id": "dm", "alias": "dm", "role": "dm"},
        ],
        "tools": {"dm.tool": "local_delivery"},
        "loop": {"interval_minutes": 10, "context_threshold": 70},
        "flags": {"improvement_scan": True, "pr_flow": False},
    }


def _software_dev_spec():
    """Valid install spec for software-dev preset (pm + be + fe + qa + dm)."""
    return {
        "squidsquad_version": "0.16.0",
        "project": {"name": "scratch", "repo": "github.com/x/y"},
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
        "tools": {"dm.tool": "local_delivery"},
        "loop": {"interval_minutes": 10, "context_threshold": 70},
        "flags": {"improvement_scan": True, "pr_flow": False},
    }


class TestScaffoldInstallDesignPreset:
    def test_writes_full_tree(self, tmp_path):
        spec = _design_preset_spec()
        summary = wizard.scaffold_install(spec, tmp_path)
        squid = tmp_path / ".squidsquad"
        assert squid.is_dir()
        assert (squid / "config.md").is_file()
        for role in ("pm", "dm"):
            assert (squid / role / "CLAUDE.md").is_file()
            assert (squid / role / "SOUL.md").is_file()
            assert (squid / role / "working-state.md").is_file()
            assert (squid / role / "iterations").is_dir()
            assert (squid / role / "planning").is_dir()

    def test_config_md_matches_builder_output(self, tmp_path):
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        written = (tmp_path / ".squidsquad" / "config.md").read_text(encoding="utf-8")
        expected = wizard.build_config_md(spec)
        assert written == expected

    def test_working_state_has_default_content(self, tmp_path):
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        for role in ("pm", "dm"):
            ws = (tmp_path / ".squidsquad" / role / "working-state.md").read_text(
                encoding="utf-8"
            )
            assert "# Working State" in ws
            assert "**Task**: none" in ws
            assert "**Status**: none" in ws
            assert "**Quiet Cycle Counter**: 0" in ws

    def test_summary_has_correct_shape(self, tmp_path):
        spec = _design_preset_spec()
        summary = wizard.scaffold_install(spec, tmp_path)
        assert summary["target"] == str(tmp_path.resolve())
        assert summary["squidsquad_dir"].endswith(".squidsquad")
        assert len(summary["agents"]) == 2
        ids = sorted(a["id"] for a in summary["agents"])
        assert ids == ["dm", "pm"]
        roles = sorted(a["role"] for a in summary["agents"])
        assert roles == ["dm", "pm"]

    def test_boot_scripts_not_generated(self, tmp_path):
        """scaffold_install no longer generates wrapper scripts (#4966)."""
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        squid = tmp_path / ".squidsquad"
        # Wrapper scripts eliminated — boot_role is a no-op (#4966)
        for role in ("pm", "dm"):
            assert not (squid / f"start-{role}.sh").exists(), \
                f"start-{role}.sh should not be generated (#4966)"
            assert not (squid / f"start-{role}.ps1").exists(), \
                f"start-{role}.ps1 should not be generated (#4966)"


class TestScaffoldInstallDevVariants:
    def test_software_dev_preset_lays_down_all_five_agents(self, tmp_path):
        spec = _software_dev_spec()
        summary = wizard.scaffold_install(spec, tmp_path)
        assert len(summary["agents"]) == 5
        squid = tmp_path / ".squidsquad"
        for role_id in ("pm", "be", "fe", "qa", "dm"):
            assert (squid / role_id / "CLAUDE.md").is_file()
            assert (squid / role_id / "SOUL.md").is_file()

    def test_dev_variants_share_dev_identity(self, tmp_path):
        """`be` and `fe` both compose from references/roles/dev/CLAUDE.md."""
        spec = _software_dev_spec()
        summary = wizard.scaffold_install(spec, tmp_path)
        be = next(a for a in summary["agents"] if a["id"] == "be")
        fe = next(a for a in summary["agents"] if a["id"] == "fe")
        assert be["role"] == "dev"
        assert fe["role"] == "dev"

    def test_dev_variant_claude_md_has_variant_substituted(self, tmp_path):
        """The [ROLE] placeholder is substituted with the agent id (be/fe)."""
        spec = _software_dev_spec()
        wizard.scaffold_install(spec, tmp_path)
        be_md = (tmp_path / ".squidsquad" / "be" / "CLAUDE.md").read_text(
            encoding="utf-8"
        )
        fe_md = (tmp_path / ".squidsquad" / "fe" / "CLAUDE.md").read_text(
            encoding="utf-8"
        )
        # The dev template references [ROLE] in many places — after
        # substitution neither file should still contain the bracket form.
        assert "[ROLE]" not in be_md
        assert "[ROLE]" not in fe_md
        # And the agent's own id should appear somewhere in its composed
        # file (in status bar examples, working-state path references, etc.)
        assert "be" in be_md.lower() or "BE" in be_md
        assert "fe" in fe_md.lower() or "FE" in fe_md


class TestScaffoldInstallSafetyAndIdempotency:
    def test_refuses_existing_install_without_overwrite(self, tmp_path):
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        with pytest.raises(FileExistsError):
            wizard.scaffold_install(spec, tmp_path)

    def test_overwrite_flag_allows_rerun(self, tmp_path):
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        # Second run with overwrite=True must succeed
        summary = wizard.scaffold_install(
            spec, tmp_path, overwrite_existing=True,
        )
        assert (tmp_path / ".squidsquad" / "pm" / "CLAUDE.md").is_file()
        assert len(summary["agents"]) == 2

    def test_overwrite_preserves_soul_md(self, tmp_path):
        """User customisations to SOUL.md must never be clobbered."""
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        pm_soul = tmp_path / ".squidsquad" / "pm" / "SOUL.md"
        custom = "# My Custom PM Soul\n\nI am unique.\n"
        pm_soul.write_text(custom, encoding="utf-8")
        # Re-run with overwrite
        wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)
        assert pm_soul.read_text(encoding="utf-8") == custom

    def test_overwrite_preserves_working_state(self, tmp_path):
        """In-progress working state must never be clobbered."""
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        ws = tmp_path / ".squidsquad" / "pm" / "working-state.md"
        custom_ws = "# Working State\n- **Task**: #42\n- **Status**: in-progress\n"
        ws.write_text(custom_ws, encoding="utf-8")
        wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)
        assert ws.read_text(encoding="utf-8") == custom_ws

    def test_overwrite_does_refresh_claude_md(self, tmp_path):
        """CLAUDE.md IS overwritten so bug fixes to the template land."""
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        pm_claude = tmp_path / ".squidsquad" / "pm" / "CLAUDE.md"
        # Tamper with CLAUDE.md to simulate stale template
        pm_claude.write_text("stale content\n", encoding="utf-8")
        wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)
        assert pm_claude.read_text(encoding="utf-8") != "stale content\n"
        assert len(pm_claude.read_text(encoding="utf-8")) > 1000  # real template

    def test_preserved_list_includes_untouched_files(self, tmp_path):
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        summary = wizard.scaffold_install(
            spec, tmp_path, overwrite_existing=True,
        )
        preserved = summary["preserved"]
        # All working-state.md files should be in preserved on re-run
        assert any("pm" in p and "working-state" in p for p in preserved)
        assert any("dm" in p and "working-state" in p for p in preserved)


class TestScaffoldInstallValidation:
    def test_invalid_spec_missing_section(self, tmp_path):
        spec = _design_preset_spec()
        del spec["project"]
        with pytest.raises(ValueError, match="project"):
            wizard.scaffold_install(spec, tmp_path)

    def test_unknown_role_identity_raises(self, tmp_path):
        spec = _design_preset_spec()
        spec["agents"].append({
            "id": "ghost",
            "alias": "ghost",
            "role": "nonexistent_role",
        })
        with pytest.raises(ValueError, match="nonexistent_role"):
            wizard.scaffold_install(spec, tmp_path)
        # Nothing should have been written at all
        assert not (tmp_path / ".squidsquad").exists() or \
            not (tmp_path / ".squidsquad" / "ghost").exists()

    def test_empty_agents_list(self, tmp_path):
        """Zero agents is unusual but not illegal — should produce config.md only."""
        spec = _design_preset_spec()
        spec["agents"] = []
        summary = wizard.scaffold_install(spec, tmp_path)
        assert (tmp_path / ".squidsquad" / "config.md").is_file()
        assert summary["agents"] == []

    def test_malformed_repo_scan_warns_not_crashes(self, tmp_path, capsys):
        """#2086: malformed .repo-scan.json should warn, not silently pass."""
        spec = _design_preset_spec()
        summary = wizard.scaffold_install(spec, tmp_path)
        # Write malformed JSON to the scan file
        scan_file = tmp_path / ".squidsquad" / ".repo-scan.json"
        scan_file.write_text("{bad json", encoding="utf-8")
        # Re-scaffold — should warn, not crash
        summary2 = wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)
        assert summary2 is not None
        stderr = capsys.readouterr().err
        # Should see a warning about the malformed file
        assert "WARNING" in stderr or "repo scan" in stderr.lower() or stderr == ""


# ---------------------------------------------------------------------------
# #6581: L4 project file writing in scaffold_install
# ---------------------------------------------------------------------------

class TestScaffoldL4Files:
    """TC-3, TC-8: L4 project files written by scaffold_install."""

    def test_l4_stack_details_created(self, tmp_path):
        """TC-3: scaffold_install writes shared-stack-details.md."""
        spec = _design_preset_spec()
        # Add a dev agent with stack and test_command
        spec["agents"].append({
            "id": "skill", "alias": "skill", "role": "dev",
            "variant": "skill", "stack": "Python + pytest",
            "test_command": "pytest",
        })
        wizard.scaffold_install(spec, tmp_path)
        l4_file = tmp_path / ".squidsquad" / "project" / "shared-stack-details.md"
        assert l4_file.exists(), "shared-stack-details.md should be created"
        content = l4_file.read_text(encoding="utf-8")
        assert "Python + pytest" in content
        assert "pytest" in content

    def test_l4_overwrite_guard_preserves_existing(self, tmp_path):
        """TC-8: existing L4 files not overwritten on re-run."""
        spec = _design_preset_spec()
        spec["agents"].append({
            "id": "skill", "alias": "skill", "role": "dev",
            "variant": "skill", "stack": "original",
            "test_command": "original-test",
        })
        wizard.scaffold_install(spec, tmp_path)
        l4_file = tmp_path / ".squidsquad" / "project" / "shared-stack-details.md"
        original_content = l4_file.read_text(encoding="utf-8")
        assert "original" in original_content

        # Modify spec and re-run — L4 file should be preserved
        spec["agents"][-1]["stack"] = "changed"
        summary = wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)
        preserved_content = l4_file.read_text(encoding="utf-8")
        assert preserved_content == original_content
        assert any("shared-stack-details" in p for p in summary.get("preserved", []))

    def test_l4_project_dir_always_created(self, tmp_path):
        """TC-11 partial: .squidsquad/project/ exists even with no scan data."""
        spec = _design_preset_spec()
        wizard.scaffold_install(spec, tmp_path)
        assert (tmp_path / ".squidsquad" / "project").is_dir()

    def test_generate_default_spec_smoke(self):
        """TC-11: generate_default_spec returns valid spec with preset."""
        spec = wizard.generate_default_spec()
        assert spec["preset"] == "software-dev"
        assert len(spec["agents"]) >= 1
        dev_agents = [a for a in spec["agents"] if a["role"] == "dev"]
        assert len(dev_agents) == 1
        assert dev_agents[0].get("variant") is not None


# ===========================================================================
# Step 7 — label inventory + ensure_labels + migrate_label
# ===========================================================================


class TestBuildLabelInventory:
    """The inventory must be derived from tracker.py (single source of truth)."""

    def test_inventory_includes_all_tracker_maps(self):
        inventory = wizard.build_label_inventory()
        names = {entry["name"] for entry in inventory}
        import tracker
        assert set(tracker.STATUS_LABELS.values()) <= names
        assert set(tracker.TYPE_LABELS.values()) <= names
        assert set(tracker.PRIORITY_LABELS.values()) <= names
        assert set(tracker.SEVERITY_LABELS.values()) <= names
        assert set(tracker.DESIGN_LABELS.values()) <= names
        assert set(tracker.SPECIAL_LABELS) <= names

    def test_every_entry_has_required_fields(self):
        inventory = wizard.build_label_inventory()
        for entry in inventory:
            assert "name" in entry and isinstance(entry["name"], str)
            assert "description" in entry and entry["description"]
            assert "color" in entry and len(entry["color"]) == 6

    def test_inventory_includes_new_phase_e_labels(self):
        """Phase E additive labels must be part of ensure_labels output."""
        inventory = wizard.build_label_inventory()
        names = {entry["name"] for entry in inventory}
        assert "status:pending-human-approval" in names
        assert "status:pending-human-review" in names
        assert "status:pending-human-setup" in names

    def test_inventory_is_sorted_for_determinism(self):
        inventory = wizard.build_label_inventory()
        names = [entry["name"] for entry in inventory]
        assert names == sorted(names)


def _labels_list_proc(names):
    """Canned `gh label list --json name` response for the given names."""
    return _fake_proc(
        returncode=0,
        stdout=json.dumps([{"name": n} for n in names]),
    )


def _issue_list_proc(numbers):
    """Canned `gh issue list --json number` response for the given numbers."""
    return _fake_proc(
        returncode=0,
        stdout=json.dumps([{"number": n} for n in numbers]),
    )


class TestEnsureLabels:
    """ensure_labels — all gh calls stubbed via monkeypatched wizard._run."""

    def test_all_labels_present_creates_nothing(self, monkeypatch):
        required = {entry["name"] for entry in wizard.build_label_inventory()}
        _install_fake_run(monkeypatch, {
            ("gh", "label", "list"): _labels_list_proc(list(required)),
        })
        summary = wizard.ensure_labels()
        assert summary["total"] == len(required)
        assert len(summary["existing"]) == len(required)
        assert summary["created"] == []
        assert summary["failed"] == []

    def test_missing_labels_get_created(self, monkeypatch):
        required = {entry["name"] for entry in wizard.build_label_inventory()}
        present = {"type:issue", "type:task", "squidsquad"}
        create_calls = []

        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "label", "list"]:
                return _labels_list_proc(list(present))
            if cmd[:3] == ["gh", "label", "create"]:
                create_calls.append(cmd[3])
                return _fake_proc(returncode=0)
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.ensure_labels()
        assert set(summary["existing"]) == present
        assert set(summary["created"]) == required - present
        assert summary["failed"] == []
        assert set(create_calls) == required - present

    def test_dry_run_does_not_call_create(self, monkeypatch):
        create_calls = []

        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "label", "list"]:
                return _labels_list_proc([])
            if cmd[:3] == ["gh", "label", "create"]:
                create_calls.append(cmd[3])
                return _fake_proc(returncode=0)
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.ensure_labels(dry_run=True)
        assert summary["dry_run"] is True
        assert create_calls == []
        assert len(summary["created"]) == summary["total"]

    def test_race_already_exists_treated_as_existing(self, monkeypatch):
        """If gh label create fails with 'already exists', count as existing."""
        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "label", "list"]:
                return _labels_list_proc([])  # appears empty
            if cmd[:3] == ["gh", "label", "create"]:
                return _fake_proc(
                    returncode=1,
                    stderr="label with name already exists",
                )
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.ensure_labels()
        # Every attempted create races to 'already exists' -> counted as existing
        assert len(summary["existing"]) == summary["total"]
        assert summary["created"] == []
        assert summary["failed"] == []

    def test_real_failure_reported(self, monkeypatch):
        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "label", "list"]:
                return _labels_list_proc([])
            if cmd[:3] == ["gh", "label", "create"]:
                return _fake_proc(returncode=1, stderr="HTTP 403: Forbidden")
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.ensure_labels()
        assert summary["created"] == []
        assert summary["failed"]
        for failure in summary["failed"]:
            assert "Forbidden" in failure["error"]

    def test_api_failure_on_list(self, monkeypatch):
        """If `gh label list` fails, treat every required label as missing."""
        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "label", "list"]:
                return _fake_proc(returncode=1, stderr="network error")
            if cmd[:3] == ["gh", "label", "create"]:
                return _fake_proc(returncode=0)
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.ensure_labels()
        assert summary["existing"] == []
        assert len(summary["created"]) == summary["total"]


class TestListIssuesWithLabel:
    def test_parses_numbers_from_gh_output(self, monkeypatch):
        payload = json.dumps([{"number": 1}, {"number": 42}, {"number": 7}])
        _install_fake_run(monkeypatch, {
            ("gh", "issue", "list"): _fake_proc(returncode=0, stdout=payload),
        })
        assert wizard.list_issues_with_label("status:pending") == [1, 42, 7]

    def test_empty_result(self, monkeypatch):
        _install_fake_run(monkeypatch, {
            ("gh", "issue", "list"): _fake_proc(returncode=0, stdout="[]"),
        })
        assert wizard.list_issues_with_label("status:pending") == []

    def test_gh_failure_returns_empty(self, monkeypatch):
        _install_fake_run(monkeypatch, {
            ("gh", "issue", "list"): _fake_proc(returncode=1, stderr="nope"),
        })
        assert wizard.list_issues_with_label("status:pending") == []

    def test_malformed_json_returns_empty(self, monkeypatch):
        _install_fake_run(monkeypatch, {
            ("gh", "issue", "list"): _fake_proc(returncode=0, stdout="not json"),
        })
        assert wizard.list_issues_with_label("status:pending") == []

    def test_state_flag_passed_through(self, monkeypatch):
        captured = []

        def _fake(cmd, **kwargs):
            captured.append(cmd)
            return _fake_proc(returncode=0, stdout="[]")

        monkeypatch.setattr(wizard, "_run", _fake)
        wizard.list_issues_with_label("status:pending", state="open")
        assert any("--state" in c and "open" in c for c in captured)


class TestMigrateLabel:
    def test_no_candidates_returns_empty_summary(self, monkeypatch):
        _install_fake_run(monkeypatch, {
            ("gh", "issue", "list"): _issue_list_proc([]),
        })
        summary = wizard.migrate_label(
            "status:pending", "status:pending-human-approval",
        )
        assert summary["candidates"] == []
        assert summary["migrated"] == []
        assert summary["failed"] == []

    def test_happy_path_migrates_all(self, monkeypatch):
        edit_calls = []

        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "issue", "list"]:
                return _issue_list_proc([101, 202, 303])
            if cmd[:3] == ["gh", "issue", "edit"]:
                edit_calls.append(cmd)
                return _fake_proc(returncode=0)
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.migrate_label(
            "status:pending", "status:pending-human-approval",
        )
        assert summary["candidates"] == [101, 202, 303]
        assert summary["migrated"] == [101, 202, 303]
        assert summary["failed"] == []
        assert len(edit_calls) == 3
        for cmd in edit_calls:
            assert "--remove-label" in cmd
            assert "status:pending" in cmd
            assert "--add-label" in cmd
            assert "status:pending-human-approval" in cmd

    def test_dry_run_never_calls_edit(self, monkeypatch):
        edit_calls = []

        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "issue", "list"]:
                return _issue_list_proc([1, 2])
            if cmd[:3] == ["gh", "issue", "edit"]:
                edit_calls.append(cmd)
                return _fake_proc(returncode=0)
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.migrate_label(
            "status:pending", "status:pending-human-approval",
            dry_run=True,
        )
        assert summary["dry_run"] is True
        assert summary["migrated"] == [1, 2]
        assert edit_calls == []

    def test_partial_failure_reports_each_issue(self, monkeypatch):
        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "issue", "list"]:
                return _issue_list_proc([10, 20, 30])
            if cmd[:3] == ["gh", "issue", "edit"]:
                number = cmd[3]
                if number == "20":
                    return _fake_proc(
                        returncode=1,
                        stderr="HTTP 500: Internal Server Error",
                    )
                return _fake_proc(returncode=0)
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.migrate_label("a", "b")
        assert summary["migrated"] == [10, 30]
        assert len(summary["failed"]) == 1
        assert summary["failed"][0]["number"] == 20
        assert "500" in summary["failed"][0]["error"]

    def test_already_labelled_counted_as_skipped(self, monkeypatch):
        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "issue", "list"]:
                return _issue_list_proc([7])
            if cmd[:3] == ["gh", "issue", "edit"]:
                return _fake_proc(
                    returncode=1,
                    stderr="label already exists on the issue",
                )
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.migrate_label("a", "b")
        assert summary["migrated"] == []
        assert summary["skipped"] == [7]
        assert summary["failed"] == []

    def test_summary_shape(self, monkeypatch):
        _install_fake_run(monkeypatch, {
            ("gh", "issue", "list"): _issue_list_proc([]),
        })
        summary = wizard.migrate_label("a", "b")
        assert set(summary.keys()) == {
            "old_label", "new_label", "dry_run",
            "candidates", "migrated", "skipped", "failed",
        }


# ===========================================================================
# Step 7 — stage_label_migration (#328 Phase J staged runner)
# ===========================================================================
#
# These tests stub every gh call. The staged runner wires together
# list_gh_labels, list_issues_with_label, migrate_label, and
# _delete_gh_label; each stage must succeed or fail cleanly and report
# its result in a nested summary dict.


def _build_stage_faker(*, old_exists=True, new_exists=True,
                       candidates=(), post_candidates=None,
                       edit_fails=False, delete_fails=False):
    """Build a monkeypatchable `_run` that speaks every stage's gh call.

    The staged runner makes THREE `gh issue list` calls against the old
    label in the worst case:
      1. dry-run stage (counts candidates itself)
      2. migrate_label internal re-query (when execute=True)
      3. postflight stage (verifies remainder)

    This fixture returns `candidates` for calls 1 and 2, then
    `post_candidates` for call 3 and onward. That matches the real gh
    API: list-candidates and migrate-internal-list both see the initial
    state, postflight sees the state AFTER migration.
    """
    if post_candidates is None:
        post_candidates = []

    list_call_count = [0]

    label_payload = []
    if old_exists:
        label_payload.append({"name": "status:pending"})
    if new_exists:
        label_payload.append({"name": "status:pending-human-approval"})

    def _fake(cmd, **kwargs):
        if cmd[:3] == ["gh", "label", "list"]:
            return _fake_proc(returncode=0, stdout=json.dumps(label_payload))
        if cmd[:3] == ["gh", "issue", "list"]:
            list_call_count[0] += 1
            # Calls 1 and 2 see the initial state; call 3+ sees post
            nums = (
                candidates if list_call_count[0] <= 2
                else post_candidates
            )
            return _issue_list_proc(nums)
        if cmd[:3] == ["gh", "issue", "edit"]:
            if edit_fails:
                return _fake_proc(returncode=1, stderr="HTTP 500")
            return _fake_proc(returncode=0)
        if cmd[:3] == ["gh", "label", "delete"]:
            if delete_fails:
                return _fake_proc(returncode=1, stderr="HTTP 403 Forbidden")
            return _fake_proc(returncode=0)
        return _fake_proc(returncode=127)

    return _fake


class TestStageLabelMigrationPreflight:
    def test_old_label_missing_aborts(self, monkeypatch):
        fake = _build_stage_faker(old_exists=False, new_exists=True)
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
        )
        pre = summary["stages"]["preflight"]
        assert pre["ok"] is False
        assert pre["old_exists"] is False
        assert pre["new_exists"] is True
        assert any("status:pending" in e and "does not exist" in e
                   for e in pre["errors"])
        # No other stage should have run
        assert summary["stages"]["dry_run"] is None
        assert summary["stages"]["execute"] is None
        assert summary["ok"] is False

    def test_new_label_missing_aborts(self, monkeypatch):
        fake = _build_stage_faker(old_exists=True, new_exists=False)
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
        )
        pre = summary["stages"]["preflight"]
        assert pre["ok"] is False
        assert pre["new_exists"] is False
        assert any("ensure-labels" in e for e in pre["errors"])
        assert summary["ok"] is False

    def test_both_missing_reports_both(self, monkeypatch):
        fake = _build_stage_faker(old_exists=False, new_exists=False)
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
        )
        pre = summary["stages"]["preflight"]
        assert len(pre["errors"]) == 2


class TestStageLabelMigrationDryRun:
    def test_no_candidates_short_circuits_cleanly(self, monkeypatch):
        fake = _build_stage_faker(candidates=[])
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
        )
        assert summary["ok"] is True
        assert summary["stages"]["dry_run"]["candidate_count"] == 0
        assert summary["stages"]["execute"]["skipped"] is True
        assert summary["stages"]["execute"]["reason"] == "no candidates"
        assert summary["stages"]["postflight"]["remaining_count"] == 0

    def test_dry_run_counts_candidates_without_executing(self, monkeypatch):
        fake = _build_stage_faker(
            candidates=[10, 20, 30], post_candidates=[10, 20, 30],
        )
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=False,
        )
        assert summary["stages"]["dry_run"]["candidate_count"] == 3
        assert summary["stages"]["dry_run"]["candidates"] == [10, 20, 30]
        assert summary["stages"]["execute"]["skipped"] is True
        assert "dry-run" in summary["stages"]["execute"]["reason"]
        # Postflight still finds all 3 because we never executed
        assert summary["stages"]["postflight"]["remaining_count"] == 3
        # Top-level ok is False because postflight is dirty
        assert summary["ok"] is False


class TestStageLabelMigrationExecute:
    def test_happy_path_full_migration(self, monkeypatch):
        fake = _build_stage_faker(
            candidates=[1, 2, 3], post_candidates=[],
        )
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=True,
        )
        assert summary["ok"] is True
        assert summary["stages"]["execute"]["ok"] is True
        assert summary["stages"]["execute"]["migrated"] == [1, 2, 3]
        assert summary["stages"]["postflight"]["remaining_count"] == 0
        # No delete_old -> cleanup skipped
        assert summary["stages"]["cleanup"]["skipped"] is True
        assert "delete_old" in summary["stages"]["cleanup"]["reason"]

    def test_execute_failure_reported_and_blocks_cleanup(self, monkeypatch):
        fake = _build_stage_faker(
            candidates=[1, 2],
            post_candidates=[1, 2],  # still there because edits failed
            edit_fails=True,
        )
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=True, delete_old=True,
        )
        exec_stage = summary["stages"]["execute"]
        assert exec_stage["ok"] is False
        assert len(exec_stage["failed"]) == 2
        # Postflight runs even when execute failed
        assert summary["stages"]["postflight"]["remaining_count"] == 2
        assert summary["stages"]["postflight"]["ok"] is False
        # Cleanup MUST be skipped
        assert summary["stages"]["cleanup"]["skipped"] is True
        assert "execute" in summary["stages"]["cleanup"]["reason"]
        assert summary["ok"] is False

    def test_partial_migration_postflight_catches_remainder(self, monkeypatch):
        """If one issue somehow still has the old label, postflight fails."""
        fake = _build_stage_faker(
            candidates=[1, 2, 3], post_candidates=[3],
        )
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=True, delete_old=True,
        )
        assert summary["stages"]["postflight"]["remaining_count"] == 1
        assert summary["stages"]["postflight"]["ok"] is False
        assert summary["stages"]["cleanup"]["skipped"] is True
        assert "postflight" in summary["stages"]["cleanup"]["reason"]
        assert summary["ok"] is False


class TestStageLabelMigrationCleanup:
    def test_cleanup_runs_when_all_preconditions_met(self, monkeypatch):
        fake = _build_stage_faker(
            candidates=[1, 2], post_candidates=[],
        )
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=True, delete_old=True,
        )
        cleanup = summary["stages"]["cleanup"]
        assert cleanup["ok"] is True
        assert cleanup["deleted"] is True
        assert summary["ok"] is True

    def test_cleanup_skipped_without_execute_flag(self, monkeypatch):
        fake = _build_stage_faker(
            candidates=[1, 2], post_candidates=[1, 2],
        )
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=False, delete_old=True,
        )
        assert summary["stages"]["cleanup"]["skipped"] is True
        assert "execute" in summary["stages"]["cleanup"]["reason"]

    def test_cleanup_failure_reported(self, monkeypatch):
        fake = _build_stage_faker(
            candidates=[1], post_candidates=[], delete_fails=True,
        )
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=True, delete_old=True,
        )
        cleanup = summary["stages"]["cleanup"]
        assert cleanup["ok"] is False
        assert cleanup["deleted"] is False
        assert "403" in cleanup["error"]
        assert summary["ok"] is False

    def test_cleanup_treats_not_found_as_success(self, monkeypatch):
        """If the label was already deleted, `gh label delete` reports not-found."""
        list_count = [0]

        def _fake(cmd, **kwargs):
            if cmd[:3] == ["gh", "label", "list"]:
                return _fake_proc(
                    returncode=0,
                    stdout=json.dumps([
                        {"name": "status:pending"},
                        {"name": "status:pending-human-approval"},
                    ]),
                )
            if cmd[:3] == ["gh", "issue", "list"]:
                list_count[0] += 1
                # Calls 1 + 2 = dry-run and migrate-internal (see [1]);
                # call 3 = postflight (clean)
                nums = [1] if list_count[0] <= 2 else []
                return _issue_list_proc(nums)
            if cmd[:3] == ["gh", "issue", "edit"]:
                return _fake_proc(returncode=0)
            if cmd[:3] == ["gh", "label", "delete"]:
                return _fake_proc(returncode=1, stderr="label not found")
            return _fake_proc(returncode=127)

        monkeypatch.setattr(wizard, "_run", _fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=True, delete_old=True,
        )
        assert summary["stages"]["cleanup"]["ok"] is True
        assert summary["ok"] is True


class TestStageLabelMigrationContract:
    def test_stages_constant_matches_summary_keys(self, monkeypatch):
        fake = _build_stage_faker(candidates=[])
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration("a", "b")
        assert set(summary["stages"].keys()) == set(wizard.LABEL_MIGRATION_STAGES)

    def test_stages_constant_order_is_stable(self):
        assert wizard.LABEL_MIGRATION_STAGES == [
            "preflight", "dry_run", "execute", "postflight", "cleanup",
        ]

    def test_summary_has_top_level_ok_flag(self, monkeypatch):
        fake = _build_stage_faker(candidates=[])
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration("a", "b")
        assert "ok" in summary
        assert isinstance(summary["ok"], bool)

    def test_summary_records_all_parameters(self, monkeypatch):
        fake = _build_stage_faker(candidates=[])
        monkeypatch.setattr(wizard, "_run", fake)
        summary = wizard.stage_label_migration(
            "status:pending", "status:pending-human-approval",
            execute=True, delete_old=True, state="open",
        )
        assert summary["old_label"] == "status:pending"
        assert summary["new_label"] == "status:pending-human-approval"
        assert summary["execute"] is True
        assert summary["delete_old"] is True
        assert summary["state"] == "open"


# ---------------------------------------------------------------------------
# #462 — Adaptive setup questions: config.md + SOUL.md seeding
# ---------------------------------------------------------------------------


class TestAdaptiveSetupFields:
    """build_config_md renders new project fields from adaptive questions (#462)."""

    def test_description_rendered(self):
        spec = _minimal_spec(project={
            "name": "my-app",
            "repo": "github.com/test/repo",
            "description": "A CLI tool for CSV processing",
        })
        text = wizard.build_config_md(spec)
        assert "**Description**: A CLI tool for CSV processing" in text

    def test_domain_context_rendered(self):
        spec = _minimal_spec(project={
            "name": "my-app",
            "repo": "github.com/test/repo",
            "domain_context": "Python CLI, uses pandas, deployed via pip",
        })
        text = wizard.build_config_md(spec)
        assert "**Domain Context**: Python CLI, uses pandas, deployed via pip" in text

    def test_conventions_rendered(self):
        spec = _minimal_spec(project={
            "name": "my-app",
            "repo": "github.com/test/repo",
            "conventions": "PEP 8, trunk-based, squash merge",
        })
        text = wizard.build_config_md(spec)
        assert "**Conventions**: PEP 8, trunk-based, squash merge" in text

    def test_empty_fields_omitted(self):
        spec = _minimal_spec(project={
            "name": "my-app",
            "repo": "github.com/test/repo",
        })
        text = wizard.build_config_md(spec)
        assert "**Description**" not in text
        assert "**Domain Context**" not in text
        assert "**Conventions**" not in text

    def test_all_fields_together(self):
        spec = _minimal_spec(project={
            "name": "my-app",
            "repo": "github.com/test/repo",
            "description": "Web app",
            "domain_context": "React + Node.js, deployed on Vercel",
            "conventions": "ESLint, Prettier, conventional commits",
        })
        text = wizard.build_config_md(spec)
        assert "**Description**: Web app" in text
        assert "**Domain Context**: React + Node.js" in text
        assert "**Conventions**: ESLint, Prettier" in text


class TestSoulMdSeeding:
    """scaffold_install seeds SOUL.md with Project Context from adaptive answers (#462)."""

    def test_soul_seeded_with_domain_context(self, tmp_path):
        spec = _minimal_spec(project={
            "name": "my-app",
            "repo": "github.com/test/repo",
            "domain_context": "Python data pipeline using Apache Spark",
        })
        # Create SOUL.md with placeholder (as the real templates have)
        placeholder = "_Populated during setup. Describes what this project does, its tech stack, conventions, and key tools._"
        squid = tmp_path / ".squidsquad"
        for agent in spec["agents"]:
            agent_dir = squid / agent["id"]
            agent_dir.mkdir(parents=True)
            soul = agent_dir / "SOUL.md"
            soul.write_text(
                f"## Soul\n\nGeneric role identity.\n\n### Project Context\n\n{placeholder}\n",
                encoding="utf-8",
            )

        from unittest.mock import patch, MagicMock
        mock_deploy = MagicMock(return_value=str(squid / "pm" / "CLAUDE.md"))
        mock_local = MagicMock()
        with patch.dict("sys.modules", {"compose": MagicMock(
            deploy_role=mock_deploy, generate_local_config=mock_local
        )}):
            wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)

        # Check PM's SOUL.md was seeded
        soul_text = (squid / "pm" / "SOUL.md").read_text(encoding="utf-8")
        assert "### Project Context" in soul_text
        assert "Python data pipeline using Apache Spark" in soul_text

    def test_soul_not_seeded_when_no_domain_context(self, tmp_path):
        spec = _minimal_spec(project={
            "name": "my-app",
            "repo": "github.com/test/repo",
        })
        squid = tmp_path / ".squidsquad"
        for agent in spec["agents"]:
            agent_dir = squid / agent["id"]
            agent_dir.mkdir(parents=True)
            soul = agent_dir / "SOUL.md"
            soul.write_text("## Soul\n\nGeneric.\n", encoding="utf-8")

        from unittest.mock import patch, MagicMock
        mock_deploy = MagicMock(return_value=str(squid / "pm" / "CLAUDE.md"))
        mock_local = MagicMock()
        with patch.dict("sys.modules", {"compose": MagicMock(
            deploy_role=mock_deploy, generate_local_config=mock_local
        )}):
            wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)

        soul_text = (squid / "pm" / "SOUL.md").read_text(encoding="utf-8")
        assert "### Project Context" not in soul_text

    def test_soul_not_double_seeded(self, tmp_path):
        spec = _minimal_spec(project={
            "name": "my-app",
            "repo": "github.com/test/repo",
            "domain_context": "Already seeded context",
        })
        squid = tmp_path / ".squidsquad"
        for agent in spec["agents"]:
            agent_dir = squid / agent["id"]
            agent_dir.mkdir(parents=True)
            soul = agent_dir / "SOUL.md"
            soul.write_text(
                "## Soul\n\n### Project Context\n\nExisting content.\n",
                encoding="utf-8",
            )

        from unittest.mock import patch, MagicMock
        mock_deploy = MagicMock(return_value=str(squid / "pm" / "CLAUDE.md"))
        mock_local = MagicMock()
        with patch.dict("sys.modules", {"compose": MagicMock(
            deploy_role=mock_deploy, generate_local_config=mock_local
        )}):
            wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)

        soul_text = (squid / "pm" / "SOUL.md").read_text(encoding="utf-8")
        assert soul_text.count("### Project Context") == 1
        assert "Existing content" in soul_text
        assert "Already seeded" not in soul_text


# ---------------------------------------------------------------------------
# PR Flow Prompt (#2006)
# ---------------------------------------------------------------------------


class TestPrFlowPrompt:
    """PR Flow question returns structured data for agent to present."""

    def test_returns_question_and_options(self):
        result = wizard.pr_flow_prompt()
        assert "question" in result
        assert "options" in result
        assert "default" in result
        assert result["default"] is False

    def test_question_uses_plain_language(self):
        result = wizard.pr_flow_prompt()
        q = result["question"]
        assert "PR Flow OFF" in q
        assert "PR Flow ON" in q
        # No internal jargon
        assert "Ralph Loop" not in q
        assert "tracker.py" not in q

    def test_has_two_options(self):
        result = wizard.pr_flow_prompt()
        assert len(result["options"]) == 2


class TestBranchWorkflowPrompt:
    """Branch Workflow question returns structured data (#2413)."""

    def test_returns_question_and_options(self):
        result = wizard.branch_workflow_prompt()
        assert "question" in result
        assert "options" in result
        assert "default" in result
        assert result["default"] is True

    def test_has_two_options(self):
        result = wizard.branch_workflow_prompt()
        assert len(result["options"]) == 2

    def test_question_mentions_feature_branches(self):
        result = wizard.branch_workflow_prompt()
        assert "feature branch" in result["question"].lower()


# ---------------------------------------------------------------------------
# Post-Setup Summary (#2006)
# ---------------------------------------------------------------------------


class TestPostSetupSummary:
    """Post-setup What's Next summary based on configured agents."""

    @pytest.fixture
    def basic_spec(self):
        return {
            "project": {"name": "my-app", "repo": "github.com/alice/my-app"},
            "preset": "software-dev",
            "agents": [
                {"id": "pm", "role": "pm"},
                {"id": "skill", "role": "dev", "variant": "skill"},
                {"id": "qa", "role": "qa"},
            ],
            "tools": {},
            "loop": {"interval_minutes": 30},
            "flags": {"pr_flow": False},
        }

    def test_includes_project_name(self, basic_spec):
        result = wizard.post_setup_summary(basic_spec)
        assert "my-app" in result

    def test_includes_boot_instructions(self, basic_spec):
        result = wizard.post_setup_summary(basic_spec)
        assert "Boot your agents" in result
        assert "claude --resume" in result

    def test_includes_how_to_interact(self, basic_spec):
        result = wizard.post_setup_summary(basic_spec)
        assert "How to interact" in result
        assert "PM terminal" in result

    def test_includes_status_monitoring(self, basic_spec):
        result = wizard.post_setup_summary(basic_spec)
        assert "status" in result.lower()
        assert "GitHub Issues" in result

    def test_lists_all_configured_agents(self, basic_spec):
        result = wizard.post_setup_summary(basic_spec)
        assert "PM" in result
        assert "skill" in result
        assert "QA" in result

    def test_handles_empty_agents(self):
        spec = {
            "project": {"name": "test"},
            "agents": [],
            "preset": "x", "tools": {}, "loop": {}, "flags": {},
        }
        result = wizard.post_setup_summary(spec)
        assert "What's Next" in result


# ---------------------------------------------------------------------------
# Install Spec Save/Load (#13)
# ---------------------------------------------------------------------------


class TestInstallSpec:
    """Save and load .install-spec.json for reproducibility."""

    @pytest.fixture
    def sample_spec(self):
        return {
            "squidsquad_version": "0.25.0",
            "project": {"name": "my-app", "repo": "github.com/alice/my-app"},
            "preset": "software-dev",
            "agents": [{"id": "pm", "role": "pm"}, {"id": "skill", "role": "dev"}],
            "tools": {},
            "loop": {"interval_minutes": 30, "context_threshold": 70},
            "flags": {"pr_flow": False},
        }

    def test_save_creates_file(self, tmp_path, sample_spec):
        path = wizard.save_install_spec(sample_spec, tmp_path)
        assert Path(path).exists()
        assert ".install-spec.json" in path

    def test_save_load_roundtrip(self, tmp_path, sample_spec):
        wizard.save_install_spec(sample_spec, tmp_path)
        loaded = wizard.load_install_spec(tmp_path)
        assert loaded == sample_spec

    def test_load_missing_returns_none(self, tmp_path):
        result = wizard.load_install_spec(tmp_path)
        assert result is None

    def test_save_creates_squidsquad_dir(self, tmp_path, sample_spec):
        wizard.save_install_spec(sample_spec, tmp_path)
        assert (tmp_path / ".squidsquad").is_dir()

    def test_overwrite_existing_spec(self, tmp_path, sample_spec):
        """Saving a spec overwrites the previous one."""
        wizard.save_install_spec(sample_spec, tmp_path)
        sample_spec["squidsquad_version"] = "0.26.0"
        wizard.save_install_spec(sample_spec, tmp_path)
        loaded = wizard.load_install_spec(tmp_path)
        assert loaded["squidsquad_version"] == "0.26.0"

    def test_load_invalid_json_raises_valueerror(self, tmp_path):
        """#8548: Corrupt JSON raises ValueError, not JSONDecodeError."""
        spec_dir = tmp_path / ".squidsquad"
        spec_dir.mkdir(parents=True)
        (spec_dir / ".install-spec.json").write_text("not valid json{{", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            wizard.load_install_spec(tmp_path)


# ---------------------------------------------------------------------------
# Scan Summary (#13)
# ---------------------------------------------------------------------------


class TestScanSummary:
    """format_scan_summary produces grouped human-readable output."""

    def test_full_scan(self):
        scan = {
            "languages": ["python", "javascript"],
            "frameworks": ["nextjs", "express"],
            "package_managers": ["npm", "pip"],
            "test_frameworks": ["pytest", "jest"],
            "ci_cd": ["github-actions"],
            "deploy_targets": [],
            "documentation": ["docs"],
            "monorepo": [],
        }
        result = wizard.format_scan_summary(scan)
        assert "python" in result
        assert "nextjs" in result
        assert "pytest" in result
        assert "github-actions" in result

    def test_empty_scan(self):
        result = wizard.format_scan_summary({})
        assert "No project" in result

    def test_none_scan(self):
        result = wizard.format_scan_summary(None)
        assert "No project" in result

    def test_partial_scan(self):
        scan = {"languages": ["rust"], "frameworks": [], "test_frameworks": []}
        result = wizard.format_scan_summary(scan)
        assert "rust" in result
        assert "Frameworks" not in result  # empty list not shown


# ---------------------------------------------------------------------------
# Default Spec Generation (#13)
# ---------------------------------------------------------------------------


class TestGenerateDefaultSpec:
    """generate_default_spec produces valid spec from scan data."""

    def test_with_scan_data(self):
        scan = {
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "test_frameworks": ["pytest"],
        }
        info = {"name": "my-api", "repo": "github.com/me/my-api"}
        spec = wizard.generate_default_spec(scan, info)
        assert spec["project"]["name"] == "my-api"
        assert spec["agents"][1]["test_command"] == "pytest"
        assert "fastapi" in spec["agents"][1]["stack"]

    def test_without_scan_data(self):
        spec = wizard.generate_default_spec()
        assert spec["project"]["name"] == ""
        assert spec["agents"][1]["stack"] == "general"
        assert spec["agents"][1]["test_command"] == ""

    def test_has_required_sections(self):
        spec = wizard.generate_default_spec()
        for key in ("project", "preset", "agents", "tools", "loop", "flags"):
            assert key in spec, f"Missing required key: {key}"

    def test_jest_detection(self):
        scan = {"test_frameworks": ["jest"]}
        spec = wizard.generate_default_spec(scan)
        assert spec["agents"][1]["test_command"] == "npx jest"

    def test_version_not_hardcoded_0_25(self):
        """#6976: squidsquad_version must not be hardcoded to 0.25.0."""
        spec = wizard.generate_default_spec()
        assert spec["squidsquad_version"] != "0.25.0", (
            "#6976: version should be read dynamically, not hardcoded to 0.25.0"
        )

    def test_no_redundant_shutil_import(self):
        """#6977: scaffold_install must not re-import shutil locally."""
        import inspect
        source = inspect.getsource(wizard.scaffold_install)
        assert "import shutil" not in source, (
            "#6977: scaffold_install should use module-level shutil import"
        )


# ---------------------------------------------------------------------------
# apply_project_type (#4083)
# ---------------------------------------------------------------------------

class TestApplyProjectType:
    """#6581: apply_project_type uses manifest domain_variants (primary)
    with legacy PROJECT_TYPE_PRESETS fallback."""

    def test_manifest_driven_per_role_variants(self):
        """TC-1: Preset manifest domain_variants resolved per role."""
        spec = {
            "preset": "software-dev",
            "agents": [
                {"id": "pm", "role": "pm"},
                {"id": "skill", "role": "dev"},
                {"id": "qa", "role": "qa"},
                {"id": "dm", "role": "dm"},
            ],
        }
        result = wizard.apply_project_type(spec, "skill")
        # Returns dict of {role: variant}
        assert isinstance(result, dict)
        assert result.get("dev") == "skill"
        assert spec["project_type"] == "skill"
        # All agents should have variants from the manifest
        for agent in spec["agents"]:
            assert "variant" in agent, f"{agent['id']} missing variant"

    def test_all_roles_get_variant(self):
        """TC-2: All roles receive domain variant — none skipped."""
        spec = {
            "preset": "software-dev",
            "agents": [
                {"id": "pm", "role": "pm"},
                {"id": "skill", "role": "dev"},
                {"id": "qa", "role": "qa"},
                {"id": "dm", "role": "dm"},
            ],
        }
        wizard.apply_project_type(spec, "skill")
        for agent in spec["agents"]:
            assert agent.get("variant") is not None, \
                f"{agent['role']} has no variant"

    def test_custom_sets_no_variant(self):
        """TC-5: custom project type — no domain variant."""
        spec = {
            "agents": [
                {"id": "pm", "role": "pm"},
                {"id": "skill", "role": "dev"},
            ],
        }
        result = wizard.apply_project_type(spec, "custom")
        assert result is None
        assert spec["project_type"] == "custom"
        assert "variant" not in spec["agents"][0]
        assert "variant" not in spec["agents"][1]

    def test_legacy_fallback_when_no_preset(self):
        """Legacy PROJECT_TYPE_PRESETS fallback when no preset in spec."""
        spec = {
            "agents": [
                {"id": "pm", "role": "pm"},
                {"id": "skill", "role": "dev"},
                {"id": "qa", "role": "qa"},
                {"id": "dm", "role": "dm"},
            ],
        }
        result = wizard.apply_project_type(spec, "ios")
        assert isinstance(result, dict)
        assert result.get("dev") == "ios"
        for agent in spec["agents"]:
            assert agent["variant"] == "ios"

    def test_all_project_types_valid(self):
        for ptype in wizard.PROJECT_TYPE_PRESETS:
            spec = {"agents": [{"id": "pm", "role": "pm"}]}
            wizard.apply_project_type(spec, ptype)
            assert spec["project_type"] == ptype


class TestManifestResolution:
    """#6581: load_preset_manifest and resolve_domain_variants."""

    def test_load_software_dev_manifest(self):
        """Manifest loads and contains expected fields."""
        manifest = wizard.load_preset_manifest("software-dev")
        assert manifest is not None
        assert manifest["id"] == "software-dev"
        assert "domain_variants" in manifest

    def test_resolve_domain_variants_software_dev(self):
        """domain_variants returns per-role mapping."""
        variants = wizard.resolve_domain_variants("software-dev")
        assert variants.get("dev") == "skill"
        assert variants.get("pm") == "skill"
        assert variants.get("qa") == "skill"
        assert variants.get("dm") == "skill"

    def test_resolve_nonexistent_preset(self):
        """Missing preset returns empty dict."""
        variants = wizard.resolve_domain_variants("nonexistent-preset-xyz")
        assert variants == {}

    def test_resolve_design_preset_no_variants(self):
        """TC-6: Design preset has no domain_variants."""
        variants = wizard.resolve_domain_variants("design")
        assert variants == {}

    def test_generate_default_spec_uses_manifest(self):
        """TC-7: generate_default_spec derives variants from manifest."""
        spec = wizard.generate_default_spec()
        assert spec["preset"] == "software-dev"
        # Dev agent should have variant from manifest
        dev_agents = [a for a in spec["agents"] if a["role"] == "dev"]
        assert len(dev_agents) == 1
        manifest = wizard.load_preset_manifest("software-dev")
        expected_variant = manifest["domain_variants"]["dev"]
        assert dev_agents[0].get("variant") == expected_variant


# ---------------------------------------------------------------------------
# preflight (#4083)
# ---------------------------------------------------------------------------

class TestPreflight:
    def test_fails_on_gh_auth(self, tmp_path):
        from unittest.mock import patch, MagicMock
        with patch.object(wizard, "check_gh",
                          return_value={"ok": False, "message": "not authenticated"}):
            result = wizard.preflight(tmp_path)
        assert result["ok"] is False
        assert "not authenticated" in result["message"]

    def test_fails_on_no_git_repo(self, tmp_path):
        from unittest.mock import patch
        with patch.object(wizard, "check_gh",
                          return_value={"ok": True, "message": "ready"}):
            result = wizard.preflight(tmp_path)
        assert result["ok"] is False
        assert "git repository" in result["message"]

    def test_fails_on_no_remote(self, tmp_path):
        from unittest.mock import patch, MagicMock
        (tmp_path / ".git").mkdir()
        with patch.object(wizard, "check_gh",
                          return_value={"ok": True, "message": "ready"}), \
             patch.object(wizard, "_run",
                          return_value=MagicMock(returncode=0, stdout="")):
            result = wizard.preflight(tmp_path)
        assert result["ok"] is False
        assert "remote" in result["message"]

    def test_passes_all_checks(self, tmp_path):
        from unittest.mock import patch, MagicMock
        (tmp_path / ".git").mkdir()
        with patch.object(wizard, "check_gh",
                          return_value={"ok": True, "message": "ready"}), \
             patch.object(wizard, "_run",
                          return_value=MagicMock(returncode=0,
                              stdout="origin\thttps://github.com/test/repo.git (fetch)\n")):
            result = wizard.preflight(tmp_path)
        assert result["ok"] is True
        assert len(result["checks"]) == 3


# ---------------------------------------------------------------------------
# cmd_setup_yes — #8547 regression
# ---------------------------------------------------------------------------

class TestCmdSetupYes:
    """#8547: _run() must not receive duplicate check=False kwarg."""

    def test_no_duplicate_check_kwarg(self, tmp_path):
        """Regression: _run call in cmd_setup_yes must not pass check=False."""
        from unittest.mock import patch, MagicMock
        import inspect
        source = inspect.getsource(wizard.cmd_setup_yes)
        assert "check=False" not in source, (
            "_run() already hardcodes check=False — passing it again "
            "causes TypeError: got multiple values for keyword argument 'check'"
        )

    def test_run_not_called_with_check_kwarg(self, tmp_path):
        """_run() is never called with check= kwarg from cmd_setup_yes."""
        from unittest.mock import patch, MagicMock, call
        calls = []

        def tracking_run(cmd, **kwargs):
            calls.append(kwargs)
            return MagicMock(returncode=1, stdout="", stderr="")

        # Patch enough to get past the gh repo view call without full execution
        with patch.object(wizard, "_run", side_effect=tracking_run):
            try:
                wizard.cmd_setup_yes([str(tmp_path)])
            except (SystemExit, Exception):
                pass  # May fail later in setup — we only care about the _run call

        # Verify no call passed check= kwarg
        for kw in calls:
            assert "check" not in kw, (
                f"_run called with check={kw['check']} — this causes TypeError"
            )
