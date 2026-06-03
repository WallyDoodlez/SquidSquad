"""
FEAT-QA-6581 — Wizard Reframing: manifest-driven domain variants + L4 project files.

Each TC from FEAT-PM-6581-TEST-PLAN.md is implemented as one test function.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO / "references" / "scripts"
WIZARD_MD = REPO / "references" / "wizard" / "WIZARD.md"
PRESETS_DIR = REPO / "references" / "presets"
TESTS_DIR = REPO / "tests"

# Add references/scripts to sys.path so imports work
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import wizard
import compose


# ---------------------------------------------------------------------------
# TC-1: Preset manifest domain_variants resolved per role (happy path)
# ---------------------------------------------------------------------------

def test_tc_01_preset_manifest_variants():
    """TC-1: apply_project_type reads manifest domain_variants and assigns
    a variant to each agent, not a single uniform PROJECT_TYPE_PRESETS value."""
    spec = {
        "preset": "software-dev",
        "agents": [
            {"id": "pm",    "role": "pm"},
            {"id": "skill", "role": "dev"},
            {"id": "qa",    "role": "qa"},
            {"id": "dm",    "role": "dm"},
        ],
    }

    result = wizard.apply_project_type(spec, "skill")

    # Return value must be a dict (per-role mapping), not None or a single string
    assert isinstance(result, dict), (
        f"apply_project_type should return a dict of role→variant, got {result!r}"
    )

    # Load the manifest to know the declared variants
    import yaml
    manifest_path = PRESETS_DIR / "software-dev" / "manifest.yaml"
    assert manifest_path.exists(), f"manifest not found at {manifest_path}"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("domain_variants", {})
    assert declared, "software-dev manifest must declare domain_variants"

    # Each agent in the spec must have the variant declared in the manifest
    for agent in spec["agents"]:
        role = agent["role"]
        if role in declared:
            assert agent.get("variant") == declared[role], (
                f"agent {agent['id']!r} (role={role!r}): "
                f"expected variant={declared[role]!r}, got {agent.get('variant')!r}"
            )


# ---------------------------------------------------------------------------
# TC-2: All roles receive domain variant — no role is skipped (happy path)
# ---------------------------------------------------------------------------

def test_tc_02_all_roles_get_variant():
    """TC-2: Every agent in a software-dev spec has a non-None variant after
    manifest-driven resolution. No role is left without a variant."""
    spec = {
        "preset": "software-dev",
        "agents": [
            {"id": "pm",    "role": "pm"},
            {"id": "skill", "role": "dev"},
            {"id": "qa",    "role": "qa"},
            {"id": "dm",    "role": "dm"},
        ],
    }

    wizard.apply_project_type(spec, "skill")

    for agent in spec["agents"]:
        assert agent.get("variant") is not None, (
            f"agent {agent['id']!r} (role={agent['role']!r}) has no variant "
            f"after manifest-driven resolution — expected all roles to receive one"
        )


# ---------------------------------------------------------------------------
# TC-3: scaffold_install writes L4 project files with structured data (happy path)
# ---------------------------------------------------------------------------

def test_tc_03_scaffold_install_writes_l4_files(tmp_path):
    """TC-3: scaffold_install creates .squidsquad/project/ and writes at least
    one structured L4 file containing mechanically-populated stack/test data."""
    # Build a minimal valid spec with scan data
    spec = {
        "squidsquad_version": "0.36.0",
        "project": {"name": "test-proj", "repo": "github.com/test/test-proj"},
        "preset": "software-dev",
        "agents": [
            {
                "id": "pm",
                "alias": "pm",
                "role": "pm",
                "stack": "pytest + Python 3.11",
                "test_command": "pytest tests/",
            },
        ],
        "tools": {},
        "loop": {"interval_minutes": 30, "context_threshold": 70},
        "flags": {"pr_flow": False, "improvement_scan": True,
                  "vault_remember": True, "diagnostics": True},
    }

    summary = wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)

    # .squidsquad/project/ directory must exist
    project_dir = tmp_path / ".squidsquad" / "project"
    assert project_dir.is_dir(), (
        f".squidsquad/project/ not created at {project_dir}"
    )

    # At least one .md file must exist in the project dir
    md_files = list(project_dir.glob("*.md"))
    assert md_files, (
        f"No .md files found in {project_dir} — scaffold_install should write "
        f"at least one structured L4 file"
    )

    # The stack details file must exist
    stack_file = project_dir / "shared-stack-details.md"
    assert stack_file.exists(), (
        f"shared-stack-details.md not found at {stack_file}"
    )

    content = stack_file.read_text(encoding="utf-8")
    # Must contain stack and test command values from scan_data
    assert "pytest" in content or "Stack" in content, (
        f"shared-stack-details.md does not contain expected stack/test data. "
        f"Content:\n{content[:500]}"
    )

    # No FAILED entries in summary
    failed = [a for a in summary.get("agents", []) if a.get("claude_md") == "FAILED"]
    assert not failed, f"scaffold_install reported FAILED agents: {failed}"


# ---------------------------------------------------------------------------
# TC-4: WIZARD.md runbook adds qualitative notes to L4 files (happy path)
# ---------------------------------------------------------------------------

def test_tc_04_wizard_md_l4_instructions():
    """TC-4: WIZARD.md references .squidsquad/project/ L4 files and directs
    the installer agent to add qualitative content (conventions, patterns)
    after the scaffold step completes."""
    assert WIZARD_MD.exists(), f"WIZARD.md not found at {WIZARD_MD}"

    content = WIZARD_MD.read_text(encoding="utf-8")

    # Must reference .squidsquad/project/ or the L4 enrichment section
    assert ".squidsquad/project/" in content, (
        "WIZARD.md must reference .squidsquad/project/ for L4 file instructions"
    )

    # Must instruct the agent to add qualitative content (conventions/patterns)
    qualitative_keywords = ["qualitative", "conventions", "Conventions"]
    assert any(kw in content for kw in qualitative_keywords), (
        "WIZARD.md must direct the installer agent to add qualitative content "
        f"(e.g. 'qualitative', 'conventions'). Keywords checked: {qualitative_keywords}"
    )

    # Must distinguish between mechanical scaffold output and agent-added content
    # (the two authorship modes)
    assert "scaffold_install" in content or "scaffold" in content.lower(), (
        "WIZARD.md must reference scaffold_install to distinguish the two "
        "authorship modes (mechanical vs. qualitative)"
    )

    # The enrichment section should reference the L4 files written by scaffold_install
    assert "shared-stack-details.md" in content or "project/" in content, (
        "WIZARD.md must reference the L4 file that scaffold_install writes "
        "(shared-stack-details.md or .squidsquad/project/)"
    )


# ---------------------------------------------------------------------------
# TC-5: "custom" project type — no domain variant, agents get L1+L2 only
# ---------------------------------------------------------------------------

def test_tc_05_custom_project_type_no_variant():
    """TC-5: When project type is 'custom', no agent receives a variant field
    and spec['project_type'] is set to 'custom'."""
    spec = {
        "preset": "software-dev",
        "agents": [
            {"id": "pm",    "role": "pm"},
            {"id": "skill", "role": "dev"},
            {"id": "qa",    "role": "qa"},
            {"id": "dm",    "role": "dm"},
        ],
    }

    result = wizard.apply_project_type(spec, "custom")

    assert result is None, (
        f"apply_project_type with 'custom' should return None, got {result!r}"
    )
    assert spec.get("project_type") == "custom", (
        f"spec['project_type'] should be 'custom', got {spec.get('project_type')!r}"
    )

    for agent in spec["agents"]:
        assert "variant" not in agent, (
            f"agent {agent['id']!r} should not have a 'variant' key for custom "
            f"project type, but got variant={agent.get('variant')!r}"
        )

    # compose_role("pm") should not include any L3 variant file in its output.
    # We verify this by checking no "variant" reference in the assembled output
    # for a fresh compose without a project install.
    # (We can't easily call compose_role against a custom install without a full
    # tmp_path setup, so we verify the spec-level contract only here.)


# ---------------------------------------------------------------------------
# TC-6: Deprecated design preset with empty role_install_order (edge case)
# ---------------------------------------------------------------------------

def test_tc_06_design_preset_empty_role_install_order():
    """TC-6: The design preset has role_install_order: [] (empty). Resolving
    domain variants returns an empty dict (no specialists, no L3 assignment)."""
    import yaml

    design_manifest_path = PRESETS_DIR / "design" / "manifest.yaml"
    assert design_manifest_path.exists(), (
        f"design/manifest.yaml not found at {design_manifest_path}"
    )

    manifest = yaml.safe_load(design_manifest_path.read_text(encoding="utf-8"))

    # role_install_order must be empty
    role_install_order = manifest.get("role_install_order", None)
    assert role_install_order == [], (
        f"design manifest role_install_order should be [], got {role_install_order!r}"
    )

    # No domain_variants key in the design preset
    assert "domain_variants" not in manifest, (
        f"design manifest should have no domain_variants field, "
        f"but got: {manifest.get('domain_variants')!r}"
    )

    # resolve_domain_variants for "design" should return empty dict
    variants = wizard.resolve_domain_variants("design")
    assert variants == {}, (
        f"resolve_domain_variants('design') should return {{}} "
        f"(no domain_variants declared), got {variants!r}"
    )

    # apply_project_type with the design preset spec should result in no variants
    spec = {
        "preset": "design",
        "agents": [
            {"id": "pm", "role": "pm"},
            {"id": "qa", "role": "qa"},
            {"id": "dm", "role": "dm"},
        ],
    }
    result = wizard.apply_project_type(spec, "design")
    # With no domain_variants in the manifest and no legacy fallback for "design",
    # result should be empty dict or None (no variants applied)
    assert not result or result == {}, (
        f"apply_project_type with design preset should return empty/None, got {result!r}"
    )
    for agent in spec["agents"]:
        assert "variant" not in agent, (
            f"agent {agent['id']!r} should have no variant for design preset "
            f"(empty role_install_order), got {agent.get('variant')!r}"
        )


# ---------------------------------------------------------------------------
# TC-7: generate_default_spec uses manifest instead of hardcoded preset
# ---------------------------------------------------------------------------

def test_tc_07_generate_default_spec_manifest_driven():
    """TC-7: generate_default_spec() returns preset='software-dev' and agent
    variants matching the manifest's domain_variants, not hardcoded strings."""
    import yaml

    spec = wizard.generate_default_spec()

    assert spec.get("preset") == "software-dev", (
        f"generate_default_spec() should return preset='software-dev', "
        f"got {spec.get('preset')!r}"
    )

    # Load the manifest and compare variants
    manifest_path = PRESETS_DIR / "software-dev" / "manifest.yaml"
    assert manifest_path.exists(), f"manifest not found at {manifest_path}"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("domain_variants", {})

    for agent in spec.get("agents", []):
        role = agent.get("role")
        if role in declared:
            assert agent.get("variant") == declared[role], (
                f"agent {agent.get('id')!r} (role={role!r}): "
                f"expected variant from manifest={declared[role]!r}, "
                f"got {agent.get('variant')!r} — variant should come from "
                f"manifest, not hardcoded"
            )


