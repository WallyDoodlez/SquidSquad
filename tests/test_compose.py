"""Tests for references/scripts/compose.py — composition engine."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def compose_env(tmp_path):
    """Set up a minimal compose environment in tmp_path."""
    # Create sub-skills directory
    sub_skills = tmp_path / "references" / "sub-skills"
    sub_skills.mkdir(parents=True)

    # Create common sub-skills
    common = sub_skills / "common"
    common.mkdir()
    (common / "context-pressure.md").write_text(
        "## Context Pressure\n\nCheck context pressure each cycle.",
        encoding="utf-8",
    )
    (common / "pull-latest.md").write_text(
        "### Step 1 — Pull Latest\n\nRun git pull.",
        encoding="utf-8",
    )

    # Create roles directory
    roles = tmp_path / "references" / "roles"
    dev_role = roles / "dev"
    dev_role.mkdir(parents=True)
    (dev_role / "instructions.md").write_text(
        "# Dev Agent\n\n"
        "{{runtime: souls/dev}}\n"
        "{{include: common/context-pressure}}\n"
        "{{include: common/pull-latest}}\n"
        "Role: [ROLE]\n"
        "Test: [ROLE_TEST_CMD]\n"
        "Interval: [INTERVAL]\n",
        encoding="utf-8",
    )
    (dev_role / "SOUL.md").write_text(
        "## Soul — Dev Agent\n\nYou are an engineer.",
        encoding="utf-8",
    )

    pm_role = roles / "pm"
    pm_role.mkdir(parents=True)
    (pm_role / "instructions.md").write_text(
        "# PM Agent\n\n"
        "{{include: common/context-pressure}}\n"
        "Active agents: [ACTIVE_AGENTS]\n"
        "E2E: [E2E_TEST_CMD]\n"
        "Interval: [INTERVAL]\n",
        encoding="utf-8",
    )

    # Create capabilities directory
    caps = sub_skills / "capabilities"
    caps.mkdir()
    test_cap = caps / "test-cap"
    test_cap.mkdir()
    (test_cap / "sub-skill.md").write_text(
        "## Test Capability\n\nDoes test things.",
        encoding="utf-8",
    )

    # Create templates directory
    templates = tmp_path / "references" / "templates"
    templates.mkdir(parents=True)
    (templates / "start-role.sh").write_text(
        "#!/bin/bash\nROLE={{ROLE}}\necho $ROLE",
        encoding="utf-8",
    )
    (templates / "start-role.ps1").write_text(
        "$Role = '{{ROLE}}'\nWrite-Host $Role",
        encoding="utf-8",
    )

    # Create .squidsquad directory
    ss = tmp_path / ".squidsquad"
    ss.mkdir()

    return tmp_path


# ---------------------------------------------------------------------------
# _resolve_includes / TestResolveIncludes retired in E6 #10685 Phase 3d.5
# along with the v1 compose_role chain. v2 path
# (v2_link_stage.emit_v2_linked → atomic_emit.assemble_and_emit) is the
# only compose pipeline post-cutover.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# _substitute_placeholders
# ---------------------------------------------------------------------------

class TestSubstitutePlaceholders:
    def test_dev_role_substitution(self):
        content = "Role: [ROLE], Upper: [ROLE_UPPER], Test: [ROLE_TEST_CMD], Interval: [INTERVAL]"
        with patch.object(compose, "_read_config_value", side_effect=lambda f: {
            "skill-tests": "python tests/run_tests.py",
            "dev-agents": "skill,be",
            "interval": "30",
        }.get(f, "")):
            result = compose._substitute_placeholders(content, "skill", "dev")
        assert "Role: skill" in result
        assert "Upper: SKILL" in result
        assert "Test: python tests/run_tests.py" in result
        assert "Interval: 30" in result

    def test_dev_role_no_test_cmd_fallback(self):
        content = "Test: [ROLE_TEST_CMD]"
        with patch.object(compose, "_read_config_value", return_value=""):
            result = compose._substitute_placeholders(content, "skill", "dev")
        assert 'echo "Skill repo -- no automated tests."' in result

    def test_non_dev_role_substitutes_role_placeholder(self):
        """[ROLE] is substituted for all roles (#2487 — universal substitution)."""
        content = "For dev: [ROLE], Active: [ACTIVE_AGENTS], E2E: [E2E_TEST_CMD], Interval: [INTERVAL]"
        with patch.object(compose, "_read_config_value", side_effect=lambda f: {
            # Post-6274.2: compose reads "workers" key (was "dev-agents") with
            # the dual-aware shim in config.py falling back to legacy.
            "workers": "skill,be",
            "e2e-tests": "npm test",
            "interval": "15",
        }.get(f, "")):
            result = compose._substitute_placeholders(content, "pm", "pm")
        # [ROLE] is now substituted for ALL roles (cycle-runner needs it)
        assert "[ROLE]" not in result
        assert "For dev: pm" in result
        assert "Active: skill,be" in result
        assert "E2E: npm test" in result
        assert "Interval: 15" in result

    def test_other_roles_computed(self):
        content = "Others: [OTHER_ROLES]"
        with patch.object(compose, "_read_config_value", side_effect=lambda f: {
            "skill-tests": "",
            # Post-6274.2: compose reads "workers" key (was "dev-agents").
            "workers": "skill,be,fe",
            "interval": "30",
        }.get(f, "")):
            result = compose._substitute_placeholders(content, "skill", "dev")
        assert "be" in result
        assert "fe" in result
        assert "skill" not in result.split("Others: ")[1]

    def test_role_class_alias_placeholders_singleton(self):
        """[PM_ALIAS]/[VERIFIER_ALIAS]/[DM_ALIAS] resolve from config (#11144 G10).

        Singleton install: aliases match canonical names (qa for verifier
        legacy key). Substituted for all roles — paths like
        `.squidsquad/[VERIFIER_ALIAS]/planning/` must resolve at compose
        time so multi-instance turn-on is a config change, not a prose
        rewrite.
        """
        content = (
            "verifier: .squidsquad/[VERIFIER_ALIAS]/planning/X.md, "
            "pm: .squidsquad/[PM_ALIAS]/working-state.md, "
            "dm: .squidsquad/[DM_ALIAS]/iterations/"
        )
        with patch.object(compose, "_read_config_value", side_effect=lambda f: {
            "alias-pm": "pm",
            "alias-qa": "qa",
            "alias-dm": "dm",
            "interval": "30",
        }.get(f, "")):
            result = compose._substitute_placeholders(content, "pm", "pm")
        assert "[VERIFIER_ALIAS]" not in result
        assert "[PM_ALIAS]" not in result
        assert "[DM_ALIAS]" not in result
        assert ".squidsquad/qa/planning/X.md" in result
        assert ".squidsquad/pm/working-state.md" in result
        assert ".squidsquad/dm/iterations/" in result

    def test_role_class_alias_placeholders_custom(self):
        """Multi-instance / custom-alias install: placeholders track config.

        Simulates a future install that aliases the verifier-class agent
        as `qa-skill` (instead of legacy `qa`). The composed output must
        carry the actual alias.
        """
        content = ".squidsquad/[VERIFIER_ALIAS]/current-state"
        with patch.object(compose, "_read_config_value", side_effect=lambda f: {
            "alias-qa": "qa-skill",
            "interval": "30",
        }.get(f, "")):
            result = compose._substitute_placeholders(content, "skill", "dev")
        assert "[VERIFIER_ALIAS]" not in result
        assert ".squidsquad/qa-skill/current-state" in result

    def test_role_class_alias_placeholders_fallback(self):
        """Missing config entries fall back to canonical names.

        When config.md doesn't have `alias-pm`/`alias-qa`/`alias-dm` keys,
        substitution uses the default (`pm`/`qa`/`dm`) so partial configs
        still compose cleanly.
        """
        content = (
            ".squidsquad/[PM_ALIAS]/ .squidsquad/[VERIFIER_ALIAS]/ "
            ".squidsquad/[DM_ALIAS]/"
        )
        with patch.object(compose, "_read_config_value", return_value=""):
            result = compose._substitute_placeholders(content, "skill", "dev")
        assert ".squidsquad/pm/" in result
        assert ".squidsquad/qa/" in result
        assert ".squidsquad/dm/" in result


# ---------------------------------------------------------------------------
# _list_known_role_identities
# ---------------------------------------------------------------------------

class TestListKnownRoleIdentities:
    def test_finds_roles_with_claude_md(self, compose_env):
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"):
            identities = compose._list_known_role_identities()
        assert "dev" in identities
        assert "pm" in identities

    def test_missing_roles_dir(self, tmp_path):
        # #6274 D2 dual-aware shim: even when ROLES_DIR doesn't exist,
        # the dual-aware identity set is still returned (worker, verifier,
        # dev, qa). After 6274.3 cutover this assertion reverts to
        # `identities == set()`.
        with patch.object(compose, "ROLES_DIR", tmp_path / "nonexistent"):
            identities = compose._list_known_role_identities()
        assert identities == {"worker", "verifier", "dev", "qa"}

    def test_ignores_dirs_without_claude_md(self, compose_env):
        # Create a directory without CLAUDE.md
        (compose_env / "references" / "roles" / "empty").mkdir()
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"):
            identities = compose._list_known_role_identities()
        assert "empty" not in identities


# ---------------------------------------------------------------------------
# _get_entry_file_for_role
# ---------------------------------------------------------------------------

class TestGetEntryFileForRole:
    def test_known_role_returns_self(self, compose_env):
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"):
            assert compose._get_entry_file_for_role("pm") == "pm"
            assert compose._get_entry_file_for_role("dev") == "dev"

    def test_unknown_role_falls_back_to_dev(self, compose_env):
        # Post-6274.2 (3b) disk-check shim: identities always includes both
        # `worker` and `dev` (dual-aware set), so the fallback now picks the
        # one whose directory actually exists on disk. In this scratch env
        # only `roles/dev/` is set up by the fixture, so the worker branch
        # short-circuits via the disk check and the dev branch wins —
        # restoring the original "fall back to dev" semantic on pre-rename
        # installs while still preferring `worker` post-rename.
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"):
            assert compose._get_entry_file_for_role("skill") == "dev"
            assert compose._get_entry_file_for_role("be") == "dev"
            assert compose._get_entry_file_for_role("fe") == "dev"


# ---------------------------------------------------------------------------
# compose_role / TestComposeRole and Layer 4 / TestL4RoleFiltering retired
# in E6 #10685 Phase 3d.5 along with the v1 compose chain. v2 L4 semantics
# diverge entirely from v1's filename-prefix routing (per cycle 1553
# audit): v2_link_stage reads a single L4 file at
# .squidsquad/project/<role-class>.md per parse_l4_file (no prefix
# routing). TestL4RoleFiltering's invariants don't map to v2.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# deploy_role: retired in E6 #10685 Phase 3d.4 (v2 ``deploy_role_v2`` /
# ``deploy_alias_v2`` are the only deploy paths post-cutover).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# generate_local_config
# ---------------------------------------------------------------------------

class TestGenerateLocalConfig:
    def test_generates_correct_format_default(self, tmp_path):
        """Without clone_paths, all agents map to '.' (single-repo fallback)."""
        ss = tmp_path / ".squidsquad"
        ss.mkdir()
        path = compose.generate_local_config(["skill", "pm"], target_root=tmp_path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "- **skill**: ." in content
        assert "- **pm**: ." in content

    def test_generates_in_squidsquad_dir(self, tmp_path):
        ss = tmp_path / ".squidsquad"
        ss.mkdir()
        path = compose.generate_local_config(["skill"], target_root=tmp_path)
        assert path.parent.name == ".squidsquad"
        assert path.name == ".local-config"

    def test_with_clone_paths_relative(self, tmp_path):
        """With clone_paths, writes relative paths per agent."""
        ss = tmp_path / ".squidsquad"
        ss.mkdir()
        clone_paths = {"pm": ".", "skill": "../myproject-skill", "qa": "../myproject-qa"}
        path = compose.generate_local_config(
            ["pm", "skill", "qa"], target_root=tmp_path, clone_paths=clone_paths,
        )
        content = path.read_text(encoding="utf-8")
        assert "- **pm**: ." in content
        assert "- **skill**: ../myproject-skill" in content
        assert "- **qa**: ../myproject-qa" in content
        # No absolute paths
        assert str(tmp_path.resolve()) not in content

    def test_clone_paths_partial(self, tmp_path):
        """Agents not in clone_paths default to '.'."""
        ss = tmp_path / ".squidsquad"
        ss.mkdir()
        clone_paths = {"skill": "../proj-skill"}
        path = compose.generate_local_config(
            ["pm", "skill"], target_root=tmp_path, clone_paths=clone_paths,
        )
        content = path.read_text(encoding="utf-8")
        assert "- **pm**: ." in content
        assert "- **skill**: ../proj-skill" in content


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# _load_manifest / TestLoadManifest retired in E6 #10685 Phase 3d.5 with
# the v1 chain. v2 uses ``_load_manifest_v2`` against the unified
# ``includes.yml`` and is exercised by test_manifest_v2 + test_compose_a*.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# _read_config_value
# ---------------------------------------------------------------------------

class TestReadConfigValue:
    def test_returns_empty_on_import_error(self):
        with patch.dict("sys.modules", {"config": None}):
            result = compose._read_config_value("nonexistent")
        assert result == ""

    def test_returns_empty_on_system_exit(self):
        import types
        mock_config = types.ModuleType("config")
        mock_config.get_field = lambda f: (_ for _ in ()).throw(SystemExit(1))
        with patch.dict("sys.modules", {"config": mock_config}):
            result = compose._read_config_value("bad-field")
        assert result == ""


# ---------------------------------------------------------------------------
# _collect_all_roles
# ---------------------------------------------------------------------------

class TestCollectAllRoles:
    def test_includes_dev_agents_and_mandatory_roles(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value="skill,be"), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert roles == ["skill", "be", "pm", "verifier", "dm"]

    def test_mandatory_roles_not_duplicated_when_in_config(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value="skill,dm"), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert roles == ["skill", "dm", "pm", "verifier"]
        assert roles.count("dm") == 1
        assert roles.count("pm") == 1

    def test_mandatory_roles_always_present(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value="skill"), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        for mandatory in ("pm", "verifier", "dm"):
            assert mandatory in roles

    def test_empty_dev_agents(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value=""), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert roles == ["pm", "verifier", "dm"]

    def test_strips_whitespace_from_agent_names(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value=" skill , be "), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert roles[0] == "skill"
        assert roles[1] == "be"


# ---------------------------------------------------------------------------
# Layered role architecture (#3465)
# ---------------------------------------------------------------------------

class TestResolveVariant:
    """Test _resolve_variant resolves nested variant directories."""

    def test_pm_skill_resolves(self):
        result = compose._resolve_variant("pm-skill")
        assert result == ("pm", "skill")

    def test_dev_ios_resolves(self):
        result = compose._resolve_variant("dev-ios")
        # Post-6274.2: legacy "dev-ios" routes to canonical worker on disk
        # via the _BASE_ALIAS_6274 dual-aware shim in _resolve_variant.
        assert result == ("worker", "ios")

    def test_qa_android_resolves(self):
        result = compose._resolve_variant("qa-android")
        # Post-6274.2: legacy "qa-android" routes to canonical verifier on disk.
        assert result == ("verifier", "android")

    def test_base_role_returns_none(self):
        assert compose._resolve_variant("pm") is None

    def test_no_hyphen_returns_none(self):
        assert compose._resolve_variant("skill") is None


class TestAssembleSoul:
    """Test _assemble_soul produces L1 base + role SOUL flat output."""

    def test_contains_layer1_base_content(self):
        content = compose._assemble_soul("skill")
        assert "<!-- layer: base -->" in content
        assert "<!-- /layer: base -->" in content
        assert "Core Identity" in content

    def test_contains_role_soul(self):
        """Role SOUL (Layer 2) is included after base."""
        content = compose._assemble_soul("skill")
        # Dev SOUL.md content (skill inherits from dev)
        assert "Professional Identity" in content

    def test_pm_has_own_soul(self):
        """PM gets its own role-specific SOUL content."""
        content = compose._assemble_soul("pm")
        assert "Soul" in content
        assert "## Project Adaptation" in content

    def test_single_flat_file(self):
        """Assembly produces a single string, not multiple files."""
        content = compose._assemble_soul("pm")
        assert isinstance(content, str)
        assert "## Project Adaptation" in content

    def test_project_adaptation_present(self):
        content = compose._assemble_soul("qa")
        assert "## Project Adaptation" in content
        assert "<!-- /project-adaptation -->" in content


class TestUpgradeSoul:
    """Test upgrade_soul preserves role content and Project Adaptation."""

    def test_preserves_role_content_on_upgrade(self, tmp_path):
        """upgrade_soul re-renders L1 but keeps role content unchanged."""
        ss = tmp_path / ".squidsquad" / "pm"
        ss.mkdir(parents=True)

        compose._assemble_and_write_soul("pm", tmp_path)
        soul_path = ss / "SOUL.md"
        original = soul_path.read_text(encoding="utf-8")

        # Simulate user customization
        modified = original.replace(
            "## Project Adaptation",
            "## Project Adaptation\n\nHuman added this custom note."
        )
        soul_path.write_text(modified, encoding="utf-8")

        compose.upgrade_soul("pm", tmp_path)
        upgraded = soul_path.read_text(encoding="utf-8")

        assert "<!-- layer: base -->" in upgraded
        assert "Human added this custom note." in upgraded

    def test_atomic_write_no_tmp_leftover(self, tmp_path):
        ss = tmp_path / ".squidsquad" / "pm"
        ss.mkdir(parents=True)
        compose._assemble_and_write_soul("pm", tmp_path)
        compose.upgrade_soul("pm", tmp_path)
        assert not (ss / "SOUL.md.tmp").exists()

    def test_creates_if_missing(self, tmp_path):
        ss = tmp_path / ".squidsquad" / "qa"
        ss.mkdir(parents=True)
        compose.upgrade_soul("qa", tmp_path)
        soul = ss / "SOUL.md"
        assert soul.exists()
        assert "<!-- layer: base -->" in soul.read_text(encoding="utf-8")

    def test_legacy_flat_soul_preserved(self, tmp_path):
        """A pre-migration SOUL.md without markers is preserved as role content."""
        ss = tmp_path / ".squidsquad" / "skill"
        ss.mkdir(parents=True)
        legacy_content = "## Soul - Legacy\n\nOld flat content.\n\n## Project Adaptation\n\nCustom.\n<!-- /project-adaptation -->\n"
        (ss / "SOUL.md").write_text(legacy_content, encoding="utf-8")

        compose.upgrade_soul("skill", tmp_path)
        upgraded = (ss / "SOUL.md").read_text(encoding="utf-8")

        assert "<!-- layer: base -->" in upgraded
        assert "Old flat content." in upgraded
        assert "Custom." in upgraded


class TestVariantInheritance:
    """Test Layer 3 variant inheritance in _get_entry_file_for_role.

    Post-E6 #10685 Phase 3d.5: ``_load_manifest`` was retired along with
    the v1 compose chain; the remaining assertions exercise the entry-file
    resolver only.
    """

    def test_get_entry_file_suffix_strip(self):
        """pm-skill resolves to pm entry file."""
        result = compose._get_entry_file_for_role("pm-skill")
        assert result == "pm"

    def test_get_entry_file_dev_variant_unchanged(self):
        """skill resolves to worker (post-6274.2 canonical; was dev pre-rename)."""
        result = compose._get_entry_file_for_role("skill")
        assert result == "worker"

    def test_get_entry_file_base_role_unchanged(self):
        """pm resolves to pm."""
        result = compose._get_entry_file_for_role("pm")
        assert result == "pm"


# ---------------------------------------------------------------------------
# Pre-layer detection and Project Adaptation extraction (#4083)
# ---------------------------------------------------------------------------

class TestPreLayerDetection:
    def test_pre_layer_install_detected(self, tmp_path):
        """Pre-layer: .squidsquad/ exists but no L1 base entry file."""
        (tmp_path / ".squidsquad").mkdir()
        # No references/roles/instructions.md
        assert compose.is_pre_layer_install(tmp_path) is True

    def test_post_layer_install_not_detected(self, tmp_path):
        """Post-layer: both .squidsquad/ and L1 base exist."""
        (tmp_path / ".squidsquad").mkdir()
        roles = tmp_path / "references" / "roles"
        roles.mkdir(parents=True)
        (roles / "instructions.md").write_text("# Base", encoding="utf-8")
        assert compose.is_pre_layer_install(tmp_path) is False

    def test_no_install_not_detected(self, tmp_path):
        """No .squidsquad/ at all — not a pre-layer install."""
        assert compose.is_pre_layer_install(tmp_path) is False


class TestExtractProjectAdaptation:
    def test_extracts_adaptation_section(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / "SOUL.md").write_text(
            "## Soul\nI am a dev.\n\n## Project Adaptation\n"
            "- Uses Python 3.12\n- Enforces 80% coverage\n\n## Other\nStuff\n",
            encoding="utf-8",
        )
        result = compose.extract_project_adaptation("skill", tmp_path)
        assert "Python 3.12" in result
        assert "80% coverage" in result
        assert "Other" not in result

    def test_no_adaptation_returns_empty(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / "SOUL.md").write_text("## Soul\nI am a dev.\n", encoding="utf-8")
        result = compose.extract_project_adaptation("skill", tmp_path)
        assert result == ""

    def test_missing_soul_returns_empty(self, tmp_path):
        result = compose.extract_project_adaptation("skill", tmp_path)
        assert result == ""


# ---------------------------------------------------------------------------
# Agent-driven composition (#4541)
# ---------------------------------------------------------------------------

class TestAgentComposeDisabled:
    """When Agent Compose is disabled, output passes through unchanged."""

    def test_returns_input_unchanged(self):
        with patch.object(compose, "_is_agent_compose_enabled", return_value=False):
            result = compose.agent_compose("hello world", "skill")
        assert result == "hello world"


class TestExtractCodeBlocks:
    def test_extracts_fenced_blocks(self):
        text = "prose\n```bash\necho hello\n```\nmore prose\n```python\nprint(1)\n```\n"
        blocks = compose._extract_code_blocks(text)
        assert len(blocks) == 2
        assert "echo hello" in blocks[0][2]
        assert "print(1)" in blocks[1][2]

    def test_empty_text(self):
        assert compose._extract_code_blocks("") == []


class TestExtractMarkers:
    def test_finds_html_comments(self):
        text = "<!-- sub-skill: foo -->\ncontent\n<!-- /sub-skill: foo -->"
        markers = compose._extract_markers(text)
        assert len(markers) == 2
        assert "sub-skill: foo" in markers[0]

    def test_empty_text(self):
        assert compose._extract_markers("") == []


class TestGenerateCQs:
    def test_generates_from_headings(self):
        sources = {
            "L2": "## Quality Bar\n\nContent here\n\n### Communication Style\nMore",
            "L4": "## Project Operations\n\nStuff",
        }
        cqs = compose._generate_cqs_from_sources(sources)
        headings = [cq["source_heading"] for cq in cqs]
        assert "Quality Bar" in headings
        assert "Communication Style" in headings
        assert "Project Operations" in headings

    def test_empty_sources(self):
        assert compose._generate_cqs_from_sources({}) == []

    def test_no_headings(self):
        sources = {"L1": "Just plain text without headings."}
        assert compose._generate_cqs_from_sources(sources) == []


class TestAgentComposeEnabled:
    """When enabled, verify fallback behavior on subprocess errors."""

    def test_falls_back_on_subprocess_error(self):
        with patch.object(compose, "_is_agent_compose_enabled", return_value=True), \
             patch("subprocess.run", side_effect=FileNotFoundError("no claude")):
            result = compose.agent_compose("original content", "skill")
        assert result == "original content"

    def test_falls_back_on_empty_output(self):
        from unittest.mock import MagicMock
        mock_result = MagicMock(returncode=0, stdout="")
        with patch.object(compose, "_is_agent_compose_enabled", return_value=True), \
             patch("subprocess.run", return_value=mock_result):
            result = compose.agent_compose("original content", "skill")
        assert result == "original content"

    def test_falls_back_on_lost_code_blocks(self):
        from unittest.mock import MagicMock
        original = "prose\n```bash\necho hello\n```\nmore"
        # Polished output loses the code block
        mock_result = MagicMock(returncode=0, stdout="just prose, no code")
        with patch.object(compose, "_is_agent_compose_enabled", return_value=True), \
             patch("subprocess.run", return_value=mock_result):
            result = compose.agent_compose(original, "skill")
        assert result == original  # fell back due to lost code block

    def test_pipes_prompt_via_stdin_not_cli_arg(self):
        """Regression: #4608 — prompt must go via stdin to avoid WinError 206."""
        from unittest.mock import MagicMock
        mock_result = MagicMock(returncode=0, stdout="polished output")
        with patch.object(compose, "_is_agent_compose_enabled", return_value=True), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            compose.agent_compose("original content", "skill")
        args, kwargs = mock_run.call_args
        # CLI args should NOT contain the prompt text
        cli_args = args[0]
        assert "original content" not in " ".join(cli_args), \
            "prompt must not appear in CLI args (Windows MAX_PATH limit)"
        # Prompt must be piped via input kwarg
        assert "input" in kwargs, "prompt must be passed via input= kwarg"
        assert "original content" in kwargs["input"]


# ---------------------------------------------------------------------------
# Regression #4918: no deprecated tempfile.mktemp()
# ---------------------------------------------------------------------------

class TestNoDeprecatedMktemp:
    """compose.py must not use deprecated tempfile.mktemp()."""

    def test_source_does_not_call_mktemp(self):
        import inspect
        source = inspect.getsource(compose)
        # mktemp() calls — exclude comments
        lines = [l for l in source.splitlines()
                 if "mktemp" in l and not l.strip().startswith("#")]
        assert lines == [], (
            f"compose.py still uses deprecated tempfile.mktemp(): {lines}"
        )


# TestNoDeadPrefixVariable (#7062 dead-code guard) retired in E6 #10685
# Phase 3d.5 — ``_resolve_includes_with_manifest`` was deleted along with
# the rest of the v1 compose chain, so the guard has no surface to assert
# against.


class TestNoRedundantReImport:
    """#7063: compose.py functions must not re-import re locally."""

    def test_no_local_re_import_in_extract_code_blocks(self):
        import inspect
        source = inspect.getsource(compose._extract_code_blocks)
        assert "import re" not in source

    def test_no_local_re_import_in_extract_markers(self):
        import inspect
        source = inspect.getsource(compose._extract_markers)
        assert "import re" not in source

    def test_no_local_re_import_in_generate_cqs(self):
        import inspect
        source = inspect.getsource(compose._generate_cqs_from_sources)
        assert "import re" not in source

    def test_no_local_import_in_agent_compose(self):
        """#8159 regression: agent_compose must not re-import subprocess/json."""
        import inspect
        source = inspect.getsource(compose.agent_compose)
        assert "import subprocess" not in source
        assert "import json" not in source


# ---------------------------------------------------------------------------
# Dual-mode composition — #8697 (parallel-manifest design per PM directive)
# ---------------------------------------------------------------------------


# TestGetWakeMode (#9745 compose-side delegation wrapper) retired in E6
# #10685 Phase 5 — ``compose._get_wake_mode`` was the v1 ``compose_role``
# helper, deleted in Phase 3d.5 (cycle 1564). ``cycle_post`` /
# ``statusline_data`` delegation is still covered in
# ``test_feat_9745_wake_mode_canonical.py``.


# #10685 PRD-E E6 V2 CUTOVER: the legacy ``TestLoadManifestSelectsByWakeMode``
# class lived here and gated v1 ``_load_manifest`` against polling vs
# event-driven manifests. Post-cutover the v2 path owns composition, and
# wake_mode-based manifest selection is retired — there is only one unified
# manifest per role (``includes.yml``, formerly ``includes-v2.yml``). The
# event-driven boot path remains as runtime behavior (config.md still flips
# the wake mode), but the COMPOSE-time mode-conditional manifest split is
# gone. Tests for that gone behavior are deleted rather than kept skipped.


class TestEventDrivenWorkflowLocation:
    """The event-driven-workflow fragment lives under common-events/ (#8697)."""

    def test_event_driven_workflow_in_common_events(self):
        path = (Path(__file__).resolve().parent.parent
                / "references" / "sub-skills" / "common-events"
                / "event-driven-workflow.md")
        assert path.exists(), "common-events/event-driven-workflow.md missing"

    def test_no_event_driven_workflow_in_common(self):
        path = (Path(__file__).resolve().parent.parent
                / "references" / "sub-skills" / "common"
                / "event-driven-workflow.md")
        assert not path.exists(), (
            "common/event-driven-workflow.md should have been moved to "
            "common-events/ (no mode-conditional logic inside fragments)"
        )

