"""D2 (#10673) — v2 link stage emits references, not sub-skill bodies.

PRD-D Story D2 hard rule per Q-D2: zero inlined sub-skill bodies in the
v2 composed CLAUDE.md instructions slot. Sub-skill files under
``references/sub-skills/`` are referenced by ``→ run sub-skill: <name>``,
which the orchestrator files under ``references/roles/.../instructions.md``
already author verbatim. The v2 link stage must NOT inline sub-skill
bodies into the instructions slot.

These tests pin the new behavior at three levels:

1. Synthetic fixture — a tmp tree with one orchestrator instructions file
   plus one sub-skill instructions file. After D2 only the orchestrator's
   reference appears; the sub-skill body is dropped.
2. Live repo — compose every mandatory role-class and assert no
   ``<!-- sub-skill: ... -->`` marker leaks into v2 output, and the
   reference grammar is present.
3. Size invariant (AC3) — per role-class and across the four mandatory
   role-classes, v2 composed output is at most 30% the byte size of the
   v1 counterpart. v2 uses ``_NO_L4`` (a guaranteed-nonexistent path)
   so ``emit_v2_linked`` falls back to ``L4Document.empty()``; v1 is
   composed into a tmp ``target_root`` that has no ``.squidsquad/``
   tree of its own, so v1's `{{include:}}` resolution likewise sees no
   per-install L4. Both sides measure the "no project L4 applied"
   baseline — the comparison is symmetric.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import v2_link_stage as v2  # noqa: E402


# Guaranteed-nonexistent L4 path for tests that intentionally bypass L4
# customization. Anchored under the live tree's own scripts dir with a
# component that cannot exist (``__d2_no_l4_sentinel__/...md``), so the
# path is absolute and cannot be shadowed by an operator dropping a real
# ``nonexistent.md`` at the repo root. ``emit_v2_linked`` falls back to
# ``L4Document.empty()`` when ``Path(l4_path).is_file()`` is False, which
# this path guarantees.
_NO_L4 = SCRIPTS / "__d2_no_l4_sentinel__" / "nonexistent.md"


# ---------------------------------------------------------------------------
# Synthetic fixture: sub-skill body filtered from instructions slot
# ---------------------------------------------------------------------------

def _write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _make_fixture_with_subskill_body(tmp_path):
    """One L1 orchestrator file containing a sub-skill reference + the
    referenced sub-skill body file at ``references/sub-skills/common/X.md``.

    Before D2 both would inline into the instructions slot. After D2
    only the orchestrator's reference text survives.
    """
    refs = tmp_path / "references"
    # Orchestrator: contains the reference line that the agent reads at runtime
    _write(
        refs / "roles" / "instructions.md",
        "---\nslot: instructions\nordinal: 10\n---\n\n"
        "### step:cycle/boot\n\n"
        "→ run sub-skill: boot-bootstrap\n\n"
        "Verify access.\n",
    )
    # Sub-skill body: would have been inlined pre-D2
    _write(
        refs / "sub-skills" / "common" / "boot-bootstrap.md",
        "---\nslot: instructions\nordinal: 10\n---\n\n"
        "<!-- sub-skill: boot-bootstrap -->\n"
        "## Boot — Mode Detection\n\n"
        "SUBSKILL_BODY_SENTINEL_BOOT\n",
    )
    # Identity slot anchor so other slots aren't empty.
    _write(
        refs / "roles" / "identity.md",
        "---\nslot: identity\nordinal: 10\n---\n\nBase identity.\n",
    )


def test_subskill_instructions_body_is_filtered_from_v2_output(tmp_path):
    """A sub-skill file with ``slot: instructions`` MUST NOT inline its body."""
    _make_fixture_with_subskill_body(tmp_path)
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    assert "SUBSKILL_BODY_SENTINEL_BOOT" not in out
    assert "<!-- sub-skill: boot-bootstrap -->" not in out
    # Reference from the orchestrator file survives.
    assert "→ run sub-skill: boot-bootstrap" in out


def test_subskill_filter_applies_only_to_instructions_slot(tmp_path):
    """A sub-skill PATH with a non-instructions slot is NOT filtered.

    The filter is keyed on (slot=instructions, path-under-sub-skills/).
    Other slots under the same path prefix still flow normally — locking
    this property means a future tightening of the predicate that
    over-broadens it (e.g. dropping all sub-skill paths regardless of
    slot) fails loudly here rather than silently. Today the live tree
    has zero non-instructions-slot files under ``references/sub-skills/``,
    so this test is a forward guard, not a current-behavior assertion.
    """
    refs = tmp_path / "references"
    _write(
        refs / "roles" / "instructions.md",
        "---\nslot: instructions\nordinal: 10\n---\n\nOrchestrator content.\n",
    )
    _write(
        refs / "sub-skills" / "common" / "extra-identity.md",
        "---\nslot: identity\nordinal: 20\n---\n\nNON_INSTRUCTIONS_SUBSKILL_SENTINEL\n",
    )
    _write(
        refs / "roles" / "identity.md",
        "---\nslot: identity\nordinal: 10\n---\n\nBase identity.\n",
    )
    out = v2.emit_v2_linked("worker", None, repo_root=tmp_path)
    assert "NON_INSTRUCTIONS_SUBSKILL_SENTINEL" in out


def test_collect_sources_for_validation_drops_sub_skill_instructions(tmp_path):
    """``collect_sources_for_validation`` must apply the same filter so the
    A2e validator and the A2d emitter see the same record set."""
    _make_fixture_with_subskill_body(tmp_path)
    sources = v2.collect_sources_for_validation("worker", None, repo_root=tmp_path)
    paths = {s.path for s in sources}
    assert "references/sub-skills/common/boot-bootstrap.md" not in paths
    assert "references/roles/instructions.md" in paths


# ---------------------------------------------------------------------------
# Live-repo invariants (AC1, AC2)
# ---------------------------------------------------------------------------

_MANDATORY_ROLES = sorted(compose.MANDATORY_ROLES | {"worker"})


@pytest.mark.parametrize("role", _MANDATORY_ROLES)
def test_live_v2_has_no_inlined_sub_skill_markers(role):
    """Live-tree v2 emission contains NO ``<!-- sub-skill: ... -->`` markers.

    Sub-skill body files start with that marker line right after their
    frontmatter; spotting it in v2 output is a deterministic regression
    indicator that the D2 filter has been bypassed.
    """
    out = v2.emit_v2_linked(role, None, l4_path=_NO_L4)
    assert "<!-- sub-skill:" not in out


@pytest.mark.parametrize("role", _MANDATORY_ROLES)
def test_live_v2_emits_sub_skill_references(role):
    """At least one ``→ run sub-skill: <name>`` reference present per role.

    The reference grammar is authored directly in the orchestrator
    instructions files; D2's filter only DROPS sub-skill bodies — it must
    NOT also drop the reference text.
    """
    out = v2.emit_v2_linked(role, None, l4_path=_NO_L4)
    assert "→ run sub-skill: " in out


def test_live_v2_boot_block_not_inlined_when_role_uses_boot_bootstrap():
    """The Boot block (``## Boot — Mode Detection``) lives in the
    boot-bootstrap sub-skill body and must NOT be inlined in v2 output
    for any role that references boot-bootstrap.
    """
    for role in _MANDATORY_ROLES:
        out = v2.emit_v2_linked(role, None, l4_path=_NO_L4)
        assert "## Boot — Mode Detection" not in out, (
            f"role={role}: Boot block prose was inlined; D2 filter bypassed."
        )


# ---------------------------------------------------------------------------
# v1-vs-v2 size invariant retired in E6 #10685 Phase 3d.4 — v1 ``deploy_role``
# was deleted, so the v1 byte baseline is no longer measurable. PRD-D §10
# criterion 10 was a pre-cutover gate; once v1 is gone the gate is moot.
# ---------------------------------------------------------------------------
