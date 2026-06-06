"""Tests for references/scripts/v2_link_stage.py (#10490, PRD-A Story A2d)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import v2_link_stage as v2  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _frontmatter(slot, ordinal, roles=None):
    lines = ["---", f"slot: {slot}", f"ordinal: {ordinal}"]
    if roles is not None:
        lines.append(f"roles: [{', '.join(roles)}]")
    lines.append("---")
    return "\n".join(lines)


def _make_source(path, slot, ordinal, body, roles=None):
    """Write a fixture source file with the given frontmatter + body."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _frontmatter(slot, ordinal, roles=roles) + "\n\n" + body
    path.write_text(text, encoding="utf-8")


def _make_minimal_fixture(repo_root):
    """A minimal fixture with at least one file per slot under role_class=worker.

    Layout:
      references/roles/identity.md       slot=identity ord=10 — "Base identity"
      references/roles/SOUL.md           slot=soul ord=10     — "Base soul"
      references/roles/instructions.md   slot=instructions ord=10 — body
      references/roles/vault.md          slot=vault ord=10    — "Vault content"
      references/roles/worker/responsibility.md  slot=responsibility ord=20 — "Worker resp"
      references/roles/worker/instructions.md    slot=instructions ord=20 — body w/ step
    """
    refs = repo_root / "references"
    _make_source(refs / "roles" / "identity.md", "identity", 10, "Base identity prose.")
    _make_source(refs / "roles" / "SOUL.md", "soul", 10, "Base soul prose.")
    _make_source(
        refs / "roles" / "instructions.md", "instructions", 10,
        "### step:cycle/boot\nBoot the agent.\n",
    )
    _make_source(refs / "roles" / "vault.md", "vault", 10, "Vault content.")
    _make_source(
        refs / "roles" / "worker" / "responsibility.md", "responsibility", 20,
        "Worker is responsible for implementation.",
    )
    _make_source(
        refs / "roles" / "worker" / "instructions.md", "instructions", 20,
        "### step:cycle/work\nDo the work.\n",
        roles=["worker"],
    )


# ---------------------------------------------------------------------------
# AC: six H2 sections in canonical order
# ---------------------------------------------------------------------------

def test_emit_v2_linked_returns_string(tmp_path):
    _make_minimal_fixture(tmp_path)
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    assert isinstance(out, str)


def test_emit_v2_linked_emits_exactly_six_h2_sections_in_canonical_order(tmp_path):
    _make_minimal_fixture(tmp_path)
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    h2_lines = [ln for ln in out.splitlines() if ln.startswith("## ")]
    assert h2_lines == [
        "## Identity",
        "## Responsibility",
        "## Soul",
        "## Instructions",
        "## Project Context",
        "## Vault",
    ]


def test_emit_v2_linked_emits_empty_section_for_absent_slot(tmp_path):
    """Project Context has no L1-L3 sources in the minimal fixture and no L4 — section is still emitted, empty."""
    _make_minimal_fixture(tmp_path)
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    assert "## Project Context\n" in out


# ---------------------------------------------------------------------------
# AC: walks L1-L3 + groups + sorts by ordinal
# ---------------------------------------------------------------------------

def test_emit_v2_linked_groups_by_slot(tmp_path):
    _make_minimal_fixture(tmp_path)
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    # The two instructions-slot sources are in the Instructions section.
    idx_instructions = out.index("## Instructions")
    idx_project_ctx = out.index("## Project Context")
    instructions_block = out[idx_instructions:idx_project_ctx]
    assert "### step:cycle/boot" in instructions_block
    assert "### step:cycle/work" in instructions_block


def test_emit_v2_linked_sorts_within_slot_by_ordinal(tmp_path):
    """Lower ordinal precedes higher ordinal within the same slot."""
    refs = tmp_path / "references"
    _make_source(refs / "roles" / "identity.md", "identity", 30, "LAST identity.")
    _make_source(refs / "roles" / "worker" / "ident_a.md", "identity", 10, "FIRST identity.")
    _make_source(refs / "roles" / "worker" / "ident_b.md", "identity", 20, "MIDDLE identity.")
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    pos_first = out.index("FIRST identity")
    pos_middle = out.index("MIDDLE identity")
    pos_last = out.index("LAST identity")
    assert pos_first < pos_middle < pos_last


