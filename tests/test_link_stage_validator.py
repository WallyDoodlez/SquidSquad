"""Tests for references/scripts/link_stage_validator.py (#10491, PRD-A A2e)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import link_stage_validator as v  # noqa: E402
from link_stage_validator import LinkStageSource, LinkStageValidationError  # noqa: E402
from l4_parser import L4Document, L4Op, parse_l4_text  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _l4_op(op_type, target=None, body=""):
    return L4Op(op_type=op_type, target_step_id=target, body_text=body)


def _l4_doc(slots):
    """slots: dict[str, list[L4Op]] — convenience constructor."""
    return L4Document(slots=dict(slots))


def _src(layer, path, slot, body=""):
    return LinkStageSource(layer=layer, path=path, slot=slot, body=body)


def _well_formed_sources_with_steps(step_ids):
    """A minimal L1-L3 source set containing the given step IDs in the instructions slot."""
    body = "\n".join(f"### step:cycle/{sid}\nbody.\n" for sid in step_ids)
    return [
        _src("L1", "references/roles/identity.md", "identity", "Base identity body."),
        _src("L1", "references/roles/instructions.md", "instructions", body),
    ]


# ---------------------------------------------------------------------------
# R1: L4 file containing ## Vault H2 → abort
# ---------------------------------------------------------------------------

def test_r1_l4_with_vault_h2_aborts():
    doc = _l4_doc({"vault": []})
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(doc, [], l4_path=".squidsquad/project/worker.md")
    assert exc.value.rule == "R1"
    assert "Vault" in str(exc.value)


def test_r1_l4_without_vault_h2_passes():
    doc = _l4_doc({"identity": [_l4_op("append", body="→ run sub-skill: x")]})
    v.validate_link_stage(doc, [])  # no raise


# ---------------------------------------------------------------------------
# R2: L2/L3 source with slot: vault → abort
# ---------------------------------------------------------------------------

def test_r2_l2_source_with_vault_slot_aborts():
    sources = [_src("L2", "references/roles/worker/oops.md", "vault")]
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(L4Document.empty(), sources)
    assert exc.value.rule == "R2"
    assert exc.value.file_path == "references/roles/worker/oops.md"


def test_r2_l3_source_with_vault_slot_aborts():
    sources = [_src("L3", "references/roles/worker/skill/oops.md", "vault")]
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(L4Document.empty(), sources)
    assert exc.value.rule == "R2"


def test_r2_l1_source_with_vault_slot_passes():
    """L1 may declare vault — that's the L1-exclusive ownership the rule protects."""
    sources = [_src("L1", "references/roles/vault.md", "vault", "Vault body.")]
    v.validate_link_stage(L4Document.empty(), sources)


# ---------------------------------------------------------------------------
# R3: L1-L3 source with slot: project-context → abort
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("layer", ["L1", "L2", "L3"])
def test_r3_any_l1_l3_source_with_project_context_slot_aborts(layer):
    sources = [_src(layer, f"references/{layer}/oops.md", "project-context")]
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(L4Document.empty(), sources)
    assert exc.value.rule == "R3"


def test_r3_l4_source_with_project_context_slot_does_not_trigger():
    # #10751 W4 regression: R3 must only fire on L1-L3 sources. If the
    # source collector ever yields L4 entries (today it pre-filters,
    # but the asymmetry with R2 was a maintenance hazard), R3's
    # explicit layer guard must keep L4's project-context content
    # flowing — that's the slot L4 is supposed to own.
    sources = [_src("L4", "project/pm.md", "project-context")]
    # No raise = guard works. R4/R5/R6/R7 don't apply to this minimal
    # input either, so the validator completes cleanly.
    v.validate_link_stage(L4Document.empty(), sources)


# ---------------------------------------------------------------------------
# R4: L4 ### append under ## Instructions without sub-skill ref → abort
# ---------------------------------------------------------------------------

def test_r4_instructions_append_without_sub_skill_ref_aborts():
    op = _l4_op("append", body="Just prose. No reference.")
    doc = _l4_doc({"instructions": [op]})
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(doc, [])
    assert exc.value.rule == "R4"


def test_r4_instructions_append_with_sub_skill_ref_passes():
    op = _l4_op("append", body="→ run sub-skill: pipeline-sentinel\n\nbody.")
    doc = _l4_doc({"instructions": [op]})
    v.validate_link_stage(doc, [])  # no raise


def test_r4_append_under_other_slot_does_not_require_sub_skill_ref():
    """R4 is Instructions-only; an append on Identity slot doesn't need a sub-skill ref."""
    op = _l4_op("append", body="Just prose. Identity slot.")
    doc = _l4_doc({"identity": [op]})
    v.validate_link_stage(doc, [])


# ---------------------------------------------------------------------------
# R5: L4 op references non-existent step-id → abort with name in diagnostic
# ---------------------------------------------------------------------------

