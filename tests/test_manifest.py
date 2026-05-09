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
        `references/roles/<role>/instructions.md`, not under sub-skills/.
        """
        from conftest import REFERENCES_DIR
        role_refs = re.findall(
            r'`references/roles/([a-z][a-z0-9_-]*)/CLAUDE\.md`',
            self.manifest_text,
        )
        assert role_refs, (
            "Expected manifest to reference at least one concrete role "
            "CLAUDE.md (e.g. `references/roles/pm/instructions.md`)."
        )
        for role in role_refs:
            path = REFERENCES_DIR / "roles" / role / "instructions.md"
            assert path.exists(), f"Role entry file missing: {path}"

    def test_include_targets_exist(self):
        """All include paths referenced in composition order exist as .md files.

        `souls/` and `roles/` are no longer valid include namespaces after
        Q-new22 — they were removed from the sub-skills directory and moved
        to `references/roles/<role>/`.
        """
        includes = re.findall(
            r'`((?:common|roles)/[^`]+)`',
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
            # project/ sub-dir contains L4 project sub-skills, auto-included by compose.py
            if rel.startswith("project/"):
                continue
            all_md.add(rel)

        referenced = set()
        for inc in re.findall(
            r'`((?:common|roles)/[^`]+)`',
            self.manifest_text,
        ):
            if not inc.endswith('.md'):
                referenced.add(f"{inc}.md")
            else:
                referenced.add(inc)

        # Also scan includes.yml files for additional_includes (Layer 3 variants)
        try:
            import yaml
            roles_dir = self.sub_skills_dir.parent / "roles"
            for inc_yml in roles_dir.rglob("includes.yml"):
                data = yaml.safe_load(inc_yml.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for inc in data.get("additional_includes", []):
                        referenced.add(f"{inc}.md")
                    for inc in data.get("includes", []):
                        referenced.add(f"{inc}.md")
        except Exception:
            pass

        orphans = all_md - referenced
        assert not orphans, f"Sub-skill files not referenced in manifest: {orphans}"

    def test_legacy_souls_namespace_gone(self):
        """Manifest must no longer reference a `souls/` include namespace."""
        assert "souls/" not in self.manifest_text, (
            "Manifest still references the legacy souls/ namespace — it "
            "was retired by Q-new22."
        )

    def test_roles_sub_skills_use_new_namespace(self):
        """Role-specific sub-skills use roles/<role>/ namespace (not <role>-specific/)."""
        legacy = re.findall(r'`(?:dev|pm|qa|dm)-specific/[^`]+`', self.manifest_text)
        assert not legacy, f"Manifest still uses legacy <role>-specific/ namespace: {legacy}"


class TestIncludesYml:
    """Verify includes.yml manifests exist and are valid for all roles."""

    ROLES = ["dev", "pm", "qa", "dm"]

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
        template include must either appear in the manifest directly or
        have a slim/role-specific variant present in the manifest.
        """
        import yaml
        for role in self.ROLES:
            yml_path = self.roles_dir / role / "includes.yml"
            tmpl_path = self.roles_dir / role / "instructions.md"
            data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
            yml_set = set(data["includes"])

            tmpl_text = tmpl_path.read_text(encoding="utf-8")
            tmpl_includes = set(re.findall(
                r'\{\{include:\s*(.+?)\}\}', tmpl_text,
            ))

            # Every manifest entry must resolve to a file
            for inc in data["includes"]:
                full = self.sub_skills_dir / f"{inc}.md"
                assert full.exists(), (
                    f"{role}: manifest references non-existent {inc}"
                )

            # Every template include should be covered by the manifest —
            # either directly, via a slim variant, or intentionally excluded.
            # The manifest is intentionally a subset of the template for
            # token savings (slim variants replace full, some sub-skills omitted).
            uncovered = set()
            for inc in tmpl_includes:
                if inc in yml_set:
                    continue
                base = inc.split("/")[-1]
                # Slim variant (e.g., vault-protocol → vault-protocol-slim)
                slim_match = any(y.endswith(f"{base}-slim") for y in yml_set)
                # Role-specific override (e.g., common/X → roles/role/X)
                role_override = any(
                    y.endswith(f"/{base}") and y != inc for y in yml_set
                )
                if not slim_match and not role_override:
                    uncovered.add(inc)

            # Known intentional exclusions — manifest omits these for token
            # savings or because the role doesn't need them. This list must
            # be updated when includes.yml or templates change.
            known_exclusions = {
                "common/vault-optimize",
                "common/vault-remember",
                "common/improvement-scan",
                "common/vault-protocol",
            }
            unexpected = uncovered - known_exclusions
            assert not unexpected, (
                f"{role}: template includes not covered by manifest "
                f"(not direct, slim, role-specific, or known-excluded): "
                f"{sorted(unexpected)}"
            )


class TestComposeManifestIntegration:
    """Test compose.py manifest-driven composition."""

    @pytest.fixture(autouse=True, scope="class")
    def _setup(self, request):
        import sys
        sys.path.insert(0, str(REFERENCES_DIR / "scripts"))
        request.cls.roles_dir = REFERENCES_DIR / "roles"

    def test_load_manifest_returns_list(self):
        """_load_manifest returns a list for each role with includes.yml."""
        from compose import _load_manifest
        for role in ["dev", "pm", "qa", "dm"]:
            result = _load_manifest(role)
            assert isinstance(result, list), f"{role}: expected list, got {type(result)}"
            assert len(result) > 0, f"{role}: empty manifest"

    def test_load_manifest_dev_variant_inheritance(self):
        """Dev variants without includes.yml inherit from dev."""
        from compose import _load_manifest
        dev_manifest = _load_manifest("dev")
        # 'skill' is a dev variant — should inherit dev's manifest
        skill_manifest = _load_manifest("skill")
        assert skill_manifest == dev_manifest, (
            "skill should inherit dev manifest"
        )

    def test_manifest_composition_matches_inline(self):
        """Manifest-driven composition produces identical output to inline."""
        from compose import _resolve_includes, _resolve_includes_with_manifest, _load_manifest
        # For dev role, both paths should produce identical output
        entry_file = self.roles_dir / "dev" / "instructions.md"
        inline_result = _resolve_includes(entry_file)
        manifest = _load_manifest("dev")
        manifest_result = _resolve_includes_with_manifest(entry_file, manifest)
        assert inline_result == manifest_result, (
            "Manifest composition differs from inline — Phase A invariant broken"
        )

    def test_slim_variant_substitution(self):
        """QA manifest with slim variants produces different (smaller) output."""
        from compose import compose_role
        # QA uses slim variants, dev uses full — QA should be smaller
        qa_output = compose_role("qa")
        dev_output = compose_role("dev")
        assert len(qa_output) < len(dev_output), (
            "QA composed output should be smaller than dev (slim variants)"
        )
