"""Tests for compose.py deploy <alias> --check --staged-l4 (#10395, PRD-A A4.5)."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
from link_stage_validator import LinkStageValidationError  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _frontmatter(slot, ordinal, roles=None):
    lines = ["---", f"slot: {slot}", f"ordinal: {ordinal}"]
    if roles is not None:
        lines.append(f"roles: [{', '.join(roles)}]")
    lines.append("---")
    return "\n".join(lines)


def _write_source(path, slot, ordinal, body, roles=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _frontmatter(slot, ordinal, roles=roles) + "\n\n" + body
    path.write_text(text, encoding="utf-8")


def _stage_minimal_install(tmp_path, *, role="pm"):
    """Stage a small fixture: L1 base + one L2 file for the role-class with a step ID."""
    refs = tmp_path / "references"
    _write_source(refs / "roles" / "identity.md", "identity", 10, "Base identity.")
    _write_source(
        refs / "roles" / "instructions.md", "instructions", 10,
        "### step:cycle/boot\n→ run sub-skill: boot-bootstrap\nBoot body.\n",
    )
    _write_source(refs / "roles" / "vault.md", "vault", 10, "Vault base.")
    _write_source(
        refs / "roles" / role / "instructions.md", "instructions", 20,
        "### step:cycle/work\n→ run sub-skill: triage-issues\nWork body.\n",
        roles=[role],
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Function-level tests for check_alias_staged_l4
# ---------------------------------------------------------------------------

def test_check_alias_staged_l4_clean_returns_role_class(tmp_path):
    _stage_minimal_install(tmp_path, role="pm")
    staged = tmp_path / "staged.md"
    staged.write_text(
        "## Agent Functions\n\n"
        "### insert-after step:cycle/boot\n\n"
        "→ run sub-skill: pipeline-sentinel\n\n"
        "Post-boot body.\n",
        encoding="utf-8",
    )
    role_class = compose.check_alias_staged_l4(
        "pm", staged, target_root=tmp_path,
        registry={"pm": ("pm", None)},
    )
    assert role_class == "pm"


def test_check_alias_staged_l4_missing_staged_file_raises_filenotfound(tmp_path):
    _stage_minimal_install(tmp_path)
    with pytest.raises(FileNotFoundError):
        compose.check_alias_staged_l4(
            "pm", tmp_path / "nonexistent.md", target_root=tmp_path,
            registry={"pm": ("pm", None)},
        )


def test_check_alias_staged_l4_unknown_alias_raises_keyerror(tmp_path):
    _stage_minimal_install(tmp_path)
    staged = tmp_path / "staged.md"
    staged.write_text("## Agent Functions\n", encoding="utf-8")
    with pytest.raises(KeyError):
        compose.check_alias_staged_l4(
            "ghost-alias", staged, target_root=tmp_path,
            registry={"pm": ("pm", None)},
        )


def test_check_alias_staged_l4_r1_violation_raises(tmp_path):
    """AC: 'staged R1 violation (vault H2)' — L4 file with `## Vault` aborts."""
    _stage_minimal_install(tmp_path)
    staged = tmp_path / "staged.md"
    staged.write_text(
        "## Vault\n\nProject-authored vault content (R1 violation).\n",
        encoding="utf-8",
    )
    with pytest.raises(LinkStageValidationError) as exc:
        compose.check_alias_staged_l4(
            "pm", staged, target_root=tmp_path,
            registry={"pm": ("pm", None)},
        )
    assert exc.value.rule == "R1"


def test_check_alias_staged_l4_r5_violation_raises(tmp_path):
    """AC: 'staged R5 violation (orphan step ID)' — L4 op targets a non-existent step."""
    _stage_minimal_install(tmp_path)
    staged = tmp_path / "staged.md"
    staged.write_text(
        "## Agent Functions\n\n"
        "### replace step:cycle/ghost-step\n\n"
        "Body.\n",
        encoding="utf-8",
    )
    with pytest.raises(LinkStageValidationError) as exc:
        compose.check_alias_staged_l4(
            "pm", staged, target_root=tmp_path,
            registry={"pm": ("pm", None)},
        )
    assert exc.value.rule == "R5"
    assert exc.value.step_id == "ghost-step"


def test_check_alias_staged_l4_r7_violation_raises(tmp_path):
    """AC: 'staged R7 violation (duplicate replace target)' — two replaces hit same step."""
    _stage_minimal_install(tmp_path)
    staged = tmp_path / "staged.md"
    staged.write_text(
        "## Agent Functions\n\n"
        "### replace step:cycle/work\n\n"
        "First body.\n\n"
        "### replace step:cycle/work\n\n"
        "Second body.\n",
        encoding="utf-8",
    )
    with pytest.raises(LinkStageValidationError) as exc:
        compose.check_alias_staged_l4(
            "pm", staged, target_root=tmp_path,
            registry={"pm": ("pm", None)},
        )
    assert exc.value.rule == "R7"
    assert exc.value.step_id == "work"


def test_check_alias_staged_l4_does_not_write_to_disk(tmp_path):
    """AC: '--check mode: no disk writes'."""
    _stage_minimal_install(tmp_path)
    staged = tmp_path / "staged.md"
    staged.write_text(
        "## Agent Functions\n\n### insert-after step:cycle/boot\n\n→ run sub-skill: x\n\nBody.\n",
        encoding="utf-8",
    )
    before = set(tmp_path.rglob("*"))
    compose.check_alias_staged_l4(
        "pm", staged, target_root=tmp_path,
        registry={"pm": ("pm", None)},
    )
    after = set(tmp_path.rglob("*"))
    assert before == after, (
        "check_alias_staged_l4 must not create any files. "
        f"new entries: {after - before}"
    )


# ---------------------------------------------------------------------------
# CLI integration tests — exit code semantics (0 clean / 1 validation / 2 setup)
# ---------------------------------------------------------------------------

def _run_compose(*args, cwd=None):
    if cwd is None:
        cwd = REPO_ROOT
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "compose.py"), *args],
        capture_output=True, text=True, cwd=str(cwd),
    )


def test_cli_missing_value_after_staged_l4_exits_2():
    """`--staged-l4` with no path argument is a setup error."""
    result = _run_compose("deploy", "pm", "--check", "--staged-l4")
    assert result.returncode == compose.CHECK_EXIT_ERROR
    assert "requires a path argument" in result.stderr


def test_cli_staged_l4_nonexistent_path_exits_2(tmp_path):
    """`--staged-l4 <bogus path>` → setup error (exit 2)."""
    result = _run_compose(
        "deploy", "pm", "--check", "--staged-l4", str(tmp_path / "ghost.md"),
    )
    assert result.returncode == compose.CHECK_EXIT_ERROR
    assert "setup error" in result.stderr


def test_cli_staged_l4_with_unknown_alias_exits_2(tmp_path):
    """Even with a valid staged file, an unknown alias is a setup error."""
    staged = tmp_path / "staged.md"
    staged.write_text("## Agent Functions\n", encoding="utf-8")
    result = _run_compose(
        "deploy", "definitely-not-a-real-alias", "--check",
        "--staged-l4", str(staged),
    )
    assert result.returncode == compose.CHECK_EXIT_ERROR
    assert "setup error" in result.stderr


def test_cli_check_without_staged_l4_exits_error_post_e6():
    """Post-E6 (#10685) Phase 3d.3: `deploy <alias> --check` without
    `--staged-l4` exits CHECK_EXIT_ERROR with a retirement diagnostic.

    The v1 drift-check fallback was retired (Option A) because the v2
    on-disk CLAUDE.md is LLM-polished and cannot byte-match a
    deterministic in-memory compose.
    """
    result = _run_compose("deploy", "pm", "--check")
    assert result.returncode == compose.CHECK_EXIT_ERROR
    assert "requires" in result.stderr and "--staged-l4" in result.stderr


def test_cli_help_or_no_args_does_not_crash():
    """Sanity: passing the new flag args parser shouldn't break the help path."""
    result = _run_compose()
    assert result.returncode == 0
