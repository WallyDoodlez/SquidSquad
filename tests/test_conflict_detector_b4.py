"""Tests for references/scripts/conflict_detector.py (#10445, PRD-B Story B4)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import conflict_detector as cd  # noqa: E402
from conflict_detector import Conflict  # noqa: E402


# ---------------------------------------------------------------------------
# parse_assemble_output — splitting body from conflicts
# ---------------------------------------------------------------------------

def test_parse_no_delimiter_returns_body_and_empty_conflicts():
    """LLM output without the delimiter is treated as zero conflicts."""
    text = "just the body\n"
    body, conflicts = cd.parse_assemble_output(text)
    assert body == "just the body\n"
    assert conflicts == []


def test_parse_delimiter_with_none_placeholder_means_zero_conflicts():
    text = "Body line one.\nBody line two.\n\n<!-- ASSEMBLE_CONFLICTS -->\n\n(none)\n"
    body, conflicts = cd.parse_assemble_output(text)
    assert body.startswith("Body line one.")
    assert "ASSEMBLE_CONFLICTS" not in body
    assert conflicts == []


def test_parse_delimiter_with_empty_block_means_zero_conflicts():
    text = "body\n\n<!-- ASSEMBLE_CONFLICTS -->\n\n"
    body, conflicts = cd.parse_assemble_output(text)
    assert body == "body\n"
    assert conflicts == []


def test_parse_one_well_formed_conflict():
    text = (
        "rewritten body\n\n"
        "<!-- ASSEMBLE_CONFLICTS -->\n\n"
        "- slot: instructions\n"
        "  winner_layer: L4\n"
        "  winner_path: .squidsquad/project/worker.md\n"
        "  winner_quote: verifier handles all verification\n"
        "  loser_layer: L2\n"
        "  loser_path: references/roles/worker/instructions.md\n"
        "  loser_quote: verify pending-test items each cycle\n"
        "  why: L4 transfers verification responsibility\n"
        "  resolution: Assembled body says verifier owns verification\n"
    )
    body, conflicts = cd.parse_assemble_output(text)
    assert body == "rewritten body\n"
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.slot == "instructions"
    assert c.winner_layer == "L4"
    assert c.loser_layer == "L2"
    assert c.winner_path == ".squidsquad/project/worker.md"
    assert "verifier handles all verification" in c.winner_quote
    assert "verify pending-test items" in c.loser_quote
    assert c.why.startswith("L4 transfers")
    assert c.resolution.startswith("Assembled body")


def test_parse_multiple_conflicts():
    text = (
        "body\n<!-- ASSEMBLE_CONFLICTS -->\n"
        "- slot: instructions\n"
        "  winner_layer: L4\n"
        "  loser_layer: L2\n"
        "  why: foo\n"
        "- slot: identity\n"
        "  winner_layer: L3\n"
        "  loser_layer: L1\n"
        "  why: bar\n"
    )
    _, conflicts = cd.parse_assemble_output(text)
    assert [c.slot for c in conflicts] == ["instructions", "identity"]
    assert [c.winner_layer for c in conflicts] == ["L4", "L3"]
    assert [c.why for c in conflicts] == ["foo", "bar"]


def test_parse_missing_fields_default_to_empty_string():
    """A partial record still surfaces in the report (avoid blocking on parse errors)."""
    text = (
        "body\n<!-- ASSEMBLE_CONFLICTS -->\n"
        "- slot: instructions\n"
        "  winner_layer: L4\n"  # everything else missing
    )
    _, conflicts = cd.parse_assemble_output(text)
    assert len(conflicts) == 1
    assert conflicts[0].why == ""
    assert conflicts[0].loser_path == ""


def test_parse_handles_quoted_string_values():
    """LLMs sometimes emit `key: "quoted value"`. Quotes are stripped."""
    text = (
        "body\n<!-- ASSEMBLE_CONFLICTS -->\n"
        "- slot: instructions\n"
        '  winner_quote: "verifier owns it"\n'
    )
    _, conflicts = cd.parse_assemble_output(text)
    assert conflicts[0].winner_quote == "verifier owns it"


def test_parse_handles_continuation_line_for_long_quote():
    """A wrapped quote (continuation line without `key:`) joins to the prior field."""
    text = (
        "body\n<!-- ASSEMBLE_CONFLICTS -->\n"
        "- slot: instructions\n"
        "  winner_quote: first line of a long quote\n"
        "    that wrapped to a second line\n"
    )
    _, conflicts = cd.parse_assemble_output(text)
    assert "wrapped to a second line" in conflicts[0].winner_quote


def test_parse_ordinal_parsed_as_int_when_present():
    text = (
        "body\n<!-- ASSEMBLE_CONFLICTS -->\n"
        "- slot: instructions\n"
        "  winner_ordinal: 30\n"
        "  loser_ordinal: 10\n"
    )
    _, conflicts = cd.parse_assemble_output(text)
    assert conflicts[0].winner_ordinal == 30
    assert conflicts[0].loser_ordinal == 10


def test_parse_unparseable_ordinal_becomes_none():
    text = (
        "body\n<!-- ASSEMBLE_CONFLICTS -->\n"
        "- slot: instructions\n"
        "  winner_ordinal: not-a-number\n"
    )
    _, conflicts = cd.parse_assemble_output(text)
    assert conflicts[0].winner_ordinal is None


# ---------------------------------------------------------------------------
# emit_conflict_report — §4.6 canonical format
# ---------------------------------------------------------------------------

_DETERMINISTIC_TS = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _full_conflict(**overrides):
    base = dict(
        slot="instructions",
        winner_layer="L4",
        loser_layer="L2",
        winner_path=".squidsquad/project/worker.md",
        loser_path="references/roles/worker/instructions.md",
        winner_quote="verifier handles all verification",
        loser_quote="verify pending-test items each cycle",
        why="L4 transfers verification responsibility to verifier role",
        resolution="Assembled body says verifier owns verification",
        winner_ordinal=30,
        loser_ordinal=10,
    )
    base.update(overrides)
    return Conflict(**base)


def test_emit_zero_conflicts_still_writes_report_header():
    """Spec: 'still emit the file with Total conflicts resolved: 0 and no CONFLICT sections'."""
    report = cd.emit_conflict_report(
        [], role_class="worker", model_id="gpt-5.2",
        commit_sha="abc123", generated_at=_DETERMINISTIC_TS,
    )
    assert "Total conflicts resolved: 0" in report
    assert "CONFLICT-" not in report
    assert "worker" in report
    assert "gpt-5.2" in report
    assert "abc123" in report


def test_emit_one_conflict_matches_spec_field_order():
    """§4.6 ordering: title -> L<loser> source -> L<winner> source -> Why -> Resolution."""
    report = cd.emit_conflict_report(
        [_full_conflict()], role_class="worker",
        generated_at=_DETERMINISTIC_TS,
    )
    # Title line.
    assert "## CONFLICT-001 — slot: instructions — precedence: L4 > L2" in report
    # Loser source appears before winner source.
    loser_idx = report.index("**L2 source**")
    winner_idx = report.index("**L4 source**")
    assert loser_idx < winner_idx
    why_idx = report.index("**Why this is a conflict**")
    resolution_idx = report.index("**Resolution in assembled output**")
    assert winner_idx < why_idx < resolution_idx


def test_emit_uses_iso8601_timestamp():
    report = cd.emit_conflict_report(
        [], role_class="worker", generated_at=_DETERMINISTIC_TS,
    )
    assert "Generated: 2026-06-01T12:00:00+00:00" in report


def test_emit_quote_truncation_at_200_chars():
    long_quote = "x" * 250
    report = cd.emit_conflict_report(
        [_full_conflict(winner_quote=long_quote)],
        role_class="worker", generated_at=_DETERMINISTIC_TS,
    )
    # The quote in the report is truncated to MAX_QUOTE_CHARS with "..." appended.
    assert "..." in report
    assert "x" * 250 not in report


def test_emit_short_quote_not_truncated():
    report = cd.emit_conflict_report(
        [_full_conflict(winner_quote="short")],
        role_class="worker", generated_at=_DETERMINISTIC_TS,
    )
    assert "> short" in report


def test_emit_ordinal_question_mark_when_missing():
    report = cd.emit_conflict_report(
        [_full_conflict(winner_ordinal=None, loser_ordinal=None)],
        role_class="worker", generated_at=_DETERMINISTIC_TS,
    )
    assert "(ordinal ?)" in report


def test_emit_ordinal_number_when_present():
    report = cd.emit_conflict_report(
        [_full_conflict(winner_ordinal=30, loser_ordinal=10)],
        role_class="worker", generated_at=_DETERMINISTIC_TS,
    )
    assert "(ordinal 10)" in report
    assert "(ordinal 30" in report


def test_emit_winner_op_suffix_when_present():
    """When the winner came in via an L4 op, the report includes it for audit."""
    report = cd.emit_conflict_report(
        [_full_conflict(winner_op="replace step:cycle/work")],
        role_class="worker", generated_at=_DETERMINISTIC_TS,
    )
    assert "op: replace step:cycle/work" in report


def test_emit_numbers_conflicts_with_three_digit_zero_padding():
    """CONFLICT-001 / CONFLICT-002 / ... up to CONFLICT-999 in this scheme."""
    report = cd.emit_conflict_report(
        [_full_conflict(), _full_conflict(slot="identity")],
        role_class="worker", generated_at=_DETERMINISTIC_TS,
    )
    assert "CONFLICT-001" in report
    assert "CONFLICT-002" in report


def test_emit_default_model_id_and_commit_sha_when_omitted():
    """The emitter should not crash when caller doesn't know the model/SHA yet."""
    report = cd.emit_conflict_report(
        [], role_class="worker", generated_at=_DETERMINISTIC_TS,
    )
    assert "Assemble model: <unknown>" in report
    assert "Compose run: <unknown>" in report


