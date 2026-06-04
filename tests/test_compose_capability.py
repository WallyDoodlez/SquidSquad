"""Tests for the {{capability:}} directive in compose.py and capability_check.py (#401)."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))


class TestCapabilityCheck:
    """Test capability_check.py."""

    def test_empty_requires_exits_zero(self, tmp_path):
        """A role with empty requires_sub_skills exits 0."""
        import capability_check

        role_dir = tmp_path / "roles" / "dev"
        role_dir.mkdir(parents=True)
        (role_dir / "manifest.yaml").write_text(
            "schema_version: 2\nid: dev\nrequires_sub_skills: {}\n",
            encoding="utf-8",
        )

        orig_roles = capability_check.ROLES_DIR
        try:
            capability_check.ROLES_DIR = tmp_path / "roles"
            code, _ = capability_check.check_role("dev")
        finally:
            capability_check.ROLES_DIR = orig_roles

        assert code == 0

    def test_builtin_capability_available(self, tmp_path):
        """A builtin capability is always available."""
        import capability_check

        # Set up capability
        cap_dir = tmp_path / "capabilities" / "local_html"
        cap_dir.mkdir(parents=True)
        (cap_dir / "manifest.yaml").write_text(
            "schema_version: 2\nid: local_html\nprovider: builtin\n",
            encoding="utf-8",
        )

        orig_caps = capability_check.CAPABILITIES_DIR
        try:
            capability_check.CAPABILITIES_DIR = tmp_path / "capabilities"
            avail, reason = capability_check.check_capability("local_html")
        finally:
            capability_check.CAPABILITIES_DIR = orig_caps

        assert avail is True
        assert "builtin" in reason

    def test_missing_capability_manifest(self, tmp_path):
        """A capability with no manifest is not available."""
        import capability_check

        orig_caps = capability_check.CAPABILITIES_DIR
        try:
            capability_check.CAPABILITIES_DIR = tmp_path / "capabilities"
            avail, reason = capability_check.check_capability("ghost")
        finally:
            capability_check.CAPABILITIES_DIR = orig_caps

        assert avail is False
        assert "not found" in reason

    def test_any_of_with_one_available(self, tmp_path):
        """any_of exits 0 if at least one capability is available."""
        import capability_check

        # Role with any_of
        role_dir = tmp_path / "roles" / "qa"
        role_dir.mkdir(parents=True)
        (role_dir / "manifest.yaml").write_text(
            "schema_version: 2\nid: qa\nrequires_sub_skills:\n  any_of: [figma, local_html]\n",
            encoding="utf-8",
        )

        # Only local_html exists
        cap_dir = tmp_path / "capabilities" / "local_html"
        cap_dir.mkdir(parents=True)
        (cap_dir / "manifest.yaml").write_text(
            "schema_version: 2\nid: local_html\nprovider: builtin\n",
            encoding="utf-8",
        )

        orig_roles = capability_check.ROLES_DIR
        orig_caps = capability_check.CAPABILITIES_DIR
        try:
            capability_check.ROLES_DIR = tmp_path / "roles"
            capability_check.CAPABILITIES_DIR = tmp_path / "capabilities"
            code, _ = capability_check.check_role("qa")
        finally:
            capability_check.ROLES_DIR = orig_roles
            capability_check.CAPABILITIES_DIR = orig_caps

        assert code == 0

    def test_any_of_with_none_available(self, tmp_path):
        """any_of exits 1 if no capabilities are available."""
        import capability_check

        role_dir = tmp_path / "roles" / "qa"
        role_dir.mkdir(parents=True)
        (role_dir / "manifest.yaml").write_text(
            "schema_version: 2\nid: qa\nrequires_sub_skills:\n  any_of: [figma, stitch]\n",
            encoding="utf-8",
        )

        orig_roles = capability_check.ROLES_DIR
        orig_caps = capability_check.CAPABILITIES_DIR
        try:
            capability_check.ROLES_DIR = tmp_path / "roles"
            capability_check.CAPABILITIES_DIR = tmp_path / "capabilities"
            code, _ = capability_check.check_role("qa")
        finally:
            capability_check.ROLES_DIR = orig_roles
            capability_check.CAPABILITIES_DIR = orig_caps

        assert code == 1

    def test_role_not_found(self, tmp_path):
        """Missing role manifest returns exit code 2."""
        import capability_check

        orig_roles = capability_check.ROLES_DIR
        try:
            capability_check.ROLES_DIR = tmp_path / "roles"
            code, _ = capability_check.check_role("nonexistent")
        finally:
            capability_check.ROLES_DIR = orig_roles

        assert code == 2
