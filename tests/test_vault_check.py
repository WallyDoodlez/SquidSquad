"""Tests for references/scripts/vault_check.py — vault validation and integrity checks."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_check


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        text = "---\ntype: decision\ntags: [a, b]\ncreated: 2026-01-01\n---\n\n## Content"
        fm = vault_check._parse_frontmatter(text)
        assert fm is not None
        assert fm["type"] == "decision"

    def test_missing_frontmatter(self):
        text = "# No frontmatter here\n\nJust content."
        assert vault_check._parse_frontmatter(text) is None

    def test_incomplete_frontmatter(self):
        text = "---\ntype: decision\n"
        assert vault_check._parse_frontmatter(text) is None

    def test_empty_values(self):
        text = "---\ntype:\ntags: []\n---\n"
        fm = vault_check._parse_frontmatter(text)
        assert fm is not None
        assert fm["type"] == ""


class TestExtractWikilinks:
    def test_extracts_links(self):
        text = "See [[decision-foo]] and [[pattern-bar]]."
        links = vault_check._extract_wikilinks(text)
        assert "decision-foo" in links
        assert "pattern-bar" in links

    def test_no_links(self):
        text = "No links here."
        assert vault_check._extract_wikilinks(text) == []

    def test_nested_brackets_ignored(self):
        text = "[[valid-link]]"
        links = vault_check._extract_wikilinks(text)
        assert links == ["valid-link"]

    def test_pipe_alias_stripped(self):
        """#8200 regression: [[note|alias]] must return 'note', not 'note|alias'."""
        text = "See [[decision-foo|Foo Decision]] for context."
        links = vault_check._extract_wikilinks(text)
        assert links == ["decision-foo"]

    def test_pipe_alias_with_spaces(self):
        """Pipe alias with whitespace around the pipe."""
        text = "[[note-name | Display Name]]"
        links = vault_check._extract_wikilinks(text)
        assert links == ["note-name"]

    def test_mixed_bare_and_aliased(self):
        """Mix of bare wikilinks and aliased ones."""
        text = "[[bare-link]] and [[aliased|Pretty Name]]"
        links = vault_check._extract_wikilinks(text)
        assert links == ["bare-link", "aliased"]


class TestCheckStructure:
    def test_valid_structure(self, tmp_path):
        vault = tmp_path / "vault"
        for d in vault_check.PARAG_DIRS:
            (vault / d).mkdir(parents=True)
        (vault / "BRIEFING.md").write_text("# Briefing")
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_structure()
        assert issues == []

    def test_missing_directory(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "BRIEFING.md").write_text("# Briefing")
        # Only create some dirs
        (vault / "galaxy").mkdir()
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_structure()
        assert len(issues) >= 1
        assert any("Missing PARAG" in i for i in issues)

    def test_missing_briefing(self, tmp_path):
        vault = tmp_path / "vault"
        for d in vault_check.PARAG_DIRS:
            (vault / d).mkdir(parents=True)
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_structure()
        assert any("BRIEFING" in i for i in issues)

    def test_vault_not_exists(self, tmp_path):
        with patch.object(vault_check, "VAULT_DIR", tmp_path / "missing"):
            issues = vault_check.check_structure()
        assert len(issues) == 1
        assert "missing" in issues[0].lower()


