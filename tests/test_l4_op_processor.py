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
    # New body appears right before the pickup heading with a blank-line
    # markdown paragraph break (so the inserted body's last paragraph
    # doesn't collapse into the next heading).
    assert "PRE-PICKUP\n\n### step:cycle/pickup\n" in out
    # Adjacent steps' bodies untouched.
    assert "### step:cycle/boot\nboot body line 1\nboot body line 2\n" in out
    assert "### step:cycle/work\nwork body\n" in out


def test_insert_before_first_step_keeps_step_after_inserted_body():
    out = op_proc.apply_l4_ops(
        SLOT_WITH_THREE_STEPS, [_op("insert-before", target="boot", body="HEADER\n")]
    )
    # Paragraph break (\n\n) separates inserted body from the first step
    # heading — matches the contract _apply_insert_after_step uses.
    assert out.startswith("HEADER\n\n### step:cycle/boot\n")


def test_insert_after_step_places_body_before_next_step():
    out = op_proc.apply_l4_ops(
        SLOT_WITH_THREE_STEPS, [_op("insert-after", target="pickup", body="POST-PICKUP\n")]
    )
    # New body appears between pickup body and work heading, with a
    # blank-line paragraph break (#11144: _ensure_paragraph_break).
    assert "pickup body\n\nPOST-PICKUP\n\n### step:cycle/work\n" in out


def test_insert_after_last_step_appends_to_slot_end():
    out = op_proc.apply_l4_ops(
        SLOT_WITH_THREE_STEPS, [_op("insert-after", target="work", body="POST-WORK\n")]
    )
    # Inserts at slot end always end with two newlines (paragraph break).
    assert out.endswith("POST-WORK\n\n")


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
    # Each insert-after appends a blank-line paragraph break to its body
    # (#11144: _ensure_paragraph_break). Stack order matches source order.
    assert "pickup body\n\nFIRST\n\nSECOND\n\n### step:cycle/work\n" in out


def test_insert_before_then_replace_targets_post_insert_content():
    """An insert-before that prepends new content should not break a subsequent replace on the same target."""
    ops = [
        _op("insert-before", target="work", body="PREFACE\n"),
        _op("replace", target="work", body="REPLACED WORK\n"),
    ]
    out = op_proc.apply_l4_ops(SLOT_WITH_THREE_STEPS, ops)
    assert "PREFACE\n\n### step:cycle/work\nREPLACED WORK\n" in out
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


# ---------------------------------------------------------------------------
# #11144: indexed step headings (Step N — step:cycle/<id>)
# ---------------------------------------------------------------------------

def test_step_heading_regex_matches_bare_form():
    """The regex still matches the original `### step:cycle/<id>` form."""
    import re
    assert op_proc._STEP_HEADING_RE.search("### step:cycle/pickup\n")


def test_step_heading_regex_matches_step_n_prefix():
    """`### Step 3 — step:cycle/pickup` matches; captures `pickup`."""
    m = op_proc._STEP_HEADING_RE.search("### Step 3 — step:cycle/pickup\n")
    assert m
    assert m.group(1) == "pickup"


def test_step_heading_regex_matches_numbered_list_prefix():
    """`### 3. step:cycle/pickup` matches; captures `pickup`."""
    m = op_proc._STEP_HEADING_RE.search("### 3. step:cycle/pickup\n")
    assert m
    assert m.group(1) == "pickup"


def test_step_heading_regex_does_not_match_op_directives():
    """Op directives like `### insert-after step:cycle/X` must NOT match
    the anchor regex — otherwise the op processor would try to use
    the directive line itself as an anchor target."""
    assert not op_proc._STEP_HEADING_RE.search("### insert-after step:cycle/pickup\n")
    assert not op_proc._STEP_HEADING_RE.search("### insert-before step:cycle/pickup\n")
    assert not op_proc._STEP_HEADING_RE.search("### replace step:cycle/pickup\n")


def test_insert_after_anchors_to_indexed_heading():
    """Indexed heading (`### Step 3 — step:cycle/pickup`) is a valid op anchor."""
    content = (
        "### Step 2 — step:cycle/resume\n"
        "resume body\n"
        "\n"
        "### Step 3 — step:cycle/pickup\n"
        "pickup body\n"
        "\n"
        "### Step 4 — step:cycle/work\n"
        "work body\n"
    )
    out = op_proc.apply_l4_ops(
        content, [_op("insert-after", target="pickup", body="POST-PICKUP\n")]
    )
    # Insert-after lands between pickup body and the next step heading.
    assert "pickup body\n\nPOST-PICKUP\n\n### Step 4 — step:cycle/work\n" in out


