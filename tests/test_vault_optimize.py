"""Tests for references/scripts/vault_optimize.py — fake vault corpus, no real git."""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import vault_optimize


# ---------------------------------------------------------------------------
# Fake vault builder
# ---------------------------------------------------------------------------

def _note(type_="decision", tags="[vault]", status="active", confidence="medium",
          created=None, updated=None, body="", links="[]"):
    """Build a fake vault note with frontmatter."""
    if created is None:
        created = "2026-01-01"
    if updated is None:
        updated = created
    return (
        f"---\n"
        f"type: {type_}\n"
        f"tags: {tags}\n"
        f"created: {created}\n"
        f"updated: {updated}\n"
        f"owner: skill\n"
        f"status: {status}\n"
        f"confidence: {confidence}\n"
        f"links: {links}\n"
        f"---\n\n"
        f"{body}\n\n"
        f"---\n\n### Changelog\n\n- {created} — Created.\n"
    )


@pytest.fixture
def fake_vault(tmp_path):
    """Create a fake vault with 25 notes (above MIN_VAULT_SIZE threshold)."""
    vault = tmp_path / ".squidsquad" / "vault"
    galaxy = vault / "galaxy"
    areas = vault / "areas"
    archives = vault / "archives"
    galaxy.mkdir(parents=True)
    areas.mkdir(parents=True)
    archives.mkdir(parents=True)

    old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    recent_date = datetime.now().strftime("%Y-%m-%d")
    mid_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # Stale + orphan note (should be pruned)
    (galaxy / "decision-old-orphan.md").write_text(
        _note(type_="decision", created="2025-10-01", updated="2025-10-01",
              body="Old orphan decision about caching."),
        encoding="utf-8",
    )

    # Stale but linked note (should NOT be pruned)
    (galaxy / "pattern-linked-old.md").write_text(
        _note(type_="pattern", created="2025-10-01", updated="2025-10-01",
              body="Old pattern that is still referenced."),
        encoding="utf-8",
    )

    # Recent note (should NOT be pruned)
    (galaxy / "decision-recent.md").write_text(
        _note(type_="decision", created=recent_date, updated=recent_date,
              body="Fresh decision. See [[pattern-linked-old]]."),
        encoding="utf-8",
    )

    # Superseded note (should be pruned regardless)
    (galaxy / "learning-superseded.md").write_text(
        _note(type_="learning", status="superseded", created="2025-11-01",
              updated="2025-11-01", body="Superseded learning."),
        encoding="utf-8",
    )

    # Evergreen note with high confidence (should NOT decay)
    (galaxy / "pattern-evergreen.md").write_text(
        _note(type_="pattern", tags="[vault, evergreen]", confidence="high",
              created=old_date, updated=old_date, body="Evergreen pattern."),
        encoding="utf-8",
    )

    # High confidence stale note (should decay to medium)
    (galaxy / "decision-stale-high.md").write_text(
        _note(type_="decision", confidence="high",
              created=old_date, updated=old_date, body="Stale high confidence."),
        encoding="utf-8",
    )

    # Two similar notes for consolidation
    (galaxy / "pattern-error-handling.md").write_text(
        _note(type_="pattern", created=mid_date, updated=mid_date,
              body="Error handling pattern for retry logic with exponential backoff and timeout management."),
        encoding="utf-8",
    )
    (galaxy / "pattern-retry-logic.md").write_text(
        _note(type_="pattern", created=mid_date, updated=mid_date,
              body="Retry logic pattern with exponential backoff for error handling and timeout configuration."),
        encoding="utf-8",
    )

    # Note created today (grace period — should NOT be pruned)
    (galaxy / "decision-today.md").write_text(
        _note(type_="decision", created=recent_date, updated=recent_date,
              status="active", body="Created today."),
        encoding="utf-8",
    )

    # Area note (should never be pruned)
    (areas / "human-profile.md").write_text(
        _note(type_="area", created="2025-09-01", updated=old_date,
              body="Human preferences."),
        encoding="utf-8",
    )

    # Pad with filler notes to reach 25
    for i in range(15):
        (galaxy / f"filler-{i:02d}.md").write_text(
            _note(type_="pattern", created=mid_date, updated=mid_date,
                  body=f"Filler note {i} with unique content about topic-{i}."),
            encoding="utf-8",
        )

    # Config
    config = tmp_path / ".squidsquad" / "config.md"
    config.write_text(
        "# SquidSquad Config\n\n## Vault Optimize\n\n- **Enabled**: yes\n",
        encoding="utf-8",
    )

    return vault


