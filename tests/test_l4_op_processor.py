"""Tests for references/scripts/l4_op_processor.py (#10489, PRD-A Story A2c)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_op_processor as op_proc  # noqa: E402
from l4_parser import L4Op  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SLOT_WITH_THREE_STEPS = (
    "### step:cycle/boot\n"
    "boot body line 1\n"
    "boot body line 2\n"
    "\n"
    "### step:cycle/pickup\n"
    "pickup body\n"
    "\n"
    "### step:cycle/work\n"
    "work body\n"
)


def _op(op_type, target=None, body=""):
    """Build an L4Op fixture matching the parser's dataclass shape."""
    return L4Op(op_type=op_type, target_step_id=target, body_text=body)


# ---------------------------------------------------------------------------
# AC: each op type round-trip
# ---------------------------------------------------------------------------

def test_no_ops_returns_content_unchanged():
    assert op_proc.apply_l4_ops("base content\n", []) == "base content\n"


def test_append_op_appends_to_end_of_slot():
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, [_op("append", body="appended footer\n")])
    assert out.endswith("appended footer\n")
    # And the original content is intact in front.
    assert out.startswith("### step:cycle/boot\n")


def test_append_to_empty_slot_uses_op_body_as_whole_content():
    out = op_proc.apply_l4_ops("", [_op("append", body="only line\n")])
    assert out == "only line\n"


def test_append_inserts_blank_line_paragraph_break():
    # #11144 Finding 7: appends must produce a real markdown paragraph
    # break (two newlines), not a soft line break that collapses adjacent
    # prose into one paragraph in the composed output.
    out = op_proc.apply_l4_ops("no trailing newline", [_op("append", body="X\n")])
    assert out == "no trailing newline\n\nX\n"


def test_whole_slot_replace_no_target_replaces_everything():
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, [_op("replace", body="totally new slot body\n")])
    assert out == "totally new slot body\n"


def test_replace_step_substitutes_only_targeted_body():
    new_body = "REPLACED PICKUP BODY\n"
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, [_op("replace", target="pickup", body=new_body)])
    # Heading preserved.
    assert "### step:cycle/pickup\n" in out
    # New body present.
    assert "REPLACED PICKUP BODY\n" in out
    # Old body gone.
    assert "pickup body\n" not in out
    # Adjacent steps untouched.
    assert "### step:cycle/boot\nboot body line 1\nboot body line 2\n" in out
    assert "### step:cycle/work\nwork body\n" in out


def test_replace_step_first_step_in_slot():
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, [_op("replace", target="boot", body="NEW BOOT\n")])
    assert "### step:cycle/boot\nNEW BOOT\n" in out
    assert "boot body line 1" not in out


def test_replace_step_last_step_in_slot():
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, [_op("replace", target="work", body="NEW WORK\n")])
    assert out.endswith("### step:cycle/work\nNEW WORK\n")
    assert "work body" not in out


def test_insert_before_step_places_body_before_heading():
    out = op_proc.apply_l4_ops(
        SLOT_WITH_THREE_STEPS, [_op("insert-before", target="pickup", body="PRE-PICKUP\n")]
    )
    # New body appears right before the pickup heading.
    assert "PRE-PICKUP\n### step:cycle/pickup\n" in out
    # Adjacent steps' bodies untouched.
    assert "### step:cycle/boot\nboot body line 1\nboot body line 2\n" in out
    assert "### step:cycle/work\nwork body\n" in out


def test_insert_before_first_step_keeps_step_after_inserted_body():
    out = op_proc.apply_l4_ops(
        SLOT_WITH_THREE_STEPS, [_op("insert-before", target="boot", body="HEADER\n")]
    )
    assert out.startswith("HEADER\n### step:cycle/boot\n")


def test_insert_after_step_places_body_before_next_step():
    out = op_proc.apply_l4_ops(
        SLOT_WITH_THREE_STEPS, [_op("insert-after", target="pickup", body="POST-PICKUP\n")]
    )
    # New body appears between pickup body and work heading.
    assert "pickup body\n\nPOST-PICKUP\n### step:cycle/work\n" in out


def test_insert_after_last_step_appends_to_slot_end():
    out = op_proc.apply_l4_ops(
        SLOT_WITH_THREE_STEPS, [_op("insert-after", target="work", body="POST-WORK\n")]
    )
    assert out.endswith("POST-WORK\n")


# ---------------------------------------------------------------------------
# AC: multi-op scenarios applied in source order
# ---------------------------------------------------------------------------

def test_multiple_ops_apply_in_source_order():
    """Two replaces on different steps + one append should compose."""
    ops = [
        _op("replace", target="boot", body="NEW BOOT\n"),
        _op("replace", target="work", body="NEW WORK\n"),
        _op("append", body="FOOTER\n"),
    ]
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, ops)
    assert "### step:cycle/boot\nNEW BOOT\n" in out
    assert "### step:cycle/pickup\npickup body\n" in out
    assert "### step:cycle/work\nNEW WORK\n" in out
    assert out.endswith("FOOTER\n")


