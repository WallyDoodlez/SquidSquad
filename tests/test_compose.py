"""Tests for references/scripts/compose.py — composition engine."""

import sys
from pathlib import Path
from unittest.mock import patch

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
    (common / "tracker-protocol.md").write_text(
        "## Tracker Protocol\n\nUse tracker.py for all operations.",
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
    (dev_role / "CLAUDE.md").write_text(
        "# Dev Agent\n\n"
        "{{runtime: souls/dev}}\n"
        "{{include: common/tracker-protocol}}\n"
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
    (pm_role / "CLAUDE.md").write_text(
        "# PM Agent\n\n"
        "{{include: common/tracker-protocol}}\n"
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
# _resolve_includes
# ---------------------------------------------------------------------------

class TestResolveIncludes:
    def test_basic_include(self, compose_env):
        entry = compose_env / "references" / "roles" / "dev" / "CLAUDE.md"
        with patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"):
            result = compose._resolve_includes(entry)
        assert "## Tracker Protocol" in result
        assert "<!-- sub-skill: tracker-protocol -->" in result
        assert "<!-- /sub-skill: tracker-protocol -->" in result

    def test_missing_include(self, compose_env):
        entry = compose_env / "test-entry.md"
        entry.write_text("{{include: common/nonexistent}}", encoding="utf-8")
        with patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"):
            result = compose._resolve_includes(entry)
        assert "<!-- ERROR: Missing include: common/nonexistent -->" in result

    def test_runtime_directive(self, compose_env):
        entry = compose_env / "references" / "roles" / "dev" / "CLAUDE.md"
        with patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"):
            result = compose._resolve_includes(entry)
        assert "## Soul" in result
        assert "<!-- sub-skill: dev -->" in result
        assert "SOUL.md" in result

    def test_capability_directive(self, compose_env):
        entry = compose_env / "cap-test.md"
        entry.write_text("{{capability: test-cap}}", encoding="utf-8")
        with patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"), \
             patch.object(compose, "CAPABILITIES_DIR", compose_env / "references" / "sub-skills" / "capabilities"):
            result = compose._resolve_includes(entry)
        assert "## Test Capability" in result
        assert "<!-- sub-skill: capability-test-cap -->" in result

    def test_missing_capability(self, compose_env):
        entry = compose_env / "cap-test.md"
        entry.write_text("{{capability: nonexistent}}", encoding="utf-8")
        with patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"), \
             patch.object(compose, "CAPABILITIES_DIR", compose_env / "references" / "sub-skills" / "capabilities"):
            result = compose._resolve_includes(entry)
        assert "<!-- ERROR: Missing capability: nonexistent -->" in result

    def test_preserves_inline_content(self, compose_env):
        entry = compose_env / "inline-test.md"
        entry.write_text(
            "# Header\n\nSome inline text.\n\n{{include: common/tracker-protocol}}\n\nMore inline.",
            encoding="utf-8",
        )
        with patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"):
            result = compose._resolve_includes(entry)
        assert "# Header" in result
        assert "Some inline text." in result
        assert "More inline." in result
        assert "## Tracker Protocol" in result


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
            "dev-agents": "skill,be",
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
            "dev-agents": "skill,be,fe",
            "interval": "30",
        }.get(f, "")):
            result = compose._substitute_placeholders(content, "skill", "dev")
        assert "be" in result
        assert "fe" in result
        assert "skill" not in result.split("Others: ")[1]


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
        with patch.object(compose, "ROLES_DIR", tmp_path / "nonexistent"):
            identities = compose._list_known_role_identities()
        assert identities == set()

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
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"):
            assert compose._get_entry_file_for_role("skill") == "dev"
            assert compose._get_entry_file_for_role("be") == "dev"
            assert compose._get_entry_file_for_role("fe") == "dev"


# ---------------------------------------------------------------------------
# compose_role
# ---------------------------------------------------------------------------

class TestComposeRole:
    def test_composes_dev_role(self, compose_env):
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"), \
             patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"):
            result = compose.compose_role("dev")
        assert "# Dev Agent" in result
        assert "## Tracker Protocol" in result
        assert "### Step 1 — Pull Latest" in result

    def test_composes_pm_role(self, compose_env):
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"), \
             patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"):
            result = compose.compose_role("pm")
        assert "# PM Agent" in result
        assert "## Tracker Protocol" in result

    def test_missing_role_exits(self, compose_env):
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"):
            with pytest.raises(SystemExit):
                compose.compose_role("nonexistent_role_xyz")