@pytest.fixture
def patched_vault(fake_vault, monkeypatch):
    """Patch vault_optimize module globals to use fake vault."""
    monkeypatch.setattr(vault_optimize, "VAULT_DIR", fake_vault)
    monkeypatch.setattr(vault_optimize, "PENDING_FILE", fake_vault / ".pending-questions")
    monkeypatch.setattr(vault_optimize, "RELEVANCE_FILE", fake_vault / ".relevance-index.json")
    monkeypatch.setattr(vault_optimize, "LOCK_FILE", fake_vault / ".optimize-lock")
    monkeypatch.setattr(vault_optimize, "CONFIG_PATH", fake_vault.parent / "config.md")
    return fake_vault


# ---------------------------------------------------------------------------
# Prune tests
# ---------------------------------------------------------------------------

class TestPrune:
    def test_prune_dry_run_identifies_stale_orphan(self, patched_vault):
        results = vault_optimize.prune(dry_run=True)
        names = " ".join(results)
        assert "decision-old-orphan" in names

    def test_prune_dry_run_skips_linked_note(self, patched_vault):
        results = vault_optimize.prune(dry_run=True)
        names = " ".join(results)
        assert "pattern-linked-old" not in names

    def test_prune_dry_run_skips_recent_note(self, patched_vault):
        results = vault_optimize.prune(dry_run=True)
        names = " ".join(results)
        assert "decision-recent" not in names

    def test_prune_dry_run_identifies_superseded(self, patched_vault):
        results = vault_optimize.prune(dry_run=True)
        names = " ".join(results)
        assert "learning-superseded" in names

    def test_prune_dry_run_skips_area_notes(self, patched_vault):
        results = vault_optimize.prune(dry_run=True)
        names = " ".join(results)
        assert "human-profile" not in names

    def test_prune_dry_run_skips_today_grace_period(self, patched_vault):
        results = vault_optimize.prune(dry_run=True)
        names = " ".join(results)
        assert "decision-today" not in names


# ---------------------------------------------------------------------------
# Decay tests
# ---------------------------------------------------------------------------

class TestDecay:
    def test_decay_dry_run_identifies_stale_high(self, patched_vault):
        results = vault_optimize.decay(dry_run=True)
        names = " ".join(results)
        assert "decision-stale-high" in names
        assert "high -> medium" in names

    def test_decay_skips_evergreen(self, patched_vault):
        results = vault_optimize.decay(dry_run=True)
        names = " ".join(results)
        assert "pattern-evergreen" not in names

    def test_decay_applies_and_appends_changelog(self, patched_vault):
        results = vault_optimize.decay(dry_run=False)
        assert any("decision-stale-high" in r for r in results)
        # Verify the file was updated
        path = patched_vault / "galaxy" / "decision-stale-high.md"
        text = path.read_text(encoding="utf-8")
        assert "confidence: medium" in text
        assert "Confidence decayed by vault-optimize" in text


# ---------------------------------------------------------------------------
# Consolidate tests
# ---------------------------------------------------------------------------

class TestConsolidateScan:
    def test_detects_similar_notes(self, patched_vault):
        results = vault_optimize.consolidate_scan(dry_run=True)
        # The error-handling and retry-logic notes should overlap
        assert len(results) >= 1
        pair_names = " ".join(
            r["note_a"] + " " + r["note_b"] for r in results
        )
        assert "error-handling" in pair_names or "retry-logic" in pair_names

    def test_writes_pending_question(self, patched_vault):
        vault_optimize.consolidate_scan(dry_run=False)
        pf = patched_vault / ".pending-questions"
        assert pf.exists()
        text = pf.read_text(encoding="utf-8")
        assert "consolidation" in text.lower() or "merge" in text.lower()


# ---------------------------------------------------------------------------
# Reindex tests
# ---------------------------------------------------------------------------