# ---------------------------------------------------------------------------
# AC: applies A2c L4 op processing per slot
# ---------------------------------------------------------------------------

def test_emit_v2_linked_applies_l4_replace_step_op(tmp_path):
    """A L4 `### replace step:cycle/work` replaces only the work step's body."""
    _make_minimal_fixture(tmp_path)
    l4_path = tmp_path / "l4.md"
    l4_path.write_text(
        "## Instructions\n\n"
        "### replace step:cycle/work\n\n"
        "Do something DIFFERENT.\n",
        encoding="utf-8",
    )
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path, l4_path=l4_path)
    assert "Do something DIFFERENT." in out
    assert "Do the work." not in out  # body replaced
    # Other slots untouched.
    assert "Base identity prose." in out


def test_emit_v2_linked_missing_l4_is_noop(tmp_path):
    """No L4 file → L1-L3 content survives unchanged."""
    _make_minimal_fixture(tmp_path)
    out = v2.emit_v2_linked(
        "worker", None,
        repo_root=tmp_path,
        l4_path=tmp_path / "nonexistent.md",
    )
    assert "Do the work." in out
    assert "Base identity prose." in out


# ---------------------------------------------------------------------------
# AC: byte-stable across re-runs
# ---------------------------------------------------------------------------

def test_emit_v2_linked_byte_stable_across_runs(tmp_path):
    """Same inputs → identical output, byte-for-byte. Required by AC."""
    _make_minimal_fixture(tmp_path)
    a = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    b = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    c = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    assert a == b == c


# ---------------------------------------------------------------------------
# Behavioral: skip unmigrated files (no frontmatter)
# ---------------------------------------------------------------------------

def test_emit_v2_linked_skips_files_without_frontmatter(tmp_path):
    """Files without YAML frontmatter (unmigrated under #10394) are skipped."""
    refs = tmp_path / "references"
    (refs / "roles").mkdir(parents=True)
    # File without frontmatter — should NOT appear in any slot.
    (refs / "roles" / "no_frontmatter.md").write_text(
        "Just prose, no frontmatter. This SHOULD NOT appear.\n",
        encoding="utf-8",
    )
    # File with frontmatter — should appear.
    _make_source(refs / "roles" / "identity.md", "identity", 10, "DOES appear.")
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    assert "DOES appear." in out
    assert "SHOULD NOT appear" not in out


# ---------------------------------------------------------------------------
# Behavioral: roles: extras filter
# ---------------------------------------------------------------------------

def test_emit_v2_linked_respects_roles_extras_filter(tmp_path):
    """Files with roles: [other_role] are excluded for this role_class."""
    refs = tmp_path / "references"
    _make_source(
        refs / "roles" / "identity.md", "identity", 10,
        "Universal identity.",  # no roles filter
    )
    _make_source(
        refs / "sub-skills" / "common" / "pm_only.md", "identity", 20,
        "PM only.", roles=["pm"],
    )
    _make_source(
        refs / "sub-skills" / "common" / "worker_only.md", "identity", 30,
        "Worker only.", roles=["worker"],
    )
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    assert "Universal identity." in out
    assert "Worker only." in out
    assert "PM only." not in out


# ---------------------------------------------------------------------------
# Behavioral: L3 domain scoping
# ---------------------------------------------------------------------------

def test_emit_v2_linked_includes_l3_domain_files(tmp_path):
    """When l3_domain is provided, files under that subdir are included."""
    refs = tmp_path / "references"
    _make_source(
        refs / "roles" / "worker" / "skill" / "identity.md", "identity", 30,
        "Skill-domain identity.",
    )
    out = v2.emit_v2_linked("worker", "skill", repo_root=tmp_path)
    assert "Skill-domain identity." in out


