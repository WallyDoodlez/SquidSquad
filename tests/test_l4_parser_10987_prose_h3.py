"""Regression tests for #10987 — L4 parser must accept H3 prose sub-headings
inside any slot.

Pre-fix the parser treated every H3 line as an op directive, raising
``L4ParseError`` for non-op-grammar headings like ``### Zero-gap gate
is absolute`` even when they appeared under ``## Soul`` / ``## Identity``
/ ``## Instructions`` as content sub-headings. 3 of 4 shipped L4 files
under ``.squidsquad/project/`` reproduced the error in production, which
in turn blocked ``compose.py deploy-all`` for dm/verifier/worker
post-#10981.

These tests pin the post-fix contract:

- H3 lines that start with a reserved op keyword (``append``, ``replace``,
  ``insert-before``, ``insert-after``) followed by whitespace or
  end-of-string are still strictly op-graded — malformed forms raise.
- H3 lines outside that op-keyword prefix are content sub-headings; they
  flow into the slot's implicit append body and the raw heading line is
  preserved verbatim in the slot prose.
- All four shipped L4 files at ``.squidsquad/project/<role>.md`` parse
  end-to-end without raising.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_parser as l4  # noqa: E402


class TestNonOpH3UnderNonInstructionsSlot:
    """The original audit symptom: ``### Zero-gap gate is absolute`` and
    siblings under ``## Soul`` raised malformed-op."""

    def test_h3_under_soul_treated_as_prose_append(self):
        text = (
            "## Soul\n"
            "\n"
            "### Zero-gap gate is absolute\n"
            "\n"
            "No exceptions without explicit human override.\n"
        )
        doc = l4.parse_l4_text(text)
        soul_ops = doc.slots.get("soul", [])
        assert len(soul_ops) == 1
        op = soul_ops[0]
        assert op.op_type == "append"
        assert op.target_step_id is None
        # The raw H3 line must survive into the body so the slot prose
        # keeps its sub-heading structure.
        assert "### Zero-gap gate is absolute" in op.body_text
        assert "No exceptions without explicit human override." in op.body_text

    def test_multiple_h3_subheadings_under_one_slot_share_one_append(self):
        text = (
            "## Soul\n"
            "\n"
            "### Principle one\n"
            "\n"
            "First principle body.\n"
            "\n"
            "### Principle two\n"
            "\n"
            "Second principle body.\n"
        )
        doc = l4.parse_l4_text(text)
        soul_ops = doc.slots.get("soul", [])
        assert len(soul_ops) == 1
        op = soul_ops[0]
        assert "### Principle one" in op.body_text
        assert "First principle body." in op.body_text
        assert "### Principle two" in op.body_text
        assert "Second principle body." in op.body_text

    def test_empty_non_instructions_slot_emits_no_op(self):
        """A bare ``## Identity`` with no content should not produce a
        no-op append entry — the L1-L3 identity content stays unchanged.
        """
        text = "## Identity\n\n## Soul\n\nSoul prose.\n"
        doc = l4.parse_l4_text(text)
        # Identity slot key is created (so apply_l4_ops can iterate it
        # without KeyError) but with zero ops.
        assert doc.slots.get("identity", []) == []
        # Soul slot has the implicit append.
        assert len(doc.slots.get("soul", [])) == 1


