"""Tests for the test-only ``_v2_test_helpers.expand_v2_includes`` shim.

The helper is itself test infrastructure (retires alongside v1 in
E6 #10685 Phase 3d), but the tests built on top of it depend on it
behaving correctly — and the cycle-1535 lesson ("skip DS review for
pure-deletion / pure-fixture commits") doesn't apply to a function
with real logic. A few targeted tests keep the helper honest.
"""

from pathlib import Path

import pytest

from _v2_test_helpers import expand_v2_includes


def test_expand_inlines_existing_include(tmp_path):
    sub_skills = tmp_path / "references" / "sub-skills" / "common"
    sub_skills.mkdir(parents=True)
    (sub_skills / "foo.md").write_text(
        "This is the foo fragment body.\n", encoding="utf-8"
    )
    text = (
        "## Some Section\n"
        "{{include: common/foo}}\n"
        "## Next Section\n"
    )
    out = expand_v2_includes(
        text, sub_skills_dir=tmp_path / "references" / "sub-skills",
    )
    assert "<!-- sub-skill: foo -->" in out
    assert "This is the foo fragment body." in out
    assert "<!-- /sub-skill: foo -->" in out
    # The original directive line is gone.
    assert "{{include: common/foo}}" not in out


def test_expand_skips_runtime_fragments(tmp_path, monkeypatch):
    """RUNTIME_READ_FRAGMENTS must never be inlined — they belong to
    the lazy-load bootstrap contract (#9588)."""
    import compose
    sub_skills = tmp_path / "references" / "sub-skills"
    (sub_skills / "roles" / "worker").mkdir(parents=True)
    (sub_skills / "roles" / "worker" / "ralph-loop-overview.md").write_text(
        "lazy-load body that must NOT be inlined", encoding="utf-8",
    )
    monkeypatch.setattr(
        compose, "RUNTIME_READ_FRAGMENTS",
        frozenset({"roles/worker/ralph-loop-overview"}),
    )
    text = (
        "before\n"
        "{{include: roles/worker/ralph-loop-overview}}\n"
        "after\n"
    )
    out = expand_v2_includes(text, sub_skills_dir=sub_skills)
    assert "lazy-load body" not in out
    assert "<!-- sub-skill: ralph-loop-overview -->" not in out
    # Surrounding context preserved.
    assert "before" in out and "after" in out


def test_expand_emits_error_for_missing_file(tmp_path):
    sub_skills = tmp_path / "references" / "sub-skills"
    sub_skills.mkdir(parents=True)
    text = "{{include: common/does-not-exist}}\n"
    out = expand_v2_includes(text, sub_skills_dir=sub_skills)
    assert "<!-- ERROR: Missing include: common/does-not-exist -->" in out


def test_expand_strips_outer_markers(tmp_path):
    """Source files carry their own ``<!-- sub-skill: name -->`` outer
    markers; the helper strips them so the rewrap doesn't double them."""
    sub_skills = tmp_path / "references" / "sub-skills" / "common"
    sub_skills.mkdir(parents=True)
    (sub_skills / "bar.md").write_text(
        "<!-- sub-skill: bar -->\n"
        "Inner body of bar.\n"
        "<!-- /sub-skill: bar -->\n",
        encoding="utf-8",
    )
    text = "{{include: common/bar}}\n"
    out = expand_v2_includes(
        text, sub_skills_dir=tmp_path / "references" / "sub-skills",
    )
    # Exactly one open + one close marker, not two.
    assert out.count("<!-- sub-skill: bar -->") == 1
    assert out.count("<!-- /sub-skill: bar -->") == 1
    assert "Inner body of bar." in out


def test_expand_strips_yaml_frontmatter(tmp_path):
    sub_skills = tmp_path / "references" / "sub-skills" / "common"
    sub_skills.mkdir(parents=True)
    (sub_skills / "baz.md").write_text(
        "---\nslot: cycle\nordinal: 3\n---\n\nBody after frontmatter.\n",
        encoding="utf-8",
    )
    text = "{{include: common/baz}}\n"
    out = expand_v2_includes(
        text, sub_skills_dir=tmp_path / "references" / "sub-skills",
    )
    assert "slot: cycle" not in out
    assert "Body after frontmatter." in out


def test_expand_passes_non_include_lines_through(tmp_path):
    sub_skills = tmp_path / "references" / "sub-skills"
    sub_skills.mkdir(parents=True)
    text = (
        "# H1\n"
        "Plain prose line.\n"
        "- bullet item\n"
        "{{capability: foo}}\n"  # NOT an include — should pass through
        "{{runtime: bar}}\n"     # NOT an include — should pass through
    )
    out = expand_v2_includes(text, sub_skills_dir=sub_skills)
    assert out == text.rstrip("\n")  # splitlines + join loses trailing \n
