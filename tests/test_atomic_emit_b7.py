"""Tests for references/scripts/atomic_emit.py.

Post-#11050 prune: the LLM assemble pipeline is gone. ``_VERBATIM_SLOTS``
covers all six canonical slots, so every slot's linked body passes
through verbatim and there is no LLM dispatch, preservation check,
conflict resolver, or per-slot cache. The tests below cover only the
surviving surfaces — slot split, verbatim copy, atomic triple write,
filename-suffix selection, and write-failure cleanup.

Removed test categories (alongside the modules they exercised):
- LLM dispatch / parse / resolve injection seams (assemble_pass /
  conflict_detector / conflict_resolver).
- Per-slot cache (assemble_cache / assemble_adapter B6 wiring).
- B2/B3/B5 verifier failure modes (assemble_verifier).
- Multi-slot conflict aggregation (no non-verbatim slot exists).
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import atomic_emit as ae  # noqa: E402


_LINKED_COMPOSITE = (
    "## Identity\n\n"
    "Base identity prose.\n\n"
    "## Responsibility\n\n"
    "Worker is responsible for implementation.\n\n"
    "## Soul\n\n"
    "Base soul prose.\n\n"
    "## Instructions\n\n"
    "### step:cycle/boot\n→ run sub-skill: boot-bootstrap\nBoot body.\n\n"
    "### step:cycle/work\n→ run sub-skill: triage-issues\nWork body.\n\n"
    "## Project Context\n\n"
    "Project context body (verbatim slot).\n\n"
    "## Vault\n\n"
    "Vault body (verbatim slot).\n"
)


# ---------------------------------------------------------------------------
# Atomic write of the triple via .tmp + rename
# ---------------------------------------------------------------------------

def test_success_writes_all_three_files(tmp_path):
    paths = ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
    )
    assert all(p.exists() for p in paths)
    names = {p.name for p in paths}
    assert names == {"CLAUDE.md", "CLAUDE.linked.md", "CLAUDE.conflicts.md"}


def test_success_no_tmp_files_remain(tmp_path):
    ae.assemble_and_emit(_LINKED_COMPOSITE, tmp_path, role_class="worker")
    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == [], f"unexpected .tmp leftovers: {leftover}"


def test_success_claude_linked_md_equals_input(tmp_path):
    ae.assemble_and_emit(_LINKED_COMPOSITE, tmp_path, role_class="worker")
    on_disk = (tmp_path / "CLAUDE.linked.md").read_text(encoding="utf-8")
    assert on_disk == _LINKED_COMPOSITE


def test_success_claude_md_contains_six_h2_sections_in_order(tmp_path):
    ae.assemble_and_emit(_LINKED_COMPOSITE, tmp_path, role_class="worker")
    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    h2 = [ln for ln in claude.splitlines() if ln.startswith("## ")]
    assert h2 == [
        "## Identity",
        "## Responsibility",
        "## Soul",
        "## Instructions",
        "## Project Context",
        "## Vault",
    ]


def test_every_slot_passes_through_verbatim(tmp_path):
    """Post-#11050: every slot is in _VERBATIM_SLOTS; the linked body for
    each slot becomes the assembled body byte-for-byte."""
    ae.assemble_and_emit(_LINKED_COMPOSITE, tmp_path, role_class="worker")
    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    # Project Context + Vault distinctive lines from the linked composite
    assert "Project context body (verbatim slot)." in claude
    assert "Vault body (verbatim slot)." in claude
    # Instructions slot's runtime references survive the verbatim copy.
    assert "→ run sub-skill: boot-bootstrap" in claude
    assert "→ run sub-skill: triage-issues" in claude


# ---------------------------------------------------------------------------
# Link-stage failure: malformed input aborts before write
# ---------------------------------------------------------------------------

def test_link_stage_fail_aborts_without_writing(tmp_path):
    """A composite with no canonical H2 headings raises LinkStageFail."""
    bad_composite = "no headings here, just prose\n"
    with pytest.raises(ae.LinkStageFail):
        ae.assemble_and_emit(bad_composite, tmp_path, role_class="worker")
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Failure during write phase — no partial artifacts
# ---------------------------------------------------------------------------

def test_write_failure_unlinks_tmp_files_and_raises(tmp_path, monkeypatch):
    """If a .tmp write fails, all .tmp files are cleaned up before raising."""
    real_write = Path.write_text
    call_count = {"writes": 0}

    def flaky_write(self, content, *args, **kwargs):
        call_count["writes"] += 1
        if call_count["writes"] == 2:
            raise OSError("disk full simulation")
        return real_write(self, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky_write)

    with pytest.raises(ae.AssembleError):
        ae.assemble_and_emit(_LINKED_COMPOSITE, tmp_path, role_class="worker")
    leftover_tmp = list(tmp_path.glob("*.tmp"))
    assert leftover_tmp == [], f"tmp leftovers after write fail: {leftover_tmp}"
    final = list(tmp_path.glob("CLAUDE*.md"))
    assert final == [], f"no final files should exist: {final}"


def test_conflict_report_write_failure_raises_specific_subclass(tmp_path, monkeypatch):
    """OSError on the conflicts file specifically -> ConflictReportWriteFail."""
    real_write = Path.write_text

    def selective_fail(self, content, *args, **kwargs):
        if self.name == "CLAUDE.conflicts.md.tmp":
            raise OSError(f"simulated failure on {self.name}")
        return real_write(self, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", selective_fail)
    with pytest.raises(ae.ConflictReportWriteFail):
        ae.assemble_and_emit(_LINKED_COMPOSITE, tmp_path, role_class="worker")
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob("CLAUDE*.md")) == []


# ---------------------------------------------------------------------------
# Conflicts report is always emitted, always empty post-#11050
# ---------------------------------------------------------------------------

def test_conflicts_report_is_empty_marker(tmp_path):
    """Verbatim-only mode means zero conflict records — the conflicts file
    is a self-describing empty-marker, not absent."""
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        model_id="sonnet", commit_sha="abc123", generated_at="2026-06-05",
    )
    on_disk = (tmp_path / "CLAUDE.conflicts.md").read_text(encoding="utf-8")
    assert "No conflict records" in on_disk
    assert "role_class: worker" in on_disk
    assert "model_id: sonnet" in on_disk
    assert "commit_sha: abc123" in on_disk


# ---------------------------------------------------------------------------
# PRD-B B9 (#10763 AC3) — filename_suffix parameter
# ---------------------------------------------------------------------------

def test_filename_suffix_default_is_canonical(tmp_path):
    paths = ae.assemble_and_emit(_LINKED_COMPOSITE, tmp_path, role_class="worker")
    names = sorted(p.name for p in paths)
    assert names == ["CLAUDE.conflicts.md", "CLAUDE.linked.md", "CLAUDE.md"]


def test_filename_suffix_v2_explicit_writes_legacy_paths(tmp_path):
    """The ``.v2.md`` family is retained as an explicit-suffix branch for
    legacy callers / coexistence-era tests."""
    paths = ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        filename_suffix=".v2.md",
    )
    names = sorted(p.name for p in paths)
    assert names == ["CLAUDE.conflicts.v2.md", "CLAUDE.linked.v2.md", "CLAUDE.v2.md"]
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / "CLAUDE.linked.md").exists()
    assert not (tmp_path / "CLAUDE.conflicts.md").exists()


# ---------------------------------------------------------------------------
# Helper: _split_linked_into_slots
# ---------------------------------------------------------------------------

def test_split_linked_returns_canonical_slot_keys():
    out = ae._split_linked_into_slots(_LINKED_COMPOSITE)
    assert set(out) == {
        "identity", "responsibility", "soul",
        "instructions", "project-context", "vault",
    }


def test_split_linked_ignores_unknown_h2_headings():
    composite = "## Not A Slot\nbody\n\n## Identity\nidbody\n"
    out = ae._split_linked_into_slots(composite)
    assert set(out) == {"identity"}


def test_split_linked_handles_closing_hashes_in_heading():
    """Markdown allows `## Foo ##` — should still recognize the slot."""
    composite = "## Identity ##\nbody\n"
    out = ae._split_linked_into_slots(composite)
    assert "identity" in out


def test_split_linked_keeps_role_suffixed_h2_inside_parent_slot(tmp_path):
    """#11011 Bug 3: ``## Soul — PM`` is NOT a slot boundary; the body stays
    inside the parent canonical ``## Soul`` slot."""
    composite = (
        "## Identity\n\nid body\n\n"
        "## Responsibility\n\nresp body\n\n"
        "## Soul\n\n"
        "## Soul — PM\n\nPM-specific soul body.\n\n"
        "## Instructions\n\ninstructions body\n\n"
        "## Project Context\n\npc\n\n"
        "## Vault\n\nvault\n"
    )
    out = ae._split_linked_into_slots(composite)
    # Soul slot contains the role-suffixed sub-heading and its body verbatim.
    assert "## Soul — PM" in out["soul"]
    assert "PM-specific soul body." in out["soul"]
    # The role-suffixed heading did NOT terminate the parent slot.
    assert "instructions body" in out["instructions"]
