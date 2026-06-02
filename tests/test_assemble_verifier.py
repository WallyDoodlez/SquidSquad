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


# ---------------------------------------------------------------------------
# B3 (#10442) — length floor
# ---------------------------------------------------------------------------

def test_length_floor_identity_passes():
    body = "abc" * 100
    assert av.check_length_floor(body, body) is True


def test_length_floor_empty_linked_empty_assembled_passes():
    assert av.check_length_floor("", "") is True


def test_length_floor_empty_assembled_with_nonempty_linked_fails():
    """AC: 'empty assembled fails floor' (when linked is non-empty)."""
    assert av.check_length_floor("x" * 100, "") is False


def test_length_floor_at_exactly_0_8x_passes():
    """AC: 'assembled at exactly 0.8x passes' — boundary is inclusive."""
    linked = "x" * 100
    assembled = "y" * 80  # exactly 0.8 * 100
    assert av.check_length_floor(linked, assembled) is True


def test_length_floor_at_0_79x_fails():
    """AC: '0.79x fails' — strictly below floor."""
    linked = "x" * 100
    assembled = "y" * 79
    assert av.check_length_floor(linked, assembled) is False


def test_length_floor_custom_floor_threshold():
    linked = "x" * 100
    assembled = "y" * 50
    assert av.check_length_floor(linked, assembled, floor=0.5) is True
    assert av.check_length_floor(linked, assembled, floor=0.51) is False


def test_length_floor_longer_assembled_passes():
    """A grown assembled (e.g. compose injected content) trivially satisfies the floor."""
    assert av.check_length_floor("short", "much longer body here") is True


# ---------------------------------------------------------------------------
# B3 (#10442) — code-block parity (fenced)
# ---------------------------------------------------------------------------

def _fenced(n, lang=""):
    """Return a body containing ``n`` well-formed fenced blocks."""
    return "\n".join(f"```{lang}\nbody {i}\n```" for i in range(n))


def test_code_block_parity_identity_passes():
    body = _fenced(10)
    assert av.check_code_block_parity(body, body) is True


def test_code_block_parity_no_blocks_either_side_passes():
    assert av.check_code_block_parity("just prose\n", "just prose still\n") is True


def test_code_block_parity_fenced_drop_at_tolerance_passes():
    """10/10 -> 9/10 is exactly 10% drop; at-tolerance boundary passes."""
    linked = _fenced(10)
    assembled = _fenced(9)
    assert av.check_code_block_parity(linked, assembled) is True


def test_code_block_parity_fenced_drop_just_over_tolerance_fails():
    """AC: 'code block count drops by >10% fails' — 10 -> 8 is 20%."""
    linked = _fenced(10)
    assembled = _fenced(8)
    assert av.check_code_block_parity(linked, assembled) is False


def test_code_block_parity_fenced_spike_over_tolerance_fails():
    """Symmetry: a >10% increase also fails."""
    linked = _fenced(10)
    assembled = _fenced(12)
    assert av.check_code_block_parity(linked, assembled) is False


def test_code_block_parity_fenced_with_lang_tag_counted():
    """Language-tagged fences (```python) count like bare fences."""
    linked = _fenced(5, lang="python") + "\n" + _fenced(5)
    assembled = linked
    assert av.check_code_block_parity(linked, assembled) is True


# ---------------------------------------------------------------------------
# B3 (#10442) — code-block parity (inline backticks)
# ---------------------------------------------------------------------------

def _inline(n):
    """Return a body with ``n`` inline single-backtick spans."""
    return " ".join(f"prose `code{i}` more" for i in range(n))


def test_code_block_parity_inline_identity_passes():
    body = _inline(10)
    assert av.check_code_block_parity(body, body) is True


def test_code_block_parity_inline_drop_just_over_tolerance_fails():
    """AC: 'inline backtick count change >10% fails' — 10 -> 8 is 20%."""
    linked = _inline(10)
    assembled = _inline(8)
    assert av.check_code_block_parity(linked, assembled) is False


def test_code_block_parity_inline_spike_just_over_tolerance_fails():
    linked = _inline(10)
    assembled = _inline(12)
    assert av.check_code_block_parity(linked, assembled) is False


