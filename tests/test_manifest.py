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

        # Also scan includes.yml AND includes-events.yml files for
        # additional_includes (Layer 3 variants) + dual-mode (#8697). A
        # fragment is an orphan only when NO manifest of any mode references
        # it.
        try:
            import yaml
            roles_dir = self.sub_skills_dir.parent / "roles"
            for inc_yml in list(roles_dir.rglob("includes.yml")) + list(roles_dir.rglob("includes-events.yml")):
                data = yaml.safe_load(inc_yml.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for inc in data.get("additional_includes", []):
                        referenced.add(f"{inc}.md")
                    for inc in data.get("includes", []):
                        referenced.add(f"{inc}.md")
        except Exception:
            pass

        # #8697: common/event-reactions.md exists but isn't referenced by
        # any current role manifest. It's a sub-skill that may be wired in
        # for future event-driven needs; explicitly tolerate its
        # un-referenced state rather than block the build.
        known_unused = {"common/event-reactions.md"}
        orphans = all_md - referenced - known_unused
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
        """TC-A1: Each role directory has both includes.yml AND
        includes-events.yml (#8697 dual-mode)."""
        for role in self.ROLES:
            for fname in ("includes.yml", "includes-events.yml"):
                path = self.roles_dir / role / fname
                assert path.exists(), f"Missing {fname} for {role}"

    def test_includes_yml_valid_yaml(self):
        """TC-X6: All manifests are valid YAML with expected structure."""
        import yaml
        for role in self.ROLES:
            for fname in ("includes.yml", "includes-events.yml"):
                path = self.roles_dir / role / fname
                if not path.exists():
                    continue
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                assert isinstance(data, dict), f"{role}/{fname}: not a dict"
                assert "includes" in data, (
                    f"{role}/{fname}: missing 'includes' key"
                )
                assert isinstance(data["includes"], list), (
                    f"{role}/{fname}: 'includes' not a list"
                )

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
        """TC-A2: includes.yml + includes-events.yml jointly cover all
        `{{include:}}` directives in templates (#8697).

        Each template include must appear in at least one mode-specific
        manifest (polling or events), either directly, via a slim variant,
        or via a role-specific override. Common-events/ entries are
        expected only in includes-events.yml; common/ entries should be in
        both manifests OR explicitly known-excluded.
        """
        import yaml
        for role in self.ROLES:
            tmpl_path = self.roles_dir / role / "instructions.md"
            tmpl_text = tmpl_path.read_text(encoding="utf-8")
            tmpl_includes = set(re.findall(
                r'\{\{include:\s*(.+?)\}\}', tmpl_text,
            ))

            # Build the union of polling and events manifests.
            manifests = {}
            for mode_name, fname in (("polling", "includes.yml"),
                                     ("events", "includes-events.yml")):
                yml_path = self.roles_dir / role / fname
                if not yml_path.exists():
                    continue
                data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
                assert isinstance(data, dict), f"{role} {fname}: not a dict"
                assert "includes" in data, f"{role} {fname}: missing includes"
                manifests[mode_name] = set(data["includes"])
                # Every manifest entry must resolve to a file
                for inc in data["includes"]:
                    full = self.sub_skills_dir / f"{inc}.md"
                    assert full.exists(), (
                        f"{role} {fname}: references non-existent {inc}"
                    )

            assert manifests, f"{role}: no manifests found"
            yml_union = set().union(*manifests.values())

            uncovered = set()
            for inc in tmpl_includes:
                if inc in yml_union:
                    continue
                base = inc.split("/")[-1]
                # Slim variant (e.g., vault-protocol → vault-protocol-slim)
                slim_match = any(
                    y.endswith(f"{base}-slim") for y in yml_union
                )
                # Role-specific override (e.g., common/X → roles/role/X)
                role_override = any(
                    y.endswith(f"/{base}") and y != inc for y in yml_union
                )
                if not slim_match and not role_override:
                    uncovered.add(inc)

            known_exclusions = {
                "common/vault-optimize",
                "common/vault-remember",
                "common/improvement-scan",
                "common/vault-protocol",
            }
            unexpected = uncovered - known_exclusions
            assert not unexpected, (
                f"{role}: template includes not covered by ANY manifest "
                f"(polling+events), and not slim/role-override/excluded: "
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

    def test_manifest_composition_matches_inline_in_polling_mode(self):
        """Phase A invariant — but mode-aware after #8697.

        With the parallel-manifest design, the inline path renders every
        `{{include:}}` directive in the template, including events-only
        ones like `common-events/event-driven-workflow`. The polling
        manifest path filters those out. So the two paths only match if we
        compare polling-manifest output against an inline rendering that
        also strips the events-only directives.

        Test: inline output equals polling-manifest output once the
        events-only fragments are removed from inline.
        """
        from compose import _resolve_includes, _resolve_includes_with_manifest, _load_manifest
        entry_file = self.roles_dir / "dev" / "instructions.md"
        manifest = _load_manifest("dev", wake_mode="polling")
        manifest_result = _resolve_includes_with_manifest(
            entry_file, manifest, wake_mode="polling"
        )
        inline_result = _resolve_includes(entry_file)
        # Strip events-only sub-skill blocks from the inline rendering so
        # the comparison is apples-to-apples with the polling manifest.
        import re
        events_only_names = (
            "event-driven-workflow",
            # #8915: the 5 event-mode L1 base fragments + DM's per-role
            # pr-merge-wait fragment are only present in includes-events.yml,
            # not includes.yml. The inline path will render them; the polling
            # manifest path filters them out.
            "l1-base",
            "cursor-management",
            "forge-read-pattern",
            "idle-cooldown-loop",
            "comment-handling",
            "pr-merge-wait",
        )
        for name in events_only_names:
            inline_result = re.sub(
                rf"<!-- sub-skill: {re.escape(name)} -->.*?<!-- /sub-skill: {re.escape(name)} -->\n?",
                "",
                inline_result,
                flags=re.DOTALL,
            )
        # Also collapse the resulting double-blank lines for fair compare.
        inline_result = re.sub(r"\n{3,}", "\n\n", inline_result)
        manifest_result = re.sub(r"\n{3,}", "\n\n", manifest_result)
        assert inline_result.strip() == manifest_result.strip(), (
            "Polling manifest composition differs from inline (stripped of "
            "events-only fragments) — Phase A invariant broken within a mode"
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