# ---------------------------------------------------------------------------
# TC-8: scaffold_install overwrite_existing guards still work for L4 files
# ---------------------------------------------------------------------------

def test_tc_08_scaffold_overwrite_guard(tmp_path):
    """TC-8: The L4 file-level overwrite guard works correctly:

    - overwrite_existing=False on a *new* install (no .squidsquad/ yet): runs OK,
      writes L4 files.
    - overwrite_existing=False when .squidsquad/ already exists: raises FileExistsError
      (the safety net documented in the smoke tests).
    - overwrite_existing=True on a second run: existing L4 files are preserved
      at the file level (because _write_l4_project_files checks file existence)
      and appear in summary['preserved'].
    """
    base_spec = {
        "squidsquad_version": "0.36.0",
        "project": {"name": "my-proj", "repo": "github.com/test/my-proj"},
        "preset": "software-dev",
        "agents": [
            {
                "id": "pm",
                "alias": "pm",
                "role": "pm",
                "stack": "first-stack",
                "test_command": "pytest",
            },
        ],
        "tools": {},
        "loop": {"interval_minutes": 30, "context_threshold": 70},
        "flags": {"pr_flow": False, "improvement_scan": True,
                  "vault_remember": True, "diagnostics": True},
    }

    # ---- Part A: overwrite_existing=False on a fresh directory raises nothing ----
    # (No .squidsquad/ yet, so no FileExistsError)
    summary1 = wizard.scaffold_install(base_spec, tmp_path, overwrite_existing=False)
    stack_file = tmp_path / ".squidsquad" / "project" / "shared-stack-details.md"
    assert stack_file.exists(), "shared-stack-details.md should exist after first install"

    # Simulate PM editing the file
    original_content = stack_file.read_text(encoding="utf-8")
    custom_content = original_content + "\n\n## Custom PM Notes\nHand-written context here.\n"
    stack_file.write_text(custom_content, encoding="utf-8")

    # ---- Part B: overwrite_existing=False when .squidsquad/ exists raises FileExistsError ----
    # (This is the documented safety net from the smoke tests)
    spec2 = {**base_spec}
    spec2["agents"] = [
        {
            "id": "pm",
            "alias": "pm",
            "role": "pm",
            "stack": "UPDATED-stack-should-not-appear",
            "test_command": "pytest",
        }
    ]
    with pytest.raises(FileExistsError):
        wizard.scaffold_install(spec2, tmp_path, overwrite_existing=False)

    # File must still contain custom content (FileExistsError prevented any writes)
    after_content = stack_file.read_text(encoding="utf-8")
    assert after_content == custom_content, (
        "shared-stack-details.md was modified despite FileExistsError being raised"
    )

    # ---- Part C: overwrite_existing=True — L4 file-level guard preserves existing files ----
    # When overwrite_existing=True, scaffold_install proceeds but _write_l4_project_files
    # checks individual file existence and skips already-written files.
    summary3 = wizard.scaffold_install(spec2, tmp_path, overwrite_existing=True)

    # The existing L4 file must still contain the custom content
    after_content3 = stack_file.read_text(encoding="utf-8")
    assert after_content3 == custom_content, (
        "shared-stack-details.md was overwritten during overwrite_existing=True re-run. "
        "_write_l4_project_files should preserve existing L4 files regardless of the "
        "directory-level overwrite_existing flag."
    )

    # The file must appear in summary['preserved']
    preserved = summary3.get("preserved", [])
    assert any("shared-stack-details.md" in p for p in preserved), (
        f"shared-stack-details.md should appear in summary['preserved'] when "
        f"it already exists, but preserved={preserved!r}"
    )


