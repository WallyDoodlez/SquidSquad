"""#11227 — activate L2-L3 inline op anchoring in the link stage.

L1-L3 source bodies may carry `### insert-after step:cycle/<id>` (and
`insert-before` / `replace step:cycle/<id>`) directives that should anchor
their content at the named cycle step rather than sit inline at the source
file's position. #11139 stripped these headers (leaving content stranded);
#11227 replaces the strip with extract-and-apply:

- `v2_link_stage._split_body_segments` splits a body into ordered
  content / op segments using a focused line scanner (NOT the L4 file
  parser, which would mis-read the body's own `## ` headings).
- `v2_link_stage._assemble_slot` collects the H3 anchor set from base
  content, applies step-targeted ops whose anchor is present, and
  degrades ops whose anchor is absent (e.g. L3 ops targeting L2-defined
  H4 sub-steps — AC-6 deferred) to inline content so compose stays green.

Covers AC-1 (extraction), AC-4/AC-5 (L2 ops anchor at L1 H3 steps),
AC-6 graceful deferral (non-anchorable ops degrade, compose does not
raise), AC-8 (these unit tests).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import v2_link_stage as v  # noqa: E402


# ---------------------------------------------------------------------------
# _split_body_segments — AC-1 extraction grammar
# ---------------------------------------------------------------------------

def test_split_extracts_step_targeted_op_as_op_segment():
    body = (
        "Base prose for the slot.\n\n"
        "### insert-after step:cycle/resume\n\n"
        "#### step:cycle/check-in\n\nCheck in with the human.\n"
    )
    segs = v._split_body_segments(body, "instructions")
    kinds = [k for k, _ in segs]
    assert kinds == ["content", "op"]
    assert segs[0][1] == "Base prose for the slot."
    op = segs[1][1]
    assert op.op_type == "insert-after"
    assert op.target_step_id == "resume"
    assert op.body_text == "#### step:cycle/check-in\n\nCheck in with the human."


def test_split_bare_append_drops_header_body_is_content():
    """A bare `### append` is not a step op — its header is dropped and the
    body flows on as a content segment (concatenation == slot-end append)."""
    body = "First chunk.\n\n### append\n\nAppended chunk.\n"
    segs = v._split_body_segments(body, "identity")
    assert [k for k, _ in segs] == ["content", "content"]
    assert segs[0][1] == "First chunk."
    assert segs[1][1] == "Appended chunk."


def test_split_section_heading_ends_op_body():
    """A `## Section` heading ends the current op body and is itself
    content — the op must not swallow a following section."""
    body = (
        "### insert-after step:cycle/work\n\n"
        "#### step:cycle/pipeline-sentinel\n\nScan pipeline.\n\n"
        "## Reactive sub-skills\n\nThese run reactively.\n"
    )
    segs = v._split_body_segments(body, "instructions")
    assert [k for k, _ in segs] == ["op", "content"]
    assert segs[0][1].body_text == "#### step:cycle/pipeline-sentinel\n\nScan pipeline."
    assert segs[1][1].startswith("## Reactive sub-skills")


def test_split_step_anchor_heading_is_content_not_op():
    """`### step:cycle/<id>` is an anchor, not an op directive — it must
    stay in content so ops can target it."""
    body = "### step:cycle/resume\n\nResume body.\n"
    segs = v._split_body_segments(body, "instructions")
    assert [k for k, _ in segs] == ["content"]
    assert "### step:cycle/resume" in segs[0][1]


def test_split_malformed_op_like_heading_is_content():
    """An op-like-but-malformed H3 (e.g. `### replace the foo`) must NOT
    raise — it degrades to content so compose stays robust to prose."""
    body = "### replace the foo with bar\n\nProse.\n"
    segs = v._split_body_segments(body, "soul")
    assert [k for k, _ in segs] == ["content"]
    assert segs[0][1].startswith("### replace the foo")


# ---------------------------------------------------------------------------
# _assemble_slot — AC-4/AC-5 apply, AC-6 graceful degrade
# ---------------------------------------------------------------------------

def test_assemble_applies_op_when_anchor_present():
    base = "### step:cycle/resume\n\nResume body.\n"
    op_body = (
        "### insert-after step:cycle/resume\n\n"
        "#### step:cycle/check-in\n\nCheck in.\n"
    )
    combined, inline_ops = v._assemble_slot("instructions", [base, op_body])
    # The op anchors → it is returned as an inline op (applied by caller).
    assert len(inline_ops) == 1
    assert inline_ops[0].target_step_id == "resume"
    # The anchor stays in the base; the op body is NOT inlined in base.
    assert "### step:cycle/resume" in combined
    assert "step:cycle/check-in" not in combined
    # Applying confirms it lands right after the resume step.
    from l4_op_processor import apply_l4_ops
    applied = apply_l4_ops(combined, inline_ops)
    r = applied.index("step:cycle/resume")
    c = applied.index("step:cycle/check-in")
    assert r < c


def test_assemble_degrades_op_when_anchor_absent():
    """An op whose target anchor is not present as an H3 (e.g. an L3 op
    targeting an L2-defined H4 sub-step) degrades to inline content; no
    inline op is emitted and the body is preserved in the base."""
    base = "#### step:cycle/delivery-packaging\n\nPackage it.\n"  # H4, not an anchor
    op_body = (
        "### insert-after step:cycle/delivery-packaging\n\n"
        "#### step:cycle/skill-delivery-doc\n\nWrite skill doc.\n"
    )
    combined, inline_ops = v._assemble_slot("instructions", [base, op_body])
    assert inline_ops == []
    # Degraded: the op body survives inline in the combined base.
    assert "step:cycle/skill-delivery-doc" in combined
    assert "Write skill doc." in combined


def test_assemble_no_op_target_not_found_raised(monkeypatch):
    """Regression: a non-anchorable op must never reach apply_l4_ops (which
    would raise L4OpTargetNotFound). _assemble_slot filters it out first."""
    base = "Base only, no anchors."
    op_body = "### insert-after step:cycle/nonexistent\n\nOrphan content.\n"
    combined, inline_ops = v._assemble_slot("soul", [base, op_body])
    assert inline_ops == []
    assert "Orphan content." in combined


# ---------------------------------------------------------------------------
# emit_v2_linked — integration against live sources (AC-4/AC-5/AC-6)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role,anchor,inserted", [
    ("pm", "### step:cycle/resume", "#### step:cycle/check-in"),
    ("dm", "### step:cycle/resume", "#### step:cycle/issue-triage"),
    ("verifier", "### step:cycle/resume", "#### step:cycle/e2e-check"),
    ("worker", "### step:cycle/resume", "#### step:cycle/triage-issues"),
])
def test_emit_l2_insert_after_anchors_at_l1_step(role, anchor, inserted):
    out = v.emit_v2_linked(role, None)
    lines = out.splitlines()
    ai = next((i for i, l in enumerate(lines) if l.strip() == anchor), -1)
    ii = next((i for i, l in enumerate(lines) if l.strip() == inserted), -1)
    assert ai >= 0, f"{role}: L1 anchor {anchor!r} missing"
    assert ii >= 0, f"{role}: inserted step {inserted!r} missing"
    assert ai < ii, f"{role}: {inserted!r} did not anchor after {anchor!r}"


@pytest.mark.parametrize("role", ["dm", "pm", "verifier", "worker"])
def test_emit_l3_compose_does_not_raise(role):
    """AC-6 deferral: L3 ops target L2-defined H4 sub-steps that are not H3
    anchors; they degrade to inline rather than raising L4OpTargetNotFound."""
    out = v.emit_v2_linked(role, "skill")
    assert out  # non-empty, no exception
