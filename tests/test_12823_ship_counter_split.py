"""#12823 — split the ship counter out of config.md into .ship-counter.

config.md carried `merge=ours` ONLY to protect the DM ship counter from
regression, but ours-wins is all-or-nothing and silently dropped every other
agent's concurrent config.md edit. The counter now lives in its own
`.ship-counter` file (merge=ours), so config.md merges 3-way normally. These
tests lock the storage redirect (read/write/migration/default) and the
.gitattributes split.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config  # noqa: E402

_CONFIG_WITH_COUNTER = (
    "## Auto Versioning\n\n"
    "- **Ship Threshold**: 10\n"
    "- **Shipped Since Last Bump**: 7\n"
)
_CONFIG_NO_COUNTER = "## Project\n\n- **Name**: Demo\n"


@pytest.fixture
def paths(tmp_path):
    cfg = tmp_path / "config.md"
    counter = tmp_path / ".ship-counter"
    with patch.object(config, "CONFIG_PATH", cfg), \
         patch.object(config, "SHIP_COUNTER_PATH", counter):
        yield cfg, counter


class TestShipCounterStorage:
    def test_get_reads_counter_file(self, paths):
        cfg, counter = paths
        cfg.write_text(_CONFIG_WITH_COUNTER, encoding="utf-8")
        counter.write_text("42\n", encoding="utf-8")
        # File is authoritative even when config.md still carries a (stale) value.
        assert config.get_field("shipped-since-bump") == "42"

    def test_get_falls_back_to_config_md_for_migration(self, paths):
        cfg, counter = paths
        cfg.write_text(_CONFIG_WITH_COUNTER, encoding="utf-8")
        # No .ship-counter yet (pre-#12823 install) -> read the legacy field.
        assert not counter.exists()
        assert config.get_field("shipped-since-bump") == "7"

    def test_get_defaults_to_zero_when_neither_present(self, paths):
        cfg, counter = paths
        cfg.write_text(_CONFIG_NO_COUNTER, encoding="utf-8")
        assert config.get_field("shipped-since-bump") == "0"

    def test_set_writes_counter_file_not_config_md(self, paths):
        cfg, counter = paths
        cfg.write_text(_CONFIG_WITH_COUNTER, encoding="utf-8")
        config.set_field("shipped-since-bump", 9)
        assert counter.read_text(encoding="utf-8").strip() == "9"
        # config.md is NOT rewritten by the counter set (its stale field is left
        # for config.md's normal 3-way merge; the file is authoritative).
        assert "Shipped Since Last Bump**: 7" in cfg.read_text(encoding="utf-8")

    def test_set_then_get_roundtrip(self, paths):
        cfg, counter = paths
        cfg.write_text(_CONFIG_NO_COUNTER, encoding="utf-8")
        config.set_field("shipped-since-bump", 13)
        assert config.get_field("shipped-since-bump") == "13"

    def test_counter_file_authoritative_over_stale_config_md(self, paths):
        cfg, counter = paths
        cfg.write_text(
            "## Auto Versioning\n\n- **Shipped Since Last Bump**: 99\n",
            encoding="utf-8")
        counter.write_text("3\n", encoding="utf-8")
        assert config.get_field("shipped-since-bump") == "3"

    def test_parse_all_overlays_authoritative_counter(self, paths):
        """DS-12823 F1: `dump`/_parse_all must agree with get_field — overlay the
        .ship-counter value, not the stale/absent config.md field."""
        cfg, counter = paths
        cfg.write_text(
            "## Auto Versioning\n\n- **Shipped Since Last Bump**: 99\n",
            encoding="utf-8")
        counter.write_text("4\n", encoding="utf-8")
        parsed = config._parse_all(cfg.read_text(encoding="utf-8"))
        assert parsed["shipped-since-bump"] == "4"
        assert parsed["shipped-since-bump"] == config.get_field("shipped-since-bump")

    def test_parse_all_counter_defaults_to_zero(self, paths):
        cfg, _ = paths
        cfg.write_text(_CONFIG_NO_COUNTER, encoding="utf-8")
        parsed = config._parse_all(cfg.read_text(encoding="utf-8"))
        assert parsed["shipped-since-bump"] == "0"

    def test_other_fields_unaffected_by_redirect(self, paths):
        cfg, _ = paths
        cfg.write_text(_CONFIG_WITH_COUNTER, encoding="utf-8")
        # A non-counter field still reads/writes config.md as before.
        assert config.get_field("ship-threshold") == "10"
        config.set_field("ship-threshold", 20)
        assert config.get_field("ship-threshold") == "20"
        assert not (cfg.parent / ".ship-counter").exists()


class TestGitattributesSplit:
    def test_counter_file_is_merge_ours_and_config_md_is_not(self):
        ga = (Path(__file__).resolve().parent.parent / ".gitattributes")
        text = ga.read_text(encoding="utf-8")
        # The counter file keeps ours-wins protection...
        assert ".squidsquad/.ship-counter merge=ours" in text
        # ...and config.md no longer carries merge=ours (the bug: it dropped
        # concurrent edits). Match the exact rule line, not the explanatory prose.
        rule_lines = [ln.strip() for ln in text.splitlines()
                      if ln.strip().startswith(".squidsquad/config.md")]
        assert all("merge=ours" not in ln for ln in rule_lines), \
            "config.md must not carry merge=ours after #12823"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
