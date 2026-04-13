"""Static analysis: Verify sub-skill manifest consistency.

Checks that all sub-skill files listed in the manifest exist,
and that all sub-skill files on disk are listed in the manifest.
"""

import re
import pytest
from pathlib import Path

from conftest import REFERENCES_DIR


class TestManifestIntegrity:
    """Verify manifest.md matches the actual sub-skill file inventory."""

    @pytest.fixture(autouse=True, scope="class")
    def _parse_manifest(self, request):
        manifest_path = REFERENCES_DIR / "sub-skills" / "manifest.md"
        assert manifest_path.exists(), "Missing manifest.md"
        request.cls.manifest_text = manifest_path.read_text(encoding="utf-8")
        request.cls.sub_skills_dir = REFERENCES_DIR / "sub-skills"

    def _extract_inventory_paths(self):
        """Extract file paths from the Sub-skill File Inventory section."""
        # Find the inventory code block
        in_inventory = False
        paths = []
        for line in self.manifest_text.splitlines():
            if "Sub-skill File Inventory" in line:
                in_inventory = True
                continue
            if in_inventory and line.strip().startswith("```"):
                if paths:  # end of block
                    break
                continue  # start of block
            if in_inventory and "├──" in line or "└──" in line:
                # Extract filename from tree line
                match = re.search(r'[├└]── (.+?)(?:\s{2,}|$)', line)
                if match:
                    paths.append(match.group(1).strip())
        return paths

    def test_manifest_exists(self):
        assert (self.sub_skills_dir / "manifest.md").exists()

    def test_role_entries_exist(self):
        """Each role entry file referenced in manifest exists.

        After #328 Q-new22, role CLAUDE.md templates live in
        `references/roles/<role>/CLAUDE.md`, not under sub-skills/.
        """
        from conftest import REFERENCES_DIR
        role_refs = re.findall(
            r'`references/roles/([a-z][a-z0-9_-]*)/CLAUDE\.md`',
            self.manifest_text,
        )
        assert role_refs, (
            "Expected manifest to reference at least one concrete role "
            "CLAUDE.md (e.g. `references/roles/pm/CLAUDE.md`)."
        )
        for role in role_refs:
            path = REFERENCES_DIR / "roles" / role / "CLAUDE.md"
            assert path.exists(), f"Role entry file missing: {path}"

    def test_include_targets_exist(self):
        """All include paths referenced in composition order exist as .md files.

        `souls/` and `roles/` are no longer valid include namespaces after
        Q-new22 — they were removed from the sub-skills directory and moved
        to `references/roles/<role>/`.
        """
        includes = re.findall(
            r'`((?:common|dev-specific|pm-specific|qa-specific|designer-specific|dm-specific)/[^`]+)`',
            self.manifest_text,
        )
        for inc in includes:
            path = self.sub_skills_dir / f"{inc}.md"
            assert path.exists(), f"Sub-skill file missing: {path}"

    def test_no_orphan_sub_skills(self):
        """Every .md file under sub-skills/ (except manifest.md and capabilities/) is referenced in manifest."""
        all_md = set()
        for md in self.sub_skills_dir.rglob("*.md"):
            rel = md.relative_to(self.sub_skills_dir).as_posix()
            if rel == "manifest.md":
                continue
            # capabilities/ sub-dir contains tool manifests, not composable sub-skills
            if rel.startswith("capabilities/"):
                continue
            all_md.add(rel)

        referenced = set()
        for inc in re.findall(
            r'`((?:common|dev-specific|pm-specific|qa-specific|designer-specific|dm-specific)/[^`]+)`',
            self.manifest_text,
        ):
            if not inc.endswith('.md'):
                referenced.add(f"{inc}.md")
            else:
                referenced.add(inc)

        orphans = all_md - referenced
        assert not orphans, f"Sub-skill files not referenced in manifest: {orphans}"

    def test_legacy_souls_namespace_gone(self):
        """Manifest must no longer reference a `souls/` include namespace."""
        assert "souls/" not in self.manifest_text, (
            "Manifest still references the legacy souls/ namespace — it "
            "was retired by Q-new22."
        )

    def test_legacy_roles_include_namespace_gone(self):
        """Manifest must no longer reference a `roles/` include namespace."""
        # The new pattern is `references/roles/<role>/CLAUDE.md`, not `roles/x`
        legacy = re.findall(r'`roles/[^`]+`', self.manifest_text)
        assert not legacy, f"Manifest still references legacy roles/: {legacy}"


class TestIncludesYml:
    """Verify includes.yml manifests exist and are valid for all roles."""

    ROLES = ["dev", "pm", "qa", "dm", "designer"]

    @pytest.fixture(autouse=True, scope="class")
    def _setup(self, request):
        request.cls.roles_dir = REFERENCES_DIR / "roles"
        request.cls.sub_skills_dir = REFERENCES_DIR / "sub-skills"

    def test_includes_yml_exists_per_role(self):
        """TC-A1: Each role directory has an includes.yml."""
        for role in self.ROLES:
            path = self.roles_dir / role / "includes.yml"
            assert path.exists(), f"Missing includes.yml for {role}"

    def test_includes_yml_valid_yaml(self):
        """TC-X6: All manifests are valid YAML with expected structure."""
        import yaml
        for role in self.ROLES:
            path = self.roles_dir / role / "includes.yml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"{role}: not a dict"
            assert "includes" in data, f"{role}: missing 'includes' key"
            assert isinstance(data["includes"], list), f"{role}: 'includes' not a list"

    def test_includes_yml_paths_exist(self):
        """All sub-skill paths in includes.yml resolve to actual files."""
        import yaml
        for role in self.ROLES:
            path = self.roles_dir / role / "includes.yml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            for inc in data["includes"]:
                full = self.sub_skills_dir / f"{inc}.md"
                assert full.exists(), f"{role}: includes.yml references missing {inc}"

    def test_includes_yml_covers_template(self):
        """TC-A2: includes.yml covers all {{include:}} directives in templates.

        The manifest may use slim variants (e.g. vault-protocol-slim for
        vault-protocol) or omit sub-skills (e.g. vault-remember). Each
        template include must either appear in the manifest directly, have
        a slim variant present, or be intentionally excluded (removed by
        the manifest for token savings).
        """
        import yaml
        for role in self.ROLES:
            yml_path = self.roles_dir / role / "includes.yml"
            tmpl_path = self.roles_dir / role / "CLAUDE.md"
            data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
            yml_set = set(data["includes"])

            tmpl_text = tmpl_path.read_text(encoding="utf-8")
            tmpl_includes = re.findall(
                r'\{\{include:\s*(.+?)\}\}', tmpl_text,
            )

            # Every manifest entry must resolve to a file
            for inc in data["includes"]:
                full = self.sub_skills_dir / f"{inc}.md"
                assert full.exists(), (
                    f"{role}: manifest references non-existent {inc}"
                )
