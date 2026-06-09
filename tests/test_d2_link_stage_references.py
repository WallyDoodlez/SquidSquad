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


# PM Path A (#11049 spec clarification, cycle 1597): the 10 mandatory
# sub-skills must stay inlined in the composite because every-cycle / at-
# boot invocation can't wait for Skill-tool runtime resolution (#9968).
# The remaining cataloged sub-skills become ``→ run sub-skill:`` references.
# D2's filter still applies to the sub-skill DIRECTORY walk path (sub-skill
# files under ``references/sub-skills/`` are not picked up by the link-stage
# walker); these tests pin the source-side migration outcome instead.
_MANDATORY_INLINE = frozenset({
    "boot-bootstrap",
    "cycle-runner",
    "context-pressure",
    "resume-working-state",
    "task-pickup",
    "working-state",
    "git-commit",
    "agent-lifecycle",
    "improvement-scan-slim",
    "status-line",
})

# PM Path A D1: retired sub-skills whose content is queued for #10360
# inlining into Identity / Responsibility slots are inlined verbatim at
# the orchestrator source with a marker, so the bodies survive the link-
# stage walk. Permitted in the composite pending #10360.
_D1_RETIRED_INLINE = frozenset({
    "agent-boundaries",
    "discussion-protocol",
    "file-conventions",
    "prohibitions",
    "responsibility",
})

# L3 domain-context sub-skills are inlined verbatim into their host L3
# instructions.md (per the cycle-1591 pass that PM endorsed). Each L3
# variant has its own ``domain-context.md`` and the marker uses the bare
# stem, so a single allowed name covers all 20.
_DOMAIN_CONTEXT_INLINE = frozenset({"domain-context"})

_EXPECTED_INLINED_MARKERS = (
    _MANDATORY_INLINE | _D1_RETIRED_INLINE | _DOMAIN_CONTEXT_INLINE
)


@pytest.mark.parametrize("role", _MANDATORY_ROLES)
def test_live_v2_inlined_markers_are_intentional_only(role):
    """Only the intentionally-inlined sub-skill markers (mandatory + D1
    retired + domain-context) may appear in v2 output; every other
    ``<!-- sub-skill: ... -->`` marker is a D2-filter bypass.

    Post-#11049 PM Path A: the mandatory set is inlined at the L1/L2
    orchestrator source so the bodies survive the link-stage walk; D1
    retired and domain-context inlines also survive; everything else is
    referenced via ``→ run sub-skill: <name>`` and its body stays out.
    """
    import re as _re
    out = v2.emit_v2_linked(role, None, l4_path=_NO_L4)
    marker_pat = _re.compile(r"<!-- /?sub-skill: ([a-z][a-z0-9-]+) -->")
    seen = set(marker_pat.findall(out))
    leaked = seen - _EXPECTED_INLINED_MARKERS
    assert not leaked, (
        f"role={role}: D2-filter bypass — non-intentional sub-skill "
        f"bodies appearing inline: {sorted(leaked)}"
    )


@pytest.mark.parametrize("role", _MANDATORY_ROLES)
def test_live_v2_emits_sub_skill_references(role):
    """At least one ``→ run sub-skill: <name>`` reference present per role.

    The reference grammar is authored directly in the orchestrator
    instructions files for situational sub-skills; D2's filter drops
    those sub-skill bodies — it must NOT also drop the reference text.
    """
    out = v2.emit_v2_linked(role, None, l4_path=_NO_L4)
    assert "→ run sub-skill: " in out


def test_live_v2_boot_block_inlined_per_path_a():
    """Post-#11049 PM Path A: ``boot-bootstrap`` is mandatory-inline, so the
    Boot block MUST appear in v2 output for every role that consumes it.
    The pre-#11049 contract (boot block referenced not inlined) is retired
    pending #9968 runtime resolution.

    Post-#11144 Iter 22 polish-restructure the H2 ``## Boot — Mode
    Detection`` heading was replaced with the step-ID form ``### Step 1
    — step:cycle/boot`` (the canonical cycle-step anchor). The marker
    survives; the heading is the step-ID form.
    """
    for role in _MANDATORY_ROLES:
        out = v2.emit_v2_linked(role, None, l4_path=_NO_L4)
        assert "### Step 1 — step:cycle/boot" in out, (
            f"role={role}: Boot block prose missing — boot-bootstrap is "
            f"mandatory-inline per #11049 Path A and must survive the "
            f"link-stage walk into the composite."
        )


# ---------------------------------------------------------------------------
# v1-vs-v2 size invariant retired in E6 #10685 Phase 3d.4 — v1 ``deploy_role``
# was deleted, so the v1 byte baseline is no longer measurable. PRD-D §10
# criterion 10 was a pre-cutover gate; once v1 is gone the gate is moot.
# ---------------------------------------------------------------------------
