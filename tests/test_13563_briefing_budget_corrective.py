"""Regression test for #13563 — BRIEFING.md had grown to 40KB/~6.7K tokens,
3.3x over its documented ~2000-token budget. The existing gate
(vault-remember.md's "before updating BRIEFING.md" check) only blocked NEW
additions once the budget was exhausted — nothing ever trimmed the file, so
it grew monotonically via its append-only Active Priorities / Recently
Shipped sections.

The fix has two parts:
1. A one-time trim: historical Active Priorities increments and Recently
   Shipped entries graduated to vault/archives/ (verbatim, never deleted),
   following the archives/shipped-pre-2026-05-19.md precedent.
2. A durable process fix: vault-remember.md's every-cycle BRIEFING.md
   staleness check (which already runs un-gated, unlike the write-budget
   gate) now treats budget overage as a must-fix this cycle
   (trim-on-contact), not just a block on new additions.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_remember

VAULT_REMEMBER_MD = REPO_ROOT / "references" / "sub-skills" / "common" / "vault-remember.md"
BRIEFING_MD = REPO_ROOT / ".squidsquad" / "vault" / "BRIEFING.md"
ARCHIVES_DIR = REPO_ROOT / ".squidsquad" / "vault" / "archives"


@pytest.fixture
def vault_remember_text():
    assert VAULT_REMEMBER_MD.exists(), f"vault-remember.md missing: {VAULT_REMEMBER_MD}"
    return VAULT_REMEMBER_MD.read_text(encoding="utf-8")


class TestStalenessCheckTreatsOverageAsMustFix13563:
    def test_token_budget_bullet_present_in_staleness_check(self, vault_remember_text):
        idx = vault_remember_text.index("**BRIEFING.md staleness check**")
        # The staleness-check block ends at the next "If any field is stale" sentence
        end = vault_remember_text.index("If any field is stale", idx)
        section = vault_remember_text[idx:end]
        assert "Token budget" in section
        assert "#13563" in section
        assert "briefing-budget" in section

    def test_must_fix_language_present(self, vault_remember_text):
        idx = vault_remember_text.index("#13563")
        section = vault_remember_text[idx:idx + 800]
        assert "must-fix" in section.lower()

    def test_not_gated_by_write_budget(self, vault_remember_text):
        idx = vault_remember_text.index("#13563")
        section = vault_remember_text[idx:idx + 800]
        assert "not gated by write budget" in section.lower()

    def test_corrective_not_just_new_addition_gate(self, vault_remember_text):
        """The must-fix check is distinct from — and cross-referenced by —
        the pre-existing 'before updating BRIEFING.md' new-addition gate."""
        idx = vault_remember_text.index("#13563")
        section = vault_remember_text[idx:idx + 1200]
        assert "corrective" in section.lower()
        assert "archives" in section.lower()

    def test_existing_new_addition_gate_points_to_the_corrective_step(self, vault_remember_text):
        idx = vault_remember_text.index("**BRIEFING.md updates**")
        section = vault_remember_text[idx:idx + 400]
        assert "trimming first" in section.lower() or "staleness above" in section.lower()
        assert "vault/archives/" in section

    def test_graduation_target_is_archives_not_galaxy(self, vault_remember_text):
        """Pre-existing drift: the new-addition gate said trimmed content
        moves to a 'galaxy note', but the actual precedent (and this fix's
        own archives) puts it in vault/archives/. Fixed on contact."""
        idx = vault_remember_text.index("**BRIEFING.md updates**")
        section = vault_remember_text[idx:idx + 400]
        assert "galaxy note" not in section.lower()


class TestBriefingOneTimeTrim13563:
    def test_briefing_under_budget(self):
        assert BRIEFING_MD.exists()
        remaining = vault_remember.briefing_budget()
        assert remaining > 0, (
            f"BRIEFING.md is still at/over its token budget (remaining={remaining}) "
            "-- the #13563 one-time trim should have brought it under."
        )

    def test_briefing_roughly_fifty_lines(self):
        text = BRIEFING_MD.read_text(encoding="utf-8")
        line_count = len(text.splitlines())
        assert line_count <= 70, (
            f"BRIEFING.md is {line_count} lines -- expected close to the "
            "documented ~50-line target shape after graduation."
        )

    def test_operator_facing_sections_survive(self):
        text = BRIEFING_MD.read_text(encoding="utf-8")
        for heading in (
            "## Active Priorities",
            "## Recently Shipped",
            "## Recent Decisions",
            "## Constraints & Blockers",
            "## Team State",
        ):
            assert heading in text, f"{heading} was dropped, not condensed"

    def test_graduated_content_points_to_archives(self):
        text = BRIEFING_MD.read_text(encoding="utf-8")
        assert "vault/archives/" in text

    def test_archive_files_exist_and_are_referenced(self):
        text = BRIEFING_MD.read_text(encoding="utf-8")
        active_priorities_archive = (
            ARCHIVES_DIR / "briefing-active-priorities-2026-06-15-to-07-17.md"
        )
        shipped_archive = ARCHIVES_DIR / "shipped-2026-05-19-to-2026-06-21.md"
        assert active_priorities_archive.exists()
        assert shipped_archive.exists()
        assert active_priorities_archive.name in text
        assert shipped_archive.name in text

    def test_graduated_content_not_deleted_preserved_verbatim(self):
        """Spot-check: a fact only present in the old (pre-trim) BRIEFING.md
        history is preserved somewhere in the new archive, not lost."""
        archive_text = (
            ARCHIVES_DIR / "briefing-active-priorities-2026-06-15-to-07-17.md"
        ).read_text(encoding="utf-8")
        # #13215 was mentioned only in an older (now-graduated) increment.
        assert "#13215" in archive_text