# ---------------------------------------------------------------------------
# AC: hierarchical sub-step renumbering (#11144 — auto-number L2/L3 sub-steps)
# ---------------------------------------------------------------------------


def test_step_heading_regex_accepts_two_level_index():
    """The step-heading regex must match `Step N.M — ` hierarchical form so
    L4 ops can still anchor to renumbered sub-step headings after compose
    runs the auto-numbering pass.
    """
    m = op_proc._STEP_HEADING_RE.search("#### Step 2.1 — step:cycle/check-in\n")
    assert m is not None
    assert m.group(1) == "check-in"


def test_unprefixed_h4_substep_gets_numbered_under_parent():
    """A bare `#### step:cycle/<sub>` heading nested under `### Step N — step:cycle/<parent>`
    is rewritten to `#### Step N.1 — step:cycle/<sub>`.
    """
    content = (
        "### Step 2 — step:cycle/resume\n"
        "resume body\n"
        "\n"
        "#### step:cycle/check-in\n"
        "check-in body\n"
        "\n"
        "### Step 3 — step:cycle/pickup\n"
        "pickup body\n"
    )
    out = op_proc.apply_l4_ops(content, [])
    assert "#### Step 2.1 — step:cycle/check-in\n" in out
    assert "#### step:cycle/check-in\n" not in out


def test_multiple_substeps_under_same_parent_get_sequential_numbers():
    """Two sub-steps under the same parent become Step N.1 and Step N.2."""
    content = (
        "### Step 6 — step:cycle/cleanup\n"
        "cleanup body\n"
        "\n"
        "#### step:cycle/health-check\n"
        "hc body\n"
        "\n"
        "#### step:cycle/vault-synthesis\n"
        "vs body\n"
        "\n"
        "### Step 7 — step:cycle/exit\n"
        "exit body\n"
    )
    out = op_proc.apply_l4_ops(content, [])
    assert "#### Step 6.1 — step:cycle/health-check\n" in out
    assert "#### Step 6.2 — step:cycle/vault-synthesis\n" in out


def test_substeps_under_different_parents_get_independent_numbering():
    """Each parent's sub-steps restart at .1; no cross-parent counter."""
    content = (
        "### Step 2 — step:cycle/resume\n"
        "\n"
        "#### step:cycle/check-in\n"
        "\n"
        "### Step 3 — step:cycle/pickup\n"
        "\n"
        "#### step:cycle/task-intake\n"
        "\n"
        "### Step 4 — step:cycle/work\n"
    )
    out = op_proc.apply_l4_ops(content, [])
    assert "#### Step 2.1 — step:cycle/check-in\n" in out
    assert "#### Step 3.1 — step:cycle/task-intake\n" in out
    # No cross-parent bleed
    assert "#### Step 3.2" not in out
    assert "#### Step 2.2" not in out


def test_renumbering_is_idempotent_overwrites_existing_prefix():
    """A heading already carrying `Step N.M — ` is recomputed, not appended
    to. Authors can hand-number freely; compose owns the canonical numbers.
    """
    content = (
        "### Step 6 — step:cycle/cleanup\n"
        "\n"
        "#### Step 6.5 — step:cycle/health-check\n"
        "hc body\n"
        "\n"
        "#### Step 6.9 — step:cycle/vault-synthesis\n"
        "vs body\n"
    )
    out = op_proc.apply_l4_ops(content, [])
    # The hand-authored .5 / .9 are recomputed to .1 / .2 based on actual order.
    assert "#### Step 6.1 — step:cycle/health-check\n" in out
    assert "#### Step 6.2 — step:cycle/vault-synthesis\n" in out
    assert "#### Step 6.5" not in out
    assert "#### Step 6.9" not in out


def test_renumbering_noop_when_no_l1_parent_headings_present():
    """Slot content without any `### Step N — step:cycle/<id>` parent headings
    is returned unchanged — the auto-numbering pass should not invent parents.
    """
    content = (
        "### step:cycle/boot\n"
        "boot body\n"
        "\n"
        "### step:cycle/work\n"
        "work body\n"
    )
    out = op_proc.apply_l4_ops(content, [])
    # No parent headings present, sub-step numbering should not fire.
    assert out == content