def test_two_replaces_on_same_step_later_wins():
    """Source order means a later op overwrites an earlier op on the same target."""
    ops = [
        _op("replace", target="pickup", body="FIRST WINS\n"),
        _op("replace", target="pickup", body="ACTUALLY LAST\n"),
    ]
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, ops)
    assert "ACTUALLY LAST" in out
    assert "FIRST WINS" not in out


def test_insert_after_then_insert_after_stacks_in_source_order():
    """Two insert-afters on the same step stack: the second lands between the first insertion and the next step."""
    ops = [
        _op("insert-after", target="pickup", body="FIRST\n"),
        _op("insert-after", target="pickup", body="SECOND\n"),
    ]
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, ops)
    # By design, "insert-after step:pickup" finds the pickup region and
    # inserts at body_end. After the first op, body_end now sits AFTER
    # "FIRST\n" because that became part of pickup's body region. So the
    # second insertion lands after FIRST — stack order matches source order.
    assert "pickup body\n\nFIRST\nSECOND\n### step:cycle/work\n" in out


def test_insert_before_then_replace_targets_post_insert_content():
    """An insert-before that prepends new content should not break a subsequent replace on the same target."""
    ops = [
        _op("insert-before", target="work", body="PREFACE\n"),
        _op("replace", target="work", body="REPLACED WORK\n"),
    ]
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, ops)
    assert "PREFACE\n### step:cycle/work\nREPLACED WORK\n" in out
    assert "work body" not in out


def test_whole_slot_replace_then_append_composes():
    """Whole-slot replace + append: replace overwrites; append adds to the new slot."""
    ops = [
        _op("replace", body="WHOLE SLOT NEW\n"),
        _op("append", body="FOOTER\n"),
    ]
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, ops)
    assert out == "WHOLE SLOT NEW\n\nFOOTER\n"


def test_order_independence_for_disjoint_targets():
    """Replaces on disjoint steps commute (final content same regardless of order)."""
    ops_a = [
        _op("replace", target="boot", body="NEW BOOT\n"),
        _op("replace", target="work", body="NEW WORK\n"),
    ]
    ops_b = list(reversed(ops_a))
    out_a = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, ops_a)
    out_b = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, ops_b)
    assert out_a == out_b


# ---------------------------------------------------------------------------
# Edge cases: missing target, hyphenated id, single-step slot
# ---------------------------------------------------------------------------

def test_replace_step_missing_target_raises():
    with pytest.raises(op_proc.L4OpTargetNotFound):
        op_proc.apply_l4_ops(
            SLOT_WITH_THREE_STEPS, [_op("replace", target="nonexistent", body="x\n")]
        )


def test_insert_before_missing_target_raises():
    with pytest.raises(op_proc.L4OpTargetNotFound):
        op_proc.apply_l4_ops(
            SLOT_WITH_THREE_STEPS, [_op("insert-before", target="nope", body="x\n")]
        )


def test_insert_after_missing_target_raises():
    with pytest.raises(op_proc.L4OpTargetNotFound):
        op_proc.apply_l4_ops(
            SLOT_WITH_THREE_STEPS, [_op("insert-after", target="nope", body="x\n")]
        )


def test_hyphenated_step_id_targetable():
    content = "### step:cycle/pickup-2\nbody-2\n"
    out = op_proc.apply_l4_ops(content, [_op("replace", target="pickup-2", body="NEW\n")])
    assert out == "### step:cycle/pickup-2\nNEW\n"


def test_single_step_slot_replace_keeps_heading():
    content = "### step:cycle/only\nold\n"
    out = op_proc.apply_l4_ops(content, [_op("replace", target="only", body="new\n")])
    assert out == "### step:cycle/only\nnew\n"


def test_step_id_with_underscores_targetable():
    content = "### step:cycle/my_step_id\nbody\n"
    out = op_proc.apply_l4_ops(content, [_op("replace", target="my_step_id", body="new\n")])
    assert out == "### step:cycle/my_step_id\nnew\n"


def test_body_without_trailing_newline_is_normalized():
    """Op bodies missing a trailing newline still produce well-formed output.

    Note: the blank-line separator between pickup and work in the input
    is part of pickup's body region, so the replace removes it. The
    insertion still gets a guaranteed trailing newline.
    """
    out = op_proc.apply_l4_ops(
        SLOT_WITH_THREE_STEPS, [_op("replace", target="pickup", body="no newline")]
    )
    assert "### step:cycle/pickup\nno newline\n### step:cycle/work\n" in out


def test_unknown_op_type_raises():
    """Defensive: an L4Op with an unrecognized op_type should not silently no-op."""
    bad_op = L4Op(op_type="frobnicate", target_step_id=None, body_text="x")
    with pytest.raises(ValueError, match="unknown L4 op_type"):
        op_proc.apply_l4_ops("content\n", [bad_op])