class TestCheckFrontmatter:
    def _setup_galaxy(self, tmp_path, notes):
        """Create a galaxy dir with notes. notes = {filename: content}."""
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        for name, content in notes.items():
            (galaxy / name).write_text(content, encoding="utf-8")
        return vault

    def test_valid_note(self, tmp_path):
        vault = self._setup_galaxy(tmp_path, {
            "decision-test.md": (
                "---\ntype: decision\ntags: [test]\ncreated: 2026-01-01\n"
                "updated: 2026-01-01\nowner: skill\nstatus: active\n"
                "confidence: high\nsource: conversation\nlinks: []\n---\n\n## Content"
            ),
        })
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert issues == []

    def test_missing_fields(self, tmp_path):
        vault = self._setup_galaxy(tmp_path, {
            "decision-bad.md": "---\ntype: decision\n---\n\n## Content",
        })
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert len(issues) >= 1
        assert any("missing fields" in i for i in issues)

    def test_invalid_prefix(self, tmp_path):
        vault = self._setup_galaxy(tmp_path, {
            "badprefix-note.md": (
                "---\ntype: decision\ntags: []\ncreated: 2026-01-01\n"
                "updated: 2026-01-01\nowner: skill\nstatus: active\n"
                "confidence: high\nsource: code\nlinks: []\n---\n"
            ),
        })
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert any("invalid prefix" in i for i in issues)

    def test_invalid_confidence(self, tmp_path):
        vault = self._setup_galaxy(tmp_path, {
            "decision-conf.md": (
                "---\ntype: decision\ntags: []\ncreated: 2026-01-01\n"
                "updated: 2026-01-01\nowner: skill\nstatus: active\n"
                "confidence: extreme\nsource: code\nlinks: []\n---\n"
            ),
        })
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert any("invalid confidence" in i for i in issues)

    def test_no_galaxy_dir(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert issues == []


class TestCheckWikilinks:
    def test_valid_links(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text("Links to [[decision-b]]")
        (galaxy / "decision-b.md").write_text("No links")
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_wikilinks()
        assert issues == []

    def test_broken_link(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text("Links to [[nonexistent]]")
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_wikilinks()
        assert len(issues) == 1
        assert "nonexistent" in issues[0]


class TestListOrphans:
    def test_linked_note_not_orphan(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text("Links to [[decision-b]]")
        (galaxy / "decision-b.md").write_text("content")
        with patch.object(vault_check, "VAULT_DIR", vault):
            orphans = vault_check.list_orphans()
        orphan_names = [Path(o).stem for o in orphans]
        assert "decision-b" not in orphan_names

    def test_unlinked_note_is_orphan(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text("no links")
        (galaxy / "decision-b.md").write_text("also no links")
        with patch.object(vault_check, "VAULT_DIR", vault):
            orphans = vault_check.list_orphans()
        assert len(orphans) == 2


class TestSuggestConnections:
    def test_suggests_by_tag_overlap(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text(
            "---\ntags: [architecture, watchdog]\n---\nContent about watchdog",
            encoding="utf-8",
        )
        (galaxy / "decision-b.md").write_text(
            "---\ntags: [architecture, lifecycle]\n---\nContent about lifecycle",
            encoding="utf-8",
        )
        with patch.object(vault_check, "VAULT_DIR", vault):
            suggestions = vault_check.suggest_connections(galaxy / "decision-a.md")
        assert len(suggestions) >= 1
        assert any("decision-b" in s["target"] for s in suggestions)

    def test_no_suggestions_for_unrelated(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text(
            "---\ntags: [frontend]\n---\nContent", encoding="utf-8"
        )
        (galaxy / "decision-b.md").write_text(
            "---\ntags: [backend]\n---\nContent", encoding="utf-8"
        )
        with patch.object(vault_check, "VAULT_DIR", vault):
            suggestions = vault_check.suggest_connections(galaxy / "decision-a.md")
        assert len(suggestions) == 0

    def test_skips_already_linked(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text(
            "---\ntags: [architecture]\n---\nSee [[decision-b]]",
            encoding="utf-8",
        )
        (galaxy / "decision-b.md").write_text(
            "---\ntags: [architecture]\n---\nContent", encoding="utf-8"
        )
        with patch.object(vault_check, "VAULT_DIR", vault):
            suggestions = vault_check.suggest_connections(galaxy / "decision-a.md")
        targets = [s["target"] for s in suggestions]
        assert "decision-b" not in targets


class TestDedupCheck:
    def test_finds_near_duplicate(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-watchdog-supervisor.md").write_text(
            "---\ntags: [architecture, watchdog]\n---\n\nContent"
        )
        with patch.object(vault_check, "VAULT_DIR", vault):
            matches = vault_check.dedup_check("decision-watchdog-new", "architecture,watchdog")
        assert len(matches) >= 1
        assert matches[0][0] >= 30  # at least 30% overlap

    def test_no_match_for_unrelated(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-foo.md").write_text("---\ntags: [unrelated]\n---\n")
        with patch.object(vault_check, "VAULT_DIR", vault):
            matches = vault_check.dedup_check("completely-different", "nothing")
        assert matches == []


class TestParseTagString:
    def test_yaml_list(self):
        assert vault_check._parse_tag_string("[a, b, c]") == {"a", "b", "c"}

    def test_plain_csv(self):
        assert vault_check._parse_tag_string("a, b") == {"a", "b"}

    def test_empty(self):
        assert vault_check._parse_tag_string("") == set()
        assert vault_check._parse_tag_string(None) == set()


class TestValidate:
    def test_passes_on_valid_vault(self, tmp_path):
        vault = tmp_path / "vault"
        for d in vault_check.PARAG_DIRS:
            (vault / d).mkdir(parents=True)
        (vault / "BRIEFING.md").write_text("# Briefing")
        with patch.object(vault_check, "VAULT_DIR", vault):
            result = vault_check.validate()
        assert result is True

    def test_fails_on_missing_structure(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        with patch.object(vault_check, "VAULT_DIR", vault):
            result = vault_check.validate()
        assert result is False
