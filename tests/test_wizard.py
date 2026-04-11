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
        "loop": {"interval_minutes": 10, "context_threshold": 80},
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

    def test_designer_with_iteration_mode_and_setup(self):
        spec = _minimal_spec()
        spec["agents"] = [
            {
                "id": "designer",
                "alias": "designer",
                "role": "designer",
                "iteration_mode": "hitl",
                "setup": {"install_optional": "yes"},
            },
        ]
        text = wizard.build_config_md(spec)
        assert "- **designer**: designer" in text
        assert "  - role: designer" in text
        assert "  - iteration_mode: hitl" in text
        assert "  - setup:" in text
        assert "    - install_optional: yes" in text

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
        spec["tools"] = {"designer.tool": None}
        text = wizard.build_config_md(spec)
        assert "**designer.tool**: (unset" in text

    def test_empty_string_also_unset(self):
        spec = _minimal_spec()
        spec["tools"] = {"designer.tool": ""}
        text = wizard.build_config_md(spec)
        assert "**designer.tool**: (unset" in text

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
        assert "- **Context Threshold**: 80" in text


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
    """Regression test for TC-01 (full software-dev + be+fe + designer=yes)."""

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
                    "id": "designer",
                    "alias": "designer",
                    "role": "designer",
                    "iteration_mode": "hitl",
                    "setup": {"install_optional": "yes"},
                },
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
                "designer.tool": None,
                "dm.tool": "local_delivery",
            },
            "loop": {"interval_minutes": 10, "context_threshold": 80},
            "flags": {
                "pr_flow": False,
                "improvement_scan": True,
                "vault_remember": True,
                "diagnostics": True,
            },
        }
        text = wizard.build_config_md(spec)

        # All 6 agents present with correct shape
        assert "- **pm**: peggy" in text
        assert "- **designer**: designer" in text
        assert "  - iteration_mode: hitl" in text
        assert "- **be**: be" in text
        assert "- **fe**: fe" in text
        assert "- **qa**: qa" in text
        assert "- **dm**: dm" in text

        # Both tool entries match Q-new17 rules
        assert "**designer.tool**: (unset" in text
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
