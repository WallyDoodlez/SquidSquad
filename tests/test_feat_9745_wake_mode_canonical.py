"""Tests for the canonical config.get_wake_mode helper (#9745).

Before #9745 wake-mode resolution was duplicated across compose.py,
cycle_post.py, and statusline_data.py with subtly different stderr-handling.
#9745 consolidates the logic into config.get_wake_mode and reduces the
duplicates to thin delegating wrappers. These tests cover:

- The canonical helper's resolution rules + stderr suppression.
- Each of the 3 wrapper sites delegates to the canonical helper.
- The bootstrap.md prose still describes the same precedence.
"""

import io
import sys
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config


# ---------------------------------------------------------------------------
# Canonical helper
# ---------------------------------------------------------------------------

class TestGetWakeMode:
    """config.get_wake_mode is the single source of truth."""

    def test_returns_event_driven_when_per_role_yes(self, monkeypatch):
        monkeypatch.setattr(config, "get_field", lambda f: "yes" if f == "event-driven-skill" else None)
        assert config.get_wake_mode("skill") == "event-driven"

    def test_returns_event_driven_when_global_yes(self, monkeypatch):
        monkeypatch.setattr(config, "get_field", lambda f: "yes" if f == "event-driven" else "")
        assert config.get_wake_mode("skill") == "event-driven"

    def test_per_role_overrides_global(self, monkeypatch):
        """Per-role value beats global."""
        def gf(f):
            return {"event-driven-skill": "no", "event-driven": "yes"}.get(f, "")
        monkeypatch.setattr(config, "get_field", gf)
        assert config.get_wake_mode("skill") == "polling"

    def test_per_role_true_variants(self, monkeypatch):
        for val in ("yes", "true", "1", "event-driven", "YES", "True", "EVENT-DRIVEN"):
            monkeypatch.setattr(config, "get_field", lambda f, v=val: v if f == "event-driven-pm" else "")
            assert config.get_wake_mode("pm") == "event-driven", f"value {val!r} should resolve to event-driven"

    def test_per_role_polling_variants(self, monkeypatch):
        for val in ("no", "false", "0", "polling", "POLLING"):
            monkeypatch.setattr(config, "get_field", lambda f, v=val: v if f == "event-driven-pm" else "")
            assert config.get_wake_mode("pm") == "polling", f"value {val!r} should resolve to polling"

    def test_defaults_to_polling_when_both_fields_missing(self, monkeypatch):
        """get_field raises SystemExit on missing field; helper catches and falls back."""
        def gf(f):
            print(f"ERROR: Field '{f}' not found in config.md", file=sys.stderr)
            raise SystemExit(1)
        monkeypatch.setattr(config, "get_field", gf)
        assert config.get_wake_mode("skill") == "polling"

    def test_stderr_suppressed_on_missing_fields(self, monkeypatch, capsys):
        """#8697 R3 regression: spurious ERROR output during normal probing is suppressed."""
        def gf(f):
            print(f"ERROR: Field '{f}' not found in config.md", file=sys.stderr)
            raise SystemExit(1)
        monkeypatch.setattr(config, "get_field", gf)
        config.get_wake_mode("skill")
        # Caller-observable stderr must be clean.
        assert capsys.readouterr().err == ""

    def test_tolerates_oserror_from_config_read(self, monkeypatch):
        """A TOCTOU race on config.md must not crash callers."""
        def gf(f):
            raise OSError("config.md vanished mid-read")
        monkeypatch.setattr(config, "get_field", gf)
        assert config.get_wake_mode("skill") == "polling"

    def test_unrecognized_value_falls_through_to_global(self, monkeypatch):
        """Per-role with garbage value falls through to global."""
        def gf(f):
            return {"event-driven-skill": "maybe", "event-driven": "yes"}.get(f, "")
        monkeypatch.setattr(config, "get_field", gf)
        assert config.get_wake_mode("skill") == "event-driven"

    def test_unrecognized_global_falls_through_to_polling(self, monkeypatch):
        def gf(f):
            return "garbage"
        monkeypatch.setattr(config, "get_field", gf)
        assert config.get_wake_mode("skill") == "polling"


# ---------------------------------------------------------------------------
# Delegation: 3 wrappers must call config.get_wake_mode
# ---------------------------------------------------------------------------

class TestWrappersDelegate:
    """compose / cycle_post / statusline_data delegate to config.get_wake_mode."""

    def _import_module(self, name):
        # Fresh import — these modules sit next to config.py on sys.path
        sys.modules.pop(name, None)
        return __import__(name)

    def test_compose_delegates(self, monkeypatch):
        compose = self._import_module("compose")
        called_with = []

        def fake_get_wake_mode(role):
            called_with.append(role)
            return "event-driven"

        monkeypatch.setattr(config, "get_wake_mode", fake_get_wake_mode)
        # Reimport compose so it picks up the patched config.get_wake_mode
        # via its `from config import get_wake_mode` lazy import.
        assert compose._get_wake_mode("skill") == "event-driven"
        assert called_with == ["skill"]

    def test_cycle_post_delegates(self, monkeypatch):
        cycle_post = self._import_module("cycle_post")
        called_with = []
        monkeypatch.setattr(config, "get_wake_mode", lambda r: called_with.append(r) or "polling")
        assert cycle_post._get_role_wake_mode("qa") == "polling"
        assert called_with == ["qa"]

    def test_statusline_data_delegates(self, monkeypatch):
        statusline_data = self._import_module("statusline_data")
        called_with = []
        monkeypatch.setattr(config, "get_wake_mode", lambda r: called_with.append(r) or "event-driven")
        assert statusline_data._get_wake_mode("dm") == "event-driven"
        assert called_with == ["dm"]


# ---------------------------------------------------------------------------
# Bootstrap prose audit
# ---------------------------------------------------------------------------

class TestBootstrapProseAudit:
    """boot-bootstrap.md Step 1 must still describe the canonical precedence."""

    BOOTSTRAP = Path(__file__).resolve().parent.parent / "references" / "sub-skills" / "common" / "boot-bootstrap.md"

    def test_bootstrap_exists(self):
        assert self.BOOTSTRAP.exists(), f"{self.BOOTSTRAP} not found"

    def test_bootstrap_mentions_per_role_override(self):
        """Per-role override `event-driven-<role>` must be documented."""
        text = self.BOOTSTRAP.read_text(encoding="utf-8")
        assert "event-driven-skill" in text or "event-driven-<role>" in text or "event-driven-pm" in text or "event-driven-" in text

    def test_bootstrap_mentions_global_default(self):
        """Global `event-driven:` field must be documented."""
        text = self.BOOTSTRAP.read_text(encoding="utf-8")
        assert "event-driven:" in text or "`event-driven`" in text

    def test_bootstrap_mentions_polling_fallback(self):
        """Polling fallback when neither field is set must be documented."""
        text = self.BOOTSTRAP.read_text(encoding="utf-8")
        # The bootstrap explicitly says polling is the safe fallback per CONTEXT-9588 D3.
        assert "polling" in text.lower()
