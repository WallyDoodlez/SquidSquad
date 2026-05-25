"""Unit tests for the manifest registry validator (#328 Phase D, #401 Phase H).

Tests use `tmp_path` fixtures to build synthetic registry layouts and run
the validator against them — no real files are touched. A single
"shipped registry" smoke test runs against the actual files in
references/{roles,sub-skills/capabilities,presets} to guarantee the v2
manifests stay clean as they evolve. v1 backward compatibility is preserved.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

# PyYAML is a hard dependency of manifest.py. Skip the whole module if
# the test environment does not have it — the validator itself exits
# cleanly with a "install PyYAML" message at runtime.
pytest.importorskip("yaml")

import manifest  # noqa: E402  (imported after sys.path manipulation)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# A minimal, valid registry: two always-installed infra roles (pm, dm),
# one specialist (dev), one tool (local_delivery), one preset (software-dev).
# Tests derive negative variants from this baseline.

VALID_PM = """\
schema_version: 2
id: pm
display_name: PM
tagline: Coordinates the team and talks to you
description: The project manager.
show_in_roster: false
always_installed: true
iteration_mode: normal
routes_to: [dev, dm]
requires_sub_skills: {}
setup_requirements: []
soul_template: SOUL.md
claude_template: CLAUDE.md
"""

VALID_DM = """\
schema_version: 2
id: dm
display_name: DM
tagline: Packages and delivers completed work
description: The delivery manager.
show_in_roster: false
always_installed: true
iteration_mode: normal
routes_to: []
requires_sub_skills:
  any_of: [local_delivery]