def test_emit_v2_linked_excludes_other_l3_domain_files(tmp_path):
    """L3 files under a DIFFERENT l3_domain subdir are NOT included."""
    refs = tmp_path / "references"
    _make_source(
        refs / "roles" / "worker" / "ios" / "identity.md", "identity", 30,
        "iOS identity.",
    )
    _make_source(
        refs / "roles" / "worker" / "skill" / "identity.md", "identity", 30,
        "Skill identity.",
    )
    out = v2.emit_v2_linked("worker", "skill", repo_root=tmp_path)
    assert "Skill identity." in out
    assert "iOS identity." not in out


def test_emit_v2_linked_l3_none_excludes_all_l3_files(tmp_path):
    """With l3_domain=None, no L3 subdir files are walked."""
    refs = tmp_path / "references"
    _make_source(
        refs / "roles" / "worker" / "skill" / "identity.md", "identity", 30,
        "Skill identity.",
    )
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    assert "Skill identity." not in out


# ---------------------------------------------------------------------------
# Helpers: _strip_frontmatter
# ---------------------------------------------------------------------------

def test_strip_frontmatter_removes_block():
    text = "---\nslot: identity\nordinal: 10\n---\n\nBody here."
    # The frontmatter regex consumes one trailing newline; bodies with a
    # blank line after the closing `---` retain that blank line, which
    # `_join_bodies` strips via its `.strip()` call downstream.
    assert v2._strip_frontmatter(text).strip() == "Body here."
    assert "slot: identity" not in v2._strip_frontmatter(text)


def test_strip_frontmatter_no_op_when_absent():
    text = "Just body.\n"
    assert v2._strip_frontmatter(text) == text


# ---------------------------------------------------------------------------
# Helpers: canonical-slot constants
# ---------------------------------------------------------------------------

def test_canonical_slot_order_is_six():
    """AC says 'exactly six H2 sections in canonical order'."""
    assert len(v2.CANONICAL_SLOT_ORDER) == 6


def test_canonical_slot_order_matches_trd():
    assert v2.CANONICAL_SLOT_ORDER == (
        "identity",
        "responsibility",
        "soul",
        "instructions",
        "project-context",
        "vault",
    )


# ---------------------------------------------------------------------------
# #11227: inline op extraction from L1-L3 source bodies
# ---------------------------------------------------------------------------

def test_extract_inline_ops_no_ops_passes_through():
    body = "Just some prose.\n\n## Some H2 header\n\nMore prose.\n"
    cleaned, ops = v2._extract_inline_ops(body)
    assert cleaned == body
    assert ops == []


def test_extract_inline_ops_empty_body_returns_empty():
    cleaned, ops = v2._extract_inline_ops("")
    assert cleaned == ""
    assert ops == []


def test_extract_inline_ops_insert_after_extracted():
    body = (
        "Lead prose.\n"
        "\n"
        "### insert-after step:cycle/work\n"
        "\n"
        "Op body line 1.\n"
        "Op body line 2.\n"
    )
    cleaned, ops = v2._extract_inline_ops(body)
    assert cleaned == "Lead prose.\n\n"
    assert len(ops) == 1
    assert ops[0].op_type == "insert-after"
    assert ops[0].target_step_id == "work"
    assert "Op body line 1." in ops[0].body_text
    assert "Op body line 2." in ops[0].body_text


def test_extract_inline_ops_insert_before_extracted():
    body = "### insert-before step:cycle/cleanup\n\nBefore-cleanup content.\n"
    _, ops = v2._extract_inline_ops(body)
    assert ops[0].op_type == "insert-before"
    assert ops[0].target_step_id == "cleanup"


def test_extract_inline_ops_replace_step_extracted():
    body = "### replace step:cycle/pickup\n\nReplacement body.\n"
    _, ops = v2._extract_inline_ops(body)
    assert ops[0].op_type == "replace"
    assert ops[0].target_step_id == "pickup"
    assert ops[0].body_text == "Replacement body."


def test_extract_inline_ops_bare_append_extracted():
    body = "### append\n\nAppended content.\n"
    _, ops = v2._extract_inline_ops(body)
    assert ops[0].op_type == "append"
    assert ops[0].target_step_id is None


