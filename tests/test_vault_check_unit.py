"""Tests for references/scripts/vault_check.py — frontmatter, wikilinks, structure, orphans, dedup."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_check


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        text = "---\ntype: decision\ntags: [arch, api]\ncreated: 2026-01-01\nupdated: 2026-01-01\nowner: skill\nstatus: active\nconfidence: high\n---\n\n# Body"
        fm = vault_check._parse_frontmatter(text)
        assert fm is not None
        assert fm["type"] == "decision"
        assert fm["confidence"] == "high"

    def test_missing_frontmatter(self):
        text = "# Just a heading\n\nNo frontmatter here."
        assert vault_check._parse_frontmatter(text) is None

    def test_incomplete_frontmatter(self):
        text = "---\ntype: decision\n"
        assert vault_check._parse_frontmatter(text) is None

    def test_empty_frontmatter(self):
        text = "---\n---\n\nBody"
        fm = vault_check._parse_frontmatter(text)
        assert fm == {}


class TestExtractWikilinks:
    def test_extracts_links(self):
        text = "See [[decision-foo]] and [[pattern-bar]] for details."
        links = vault_check._extract_wikilinks(text)
        assert links == ["decision-foo", "pattern-bar"]

    def test_no_links(self):
        text = "Plain text with no links."
        assert vault_check._extract_wikilinks(text) == []

    def test_nested_brackets_handled(self):
        text = "Link: [[some-note]]"
        assert vault_check._extract_wikilinks(text) == ["some-note"]


class TestParseTagString:
    def test_yaml_list_format(self):
        tags = vault_check._parse_tag_string("[arch, api, rest]")
        assert tags == {"arch", "api", "rest"}

    def test_comma_separated(self):
        tags = vault_check._parse_tag_string("arch, api")
        assert tags == {"arch", "api"}

    def test_empty_string(self):
        assert vault_check._parse_tag_string("") == set()

    def test_none(self):
        assert vault_check._parse_tag_string(None) == set()


class TestStripGalaxyPrefix:
    def test_strips_decision(self):
        assert vault_check._strip_galaxy_prefix("decision use rest") == "use rest"

    def test_strips_pattern(self):
        assert vault_check._strip_galaxy_prefix("pattern error handling") == "error handling"

    def test_no_prefix(self):
        assert vault_check._strip_galaxy_prefix("something else") == "something else"


class TestCheckStructure:
    def test_valid_structure(self, tmp_path):
        vault = tmp_path / "vault"
        for d in vault_check.PARAG_DIRS:
            (vault / d).mkdir(parents=True)
        (vault / "BRIEFING.md").write_text("# Briefing")
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_structure()
        assert issues == []

    def test_missing_dirs(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "BRIEFING.md").write_text("# Briefing")
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_structure()
        assert len(issues) == 5  # all 5 PARAG dirs missing

    def test_missing_vault(self, tmp_path):
        with patch.object(vault_check, "VAULT_DIR", tmp_path / "nonexistent"):
            issues = vault_check.check_structure()
        assert len(issues) == 1
        assert "missing" in issues[0].lower()

    def test_missing_briefing(self, tmp_path):
        vault = tmp_path / "vault"
        for d in vault_check.PARAG_DIRS:
            (vault / d).mkdir(parents=True)
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_structure()
        assert any("BRIEFING" in i for i in issues)


class TestCheckFrontmatter:
    def _setup_galaxy(self, tmp_path, notes):
        """Create galaxy notes. notes is a dict of {filename: text}."""
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        for name, text in notes.items():
            (galaxy / name).write_text(text, encoding="utf-8")
        return vault

    def test_valid_note(self, tmp_path):
        vault = self._setup_galaxy(tmp_path, {
            "decision-use-rest.md": "---\ntype: decision\ntags: [api]\ncreated: 2026-01-01\nupdated: 2026-01-01\nowner: skill\nstatus: active\nconfidence: high\nsource: conversation\n---\n\n# Decision"
        })
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert issues == []

    def test_missing_fields(self, tmp_path):
        vault = self._setup_galaxy(tmp_path, {
            "decision-test.md": "---\ntype: decision\n---\n\n# Test"
        })
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert any("missing fields" in i for i in issues)

    def test_invalid_confidence(self, tmp_path):
        vault = self._setup_galaxy(tmp_path, {
            "decision-test.md": "---\ntype: decision\ntags: [x]\ncreated: 2026-01-01\nupdated: 2026-01-01\nowner: skill\nstatus: active\nconfidence: maybe\nsource: code\n---\n\n# Test"
        })
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert any("invalid confidence" in i for i in issues)

    def test_invalid_prefix(self, tmp_path):
        vault = self._setup_galaxy(tmp_path, {
            "random-note.md": "---\ntype: decision\ntags: [x]\ncreated: 2026-01-01\nupdated: 2026-01-01\nowner: skill\nstatus: active\nconfidence: high\n---\n\n# Test"
        })
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_frontmatter()
        assert any("invalid prefix" in i for i in issues)

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
        (galaxy / "decision-foo.md").write_text("---\ntype: decision\n---\nSee [[pattern-bar]]")
        (galaxy / "pattern-bar.md").write_text("---\ntype: pattern\n---\nContent")
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_wikilinks()
        assert issues == []

    def test_broken_link(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-foo.md").write_text("---\ntype: decision\n---\nSee [[nonexistent-note]]")
        with patch.object(vault_check, "VAULT_DIR", vault):
            issues = vault_check.check_wikilinks()
        assert len(issues) == 1
        assert "nonexistent-note" in issues[0]


class TestListOrphans:
    def test_no_orphans(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text("See [[decision-b]]")
        (galaxy / "decision-b.md").write_text("See [[decision-a]]")
        with patch.object(vault_check, "VAULT_DIR", vault):
            orphans = vault_check.list_orphans()
        assert orphans == []

    def test_orphan_detected(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-a.md").write_text("No links here")
        (galaxy / "decision-b.md").write_text("No links here either")
        with patch.object(vault_check, "VAULT_DIR", vault):
            orphans = vault_check.list_orphans()
        assert len(orphans) == 2

    def test_top_level_files_exempt(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        (vault / "BRIEFING.md").write_text("Top level - not an orphan", encoding="utf-8")
        with patch.object(vault_check, "VAULT_DIR", vault):
            orphans = vault_check.list_orphans()
        assert orphans == []


class TestDedupCheck:
    def test_finds_match(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-use-rest-api.md").write_text("---\ntags: [api, rest]\n---\n# Decision")
        with patch.object(vault_check, "VAULT_DIR", vault):
            matches = vault_check.dedup_check("decision-use-rest", "api")
        assert len(matches) >= 1

    def test_no_match(self, tmp_path):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        (galaxy / "decision-use-rest-api.md").write_text("---\ntags: [api]\n---\n# Decision")
        with patch.object(vault_check, "VAULT_DIR", vault):
            matches = vault_check.dedup_check("completely-unrelated-topic", "zebrafish")
        assert matches == []
