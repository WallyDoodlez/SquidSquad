"""Assemble-pass preservation verifier — pure Python (#10441, PRD-B Story B2).

Per PRD-B success criterion 3 + TRD §4.6 hard preservation guarantees,
the assemble pass MUST preserve every sub-skill reference and every
``step:cycle/<id>`` reference from its linked input. This module owns
that check as a pure function — no LLM, no I/O.

Grammar (TRD §6.1):
- Sub-skill refs:  ``→ run sub-skill: <name>``  (arrow is U+2192)
- Step IDs:        ``step:cycle/<id>``

B3 (#10442) extends this same module with length-floor + code-block
parity checks; keep B3 additions out of this commit.
"""

import re
from collections import Counter
from dataclasses import dataclass, field


# The arrow is U+2192. Allow flexible whitespace around it so a stray
# extra space after the colon doesn't make a reference invisible. The
# name grammar (alphanumeric + ``_-``) matches the codebase convention
# observed in sub-skill manifests.
_SUB_SKILL_RE = re.compile(r"→\s*run\s+sub-skill:\s*([A-Za-z0-9_-]+)")
# ``step:cycle/<id>`` — bounded with a word boundary on the left so
# ``X-step:cycle/boot`` still matches (``-`` is non-word) but ``mystep:cycle/boot``
# does not (``y`` is word, prevents the boundary).
_STEP_ID_RE = re.compile(r"\bstep:cycle/([A-Za-z0-9_-]+)")


@dataclass
class PreservationResult:
    """Outcome of one ``verify_preservation`` call.

    ``ok`` is True iff both multisets matched exactly (no missing, no
    extra). The four list fields carry sorted multiset differences so
    a caller (B7 abort path) can emit a precise diagnostic.
    """

    ok: bool
    missing_sub_skills: list = field(default_factory=list)
    extra_sub_skills: list = field(default_factory=list)
    missing_step_ids: list = field(default_factory=list)
    extra_step_ids: list = field(default_factory=list)


def _multiset_diff(linked_items, assembled_items):
    """Return ``(missing_in_assembled, extra_in_assembled)`` as sorted lists.

    Both diffs are multiset-aware: if ``linked`` has ``["a","a"]`` and
    ``assembled`` has ``["a"]``, ``missing == ["a"]``.
    """
    c_linked = Counter(linked_items)
    c_assembled = Counter(assembled_items)
    missing = sorted((c_linked - c_assembled).elements())
    extra = sorted((c_assembled - c_linked).elements())
    return missing, extra


def verify_preservation(linked, assembled):
    """Verify the assembled body preserved every preservation token from the linked input.

    Pure, deterministic, no I/O. Empty inputs are valid and trivially pass.
    """
    linked_subs = _SUB_SKILL_RE.findall(linked)
    assembled_subs = _SUB_SKILL_RE.findall(assembled)
    linked_steps = _STEP_ID_RE.findall(linked)
    assembled_steps = _STEP_ID_RE.findall(assembled)

    missing_subs, extra_subs = _multiset_diff(linked_subs, assembled_subs)
    missing_steps, extra_steps = _multiset_diff(linked_steps, assembled_steps)

    return PreservationResult(
        ok=not (missing_subs or extra_subs or missing_steps or extra_steps),
        missing_sub_skills=missing_subs,
        extra_sub_skills=extra_subs,
        missing_step_ids=missing_steps,
        extra_step_ids=extra_steps,
    )
