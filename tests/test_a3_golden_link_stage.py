"""Byte-stability golden-file test suite for the v2 link stage (#10387, PRD-A A3).

Each fixture under ``tests/compose-fixtures/<install>/`` is a miniature
installed repo: ``references/`` (L1-L3 source tree) + ``.squidsquad/``
(L4 file). For every fixture, ``emit_v2_linked`` is invoked against the
fixture root and the result is diffed byte-for-byte against the
committed ``CLAUDE.linked.golden.md``. Any drift fails the test.

The negative test mutates a fixture's L4 to a parse-error shape (a
malformed H3 op heading) and confirms ``emit_v2_linked`` raises
``L4ParseError`` rather than silently producing a different output.

Out of scope per the issue body: CI hook / pre-merge wiring; that
belongs to PRD-E. This suite makes the regression net catchable; the
hook to make it gating lands later.
"""

import re
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
FIXTURES = REPO_ROOT / "tests" / "compose-fixtures"
sys.path.insert(0, str(SCRIPTS))

import v2_link_stage  # noqa: E402
from l4_parser import L4ParseError  # noqa: E402


# Per-fixture (alias, role_class, l3_domain) tuples. The alias is the
# directory name under tests/compose-fixtures/; role_class + l3_domain
# are the arguments emit_v2_linked needs to scope the L1-L3 walk.
_FIXTURES = [
    ("pm", "pm", None),
    ("worker-fe", "worker", "fe"),
]


@pytest.mark.parametrize("fixture_name,role_class,l3_domain", _FIXTURES)
def test_fixture_emit_matches_committed_golden(fixture_name, role_class, l3_domain):
    """The link stage's output for this fixture must byte-match the golden."""
    fixture_root = FIXTURES / fixture_name
    golden_path = fixture_root / "CLAUDE.linked.golden.md"
    assert golden_path.exists(), (
        f"Golden file missing for fixture '{fixture_name}'. "
        f"Regenerate with: python -c \"from pathlib import Path; "
        f"import sys; sys.path.insert(0, '{SCRIPTS}'); "
        f"import v2_link_stage; "
        f"Path('{golden_path}').write_text("
        f"v2_link_stage.emit_v2_linked('{role_class}', "
        f"{l3_domain!r}, repo_root=Path('{fixture_root}')))\""
    )
    expected = golden_path.read_text(encoding="utf-8")
    actual = v2_link_stage.emit_v2_linked(
        role_class, l3_domain, repo_root=fixture_root,
    )
    if actual != expected:
        # Surface a precise diff in the failure message so the operator
        # can decide between "fix the link stage" and "regenerate the
        # golden" without re-running by hand.
        import difflib
        diff = "\n".join(difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile=f"{golden_path}",
            tofile=f"emit_v2_linked({role_class!r}, {l3_domain!r})",
            lineterm="",
        ))
        pytest.fail(
            f"Golden drift on fixture '{fixture_name}'. "
            f"Either fix the link stage to restore the golden output or "
            f"regenerate the golden if the change was intentional.\n\n{diff}"
        )


# ---------------------------------------------------------------------------
# AC: L4 ops of each type — fixture coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_name,role_class,l3_domain", _FIXTURES)
def test_fixture_l4_uses_all_four_op_types(fixture_name, role_class, l3_domain):
    """Each fixture's L4 must exercise replace + insert-before + insert-after + append."""
    fixture_root = FIXTURES / fixture_name
    l4_path = fixture_root / ".squidsquad" / "project" / f"{role_class}.md"
    assert l4_path.exists(), f"L4 file missing for fixture '{fixture_name}'"
    l4_text = l4_path.read_text(encoding="utf-8")
    # Each op heading present at least once. Matched line-anchored so a
    # stray phrase in prose doesn't satisfy the check.
    assert re.search(r"^### replace\b", l4_text, re.MULTILINE), (
        f"fixture '{fixture_name}' L4 missing `### replace`"
    )
    assert re.search(r"^### insert-before\b", l4_text, re.MULTILINE), (
        f"fixture '{fixture_name}' L4 missing `### insert-before`"
    )
    assert re.search(r"^### insert-after\b", l4_text, re.MULTILINE), (
        f"fixture '{fixture_name}' L4 missing `### insert-after`"
    )
    assert re.search(r"^### append\b", l4_text, re.MULTILINE), (
        f"fixture '{fixture_name}' L4 missing `### append`"
    )


def test_fixture_pm_has_no_l3_subtree():
    """AC: 'one role-class with no L3 (pm)' — verify the structural property."""
    pm_role_dir = FIXTURES / "pm" / "references" / "roles" / "pm"
    assert pm_role_dir.is_dir()
    subdirs = [p for p in pm_role_dir.iterdir() if p.is_dir()]
    assert subdirs == [], (
        f"pm fixture should have no L3 subtree under references/roles/pm/; "
        f"found {subdirs}"
    )


def test_fixture_worker_fe_has_l3_subtree():
    """AC: 'one with L3 (worker + fe)' — verify the structural property."""
    fe_dir = FIXTURES / "worker-fe" / "references" / "roles" / "worker" / "fe"
    assert fe_dir.is_dir()
    md_files = list(fe_dir.glob("*.md"))
    assert md_files, "worker-fe fixture should have at least one .md under worker/fe/"


# ---------------------------------------------------------------------------
# Negative test: corrupted L4 → compose aborts (does not silently produce drift)
# ---------------------------------------------------------------------------

def test_corrupted_l4_aborts_with_parse_error(tmp_path):
    """AC: 'corrupted L4 op → compose aborts (does not silently produce drift)'."""
    # Copy the pm fixture into a tmp tree so we can mutate it safely.
    src = FIXTURES / "pm"
    shutil.copytree(src, tmp_path / "pm")
    bad_root = tmp_path / "pm"
    l4_path = bad_root / ".squidsquad" / "project" / "pm.md"
    # Corrupt: introduce an H3 line that does NOT match any legal op
    # grammar. A2b's parser rejects this with L4ParseError.
    l4_path.write_text(
        "## Instructions\n\n"
        "### frobnicate step:cycle/work\n\n"
        "Not a legal op heading.\n",
        encoding="utf-8",
    )
    with pytest.raises(L4ParseError):
        v2_link_stage.emit_v2_linked(
            "pm", None, repo_root=bad_root,
        )


def test_corrupted_l4_does_not_silently_match_golden(tmp_path):
    """The link stage must NOT silently swallow a corrupted L4 and emit the same body.

    Belt-and-braces companion to the parse-error test: even if a future
    refactor caught L4ParseError and proceeded, the byte-stability test
    would still catch the drift. This test pins that property.
    """
    src = FIXTURES / "pm"
    shutil.copytree(src, tmp_path / "pm")
    bad_root = tmp_path / "pm"
    l4_path = bad_root / ".squidsquad" / "project" / "pm.md"
    l4_path.write_text(
        "## Instructions\n\n"
        "### frobnicate step:cycle/work\n\n"
        "Not a legal op heading.\n",
        encoding="utf-8",
    )
    golden = (FIXTURES / "pm" / "CLAUDE.linked.golden.md").read_text(encoding="utf-8")
    try:
        actual = v2_link_stage.emit_v2_linked("pm", None, repo_root=bad_root)
    except L4ParseError:
        return  # Expected — assertion holds via the raise.
    assert actual != golden, (
        "A corrupted L4 produced byte-identical output to the golden — "
        "the link stage silently dropped the malformed ops, masking drift."
    )
