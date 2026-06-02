"""Tests for references/scripts/v2_catalog_gate.py (#10674, PRD-D D3).

AC6 mandates tests covering:
  (a) clean compose with all refs resolved -> no error
  (b) single unresolved reference -> abort
  (c) multiple unresolved -> ALL reported, not just first
  (d) resolved but source file missing on disk -> abort
  (e) mix of unresolved + missing-file -> both reported
  (f) v1 path untouched -- verified at the compose dispatch level
     (D3's gate function never runs on v1 output)

Plus structural tests for the regex (slash-bearing names, duplicate
references collapse to one issue, the reference syntax variants).
"""

import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import v2_catalog_gate as gate  # noqa: E402


def _make_repo(tmp_path, *, catalog_body, sub_skill_files):
    """Build a self-contained repo-root fixture."""
    (tmp_path / "docs").mkdir()
    catalog = tmp_path / "docs" / "sub-skill-catalog.md"
    catalog.write_text(textwrap.dedent(catalog_body).lstrip("\n"),
                       encoding="utf-8")
    sub_skills = tmp_path / "references" / "sub-skills"
    sub_skills.mkdir(parents=True)
    for rel in sub_skill_files:
        full = sub_skills / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(f"# {rel}\n", encoding="utf-8")
    return tmp_path, catalog


_CATALOG_TWO_ROWS = """
## `common/` — Cross-cutting

### Boot

| Sub-skill | One-liner | Used by |
|---|---|---|
| `boot-bootstrap` | Mode detection | all |
| `cycle-runner` | 3-phase cycle | all |
"""


# ---------------------------------------------------------------------------
# find_references — regex shape
# ---------------------------------------------------------------------------


class TestFindReferences:

    def test_finds_plain_name(self):
        text = "Step 1 → run sub-skill: boot-bootstrap"
        assert gate.find_references(text) == ["boot-bootstrap"]

    def test_finds_multiple(self):
        text = textwrap.dedent("""
            Step 1 → run sub-skill: boot-bootstrap

            Step 2 → run sub-skill: cycle-runner

            Step 3 → run sub-skill: vault-remember
        """)
        out = gate.find_references(text)
        assert out == ["boot-bootstrap", "cycle-runner", "vault-remember"]

    def test_finds_slash_bearing_name(self):
        # Catalog convention for nested paths (e.g. event variants).
        text = "→ run sub-skill: roles/dm/events/pr-merge-wait"
        assert gate.find_references(text) == [
            "roles/dm/events/pr-merge-wait",
        ]

    def test_ignores_unrelated_arrows(self):
        # The composed output uses → as a directional glyph in prose
        # too; only the `→ run sub-skill:` shape counts.
        text = "pre-cycle → creative work → post-cycle (no ref)"
        assert gate.find_references(text) == []

    def test_duplicates_preserved_in_extraction(self):
        # find_references doesn't dedupe -- dedup happens in the
        # gate's issue construction so each issue lands once.
        text = "→ run sub-skill: boot-bootstrap\n→ run sub-skill: boot-bootstrap"
        assert gate.find_references(text) == [
            "boot-bootstrap", "boot-bootstrap",
        ]


# ---------------------------------------------------------------------------
# AC6(a) clean compose -> no issues
# ---------------------------------------------------------------------------


class TestCleanCompose:

    def test_all_refs_resolved_returns_clean(self, tmp_path):
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
        )
        text = textwrap.dedent("""
            → run sub-skill: boot-bootstrap
            → run sub-skill: cycle-runner
        """)
        result = gate.validate_v2_compose(
            text, catalog_path=catalog, repo_root=repo)
        assert result.has_issues is False
        assert result.format() == ""

    def test_no_references_at_all_returns_clean(self, tmp_path):
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
        )
        # Composed text with no `→ run sub-skill:` lines (e.g. a role
        # with no orchestrator references).
        result = gate.validate_v2_compose(
            "## Identity\n\nNo refs here.\n",
            catalog_path=catalog, repo_root=repo,
        )
        assert result.has_issues is False


# ---------------------------------------------------------------------------
# AC6(b)+(c) unresolved single + multiple
# ---------------------------------------------------------------------------


class TestUnresolved:

    def test_single_unresolved_aborts(self, tmp_path):
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
        )
        text = "→ run sub-skill: phantom-skill"
        result = gate.validate_v2_compose(
            text, catalog_path=catalog, repo_root=repo)
        assert result.has_issues is True
        assert len(result.issues) == 1
        i = result.issues[0]
        assert i.kind == "unresolved"
        assert i.name == "phantom-skill"
        out = result.format()
        assert "Unresolved sub-skill references" in out
        assert "`phantom-skill`" in out

    def test_multiple_unresolved_all_reported(self, tmp_path):
        # AC4 explicit: report ALL unresolved, not just the first.
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
        )
        text = textwrap.dedent("""
            → run sub-skill: phantom-one
            → run sub-skill: cycle-runner
            → run sub-skill: phantom-two
            → run sub-skill: phantom-three
        """)
        result = gate.validate_v2_compose(
            text, catalog_path=catalog, repo_root=repo)
        unresolved = [i.name for i in result.issues
                      if i.kind == "unresolved"]
        assert sorted(unresolved) == [
            "phantom-one", "phantom-three", "phantom-two",
        ]

    def test_duplicate_unresolved_reference_collapses_to_one_issue(
            self, tmp_path):
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
        )
        text = "→ run sub-skill: phantom\n→ run sub-skill: phantom"
        result = gate.validate_v2_compose(
            text, catalog_path=catalog, repo_root=repo)
        assert len(result.issues) == 1
        assert result.format().count("`phantom`") == 1


