"""Unit tests for compose._strip_yaml_frontmatter (#10394 A2.6 prereq).

The strip is a precondition for the A2.6 migration: when L1-L3 source
files carry YAML frontmatter, v1's ``_resolve_includes`` would otherwise
carry the block through to its composed output and break the §9a
byte-equivalent contract. These tests pin the helper's behavior at the
boundary so future edits don't accidentally widen or narrow what it
matches.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402


def test_strips_leading_frontmatter_block():
    text = "---\nslot: identity\nordinal: 10\n---\n\nBody content here.\n"
    assert compose._strip_yaml_frontmatter(text) == "Body content here.\n"


def test_strips_frontmatter_with_no_blank_line_after():
    text = "---\nslot: instructions\nordinal: 20\n---\nBody immediately after.\n"
    assert compose._strip_yaml_frontmatter(text) == "Body immediately after.\n"


def test_strips_frontmatter_with_extra_fields():
    text = (
        "---\n"
        "slot: instructions\n"
        "ordinal: 30\n"
        "roles: [worker, pm]\n"
        "step-ids: [step:cycle/boot]\n"
        "---\n\n"
        "### step:cycle/boot\nBody.\n"
    )
    assert compose._strip_yaml_frontmatter(text) == (
        "### step:cycle/boot\nBody.\n"
    )


def test_no_frontmatter_is_passthrough():
    text = "Just body content, no frontmatter at all.\n"
    assert compose._strip_yaml_frontmatter(text) == text


def test_mid_file_horizontal_rule_not_stripped():
    """A `---` horizontal rule in the middle of the document is NOT a frontmatter delimiter."""
    text = "Body line one.\n\n---\n\nBody line two after a rule.\n"
    assert compose._strip_yaml_frontmatter(text) == text


def test_empty_input_is_passthrough():
    assert compose._strip_yaml_frontmatter("") == ""


def test_only_opening_delimiter_is_passthrough():
    """An unbalanced opening `---\\n` is treated as body content (not a frontmatter)."""
    text = "---\nslot: identity\nNo closing delimiter here.\n"
    assert compose._strip_yaml_frontmatter(text) == text


def test_strips_frontmatter_with_horizontal_whitespace_on_delimiters():
    """Per Jekyll convention, `--- ` (with trailing whitespace) on the delimiter is legal."""
    text = "---  \nslot: identity\nordinal: 10\n---\t\n\nBody.\n"
    assert compose._strip_yaml_frontmatter(text) == "Body.\n"


def test_strips_only_first_frontmatter_block():
    """A second `---` block later in the file is content, not a re-strip."""
    text = (
        "---\nslot: instructions\nordinal: 10\n---\n\n"
        "Body content.\n\n"
        "---\nthis is content prose with --- markers\n---\n"
    )
    out = compose._strip_yaml_frontmatter(text)
    assert out.startswith("Body content.")
    assert "this is content prose" in out


def test_frontmatter_at_very_start_of_file():
    """Frontmatter MUST be at position 0 — leading whitespace breaks it."""
    text = "\n---\nslot: identity\n---\n\nBody.\n"  # leading newline
    # Conservative: text with a leading newline is NOT frontmatter per the regex \A anchor.
    assert compose._strip_yaml_frontmatter(text) == text