# ---------------------------------------------------------------------------
# TC-9: compose.py L4 auto-include path works with new L4 file format
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason="TC-9 tested v1's L4 filename-prefix routing of user-side "
    "`.squidsquad/project/{shared,<role>}-*.md` files. v2 L4 semantics are "
    "different — `v2_link_stage.emit_v2_linked` reads a single L4 file at "
    "`.squidsquad/project/<role_class>.md`, not a directory of prefix-routed "
    "files. The TC-9 invariant doesn't carry over. Retires with v1 in E6 "
    "#10685 Phase 3d."
)
def test_tc_09_compose_l4_role_filtering(tmp_path):
    """TC-9: compose_role() includes shared-*.md for all roles and dev-*.md
    only for the dev agent, wrapped in <!-- sub-skill: project-* --> markers."""
    # Create .squidsquad/project/ with L4 files
    project_dir = tmp_path / ".squidsquad" / "project"
    project_dir.mkdir(parents=True)

    # shared file — should appear in both dev and pm output
    (project_dir / "shared-stack-details.md").write_text(
        "## Shared Stack\n\nAll agents see this.\n",
        encoding="utf-8",
    )

    # dev-prefixed file — should appear in dev output only
    (project_dir / "dev-testing-notes.md").write_text(
        "## Dev Testing Notes\n\nDev only content here.\n",
        encoding="utf-8",
    )

    # Temporarily override REPO_ROOT in compose module so the project dir
    # is found in tmp_path
    original_repo_root = compose.REPO_ROOT
    try:
        compose.REPO_ROOT = tmp_path
        dev_out = compose.compose_role("dev")
        pm_out = compose.compose_role("pm")
    finally:
        compose.REPO_ROOT = original_repo_root

    # shared file must appear in both outputs
    assert "sub-skill: project-shared-stack-details" in dev_out, (
        "shared-stack-details.md should appear in dev agent output with "
        "<!-- sub-skill: project-shared-stack-details --> marker"
    )
    assert "sub-skill: project-shared-stack-details" in pm_out, (
        "shared-stack-details.md should appear in pm agent output with "
        "<!-- sub-skill: project-shared-stack-details --> marker"
    )

    # dev-prefixed file must appear in dev output
    assert "sub-skill: project-dev-testing-notes" in dev_out, (
        "dev-testing-notes.md should appear in dev agent output with "
        "<!-- sub-skill: project-dev-testing-notes --> marker"
    )

    # dev-prefixed file must NOT appear in pm output
    assert "sub-skill: project-dev-testing-notes" not in pm_out, (
        "dev-testing-notes.md should NOT appear in pm agent output — "
        "it is dev-role-prefixed and should be filtered out"
    )