def test_code_block_parity_inline_does_not_count_fenced_backticks():
    """Triple-backtick fences must not inflate the inline count."""
    linked = _fenced(3)  # zero inline spans
    assembled = _fenced(3) + "\n" + _inline(1)  # one inline span (10 backticks delta if naive)
    # Inline count goes 0 -> 1; using max(linked,1) denominator, delta=1/1=1.0 > 0.1 → fail.
    assert av.check_code_block_parity(linked, assembled) is False


def test_code_block_parity_mixed_fenced_and_inline_pass():
    body = _fenced(4) + "\n" + _inline(20)
    assert av.check_code_block_parity(body, body) is True


def test_code_block_parity_custom_tolerance():
    linked = _inline(10)
    assembled = _inline(7)
    # 30% drop: fails at default 0.1, passes at 0.3
    assert av.check_code_block_parity(linked, assembled) is False
    assert av.check_code_block_parity(linked, assembled, tolerance=0.3) is True


def test_code_block_parity_either_side_failure_fails_combined():
    """When fenced is OK but inline is off, the combined check still fails."""
    linked = _fenced(5) + "\n" + _inline(10)
    assembled = _fenced(5) + "\n" + _inline(7)  # fenced fine, inline -30%
    assert av.check_code_block_parity(linked, assembled) is False


# ---------------------------------------------------------------------------
# PRD-B #10752 W1 — verify_fenced_block_content + verify_file_paths
# ---------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

_PY_BLOCK = "```python\nprint('hello')\n```"
_BASH_BLOCK = "```bash\ncd /tmp\n```"


class TestVerifyFencedBlockContent:

    def test_identity_passes(self):
        text = f"prose\n\n{_PY_BLOCK}\n\nmore\n\n{_BASH_BLOCK}\n"
        missing, extra = av.verify_fenced_block_content(text, text)
        assert missing == []
        assert extra == []

    def test_swapped_body_fails(self):
        # Same count, same lang tags, but the body content was rewritten.
        # check_code_block_parity passes (counts match); content check
        # catches the swap.
        linked = f"prose\n\n{_PY_BLOCK}\n"
        assembled = "prose\n\n```python\nprint('CHANGED')\n```\n"
        missing, extra = av.verify_fenced_block_content(linked, assembled)
        assert missing == [("python", "print('hello')")]
        assert extra == [("python", "print('CHANGED')")]
        # The parity counter agrees both texts have 1 block — that's
        # the gap this check closes.
        assert av.check_code_block_parity(linked, assembled) is True

    def test_dropped_block_fails(self):
        linked = f"a\n\n{_PY_BLOCK}\n\nb\n\n{_BASH_BLOCK}\n"
        assembled = f"a\n\nb\n\n{_BASH_BLOCK}\n"
        missing, extra = av.verify_fenced_block_content(linked, assembled)
        assert missing == [("python", "print('hello')")]
        assert extra == []

    def test_added_block_fails(self):
        linked = f"a\n\n{_PY_BLOCK}\n"
        assembled = f"a\n\n{_PY_BLOCK}\n\n{_BASH_BLOCK}\n"
        missing, extra = av.verify_fenced_block_content(linked, assembled)
        assert missing == []
        assert extra == [("bash", "cd /tmp")]

    def test_no_blocks_at_all_passes(self):
        missing, extra = av.verify_fenced_block_content(
            "just prose", "rewritten prose")
        assert missing == []
        assert extra == []