# ---------------------------------------------------------------------------
# deploy_role
# ---------------------------------------------------------------------------

class TestDeployRole:
    def test_deploys_to_squidsquad_dir(self, compose_env):
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"), \
             patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"), \
             patch.object(compose, "_read_config_value", return_value=""):
            output = compose.deploy_role("pm", target_root=compose_env)
        assert output.exists()
        assert output.name == "CLAUDE.md"
        assert ".squidsquad" in str(output)
        content = output.read_text(encoding="utf-8")
        assert "GENERATED by compose.py" in content

    def test_creates_soul_md(self, compose_env):
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"), \
             patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"), \
             patch.object(compose, "_read_config_value", return_value=""):
            compose.deploy_role("skill", target_root=compose_env)
        # Dev variant should get SOUL.md from dev role
        soul = compose_env / ".squidsquad" / "skill" / "SOUL.md"
        assert soul.exists()
        assert "engineer" in soul.read_text(encoding="utf-8").lower()

    def test_does_not_overwrite_existing_soul(self, compose_env):
        soul_dir = compose_env / ".squidsquad" / "skill"
        soul_dir.mkdir(parents=True)
        soul = soul_dir / "SOUL.md"
        soul.write_text("Custom soul content", encoding="utf-8")

        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"), \
             patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"), \
             patch.object(compose, "_read_config_value", return_value=""):
            compose.deploy_role("skill", target_root=compose_env)
        assert soul.read_text(encoding="utf-8") == "Custom soul content"


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
# boot_role
# ---------------------------------------------------------------------------

class TestBootRole:
    def test_generates_sh_and_ps1(self, compose_env):
        with patch.object(compose, "TEMPLATES_DIR", compose_env / "references" / "templates"), \
             patch.object(compose, "REPO_ROOT", compose_env):
            outputs = compose.boot_role("skill")
        assert len(outputs) == 2
        sh = [o for o in outputs if o.suffix == ".sh"][0]
        ps1 = [o for o in outputs if o.suffix == ".ps1"][0]
        assert sh.exists()
        assert ps1.exists()
        assert "ROLE=skill" in sh.read_text(encoding="utf-8")
        assert "$Role = 'skill'" in ps1.read_text(encoding="utf-8")

    def test_substitutes_role_placeholder(self, compose_env):
        with patch.object(compose, "TEMPLATES_DIR", compose_env / "references" / "templates"), \
             patch.object(compose, "REPO_ROOT", compose_env):
            outputs = compose.boot_role("pm")
        sh = [o for o in outputs if o.suffix == ".sh"][0]
        content = sh.read_text(encoding="utf-8")
        assert "{{ROLE}}" not in content
        assert "pm" in content


class TestStartRolePs1Template:
    """Real template checks for start-role.ps1 (#2411)."""

    def test_role_dir_is_absolute(self):
        """RoleDir must use Join-Path or $repoRoot, not a bare relative path."""
        template = Path(compose.TEMPLATES_DIR) / "start-role.ps1"
        if not template.exists():
            pytest.skip("start-role.ps1 template not found")
        content = template.read_text(encoding="utf-8")
        # Must not have a bare relative assignment like $RoleDir = ".squidsquad/..."
        for line in content.splitlines():
            if "$RoleDir" in line and "=" in line and '".squidsquad' in line:
                assert "Join-Path" in line or "$repoRoot" in line or "$PSScriptRoot" in line, \
                    f"RoleDir must be absolute: {line.strip()}"

    def test_no_resolve_path_on_health_file(self):
        """Resolve-Path fails on non-existent files — use Join-Path instead."""
        template = Path(compose.TEMPLATES_DIR) / "start-role.ps1"
        if not template.exists():
            pytest.skip("start-role.ps1 template not found")
        content = template.read_text(encoding="utf-8")
        assert "Resolve-Path $HealthFile" not in content, \
            "Resolve-Path fails on non-existent files — use Join-Path"

    def test_claude_exe_not_bare_claude(self):
        """Start-Process must use claude.exe, not bare 'claude'."""
        template = Path(compose.TEMPLATES_DIR) / "start-role.ps1"
        if not template.exists():
            pytest.skip("start-role.ps1 template not found")
        content = template.read_text(encoding="utf-8")
        for line in content.splitlines():
            if "Start-Process" in line and "claude" in line.lower():
                assert "claude.exe" in line, \
                    f"Start-Process must use claude.exe: {line.strip()}"