# ---------------------------------------------------------------------------
# Round trip: parse output -> emit report
# ---------------------------------------------------------------------------

def test_round_trip_parse_then_emit_produces_valid_report():
    llm_output = (
        "rewritten body\n\n"
        "<!-- ASSEMBLE_CONFLICTS -->\n\n"
        "- slot: instructions\n"
        "  winner_layer: L4\n"
        "  winner_path: .squidsquad/project/worker.md\n"
        "  winner_quote: verifier owns verification\n"
        "  loser_layer: L2\n"
        "  loser_path: references/roles/worker/instructions.md\n"
        "  loser_quote: verify pending-test items\n"
        "  why: L4 transfers verification responsibility\n"
        "  resolution: Assembled body aligns with L4\n"
    )
    body, conflicts = cd.parse_assemble_output(llm_output)
    report = cd.emit_conflict_report(
        conflicts, role_class="worker",
        generated_at=_DETERMINISTIC_TS,
    )
    assert body == "rewritten body\n"
    assert "Total conflicts resolved: 1" in report
    assert "verifier owns verification" in report
    assert "verify pending-test items" in report


# ---------------------------------------------------------------------------
# Template-side: assemble.md.j2 instructs the LLM to emit the delimiter
# ---------------------------------------------------------------------------

def test_assemble_template_includes_conflicts_delimiter_directive():
    repo_root = Path(__file__).resolve().parent.parent
    template = (repo_root / "references" / "prompts" / "assemble.md.j2").read_text(encoding="utf-8")
    assert cd.CONFLICTS_DELIMITER in template
    assert "(none)" in template  # zero-conflicts placeholder mandate
    # The template must enumerate the field names the parser expects.
    for field in ("winner_layer", "loser_layer", "winner_quote",
                  "loser_quote", "why", "resolution"):
        assert field in template, f"template missing field directive: {field}"