# ---------------------------------------------------------------------------
# TC-10: TestApplyProjectType tests — PROJECT_TYPE_PRESETS not referenced
# ---------------------------------------------------------------------------

def test_tc_10_test_wizard_no_old_preset_constant():
    """TC-10: tests/test_wizard.py must not reference the old PROJECT_TYPE_PRESETS
    dict as the sole path for apply_project_type (manifest path should be primary).
    The TestApplyProjectType class should exercise manifest-driven logic."""
    test_wizard_path = TESTS_DIR / "test_wizard.py"
    assert test_wizard_path.exists(), (
        f"tests/test_wizard.py not found at {test_wizard_path}"
    )

    content = test_wizard_path.read_text(encoding="utf-8")

    # Check that TestApplyProjectType exists (was not removed entirely)
    assert "TestApplyProjectType" in content, (
        "TestApplyProjectType class should exist in tests/test_wizard.py"
    )

    # The class should reference manifest-driven logic (domain_variants or manifest)
    assert "domain_variants" in content or "manifest" in content, (
        "tests/test_wizard.py should reference manifest-driven logic "
        "(domain_variants or manifest) in TestApplyProjectType tests"
    )

    # Verify PROJECT_TYPE_PRESETS is still present in wizard.py as legacy fallback
    # (it may still be referenced in tests for the fallback path, which is expected)
    wizard_path = SCRIPTS_DIR / "wizard.py"
    wizard_content = wizard_path.read_text(encoding="utf-8")
    assert "PROJECT_TYPE_PRESETS" in wizard_content, (
        "wizard.py should still contain PROJECT_TYPE_PRESETS as legacy fallback "
        "per the post-refactor design"
    )