def test_r5_unknown_step_id_aborts_and_names_it():
    sources = _well_formed_sources_with_steps(["boot", "work"])
    bad_op = _l4_op("replace", target="ghost", body="x")
    doc = _l4_doc({"instructions": [bad_op]})
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(doc, sources)
    assert exc.value.rule == "R5"
    assert exc.value.step_id == "ghost"
    assert "ghost" in str(exc.value)


def test_r5_known_step_id_passes():
    sources = _well_formed_sources_with_steps(["boot", "work"])
    doc = _l4_doc({
        "instructions": [
            _l4_op("replace", target="work", body="new body"),
            _l4_op("insert-after", target="boot", body="extra"),
        ]
    })
    v.validate_link_stage(doc, sources)


def test_r5_targetless_op_does_not_trigger():
    """`append` and whole-slot `replace` have target_step_id=None — never R5."""
    sources = []  # no step ids at all
    doc = _l4_doc({
        "instructions": [_l4_op("append", body="→ run sub-skill: x")],
        "responsibility": [_l4_op("replace", body="whole-slot replace body")],
    })
    v.validate_link_stage(doc, sources)


# ---------------------------------------------------------------------------
# R6: whole-slot replace mixed with other ops in same slot → abort
# ---------------------------------------------------------------------------

def test_r6_whole_slot_replace_with_another_op_in_same_slot_aborts():
    doc = _l4_doc({"responsibility": [
        _l4_op("replace", body="whole new responsibility"),
        _l4_op("append", body="more"),
    ]})
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(doc, [])
    assert exc.value.rule == "R6"


def test_r6_solo_whole_slot_replace_passes():
    """A whole-slot replace by itself is legal (mutual exclusivity = no co-ops)."""
    doc = _l4_doc({"responsibility": [_l4_op("replace", body="new body")]})
    v.validate_link_stage(doc, [])


def test_r6_scope_is_per_slot_not_per_file():
    """A whole-slot replace in one slot does not affect ops in a different slot."""
    doc = _l4_doc({
        "responsibility": [_l4_op("replace", body="new resp body")],
        "instructions": [_l4_op("append", body="→ run sub-skill: x")],
    })
    v.validate_link_stage(doc, [])


# ---------------------------------------------------------------------------
# R7: two replace step:cycle/<id> blocks targeting same step → abort
# ---------------------------------------------------------------------------

def test_r7_duplicate_replace_target_aborts():
    sources = _well_formed_sources_with_steps(["work"])
    doc = _l4_doc({"instructions": [
        _l4_op("replace", target="work", body="first"),
        _l4_op("replace", target="work", body="second"),
    ]})
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(doc, sources)
    assert exc.value.rule == "R7"
    assert exc.value.step_id == "work"


def test_r7_disjoint_replace_targets_pass():
    sources = _well_formed_sources_with_steps(["boot", "work"])
    doc = _l4_doc({"instructions": [
        _l4_op("replace", target="boot", body="x"),
        _l4_op("replace", target="work", body="y"),
    ]})
    v.validate_link_stage(doc, sources)


def test_r7_replace_plus_insert_before_same_target_is_legal():
    """R7 is duplicate REPLACE-on-same-step. An insert-before/after on the same step is fine."""
    sources = _well_formed_sources_with_steps(["work"])
    doc = _l4_doc({"instructions": [
        _l4_op("replace", target="work", body="x"),
        _l4_op("insert-after", target="work", body="y"),
    ]})
    v.validate_link_stage(doc, sources)


# ---------------------------------------------------------------------------
# Cross-rule: empty L4 + clean sources passes
# ---------------------------------------------------------------------------

def test_empty_l4_and_clean_sources_passes():
    v.validate_link_stage(L4Document.empty(), _well_formed_sources_with_steps(["boot"]))


def test_validation_runs_rules_in_declaration_order_r1_first():
    """If both R1 and (say) R7 would fire, R1 reported first per declaration order."""
    sources = _well_formed_sources_with_steps(["work"])
    doc = _l4_doc({
        "vault": [],  # triggers R1
        "instructions": [
            _l4_op("replace", target="work", body="a"),
            _l4_op("replace", target="work", body="b"),  # also triggers R7
        ],
    })
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(doc, sources)
    assert exc.value.rule == "R1"


# ---------------------------------------------------------------------------
# Integration with A2b's parser (sanity)
# ---------------------------------------------------------------------------

def test_validates_against_l4doc_parsed_from_text():
    """End-to-end: parse L4 text via A2b, then validate via A2e."""
    l4_text = (
        "## Instructions\n\n"
        "### append\n\n"
        "→ run sub-skill: pipeline-sentinel\n\n"
        "Body.\n"
    )
    doc = parse_l4_text(l4_text)
    v.validate_link_stage(doc, _well_formed_sources_with_steps([]))


def test_validates_l4_append_without_sub_skill_ref_via_parser():
    l4_text = (
        "## Instructions\n\n"
        "### append\n\n"
        "Just prose. No reference.\n"
    )
    doc = parse_l4_text(l4_text)
    with pytest.raises(LinkStageValidationError) as exc:
        v.validate_link_stage(doc, [])
    assert exc.value.rule == "R4"
