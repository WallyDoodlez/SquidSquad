"""Tests for references/scripts/source_frontmatter.py (#10487, PRD-A Story A2a)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))
# DS finding 3: don't rely on pytest's CWD putting repo root on sys.path
# for the v1-untouched compose import below.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import source_frontmatter as sf  # noqa: E402


# ---------------------------------------------------------------------------
# Valid frontmatter
# ---------------------------------------------------------------------------

def test_valid_frontmatter_returns_slot_and_ordinal():
    text = (
        "---\n"
        "slot: instructions\n"
        "ordinal: 20\n"
        "---\n\n"
        "# body content\n"
    )
    fm = sf.parse_source_frontmatter_text(text)
    assert fm is not None
    assert fm.slot == "instructions"
    assert fm.ordinal == 20
    assert fm.extras == {}


def test_extras_preserved_as_is():
    text = (
        "---\n"
        "slot: instructions\n"
        "ordinal: 20\n"
        "roles: [worker]\n"
        "step-ids: [step:cycle/triage, step:cycle/implement]\n"
        "custom-field: anything\n"
        "---\n\n"
        "body\n"
    )
    fm = sf.parse_source_frontmatter_text(text)
    assert fm.extras == {
        "roles": ["worker"],
        "step-ids": ["step:cycle/triage", "step:cycle/implement"],
        "custom-field": "anything",
    }


def test_ordinal_zero_accepted():
    text = "---\nslot: identity\nordinal: 0\n---\n"
    fm = sf.parse_source_frontmatter_text(text)
    assert fm.ordinal == 0


@pytest.mark.parametrize(
    "slot",
    ["identity", "responsibility", "soul", "instructions", "project-context", "vault"],
)
def test_each_legal_slot_accepted(slot):
    text = f"---\nslot: {slot}\nordinal: 10\n---\n"
    fm = sf.parse_source_frontmatter_text(text)
    assert fm.slot == slot


# ---------------------------------------------------------------------------
# Missing frontmatter → returns None
# ---------------------------------------------------------------------------

def test_no_frontmatter_returns_none():
    text = "# Just a heading\n\nsome body\n"
    assert sf.parse_source_frontmatter_text(text) is None


def test_frontmatter_must_be_at_very_top():
    # Leading whitespace / blank lines before the opening --- mean the
    # frontmatter is not at the top per CommonMark / Jekyll convention.
    text = "\n\n---\nslot: identity\nordinal: 10\n---\n"
    assert sf.parse_source_frontmatter_text(text) is None


def test_unterminated_frontmatter_returns_none():
    # No closing --- → not valid frontmatter at all.
    text = "---\nslot: identity\nordinal: 10\n\n# body\n"
    assert sf.parse_source_frontmatter_text(text) is None


def test_empty_file_returns_none():
    assert sf.parse_source_frontmatter_text("") is None


def test_empty_frontmatter_block_raises():
    # DS finding 1: `---\n---\n` is structurally a frontmatter block,
    # just empty. The previous regex returned None silently here even
    # though `---\n\n---\n` (with one blank line) raised. Lock that both
    # shapes now reject consistently.
    text = "---\n---\n\nbody\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "empty" in str(exc.value).lower()


def test_closing_delimiter_trailing_whitespace_tolerated():
    # DS finding 4: closing `---` followed by spaces/tabs is acceptable
    # per Jekyll convention. The regex tolerates `[ \t]*`.
    text = "---\nslot: identity\nordinal: 0\n---   \t\n\nbody\n"
    fm = sf.parse_source_frontmatter_text(text)
    assert fm is not None
    assert fm.slot == "identity"


def test_opening_delimiter_horizontal_whitespace_tolerated():
    text = "---  \nslot: identity\nordinal: 0\n---\n\nbody\n"
    fm = sf.parse_source_frontmatter_text(text)
    assert fm is not None


def test_yaml_anchor_alias_in_extras():
    # DS finding 5: yaml.safe_load supports anchors. Extras must
    # round-trip through the anchor resolution correctly.
    text = (
        "---\n"
        "slot: identity\n"
        "ordinal: 0\n"
        "x: &anchor value\n"
        "y: *anchor\n"
        "---\n"
    )
    fm = sf.parse_source_frontmatter_text(text)
    assert fm.extras == {"x": "value", "y": "value"}


def test_yaml_undefined_alias_raises_clean():
    # An alias to a non-existent anchor is malformed YAML — must surface
    # as FrontmatterError, not a bare yaml.YAMLError leak.
    text = "---\nslot: identity\nordinal: 0\nx: *missing\n---\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "malformed YAML" in str(exc.value)


# ---------------------------------------------------------------------------
# Malformed YAML
# ---------------------------------------------------------------------------

def test_malformed_yaml_raises():
    text = "---\nslot: identity\nordinal: 20\n  bad-indent: x\n---\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "malformed YAML" in str(exc.value)


def test_top_level_must_be_mapping():
    # A YAML list at top level is well-formed YAML but invalid frontmatter.
    text = "---\n- one\n- two\n---\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "YAML mapping" in str(exc.value)


# ---------------------------------------------------------------------------
# Invalid slot value
# ---------------------------------------------------------------------------

def test_missing_slot_field_raises():
    text = "---\nordinal: 10\n---\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "missing required `slot`" in str(exc.value)


def test_unknown_slot_value_raises():
    text = "---\nslot: bogus\nordinal: 10\n---\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "invalid `slot`" in str(exc.value)
    assert "bogus" in str(exc.value)


def test_non_string_slot_raises():
    text = "---\nslot: 42\nordinal: 10\n---\n"
    with pytest.raises(sf.FrontmatterError):
        sf.parse_source_frontmatter_text(text)


# ---------------------------------------------------------------------------
# Invalid ordinal value
# ---------------------------------------------------------------------------

def test_missing_ordinal_field_raises():
    text = "---\nslot: identity\n---\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "missing required `ordinal`" in str(exc.value)


def test_non_integer_ordinal_raises():
    text = "---\nslot: identity\nordinal: ten\n---\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "non-negative integer" in str(exc.value)


def test_float_ordinal_raises():
    text = "---\nslot: identity\nordinal: 10.5\n---\n"
    with pytest.raises(sf.FrontmatterError):
        sf.parse_source_frontmatter_text(text)


def test_negative_ordinal_raises():
    text = "---\nslot: identity\nordinal: -1\n---\n"
    with pytest.raises(sf.FrontmatterError) as exc:
        sf.parse_source_frontmatter_text(text)
    assert "non-negative" in str(exc.value)


def test_boolean_ordinal_rejected():
    # YAML `true` is a bool, not an int — even though Python's
    # `isinstance(True, int)` is True. A scalar of `true` is not an
    # ordinal value and would silently sort as 1.
    text = "---\nslot: identity\nordinal: true\n---\n"
    with pytest.raises(sf.FrontmatterError):
        sf.parse_source_frontmatter_text(text)


# ---------------------------------------------------------------------------
# File I/O round-trip
# ---------------------------------------------------------------------------

def test_parse_source_frontmatter_reads_file(tmp_path):
    f = tmp_path / "instructions.md"
    f.write_text(
        "---\nslot: instructions\nordinal: 20\nroles: [worker]\n---\n\nbody\n",
        encoding="utf-8",
    )
    fm = sf.parse_source_frontmatter(f)
    assert fm.slot == "instructions"
    assert fm.ordinal == 20
    assert fm.extras == {"roles": ["worker"]}


def test_parse_source_frontmatter_propagates_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        sf.parse_source_frontmatter(tmp_path / "does_not_exist.md")


# ---------------------------------------------------------------------------
# Real source files in this repo
# ---------------------------------------------------------------------------

def test_existing_dm_identity_parses_correctly():
    # references/roles/dm/identity.md was the first file to carry the
    # v2 frontmatter shape. Lock that the parser handles it.
    repo_root = Path(__file__).resolve().parent.parent
    f = repo_root / "references" / "roles" / "dm" / "identity.md"
    if not f.is_file():
        pytest.skip(f"{f} not present in this branch")
    fm = sf.parse_source_frontmatter(f)
    assert fm is not None
    assert fm.slot == "identity"
    assert isinstance(fm.ordinal, int)
    assert fm.ordinal >= 0


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def test_extras_default_factory_is_independent():
    a = sf.SourceFrontmatter(slot="identity", ordinal=10)
    b = sf.SourceFrontmatter(slot="identity", ordinal=10)
    a.extras["x"] = 1
    assert b.extras == {}
