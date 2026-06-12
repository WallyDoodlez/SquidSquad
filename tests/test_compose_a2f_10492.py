"""Tests for compose.py deploy_alias_v2 wiring of v2 link stage (#10492, PRD-A A2f)."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import v2_link_stage as v2  # noqa: E402
import atomic_emit  # noqa: E402 — needed for the assemble stub fixture
from link_stage_validator import LinkStageValidationError  # noqa: E402


@pytest.fixture(autouse=True)
def _stub_assemble_pipeline(monkeypatch):
    """A2f tests exercise the v2 LINK stage. PRD-B B9 (#10763) wires
    the assemble pipeline into ``deploy_alias_v2`` after the link
    stage returns; without a real LLM provider those tests would now
    fail. Stub ``atomic_emit.assemble_and_emit`` to write the linked
    composite verbatim into all three v2 paths so the A2f tests can
    keep asserting on what the link stage emitted."""

    def fake_assemble_and_emit(
        linked_composite, output_dir, *, role_class, model_id=None,
        commit_sha=None, generated_at=None, filename_suffix=".v2.md",
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


# ---------------------------------------------------------------------------
# Helpers — minimal fixture install under tmp_path
# ---------------------------------------------------------------------------

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


def _stage_minimal_install(tmp_path, alias="pm", role="pm"):
    """Stage a tiny fixture install: 6 slots covered, an alias registry, a clean L4."""
    refs = tmp_path / "references"
    # L1 — base files (one per slot for the canonical six).
    _write_source(refs / "roles" / "identity.md", "identity", 10, "Identity base.")
    _write_source(refs / "roles" / "responsibility.md", "responsibility", 10, "Responsibility base.")
    _write_source(refs / "roles" / "SOUL.md", "soul", 10, "Soul base.")
    _write_source(
        refs / "roles" / "instructions.md", "instructions", 10,
        "### step:cycle/boot\nBoot body.\n",
    )
    _write_source(refs / "roles" / "vault.md", "vault", 10, "Vault base.")
    # L2 — role-class.
    _write_source(
        refs / "roles" / role / "instructions.md", "instructions", 20,
        "### step:cycle/work\nWork body.\n",
        roles=[role],
    )

    # PRD-D D3 (#10674) catalog gate: deploy_alias_v2 now consults
    # docs/sub-skill-catalog.md after emit_v2_linked. The fixture's
    # instructions slot doesn't emit any `→ run sub-skill:` references
    # (just `### step:` markers and prose), so a minimal one-section
    # catalog with at least one valid row is enough to pass the gate.
    catalog = tmp_path / "docs" / "sub-skill-catalog.md"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(
        "## `common/` — Cross-cutting\n\n"
        "| Sub-skill | One-liner | Used by |\n"
        "|---|---|---|\n"
        "| `boot-bootstrap` | Mode detection | all |\n",
        encoding="utf-8",
    )

    # Aliases registry: alias -> role (no L3 domain).
    # #10751 W1: canonical column header is `| alias | role-class |
    # L3 domain |` (lowercase, hyphen). The previous "Role class" with
    # space silently fell through `parse_aliases_registry`'s strict
    # comparison and only passed in this test because the test bypasses
    # the parser via a pre-built registry dict elsewhere.
    config_md = tmp_path / ".squidsquad" / "config.md"
    config_md.parent.mkdir(parents=True, exist_ok=True)
    config_md.write_text(
        "## Aliases\n\n"
        "| alias | role-class | L3 domain |\n"
        "|---|---|---|\n"
        f"| {alias} | {role} | |\n",
        encoding="utf-8",
    )

    return tmp_path


def _mk_registry(alias_to_role):
    """Build a registry dict matching parse_aliases_registry's contract."""
    return {alias: (role, None) for alias, role in alias_to_role.items()}


# ---------------------------------------------------------------------------
# AC: deploy_alias_v2 calls emit_v2_linked + writes the file
# ---------------------------------------------------------------------------

def test_deploy_alias_v2_writes_to_canonical_v2_path(tmp_path):
    _stage_minimal_install(tmp_path)
    registry = _mk_registry({"pm": "pm"})
    out = compose.deploy_alias_v2("pm", registry=registry, target_root=tmp_path)
    # PRD-B B9 (#10763): deploy_alias_v2 now returns the assembled
    # ``CLAUDE.v2.md`` (the runtime artifact agents actually read).
    # The linked composite sits beside it at CLAUDE.linked.v2.md and
    # the conflict report at CLAUDE.conflicts.v2.md — all three are
    # written by atomic_emit.assemble_and_emit.
    alias_dir = tmp_path / ".squidsquad" / "pm"
    assert out == alias_dir / "CLAUDE.v2.md"
    assert out.exists()
    assert (alias_dir / "CLAUDE.linked.v2.md").exists()
    assert (alias_dir / "CLAUDE.conflicts.v2.md").exists()


def test_deploy_alias_v2_output_contains_six_canonical_h2_sections(tmp_path):
    """AC: 'compose.py deploy pm --v2 produces a CLAUDE.linked.v2.md containing the six canonical H2 slots in order'."""
    _stage_minimal_install(tmp_path)
    registry = _mk_registry({"pm": "pm"})
    out = compose.deploy_alias_v2("pm", registry=registry, target_root=tmp_path)
    text = out.read_text(encoding="utf-8")
    h2_lines = [ln for ln in text.splitlines() if ln.startswith("## ")]
    assert h2_lines == [
        "## Identity",
        "## Responsibility",
        "## Soul",
        "## Agent Functions",
        "## Project Context",
        "## Vault",
    ]


def test_deploy_alias_v2_emits_generated_header(tmp_path):
    """Output carries the standard `# SquidSquad -- <alias> Lead` + DO NOT EDIT block.

    Post-E6 cutover (#10685) the regenerate hint is the bare ``deploy <alias>`` form;
    the pre-cutover ``--v2`` flag is retired.
    """
    _stage_minimal_install(tmp_path, alias="pm", role="pm")
    registry = _mk_registry({"pm": "pm"})
    out = compose.deploy_alias_v2("pm", registry=registry, target_root=tmp_path)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# SquidSquad -- pm Lead\n")
    assert "GENERATED by compose.py deploy pm." in text
    assert "--v2" not in text


# ---------------------------------------------------------------------------
# AC: validation runs BEFORE write — abort path preserved (zero partial artifacts)
# ---------------------------------------------------------------------------

def test_deploy_alias_v2_aborts_on_validation_failure_and_writes_nothing(tmp_path, capsys):
    """R2 violation: L2 source declares slot: vault. v2 path must abort BEFORE the write."""
    _stage_minimal_install(tmp_path, alias="pm", role="pm")
    # Inject the violation.
    refs = tmp_path / "references"
    _write_source(refs / "roles" / "pm" / "rogue_vault.md", "vault", 20, "Should not be here.")
    registry = _mk_registry({"pm": "pm"})
    expected_out = tmp_path / ".squidsquad" / "pm" / "CLAUDE.linked.v2.md"
    with pytest.raises(SystemExit) as exc:
        compose.deploy_alias_v2("pm", registry=registry, target_root=tmp_path)
    assert exc.value.code == 1
    # AC: zero partial artifacts.
    assert not expected_out.exists()
    err = capsys.readouterr().err
    assert "validation failed" in err
    assert "R2" in err


def test_deploy_alias_v2_aborts_on_r5_unknown_step_id(tmp_path, capsys):
    """R5: L4 op targets a step ID that doesn't exist in L1-L3."""
    _stage_minimal_install(tmp_path, alias="pm", role="pm")
    l4_path = tmp_path / ".squidsquad" / "project" / "pm.md"
    l4_path.parent.mkdir(parents=True, exist_ok=True)
    l4_path.write_text(
        "## Agent Functions\n\n"
        "### replace step:cycle/ghost\n\n"
        "Ghost body.\n",
        encoding="utf-8",
    )
    registry = _mk_registry({"pm": "pm"})
    expected_out = tmp_path / ".squidsquad" / "pm" / "CLAUDE.linked.v2.md"
    with pytest.raises(SystemExit) as exc:
        compose.deploy_alias_v2("pm", registry=registry, target_root=tmp_path)
    assert exc.value.code == 1
    assert not expected_out.exists()
    err = capsys.readouterr().err
    assert "R5" in err
    assert "ghost" in err


# ---------------------------------------------------------------------------
# AC: L4 absent is a no-op (L1-L3 only)
# ---------------------------------------------------------------------------

def test_deploy_alias_v2_no_l4_file_is_noop(tmp_path):
    _stage_minimal_install(tmp_path, alias="pm", role="pm")
    registry = _mk_registry({"pm": "pm"})
    # Confirm no L4 file is staged.
    assert not (tmp_path / ".squidsquad" / "project" / "pm.md").exists()
    out = compose.deploy_alias_v2("pm", registry=registry, target_root=tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "Boot body." in text  # L1 content survives
    assert "Work body." in text  # L2 content survives


# ---------------------------------------------------------------------------
# A2f's v1 byte-stability assertion (test_v1_deploy_role_signature_unchanged)
# retired in E6 #10685 Phase 3d.4 — v1 ``deploy_role`` was deleted.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# AC: existing A6 tests still pass (test_compose_a6_v2 lives separately)
# ---------------------------------------------------------------------------

def test_a6_v2_tests_still_pass():
    """Run the existing A6 test module as a smoke check — A2f must not regress it."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_compose_a6_v2.py", "--tb=short"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"A6 tests regressed under A2f\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Behavioral: L3 domain alias resolves correctly
# ---------------------------------------------------------------------------

def test_deploy_alias_v2_with_l3_domain_includes_l3_files(tmp_path):
    """Registry maps alias -> (role_class, l3_domain); A2f forwards both to A2d."""
    _stage_minimal_install(tmp_path, alias="skill", role="worker")
    # Stage an L3 file that should appear only with l3_domain="skill".
    refs = tmp_path / "references"
    _write_source(
        refs / "roles" / "worker" / "skill" / "identity.md", "identity", 30,
        "Worker-skill domain identity.",
    )
    # Override registry to include l3_domain.
    registry = {"skill": ("worker", "skill")}
    out = compose.deploy_alias_v2("skill", registry=registry, target_root=tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "Worker-skill domain identity." in text


# ---------------------------------------------------------------------------
# Helper: collect_sources_for_validation correctness
# ---------------------------------------------------------------------------

def test_collect_sources_for_validation_classifies_layers(tmp_path):
    _stage_minimal_install(tmp_path, alias="pm", role="pm")
    sources = v2.collect_sources_for_validation("pm", None, repo_root=tmp_path)
    by_path = {s.path: s for s in sources}
    # L1 — top-level roles/*.md.
    assert by_path["references/roles/identity.md"].layer == "L1"
    # L2 — roles/pm/*.md (direct child).
    assert by_path["references/roles/pm/instructions.md"].layer == "L2"


def test_collect_sources_for_validation_classifies_l3_subdir(tmp_path):
    refs = tmp_path / "references"
    _write_source(
        refs / "roles" / "worker" / "skill" / "identity.md", "identity", 30,
        "Skill identity.",
    )
    sources = v2.collect_sources_for_validation("worker", "skill", repo_root=tmp_path)
    layers = {s.path: s.layer for s in sources}
    assert layers["references/roles/worker/skill/identity.md"] == "L3"


def test_collect_sources_for_validation_skips_unmigrated(tmp_path):
    """Files without frontmatter return no LinkStageSource — same skip rule as A2d."""
    refs = tmp_path / "references"
    (refs / "roles").mkdir(parents=True)
    (refs / "roles" / "no_fm.md").write_text("no frontmatter here\n", encoding="utf-8")
    sources = v2.collect_sources_for_validation("pm", None, repo_root=tmp_path)
    assert all("no_fm.md" not in s.path for s in sources)
