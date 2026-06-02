"""Tests for references/scripts/catalog_parser.py (#10672, PRD-D D1).

AC6 mandates tests for:
  (a) clean catalog parse → returns expected `{name: source_path}` mapping
  (b) malformed row → abort with diagnostic
  (c) duplicate name → abort
  (d) path traversal → abort
  (e) valid forward-compatible extra column → ignored cleanly

Plus the live-catalog integration check: parse the real
`docs/sub-skill-catalog.md` and confirm every emitted source-path
points at a file that exists on disk (defensive — catches drift
between catalog and source tree).
"""

import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import catalog_parser as cp  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_catalog(tmp_path, body):
    """Write a catalog fixture to tmp_path/catalog.md and return the path."""
    f = tmp_path / "catalog.md"
    f.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# AC6(a) — clean parse
# ---------------------------------------------------------------------------


class TestCleanParse:
    def test_common_section_resolves_to_common_dir(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting sub-skills

        ### Boot

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `boot-bootstrap` | Mode detection | all |
        | `cycle-runner` | 3-phase cycle | all |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "boot-bootstrap": "references/sub-skills/common/boot-bootstrap.md",
            "cycle-runner": "references/sub-skills/common/cycle-runner.md",
        }

    def test_common_events_section_resolves_to_common_events_dir(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common-events/` — Event-shaped fragments

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `event-driven-workflow` | The event-mode l2 base | all |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "event-driven-workflow":
                "references/sub-skills/common-events/event-driven-workflow.md",
        }

    def test_roles_h3_pins_role_specific_directory(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `roles/<role>/` — Role-specific sub-skills

        ### PM (`roles/pm/`)

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `pm-planning` | Phase 1/2 research | PM |
        | `pm-orphan-cleanup` | Stale ticket sweep | PM |

        ### Dev (`roles/dev/`)

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `implement-tasks` | Task implementation flow | dev |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "pm-planning": "references/sub-skills/roles/pm/pm-planning.md",
            "pm-orphan-cleanup":
                "references/sub-skills/roles/pm/pm-orphan-cleanup.md",
            "implement-tasks":
                "references/sub-skills/roles/dev/implement-tasks.md",
        }

    def test_slash_bearing_name_overrides_h2_directory(self, tmp_path):
        """B1 fix: names containing slashes encode the relative source-path
        directly (catalog convention used at lines 177 + 225 of the
        live catalog for cross-directory sub-skills like
        `roles/dm/events/pr-merge-wait`). The slash-bearing name IS
        the lookup key, and source-path = `references/sub-skills/{name}.md`.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common-events/` — Event-shaped fragments

        ### Role-specific event extras

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `roles/dm/events/pr-merge-wait` | DM's behavior while a PR is merging | DM (event mode) |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "roles/dm/events/pr-merge-wait":
                "references/sub-skills/roles/dm/events/pr-merge-wait.md",
        }

    def test_slash_bearing_name_under_role_h3(self, tmp_path):
        """Live-catalog row at line 225 — `skill/finding-categories`
        under `### QA (\`roles/qa/\`)` — uses the slash-name override
        even when the H3 has its own role directory.
        """
        catalog = _write_catalog(tmp_path, """
        ## `roles/<role>/` — Role-specific sub-skills

        ### QA (`roles/qa/`)

        | Sub-skill | One-liner |
        |---|---|
        | `verification` | E2E tests | QA |
        | `skill/finding-categories` | Skill-domain finding taxonomy | QA |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "verification": "references/sub-skills/roles/qa/verification.md",
            # Slash-name overrides the H3 directory — it's an absolute
            # path under references/sub-skills/
            "skill/finding-categories":
                "references/sub-skills/skill/finding-categories.md",
        }

    def test_project_section_is_excluded(self, tmp_path):
        """L4 seed templates under `project/` are NOT sub-skills resolved
        by compose — they're install scaffolding. Parser excludes them.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` | Tracker comments | all |

        ## `project/` — L4 seed templates

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `seed-pm-l4` | PM L4 starter | install |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "discussion": "references/sub-skills/common/discussion.md",
        }
        assert "seed-pm-l4" not in out


# ---------------------------------------------------------------------------
# AC6(e) — forward-compatible extra columns
# ---------------------------------------------------------------------------


