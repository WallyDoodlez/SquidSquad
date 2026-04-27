"""Tests for #605 — Display issue URL link when agents mention an issue number.

Tests the _expand_issue_refs and _get_repo_url functions in tracker.py.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tracker


class TestExpandIssueRefs:
    """Issue references (#NNN) expanded with full URL."""

    def test_single_reference(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_repo_url",
                            lambda: "https://github.com/WallyDoodlez/SquidSquad")
        result = tracker._expand_issue_refs("Fixed #3495. Status → Pending Test.")
        assert "#3495 (https://github.com/WallyDoodlez/SquidSquad/issues/3495)" in result

    def test_multiple_references(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_repo_url",
                            lambda: "https://github.com/WallyDoodlez/SquidSquad")
        result = tracker._expand_issue_refs("Cross-ref #100, #200, and #300.")
        assert "/issues/100)" in result
        assert "/issues/200)" in result
        assert "/issues/300)" in result

    def test_no_false_positive_hex(self, monkeypatch):
        """Hex codes like #ff0000 should not be expanded."""
        monkeypatch.setattr(tracker, "_get_repo_url",
                            lambda: "https://github.com/WallyDoodlez/SquidSquad")
        result = tracker._expand_issue_refs("Color is #ff0000.")
        # #ff0000 has letters so regex won't match (only digits)
        assert "issues" not in result

    def test_no_expansion_without_repo(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_repo_url", lambda: None)
        text = "Fixed #123."
        assert tracker._expand_issue_refs(text) == text

    def test_already_expanded_not_doubled(self, monkeypatch):
        monkeypatch.setattr(tracker, "_get_repo_url",
                            lambda: "https://github.com/WallyDoodlez/SquidSquad")
        text = "#123 (https://github.com/WallyDoodlez/SquidSquad/issues/123)"
        result = tracker._expand_issue_refs(text)
        # Should not double-expand
        assert result.count("issues/123") == 1

    def test_word_boundary_respected(self, monkeypatch):
        """Issue refs inside URLs or after word chars should not expand."""
        monkeypatch.setattr(tracker, "_get_repo_url",
                            lambda: "https://github.com/WallyDoodlez/SquidSquad")
        # PR#123 — preceded by word char, should not expand
        result = tracker._expand_issue_refs("See PR#123 for details.")
        assert "issues" not in result

    def test_repo_url_normalization(self, monkeypatch):
        """Repo URL without https:// prefix gets normalized."""
        monkeypatch.setattr(tracker, "_get_repo_url",
                            lambda: "https://github.com/WallyDoodlez/SquidSquad")
        result = tracker._expand_issue_refs("See #42.")
        assert "https://github.com/WallyDoodlez/SquidSquad/issues/42" in result


class TestGetRepoUrl:
    """_get_repo_url reads from config.md."""

    def test_returns_url_from_config(self, monkeypatch):
        fake_run = MagicMock()
        fake_run.stdout = "github.com/WallyDoodlez/SquidSquad\n"
        monkeypatch.setattr(tracker.subprocess, "run", lambda *a, **kw: fake_run)
        url = tracker._get_repo_url()
        assert url == "https://github.com/WallyDoodlez/SquidSquad"

    def test_returns_none_on_empty(self, monkeypatch):
        fake_run = MagicMock()
        fake_run.stdout = "\n"
        monkeypatch.setattr(tracker.subprocess, "run", lambda *a, **kw: fake_run)
        url = tracker._get_repo_url()
        assert url is None

    def test_preserves_existing_https(self, monkeypatch):
        fake_run = MagicMock()
        fake_run.stdout = "https://github.com/WallyDoodlez/SquidSquad\n"
        monkeypatch.setattr(tracker.subprocess, "run", lambda *a, **kw: fake_run)
        url = tracker._get_repo_url()
        assert url == "https://github.com/WallyDoodlez/SquidSquad"