class TestVerifyFilePaths:

    def test_identity_passes(self):
        text = (
            "See references/scripts/foo.py for details, and "
            "docs/COMPOSE-ARCHITECTURE.md for the spec.\n"
        )
        missing, extra = av.verify_file_paths(text, text)
        assert missing == []
        assert extra == []

    def test_dropped_path_fails(self):
        # SC3 item 4 failure mode: the LLM rewrote the prose into
        # "see the script" and no longer names the script.
        linked = "Read references/scripts/foo.py for the helper."
        assembled = "Read the helper script for details."
        missing, extra = av.verify_file_paths(linked, assembled)
        assert "references/scripts/foo.py" in missing
        assert extra == []

    def test_substituted_path_fails(self):
        linked = "See references/scripts/foo.py."
        assembled = "See references/scripts/bar.py."
        missing, extra = av.verify_file_paths(linked, assembled)
        assert missing == ["references/scripts/foo.py"]
        assert extra == ["references/scripts/bar.py"]

    def test_bare_filename_does_not_false_positive(self):
        # Bare README, version strings, and slug-only tokens
        # shouldn't be flagged as file paths.
        linked = "See README. Version is 1.2.3. The pipeline-sentinel skill."
        missing, extra = av.verify_file_paths(linked, linked)
        assert missing == []
        assert extra == []

    def test_multiple_paths_multiset(self):
        linked = "Files: a/b.py, c/d.md, and a/b.py again."
        assembled = "Files: a/b.py and c/d.md."
        missing, extra = av.verify_file_paths(linked, assembled)
        # a/b.py appears twice in linked, once in assembled.
        assert missing == ["a/b.py"]
        assert extra == []


class TestVerifyPreservationFullCoverage:
    """The top-level ``verify_preservation`` rolls fenced-content +
    file-paths into ``ok``. #10752 W1 acceptance: a failure in either
    new dimension flips ``ok`` to False."""

    def test_ok_when_all_four_dimensions_intact(self):
        text = (
            "→ run sub-skill: pipeline-sentinel\n"
            "step:cycle/boot\n"
            f"{_PY_BLOCK}\n"
            "See references/scripts/foo.py.\n"
        )
        result = av.verify_preservation(text, text)
        assert result.ok is True

    def test_dropped_fenced_block_flips_ok(self):
        linked = f"→ run sub-skill: x\n{_PY_BLOCK}\n"
        assembled = "→ run sub-skill: x\n"
        result = av.verify_preservation(linked, assembled)
        assert result.ok is False
        assert result.missing_fenced_blocks == [("python", "print('hello')")]

    def test_dropped_file_path_flips_ok(self):
        linked = "→ run sub-skill: x\nSee references/scripts/foo.py."
        assembled = "→ run sub-skill: x\nSee the helper."
        result = av.verify_preservation(linked, assembled)
        assert result.ok is False
        assert "references/scripts/foo.py" in result.missing_file_paths

    def test_preservation_result_carries_all_eight_diff_fields(self):
        """Smoke: PreservationResult has the four new ``missing_*`` +
        ``extra_*`` lists for fenced blocks + file paths in addition
        to sub-skills + step IDs."""
        result = av.verify_preservation("", "")
        for field_name in (
            "missing_sub_skills", "extra_sub_skills",
            "missing_step_ids", "extra_step_ids",
            "missing_fenced_blocks", "extra_fenced_blocks",
            "missing_file_paths", "extra_file_paths",
        ):
            assert hasattr(result, field_name)
            assert getattr(result, field_name) == []


class TestAssemblePassContextStringW4:
    """#10752 W4: the LLM context string in assemble_pass must name
    ALL FOUR preservation dimensions, not just sub-skills + step IDs."""

    def test_context_mentions_all_four_dimensions(self):
        # Static-grep on the assemble_pass source. The prompt is a
        # string literal whose parens balance — walk forward until
        # the open-paren count returns to zero to capture the full
        # multi-line concat (inner parens like "(a)" / "(b)" don't
        # trip the balance check).
        src = (
            (Path(__file__).resolve().parent.parent
             / "references" / "scripts" / "assemble_pass.py")
            .read_text(encoding="utf-8")
        )
        marker = "context = ("
        start = src.index(marker) + len(marker) - 1
        depth = 0
        end = start
        for i in range(start, len(src)):
            ch = src[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        ctx_block = src[start:end].lower()
        assert "sub-skill" in ctx_block or "run sub-skill" in ctx_block, ctx_block
        assert (
            "step:cycle" in ctx_block
            or "step id" in ctx_block
            or "step-id" in ctx_block
        )
        assert "fenced" in ctx_block or "code block" in ctx_block
        assert "file path" in ctx_block or "path" in ctx_block