setup_requirements: []
soul_template: SOUL.md
claude_template: CLAUDE.md
"""

VALID_DEV = """\
schema_version: 2
id: dev
display_name: Dev
tagline: Writes code
description: Engineering specialist.
show_in_roster: true
always_installed: false
iteration_mode: normal
routes_to: [dm]
requires_sub_skills: {}
setup_requirements: []
soul_template: SOUL.md
claude_template: CLAUDE.md
"""

VALID_TOOL_LOCAL_DELIVERY = """\
schema_version: 2
id: local_delivery
display_name: Local delivery
category: delivery
description: Plain local-filesystem delivery.
provider: builtin
applicable_roles: [dm]
sub_skill: sub-skill.md
"""

VALID_PRESET_SOFTWARE_DEV = """\
schema_version: 2
id: software-dev
display_name: Software Development
description: A software team.
role_install_order: [dev]
"""


def _make_valid_registry(base: Path) -> Path:
    """Build a minimal valid registry under `base / references`.

    Post-Q-new22, each role directory must contain its own SOUL.md and
    CLAUDE.md files at the paths declared by the manifest's
    soul_template / claude_template fields.

    Post-#401, capabilities live under sub-skills/capabilities/ (not tools/).
    """
    ref = base / "references"
    for role in ("pm", "dm", "dev"):
        _write(ref / "roles" / role / "SOUL.md", f"# {role} soul\n")
        _write(ref / "roles" / role / "CLAUDE.md", f"# {role} template\n")
    _write(ref / "roles" / "pm" / "manifest.yaml", VALID_PM)
    _write(ref / "roles" / "dm" / "manifest.yaml", VALID_DM)
    _write(ref / "roles" / "dev" / "manifest.yaml", VALID_DEV)
    _write(ref / "sub-skills" / "capabilities" / "local_delivery" / "manifest.yaml", VALID_TOOL_LOCAL_DELIVERY)
    _write(ref / "sub-skills" / "capabilities" / "local_delivery" / "sub-skill.md", "# sub-skill\n")
    _write(ref / "sub-skills" / "capabilities" / "local_delivery" / "setup.md", "# setup\n")
    _write(ref / "presets" / "software-dev" / "manifest.yaml", VALID_PRESET_SOFTWARE_DEV)
    return ref


def _errors(issues):
    return [i for i in issues if i.severity == "error"]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidRegistry:
    def test_minimal_registry_validates(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        issues, roles, tools, presets = manifest.validate_registry(ref)
        assert not _errors(issues), [str(i) for i in issues]
        assert set(roles) == {"pm", "dm", "dev"}
        assert set(tools) == {"local_delivery"}
        assert set(presets) == {"software-dev"}

    def test_resolve_pipeline(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _, roles, _, presets = manifest.validate_registry(ref)
        resolved = manifest.resolve_pipeline("software-dev", roles, presets)
        assert resolved == {"pm", "dm", "dev"}

    def test_resolve_unknown_preset_raises(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _, roles, _, presets = manifest.validate_registry(ref)
        with pytest.raises(KeyError):
            manifest.resolve_pipeline("does-not-exist", roles, presets)

    def test_empty_registry_validates_cleanly(self, tmp_path):
        """No manifests at all is a valid (if useless) state."""
        ref = tmp_path / "references"
        (ref / "roles").mkdir(parents=True)
        (ref / "sub-skills" / "capabilities").mkdir(parents=True)
        (ref / "presets").mkdir(parents=True)
        issues, roles, tools, presets = manifest.validate_registry(ref)
        assert not _errors(issues)
        assert roles == tools == presets == {}


# ---------------------------------------------------------------------------
# Shipped registry smoke test — guarantees the real v1 manifests are clean.
# ---------------------------------------------------------------------------


class TestShippedRegistry:
    def test_shipped_v2_registry_is_clean(self):
        """The actual references/ registry must pass validation.

        This is the critical meta-test — it fails loudly if anyone edits
        a shipped manifest in a way that breaks its own invariants.
        """
        issues, roles, tools, presets = manifest.validate_registry()
        errors = _errors(issues)
        assert not errors, (
            f"Shipped registry has {len(errors)} error(s):\n"
            + "\n".join(str(i) for i in errors)
        )
        # v2 shape guarantee (post-#6274.2: dev→worker, qa→verifier)
        assert set(roles) >= {"pm", "dm", "worker", "verifier"}
        assert set(tools) >= {"figma", "google_stitch", "local_html", "local_delivery"}
        assert set(presets) >= {"software-dev", "design"}

    def test_shipped_pipelines_match_spec(self):
        """Resolved pipelines match expected sets (verifier always_installed since #347)."""
        _, roles, _, presets = manifest.validate_registry()
        sw = manifest.resolve_pipeline("software-dev", roles, presets)
        assert sw == {"pm", "dm", "worker", "verifier"}
        design = manifest.resolve_pipeline("design", roles, presets)
        assert design == {"pm", "dm", "verifier"}


# ---------------------------------------------------------------------------
# Role manifest schema errors
# ---------------------------------------------------------------------------


class TestRoleSchemaErrors:
    def test_missing_schema_version(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("schema_version: 2\n", ""))
        issues, *_ = manifest.validate_registry(ref)
        errs = _errors(issues)
        assert any(i.field == "schema_version" and "missing" in i.message
                   for i in errs), [str(e) for e in errs]

    def test_unknown_schema_version(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("schema_version: 2", "schema_version: 99"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("unknown schema_version" in i.message for i in _errors(issues))

    def test_id_mismatch_with_directory(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("id: dev", "id: wrongname"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("does not match directory" in i.message for i in _errors(issues))

    def test_invalid_iteration_mode(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("iteration_mode: normal",
                                 "iteration_mode: turbo"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("iteration_mode" in i.message for i in _errors(issues))

    def test_missing_required_field(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("show_in_roster: true\n", ""))
        issues, *_ = manifest.validate_registry(ref)
        assert any("show_in_roster" in (i.field or "") for i in _errors(issues))

    def test_routes_to_must_be_list(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("routes_to: [dm]", "routes_to: dm"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("routes_to" in (i.field or "") for i in _errors(issues))

    def test_missing_soul_template_field(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("soul_template: SOUL.md\n", ""))
        issues, *_ = manifest.validate_registry(ref)
        assert any(i.field == "soul_template" and "missing" in i.message
                   for i in _errors(issues))

    def test_missing_claude_template_field(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("claude_template: CLAUDE.md\n", ""))
        issues, *_ = manifest.validate_registry(ref)
        assert any(i.field == "claude_template" and "missing" in i.message
                   for i in _errors(issues))

    def test_soul_template_file_not_found(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        (ref / "roles" / "dev" / "SOUL.md").unlink()
        issues, *_ = manifest.validate_registry(ref)
        errs = _errors(issues)
        assert any(i.field == "soul_template"
                   and "not found" in i.message for i in errs), errs

    def test_claude_template_file_not_found(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        (ref / "roles" / "dev" / "CLAUDE.md").unlink()
        issues, *_ = manifest.validate_registry(ref)
        errs = _errors(issues)
        assert any(i.field == "claude_template"
                   and "not found" in i.message for i in errs), errs

    def test_template_path_relative_to_role_dir(self, tmp_path):
        """soul_template/claude_template are relative to the manifest's directory."""
        ref = _make_valid_registry(tmp_path)
        # Point soul_template at a subfolder that DOES exist
        _write(ref / "roles" / "dev" / "nested" / "SOUL.md", "# nested\n")
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("soul_template: SOUL.md",
                                 "soul_template: nested/SOUL.md"))
        issues, *_ = manifest.validate_registry(ref)
        # Only the original SOUL.md concern — the nested path resolves fine
        soul_errs = [i for i in _errors(issues)
                     if i.field == "soul_template"]
        assert not soul_errs, soul_errs

    def test_setup_requirements_missing_subfields(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        bad = VALID_DEV.replace(
            "setup_requirements: []",
            "setup_requirements:\n  - id: variant",
        )
        _write(ref / "roles" / "dev" / "manifest.yaml", bad)
        issues, *_ = manifest.validate_registry(ref)
        fields = [i.field for i in _errors(issues)]
        assert any("setup_requirements[0].needs" == f
                   or "setup_requirements[0].used_for" == f
                   for f in fields), fields


# ---------------------------------------------------------------------------
# Cross-reference errors
# ---------------------------------------------------------------------------


class TestCrossReferenceErrors:
    def test_role_requires_unknown_tool(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        bad = VALID_DEV.replace(
            "requires_sub_skills: {}",
            "requires_sub_skills:\n  any_of: [ghost_tool]",
        )
        _write(ref / "roles" / "dev" / "manifest.yaml", bad)
        issues, *_ = manifest.validate_registry(ref)
        errs = _errors(issues)
        assert any("ghost_tool" in i.message for i in errs), errs

    def test_role_routes_to_unknown_role(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               VALID_DEV.replace("routes_to: [dm]", "routes_to: [mystery]"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("mystery" in i.message for i in _errors(issues))

    def test_preset_references_unknown_role(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "presets" / "software-dev" / "manifest.yaml",
               VALID_PRESET_SOFTWARE_DEV.replace("[dev]", "[phantom]"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("phantom" in i.message for i in _errors(issues))

    def test_preset_lists_always_installed_role(self, tmp_path):
        """Q-new16: always_installed roles must not appear in role_install_order."""
        ref = _make_valid_registry(tmp_path)
        _write(ref / "presets" / "software-dev" / "manifest.yaml",
               VALID_PRESET_SOFTWARE_DEV.replace("[dev]", "[pm, dev]"))
        issues, *_ = manifest.validate_registry(ref)
        errs = _errors(issues)
        assert any("always_installed" in i.message for i in errs), errs

    def test_tool_applicable_role_unknown(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "sub-skills" / "capabilities" / "local_delivery" / "manifest.yaml",
               VALID_TOOL_LOCAL_DELIVERY.replace("[dm]", "[ghost]"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("ghost" in i.message for i in _errors(issues))


# ---------------------------------------------------------------------------
# Tool manifest errors
# ---------------------------------------------------------------------------


class TestToolSchemaErrors:
    def test_mcp_provider_without_mcp_name(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "sub-skills" / "capabilities" / "local_delivery" / "manifest.yaml",
               VALID_TOOL_LOCAL_DELIVERY.replace("provider: builtin",
                                                  "provider: mcp"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("mcp_name" in (i.field or "") for i in _errors(issues))

    def test_invalid_category(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "sub-skills" / "capabilities" / "local_delivery" / "manifest.yaml",
               VALID_TOOL_LOCAL_DELIVERY.replace("category: delivery",
                                                  "category: quantum"))
        issues, *_ = manifest.validate_registry(ref)
        assert any("category" in (i.field or "") for i in _errors(issues))

    def test_missing_sub_skill_file(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        (ref / "sub-skills" / "capabilities" / "local_delivery" / "sub-skill.md").unlink()
        issues, *_ = manifest.validate_registry(ref)
        assert any("sub-skill" in i.message.lower() for i in _errors(issues))

    def test_missing_setup_md(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        (ref / "sub-skills" / "capabilities" / "local_delivery" / "setup.md").unlink()
        issues, *_ = manifest.validate_registry(ref)
        assert any("setup.md" in i.message for i in _errors(issues))


# ---------------------------------------------------------------------------
# Domain-only linter (Q-new14)
# ---------------------------------------------------------------------------


class TestDomainOnlyLinter:
    @pytest.mark.parametrize("phrase", [
        "config.md",
        ".squidsquad",
        "CLAUDE.md",
        "SOUL.md",
        "sub-skill",
        "tracker.py",
    ])
    def test_description_rejects_internal_reference(self, tmp_path, phrase):
        ref = _make_valid_registry(tmp_path)
        bad = VALID_DEV.replace(
            "description: Engineering specialist.",
            f"description: Engineering specialist. See {phrase}.",
        )
        _write(ref / "roles" / "dev" / "manifest.yaml", bad)
        issues, *_ = manifest.validate_registry(ref)
        errs = _errors(issues)
        assert any("domain-only" in i.message for i in errs), [str(i) for i in errs]

    def test_tagline_checked_too(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        bad = VALID_DEV.replace(
            "tagline: Writes code",
            "tagline: Writes code and edits config.md",
        )
        _write(ref / "roles" / "dev" / "manifest.yaml", bad)
        issues, *_ = manifest.validate_registry(ref)
        assert any("domain-only" in i.message for i in _errors(issues))

    def test_clean_fields_are_fine(self, tmp_path):
        """Sanity: normal domain language should not trigger the linter."""
        ref = _make_valid_registry(tmp_path)
        issues, *_ = manifest.validate_registry(ref)
        assert not _errors(issues)


# ---------------------------------------------------------------------------
# YAML parse errors
# ---------------------------------------------------------------------------


class TestYamlErrors:
    def test_malformed_yaml_reported(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               "schema_version: 2\nid: dev\nbroken: [unclosed")
        issues, *_ = manifest.validate_registry(ref)
        errs = _errors(issues)
        assert any("YAML parse error" in i.message for i in errs), errs

    def test_top_level_not_mapping(self, tmp_path):
        ref = _make_valid_registry(tmp_path)
        _write(ref / "roles" / "dev" / "manifest.yaml",
               "- just\n- a\n- list\n")
        issues, *_ = manifest.validate_registry(ref)
        errs = _errors(issues)
        assert any("mapping" in i.message for i in errs), errs


# ---------------------------------------------------------------------------
# Issue object + helpers
# ---------------------------------------------------------------------------


class TestIssueFormatting:
    def test_str_format_with_field(self):
        i = manifest.Issue("roles/dev/manifest.yaml", "id", "oops")
        s = str(i)
        assert "ERROR" in s
        assert "roles/dev/manifest.yaml:id" in s
        assert "oops" in s

    def test_str_format_without_field(self):
        i = manifest.Issue("roles/dev", "", "missing file")
        s = str(i)
        assert "ERROR" in s
        assert "roles/dev" in s
        assert "missing file" in s

    def test_severity_default_is_error(self):
        i = manifest.Issue("x", "", "y")
        assert i.severity == "error"


# ---------------------------------------------------------------------------
# #7590: _load_kind uses module-level yaml import, not redundant inner import
# ---------------------------------------------------------------------------

class TestLoadKindYamlImport:
    """#7590: includes.yml parsing uses module-level yaml, catches YAMLError."""

    def test_malformed_includes_yml_does_not_crash(self, tmp_path):
        """Malformed includes.yml should be caught by yaml.YAMLError, not Exception."""
        role_dir = tmp_path / "roles" / "testrole"
        role_dir.mkdir(parents=True)
        (role_dir / "instructions.md").write_text("# test")
        (role_dir / "includes.yml").write_text(": invalid: yaml: {{{\n")
        # Should not raise — malformed YAML caught gracefully
        _, issues = manifest._load_kind(tmp_path, "roles", lambda m: [])
        # The malformed includes.yml means it's not detected as a variant,
        # so it may report a missing manifest issue — that's expected behavior
        assert isinstance(issues, list)
