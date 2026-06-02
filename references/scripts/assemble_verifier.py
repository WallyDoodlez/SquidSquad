"""Assemble-pass preservation verifier — pure Python.

Per PRD-B success criterion 3 + TRD §4.6 hard preservation guarantees,
the assemble pass MUST preserve every sub-skill reference and every
``step:cycle/<id>`` reference from its linked input. This module owns
that check as a pure function — no LLM, no I/O.

Grammar (TRD §6.1):
- Sub-skill refs:  ``→ run sub-skill: <name>``  (arrow is U+2192)
- Step IDs:        ``step:cycle/<id>``

B2 (#10441) added ``verify_preservation`` for sub-skill + step-ID
multiset checks. B3 (#10442) adds two additional preservation checks
operating on the same (linked, assembled) pair:

- ``check_length_floor``: guards against pathological truncation.
- ``check_code_block_parity``: guards against silently-dropped or
  silently-added code blocks (fenced + inline).
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

# PRD-B / #10752 W1: fenced-block content extractor. Matches
# ``` (or ````` etc.) [lang_tag] \n body \n ``` and captures the
# (lang_tag, body) tuple so verify_fenced_block_content can multiset-
# compare them. ``DOTALL`` lets ``.`` span lines inside the body.
_FENCED_BLOCK_RE = re.compile(
    r"^(`{3,})([^\n`]*)\n(.*?)^\1\s*$",
    re.MULTILINE | re.DOTALL,
)

# PRD-B / #10752 W1: file-path extractor. Path-shaped tokens like
# ``references/scripts/foo.py``, ``.squidsquad/config.md``, or
# ``docs/COMPOSE-ARCHITECTURE.md`` — at least one path separator,
# ending in a small file extension (1-6 chars). Conservative on
# purpose: bare filenames (``README``) and version strings (``1.2.3``)
# don't match; backtick-wrapped paths still match because the path
# itself satisfies the pattern. The leading boundary
# ``(?<![A-Za-z0-9._/-])`` prevents a longer URL fragment from being
# truncated mid-path.
_FILE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9._/-])"
    r"([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.[a-zA-Z]{1,6})"
)


@dataclass
class PreservationResult:
    """Outcome of one ``verify_preservation`` call.

    ``ok`` is True iff every preservation multiset matched exactly
    (no missing, no extra) across all four preservation dimensions:

    - Sub-skill references (PRD-B SC3 item 1)
    - Step IDs (item 2)
    - Fenced code blocks — ``(lang_tag, body)`` tuples preserved
      verbatim per item 3 (PRD-B #10752 W1; pre-fix the verifier
      only counted block PARITY, not content equality)
    - File paths (item 4; PRD-B #10752 W1)

    Each multiset diff is exposed as a sorted ``missing_*`` /
    ``extra_*`` pair so a caller (B7 abort path) can emit a precise
    operator diagnostic.
    """

    ok: bool
    missing_sub_skills: list = field(default_factory=list)
    extra_sub_skills: list = field(default_factory=list)
    missing_step_ids: list = field(default_factory=list)
    extra_step_ids: list = field(default_factory=list)
    # PRD-B #10752 W1: extended preservation coverage.
    missing_fenced_blocks: list = field(default_factory=list)
    extra_fenced_blocks: list = field(default_factory=list)
    missing_file_paths: list = field(default_factory=list)
    extra_file_paths: list = field(default_factory=list)


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


def _extract_fenced_block_tuples(text):
    """Return list of ``(lang_tag, body)`` tuples for every fenced
    block in ``text``.

    Bodies are returned with surrounding whitespace stripped so an
    indentation diff that doesn't change the block's content doesn't
    flag drift. The lang tag is taken from the opener line after the
    fence run (e.g. ``python`` from ```` ```python ````); empty when
    no tag is present.
    """
    tuples = []
    for m in _FENCED_BLOCK_RE.finditer(text):
        lang_tag = m.group(2).strip()
        body = m.group(3).strip()
        tuples.append((lang_tag, body))
    return tuples


def verify_fenced_block_content(linked, assembled):
    """Return ``(missing, extra)`` multiset diff of fenced blocks.

    Each element is a ``(lang_tag, body)`` tuple. Pre-#10752 W1 the
    verifier only counted block COUNT parity via
    ``check_code_block_parity``; the LLM could swap an entire block's
    contents and still pass the count check. This helper closes that
    hole.
    """
    linked_tuples = _extract_fenced_block_tuples(linked)
    assembled_tuples = _extract_fenced_block_tuples(assembled)
    return _multiset_diff(linked_tuples, assembled_tuples)


def verify_file_paths(linked, assembled):
    """Return ``(missing, extra)`` multiset diff of file-path tokens.

    Per PRD-B SC3 item 4 (#10752 W1), every file path the linked body
    mentions must survive the assemble pass — losing one means the
    LLM rewrote the prose into a "see the script" form that no longer
    names the script. The regex matches path tokens with at least one
    separator AND a small file extension (1-6 chars) so version
    strings and bare slugs don't false-positive.
    """
    linked_paths = _FILE_PATH_RE.findall(linked)
    assembled_paths = _FILE_PATH_RE.findall(assembled)
    return _multiset_diff(linked_paths, assembled_paths)


def verify_preservation(linked, assembled):
    """Verify the assembled body preserved every preservation token from the linked input.

    Pure, deterministic, no I/O. Empty inputs are valid and trivially pass.

    Per PRD-B SC3 + #10752 W1, this covers all four preservation
    dimensions: sub-skill references, step IDs, fenced-block content
    (``(lang_tag, body)`` multiset), and file paths. ``ok`` is True
    iff every multiset matched exactly.
    """
    linked_subs = _SUB_SKILL_RE.findall(linked)
    assembled_subs = _SUB_SKILL_RE.findall(assembled)
    linked_steps = _STEP_ID_RE.findall(linked)
    assembled_steps = _STEP_ID_RE.findall(assembled)

    missing_subs, extra_subs = _multiset_diff(linked_subs, assembled_subs)
    missing_steps, extra_steps = _multiset_diff(linked_steps, assembled_steps)
    missing_blocks, extra_blocks = verify_fenced_block_content(linked, assembled)
    missing_paths, extra_paths = verify_file_paths(linked, assembled)

    return PreservationResult(
        ok=not (
            missing_subs or extra_subs
            or missing_steps or extra_steps
            or missing_blocks or extra_blocks
            or missing_paths or extra_paths
        ),
        missing_sub_skills=missing_subs,
        extra_sub_skills=extra_subs,
        missing_step_ids=missing_steps,
        extra_step_ids=extra_steps,
        missing_fenced_blocks=missing_blocks,
        extra_fenced_blocks=extra_blocks,
        missing_file_paths=missing_paths,
        extra_file_paths=extra_paths,
    )


# B3 (#10442) — length floor + code-block parity checks.

# Fenced code-block opener/closer. Required at line start per CommonMark
# §4.5; three-or-more backticks. We count fence markers and pair them up.
_FENCE_RE = re.compile(r"^```+", re.MULTILINE)


def check_length_floor(linked, assembled, floor=0.8):
    """Return True iff ``len(assembled) >= floor * len(linked)``.

    Guards against the assemble pass silently truncating output. Empty
    linked is trivially satisfied (``floor * 0 == 0``), so empty
    assembled passes only when linked is also empty.
    """
    return len(assembled) >= floor * len(linked)


def _count_fenced_blocks(text):
    """Count fenced code blocks (pairs of ```-fence markers at line start)."""
    return len(_FENCE_RE.findall(text)) // 2


def _strip_fenced_blocks(text):
    """Remove fenced regions so inline-backtick counts don't double-count fences.

    Greedy across newlines; the ``re.DOTALL`` form is needed because
    fenced regions span lines.
    """
    return re.sub(r"```+.*?```+", "", text, flags=re.DOTALL)


def _count_inline_backtick_spans(text):
    """Count inline ``\\`...\\``` spans (single-backtick delimited)."""
    stripped = _strip_fenced_blocks(text)
    # Single backticks that are NOT part of a longer backtick run, paired up.
    # A standalone backtick has neither a backtick neighbor on the left nor
    # the right. Two such backticks form one inline span.
    standalone = re.findall(r"(?<!`)`(?!`)", stripped)
    return len(standalone) // 2


def _within_tolerance(linked_count, assembled_count, tolerance):
    """Return True iff the assembled count is within ``±tolerance`` of linked.

    Uses ``max(linked_count, 1)`` as the denominator so a linked count of
    0 still yields a meaningful comparison: any nonzero ``assembled_count``
    is treated as an unbounded change and fails when ``tolerance < 1``.
    """
    delta = abs(assembled_count - linked_count)
    return delta / max(linked_count, 1) <= tolerance


def check_code_block_parity(linked, assembled, tolerance=0.1):
    """Return True iff fenced-block AND inline-backtick counts are both within ``±tolerance``.

    Both checks must pass; a drop or a spike in either count beyond
    ``tolerance`` fails. Default ``tolerance=0.1`` matches the AC
    (±10%).
    """
    fenced_ok = _within_tolerance(
        _count_fenced_blocks(linked),
        _count_fenced_blocks(assembled),
        tolerance,
    )
    inline_ok = _within_tolerance(
        _count_inline_backtick_spans(linked),
        _count_inline_backtick_spans(assembled),
        tolerance,
    )
    return fenced_ok and inline_ok
