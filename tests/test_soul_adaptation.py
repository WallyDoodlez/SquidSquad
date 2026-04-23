"""Tests for references/scripts/soul_adaptation.py — project-adaptive souls (#361)."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import soul_adaptation


@pytest.fixture
def squid_dir(tmp_path):
    squid = tmp_path / ".squidsquad"
    (squid / "skill").mkdir(parents=True)
    (squid / "vault" / "areas").mkdir(parents=True)
    return squid


@pytest.fixture
def patch_dirs(squid_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(soul_adaptation, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(soul_adaptation, "SQUID_DIR", squid_dir)
    monkeypatch.setattr(soul_adaptation, "VAULT_DIR", squid_dir / "vault")
    monkeypatch.setattr(soul_adaptation, "ADAPTATIONS_FILE",
                        squid_dir / "vault" / "areas" / "role-adaptations.md")
    return tmp_path


class TestAddAdaptation:
    def test_creates_file_if_missing(self, patch_dirs, squid_dir):
        soul_adaptation.add_adaptation("skill", "tech-stack", "Uses Python 3.12 + pytest")
        assert (squid_dir / "vault" / "areas" / "role-adaptations.md").exists()

    def test_adds_entry(self, patch_dirs):
        soul_adaptation.add_adaptation("skill", "tech-stack", "Uses FastAPI", source_task="42")
        entries = soul_adaptation.get_adaptations("skill")
        assert len(entries) == 1
        assert entries[0]["category"] == "tech-stack"
        assert "FastAPI" in entries[0]["signal"]
        assert entries[0]["source_task"] == "42"

    def test_multiple_entries(self, patch_dirs):
        soul_adaptation.add_adaptation("skill", "tech-stack", "Python 3.12")
        soul_adaptation.add_adaptation("skill", "domain-vocabulary", "REST APIs for fintech")
        entries = soul_adaptation.get_adaptations("skill")
        assert len(entries) == 2

    def test_multiple_roles(self, patch_dirs):
        soul_adaptation.add_adaptation("skill", "tech-stack", "Python")
        soul_adaptation.add_adaptation("pm", "user-persona", "Enterprise B2B users")
        assert len(soul_adaptation.get_adaptations("skill")) == 1
        assert len(soul_adaptation.get_adaptations("pm")) == 1


class TestRenderSection:
    def test_empty_adaptations(self, patch_dirs):
        section = soul_adaptation.render_adaptation_section("skill")
        assert "No project-specific adaptations" in section
        assert soul_adaptation.ADAPTATION_HEADER in section

    def test_with_entries(self, patch_dirs):
        soul_adaptation.add_adaptation("skill", "tech-stack", "Python 3.12")
        soul_adaptation.add_adaptation("skill", "quality-preference", "100% test coverage required")
        section = soul_adaptation.render_adaptation_section("skill")
        assert "Python 3.12" in section
        assert "100% test coverage" in section
        assert "**tech-stack**:" in section
        assert "**quality-preference**:" in section


class TestRenderSoul:
    def test_appends_when_no_section_exists(self, patch_dirs, squid_dir):
        soul_path = squid_dir / "skill" / "SOUL.md"
        soul_path.write_text("## Soul — Dev\n\nExisting content.\n", encoding="utf-8")
        soul_adaptation.add_adaptation("skill", "tech-stack", "Rust + Cargo")
        soul_adaptation.render_soul("skill")
        content = soul_path.read_text(encoding="utf-8")
        assert "Existing content" in content
        assert soul_adaptation.ADAPTATION_HEADER in content
        assert "Rust + Cargo" in content

    def test_replaces_existing_section(self, patch_dirs, squid_dir):
        soul_path = squid_dir / "skill" / "SOUL.md"
        soul_path.write_text(
            "## Soul — Dev\n\nBefore.\n\n"
            f"{soul_adaptation.ADAPTATION_HEADER}\n\nOld content.\n"
            f"{soul_adaptation.ADAPTATION_FOOTER}\n\n"
            "## Other Section\n\nAfter.\n",
            encoding="utf-8",
        )
        soul_adaptation.add_adaptation("skill", "tech-stack", "Go 1.22")
        soul_adaptation.render_soul("skill")
        content = soul_path.read_text(encoding="utf-8")
        assert "Before." in content
        assert "After." in content
        assert "Old content." not in content
        assert "Go 1.22" in content

    def test_preserves_other_sections(self, patch_dirs, squid_dir):
        soul_path = squid_dir / "skill" / "SOUL.md"
        soul_path.write_text(
            "## Soul\n\nIdentity.\n\n### Quality Bar\n\nHigh.\n",
            encoding="utf-8",
        )
        soul_adaptation.render_soul("skill")
        content = soul_path.read_text(encoding="utf-8")
        assert "Identity." in content
        assert "Quality Bar" in content
        assert "High." in content


class TestCheckCap:
    def test_under_cap(self, patch_dirs):
        soul_adaptation.add_adaptation("skill", "tech-stack", "Python")
        count, exceeds = soul_adaptation.check_cap("skill")
        assert not exceeds
        assert count < soul_adaptation.LINE_CAP

    def test_empty_under_cap(self, patch_dirs):
        count, exceeds = soul_adaptation.check_cap("skill")
        assert not exceeds


class TestGetAdaptations:
    def test_empty_file(self, patch_dirs):
        assert soul_adaptation.get_adaptations("skill") == []

    def test_no_file(self, patch_dirs):
        assert soul_adaptation.get_adaptations("skill") == []
