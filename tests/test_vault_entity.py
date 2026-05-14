"""Tests for references/scripts/vault_entity.py — entity extraction from text."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_entity


class TestExtractURLs:
    def test_finds_url(self):
        entities = vault_entity.extract_entities(
            "Check https://figma.com/our-board for designs."
        )
        urls = [e for e in entities if e["type"] == "url"]
        assert len(urls) == 1
        assert "figma.com" in urls[0]["value"]

    def test_multiple_urls(self):
        entities = vault_entity.extract_entities(
            "See https://github.com and https://gitlab.com for repos."
        )
        urls = [e for e in entities if e["type"] == "url"]
        assert len(urls) == 2

    def test_no_duplicate_urls(self):
        entities = vault_entity.extract_entities(
            "Visit https://example.com and also https://example.com again."
        )
        urls = [e for e in entities if e["type"] == "url"]
        assert len(urls) == 1


class TestExtractNames:
    def test_finds_person_name(self):
        entities = vault_entity.extract_entities(
            "Sarah Johnson said the design is ready."
        )
        people = [e for e in entities if e["type"] == "person"]
        assert len(people) >= 1
        assert any("Sarah" in p["value"] for p in people)

    def test_finds_business_name(self):
        entities = vault_entity.extract_entities(
            "We signed a deal with Acme Corp for analytics."
        )
        names = [e for e in entities if e["type"] in ("business", "person")]
        assert any("Acme Corp" in n["value"] for n in names)

    def test_filters_noise_words(self):
        entities = vault_entity.extract_entities(
            "This Monday we have a meeting about the Task."
        )
        # Monday, This, Task should be filtered
        names = [e for e in entities if e["type"] in ("person", "business", "unknown")]
        noise_values = [n["value"] for n in names]
        assert "Monday" not in noise_values
        assert "This Monday" not in noise_values


class TestExtractProjects:
    def test_finds_project_reference(self):
        entities = vault_entity.extract_entities(
            "The project marketplace needs a new feature."
        )
        projects = [e for e in entities if e["type"] == "project"]
        assert len(projects) >= 1
        assert any("marketplace" in p["value"] for p in projects)

    def test_finds_repo_reference(self):
        entities = vault_entity.extract_entities(
            "Check the repo squidsquad-tools for the latest code."
        )
        projects = [e for e in entities if e["type"] == "project"]
        assert len(projects) >= 1


class TestExtractPreferences:
    def test_finds_preference(self):
        entities = vault_entity.extract_entities(
            "Always use kebab-case for file names."
        )
        prefs = [e for e in entities if e["type"] == "preference"]
        assert len(prefs) >= 1
        assert any("kebab-case" in p["value"] for p in prefs)

    def test_finds_negative_preference(self):
        entities = vault_entity.extract_entities(
            "Never use tabs for indentation."
        )
        prefs = [e for e in entities if e["type"] == "preference"]
        assert len(prefs) >= 1, "Expected 'never use' to match PREFERENCE_MARKERS"
        assert any("tabs" in p["value"].lower() for p in prefs)

    def test_finds_convention(self):
        entities = vault_entity.extract_entities(
            "The convention is to prefix all test files with test_."
        )
        prefs = [e for e in entities if e["type"] == "preference"]
        assert len(prefs) >= 1


class TestMixedEntities:
    def test_extracts_multiple_types(self):
        text = (
            "Ask Sarah about the marketplace project. "
            "She uses https://figma.com/our-board for designs. "
            "Always use kebab-case for file names."
        )
        entities = vault_entity.extract_entities(text)
        types = {e["type"] for e in entities}
        assert len(types) >= 3  # person, url, preference at minimum

    def test_empty_text_returns_empty(self):
        entities = vault_entity.extract_entities("")
        assert entities == []

    def test_no_entities_returns_empty(self):
        entities = vault_entity.extract_entities(
            "the quick brown fox jumps over the lazy dog"
        )
        assert entities == []


class TestEntityConfidence:
    def test_urls_are_high_confidence(self):
        entities = vault_entity.extract_entities("Visit https://example.com")
        urls = [e for e in entities if e["type"] == "url"]
        assert urls[0]["confidence"] == "high"

    def test_names_without_person_signal_are_low_confidence(self):
        entities = vault_entity.extract_entities("Talk to John Smith about it.")
        names = [e for e in entities if e["value"] == "John Smith"]
        assert names, "Expected entity for 'John Smith'"
        # Without trailing person signals (said/asked/from/at), classified as unknown
        assert names[0]["type"] == "unknown"
        assert names[0]["confidence"] == "low"


class TestEntityContext:
    def test_includes_surrounding_text(self):
        # Proper name pattern requires 2+ capitalized words; "from" triggers person type
        entities = vault_entity.extract_entities(
            "The feedback from Sarah Chen at the design review was helpful."
        )
        people = [e for e in entities if e["value"] == "Sarah Chen"]
        assert people, "Expected entity for 'Sarah Chen' (2-word proper name with person signal)"
        assert len(people[0]["context"]) > 0


class TestCLI:
    def test_extract_returns_json(self, capsys):
        sys.argv = [
            "vault_entity.py", "extract",
            "Check https://example.com for details."
        ]
        code = vault_entity.main()
        assert code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["count"] >= 1

    def test_no_entities_returns_1(self):
        sys.argv = ["vault_entity.py", "extract", "nothing here"]
        code = vault_entity.main()
        assert code == 1

    def test_no_text_returns_2(self):
        sys.argv = ["vault_entity.py", "extract"]
        code = vault_entity.main()
        assert code == 2


class TestProperNameClassification:
    """#7615: ambiguous proper names should be 'unknown', not 'person'."""

    def test_ambiguous_name_classified_as_unknown(self):
        """A proper name without person or business context = unknown."""
        text = "We evaluated Red Hat for the project."
        entities = vault_entity.extract_entities(text)
        red_hat = [e for e in entities if e["value"] == "Red Hat"]
        if red_hat:
            assert red_hat[0]["type"] == "unknown", \
                f"Ambiguous name should be 'unknown', got '{red_hat[0]['type']}'"
            assert red_hat[0]["confidence"] == "low"
