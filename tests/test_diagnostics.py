"""Tests for references/scripts/diagnostics.py — log, read, rotate, sanitize,
generate_report, is_public_repo."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import diagnostics


class TestLogEntry:
    def test_creates_log_file(self, tmp_path):
        log_dir = tmp_path / "diagnostics"
        log_file = log_dir / "diagnostic.jsonl"
        with patch.object(diagnostics, "DIAGNOSTICS_DIR", log_dir), \
             patch.object(diagnostics, "LOG_FILE", log_file):
            entry = diagnostics.log_entry("warning", "tracker", "test message")
        assert log_file.exists()
        assert entry["severity"] == "warning"
        assert entry["source"] == "tracker"
        assert entry["message"] == "test message"

    def test_appends_to_existing(self, tmp_path):
        log_dir = tmp_path / "diagnostics"
        log_dir.mkdir()
        log_file = log_dir / "diagnostic.jsonl"
        log_file.write_text('{"existing": true}\n', encoding="utf-8")
        with patch.object(diagnostics, "DIAGNOSTICS_DIR", log_dir), \
             patch.object(diagnostics, "LOG_FILE", log_file):
            diagnostics.log_entry("info", "cycle", "second entry")
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_json_context(self, tmp_path):
        log_dir = tmp_path / "diagnostics"
        log_file = log_dir / "diagnostic.jsonl"
        with patch.object(diagnostics, "DIAGNOSTICS_DIR", log_dir), \
             patch.object(diagnostics, "LOG_FILE", log_file):
            entry = diagnostics.log_entry("error", "boot", "fail", context='{"pid": 123}')
        assert entry["context"] == {"pid": 123}

    def test_non_json_context(self, tmp_path):
        log_dir = tmp_path / "diagnostics"
        log_file = log_dir / "diagnostic.jsonl"
        with patch.object(diagnostics, "DIAGNOSTICS_DIR", log_dir), \
             patch.object(diagnostics, "LOG_FILE", log_file):
            entry = diagnostics.log_entry("info", "test", "msg", context="plain text")
        assert entry["context"] == {"raw": "plain text"}


class TestReadEntries:
    def test_reads_last_n(self, tmp_path, capsys):
        log_file = tmp_path / "diagnostic.jsonl"
        entries = [json.dumps({"n": i}) for i in range(10)]
        log_file.write_text("\n".join(entries) + "\n", encoding="utf-8")
        with patch.object(diagnostics, "LOG_FILE", log_file):
            result = diagnostics.read_entries(last=3)
        assert len(result) == 3
        assert result[0]["n"] == 7

    def test_missing_file_returns_empty(self, tmp_path, capsys):
        with patch.object(diagnostics, "LOG_FILE", tmp_path / "missing.jsonl"):
            result = diagnostics.read_entries()
        assert result == []

    def test_malformed_lines_skipped(self, tmp_path, capsys):
        log_file = tmp_path / "diagnostic.jsonl"
        log_file.write_text('{"good": true}\nnot json\n{"also": "good"}\n', encoding="utf-8")
        with patch.object(diagnostics, "LOG_FILE", log_file):
            result = diagnostics.read_entries(last=10)
        assert len(result) == 2


class TestRotate:
    def test_rotates_when_over_500(self, tmp_path):
        log_file = tmp_path / "diagnostic.jsonl"
        entries = [json.dumps({"n": i}) for i in range(600)]
        log_file.write_text("\n".join(entries) + "\n", encoding="utf-8")
        with patch.object(diagnostics, "LOG_FILE", log_file):
            diagnostics.rotate()
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 500

    def test_no_rotation_under_500(self, tmp_path):
        log_file = tmp_path / "diagnostic.jsonl"
        entries = [json.dumps({"n": i}) for i in range(100)]
        log_file.write_text("\n".join(entries) + "\n", encoding="utf-8")
        with patch.object(diagnostics, "LOG_FILE", log_file):
            diagnostics.rotate()
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 100

    def test_missing_file_no_error(self, tmp_path):
        with patch.object(diagnostics, "LOG_FILE", tmp_path / "missing.jsonl"):
            diagnostics.rotate()  # should not raise

    def test_log_entry_rotates_before_write(self, tmp_path):
        """#5385: rotation is called before write, not after."""
        log_file = tmp_path / "diagnostic.jsonl"
        # Create a file over the byte cap
        log_file.write_text("x" * 200, encoding="utf-8")

        rotate_calls = []
        original_rotate = diagnostics.rotate

        def tracking_rotate():
            rotate_calls.append("rotated")
            original_rotate()

        with patch.object(diagnostics, "LOG_FILE", log_file), \
             patch.object(diagnostics, "DIAGNOSTICS_DIR", tmp_path), \
             patch.object(diagnostics, "MAX_LOG_BYTES", 100), \
             patch.object(diagnostics, "rotate", tracking_rotate):
            diagnostics.log_entry("info", "test", "after rotation")

        assert len(rotate_calls) == 1, "rotate() should have been called before write"
        # The new entry should be in the file
        content = log_file.read_text(encoding="utf-8")
        assert "after rotation" in content