class TestNonOpH3UnderInstructionsSlot:
    """Production L4 files use prose H3s under ``## Instructions`` too
    (``### Boot & Pre-flight``, ``### Delivery Flow``, etc.). Those must
    flow into an implicit append rather than raising malformed-op.
    """

    def test_prose_h3_in_instructions_opens_implicit_append(self):
        text = (
            "## Instructions\n"
            "\n"
            "### Boot & Pre-flight\n"
            "\n"
            "- Run `tracker.py check-gh` and `capability_check.py`.\n"
        )
        doc = l4.parse_l4_text(text)
        instr = doc.slots.get("instructions", [])
        assert len(instr) == 1
        op = instr[0]
        assert op.op_type == "append"
        assert op.target_step_id is None
        assert "### Boot & Pre-flight" in op.body_text
        assert "tracker.py check-gh" in op.body_text

    def test_explicit_op_still_parsed_as_op_in_instructions_slot(self):
        """The grammar's primary purpose — step-targeted edits — must
        still work alongside the new prose-H3 acceptance.
        """
        text = (
            "## Instructions\n"
            "\n"
            "### append\n"
            "\n"
            "Explicit append body.\n"
            "\n"
            "### insert-after step:cycle/boot\n"
            "\n"
            "Insert-after body.\n"
        )
        doc = l4.parse_l4_text(text)
        instr = doc.slots.get("instructions", [])
        assert len(instr) == 2
        assert instr[0].op_type == "append"
        assert instr[0].target_step_id is None
        assert instr[0].body_text == "Explicit append body."
        assert instr[1].op_type == "insert-after"
        assert instr[1].target_step_id == "boot"
        assert instr[1].body_text == "Insert-after body."

    def test_prose_h3_then_explicit_op_both_captured(self):
        """A slot containing both prose H3s and explicit ops captures
        them as separate L4Op entries — the implicit append accumulates
        until the next explicit op opens its own.
        """
        text = (
            "## Instructions\n"
            "\n"
            "### Boot & Pre-flight\n"
            "\n"
            "Prose paragraph.\n"
            "\n"
            "### append\n"
            "\n"
            "Explicit append body.\n"
        )
        doc = l4.parse_l4_text(text)
        instr = doc.slots.get("instructions", [])
        assert len(instr) == 2
        # First op: implicit append accumulating the prose H3.
        assert instr[0].op_type == "append"
        assert "### Boot & Pre-flight" in instr[0].body_text
        assert "Prose paragraph." in instr[0].body_text
        # Second op: explicit append, prose-side content NOT in it.
        assert instr[1].op_type == "append"
        assert "### Boot & Pre-flight" not in instr[1].body_text
        assert instr[1].body_text == "Explicit append body."

    def test_explicit_op_then_prose_h3_both_captured(self):
        """DS finding 3: an explicit op followed by a prose H3 must
        produce two separate L4Op entries — the prose H3 must NOT be
        silently absorbed into the explicit op's body.
        """
        text = (
            "## Instructions\n"
            "\n"
            "### append\n"
            "\n"
            "→ run sub-skill: example\n"
            "\n"
            "Explicit body.\n"
            "\n"
            "### Boot & Pre-flight\n"
            "\n"
            "Prose paragraph that must not be absorbed into the explicit append above.\n"
        )
        doc = l4.parse_l4_text(text)
        instr = doc.slots.get("instructions", [])
        assert len(instr) == 2
        # First op: explicit append — body must NOT contain the prose H3 line.
        assert instr[0].op_type == "append"
        assert "### Boot & Pre-flight" not in instr[0].body_text
        assert "Prose paragraph" not in instr[0].body_text
        assert "Explicit body." in instr[0].body_text
        # Second op: implicit append containing the prose H3.
        assert instr[1].op_type == "append"
        assert "### Boot & Pre-flight" in instr[1].body_text
        assert "Prose paragraph that must not be absorbed" in instr[1].body_text

    def test_plain_prose_before_first_h3_in_instructions_not_lost(self):
        """DS finding 4: plain prose between ``## Instructions`` and the
        first H3 must flow into the implicit append, not silently drop.
        """
        text = (
            "## Instructions\n"
            "\n"
            "Plain prose paragraph that should be captured.\n"
            "\n"
            "More prose.\n"
            "\n"
            "### Boot & Pre-flight\n"
            "\n"
            "Sub-heading body.\n"
        )
        doc = l4.parse_l4_text(text)
        instr = doc.slots.get("instructions", [])
        assert len(instr) == 1
        op = instr[0]
        assert op.op_type == "append"
        assert "Plain prose paragraph that should be captured." in op.body_text
        assert "More prose." in op.body_text
        assert "### Boot & Pre-flight" in op.body_text
        assert "Sub-heading body." in op.body_text


