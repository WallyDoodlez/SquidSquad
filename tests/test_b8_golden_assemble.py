"""Golden-file regression tests for the assemble pass (#10448, PRD-B B8).

Validates ``atomic_emit.assemble_and_emit`` against committed
``CLAUDE.md.golden`` + ``CLAUDE.conflicts.md.golden`` artifacts. The
LLM call is stubbed (no live model dispatch in this suite) — the stub
is fully deterministic and exercises:

- A slot that produces a §4.6 conflict (the L4 contradiction in the
  ``assemble-contradiction`` fixture's Responsibility slot).
- The cache flow: a second run with a populated cache returns cached
  bodies and never calls the stub LLM.
- A negative path: corrupt a copy of the fixture so a preservation
  token disappears from the assembled output; ``assemble_and_emit``
  raises ``PreservationFail`` instead of silently producing drift.

Out of scope per the issue body: CI-gating wiring; live-LLM end-to-end
(B1's smoke tests cover that surface).
"""

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
FIXTURES = REPO_ROOT / "tests" / "compose-fixtures"
sys.path.insert(0, str(SCRIPTS))

import atomic_emit  # noqa: E402
import v2_link_stage  # noqa: E402


_FIXTURE_NAME = "assemble-contradiction"
_FIXTURE_ROOT = FIXTURES / _FIXTURE_NAME
_GOLDEN_CLAUDE_PATH = _FIXTURE_ROOT / "CLAUDE.md.golden"
_GOLDEN_CONFLICTS_PATH = _FIXTURE_ROOT / "CLAUDE.conflicts.md.golden"

# Deterministic generated-at for the conflict report header so the
# golden stays byte-stable across runs.
_GENERATED_AT = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Deterministic stub LLM
# ---------------------------------------------------------------------------

# Stub assembled body for the contradiction slot. Crafted to:
# - drop the L2 phrase "PM coordinates the team" (so B5 drop-check passes)
# - paraphrase the L4 position so the higher layer is reflected
# - satisfy B3's length floor (>= 0.8 × linked length) and code-block
#   parity (0 fenced / 0 inline both sides)
# - preserve B2 preservation tokens (responsibility slot has none)
_STUB_RESPONSIBILITY_BODY = (
    "In this project, verifier coordinates the team; PM does not coordinate. "
    "The PM still shapes incoming work and assigns it to the right specialist "
    "for delivery, but team-level coordination is the verifier's job.\n"
)

_STUB_RESPONSIBILITY_CONFLICTS = (
    "<!-- ASSEMBLE_CONFLICTS -->\n\n"
    "- slot: responsibility\n"
    "  winner_layer: L4\n"
    "  winner_path: .squidsquad/project/pm.md\n"
    "  winner_quote: Project override: in this project, PM does NOT coordinate the team; "
    "verifier coordinates instead.\n"
    "  loser_layer: L2\n"
    "  loser_path: references/roles/pm/responsibility.md\n"
    "  loser_quote: PM coordinates the team\n"
    "  why: L4 transfers team coordination from PM to verifier for this project.\n"
    "  resolution: Assembled body says verifier coordinates the team; PM still shapes work "
    "but does not coordinate.\n"
)


def stub_assemble_slot(slot, linked_body):
    """Deterministic LLM stand-in.

    Responsibility slot returns the hand-crafted assembled body + a
    single-entry conflicts section. Other slots return the linked body
    verbatim with an empty ``(none)`` conflicts section.
    """
    if slot == "responsibility":
        return _STUB_RESPONSIBILITY_BODY + "\n" + _STUB_RESPONSIBILITY_CONFLICTS
    return linked_body + "\n<!-- ASSEMBLE_CONFLICTS -->\n\n(none)\n"


# ---------------------------------------------------------------------------
# Helpers — emit_and_compare orchestration
# ---------------------------------------------------------------------------

