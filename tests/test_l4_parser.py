"""Tests for references/scripts/l4_parser.py (#10488, PRD-A Story A2b)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_parser as l4  # noqa: E402


# ---------------------------------------------------------------------------
# Empty / missing file
# ---------------------------------------------------------------------------

def test_missing_file_returns_empty_document(tmp_path):
    doc = l4.parse_l4_file(tmp_path / "does_not_exist.md")
    assert isinstance(doc, l4.L4Document)
    assert doc.slots == {}


def test_empty_file_returns_empty_document(tmp_path):
    f = tmp_path / "worker.md"
    f.write_text("", encoding="utf-8")
    doc = l4.parse_l4_file(f)
    assert doc.slots == {}


# ---------------------------------------------------------------------------
# Six legal slot H2 sections
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "h2,slot_key",
    [
        ("## Identity", "identity"),
        ("## Responsibility", "responsibility"),
        ("## Soul", "soul"),
        ("## Instructions", "instructions"),
        ("## Project Context", "project-context"),
        ("## Vault", "vault"),
    ],
)
def test_each_legal_slot_recognized(h2, slot_key):
    doc = l4.parse_l4_text(f"{h2}\n\n### append\n\nbody\n")
    assert slot_key in doc.slots
    assert len(doc.slots[slot_key]) == 1


def test_unknown_slot_rejected_with_diagnostic():
    with pytest.raises(l4.L4ParseError) as exc:
        l4.parse_l4_text("## Bogus Slot\n\n### append\n\nbody\n")
    msg = str(exc.value)
    assert "unknown L4 slot" in msg
    assert "Bogus Slot" in msg


def test_slot_h2_with_closing_hashes_tolerated():
    # Markdown allows `## Identity ##`; the parser should still pick up the slot.
    doc = l4.parse_l4_text("## Identity ##\n\n### append\n\nbody\n")
    assert "identity" in doc.slots


# ---------------------------------------------------------------------------
# All five legal H3 op shapes
# ---------------------------------------------------------------------------

def test_append_no_target():
    doc = l4.parse_l4_text("## Identity\n\n### append\n\nproject prose\n")
    op = doc.slots["identity"][0]
    assert op.op_type == "append"
    assert op.target_step_id is None
    assert op.body_text == "project prose"


def test_whole_slot_replace_no_target():
    doc = l4.parse_l4_text("## Responsibility\n\n### replace\n\nnew body\n")
    op = doc.slots["responsibility"][0]
    assert op.op_type == "replace"
    assert op.target_step_id is None


def test_replace_step_targeted():
    doc = l4.parse_l4_text(
        "## Instructions\n\n### replace step:cycle/triage\n\nnew body\n"
    )
    op = doc.slots["instructions"][0]
    assert op.op_type == "replace"
    assert op.target_step_id == "triage"


def test_insert_before_step_targeted():
    doc = l4.parse_l4_text(
        "## Instructions\n\n### insert-before step:cycle/file-bug\n\nnew step\n"
    )
    op = doc.slots["instructions"][0]
    assert op.op_type == "insert-before"
    assert op.target_step_id == "file-bug"


def test_insert_after_step_targeted_with_hyphenated_id():
    doc = l4.parse_l4_text(
        "## Instructions\n\n### insert-after step:cycle/pipeline-sentinel\n\nbody\n"
    )
    op = doc.slots["instructions"][0]
    assert op.op_type == "insert-after"
    assert op.target_step_id == "pipeline-sentinel"


# ---------------------------------------------------------------------------
# Multiple ops in one slot (file order)
# ---------------------------------------------------------------------------

def test_multiple_ops_in_one_slot_preserved_in_file_order():
    text = (
        "## Instructions\n\n"
        "### append\n\nfirst block\n\n"
        "### insert-before step:cycle/X\n\nsecond block\n\n"
        "### append\n\nthird block\n"
    )
    ops = l4.parse_l4_text(text).slots["instructions"]
    assert [o.op_type for o in ops] == ["append", "insert-before", "append"]
    assert [o.target_step_id for o in ops] == [None, "X", None]
    assert ops[0].body_text == "first block"
    assert ops[1].body_text == "second block"
    assert ops[2].body_text == "third block"


def test_ops_across_multiple_slots():
    text = (
        "## Identity\n\n### append\n\nidentity prose\n\n"
        "## Instructions\n\n### append\n\ninstructions prose\n"
    )
    doc = l4.parse_l4_text(text)
    assert set(doc.slots) == {"identity", "instructions"}
    assert doc.slots["identity"][0].body_text == "identity prose"
    assert doc.slots["instructions"][0].body_text == "instructions prose"


# ---------------------------------------------------------------------------
# Malformed H3 ops — rejected with diagnostic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_h3",
    [
        "### Boot & Queue",  # arbitrary prose H3
        "### replace step:cycle/",  # missing step id
        "### replace step:wrong/foo",  # wrong step prefix
        "### insert-around step:cycle/foo",  # unknown op
        "### appendix",  # near-miss op name
        "### insert-before",  # missing target on a targeted op
        "### replace step:cycle/foo extra",  # trailing garbage
    ],
)
def test_malformed_h3_rejected(bad_h3):
    text = f"## Instructions\n\n{bad_h3}\n\nbody\n"
    with pytest.raises(l4.L4ParseError) as exc:
        l4.parse_l4_text(text)
    assert "malformed H3 op" in str(exc.value)


def test_h3_outside_any_slot_rejected():
    with pytest.raises(l4.L4ParseError) as exc:
        l4.parse_l4_text("### append\n\nbody\n")
    assert "outside any slot" in str(exc.value)


# ---------------------------------------------------------------------------
# HTML-comment metadata trailer
# ---------------------------------------------------------------------------

def test_metadata_trailer_extracted_and_stripped():
    text = (
        "## Instructions\n\n"
        "### append\n\n"
        "body line one\n"
        "body line two\n\n"
        "<!--\n"
        "authored-by: skill-lead\n"
        "authored-at: 2026-05-31\n"
        "source-conversation: cycle 1443\n"
        "-->\n"
    )
    op = l4.parse_l4_text(text).slots["instructions"][0]
    assert op.metadata == {
        "authored-by": "skill-lead",
        "authored-at": "2026-05-31",
        "source-conversation": "cycle 1443",
    }
    # Trailer must be stripped from the body.
    assert "<!--" not in op.body_text
    assert "authored-by" not in op.body_text
    assert op.body_text.endswith("body line two")


def test_metadata_optional_op_with_no_trailer():
    text = "## Identity\n\n### append\n\nbody\n"
    op = l4.parse_l4_text(text).slots["identity"][0]
    assert op.metadata == {}
    assert op.body_text == "body"


def test_metadata_only_terminal_comment_counts_as_trailer():
    # An HTML comment in the middle of the body is NOT a trailer — only
    # the one at the end. Locks the regex's "end of body" anchor.
    text = (
        "## Instructions\n\n"
        "### append\n\n"
        "<!-- not metadata -->\n\n"
        "real body\n\n"
        "<!--\nauthored-by: x\n-->\n"
    )
    op = l4.parse_l4_text(text).slots["instructions"][0]
    assert op.metadata == {"authored-by": "x"}
    assert "<!-- not metadata -->" in op.body_text


def test_metadata_multiline_midbody_comment_not_treated_as_trailer():
    # DS finding 1: with re.MULTILINE on the trailer regex, a multi-line
    # `<!--\n...\n-->` block in the MIDDLE of the body would be wrongly
    # picked up as the trailer because `$` matched any end-of-line. With
    # \Z (end-of-string), only the terminal comment counts.
    text = (
        "## Instructions\n\n"
        "### append\n\n"
        "real intro text\n\n"
        "<!--\n"
        "mid-body multi-line comment\n"
        "-->\n\n"
        "real outro text\n\n"
        "<!--\n"
        "authored-by: skill-lead\n"
        "-->\n"
    )
    op = l4.parse_l4_text(text).slots["instructions"][0]
    # Only the terminal comment is metadata.
    assert op.metadata == {"authored-by": "skill-lead"}
    # The mid-body comment stays as part of body_text.
    assert "mid-body multi-line comment" in op.body_text
    assert "real intro text" in op.body_text
    assert "real outro text" in op.body_text


def test_metadata_trailer_is_the_entire_body():
    # DS finding 2: an H3 op whose ONLY content is the metadata trailer
    # (no preceding prose) must still parse the trailer correctly. With
    # the .strip('\n') of the old code, the leading \n that the regex
    # required was stripped and the trailer was silently kept as body.
    text = (
        "## Identity\n\n"
        "### append\n\n"
        "<!--\n"
        "authored-by: skill-lead\n"
        "authored-at: 2026-05-31\n"
        "-->\n"
    )
    op = l4.parse_l4_text(text).slots["identity"][0]
    assert op.metadata == {
        "authored-by": "skill-lead",
        "authored-at": "2026-05-31",
    }
    assert op.body_text == ""


def test_metadata_unparseable_lines_ignored_per_trd_7_3():
    # TRD §7.3: "Compose does not require or validate the metadata; only
    # the section structure (H2 slot, H3 op + target) is load-bearing."
    text = (
        "## Identity\n\n### append\n\nbody\n\n"
        "<!--\n"
        "authored-by: skill-lead\n"
        "this line has no colon\n"
        "another: ok\n"
        "-->\n"
    )
    op = l4.parse_l4_text(text).slots["identity"][0]
    assert op.metadata == {"authored-by": "skill-lead", "another": "ok"}


# ---------------------------------------------------------------------------
# parse_l4_file: real I/O path
# ---------------------------------------------------------------------------

def test_parse_l4_file_round_trip(tmp_path):
    text = (
        "## Identity\n\n### append\n\nidentity body\n\n"
        "## Instructions\n\n"
        "### append\n\nappend body\n\n"
        "### replace step:cycle/foo\n\nreplace body\n"
    )
    f = tmp_path / "worker.md"
    f.write_text(text, encoding="utf-8")
    doc = l4.parse_l4_file(f)
    assert set(doc.slots) == {"identity", "instructions"}
    assert len(doc.slots["instructions"]) == 2
    assert doc.slots["instructions"][1].target_step_id == "foo"


# ---------------------------------------------------------------------------
# Coexistence: parser does not modify v1 read sites
# ---------------------------------------------------------------------------

def test_v1_compose_untouched():
    # A2b is pure additive. compose.py must not import l4_parser yet.
    import compose
    source = compose.__file__
    with open(source, encoding="utf-8") as f:
        text = f.read()
    assert "l4_parser" not in text, (
        "A2b is parse-only; A2 will wire l4_parser into compose.py later."
    )


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def test_l4op_metadata_default_factory_is_independent():
    # Defensive against the dataclass mutable-default trap.
    a = l4.L4Op(op_type="append", target_step_id=None, body_text="x")
    b = l4.L4Op(op_type="append", target_step_id=None, body_text="y")
    a.metadata["x"] = 1
    assert b.metadata == {}


def test_l4document_empty_factory_returns_isolated_slots():
    a = l4.L4Document.empty()
    b = l4.L4Document.empty()
    a.slots["x"] = []
    assert b.slots == {}
