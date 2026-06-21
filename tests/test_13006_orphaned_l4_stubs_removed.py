"""Guard for #13006 — orphaned legacy L4 seed stubs deleted and stay deleted.

`references/sub-skills/project/` once carried per-slot legacy L4 seed stubs for
every role class (`<role>-instructions.md`, `<role>-responsibility.md`,
`<role>-soul-directives.md`). The L4-seed mechanism was later scoped (sub-phase
6274.2) so the wizard only seeds the `worker-*`/`verifier-*` slots — see
`wizard.py:_copy_l4_seed_stubs`, which explicitly skips everything else. That
left the `pm-*` and `dm-*` per-slot stubs dead: the wizard never copies them,
compose reads role L2 from `references/roles/<role>/` (not from here), they are
not in `docs/sub-skill-catalog.md`, and no code references them.

This locks their removal: the pm/dm role classes receive no per-slot seed
stubs, so none may reappear in `references/sub-skills/project/`.

Scope note: `shared-*.md` and `setup-upgrade-gate.md` also live in this
directory and are intentionally NOT asserted here — their disposition is still
open per `docs/sub-skill-catalog.md` (fold into role files vs. remain as a
shared baseline), so they are out of #13006's scope.
"""

from pathlib import Path

PROJECT_SEEDS = (
    Path(__file__).resolve().parent.parent
    / "references" / "sub-skills" / "project"
)

# The dead per-slot stubs #13006 deletes.
ORPHANED_STUBS = [
    "pm-instructions.md",
    "pm-responsibility.md",
    "pm-soul-directives.md",
    "dm-instructions.md",
    "dm-responsibility.md",
    "dm-soul-directives.md",
]


def test_orphaned_pm_dm_stubs_absent():
    """None of the 6 named dead stubs may exist."""
    present = [n for n in ORPHANED_STUBS if (PROJECT_SEEDS / n).exists()]
    assert not present, (
        f"Dead legacy L4 stubs reappeared in {PROJECT_SEEDS}: {present}. "
        "The pm/dm role classes get no per-slot seed stubs (#13006)."
    )


def test_no_pm_or_dm_per_slot_seed_stubs():
    """No pm-* / dm-* per-slot seed stub may exist in project/ at all.

    Broader than the named list: the wizard only seeds worker-*/verifier-*,
    so any pm-/dm- per-slot stub is dead weight by construction.
    """
    stragglers = [
        p.name
        for p in PROJECT_SEEDS.glob("*.md")
        if p.name.startswith("pm-") or p.name.startswith("dm-")
    ]
    assert not stragglers, (
        f"Unexpected pm-/dm- per-slot seed stubs in {PROJECT_SEEDS}: "
        f"{stragglers}. These role classes receive no L4 seed stubs (#13006)."
    )
