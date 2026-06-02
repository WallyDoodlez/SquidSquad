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

        # Also scan includes.yml files for additional_includes (Layer 3
        # variants). Post-E6 (#10685) v2-cutover the includes-events.yml
        # split is retired — there is one unified manifest per role.
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

        # #9588: mode-specific fragments are Read at runtime by
        # `common/boot-bootstrap.md` instead of being inlined via manifest.
        # Treat any fragment whose path appears inside the bootstrap text
        # as referenced — broken paths there are caught by a dedicated
        # test in test_compose_9588.py, so duplicating that check here
        # would just couple the orphan-scan to bootstrap formatting.
        bootstrap_path = self.sub_skills_dir / "common" / "boot-bootstrap.md"
        if bootstrap_path.exists():
            bootstrap_text = bootstrap_path.read_text(encoding="utf-8")
            for rel_str in re.findall(
                r"references/sub-skills/([^\s`)]+\.md)", bootstrap_text
            ):
                referenced.add(rel_str)
            # The polling-fragment path is templated via the
            # `[POLLING_FRAGMENT_PATH]` placeholder so the bootstrap
            # text itself never spells out each role's polling fragment
            # literally. Compose substitutes per role — see
            # compose._substitute_placeholders. Mark every shipped
            # role's polling fragment as referenced if the placeholder
            # is in the bootstrap.
            if "[POLLING_FRAGMENT_PATH]" in bootstrap_text:
                roles_dir = self.sub_skills_dir / "roles"
                for ralph in roles_dir.rglob("ralph-loop-overview.md"):
                    referenced.add(
                        ralph.relative_to(self.sub_skills_dir).as_posix()
                    )

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

    ROLES = ["worker", "pm", "verifier", "dm"]

    @pytest.fixture(autouse=True, scope="class")
    def _setup(self, request):
        request.cls.roles_dir = REFERENCES_DIR / "roles"
        request.cls.sub_skills_dir = REFERENCES_DIR / "sub-skills"

    def test_includes_yml_exists_per_role(self):
        """TC-A1: Each role directory has includes.yml. The pre-E6
        includes-events.yml mode split (#8697) was retired by the
        v2 cutover (#10685) — a single unified manifest per role."""
        for role in self.ROLES:
            path = self.roles_dir / role / "includes.yml"
            assert path.exists(), f"Missing includes.yml for {role}"

    def test_includes_yml_valid_yaml(self):
        """TC-X6: All manifests are valid YAML with expected structure."""
        import yaml
        for role in self.ROLES:
            path = self.roles_dir / role / "includes.yml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"{role}/includes.yml: not a dict"
            assert "includes" in data, (
                f"{role}/includes.yml: missing 'includes' key"
            )
            assert isinstance(data["includes"], list), (
                f"{role}/includes.yml: 'includes' not a list"
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
        """TC-A2: includes.yml covers all `{{include:}}` directives in
        the role's template.

        Each template include must appear in the role's manifest, either
        directly, via a slim variant, or via a role-specific override.
        Mode-specific (event-driven) fragments are Read at runtime via
        `common/boot-bootstrap` and intentionally absent from the manifest.

        Pre-E6 (#10685) this used to take the union of polling and events
        manifests (#8697 dual-mode); the cutover unified into a single
        per-role manifest.
        """
        import yaml
        for role in self.ROLES:
            tmpl_path = self.roles_dir / role / "instructions.md"
            tmpl_text = tmpl_path.read_text(encoding="utf-8")
            tmpl_includes = set(re.findall(
                r'\{\{include:\s*(.+?)\}\}', tmpl_text,
            ))

            yml_path = self.roles_dir / role / "includes.yml"
            data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
            assert isinstance(data, dict), f"{role} includes.yml: not a dict"
            assert "includes" in data, f"{role} includes.yml: missing includes"
            yml_union = set(data["includes"])
            # Every manifest entry must resolve to a file
            for inc in data["includes"]:
                full = self.sub_skills_dir / f"{inc}.md"
                assert full.exists(), (
                    f"{role} includes.yml: references non-existent {inc}"
                )

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

            # #9588: mode-specific includes are intentionally NOT in any
            # manifest. compose skips them; the agent Reads them at runtime
            # via `common/boot-bootstrap`. The directives stay in the
            # template as architectural documentation of the fragments
            # involved on each mode branch. Add them to the exclusion set
            # so this coverage test does not flag them as orphans —
            # test_compose_9588.py asserts the bootstrap actually wires
            # them up at runtime.
            mode_specific_runtime_loaded = {
                "common-events/event-driven-workflow",
                "common-events/l1-base",
                "common-events/cursor-management",
                "common-events/forge-read-pattern",
                "common-events/idle-cooldown-loop",
                "common-events/comment-handling",
                "roles/worker/ralph-loop-overview",
                "roles/pm/ralph-loop-overview",
                "roles/verifier/ralph-loop-overview",
                "roles/dm/ralph-loop-overview",
                "roles/dm/events/pr-merge-wait",
            }
            unexpected = uncovered - known_exclusions - mode_specific_runtime_loaded
            assert not unexpected, (
                f"{role}: template includes not covered by includes.yml, "
                f"and not slim/role-override/excluded: "
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
        """Worker variants inherit worker's manifest via base_role (post-6274.2).

        Pre-6274.2 the legacy bare-name fallback (`_load_manifest('skill')`)
        returned `dev`'s manifest verbatim because `roles/<variant>/includes.yml`
        was absent. Post-6274.2 each variant has its own `includes.yml` with
        `base_role: worker`, so the canonical inheritance check is now done
        through the hyphenated variant form (`worker-skill`) and asserts the
        base's manifest is a subset of the variant's expanded manifest.
        """
        from compose import _load_manifest
        worker_manifest = _load_manifest("worker")
        skill_manifest = _load_manifest("worker-skill")
        assert worker_manifest, "worker manifest should be non-empty"
        assert skill_manifest, "worker-skill manifest should be non-empty"
        assert set(worker_manifest).issubset(set(skill_manifest)), (
            "worker-skill should inherit every include from worker"
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
        entry_file = self.roles_dir / "worker" / "instructions.md"
        manifest = _load_manifest("worker", wake_mode="polling")
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
            # #9588: the polling-mode ralph-loop-overview is now Read at
            # runtime via boot-bootstrap rather than inlined via manifest.
            # The inline path still renders it (the directive is in the
            # template); strip it so the comparison stays apples-to-apples
            # with the post-#9588 polling manifest output.
            "ralph-loop-overview",
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
