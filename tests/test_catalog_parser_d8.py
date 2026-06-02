"""Tests for D8 row-schema validation folded into catalog_parser.py (#10679).

D8 AC6 mandates tests for:
  (a) clean row → pass
  (b) missing required column → abort with diagnostic
  (c) empty required column → abort
  (d) extra optional column → ignored (already covered by D1's tests)

These tests focus on D8's contribution (the description-required check).
The D1 tests in test_catalog_parser_d1.py cover the clean / extra-col
paths against the broader parser surface; this module pins the
D8-specific abort behavior.
"""

import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import catalog_parser as cp  # noqa: E402


def _write_catalog(tmp_path, body):
    f = tmp_path / "catalog.md"
    f.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# AC6(a) — clean row passes (regression check that D8 didn't break D1)
# ---------------------------------------------------------------------------


class TestCleanRowPasses:
    def test_row_with_non_empty_description_parses(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` | Append-only tracker comment format | all |
        """)
        entries = cp.parse_catalog_entries(catalog)
        assert len(entries) == 1
        assert entries[0].name == "discussion"
        assert entries[0].description == "Append-only tracker comment format"


# ---------------------------------------------------------------------------
# AC6(b) — missing description column → abort
# ---------------------------------------------------------------------------


class TestMissingColumnAborts:
    def test_row_with_only_name_column_aborts(self, tmp_path):
        """A row with just the name cell (no description column at all)
        violates the row schema. The header still has the column; the
        row is structurally short.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        msg = str(e.value).lower()
        assert "description" in msg
        assert "discussion" in str(e.value)


# ---------------------------------------------------------------------------
# AC6(c) — empty description value → abort
# ---------------------------------------------------------------------------


class TestEmptyDescriptionAborts:
    def test_empty_description_cell_aborts(self, tmp_path):
        """The description column EXISTS structurally but has an empty
        value. Treated identically to missing column per AC3.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` |  | all |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        msg = str(e.value).lower()
        assert "empty" in msg
        assert "description" in msg
        assert "discussion" in str(e.value)

    def test_whitespace_only_description_aborts(self, tmp_path):
        """A description cell containing only spaces is treated as empty.
        Spaces are stripped before the emptiness check.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` |    | all |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        assert "empty" in str(e.value).lower()

    def test_diagnostic_suggests_retirement_marker(self, tmp_path):
        """Per the helper's docstring, the empty-description diagnostic
        suggests the retirement convention (`~~`name`~~`) as the
        operator-facing fix.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `old-thing` |  | _retired_ |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        msg = str(e.value)
        # Either the retirement convention is mentioned, or the "fill the
        # description" guidance is — both are valid operator paths
        assert "~~" in msg or "retired" in msg.lower() or "fill" in msg.lower()


# ---------------------------------------------------------------------------
# AC6(d) — extra optional column ignored (already covered by D1's
# `test_extra_trailing_column_ignored` in test_catalog_parser_d1.py).
# Repeat one shape here as a D8 regression guard.
# ---------------------------------------------------------------------------


class TestExtraColumnIgnored:
    def test_extra_columns_beyond_description_do_not_abort(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by | Status | Notes |
        |---|---|---|---|---|
        | `discussion` | Tracker comments | all | active | n/a |
        """)
        entries = cp.parse_catalog_entries(catalog)
        assert len(entries) == 1
        assert entries[0].description == "Tracker comments"


# ---------------------------------------------------------------------------
# Multi-row interaction — first valid row passes, second invalid aborts
# ---------------------------------------------------------------------------


class TestMultiRowAbortBehavior:
    def test_first_row_valid_second_row_aborts_on_empty_description(self, tmp_path):
        """Catalog is parsed top-to-bottom; the first error encountered
        aborts the whole parse. The earlier valid row is NOT silently
        included in the output (the abort wins).
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `valid-row` | Has description | all |
        | `invalid-row` |  | all |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        assert "invalid-row" in str(e.value)
