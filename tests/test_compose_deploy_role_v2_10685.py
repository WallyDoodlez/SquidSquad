"""Tests for compose.deploy_role_v2 — wizard's v2 entry point.

E6 #10685 Phase 3c (Path B): wizard moves off v1's deploy_role onto
deploy_role_v2 so v1 deploy_role can retire in Phase 3d. These tests
pin the wizard-facing contract:

- `(role_name, target_root, output_name)` triple where output_name may
  differ from role_name (variant case).
- Triple-file write to <target_root>/.squidsquad/<output_name>/.
- Header uses output_name (not role_name).
- SOUL.md seeded from layer-base template when missing.
- Variant prefix (worker-ios) resolves to (role_class, l3_domain).
- Bypasses the `## Aliases` registry entirely (wizard knows the name
  directly; this is the gap that motivated Path B over Path C).
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import atomic_emit  # noqa: E402


@pytest.fixture(autouse=True)
def _stub_assemble_pipeline(monkeypatch):
    """Stub the LLM-backed assemble pass — same pattern as the A2f suite."""

    def fake_assemble_and_emit(
        linked_composite, output_dir, *, role_class, model_id=None,
        commit_sha=None, generated_at=None, filename_suffix="",
        **kwargs,
    ):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if filename_suffix == "":
            base, linked, conflicts = (
                "CLAUDE.md", "CLAUDE.linked.md", "CLAUDE.conflicts.md",
            )
        else:
            base = f"CLAUDE{filename_suffix}"
            linked = f"CLAUDE.linked{filename_suffix}"
            conflicts = f"CLAUDE.conflicts{filename_suffix}"
        (output_dir / base).write_text(linked_composite, encoding="utf-8")
        (output_dir / linked).write_text(linked_composite, encoding="utf-8")
        (output_dir / conflicts).write_text(
            "# Stub conflicts report — assemble bypassed in tests\n",
            encoding="utf-8",
        )
        return (
            output_dir / base,
            output_dir / linked,
            output_dir / conflicts,
        )

    monkeypatch.setattr(atomic_emit, "assemble_and_emit", fake_assemble_and_emit)


@pytest.fixture(autouse=True)
def _stub_soul_seeding(monkeypatch):
    """Stub _assemble_and_write_soul so tests don't need the full v1 layered
    SOUL fixture — the wedge under test is "is it called", not "what it writes"."""

    def fake_assemble_and_write_soul(role_name, target_root, output_name):
        soul_path = Path(target_root) / ".squidsquad" / output_name / "SOUL.md"
        soul_path.parent.mkdir(parents=True, exist_ok=True)
        soul_path.write_text(
            f"# Stub SOUL.md for {output_name} (role={role_name})\n",
            encoding="utf-8",
        )
        return soul_path

    monkeypatch.setattr(
        compose, "_assemble_and_write_soul", fake_assemble_and_write_soul,
    )


def _frontmatter(slot, ordinal, roles=None):
    lines = ["---", f"slot: {slot}", f"ordinal: {ordinal}"]
    if roles is not None:
        lines.append(f"roles: [{', '.join(roles)}]")
    lines.append("---")
    return "\n".join(lines)


def _write_source(path, slot, ordinal, body, roles=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _frontmatter(slot, ordinal, roles=roles) + "\n\n" + body
    path.write_text(text, encoding="utf-8")


def _stage_install(tmp_path, role_class="pm", l3_variant=None):
    """Stage a minimal install. NOTE: no `## Aliases` section — deploy_role_v2
    must work without one (that's the whole point of Path B)."""
    refs = tmp_path / "references"
    # L1
    _write_source(refs / "roles" / "identity.md", "identity", 10, "Identity base.")
    _write_source(refs / "roles" / "responsibility.md", "responsibility", 10, "Responsibility base.")
    _write_source(refs / "roles" / "SOUL.md", "soul", 10, "Soul base.")
    _write_source(
        refs / "roles" / "instructions.md", "instructions", 10,
        "### step:cycle/boot\nBoot body.\n",
    )
    _write_source(refs / "roles" / "vault.md", "vault", 10, "Vault base.")
    # L2 (role-class)
    _write_source(
        refs / "roles" / role_class / "instructions.md", "instructions", 20,
        "### step:cycle/work\nWork body.\n",
        roles=[role_class],
    )
    # L3 (variant) — only when caller passes one
    if l3_variant:
        _write_source(
            refs / "roles" / role_class / l3_variant / "instructions.md",
            "instructions", 30,
            "### step:cycle/variant\nVariant body.\n",
            roles=[role_class],
        )

    catalog = tmp_path / "docs" / "sub-skill-catalog.md"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(
        "## `common/` — Cross-cutting\n\n"
        "| Sub-skill | One-liner | Used by |\n"
        "|---|---|---|\n"
        "| `boot-bootstrap` | Mode detection | all |\n",
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Triple write — wizard's primary contract
# ---------------------------------------------------------------------------

def test_deploy_role_v2_writes_triple_under_output_name(tmp_path):
    """output_name (not role_name) selects the agent directory."""
    _stage_install(tmp_path, role_class="pm")
    out = compose.deploy_role_v2(
        "pm", target_root=tmp_path, output_name="peggy",
        source_root=tmp_path,
    )
    agent_dir = tmp_path / ".squidsquad" / "peggy"
    assert out == agent_dir / "CLAUDE.md"
    assert out.exists()
    assert (agent_dir / "CLAUDE.linked.md").exists()
    assert (agent_dir / "CLAUDE.conflicts.md").exists()
    # No leak into a role_name-named dir.
    assert not (tmp_path / ".squidsquad" / "pm").exists()


def test_deploy_role_v2_defaults_output_name_to_role_name(tmp_path):
    _stage_install(tmp_path, role_class="pm")
    out = compose.deploy_role_v2("pm", target_root=tmp_path, source_root=tmp_path)
    assert out == tmp_path / ".squidsquad" / "pm" / "CLAUDE.md"


# ---------------------------------------------------------------------------
# Header uses output_name — important for regenerate hint correctness
# ---------------------------------------------------------------------------

def test_deploy_role_v2_header_uses_output_name(tmp_path):
    _stage_install(tmp_path, role_class="pm")
    out = compose.deploy_role_v2(
        "pm", target_root=tmp_path, output_name="peggy",
        source_root=tmp_path,
    )
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# SquidSquad -- peggy Lead\n")
    assert "GENERATED by compose.py deploy peggy." in text
    assert "deploy peggy" in text  # regenerate hint
    # role_name should NOT leak into the header.
    assert "deploy pm." not in text


# ---------------------------------------------------------------------------
# SOUL.md seeding — wizard depends on this
# ---------------------------------------------------------------------------

def test_deploy_role_v2_seeds_soul_when_missing(tmp_path):
    _stage_install(tmp_path, role_class="pm")
    compose.deploy_role_v2("pm", target_root=tmp_path, output_name="peggy")
    soul = tmp_path / ".squidsquad" / "peggy" / "SOUL.md"
    assert soul.exists()
    assert "peggy" in soul.read_text(encoding="utf-8")


def test_deploy_role_v2_preserves_existing_soul(tmp_path):
    """Re-deploy must not clobber an existing SOUL — operators customize it."""
    _stage_install(tmp_path, role_class="pm")
    agent_dir = tmp_path / ".squidsquad" / "peggy"
    agent_dir.mkdir(parents=True, exist_ok=True)
    existing_soul = agent_dir / "SOUL.md"
    existing_soul.write_text("# Custom SOUL — do not overwrite\n", encoding="utf-8")

    compose.deploy_role_v2("pm", target_root=tmp_path, output_name="peggy")

    assert existing_soul.read_text(encoding="utf-8") == (
        "# Custom SOUL — do not overwrite\n"
    )


# ---------------------------------------------------------------------------
# No `## Aliases` registry required — Path B's defining behavior
# ---------------------------------------------------------------------------

def test_deploy_role_v2_requires_no_aliases_registry(tmp_path):
    """Fresh wizard install has no `## Aliases` section. deploy_role_v2 must
    succeed regardless — this is the gap that motivated Path B over Path C."""
    _stage_install(tmp_path, role_class="pm")
    # Explicitly assert no config.md exists.
    assert not (tmp_path / ".squidsquad" / "config.md").exists()
    # Must not raise.
    out = compose.deploy_role_v2("pm", target_root=tmp_path, output_name="peggy")
    assert out.exists()


# ---------------------------------------------------------------------------
# Variant resolution — worker-ios → (role_class=worker, l3_domain=ios)
# ---------------------------------------------------------------------------

def test_deploy_role_v2_resolves_variant_to_role_and_l3(tmp_path, monkeypatch):
    """Variant-prefixed role_name routes through _resolve_variant and the L3
    sources for the variant get walked into the link stage."""
    _stage_install(tmp_path, role_class="pm", l3_variant="ios")

    captured = {}

    real_collect = compose.__dict__.get("collect_sources_for_validation")
    import v2_link_stage
    real_collect = v2_link_stage.collect_sources_for_validation

    def spy_collect(role_class, l3_domain, *, repo_root=None):
        captured["role_class"] = role_class
        captured["l3_domain"] = l3_domain
        return real_collect(role_class, l3_domain, repo_root=repo_root)

    monkeypatch.setattr(
        v2_link_stage, "collect_sources_for_validation", spy_collect,
    )

    compose.deploy_role_v2(
        "pm-ios", target_root=tmp_path, output_name="peggy",
        source_root=tmp_path,
    )
    assert captured == {"role_class": "pm", "l3_domain": "ios"}


# ---------------------------------------------------------------------------
# Wizard contract — source_root=REPO_ROOT, target_root=fresh project dir
# ---------------------------------------------------------------------------

def test_deploy_role_v2_wizard_contract_source_root_split(tmp_path):
    """The wizard installs into a foreign project (target_root) but reads
    templates from REPO_ROOT (source_root default). target_root has neither
    references/ nor docs/ — must still succeed."""
    # NO references/ or docs/ staged under tmp_path — it's a fresh project.
    assert not (tmp_path / "references").exists()
    assert not (tmp_path / "docs").exists()
    out = compose.deploy_role_v2(
        "pm", target_root=tmp_path, output_name="peggy",
        # source_root defaults to REPO_ROOT — the real templates.
    )
    assert out == tmp_path / ".squidsquad" / "peggy" / "CLAUDE.md"
    assert out.exists()


def test_deploy_role_v2_no_variant_l3_is_none(tmp_path, monkeypatch):
    """Bare role_name (no hyphen) resolves with l3_domain=None."""
    _stage_install(tmp_path, role_class="pm")

    captured = {}
    import v2_link_stage
    real_collect = v2_link_stage.collect_sources_for_validation

    def spy_collect(role_class, l3_domain, *, repo_root=None):
        captured["role_class"] = role_class
        captured["l3_domain"] = l3_domain
        return real_collect(role_class, l3_domain, repo_root=repo_root)

    monkeypatch.setattr(
        v2_link_stage, "collect_sources_for_validation", spy_collect,
    )

    compose.deploy_role_v2(
        "pm", target_root=tmp_path, output_name="pm", source_root=tmp_path,
    )
    assert captured == {"role_class": "pm", "l3_domain": None}
