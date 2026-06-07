"""Guard test for #11144 polish: L1 "Your cycle (event mode)" H4 indexing
must stay in sync with the Mermaid lifetime-overview diagram's §N labels.

Per #11144 discussion (option A): the H4 sub-sections under "### Your cycle
(event mode)" are hand-numbered 1..N, and the lifetime-overview Mermaid
sequence diagram's `Note over A: §N <Title>` labels reference those
ordinals. Markdown and Mermaid have no autonumber, so a reorder/insert can
silently desync the diagram from the table of contents — this test is the
backstop.

The L1 source is the single edit site (it's inlined into the composed
CLAUDE.md), so this guard runs against `references/roles/instructions.md`
directly, not against composed output.
"""

import re
from pathlib import Path

L1_PATH = Path(__file__).parent.parent / "references" / "roles" / "instructions.md"

_YOUR_CYCLE_H3_RE = re.compile(r"^### Your cycle \(event mode\)\s*$", re.MULTILINE)
_NEXT_H3_RE = re.compile(r"^### ", re.MULTILINE)
_INDEXED_H4_RE = re.compile(r"^####\s+(\d+)\.\s+(.+?)\s*$", re.MULTILINE)
_LIFETIME_DIAGRAM_RE = re.compile(
    r"```mermaid\n(sequenceDiagram[\s\S]*?participant O as Operator[\s\S]*?)\n```"
)
_NOTE_LABEL_RE = re.compile(r"Note over A: §(\d+)\s+(.+?)$", re.MULTILINE)


def _extract_your_cycle_section():
    text = L1_PATH.read_text(encoding="utf-8")
    m = _YOUR_CYCLE_H3_RE.search(text)
    assert m, "### Your cycle (event mode) H3 not found in L1 instructions.md"
    start = m.end()
    next_h3 = _NEXT_H3_RE.search(text, start + 1)
    end = next_h3.start() if next_h3 else len(text)
    return text[start:end]


def test_your_cycle_h4s_are_indexed_contiguously_from_one():
    """Every H4 directly under "### Your cycle (event mode)" must carry an
    `N.` prefix with N forming a contiguous 1..len(H4s) sequence. A gap
    (e.g. 1, 2, 4) or unindexed H4 in this block fails fast.
    """
    section = _extract_your_cycle_section()
    headings = _INDEXED_H4_RE.findall(section)
    assert len(headings) >= 4, (
        f"expected at least 4 indexed H4s under 'Your cycle (event mode)', "
        f"got {len(headings)}. An H4 may be missing its `N.` prefix."
    )
    numbers = [int(n) for n, _ in headings]
    expected = list(range(1, len(numbers) + 1))
    assert numbers == expected, (
        f"H4 indices under 'Your cycle (event mode)' must be 1..{len(numbers)} "
        f"contiguous, got {numbers}"
    )


def test_lifetime_diagram_section_labels_match_h4_titles():
    """The lifetime-overview Mermaid sequence diagram carries `Note over A: §N <Title>`
    labels for the three lifecycle phases (boot, per-nudge, improvement subloop).
    Each `§N` must point at an existing H4 of the same number, and the inline
    title text must appear (case-insensitive, substring match) inside that
    H4's heading title.
    """
    section = _extract_your_cycle_section()
    h4_by_num = {
        int(n): title.strip() for n, title in _INDEXED_H4_RE.findall(section)
    }
    text = L1_PATH.read_text(encoding="utf-8")
    diagram_match = _LIFETIME_DIAGRAM_RE.search(text)
    assert diagram_match, "lifetime-overview Mermaid block not found in L1"
    diagram = diagram_match.group(1)
    notes = _NOTE_LABEL_RE.findall(diagram)
    assert notes, (
        "no `Note over A: §N <title>` labels found in lifetime overview "
        "diagram. The `§N` indexing scheme is the cross-reference contract."
    )
    for num_str, label in notes:
        num = int(num_str)
        assert num in h4_by_num, (
            f"lifetime diagram references §{num} but no H4 with that index "
            f"exists. H4s found: {sorted(h4_by_num)}"
        )
        h4_title = h4_by_num[num]
        norm_label = label.strip().lower()
        norm_h4 = h4_title.lower()
        assert norm_label in norm_h4, (
            f"lifetime diagram label '§{num} {label}' does not match the "
            f"corresponding H4 title '{num}. {h4_title}'. Either the diagram "
            f"or the H4 was renamed without updating the other."
        )