class TestImplicitAppendExemptFromR4Validation:
    """DS finding 1: R4 in link_stage_validator rejects ``### append``
    ops under ``## Instructions`` without a ``→ run sub-skill:`` ref.
    Implicit appends from prose H3s (which by definition can't have a
    sub-skill ref — that's the whole point of being prose) must be
    exempt, otherwise compose for dm/verifier/worker aborts at R4.
    """

    def test_implicit_append_op_is_marked_implicit(self):
        """Sanity: the parser sets ``_implicit=True`` on auto-opened
        appends so downstream consumers (R4, future validators) can
        distinguish them from explicit author-written appends.
        """
        text = "## Soul\n\n### Some principle\n\nBody.\n"
        op = l4.parse_l4_text(text).slots["soul"][0]
        assert getattr(op, "_implicit", False) is True

    def test_explicit_append_op_is_not_marked_implicit(self):
        text = "## Instructions\n\n### append\n\n→ run sub-skill: x\n"
        op = l4.parse_l4_text(text).slots["instructions"][0]
        assert getattr(op, "_implicit", False) is False

    def test_r4_skips_implicit_append_op(self):
        """The validator integration is the load-bearing test for
        Finding 1 — without the exemption, the live dm.md L4 file
        aborts at R4 even though it should compose cleanly.
        """
        SCRIPTS = REPO_ROOT / "references" / "scripts"
        sys.path.insert(0, str(SCRIPTS))
        from link_stage_validator import (  # noqa: E402
            LinkStageValidationError,
            _check_r4_instructions_append_has_sub_skill_ref,
        )

        text = (
            "## Instructions\n"
            "\n"
            "### Boot & Pre-flight\n"
            "\n"
            "Bullet-list content with no `→ run sub-skill:` reference.\n"
        )
        doc = l4.parse_l4_text(text)
        # Implicit append, no sub-skill ref — must not raise post-fix.
        try:
            _check_r4_instructions_append_has_sub_skill_ref(doc, "<text>")
        except LinkStageValidationError as e:
            pytest.fail(
                f"R4 should exempt implicit append ops; got {e}"
            )

    def test_r4_still_rejects_explicit_append_without_sub_skill_ref(self):
        """Hardening: the exemption must NOT loosen R4 for explicit
        ops. An explicit ``### append`` under Instructions with no
        sub-skill ref still violates the thin-orchestration invariant.
        """
        SCRIPTS = REPO_ROOT / "references" / "scripts"
        sys.path.insert(0, str(SCRIPTS))
        from link_stage_validator import (  # noqa: E402
            LinkStageValidationError,
            _check_r4_instructions_append_has_sub_skill_ref,
        )

        text = (
            "## Instructions\n"
            "\n"
            "### append\n"
            "\n"
            "Body without a sub-skill ref.\n"
        )
        doc = l4.parse_l4_text(text)
        with pytest.raises(LinkStageValidationError) as exc:
            _check_r4_instructions_append_has_sub_skill_ref(doc, "<text>")
        assert exc.value.rule == "R4"


class TestOpLikeH3StillStrict:
    """``_OP_LIKE_RE`` reserves the ``append`` / ``replace`` /
    ``insert-before`` / ``insert-after`` prefixes — typos there still
    raise so authors can't accidentally turn a malformed op into prose.
    """

    @pytest.mark.parametrize(
        "bad_h3",
        [
            "### replace step:cycle/",  # missing id after step:cycle/
            "### insert-before",  # missing target on a targeted op
            "### replace step:cycle/foo extra",  # trailing garbage
            "### insert-after step:cycle/",  # missing id
        ],
    )
    @pytest.mark.parametrize("slot", ["instructions", "soul", "identity"])
    def test_op_like_malformed_still_rejected(self, bad_h3, slot):
        slot_label = "Project Context" if slot == "project-context" else slot.capitalize()
        text = f"## {slot_label}\n\n{bad_h3}\n\nbody\n"
        with pytest.raises(l4.L4ParseError) as exc:
            l4.parse_l4_text(text)
        assert "malformed H3 op" in str(exc.value)


class TestLiveProductionL4Files:
    """The four shipped L4 files at ``.squidsquad/project/<role>.md`` all
    parse without raising — the original audit symptom of #10987.
    """

    @pytest.mark.parametrize("role", ["pm", "dm", "verifier", "worker"])
    def test_live_l4_file_parses(self, role):
        path = REPO_ROOT / ".squidsquad" / "project" / f"{role}.md"
        if not path.is_file():
            pytest.skip(f"live L4 file {path} not present in this checkout")
        doc = l4.parse_l4_file(path)
        # Every slot that's referenced in the file should have at least
        # one op recorded — that's how we'll know the slot content was
        # captured rather than silently dropped.
        text = path.read_text(encoding="utf-8")
        for slot_label, slot_key in [
            ("## Identity", "identity"),
            ("## Soul", "soul"),
            ("## Instructions", "instructions"),
            ("## Project Context", "project-context"),
        ]:
            if slot_label in text:
                # Slot present in source — there may or may not be ops
                # (empty slots are explicitly allowed), but the slot key
                # must be present in the parsed document.
                assert slot_key in doc.slots, (
                    f"{role}.md contains `{slot_label}` but parser did "
                    f"not register slot key `{slot_key}`"
                )