def test_extract_inline_ops_bare_replace_extracted():
    body = "### replace\n\nWhole-slot replacement.\n"
    _, ops = v2._extract_inline_ops(body)
    assert ops[0].op_type == "replace"
    assert ops[0].target_step_id is None


def test_extract_inline_ops_multiple_ops_in_source_order():
    body = (
        "Prose before any op.\n"
        "\n"
        "### insert-after step:cycle/resume\n"
        "\n"
        "First op body.\n"
        "\n"
        "### insert-after step:cycle/work\n"
        "\n"
        "Second op body.\n"
        "\n"
        "### append\n"
        "\n"
        "Third op body.\n"
    )
    cleaned, ops = v2._extract_inline_ops(body)
    assert cleaned == "Prose before any op.\n\n"
    assert [op.op_type for op in ops] == ["insert-after", "insert-after", "append"]
    assert [op.target_step_id for op in ops] == ["resume", "work", None]
    assert "First op body." in ops[0].body_text
    assert "Second op body." in ops[1].body_text
    assert "Third op body." in ops[2].body_text


def test_extract_inline_ops_non_op_h3_in_pre_op_body():
    """A regular H3 sub-heading is NOT an op directive."""
    body = (
        "### Regular Sub-Heading\n"
        "\n"
        "This stays in cleaned_body.\n"
        "\n"
        "### insert-after step:cycle/work\n"
        "\n"
        "Op body.\n"
    )
    cleaned, ops = v2._extract_inline_ops(body)
    assert "### Regular Sub-Heading" in cleaned
    assert "This stays in cleaned_body." in cleaned
    assert len(ops) == 1
    assert ops[0].op_type == "insert-after"


def test_extract_inline_ops_h4_step_heading_inside_op_body():
    """H4 sub-step headings inside an op body are NOT extracted as ops."""
    body = (
        "### insert-after step:cycle/work\n"
        "\n"
        "#### step:cycle/sub-task\n"
        "\n"
        "Sub-task body.\n"
    )
    cleaned, ops = v2._extract_inline_ops(body)
    assert cleaned == ""
    assert len(ops) == 1
    assert "#### step:cycle/sub-task" in ops[0].body_text
    assert "Sub-task body." in ops[0].body_text


def test_extract_inline_ops_op_body_trailing_newlines_stripped():
    body = "### append\n\nContent.\n\n\n\n"
    _, ops = v2._extract_inline_ops(body)
    assert ops[0].body_text == "Content."


# ---------------------------------------------------------------------------
# #11227: end-to-end op application across L1-L4 layers
# ---------------------------------------------------------------------------

def test_emit_v2_linked_applies_l2_insert_after_step_op(tmp_path):
    """L2 source `### insert-after step:cycle/work` anchors to L1 H3."""
    repo = tmp_path
    (repo / "references" / "sub-skills" / "common").mkdir(parents=True)
    (repo / "references" / "roles" / "pm").mkdir(parents=True)
    # L1 base provides the step:cycle/work anchor at H3.
    _make_source(
        repo / "references" / "roles" / "instructions.md",
        slot="instructions",
        ordinal=10,
        body="### step:cycle/work\n\nL1 base body for work step.\n",
    )
    # L2 PM extends with an op that anchors to it.
    _make_source(
        repo / "references" / "roles" / "pm" / "instructions.md",
        slot="instructions",
        ordinal=20,
        roles=["pm"],
        body=(
            "### insert-after step:cycle/work\n"
            "\n"
            "#### step:cycle/check-in\n"
            "\n"
            "PM-only check-in content.\n"
        ),
    )
    result = v2.emit_v2_linked("pm", None, repo_root=repo)
    assert "### step:cycle/work" in result
    assert "L1 base body for work step." in result
    # The L2 op's content must appear AFTER the L1 anchor.
    work_idx = result.index("### step:cycle/work")
    checkin_idx = result.index("#### step:cycle/check-in")
    assert work_idx < checkin_idx
    assert "PM-only check-in content." in result
