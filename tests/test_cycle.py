"""Tests for references/scripts/cycle.py — timestamps, counters, iteration logs, cleanup."""

import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle


FIXED_NOW = datetime(2026, 4, 13, 14, 30, 45)


class TestTimestamp:
    @patch.object(cycle, "_now", return_value=FIXED_NOW)
    def test_timestamp_format(self, mock_now, capsys):
        result = cycle.timestamp()
        assert result == "2026-04-13 14:30"
        assert capsys.readouterr().out.strip() == "2026-04-13 14:30"

    @patch.object(cycle, "_now", return_value=FIXED_NOW)
    def test_timestamp_short_format(self, mock_now, capsys):
        result = cycle.timestamp_short()
        assert result == "14:30:45"
        assert capsys.readouterr().out.strip() == "14:30:45"


class TestStepMarker:
    @patch.object(cycle, "_now", return_value=FIXED_NOW)
    def test_step_marker_format(self, mock_now, capsys):
        result = cycle.step_marker("Pulling latest...")
        assert "[🦑 14:30:45]" in result
        assert "Pulling latest..." in result


class TestStatusBar:
    def test_writes_state_file(self, tmp_path):
        role_dir = tmp_path / "skill"
        role_dir.mkdir()
        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path):
            result = cycle.status_bar("skill", "implementing", "#5 working...")
        assert result == "implementing|#5 working..."
        state = (role_dir / "current-state").read_text(encoding="utf-8")
        assert state == "implementing|#5 working..."

    def test_empty_description(self, tmp_path):
        role_dir = tmp_path / "skill"
        role_dir.mkdir()
        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path):
            result = cycle.status_bar("skill", "idle")
        assert result == "idle|"


class TestStatusBarSelf:
    """#9747: status-bar-self derives role from SQUIDSQUAD_ROLE env."""

    def test_uses_squidsquad_role_env(self, tmp_path, monkeypatch):
        role_dir = tmp_path / "skill"
        role_dir.mkdir()
        monkeypatch.setenv("SQUIDSQUAD_ROLE", "skill")
        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path):
            result = cycle.status_bar_self("implementing", "#42 working...")
        assert result == "implementing|#42 working..."
        assert (role_dir / "current-state").read_text(encoding="utf-8") == "implementing|#42 working..."

    def test_routes_to_role_specific_dir(self, tmp_path, monkeypatch):
        """qa role writes to .squidsquad/qa/current-state, not skill's."""
        (tmp_path / "skill").mkdir()
        qa_dir = tmp_path / "qa"
        qa_dir.mkdir()
        monkeypatch.setenv("SQUIDSQUAD_ROLE", "qa")
        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path):
            cycle.status_bar_self("verifying", "#100")
        assert (qa_dir / "current-state").read_text(encoding="utf-8") == "verifying|#100"
        assert not (tmp_path / "skill" / "current-state").exists()

    def test_missing_env_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("SQUIDSQUAD_ROLE", raising=False)
        with pytest.raises(SystemExit) as exc:
            cycle.status_bar_self("phase")
        assert exc.value.code == 1
        assert "SQUIDSQUAD_ROLE" in capsys.readouterr().err

    def test_empty_env_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("SQUIDSQUAD_ROLE", "")
        with pytest.raises(SystemExit) as exc:
            cycle.status_bar_self("phase")
        assert exc.value.code == 1

    def test_whitespace_env_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("SQUIDSQUAD_ROLE", "   ")
        with pytest.raises(SystemExit) as exc:
            cycle.status_bar_self("phase")
        assert exc.value.code == 1