def test_hydrated_diagram_marker_replaced_with_mermaid_block():
    """The L1 source carries `<!-- compose:hydrated-cycle-diagram -->`. Compose
    replaces it with a generated mermaid block reflecting the step hierarchy.
    """
    content = (
        "intro line\n\n"
        "<!-- compose:hydrated-cycle-diagram -->\n\n"
        "### Step 1 — step:cycle/boot\n"
        "boot body\n\n"
        "### Step 2 — step:cycle/resume\n"
        "resume body\n\n"
        "### Step 3 — step:cycle/pickup\n"
        "pickup body\n"
    )
    out = op_proc.apply_l4_ops(content, [])
    assert "<!-- compose:hydrated-cycle-diagram -->" not in out
    assert "```mermaid\nflowchart LR\n" in out
    assert "1. step:cycle/boot" in out
    assert "2. step:cycle/resume" in out
    assert "3. step:cycle/pickup" in out


def test_hydrated_diagram_includes_substeps_with_dotted_labels():
    """Sub-steps anchored under a parent step appear in the rendered diagram
    with their auto-numbered `N.M` labels, in document order.
    """
    content = (
        "<!-- compose:hydrated-cycle-diagram -->\n\n"
        "### Step 2 — step:cycle/resume\n"
        "\n"
        "#### step:cycle/check-in\n"
        "\n"
        "#### step:cycle/triage-external\n"
        "\n"
        "### Step 3 — step:cycle/pickup\n"
    )
    out = op_proc.apply_l4_ops(content, [])
    assert "2.1 check-in" in out
    assert "2.2 triage-external" in out
    # Sub-steps should be wired up as edges in the chain
    assert "S2 --> S2_1" in out
    assert "S2_1 --> S2_2" in out


def test_hydrated_diagram_partitions_boot_phase_into_session_boot_subgraph():
    """Parents matching boot-phase step IDs (boot, resume) and their
    sub-steps go into the SessionBoot subgraph; later steps go into WalkLoop.
    """
    content = (
        "<!-- compose:hydrated-cycle-diagram -->\n\n"
        "### Step 1 — step:cycle/boot\n"
        "\n"
        "### Step 2 — step:cycle/resume\n"
        "\n"
        "### Step 3 — step:cycle/pickup\n"
        "\n"
        "### Step 7 — step:cycle/exit\n"
    )
    out = op_proc.apply_l4_ops(content, [])
    assert 'subgraph SessionBoot["Session boot (once per session)"]' in out
    assert 'subgraph WalkLoop["Per cared event (repeats per nudge)"]' in out
    # SessionBoot → WalkLoop transition edge exists
    assert "SessionBoot --> WalkLoop" in out


def test_hydrated_diagram_marker_absent_is_noop():
    """If the marker isn't present in the slot content (e.g. non-instructions
    slots), the diagram render is a no-op and content passes through unchanged.
    """
    content = "## Identity\nsome body\n"
    out = op_proc.apply_l4_ops(content, [])
    assert out == content


def test_hydrated_diagram_marker_with_no_parents_leaves_marker():
    """If the marker is present but the slot has no L1 parent step headings
    (malformed content), leave the marker in place so the gap is visible
    rather than silently emitting an empty diagram.
    """
    content = "<!-- compose:hydrated-cycle-diagram -->\n\nno steps here\n"
    out = op_proc.apply_l4_ops(content, [])
    assert "<!-- compose:hydrated-cycle-diagram -->" in out


def test_renumbering_applies_after_l4_ops_so_inserted_substeps_are_indexed():
    """L4 insert-after ops that add a new sub-step are picked up by the
    renumbering pass and indexed in their final position. The compose-time
    contract: author L2/L3 sub-steps WITHOUT numbers; the renumber pass
    indexes them.
    """
    content = (
        "### Step 2 — step:cycle/resume\n"
        "resume body\n"
        "\n"
        "#### step:cycle/check-in\n"
        "check-in body\n"
        "\n"
        "### Step 3 — step:cycle/pickup\n"
        "pickup body\n"
    )
    out = op_proc.apply_l4_ops(
        content,
        [
            _op(
                "insert-after",
                target="check-in",
                body="#### step:cycle/triage-external\n\ntriage body\n",
            )
        ],
    )
    assert "#### Step 2.1 — step:cycle/check-in\n" in out
    assert "#### Step 2.2 — step:cycle/triage-external\n" in out
