"""Unit tests for config.parse_aliases_registry (PRD-A Story A5, #10385).

Covers the AC list verbatim:
  - valid table -> {alias: (role_class, l3_domain)}
  - missing `## Aliases` section -> AliasesRegistryError
  - malformed table row (wrong column count) -> AliasesRegistryError
  - unknown role-class -> AliasesRegistryError
  - duplicate alias -> AliasesRegistryError
  - em-dash "—" in L3 column -> None (sentinel)

Plus boundary cases the AC implies but doesn't enumerate verbatim:
  - empty section -> AliasesRegistryError
  - header row name mismatch -> AliasesRegistryError
  - missing separator row -> AliasesRegistryError
  - empty alias / empty role-class cell -> AliasesRegistryError
  - table with only a header (zero data rows) -> AliasesRegistryError
  - module-level constants exported (callers should consume, not redefine)
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import config  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures: canned config.md bodies with various `## Aliases` shapes
# ---------------------------------------------------------------------------


def _wrap_with_aliases(table_body):
    """Wrap a table body in a minimal config.md so _parse_sections finds it."""
    return (
        "- **SquidSquad Version**: 0.0.1\n"
        "\n"
        "## Aliases\n"
        "\n"
        f"{table_body}"
        "\n"
        "## Project\n"
        "- **Name**: test\n"
    )


CANONICAL_TABLE = (
    "| alias | role-class | L3 domain |\n"
    "|---|---|---|\n"
    "| pm | pm | — |\n"
    "| frontend-1 | worker | fe |\n"
    "| backend-1 | worker | be |\n"
    "| verifier | verifier | — |\n"
    "| dm | dm | — |\n"
)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidTable:
    """The §3.0 canonical example parses without complaint."""

    def test_returns_dict_of_tuples(self):
        result = config.parse_aliases_registry(_wrap_with_aliases(CANONICAL_TABLE))
        assert isinstance(result, dict)
        assert all(
            isinstance(v, tuple) and len(v) == 2 for v in result.values()
        )

    def test_canonical_table_round_trips(self):
        result = config.parse_aliases_registry(_wrap_with_aliases(CANONICAL_TABLE))
        assert result == {
            "pm": ("pm", None),
            "frontend-1": ("worker", "fe"),
            "backend-1": ("worker", "be"),
            "verifier": ("verifier", None),
            "dm": ("dm", None),
        }

    def test_em_dash_l3_becomes_none(self):
        """Spec says `—` (U+2014) signals 'no L3' — must become Python None."""
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
            "| pm | pm | — |\n"
        )
        result = config.parse_aliases_registry(_wrap_with_aliases(body))
        assert result["pm"] == ("pm", None)

    def test_non_dash_l3_preserved_verbatim(self):
        """Anything other than the sentinel passes through unchanged."""
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
            "| ios-1 | worker | ios |\n"
            "| web-2 | worker | web-mobile |\n"  # multi-word L3 allowed
        )
        result = config.parse_aliases_registry(_wrap_with_aliases(body))
        assert result["ios-1"] == ("worker", "ios")
        assert result["web-2"] == ("worker", "web-mobile")

    def test_all_four_role_classes_accepted(self):
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
            "| a | pm | — |\n"
            "| b | worker | fe |\n"
            "| c | verifier | — |\n"
            "| d | dm | — |\n"
        )
        result = config.parse_aliases_registry(_wrap_with_aliases(body))
        assert {v[0] for v in result.values()} == {"pm", "worker", "verifier", "dm"}


# ---------------------------------------------------------------------------
# Diagnostic-on-malformed cases (one per AC error bullet + boundary cases)
# ---------------------------------------------------------------------------


class TestMalformedInputs:

    def test_missing_aliases_section(self):
        text = "- **SquidSquad Version**: 0.0.1\n\n## Project\n- **Name**: test\n"
        with pytest.raises(config.AliasesRegistryError, match="missing"):
            config.parse_aliases_registry(text)

    def test_empty_aliases_section(self):
        text = (
            "- **SquidSquad Version**: 0.0.1\n"
            "\n"
            "## Aliases\n"
            "\n"
            "## Project\n"
        )
        with pytest.raises(config.AliasesRegistryError, match="no table"):
            config.parse_aliases_registry(text)

    def test_wrong_column_count_in_header(self):
        body = (
            "| alias | role-class |\n"  # 2 columns, not 3
            "|---|---|\n"
            "| pm | pm |\n"
        )
        with pytest.raises(config.AliasesRegistryError, match="header row"):
            config.parse_aliases_registry(_wrap_with_aliases(body))

    def test_wrong_column_names_in_header(self):
        body = (
            "| name | role | l3 |\n"  # 3 columns, wrong names
            "|---|---|---|\n"
            "| pm | pm | — |\n"
        )
        with pytest.raises(config.AliasesRegistryError, match="header row"):
            config.parse_aliases_registry(_wrap_with_aliases(body))

    def test_missing_separator_row(self):
        body = (
            "| alias | role-class | L3 domain |\n"
            "| pm | pm | — |\n"  # data row directly after header, no |---|---|---|
        )
        with pytest.raises(config.AliasesRegistryError, match="separator row"):
            config.parse_aliases_registry(_wrap_with_aliases(body))

    def test_data_row_wrong_column_count(self):
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
            "| pm | pm |\n"  # 2 cells, not 3
        )
        with pytest.raises(config.AliasesRegistryError, match="row 1 has 2"):
            config.parse_aliases_registry(_wrap_with_aliases(body))

    def test_unknown_role_class_rejected(self):
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
            "| pm | pm | — |\n"
            "| weird | designer | — |\n"  # `designer` no longer a role-class
        )
        with pytest.raises(config.AliasesRegistryError, match="unknown role-class"):
            config.parse_aliases_registry(_wrap_with_aliases(body))

    def test_duplicate_alias_rejected(self):
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
            "| worker-1 | worker | fe |\n"
            "| worker-1 | worker | be |\n"  # same alias, different L3 — illegal
        )
        with pytest.raises(config.AliasesRegistryError, match="duplicate alias"):
            config.parse_aliases_registry(_wrap_with_aliases(body))

    def test_empty_alias_cell_rejected(self):
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
            "|  | worker | fe |\n"
        )
        with pytest.raises(config.AliasesRegistryError, match="empty `alias`"):
            config.parse_aliases_registry(_wrap_with_aliases(body))

    def test_empty_role_class_cell_rejected(self):
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
            "| foo |  | fe |\n"
        )
        with pytest.raises(config.AliasesRegistryError, match="empty `role-class`"):
            config.parse_aliases_registry(_wrap_with_aliases(body))

    def test_header_only_no_data_rejected(self):
        body = (
            "| alias | role-class | L3 domain |\n"
            "|---|---|---|\n"
        )
        with pytest.raises(config.AliasesRegistryError, match="zero data rows"):
            config.parse_aliases_registry(_wrap_with_aliases(body))


# ---------------------------------------------------------------------------
# Module surface — callers should consume exported constants, not redefine
# ---------------------------------------------------------------------------


class TestExportedConstants:

    def test_role_classes_frozenset_matches_spec(self):
        """COMPOSE-ARCHITECTURE §3.0 enumerates the 4 L2 classes."""
        assert config.ALIASES_ROLE_CLASSES == frozenset(
            {"pm", "worker", "verifier", "dm"}
        )

    def test_l3_none_sentinel_is_em_dash(self):
        assert config.ALIASES_L3_NONE_SENTINEL == "—"

    def test_error_is_value_error_subclass(self):
        """Callers that already catch ValueError keep working."""
        assert issubclass(config.AliasesRegistryError, ValueError)
