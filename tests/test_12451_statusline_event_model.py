"""S1 tests for #12451 — status bar event-model support.

Covers the dependency-free statusline_data.py surface:
- AC4: the explicit `inline` current-state marker is surfaced as a distinct
  labelled state, taking precedence over a stale harness phase (folds #12854's
  lingering-content case for the inline window).
- AC2/AC5: an idle event-mode agent is rendered from the live harness phase,
  not a stale current-state file — no file-age staleness verdict here.
- AC1: wake mode (event vs loop) is reported for the statusline.

S2 (#12854 write-on-transition discipline) and S3 (loop-mode regression) land
in their own commits per the #12451 work-contract.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import statusline_data


def _write_state(tmp_path, role, content):
    (tmp_path / role).mkdir(parents=True, exist_ok=True)
    (tmp_path / role / "current-state").write_text(content, encoding="utf-8")


class TestInlineMarkerDetection:
    def test_bare_inline_marker(self):
        assert statusline_data._is_inline_marker("inline|")

    def test_inline_with_desc(self):
        assert statusline_data._is_inline_marker("inline|operator session")

    def test_inline_case_insensitive(self):
        assert statusline_data._is_inline_marker("INLINE|")

    def test_non_inline_phase(self):
        assert not statusline_data._is_inline_marker("implementing|#42")

    def test_empty_line(self):
        assert not statusline_data._is_inline_marker("")

    def test_inline_substring_is_not_a_marker(self):
        # only the phase token (before the first |) counts
        assert not statusline_data._is_inline_marker("reviewing|inline edit")


class TestInlinePrecedence:
    """#12451 AC4: the inline marker wins over a stale harness phase, either mode."""

    def test_inline_beats_stale_harness_phase_event_mode(self, tmp_path, capsys):
        _write_state(tmp_path, "pm", "inline|")
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get",
                          return_value={"current_phase": "implementing",
                                        "intent": "running"}) as mock_get:
            rc = statusline_data.cmd_phase("pm")
        assert rc == 0
        # bare marker → clearly-labelled operator-session state
        assert capsys.readouterr().out.strip() == "inline|operator session"
        # inline short-circuits before any harness query
        mock_get.assert_not_called()

    def test_inline_preserves_custom_description(self, tmp_path, capsys):
        _write_state(tmp_path, "pm", "inline|chatting with operator")
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get",
                          return_value={"current_phase": "x", "intent": "running"}):
            statusline_data.cmd_phase("pm")
        assert capsys.readouterr().out.strip() == "inline|chatting with operator"

    def test_inline_surfaced_in_polling_mode(self, tmp_path, capsys):
        _write_state(tmp_path, "pm", "inline|")
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="polling"), \
             patch.object(statusline_data, "_harness_get") as mock_get:
            statusline_data.cmd_phase("pm")
        assert capsys.readouterr().out.strip() == "inline|operator session"
        mock_get.assert_not_called()


class TestEventModeNoFileAgeVerdict:
    """#12451 AC2/AC5: idle event agent rendered from the live harness phase,
    never from a stale current-state file (no file-age staleness verdict)."""

    def test_event_mode_uses_harness_not_stale_file(self, tmp_path, capsys):
        _write_state(tmp_path, "skill", "implementing|#999 (long done)")
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get",
                          return_value={"current_phase": "idle", "intent": "running"}):
            statusline_data.cmd_phase("skill")
        # live harness 'idle' wins; stale file content is NOT surfaced
        assert capsys.readouterr().out.strip() == "idle|"

    def test_event_mode_falls_back_to_file_when_harness_down(self, tmp_path, capsys):
        _write_state(tmp_path, "skill", "implementing|#42")
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get", return_value=None):
            statusline_data.cmd_phase("skill")
        # harness unreachable → file fallback so the line doesn't go blank
        assert capsys.readouterr().out.strip() == "implementing|#42"


class TestCmdModeVisible:
    """#12451 AC1: wake mode (event vs loop) is reported for the statusline."""

    def test_event_mode_reported(self, capsys):
        with patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"):
            rc = statusline_data.cmd_mode("skill")
        assert rc == 0
        assert capsys.readouterr().out.strip() == "event-driven"

    def test_polling_mode_reported(self, capsys):
        with patch.object(statusline_data, "_get_wake_mode", return_value="polling"):
            statusline_data.cmd_mode("pm")
        assert capsys.readouterr().out.strip() == "polling"
