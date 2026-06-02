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
   v1 counterpart. Measurement uses ``l4_path=Path('nonexistent.md')``
   to isolate D2's effect from project-state L4 file divergence; D2's
   contract is about emission, not about how operators have authored
   their L4 files.
"""

import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import v2_link_stage as v2  # noqa: E402


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
    Other slots under the same path prefix still flow normally — this
    preserves the test-fixture pattern that places identity/soul content
    under ``references/sub-skills/common/`` for orthogonal tests, and
    leaves room for future slot semantics under sub-skill paths without
    silently disappearing content.
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
    out = v2.emit_v2_linked(role, None, l4_path=Path("nonexistent.md"))
    assert "<!-- sub-skill:" not in out


@pytest.mark.parametrize("role", _MANDATORY_ROLES)
def test_live_v2_emits_sub_skill_references(role):
    """At least one ``→ run sub-skill: <name>`` reference present per role.

    The reference grammar is authored directly in the orchestrator
    instructions files; D2's filter only DROPS sub-skill bodies — it must
    NOT also drop the reference text.
    """
    out = v2.emit_v2_linked(role, None, l4_path=Path("nonexistent.md"))
    assert "→ run sub-skill: " in out


def test_live_v2_boot_block_not_inlined_when_role_uses_boot_bootstrap():
    """The Boot block (``## Boot — Mode Detection``) lives in the
    boot-bootstrap sub-skill body and must NOT be inlined in v2 output
    for any role that references boot-bootstrap.
    """
    for role in _MANDATORY_ROLES:
        out = v2.emit_v2_linked(role, None, l4_path=Path("nonexistent.md"))
        assert "## Boot — Mode Detection" not in out, (
            f"role={role}: Boot block prose was inlined; D2 filter bypassed."
        )


# ---------------------------------------------------------------------------
# Size invariant (AC3): v2 <= 30% of v1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", _MANDATORY_ROLES)
def test_v2_size_is_at_most_30pct_of_v1(role):
    """Per-role: composed v2 byte size <= 30% of v1 byte size.

    Per AC3 + PRD-D §10 criterion 10. The threshold is the average
    across role-classes, but a per-role gate keeps a single inflated
    role-class from sneaking past via averaging. ``nonexistent.md`` L4
    path isolates D2's emission contract from project-state L4
    customizations that vary per install.
    """
    v2_out = v2.emit_v2_linked(role, None, l4_path=Path("nonexistent.md"))
    with tempfile.TemporaryDirectory() as td:
        v1_out = compose.deploy_role(role, target_root=Path(td)).read_text(
            encoding="utf-8",
        )
    ratio = len(v2_out) / len(v1_out)
    assert ratio <= 0.30, (
        f"role={role}: v2/v1 size ratio = {ratio:.1%} exceeds 30% target. "
        f"v1={len(v1_out)} v2={len(v2_out)}"
    )


def test_v2_average_size_at_most_30pct_of_v1():
    """Average across role-classes: v2 / v1 <= 30%. PRD-D §10 criterion 10."""
    ratios = []
    for role in _MANDATORY_ROLES:
        v2_out = v2.emit_v2_linked(role, None, l4_path=Path("nonexistent.md"))
        with tempfile.TemporaryDirectory() as td:
            v1_out = compose.deploy_role(role, target_root=Path(td)).read_text(
                encoding="utf-8",
            )
        ratios.append(len(v2_out) / len(v1_out))
    avg = sum(ratios) / len(ratios)
    assert avg <= 0.30, (
        f"avg v2/v1 ratio = {avg:.1%} exceeds 30% target across "
        f"roles {_MANDATORY_ROLES}."
    )
