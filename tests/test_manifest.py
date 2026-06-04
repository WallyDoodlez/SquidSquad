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

        Scope (#10861): only **numbered list entries** inside the
        ``## Composition Order`` section count as real include targets.
        Backticked prose in surrounding paragraphs (retirement notes
        like ``### Legacy Sub-Skills``, narrative mentions, etc.) is
        skipped — such mentions reference files that may have been
        deleted or carry an explicit ``.md`` suffix for narrative
        purposes, which would yield false-positive missing-file failures.
        """
        for inc in self._extract_composition_order_includes(self.manifest_text):
            # Defensive: a manifest numbered-list entry should never carry
            # an explicit ``.md`` suffix (this loop appends it). Skip if
            # one slips in — it's prose, not a manifest target.
            if inc.endswith(".md"):
                continue
            path = self.sub_skills_dir / f"{inc}.md"
            assert path.exists(), f"Sub-skill file missing: {path}"

    @staticmethod
    def _extract_composition_order_includes(text: str) -> list:
        """Return manifest include targets from ``## Composition Order``.

        Walks the section line by line and captures backticked
        ``namespace/name`` references only from **numbered list items**
        of the form ``N. <backticked-path> — description``. Paragraph
        prose and ``### Legacy Sub-Skills`` retirement notes are ignored
        even though they share the section's enclosing scope. The walk
        stops at the next top-level H2.
        """
        in_section = False
        includes = []
        entry_re = re.compile(r'^\s*\d+\.\s+.*?`((?:common|roles)/[^`]+)`')
        for line in text.splitlines():
            if re.match(r'^##\s+Composition Order\s*$', line):
                in_section = True
                continue
            if in_section and re.match(r'^##\s+\S', line):
                break
            if not in_section:
                continue
            m = entry_re.match(line)
            if m:
                includes.append(m.group(1))
        return includes

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

        # #10862: role instructions reference sub-skills via the
        # ``→ run sub-skill: <name>`` directive grammar (per
        # ``common/base-l1-instructions.md`` step-id contract). These
        # references are resolved by compose at inline time, not via
        # ``includes.yml``, so the manifest-only scan above doesn't see
        # them. Walk every ``references/roles/**/instructions.md`` for
        # the directive and mark any file whose stem matches the named
        # sub-skill as referenced.
        directive_names = self._collect_run_subskill_directive_names()
        if directive_names:
            for md_rel in all_md:
                stem = Path(md_rel).stem
                if stem in directive_names:
                    referenced.add(md_rel)

        # #8697: common/event-reactions.md exists but isn't referenced by
        # any current role manifest. It's a sub-skill that may be wired in
        # for future event-driven needs; explicitly tolerate its
        # un-referenced state rather than block the build.
        known_unused = {"common/event-reactions.md"}
        orphans = all_md - referenced - known_unused
        assert not orphans, f"Sub-skill files not referenced in manifest: {orphans}"

    @staticmethod
    def _collect_run_subskill_directive_names() -> set:
        """Return the set of bare sub-skill names referenced via the
        ``→ run sub-skill: <name>`` directive grammar in any
        ``references/roles/**/instructions.md`` file.

        The directive is the base-layer mechanism by which role
        instructions point at a sub-skill that compose will inline; it
        does NOT live in any ``includes.yml``. Names are bare kebab-case
        identifiers (e.g. ``l4-curation``) — file resolution happens at
        compose time across ``common/`` and ``roles/<role>/``.
        """
        roles_dir = REFERENCES_DIR / "roles"
        if not roles_dir.exists():
            return set()
        directive_re = re.compile(r'→\s*run\s+sub-skill:\s*([A-Za-z0-9][\w-]*)')
        names = set()
        for instr in roles_dir.rglob("instructions.md"):
            text = instr.read_text(encoding="utf-8")
            for m in directive_re.finditer(text):
                names.add(m.group(1))
        return names

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


# TestComposeManifestIntegration retired in E6 #10685 Phase 3d.5 — every
# member exercised v1 helpers (``_load_manifest``, ``_resolve_includes``,
# ``_resolve_includes_with_manifest``, ``compose_role``) that were deleted
# alongside the v1 chain. The v2 manifest is exercised by
# ``test_manifest_v2`` + ``test_compose_a*``; the unified ``includes.yml``
# integrity tests in TestIncludesYml above already validate manifest
# structure post-cutover.