# ---------------------------------------------------------------------------
# AC6(d) resolved but file missing
# ---------------------------------------------------------------------------


class TestMissingSourceFile:

    def test_resolved_but_file_missing_aborts(self, tmp_path):
        # Catalog has the row, but the source file is not on disk.
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                # cycle-runner.md intentionally NOT on disk
            ],
        )
        text = "→ run sub-skill: cycle-runner"
        result = gate.validate_v2_compose(
            text, catalog_path=catalog, repo_root=repo)
        assert result.has_issues is True
        assert len(result.issues) == 1
        i = result.issues[0]
        assert i.kind == "missing-file"
        assert i.name == "cycle-runner"
        assert i.source_path == (
            "references/sub-skills/common/cycle-runner.md"
        )
        out = result.format()
        assert "source file missing on disk" in out


# ---------------------------------------------------------------------------
# AC6(e) mixed: clean + unresolved + missing-file
# ---------------------------------------------------------------------------


class TestMixedIssues:

    def test_clean_plus_unresolved_plus_missing_all_reported(self, tmp_path):
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                # cycle-runner.md NOT on disk -> missing-file
            ],
        )
        text = textwrap.dedent("""
            → run sub-skill: boot-bootstrap
            → run sub-skill: cycle-runner
            → run sub-skill: phantom
        """)
        result = gate.validate_v2_compose(
            text, catalog_path=catalog, repo_root=repo)
        kinds = sorted((i.kind, i.name) for i in result.issues)
        assert kinds == [
            ("missing-file", "cycle-runner"),
            ("unresolved", "phantom"),
        ]
        out = result.format()
        # Both sections render in the same report.
        assert "Unresolved sub-skill references" in out
        assert "source file missing on disk" in out


# ---------------------------------------------------------------------------
# CatalogGateError shape
# ---------------------------------------------------------------------------


class TestCatalogGateError:

    def test_error_message_includes_alias_and_report(self, tmp_path):
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
        )
        text = "→ run sub-skill: phantom"
        result = gate.validate_v2_compose(
            text, catalog_path=catalog, repo_root=repo)
        with pytest.raises(gate.CatalogGateError) as ei:
            raise gate.CatalogGateError(result, alias="pm")
        msg = str(ei.value)
        assert "pm" in msg
        assert "phantom" in msg

    def test_error_has_structured_result_attribute(self, tmp_path):
        repo, catalog = _make_repo(
            tmp_path,
            catalog_body=_CATALOG_TWO_ROWS,
            sub_skill_files=[
                "common/boot-bootstrap.md",
                "common/cycle-runner.md",
            ],
        )
        text = "→ run sub-skill: phantom"
        result = gate.validate_v2_compose(
            text, catalog_path=catalog, repo_root=repo)
        err = gate.CatalogGateError(result, alias="pm")
        assert err.result is result
        assert err.alias == "pm"


# ---------------------------------------------------------------------------
# Compose pipeline integration: v1 path untouched (AC5)
# ---------------------------------------------------------------------------


class TestV1Untouched:
    """AC5 — v1 compose path never calls the gate. Verified by static
    grep: only the v2 dispatch (deploy_alias_v2) imports v2_catalog_gate."""

    def test_only_v2_dispatch_imports_gate(self):
        src = (SCRIPTS / "compose.py").read_text(encoding="utf-8")
        # Locate every v2_catalog_gate reference and confirm it sits
        # inside ``def deploy_alias_v2(`` (the v2 dispatch).
        ref_positions = []
        start = 0
        while True:
            idx = src.find("v2_catalog_gate", start)
            if idx < 0:
                break
            ref_positions.append(idx)
            start = idx + 1
        assert ref_positions, (
            "compose.py should reference v2_catalog_gate at least once "
            "(the v2 dispatch wiring)"
        )
        # Find the function that ENCLOSES each reference. Walk back
        # to the most recent ``def `` line and assert it's the v2
        # dispatch.
        for pos in ref_positions:
            preceding = src.rfind("\ndef ", 0, pos)
            if preceding < 0:
                pytest.fail(
                    f"reference at offset {pos} sits outside any function"
                )
            fn_line_end = src.index("\n", preceding + 1)
            fn_signature = src[preceding + 1:fn_line_end]
            assert "deploy_alias_v2" in fn_signature, (
                f"v2_catalog_gate referenced inside non-v2 function: "
                f"{fn_signature!r}"
            )