class TestSanitizeConfig:
    def test_redacts_repo_field(self):
        config_text = "- **Repo**: github.com/secret/repo\n- **Name**: MyApp\n"
        with patch.object(diagnostics, "_read_config", return_value=config_text):
            result = diagnostics._sanitize_config()
        assert "[REDACTED]" in result
        assert "secret" not in result
        assert "MyApp" in result

    def test_preserves_non_sensitive(self):
        config_text = "- **Minutes**: 30\n- **Enabled**: yes\n"
        with patch.object(diagnostics, "_read_config", return_value=config_text):
            result = diagnostics._sanitize_config()
        assert "30" in result
        assert "yes" in result
        assert "[REDACTED]" not in result

    def test_redacts_plain_text_without_markdown_bold(self):
        """#7518: lines without ** markers must still be redacted."""
        config_text = "repo: https://github.com/user/private-repo\nname: MyApp\n"
        with patch.object(diagnostics, "_read_config", return_value=config_text):
            result = diagnostics._sanitize_config()
        assert "[REDACTED]" in result
        assert "private-repo" not in result
        assert "MyApp" in result

    def test_redacts_token_without_bold(self):
        """#7518: token field without markdown bold must be redacted."""
        config_text = "token: abc123secret\nversion: 0.37.0\n"
        with patch.object(diagnostics, "_read_config", return_value=config_text):
            result = diagnostics._sanitize_config()
        assert "abc123secret" not in result
        assert "[REDACTED]" in result
        assert "0.37.0" in result

    def test_redacts_url_field(self):
        """#8235 regression: url fields must be redacted."""
        config_text = "clone-url: https://github.com/user/private\nversion: 0.38.0\n"
        with patch.object(diagnostics, "_read_config", return_value=config_text):
            result = diagnostics._sanitize_config()
        assert "private" not in result
        assert "[REDACTED]" in result
        assert "0.38.0" in result

    def test_redacts_webhook_field(self):
        """#8235 regression: webhook fields must be redacted."""
        config_text = "webhook: https://hooks.slack.com/secret123\nname: app\n"
        with patch.object(diagnostics, "_read_config", return_value=config_text):
            result = diagnostics._sanitize_config()
        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_redacts_password_field(self):
        """#8235 regression: password fields must be redacted."""
        config_text = "password: hunter2\ninterval: 30\n"
        with patch.object(diagnostics, "_read_config", return_value=config_text):
            result = diagnostics._sanitize_config()
        assert "hunter2" not in result
        assert "[REDACTED]" in result
        assert "30" in result


class TestIsPublicRepo:
    def test_public_repo(self, capsys):
        mock_result = MagicMock()
        mock_result.stdout = '{"isPrivate": false}'
        with patch("diagnostics.subprocess.run", return_value=mock_result):
            result = diagnostics.is_public_repo()
        assert result is True
        assert "true" in capsys.readouterr().out

    def test_private_repo(self, capsys):
        mock_result = MagicMock()
        mock_result.stdout = '{"isPrivate": true}'
        with patch("diagnostics.subprocess.run", return_value=mock_result):
            result = diagnostics.is_public_repo()
        assert result is False
        assert "false" in capsys.readouterr().out

    def test_missing_field_defaults_private(self, capsys):
        mock_result = MagicMock()
        mock_result.stdout = '{}'
        with patch("diagnostics.subprocess.run", return_value=mock_result):
            result = diagnostics.is_public_repo()
        assert result is False

    def test_gh_command_fails(self, capsys):
        with patch("diagnostics.subprocess.run",
                   side_effect=subprocess.CalledProcessError(1, "gh")):
            result = diagnostics.is_public_repo()
        assert result is None
        assert "unknown" in capsys.readouterr().out

    def test_invalid_json_response(self, capsys):
        mock_result = MagicMock()
        mock_result.stdout = "not json"
        with patch("diagnostics.subprocess.run", return_value=mock_result):
            result = diagnostics.is_public_repo()
        assert result is None
        assert "unknown" in capsys.readouterr().out