class TestReindex:
    def test_reindex_updates_links(self, patched_vault):
        results = vault_optimize.reindex()
        # decision-recent links to pattern-linked-old
        assert any("decision-recent" in r for r in results)

    def test_reindex_adds_missing_links_field(self, patched_vault):
        # Write a note WITHOUT links field
        no_links = (
            "---\ntype: decision\ntags: [test]\ncreated: 2026-01-01\n"
            "updated: 2026-01-01\nowner: skill\nstatus: active\n"
            "confidence: medium\n---\n\nBody with [[decision-recent]].\n"
        )
        (patched_vault / "galaxy" / "no-links-note.md").write_text(
            no_links, encoding="utf-8"
        )
        results = vault_optimize.reindex()
        text = (patched_vault / "galaxy" / "no-links-note.md").read_text(encoding="utf-8")
        assert "links:" in text
        assert "decision-recent" in text


# ---------------------------------------------------------------------------
# Relevance tests
# ---------------------------------------------------------------------------

class TestRelevance:
    def test_relevance_produces_scores(self, patched_vault):
        scores = vault_optimize.relevance()
        assert len(scores) > 0
        # Each entry should have score, links, recency, confidence
        for rel, data in scores.items():
            assert "score" in data
            assert "links" in data
            assert "recency" in data
            assert "confidence" in data

    def test_relevance_writes_index_file(self, patched_vault):
        vault_optimize.relevance()
        idx = patched_vault / ".relevance-index.json"
        assert idx.exists()
        data = json.loads(idx.read_text(encoding="utf-8"))
        assert len(data) > 0


# ---------------------------------------------------------------------------
# Pending questions
# ---------------------------------------------------------------------------

class TestPendingQuestions:
    def test_pending_count_empty(self, patched_vault):
        assert vault_optimize.pending_count() == 0

    def test_add_and_count(self, patched_vault):
        vault_optimize.add_question("skill", "galaxy/test.md", "Merge these?")
        assert vault_optimize.pending_count() == 1
        vault_optimize.add_question("skill", "galaxy/test2.md", "Archive this?")
        assert vault_optimize.pending_count() == 2


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

class TestGuards:
    def test_config_disabled(self, patched_vault):
        config = patched_vault.parent / "config.md"
        config.write_text(
            "# SquidSquad Config\n\n## Vault Optimize\n\n- **Enabled**: no\n",
            encoding="utf-8",
        )
        ok, reason = vault_optimize._check_guards()
        assert not ok
        assert "disabled" in reason

    def test_vault_too_small(self, tmp_path, monkeypatch):
        small_vault = tmp_path / ".squidsquad" / "vault" / "galaxy"
        small_vault.mkdir(parents=True)
        (small_vault / "one.md").write_text("---\ntype: decision\n---\n", encoding="utf-8")
        monkeypatch.setattr(vault_optimize, "VAULT_DIR", tmp_path / ".squidsquad" / "vault")
        monkeypatch.setattr(vault_optimize, "CONFIG_PATH", tmp_path / "nope.md")
        monkeypatch.setattr(vault_optimize, "LOCK_FILE", tmp_path / "lock")
        ok, reason = vault_optimize._check_guards()
        assert not ok
        assert "too small" in reason

    def test_lock_prevents_concurrent(self, patched_vault):
        # Acquire lock manually
        lock = patched_vault / ".optimize-lock"
        lock.write_text(str(99999), encoding="utf-8")
        ok, reason = vault_optimize._check_guards()
        assert not ok
        assert "lock" in reason


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_parse_frontmatter(self):
        text = "---\ntype: decision\ntags: [a, b]\n---\n\nBody."
        fm = vault_optimize._parse_frontmatter(text)
        assert fm["type"] == "decision"
        assert "a, b" in fm["tags"]

    def test_extract_wikilinks(self):
        text = "---\nlinks: []\n---\n\nSee [[note-a]] and [[note-b]]."
        links = vault_optimize._extract_wikilinks(text)
        assert links == {"note-a", "note-b"}

    def test_extract_wikilinks_skips_frontmatter(self):
        text = "---\nlinks: [note-in-fm]\n---\n\nBody with [[real-link]]."
        links = vault_optimize._extract_wikilinks(text)
        assert "real-link" in links
        assert "note-in-fm" not in links

    def test_extract_keywords(self):
        text = "---\ntype: x\n---\n\nError handling with retry logic and backoff."
        kw = vault_optimize._extract_keywords(text)
        assert "error" in kw
        assert "handling" in kw
        assert "retry" in kw
        assert "logic" in kw
        # Short words excluded
        assert "and" not in kw
