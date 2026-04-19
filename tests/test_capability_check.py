"""Tests for references/scripts/capability_check.py — capability availability checks."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capability_check


class TestLoadYaml:
    def test_valid_yaml(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text("name: test\nprovider: builtin\n")
        result = capability_check._load_yaml(f)
        assert result["name"] == "test"

    def test_missing_file(self, tmp_path):
        assert capability_check._load_yaml(tmp_path / "missing.yaml") is None

    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("{{invalid yaml::")
        assert capability_check._load_yaml(f) is None


class TestCheckCapability:
    def _setup_cap(self, tmp_path, cap_id, manifest_content):
        """Create a capability manifest."""
        cap_dir = tmp_path / cap_id
        cap_dir.mkdir()
        (cap_dir / "manifest.yaml").write_text(manifest_content)
        return tmp_path

    def test_builtin_always_available(self, tmp_path):
        caps = self._setup_cap(tmp_path, "test-cap", "provider: builtin\n")
        with patch.object(capability_check, "CAPABILITIES_DIR", caps):
            available, reason = capability_check.check_capability("test-cap")
        assert available is True
        assert "builtin" in reason

    def test_mcp_available_if_manifest_exists(self, tmp_path):
        caps = self._setup_cap(
            tmp_path, "test-mcp", "provider: mcp\nmcp_name: test-server\n"
        )
        with patch.object(capability_check, "CAPABILITIES_DIR", caps):
            available, reason = capability_check.check_capability("test-mcp")
        assert available is True
        assert "mcp" in reason

    def test_cli_available_when_command_found(self, tmp_path):
        caps = self._setup_cap(
            tmp_path, "test-cli", "provider: cli\ncli_command: python\n"
        )
        with patch.object(capability_check, "CAPABILITIES_DIR", caps):
            available, reason = capability_check.check_capability("test-cli")
        assert available is True
        assert "cli" in reason

    def test_cli_missing_when_command_not_found(self, tmp_path):
        caps = self._setup_cap(
            tmp_path, "test-cli", "provider: cli\ncli_command: nonexistent_cmd_xyz\n"
        )
        with patch.object(capability_check, "CAPABILITIES_DIR", caps):
            available, reason = capability_check.check_capability("test-cli")
        assert available is False
        assert "not found" in reason

    def test_http_available_if_manifest_exists(self, tmp_path):
        caps = self._setup_cap(
            tmp_path, "test-http", "provider: http\ndocs_url: http://example.com\n"
        )
        with patch.object(capability_check, "CAPABILITIES_DIR", caps):
            available, reason = capability_check.check_capability("test-http")
        assert available is True
        assert "http" in reason

    def test_missing_manifest(self, tmp_path):
        with patch.object(capability_check, "CAPABILITIES_DIR", tmp_path):
            available, reason = capability_check.check_capability("nonexistent")
        assert available is False
        assert "manifest not found" in reason

    def test_unknown_provider(self, tmp_path):
        caps = self._setup_cap(tmp_path, "test-unk", "provider: alien\n")
        with patch.object(capability_check, "CAPABILITIES_DIR", caps):
            available, reason = capability_check.check_capability("test-unk")
        assert available is False
        assert "unknown provider" in reason


class TestCheckRole:
    def _setup_role(self, tmp_path, role_id, manifest_content):
        """Create a role manifest."""
        role_dir = tmp_path / role_id
        role_dir.mkdir()
        (role_dir / "manifest.yaml").write_text(manifest_content)

    def test_no_capabilities_required(self, tmp_path):
        self._setup_role(tmp_path, "test-role", "id: test-role\n")
        with patch.object(capability_check, "ROLES_DIR", tmp_path):
            code, results = capability_check.check_role("test-role")
        assert code == 0
        assert results == []

    def test_missing_role_manifest(self, tmp_path):
        with patch.object(capability_check, "ROLES_DIR", tmp_path):
            code, results = capability_check.check_role("nonexistent")
        assert code == 2

    def test_any_of_passes_when_one_available(self, tmp_path):
        self._setup_role(tmp_path, "test-role", (
            "id: test-role\n"
            "requires_sub_skills:\n"
            "  any_of:\n"
            "    - builtin-cap\n"
            "    - missing-cap\n"
        ))
        # Setup capabilities
        caps_dir = tmp_path / "caps"
        cap_dir = caps_dir / "builtin-cap"
        cap_dir.mkdir(parents=True)
        (cap_dir / "manifest.yaml").write_text("provider: builtin\n")

        with patch.object(capability_check, "ROLES_DIR", tmp_path), \
             patch.object(capability_check, "CAPABILITIES_DIR", caps_dir):
            code, results = capability_check.check_role("test-role")
        assert code == 0

    def test_any_of_fails_when_none_available(self, tmp_path):
        self._setup_role(tmp_path, "test-role", (
            "id: test-role\n"
            "requires_sub_skills:\n"
            "  any_of:\n"
            "    - missing-a\n"
            "    - missing-b\n"
        ))
        with patch.object(capability_check, "ROLES_DIR", tmp_path), \
             patch.object(capability_check, "CAPABILITIES_DIR", tmp_path / "empty"):
            code, results = capability_check.check_role("test-role")
        assert code == 1

    def test_all_of_passes_when_all_available(self, tmp_path):
        self._setup_role(tmp_path, "test-role", (
            "id: test-role\n"
            "requires_sub_skills:\n"
            "  all_of:\n"
            "    - cap-a\n"
            "    - cap-b\n"
        ))
        caps_dir = tmp_path / "caps"
        for cap in ("cap-a", "cap-b"):
            d = caps_dir / cap
            d.mkdir(parents=True)
            (d / "manifest.yaml").write_text("provider: builtin\n")

        with patch.object(capability_check, "ROLES_DIR", tmp_path), \
             patch.object(capability_check, "CAPABILITIES_DIR", caps_dir):
            code, results = capability_check.check_role("test-role")
        assert code == 0

    def test_all_of_fails_when_one_missing(self, tmp_path):
        self._setup_role(tmp_path, "test-role", (
            "id: test-role\n"
            "requires_sub_skills:\n"
            "  all_of:\n"
            "    - cap-a\n"
            "    - cap-missing\n"
        ))
        caps_dir = tmp_path / "caps"
        d = caps_dir / "cap-a"
        d.mkdir(parents=True)
        (d / "manifest.yaml").write_text("provider: builtin\n")

        with patch.object(capability_check, "ROLES_DIR", tmp_path), \
             patch.object(capability_check, "CAPABILITIES_DIR", caps_dir):
            code, results = capability_check.check_role("test-role")
        assert code == 1