def test_tc_10b_run_tests_exit_zero():
    """TC-10b: python tests/run_tests.py exits 0 (full test suite passes)."""
    run_tests_path = TESTS_DIR / "run_tests.py"
    if not run_tests_path.exists():
        pytest.skip(f"tests/run_tests.py not found at {run_tests_path}")

    result = subprocess.run(
        [sys.executable, str(run_tests_path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, (
        f"tests/run_tests.py exited with code {result.returncode}.\n"
        f"stdout:\n{result.stdout[-3000:]}\n"
        f"stderr:\n{result.stderr[-2000:]}"
    )


# ---------------------------------------------------------------------------
# TC-11: Fresh install with default preset produces working agent setup (smoke)
# ---------------------------------------------------------------------------

def test_tc_11_fresh_install_smoke(tmp_path):
    """TC-11: generate_default_spec() + scaffold_install() in a fresh tmp dir
    creates the .squidsquad/ tree with agent directories, CLAUDE.md files,
    .squidsquad/project/, and no FAILED entries in summary."""
    spec = wizard.generate_default_spec()

    # scaffold_install requires a git repo for clone detection; use the actual
    # repo root so git ops don't fail, but write to tmp_path
    summary = wizard.scaffold_install(spec, tmp_path, overwrite_existing=True)

    squid_dir = tmp_path / ".squidsquad"
    assert squid_dir.is_dir(), f".squidsquad/ not created at {squid_dir}"

    # .squidsquad/project/ must exist
    project_dir = squid_dir / "project"
    assert project_dir.is_dir(), (
        f".squidsquad/project/ not created — scaffold_install should always "
        f"create this directory"
    )

    # No FAILED entries in summary
    failed = [a for a in summary.get("agents", []) if a.get("claude_md") == "FAILED"]
    assert not failed, (
        f"scaffold_install reported FAILED agents: {failed}\n"
        f"Full summary: {json.dumps(summary, indent=2)}"
    )

    # Each installed agent must have a CLAUDE.md
    for agent_summary in summary.get("agents", []):
        agent_id = agent_summary["id"]
        claude_path = Path(agent_summary["claude_md"])
        assert claude_path.exists(), (
            f"CLAUDE.md not found for agent {agent_id!r} at {claude_path}"
        )
        content = claude_path.read_text(encoding="utf-8")
        assert len(content) > 100, (
            f"CLAUDE.md for agent {agent_id!r} seems too short "
            f"({len(content)} chars) — may not have been composed properly"
        )

    # config.md must exist
    config_path = squid_dir / "config.md"
    assert config_path.exists(), f"config.md not found at {config_path}"

    # .install-spec.json must exist
    spec_path = squid_dir / ".install-spec.json"
    assert spec_path.exists(), f".install-spec.json not found at {spec_path}"
    loaded_spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert loaded_spec.get("preset") == "software-dev", (
        f"install spec preset should be 'software-dev', got {loaded_spec.get('preset')!r}"
    )
