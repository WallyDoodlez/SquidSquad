"""Regression test for #13683 — l4_parser.py's H3 op grammar was
case-sensitive against the reserved op keywords, but the module's own
docstring and #10987's design intent both promise malformed ops fail
loud ("that's the 'malformed H3 op' AC bullet"). A case-varied exact
keyword (``### Append``, ``### Replace step:cycle/boot``) matched
neither the op-like check (case-sensitive) nor the malformed-diagnostic
path, and was silently absorbed as inert prose into the slot's implicit
append body instead: the intended customization never applied, no error
was raised, and the malformed L4 syntax leaked verbatim into composed
output.

Fix: ``_OP_LIKE_RE`` now matches case-insensitively, so a case-varied
keyword is still recognized as an op ATTEMPT and routed into ``_OP_RE``
(still case-sensitive) — which now rejects it loudly via the existing
malformed-op diagnostic instead of silently degrading to prose.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_parser as l4  # noqa: E402


@pytest.mark.parametrize(
    "bad_h3",
    [
        "### Append",
        "### APPEND",
        "### Replace",
        "### Replace step:cycle/boot",
        "### REPLACE step:cycle/boot",
        "### Insert-Before step:cycle/boot",
        "### INSERT-AFTER step:cycle/boot",
        "### apPEND",
    ],
)
def test_case_varied_op_keyword_rejected_not_silently_absorbed(bad_h3):
    text = f"## Agent Functions\n\n{bad_h3}\nbody\n"
    with pytest.raises(l4.L4ParseError) as exc:
        l4.parse_l4_text(text)
    assert "malformed H3 op" in str(exc.value)


def test_case_varied_op_keyword_error_names_the_offending_heading():
    text = "## Agent Functions\n\n### Replace step:cycle/boot\nNEW BODY\n"
    with pytest.raises(l4.L4ParseError) as exc:
        l4.parse_l4_text(text)
    assert "### Replace step:cycle/boot" in str(exc.value)


class TestExistingBehaviorUnaffected:
    """The fix widens the op-like net case-insensitively but must not
    change behavior for canonical-case ops or genuinely unrelated prose.
    """

    def test_canonical_lowercase_ops_still_parse_normally(self):
        text = (
            "## Agent Functions\n\n"
            "### replace step:cycle/boot\n\nNEW BOOT BODY\n"
        )
        doc = l4.parse_l4_text(text)
        op = doc.slots["instructions"][0]
        assert op.op_type == "replace"
        assert op.target_step_id == "boot"
        assert op.body_text == "NEW BOOT BODY"

    def test_canonical_append_still_parses_normally(self):
        text = "## Agent Functions\n\n### append\n\nExplicit append body.\n"
        doc = l4.parse_l4_text(text)
        op = doc.slots["instructions"][0]
        assert op.op_type == "append"
        assert op.body_text == "Explicit append body."

    @pytest.mark.parametrize(
        "prose_h3",
        [
            "### Boot & Queue",
            "### insert-around step:cycle/foo",
            "### appendix",
            "### Zero-gap gate",
        ],
    )
    def test_unrelated_prose_h3_still_treated_as_prose(self, prose_h3):
        """Existing #10987 prose-H3 cases (none of which is a
        case-varied reserved keyword) must remain unaffected."""
        text = f"## Agent Functions\n\n{prose_h3}\n\nfollowing prose\n"
        doc = l4.parse_l4_text(text)
        instructions = doc.slots.get("instructions", [])
        assert len(instructions) == 1
        op = instructions[0]
        assert op.op_type == "append"
        assert op.target_step_id is None
        assert prose_h3 in op.body_text