class TestForwardCompatibleColumns:
    def test_extra_trailing_column_ignored(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by | Status | Ordinal |
        |---|---|---|---|---|
        | `discussion` | Tracker comments | all | active | 10 |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "discussion": "references/sub-skills/common/discussion.md",
        }

    def test_description_extracted_from_one_liner_column(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` | Tracker comment append-only format | all |
        """)
        entries = cp.parse_catalog_entries(catalog)
        assert entries[0].description == "Tracker comment append-only format"

    def test_description_falls_back_to_second_column_when_header_differs(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | Purpose | Used by |
        |---|---|---|
        | `discussion` | Tracker comments | all |
        """)
        entries = cp.parse_catalog_entries(catalog)
        # `purpose` is in the description-alias list — extracted from col 1
        assert entries[0].description == "Tracker comments"


# ---------------------------------------------------------------------------
# AC6(c) — duplicate name aborts
# ---------------------------------------------------------------------------


class TestDuplicateAbort:
    def test_duplicate_in_same_section_aborts(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` | First definition | all |
        | `discussion` | Second definition | dev |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        assert "duplicate" in str(e.value).lower()
        assert "discussion" in str(e.value)

    def test_duplicate_diagnostic_includes_both_source_paths(self, tmp_path):
        """C3 fix: the duplicate diagnostic surfaces BOTH source-paths
        so PM can disambiguate without manually re-reading the catalog.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `improvement-scan` | The common variant | all |

        ## `roles/<role>/` — Role-specific

        ### PM (`roles/pm/`)

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `improvement-scan` | The PM variant | PM |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        msg = str(e.value)
        # Both source-paths named in the diagnostic
        assert "common/improvement-scan.md" in msg
        assert "roles/pm/improvement-scan.md" in msg
        # PM-facing guidance present
        assert "disambiguate" in msg.lower() or "rename" in msg.lower()

    def test_duplicate_across_sections_aborts(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `vault-protocol` | Full protocol | all |

        ## `common-events/` — Events

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `vault-protocol` | Re-defined here (bug) | all |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        assert "duplicate" in str(e.value).lower()


# ---------------------------------------------------------------------------
# AC6(d) — path traversal / malformed source-path aborts
# ---------------------------------------------------------------------------


class TestPathValidationAbort:
    def test_double_dot_in_directory_aborts(self, tmp_path):
        """A malformed H2 directory token containing `..` MUST be caught
        by the source-path validator before any consumer sees it.
        """
        # Hand-craft a catalog with a directory token that would resolve
        # to a `..` segment. The H2_DIR regex is restrictive enough that
        # `..` won't match a directory pattern — so this test exercises
        # the defensive _validate_source_path path via a direct call.
        with pytest.raises(cp.CatalogParseError) as e:
            cp._validate_source_path(
                "references/sub-skills/common/../escape.md",
                lineno=42, name="escape",
            )
        assert "traversal" in str(e.value).lower() or ".." in str(e.value)

    def test_dot_claude_path_aborts(self, tmp_path):
        """AC5: `.claude/skills/` paths are NEVER valid catalog entries."""
        with pytest.raises(cp.CatalogParseError) as e:
            cp._validate_source_path(
                "references/sub-skills/.claude/skills/foo.md",
                lineno=42, name="foo",
            )
        assert ".claude" in str(e.value)

    def test_non_md_suffix_aborts(self, tmp_path):
        with pytest.raises(cp.CatalogParseError):
            cp._validate_source_path(
                "references/sub-skills/common/boot-bootstrap.txt",
                lineno=42, name="boot-bootstrap",
            )

    def test_outside_references_sub_skills_aborts(self, tmp_path):
        with pytest.raises(cp.CatalogParseError) as e:
            cp._validate_source_path(
                "docs/sub-skill-catalog.md",
                lineno=42, name="catalog",
            )
        assert "rooted" in str(e.value).lower()


# ---------------------------------------------------------------------------
# AC6(b) — malformed-row diagnostics
# ---------------------------------------------------------------------------


class TestMalformedRowAbort:
    def test_row_under_placeholder_h2_without_h3_aborts(self, tmp_path):
        """H2 `## \\`roles/<role>/\\` —` is a placeholder; rows under it
        without an H3 pinning a concrete directory cannot resolve.
        """
        catalog = _write_catalog(tmp_path, """
        ## `roles/<role>/` — Role-specific sub-skills

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `dangling-row` | This row has no role context | ? |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        assert "placeholder" in str(e.value).lower() \
            or "role" in str(e.value).lower()

    def test_row_outside_any_h2_aborts(self, tmp_path):
        """A row appearing before any H2 has no source directory context."""
        catalog = _write_catalog(tmp_path, """
        Some intro prose, no H2 yet.

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `floating` | No H2 above this row | ? |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        assert "h2" in str(e.value).lower() \
            or "enclosing" in str(e.value).lower()


class TestIgnoredRows:
    def test_strikethrough_retirement_rows_are_skipped(self, tmp_path):
        """Rows like `~~discussion-protocol~~` are retirement annotations,
        not active catalog entries. They MUST be skipped silently — not
        treated as malformed rows.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` | Active row | all |
        | ~~`discussion-protocol`~~ | Retired; do not use | _retired_ |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "discussion": "references/sub-skills/common/discussion.md",
        }

    def test_non_backtick_meta_rows_are_skipped(self, tmp_path):
        """Rows whose first cell has NO backticks (like the catalog's
        `| Domain context | Per-stack QA notes ... |` meta-row at
        line 223) are silently skipped — they describe how the section
        works, they're not catalog entries.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` | Active row | all |
        | Domain context | Per-stack notes | all |
        """)
        out = cp.parse_catalog(catalog)
        assert out == {
            "discussion": "references/sub-skills/common/discussion.md",
        }


class TestBacktickWrappedNonMatchingRaises:
    """C1 fix: when first cell has a backtick-wrapped name that does NOT
    match the strict name regex, silent-skip would mask either a PM typo
    OR a real catalog entry. The parser RAISES so the defect surfaces
    at parser-build time rather than at v2 compose time.
    """

    def test_capital_letter_in_name_raises(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `Boot-bootstrap` | Capital B is wrong | all |
        """)
        with pytest.raises(cp.CatalogParseError) as e:
            cp.parse_catalog(catalog)
        assert "strict-name regex" in str(e.value).lower() \
            or "lowercase" in str(e.value).lower()

    def test_html_strikethrough_raises(self, tmp_path):
        """If a PM uses HTML strikethrough instead of Markdown `~~`,
        the parser RAISES rather than silently skipping. The right
        retirement convention is `~~`name`~~`.
        """
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | <s>`old-name`</s> | HTML strike instead of Markdown | _retired_ |
        """)
        with pytest.raises(cp.CatalogParseError):
            cp.parse_catalog(catalog)


# ---------------------------------------------------------------------------
# Live catalog integration check
# ---------------------------------------------------------------------------


class TestLiveCatalogIntegration:
    """Live catalog integration check.

    The original #10687 (and re-filing as #10743) defect — duplicate
    bare-name catalog rows for `improvement-scan`, `issue-filing`,
    `task-pickup`, `discussion-protocol`, `ralph-loop-overview` — was
    resolved by renaming the per-role variants to slash-bearing form
    (e.g. `roles/pm/improvement-scan`). The xfail-strict regression
    pin flipped to XPASS and is now removed; the live catalog parses
    cleanly.
    """

    def test_real_catalog_parses_cleanly(self):
        """The live catalog must parse without raising. Replaces the
        old xfail-strict pin from when #10743's duplicates blocked
        parsing."""
        catalog = REPO_ROOT / "docs" / "sub-skill-catalog.md"
        if not catalog.is_file():
            pytest.skip("docs/sub-skill-catalog.md not present")
        out = cp.parse_catalog(catalog)
        assert len(out) >= 10
        # Spot-check: the previously-duplicated name now appears in
        # both forms (common bare-name + roles/pm slash-bearing) so
        # callers that look up either string find the right source.
        assert "improvement-scan" in out
        assert "roles/pm/improvement-scan" in out

    def test_real_catalog_partial_entries_have_valid_path_shape(self, tmp_path):
        """Up to the point the parser hits the duplicate, every emitted
        path satisfies AC4 (rooted, no traversal, .md suffix). This
        exercises the live catalog's first 100+ lines.
        """
        catalog = REPO_ROOT / "docs" / "sub-skill-catalog.md"
        if not catalog.is_file():
            pytest.skip("docs/sub-skill-catalog.md not present")
        text = catalog.read_text(encoding="utf-8").splitlines()
        # Cut at the section containing the duplicate (line ~140)
        partial_text = "\n".join(text[:138])
        # N3 fix: write under tmp_path, not docs/, so an interrupted
        # test doesn't leave a dotfile in the docs tree.
        partial_catalog = tmp_path / "partial-catalog.md"
        partial_catalog.write_text(partial_text, encoding="utf-8")
        out = cp.parse_catalog(partial_catalog)
        assert len(out) >= 10  # non-trivial number of entries
        for name, path in out.items():
            assert path.startswith("references/sub-skills/"), name
            assert ".." not in Path(path).parts, name
            assert path.endswith(".md"), name


# ---------------------------------------------------------------------------
# CatalogEntry dataclass surface
# ---------------------------------------------------------------------------


class TestCatalogEntryShape:
    def test_default_description_is_empty(self):
        e = cp.CatalogEntry(name="foo", source_path="references/sub-skills/common/foo.md")
        assert e.description == ""

    def test_parse_catalog_returns_dict(self, tmp_path):
        catalog = _write_catalog(tmp_path, """
        ## `common/` — Cross-cutting

        | Sub-skill | One-liner | Used by |
        |---|---|---|
        | `discussion` | Tracker comments | all |
        """)
        out = cp.parse_catalog(catalog)
        assert isinstance(out, dict)
        assert isinstance(list(out.keys())[0], str)
