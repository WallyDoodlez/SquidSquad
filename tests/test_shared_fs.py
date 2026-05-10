"""Tests for references/scripts/shared_fs.py — shared filesystem at ~/.squidsquad/."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shared_fs


class TestGetHome:
    def test_returns_path_under_home(self):
        home = shared_fs.get_home()
        assert home == Path.home() / ".squidsquad"

    def test_returns_path_object(self):
        assert isinstance(shared_fs.get_home(), Path)


class TestInit:
    def test_creates_structure(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
        assert fake_home.exists()
        assert (fake_home / "secrets").exists()
        assert (fake_home / "config").exists()
        assert (fake_home / "clones").is_dir()

    def test_idempotent(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            # Write a secret, then re-init — should not overwrite
            (fake_home / "secrets").write_text("MY_KEY=my_value\n")
            shared_fs.init()
        content = (fake_home / "secrets").read_text()
        assert "MY_KEY=my_value" in content

    def test_secrets_has_comment_header(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
        content = (fake_home / "secrets").read_text()
        assert content.startswith("#")


class TestSecrets:
    def test_write_and_read(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("OPENAI_API_KEY", "sk-test123")
            value = shared_fs.read_secret("OPENAI_API_KEY")
        assert value == "sk-test123"

    def test_read_missing_key(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            value = shared_fs.read_secret("NONEXISTENT")
        assert value is None

    def test_read_no_file(self, tmp_path):
        fake_home = tmp_path / ".squidsquad-missing"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            value = shared_fs.read_secret("ANY_KEY")
        assert value is None

    def test_update_existing_secret(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("KEY", "old_value")
            shared_fs.write_secret("KEY", "new_value")
            value = shared_fs.read_secret("KEY")
        assert value == "new_value"

    def test_multiple_secrets(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("KEY_A", "val_a")
            shared_fs.write_secret("KEY_B", "val_b")
            assert shared_fs.read_secret("KEY_A") == "val_a"
            assert shared_fs.read_secret("KEY_B") == "val_b"

    def test_comments_ignored(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        fake_home.mkdir(parents=True)
        (fake_home / "secrets").write_text("# comment\nKEY=value\n# another\n")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            assert shared_fs.read_secret("KEY") == "value"
            assert shared_fs.read_secret("#") is None


class TestReadSecretOrEnv:
    def test_prefers_secrets_file(self, tmp_path, monkeypatch):
        fake_home = tmp_path / ".squidsquad"
        monkeypatch.setenv("TEST_KEY", "from_env")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("TEST_KEY", "from_file")
            value = shared_fs.read_secret_or_env("TEST_KEY")
        assert value == "from_file"

    def test_falls_back_to_env(self, tmp_path, monkeypatch):
        fake_home = tmp_path / ".squidsquad-empty"
        monkeypatch.setenv("TEST_KEY2", "from_env")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            value = shared_fs.read_secret_or_env("TEST_KEY2")
        assert value == "from_env"

    def test_returns_none_if_nowhere(self, tmp_path, monkeypatch):
        fake_home = tmp_path / ".squidsquad-empty"
        monkeypatch.delenv("MISSING_KEY_XYZ", raising=False)
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            value = shared_fs.read_secret_or_env("MISSING_KEY_XYZ")
        assert value is None

    def test_empty_string_secret_not_dropped(self, tmp_path, monkeypatch):
        """#4050 regression: empty-string secret must not fall through to env."""
        fake_home = tmp_path / ".squidsquad"
        monkeypatch.setenv("EMPTY_KEY", "from_env")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("EMPTY_KEY", "")
            value = shared_fs.read_secret_or_env("EMPTY_KEY")
        # Secrets file takes precedence — even for empty string
        assert value == ""


class TestClones:
    def test_write_and_read(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_clone("skill", "/path/to/skill-clone")
            shared_fs.write_clone("pm", "/path/to/pm-clone")
            clones = shared_fs.read_clones()
        assert clones["skill"] == "/path/to/skill-clone"
        assert clones["pm"] == "/path/to/pm-clone"

    def test_empty_clones(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            clones = shared_fs.read_clones()
        assert clones == {}

    def test_no_clones_dir(self, tmp_path):
        fake_home = tmp_path / ".squidsquad-missing"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            clones = shared_fs.read_clones()
        assert clones == {}


class TestCLI:
    def test_help(self, capsys):
        sys.argv = ["shared_fs.py", "--help"]
        result = shared_fs.main()
        assert result == 0
        output = capsys.readouterr().out
        assert "shared_fs.py" in output

    def test_home(self, capsys):
        sys.argv = ["shared_fs.py", "home"]
        shared_fs.main()
        output = capsys.readouterr().out.strip()
        assert ".squidsquad" in output

    def test_init(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            sys.argv = ["shared_fs.py", "init"]
            shared_fs.main()
        assert fake_home.exists()

    def test_read_secret_empty_value_not_false_negative(self, tmp_path, capsys):
        """#6818: read-secret CLI must return exit 0 for empty secret, not 'not found'."""
        fake_home = tmp_path / ".squidsquad"
        fake_home.mkdir()
        secrets = fake_home / "secrets"
        secrets.write_text("EMPTY_KEY=\n", encoding="utf-8")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            sys.argv = ["shared_fs.py", "read-secret", "EMPTY_KEY"]
            result = shared_fs.main()
        assert result is None or result == 0, (
            f"#6818: read-secret returned {result} for empty secret — should be 0"
        )
