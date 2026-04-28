"""Tests for references/scripts/vault_remember.py — quiet detection, write budget, confidence decay."""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_remember


class TestIsQuiet:
    def test_no_iterations_dir_is_quiet(self, tmp_path):
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path):
            assert vault_remember.is_quiet("skill") is True

    def test_recent_log_is_non_quiet(self, tmp_path):
        iter_dir = tmp_path / "skill" / "iterations"
        iter_dir.mkdir(parents=True)
        (iter_dir / "iter-1.md").write_text("log")
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="30"):
            assert vault_remember.is_quiet("skill") is False

    def test_old_log_is_quiet(self, tmp_path):
        iter_dir = tmp_path / "skill" / "iterations"
        iter_dir.mkdir(parents=True)
        f = iter_dir / "iter-1.md"
        f.write_text("log")
        import os
        old_time = time.time() - 3600  # 1 hour ago
        os.utime(f, (old_time, old_time))
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="30"):
            assert vault_remember.is_quiet("skill") is True


class TestWriteBudget:
    def _setup_ws(self, tmp_path, writes=0):
        ws_dir = tmp_path / "skill"
        ws_dir.mkdir(parents=True)
        ws = ws_dir / "working-state.md"
        ws.write_text(
            f"# Working State\n\n- **Vault Writes This Cycle**: {writes}\n",
            encoding="utf-8",
        )
        return ws

    def test_full_budget(self, tmp_path, capsys):
        self._setup_ws(tmp_path, writes=0)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="2"):
            result = vault_remember.write_budget("skill")
        assert result == 2

    def test_exhausted_budget(self, tmp_path, capsys):
        self._setup_ws(tmp_path, writes=2)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="2"):
            result = vault_remember.write_budget("skill")
        assert result == 0

    def test_partial_budget(self, tmp_path, capsys):
        self._setup_ws(tmp_path, writes=1)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="2"):
            result = vault_remember.write_budget("skill")
        assert result == 1

    def test_no_working_state_full_budget(self, tmp_path, capsys):
        (tmp_path / "skill").mkdir(parents=True)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="2"):
            result = vault_remember.write_budget("skill")
        assert result == 2


class TestIncWrites:
    def test_increments_from_zero(self, tmp_path, capsys):
        ws_dir = tmp_path / "skill"
        ws_dir.mkdir(parents=True)
        ws = ws_dir / "working-state.md"
        ws.write_text("# Working State\n\n- **Vault Writes This Cycle**: 0\n")
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path):
            result = vault_remember.inc_writes("skill")
        assert result == 1
        assert "1" in ws.read_text()

    def test_increments_existing(self, tmp_path, capsys):
        ws_dir = tmp_path / "skill"
        ws_dir.mkdir(parents=True)
        ws = ws_dir / "working-state.md"
        ws.write_text("# Working State\n\n- **Vault Writes This Cycle**: 3\n")
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path):
            result = vault_remember.inc_writes("skill")
        assert result == 4


class TestResetWrites:
    def test_resets_to_zero(self, tmp_path, capsys):
        ws_dir = tmp_path / "skill"
        ws_dir.mkdir(parents=True)
        ws = ws_dir / "working-state.md"
        ws.write_text("# Working State\n\n- **Vault Writes This Cycle**: 5\n")
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path):
            result = vault_remember.reset_writes("skill")
        assert result == 0
        assert "0" in ws.read_text()


class TestBriefingBudget:
    def test_empty_briefing_full_budget(self, tmp_path, capsys):
        with patch.object(vault_remember, "VAULT_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="2000"):
            result = vault_remember.briefing_budget()
        assert result == 2000

    def test_partial_briefing(self, tmp_path, capsys):
        briefing = tmp_path / "BRIEFING.md"
        # ~100 words * 1.3 = ~130 tokens
        briefing.write_text(" ".join(["word"] * 100), encoding="utf-8")
        with patch.object(vault_remember, "VAULT_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="2000"):
            result = vault_remember.briefing_budget()
        assert 1800 < result < 2000


class TestEffectiveConfidence:
    def _make_note(self, tmp_path, confidence="high", updated="2026-04-14", tags=""):
        vault = tmp_path / "vault"
        galaxy = vault / "galaxy"
        galaxy.mkdir(parents=True)
        note = galaxy / "decision-test.md"
        note.write_text(
            f"---\ntype: decision\ntags: {tags}\ncreated: 2026-01-01\n"
            f"updated: {updated}\nowner: skill\nstatus: active\n"
            f"confidence: {confidence}\n---\n\n# Test\n",
            encoding="utf-8",
        )
        return note, vault

    def test_recent_note_no_decay(self, tmp_path, capsys):
        today = datetime.now().strftime("%Y-%m-%d")
        note, vault = self._make_note(tmp_path, confidence="high", updated=today)
        with patch.object(vault_remember, "VAULT_DIR", vault), \
             patch.object(vault_remember, "get_field", return_value="60"):
            result = vault_remember.effective_confidence(str(note))
        assert result == "high"

    def test_old_high_decays_to_medium(self, tmp_path, capsys):
        old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        note, vault = self._make_note(tmp_path, confidence="high", updated=old_date)
        with patch.object(vault_remember, "VAULT_DIR", vault), \
             patch.object(vault_remember, "get_field", return_value="60"):
            result = vault_remember.effective_confidence(str(note))
        assert result == "medium"

    def test_old_medium_decays_to_low(self, tmp_path, capsys):
        old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        note, vault = self._make_note(tmp_path, confidence="medium", updated=old_date)
        with patch.object(vault_remember, "VAULT_DIR", vault), \
             patch.object(vault_remember, "get_field", return_value="60"):
            result = vault_remember.effective_confidence(str(note))
        assert result == "low"

    def test_low_stays_low(self, tmp_path, capsys):
        old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        note, vault = self._make_note(tmp_path, confidence="low", updated=old_date)
        with patch.object(vault_remember, "VAULT_DIR", vault), \
             patch.object(vault_remember, "get_field", return_value="60"):
            result = vault_remember.effective_confidence(str(note))
        assert result == "low"

    def test_evergreen_exempt(self, tmp_path, capsys):
        old_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        note, vault = self._make_note(
            tmp_path, confidence="high", updated=old_date, tags="[evergreen, arch]"
        )
        with patch.object(vault_remember, "VAULT_DIR", vault), \
             patch.object(vault_remember, "get_field", return_value="60"):
            result = vault_remember.effective_confidence(str(note))
        assert result == "high"

    def test_prefix_collision_blocked(self, tmp_path, capsys):
        """Path like /vault-other/note.md must not pass check for /vault."""
        vault = tmp_path / "vault"
        vault.mkdir()
        # Create a sibling directory whose name starts with "vault"
        sibling = tmp_path / "vault-other"
        sibling.mkdir()
        note = sibling / "malicious.md"
        note.write_text(
            "---\ntype: learning\ntags: test\ncreated: 2026-01-01\n"
            "updated: 2026-01-01\nowner: test\nstatus: active\n"
            "confidence: high\nlinks: []\n---\nBody\n"
        )
        with patch.object(vault_remember, "VAULT_DIR", vault), \
             patch.object(vault_remember, "get_field", return_value="60"):
            with pytest.raises(SystemExit) as exc_info:
                vault_remember.effective_confidence(str(note))
            assert exc_info.value.code == 2
