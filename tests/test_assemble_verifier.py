"""Tests for references/scripts/assemble_verifier.py (#10441, PRD-B Story B2)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import assemble_verifier as av  # noqa: E402


# ---------------------------------------------------------------------------
# Identity / empty
# ---------------------------------------------------------------------------

def test_identity_passes():
    body = "→ run sub-skill: boot-bootstrap\n\n### step:cycle/boot\nbody\n"
    result = av.verify_preservation(body, body)
    assert result.ok is True
    assert result.missing_sub_skills == []
    assert result.extra_sub_skills == []
    assert result.missing_step_ids == []
    assert result.extra_step_ids == []


def test_empty_inputs_pass():
    result = av.verify_preservation("", "")
    assert result.ok is True


def test_no_refs_at_all_passes():
    linked = "# Heading\n\nProse without preservation tokens.\n"
    assembled = "# Different heading\n\nReworded prose.\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is True


# ---------------------------------------------------------------------------
# Sub-skill multiset
# ---------------------------------------------------------------------------

def test_missing_sub_skill_ref_detected():
    linked = "→ run sub-skill: boot-bootstrap\n→ run sub-skill: task-pickup\n"
    assembled = "→ run sub-skill: boot-bootstrap\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is False
    assert result.missing_sub_skills == ["task-pickup"]
    assert result.extra_sub_skills == []


def test_extra_sub_skill_ref_detected():
    linked = "→ run sub-skill: boot-bootstrap\n"
    assembled = "→ run sub-skill: boot-bootstrap\n→ run sub-skill: hallucinated\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is False
    assert result.missing_sub_skills == []
    assert result.extra_sub_skills == ["hallucinated"]


def test_duplicate_sub_skill_refs_preserved_passes():
    linked = "→ run sub-skill: x\n→ run sub-skill: x\n→ run sub-skill: y\n"
    assembled = "→ run sub-skill: y\n→ run sub-skill: x\n→ run sub-skill: x\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is True


def test_duplicate_collapsed_in_assembled_fails():
    # linked has two copies of 'x'; assembled has only one.
    linked = "→ run sub-skill: x\n→ run sub-skill: x\n"
    assembled = "→ run sub-skill: x\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is False
    assert result.missing_sub_skills == ["x"]


def test_sub_skill_ref_flexible_whitespace():
    # Implementation detail (#10441): allow stray whitespace after the
    # arrow / colon so the regex doesn't miss a reference that survived
    # the LLM with cosmetic spacing changes.
    linked = "→ run sub-skill: x\n"
    assembled = "→  run sub-skill:  x\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is True


# ---------------------------------------------------------------------------
# Step ID multiset
# ---------------------------------------------------------------------------

def test_missing_step_id_detected():
    linked = "### step:cycle/boot\n### step:cycle/work\n"
    assembled = "### step:cycle/boot\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is False
    assert result.missing_step_ids == ["work"]


def test_extra_step_id_detected():
    linked = "### step:cycle/boot\n"
    assembled = "### step:cycle/boot\n### step:cycle/invented\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is False
    assert result.extra_step_ids == ["invented"]


def test_step_id_duplicates_preserved():
    linked = "step:cycle/a step:cycle/a step:cycle/b"
    assembled = "step:cycle/b step:cycle/a step:cycle/a"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is True


def test_step_id_with_hyphenated_id():
    linked = "step:cycle/check-in step:cycle/pipeline-sentinel"
    assembled = "step:cycle/pipeline-sentinel step:cycle/check-in"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is True


# ---------------------------------------------------------------------------
# Combined diffs (sub-skill AND step both off)
# ---------------------------------------------------------------------------

def test_both_dimensions_off_reports_both():
    linked = "→ run sub-skill: x\nstep:cycle/a\n"
    assembled = "→ run sub-skill: y\nstep:cycle/b\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is False
    assert result.missing_sub_skills == ["x"]
    assert result.extra_sub_skills == ["y"]
    assert result.missing_step_ids == ["a"]
    assert result.extra_step_ids == ["b"]


def test_diff_lists_are_sorted():
    linked = "→ run sub-skill: c\n→ run sub-skill: a\n→ run sub-skill: b\n"
    assembled = ""
    result = av.verify_preservation(linked, assembled)
    assert result.missing_sub_skills == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Robustness against partial-word noise
# ---------------------------------------------------------------------------

def test_step_id_word_prefix_does_not_match():
    # ``mystep:cycle/boot`` should NOT be treated as ``step:cycle/boot`` —
    # the ``\b`` boundary requires a non-word char (or start-of-string)
    # before ``s``. A surrounding word char defeats the match.
    linked = ""
    assembled = "mystep:cycle/boot\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is True
    assert result.extra_step_ids == []


def test_step_id_punctuation_prefix_matches():
    # ``-step:cycle/boot`` IS a step-ID reference (hyphen is non-word).
    linked = ""
    assembled = "-step:cycle/boot\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is False
    assert result.extra_step_ids == ["boot"]


def test_sub_skill_ref_whitespace_between_run_and_subskill():
    linked = "→ run sub-skill: x\n"
    assembled = "→ run  sub-skill: x\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is True


def test_sub_skill_ref_requires_arrow():
    # Plain ``run sub-skill: x`` (no arrow) is not a reference per TRD §6.1.
    linked = ""
    assembled = "run sub-skill: ghost\n"
    result = av.verify_preservation(linked, assembled)
    assert result.ok is True
    assert result.extra_sub_skills == []


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def test_preservation_result_default_lists_are_independent():
    # Defensive against the classic dataclass mutable-default trap.
    r1 = av.PreservationResult(ok=True)
    r2 = av.PreservationResult(ok=True)
    r1.missing_sub_skills.append("polluted")
    assert r2.missing_sub_skills == []


def test_preservation_result_fields_present():
    body = "→ run sub-skill: x\nstep:cycle/y"
    r = av.verify_preservation(body, body)
    for attr in (
        "ok",
        "missing_sub_skills",
        "extra_sub_skills",
        "missing_step_ids",
        "extra_step_ids",
    ):
        assert hasattr(r, attr)