# ---------------------------------------------------------------------------
# _load_manifest (requires pyyaml)
# ---------------------------------------------------------------------------

class TestLoadManifest:
    def test_returns_none_without_yaml(self, compose_env):
        with patch.object(compose, "yaml", None):
            result = compose._load_manifest("dev")
        assert result is None

    def test_returns_none_for_missing_manifest(self, compose_env):
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"):
            # No includes.yml exists
            result = compose._load_manifest("pm")
        assert result is None

    @pytest.mark.skipif(compose.yaml is None, reason="pyyaml not installed")
    def test_loads_valid_manifest(self, compose_env):
        manifest_dir = compose_env / "references" / "roles" / "dev"
        (manifest_dir / "includes.yml").write_text(
            "includes:\n  - common/tracker-protocol\n  - common/pull-latest\n",
            encoding="utf-8",
        )
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"), \
             patch.object(compose, "SUB_SKILLS_DIR", compose_env / "references" / "sub-skills"):
            result = compose._load_manifest("dev")
        assert result == ["common/tracker-protocol", "common/pull-latest"]

    @pytest.mark.skipif(compose.yaml is None, reason="pyyaml not installed")
    def test_invalid_yaml_returns_none(self, compose_env):
        manifest_dir = compose_env / "references" / "roles" / "pm"
        (manifest_dir / "includes.yml").write_text(
            "not_includes: foo\n",
            encoding="utf-8",
        )
        with patch.object(compose, "ROLES_DIR", compose_env / "references" / "roles"):
            result = compose._load_manifest("pm")
        assert result is None


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
    def test_includes_dev_agents_and_pm(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value="skill,be"), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert roles == ["skill", "be", "pm"]

    def test_includes_dm_when_dir_exists(self, tmp_path):
        (tmp_path / ".squidsquad" / "dm").mkdir(parents=True)
        with patch.object(compose, "_read_config_value", return_value="skill"), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert roles == ["skill", "pm", "dm"]

    def test_no_dm_when_dir_missing(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value="skill"), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert "dm" not in roles

    def test_empty_dev_agents(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value=""), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert roles == ["pm"]

    def test_strips_whitespace_from_agent_names(self, tmp_path):
        with patch.object(compose, "_read_config_value", return_value=" skill , be "), \
             patch.object(compose, "REPO_ROOT", tmp_path):
            roles = compose._collect_all_roles()
        assert roles[0] == "skill"
        assert roles[1] == "be"


# ---------------------------------------------------------------------------
# Layered role architecture (#3465)
# ---------------------------------------------------------------------------

class TestStripVariantSuffix:
    """Test _strip_variant_suffix resolves variant names to base roles."""

    def test_pm_skill_resolves_to_pm(self):
        assert compose._strip_variant_suffix("pm-skill") == "pm"

    def test_dev_ios_resolves_to_dev(self):
        assert compose._strip_variant_suffix("dev-ios") == "dev"

    def test_qa_android_resolves_to_qa(self):
        assert compose._strip_variant_suffix("qa-android") == "qa"

    def test_base_role_returns_none(self):
        assert compose._strip_variant_suffix("pm") is None

    def test_no_hyphen_returns_none(self):
        assert compose._strip_variant_suffix("skill") is None


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
    """Test Layer 3 variant inheritance in _load_manifest and _get_entry_file_for_role."""

    def test_get_entry_file_suffix_strip(self):
        """pm-skill resolves to pm entry file."""
        result = compose._get_entry_file_for_role("pm-skill")
        assert result == "pm"

    def test_get_entry_file_dev_variant_unchanged(self):
        """skill still resolves to dev (legacy behavior)."""
        result = compose._get_entry_file_for_role("skill")
        assert result == "dev"

    def test_get_entry_file_base_role_unchanged(self):
        """pm resolves to pm."""
        result = compose._get_entry_file_for_role("pm")
        assert result == "pm"
