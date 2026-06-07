"""Tests for `_apply_role_conditionals` in compose.py — the role-scoped
conditional content stripping that lets L1 source carry role-specific
content without leaking it to other roles' composed CLAUDE.md (#11144).
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402


def test_block_for_matching_role_is_kept_without_markers():
    """When the target role matches the `if role:<name>` marker, the block
    body survives in the output with the marker lines stripped.
    """
    content = (
        "intro line\n"
        "<!-- if role:dm -->\n"
        "DM-only line\n"
        "<!-- endif -->\n"
        "tail line\n"
    )
    out = compose._apply_role_conditionals(content, "dm")
    assert "<!-- if role:dm -->" not in out
    assert "<!-- endif -->" not in out
    assert "DM-only line\n" in out
    assert "intro line" in out
    assert "tail line" in out


def test_block_for_non_matching_role_is_removed_entirely():
    """When the target role doesn't match, the entire block (markers +
    body) is removed and no trace remains.
    """
    content = (
        "intro line\n"
        "<!-- if role:dm -->\n"
        "DM-only line\n"
        "<!-- endif -->\n"
        "tail line\n"
    )
    out = compose._apply_role_conditionals(content, "pm")
    assert "<!-- if role:dm -->" not in out
    assert "<!-- endif -->" not in out
    assert "DM-only line" not in out
    assert "intro line" in out
    assert "tail line" in out


def test_multiple_blocks_each_evaluated_independently():
    """Two conditional blocks targeting different roles: only the matching
    one survives.
    """
    content = (
        "<!-- if role:pm -->\n"
        "PM-only line\n"
        "<!-- endif -->\n"
        "<!-- if role:dm -->\n"
        "DM-only line\n"
        "<!-- endif -->\n"
    )
    out_pm = compose._apply_role_conditionals(content, "pm")
    assert "PM-only line" in out_pm
    assert "DM-only line" not in out_pm

    out_dm = compose._apply_role_conditionals(content, "dm")
    assert "PM-only line" not in out_dm
    assert "DM-only line" in out_dm


def test_multiline_block_body_preserved_when_role_matches():
    """Block body containing multiple lines (including blank lines) survives
    intact when the role matches.
    """
    content = (
        "<!-- if role:dm -->\n"
        "First DM line\n"
        "\n"
        "Second DM line\n"
        "<!-- endif -->\n"
    )
    out = compose._apply_role_conditionals(content, "dm")
    assert "First DM line\n" in out
    assert "Second DM line\n" in out


def test_content_without_conditionals_is_unchanged():
    """A document with no conditional markers passes through untouched."""
    content = "no conditionals\njust regular content\n"
    assert compose._apply_role_conditionals(content, "dm") == content


def test_non_matching_role_block_leaves_no_blank_line_gap():
    """When a block is removed, the surrounding lines should not develop
    a multi-blank-line gap — the markdown around the block should read
    naturally after stripping.
    """
    content = (
        "Line A\n"
        "\n"
        "<!-- if role:dm -->\n"
        "DM content\n"
        "<!-- endif -->\n"
        "\n"
        "Line B\n"
    )
    out = compose._apply_role_conditionals(content, "pm")
    # The result should not have three or more consecutive newlines.
    assert "\n\n\n" not in out
    assert "Line A" in out
    assert "Line B" in out


def test_role_conditional_runs_inside_substitute_placeholders():
    """`_substitute_placeholders` calls `_apply_role_conditionals` first so
    DM-only blocks vanish for non-DM compose targets even when they go
    through the full substitution pipeline.
    """
    content = (
        "header\n"
        "<!-- if role:dm -->\n"
        "DM-only [ROLE] line\n"
        "<!-- endif -->\n"
        "footer\n"
    )
    pm_out = compose._substitute_placeholders(content, "pm", "pm")
    assert "DM-only" not in pm_out
    # And [ROLE] in surviving content for PM was substituted.
    assert "header" in pm_out
    assert "footer" in pm_out

    dm_out = compose._substitute_placeholders(content, "dm", "dm")
    assert "DM-only dm line" in dm_out