class TestGenerateReport:
    def test_report_contains_version(self, capsys):
        with patch.object(diagnostics, "get_field", return_value="0.30.0"), \
             patch.object(diagnostics, "_sanitize_config", return_value="config here"), \
             patch.object(diagnostics, "LOG_FILE", Path("/nonexistent")):
            report = diagnostics.generate_report()
        assert "0.30.0" in report
        assert "config here" in report
        assert "Issue Report" in report

    def test_report_with_diagnostics_entries(self, tmp_path, capsys):
        log_file = tmp_path / "diagnostic.jsonl"
        log_file.write_text(
            json.dumps({"severity": "warning", "message": "test"}) + "\n",
            encoding="utf-8",
        )
        with patch.object(diagnostics, "get_field", return_value="1.0.0"), \
             patch.object(diagnostics, "_sanitize_config", return_value="cfg"), \
             patch.object(diagnostics, "LOG_FILE", log_file):
            report = diagnostics.generate_report()
        assert "Recent Diagnostics" in report
        assert '"warning"' in report

    def test_report_no_log_file(self, tmp_path, capsys):
        no_log = tmp_path / "no_such_log.jsonl"
        with patch.object(diagnostics, "get_field", return_value="1.0.0"), \
             patch.object(diagnostics, "_sanitize_config", return_value="cfg"), \
             patch.object(diagnostics, "LOG_FILE", no_log):
            report = diagnostics.generate_report()
        assert "Recent Diagnostics" not in report
        assert "Issue Report" in report

    def test_report_version_unknown_on_error(self, tmp_path, capsys):
        no_log = tmp_path / "no_such_log.jsonl"
        with patch.object(diagnostics, "get_field", side_effect=SystemExit(1)), \
             patch.object(diagnostics, "_sanitize_config", return_value="cfg"), \
             patch.object(diagnostics, "LOG_FILE", no_log):
            report = diagnostics.generate_report()
        assert "unknown" in report

    def test_report_skips_malformed_log_lines(self, tmp_path, capsys):
        log_file = tmp_path / "diagnostic.jsonl"
        log_file.write_text("not json\n" + json.dumps({"ok": True}) + "\n",
                            encoding="utf-8")
        with patch.object(diagnostics, "get_field", return_value="1.0.0"), \
             patch.object(diagnostics, "_sanitize_config", return_value="cfg"), \
             patch.object(diagnostics, "LOG_FILE", log_file):
            report = diagnostics.generate_report()
        assert '"ok"' in report
        assert "not json" not in report


class TestRedactEntry:
    """#10005: diagnostic entries must be redacted before inclusion in the
    bug-report output. The keyword list mirrors `_sanitize_config`'s — values
    under matching keys are replaced with `[REDACTED]`."""

    def test_redacts_sensitive_context_key(self):
        entry = {"severity": "error", "context": {"token": "abc123", "ok": "safe"}}
        result = diagnostics._redact_entry(entry)
        assert result["context"]["token"] == "[REDACTED]"
        assert result["context"]["ok"] == "safe"

    def test_redacts_nested_dict(self):
        entry = {"context": {"outer": {"clone_url": "https://x.y/repo.git", "name": "ok"}}}
        result = diagnostics._redact_entry(entry)
        assert result["context"]["outer"]["clone_url"] == "[REDACTED]"
        assert result["context"]["outer"]["name"] == "ok"

    def test_recurses_through_lists(self):
        entry = {"context": {"items": [{"password": "p1"}, {"name": "ok"}]}}
        result = diagnostics._redact_entry(entry)
        assert result["context"]["items"][0]["password"] == "[REDACTED]"
        assert result["context"]["items"][1]["name"] == "ok"

    def test_non_matching_top_level_keys_pass_through(self):
        entry = {"severity": "info", "source": "boot", "message": "ok"}
        result = diagnostics._redact_entry(entry)
        assert result == entry

    def test_does_not_mutate_input(self):
        entry = {"context": {"token": "abc"}}
        diagnostics._redact_entry(entry)
        assert entry["context"]["token"] == "abc"

    def test_generate_report_redacts_diagnostic_context(self, tmp_path):
        """End-to-end: a token logged into context must not appear in the
        rendered report. This is the public-tracker leak path from the
        original finding."""
        log_file = tmp_path / "diagnostic.jsonl"
        log_file.write_text(
            json.dumps({
                "severity": "error",
                "source": "boot",
                "message": "fail",
                "context": {"token": "abc-secret-123", "ok": "visible"},
            }) + "\n",
            encoding="utf-8",
        )
        with patch.object(diagnostics, "get_field", return_value="1.0.0"), \
             patch.object(diagnostics, "_sanitize_config", return_value="cfg"), \
             patch.object(diagnostics, "LOG_FILE", log_file):
            report = diagnostics.generate_report()
        assert "abc-secret-123" not in report
        assert "[REDACTED]" in report
        assert "visible" in report


class TestLastFlagValidation:
    """#7519: --last flag must reject non-integer arguments."""

    def test_non_integer_last_exits_with_error(self):
        """diagnostics.py read --last foo should exit 1, not crash."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "diagnostics.py"), "read", "--last", "foo"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 1
        assert "integer" in result.stderr.lower() or "error" in result.stderr.lower()