def _run_assemble(fixture_root, tmp_output_dir, *, cache_lookup_fn=None,
                  cache_store_fn=None, llm_call_recorder=None):
    """Build linked composite for the fixture, run assemble_and_emit, return triple paths."""
    linked = v2_link_stage.emit_v2_linked("pm", None, repo_root=fixture_root)

    def recording_stub(slot, linked_body):
        if llm_call_recorder is not None:
            llm_call_recorder.append(slot)
        return stub_assemble_slot(slot, linked_body)

    return atomic_emit.assemble_and_emit(
        linked,
        tmp_output_dir,
        role_class="pm",
        model_id="stub-llm",
        commit_sha="fixture-sha",
        generated_at=_GENERATED_AT,
        assemble_slot_fn=recording_stub,
        cache_lookup_fn=cache_lookup_fn,
        cache_store_fn=cache_store_fn,
    )


# ---------------------------------------------------------------------------
# AC: assembled CLAUDE.md matches golden
# ---------------------------------------------------------------------------

def test_assembled_claude_md_matches_golden(tmp_path):
    """End-to-end: emit_v2_linked + assemble_and_emit + diff vs committed CLAUDE.md.golden."""
    assert _GOLDEN_CLAUDE_PATH.exists(), (
        f"Golden CLAUDE.md missing for fixture '{_FIXTURE_NAME}'. "
        f"Regenerate by running the assemble pass against the fixture."
    )
    paths = _run_assemble(_FIXTURE_ROOT, tmp_path)
    claude_md = paths[0].read_text(encoding="utf-8")
    expected = _GOLDEN_CLAUDE_PATH.read_text(encoding="utf-8")
    if claude_md != expected:
        import difflib
        diff = "\n".join(difflib.unified_diff(
            expected.splitlines(), claude_md.splitlines(),
            fromfile=str(_GOLDEN_CLAUDE_PATH),
            tofile="assemble_and_emit output",
            lineterm="",
        ))
        pytest.fail(f"CLAUDE.md drift on '{_FIXTURE_NAME}':\n\n{diff}")


def test_assembled_claude_conflicts_md_matches_golden(tmp_path):
    """The §4.6 conflict report matches the committed golden (header + 1 conflict entry)."""
    assert _GOLDEN_CONFLICTS_PATH.exists(), (
        f"Golden CLAUDE.conflicts.md missing for fixture '{_FIXTURE_NAME}'."
    )
    paths = _run_assemble(_FIXTURE_ROOT, tmp_path)
    conflicts_md = paths[2].read_text(encoding="utf-8")
    expected = _GOLDEN_CONFLICTS_PATH.read_text(encoding="utf-8")
    if conflicts_md != expected:
        import difflib
        diff = "\n".join(difflib.unified_diff(
            expected.splitlines(), conflicts_md.splitlines(),
            fromfile=str(_GOLDEN_CONFLICTS_PATH),
            tofile="emit_conflict_report output",
            lineterm="",
        ))
        pytest.fail(f"CLAUDE.conflicts.md drift on '{_FIXTURE_NAME}':\n\n{diff}")


def test_conflict_report_names_the_l4_contradiction():
    """AC: 'fixture covering at least one L4 contradiction with golden CLAUDE.conflicts.md'."""
    text = _GOLDEN_CONFLICTS_PATH.read_text(encoding="utf-8")
    # One CONFLICT-001 entry naming responsibility, L4 > L2.
    assert "Total conflicts resolved: 1" in text
    assert "CONFLICT-001" in text
    assert "slot: responsibility" in text
    assert "L4 > L2" in text


# ---------------------------------------------------------------------------
# AC: cache hit on second run (no LLM invocation)
# ---------------------------------------------------------------------------