class TestCounters:
    def _setup_working_state(self, tmp_path, role, counter=0):
        role_dir = tmp_path / role
        role_dir.mkdir(parents=True, exist_ok=True)
        ws = role_dir / "working-state.md"
        ws.write_text(
            f"# Working State\n\n- **Task**: none\n- **Status**: none\n"
            f"- **Quiet Cycle Counter**: {counter}\n"
        )
        return ws

    def _patch(self, tmp_path):
        """Context manager patching both SQUIDSQUAD_DIR and _state_path."""
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path))
        stack.enter_context(patch.object(cycle, "_state_path", lambda rel: tmp_path / rel))
        return stack

    def test_get_counter(self, tmp_path, capsys):
        self._setup_working_state(tmp_path, "skill", counter=3)
        with self._patch(tmp_path):
            result = cycle.get_counter("skill")
        assert result == 3
        output = capsys.readouterr().out.strip()
        assert output == "3", f"get_counter should print counter value, got: {output!r}"

    def test_get_counter_missing_file(self, tmp_path, capsys):
        with self._patch(tmp_path):
            result = cycle.get_counter("skill")
        assert result == 0
        output = capsys.readouterr().out.strip()
        assert output == "0", f"get_counter should print 0 for missing file, got: {output!r}"

    def test_set_counter(self, tmp_path):
        ws = self._setup_working_state(tmp_path, "skill", counter=2)
        with self._patch(tmp_path):
            cycle.set_counter("skill", 5)
        text = ws.read_text()
        assert "Quiet Cycle Counter**: 5" in text

    def test_set_counter_upserts_when_field_absent(self, tmp_path):
        """#8484: set_counter creates the field if it doesn't exist."""
        role_dir = tmp_path / "skill"
        role_dir.mkdir(parents=True, exist_ok=True)
        ws = role_dir / "working-state.md"
        ws.write_text("# Working State\n\n- **Task**: none\n- **Status**: none\n")
        with self._patch(tmp_path):
            cycle.set_counter("skill", 3)
        text = ws.read_text()
        assert "- **Quiet Cycle Counter**: 3\n" in text
        assert text.count("Quiet Cycle Counter") == 1

    def test_inc_counter_upserts_when_field_absent(self, tmp_path, capsys):
        """#8484: inc_counter persists when field starts absent."""
        role_dir = tmp_path / "skill"
        role_dir.mkdir(parents=True, exist_ok=True)
        ws = role_dir / "working-state.md"
        ws.write_text("# Working State\n\n- **Task**: none\n- **Status**: none\n")
        with self._patch(tmp_path):
            result = cycle.inc_counter("skill")
        assert result == 1
        text = ws.read_text()
        assert "- **Quiet Cycle Counter**: 1\n" in text
        assert capsys.readouterr().out.strip() == "1"

    def test_inc_counter(self, tmp_path, capsys):
        self._setup_working_state(tmp_path, "skill", counter=2)
        with self._patch(tmp_path):
            result = cycle.inc_counter("skill")
        assert result == 3
        output = capsys.readouterr().out.strip()
        assert output == "3", f"inc_counter should print new value, got: {output!r}"

    def test_inc_counter_single_output_line(self, tmp_path, capsys):
        """#7610: inc_counter must emit exactly one line (new value only)."""
        self._setup_working_state(tmp_path, "skill", counter=5)
        with self._patch(tmp_path):
            cycle.inc_counter("skill")
        output = capsys.readouterr().out.strip()
        lines = [l for l in output.splitlines() if l.strip()]
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}: {lines}"
        assert lines[0] == "6"

    def test_reset_counter(self, tmp_path, capsys):
        self._setup_working_state(tmp_path, "skill", counter=5)
        with self._patch(tmp_path):
            result = cycle.reset_counter("skill")
        assert result == 0
        output = capsys.readouterr().out.strip()
        assert output == "0", f"reset_counter should print 0, got: {output!r}"


class TestLogIteration:
    @patch.object(cycle, "_now", return_value=FIXED_NOW)
    def test_creates_log_file(self, mock_now, tmp_path, capsys):
        role_dir = tmp_path / "skill" / "iterations"
        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(cycle, "REPO_ROOT", tmp_path.parent), \
             patch.object(cycle, "_state_path", lambda rel: tmp_path / rel):
            path = cycle.log_iteration("skill", 5, bugs="#42", features="none",
                                       tests="all pass", notes="test note")
        log = Path(path)
        assert log.exists()
        content = log.read_text()
        assert "Iteration 5" in content
        assert "#42" in content
        assert "test note" in content
        assert "2026-04-13 14:30" in content

    @patch.object(cycle, "_now", return_value=FIXED_NOW)
    def test_new_param_names(self, mock_now, tmp_path, capsys):
        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(cycle, "REPO_ROOT", tmp_path.parent), \
             patch.object(cycle, "_state_path", lambda rel: tmp_path / rel):
            path = cycle.log_iteration("skill", 1, issues="#100", tasks="#200")
        content = Path(path).read_text()
        assert "#100" in content
        assert "#200" in content


class TestCleanupIterations:
    def test_keeps_recent_files(self, tmp_path):
        iter_dir = tmp_path / "skill" / "iterations"
        iter_dir.mkdir(parents=True)
        # Create 25 files with staggered mtimes
        for i in range(25):
            f = iter_dir / f"iter-{i}.md"
            f.write_text(f"iter {i}")
            import os
            os.utime(f, (time.time() - (25 - i), time.time() - (25 - i)))

        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(cycle, "_state_path", lambda rel: tmp_path / rel):
            removed = cycle.cleanup_iterations("skill", keep=20)
        assert removed == 5
        remaining = list(iter_dir.glob("iter-*.md"))
        assert len(remaining) == 20

    def test_no_removal_under_limit(self, tmp_path):
        iter_dir = tmp_path / "skill" / "iterations"
        iter_dir.mkdir(parents=True)
        for i in range(5):
            (iter_dir / f"iter-{i}.md").write_text(f"iter {i}")

        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(cycle, "_state_path", lambda rel: tmp_path / rel):
            removed = cycle.cleanup_iterations("skill", keep=20)
        assert removed == 0

    def test_missing_dir_returns_zero(self, tmp_path):
        with patch.object(cycle, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(cycle, "_state_path", lambda rel: tmp_path / rel):
            removed = cycle.cleanup_iterations("skill")
        assert removed == 0


class TestLogIterationUsageMessage:
    """#7706: log-iteration error message must match documented interface."""

    def test_error_message_matches_docstring(self):
        """CLI error message for log-iteration should advertise --work/--notes, not --issues/--tasks."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "cycle.py"), "log-iteration"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 1
        assert "--work" in result.stderr, \
            f"Error message should mention --work, got: {result.stderr!r}"
        assert "--issues" not in result.stderr, \
            f"Error message should NOT mention --issues (legacy), got: {result.stderr!r}"