def test_cache_hit_on_second_run_skips_llm(tmp_path):
    """AC: 'suite asserts cache hit on second run (no LLM invocation)'."""
    cache_store = {}

    def cache_lookup_fn(slot, linked_body):
        return cache_store.get((slot, linked_body))

    def cache_store_fn(slot, linked_body, output):
        cache_store[(slot, linked_body)] = output

    first_calls = []
    _run_assemble(
        _FIXTURE_ROOT, tmp_path / "first",
        cache_lookup_fn=cache_lookup_fn,
        cache_store_fn=cache_store_fn,
        llm_call_recorder=first_calls,
    )
    assert first_calls, "first run should have populated the LLM"

    # Second run: same cache should yield zero LLM calls.
    second_calls = []
    _run_assemble(
        _FIXTURE_ROOT, tmp_path / "second",
        cache_lookup_fn=cache_lookup_fn,
        cache_store_fn=cache_store_fn,
        llm_call_recorder=second_calls,
    )
    assert second_calls == [], (
        f"second run should not invoke the LLM; recorded calls: {second_calls}"
    )


def test_cache_hit_second_run_writes_byte_identical_artifacts(tmp_path):
    """Two consecutive runs (cache miss then hit) emit byte-identical triples."""
    cache_store = {}

    def cache_lookup_fn(slot, linked_body):
        return cache_store.get((slot, linked_body))

    def cache_store_fn(slot, linked_body, output):
        cache_store[(slot, linked_body)] = output

    first_paths = _run_assemble(
        _FIXTURE_ROOT, tmp_path / "first",
        cache_lookup_fn=cache_lookup_fn,
        cache_store_fn=cache_store_fn,
    )
    second_paths = _run_assemble(
        _FIXTURE_ROOT, tmp_path / "second",
        cache_lookup_fn=cache_lookup_fn,
        cache_store_fn=cache_store_fn,
    )
    for f1, f2 in zip(first_paths, second_paths):
        assert f1.read_text(encoding="utf-8") == f2.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC: negative — corrupt fixture mid-test → suite catches
# ---------------------------------------------------------------------------

def test_corrupt_fixture_triggers_preservation_fail(tmp_path):
    """AC: 'corrupt a fixture mid-test → suite catches'.

    Mutate a copy of the fixture so the L1 instructions file loses its
    `→ run sub-skill: boot-bootstrap` reference. The stub returns the
    linked body verbatim (unchanged for non-responsibility slots), so the
    preservation multiset still matches — BUT a stub that DROPS the
    token would trigger PreservationFail. Simulate that by injecting a
    stub that returns a body with the token removed for instructions.
    """
    src = FIXTURES / _FIXTURE_NAME
    bad_root = tmp_path / "bad"
    shutil.copytree(src, bad_root)
    linked = v2_link_stage.emit_v2_linked("pm", None, repo_root=bad_root)

    def corrupting_stub(slot, linked_body):
        if slot == "instructions":
            # Drop the sub-skill reference -- B2 multiset must catch this.
            corrupted = linked_body.replace(
                "→ run sub-skill: boot-bootstrap", ""
            )
            return corrupted + "\n<!-- ASSEMBLE_CONFLICTS -->\n\n(none)\n"
        return stub_assemble_slot(slot, linked_body)

    out_dir = tmp_path / "out"
    with pytest.raises(atomic_emit.PreservationFail):
        atomic_emit.assemble_and_emit(
            linked, out_dir,
            role_class="pm",
            generated_at=_GENERATED_AT,
            assemble_slot_fn=corrupting_stub,
        )
    # AC: zero partial artifacts on abort.
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# Structural sanity: fixture has the contradiction the goldens encode
# ---------------------------------------------------------------------------

def test_fixture_has_l4_contradiction_in_responsibility():
    """The fixture's L4 file authors a position that contradicts L2 responsibility."""
    l4 = (_FIXTURE_ROOT / ".squidsquad" / "project" / "pm.md").read_text(encoding="utf-8")
    l2 = (_FIXTURE_ROOT / "references" / "roles" / "pm" / "responsibility.md").read_text(
        encoding="utf-8"
    )
    assert "PM coordinates the team" in l2
    assert "PM does NOT coordinate" in l4
