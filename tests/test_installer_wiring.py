"""Static consistency checks for the npx install flow (#328 Phase G.4).

After Phase G.3 shipped the prose runbook at `references/wizard/WIZARD.md`,
Phase G.4 rewires three places to point at it instead of the legacy
inline setup in SKILL.md:

  1. `SKILL.md` — its "Setup Instructions" section is a thin pointer to
     the runbook (not the full step-by-step content it used to contain).
  2. `packages/cli/index.js` — `npx squidsquad` must fetch BOTH SKILL.md
     and the wizard runbook, and commit both as seed files.
  3. `.claude/commands/squidsquad-setup.md` (seeded by the CLI) — the
     slash command prose must point at the runbook, not at SKILL.md's
     Setup Instructions section.

These tests enforce the three-way consistency at static-analysis time so
a rename or path change in any one file is caught immediately.
"""

import re
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = REPO_ROOT / "SKILL.md"
WIZARD_MD = REPO_ROOT / "references" / "wizard" / "WIZARD.md"
CLI_JS = REPO_ROOT / "packages" / "cli" / "index.js"

# #12861: the sub-skill marker-completeness gate reuses the SAME catalog
# resolver the compose catalog gate runs at deploy time (compose.py:1217),
# so a `→ run sub-skill: <name>` reference resolves to its source path
# exactly as runtime does.
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
import catalog_parser as _catalog_parser  # noqa: E402

# Backtick-tolerant marker matcher. v2_catalog_gate._REF_RE matches only
# BARE names — fine for composed output (the link stage emits markers
# bare), but markers hand-authored INSIDE a sub-skill body are styled
# with backticks (e.g. git-commit.md's ``→ run sub-skill: `pr-protocol` ``).
# The completeness gate must follow those chained references, so it
# tolerates the optional backticks the shared regex does not.
_SUBSKILL_MARKER_RE = re.compile(r"→\s+run\s+sub-skill:\s+`?([a-z][a-z0-9/_-]*)`?")


@pytest.fixture(scope="module")
def skill_md():
    assert SKILL_MD.exists(), f"Missing {SKILL_MD}"
    return SKILL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cli_js():
    assert CLI_JS.exists(), f"Missing {CLI_JS}"
    return CLI_JS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# SKILL.md — Setup Instructions is a pointer, not a reimplementation
# ---------------------------------------------------------------------------


class TestSkillMdSetupInstructions:
    def test_setup_section_present(self, skill_md):
        assert "## Setup Instructions" in skill_md

    def test_setup_section_points_at_runbook(self, skill_md):
        """The section body must reference the canonical runbook path."""
        setup = _extract_section(skill_md, "## Setup Instructions", "## Upgrade Instructions")
        assert "references/wizard/WIZARD.md" in setup, (
            "SKILL.md Setup Instructions section must reference the "
            "canonical install wizard runbook at references/wizard/WIZARD.md"
        )

    def test_setup_section_is_concise(self, skill_md):
        """Must not be 600+ lines of inline setup steps anymore."""
        setup = _extract_section(skill_md, "## Setup Instructions", "## Upgrade Instructions")
        # The pointer section should be well under 150 lines
        assert setup.count("\n") < 150, (
            f"Setup Instructions block is {setup.count(chr(10))} lines — "
            f"it should be a thin pointer (<150 lines) after #328 G.4, "
            f"not an inline reimplementation of the wizard flow."
        )

    def test_setup_section_no_legacy_inline_steps(self, skill_md):
        """The old inline step headings should be gone from SKILL.md."""
        setup = _extract_section(skill_md, "## Setup Instructions", "## Upgrade Instructions")
        legacy_markers = [
            "### Step 0 — Clean Worktree Check",
            "### Step 1 — Gather Project Details",
            "### Step 2 — Create `.squidsquad/` Folder Structure",
            "### Step 3 — Generate `config.md`",
            "### Step 4 — Generate Templates",
            "### Step 5 — Generate Boot Scripts",
            "### Step 6 — Seed GitHub Issues Labels",
            "### Step 7 — Configure SessionStart Hook",
            "### Step 8 — Commit and Push",
            "### Step 9 — Confirm Setup",
        ]
        stragglers = [m for m in legacy_markers if m in setup]
        assert not stragglers, (
            f"SKILL.md Setup Instructions still contains legacy step "
            f"headings: {stragglers}"
        )

    def test_runbook_referenced_in_setup_exists(self, skill_md):
        """Every `references/...` path in the Setup block must exist."""
        setup = _extract_section(skill_md, "## Setup Instructions", "## Upgrade Instructions")
        refs = re.findall(
            r"`(references/(?:wizard|scripts|roles|tools|presets)[A-Za-z0-9_./<>-]*)`",
            setup,
        )
        for ref in refs:
            # Skip template placeholders like references/roles/<role>/
            if "<" in ref or ">" in ref:
                continue
            path = REPO_ROOT / ref
            assert path.exists(), f"Setup Instructions references missing path: {ref}"

    def test_dangling_step_4b_refs_fixed(self, skill_md):
        """Upgrade Instructions must not reference 'Step 4b in Setup Instructions'."""
        assert "Step 4b in Setup Instructions" not in skill_md, (
            "Upgrade Instructions still points at the deleted 'Step 4b in "
            "Setup Instructions' — these refs must be replaced with a "
            "pointer to compose.py or the role directory structure."
        )


# ---------------------------------------------------------------------------
# packages/cli/index.js — fetches SKILL.md AND the runbook
# ---------------------------------------------------------------------------


class TestCliIndexJs:
    def test_cli_file_exists(self, cli_js):
        assert cli_js

    def test_fetches_file_manifest(self, cli_js):
        """#373 — npx squidsquad must fetch the file manifest first."""
        assert 'fetchRawFile("references/installer-files.txt")' in cli_js, (
            "packages/cli/index.js must fetch the installer file manifest "
            "as the first step, then fetch every file listed in it"
        )

    def test_manifest_driven_fetch_loop(self, cli_js):
        """Files are fetched from the manifest, not hardcoded one-by-one."""
        assert "filePaths" in cli_js or "filePath" in cli_js
        assert "fetchRawFile(filePath)" in cli_js, (
            "CLI must loop over manifest entries and fetchRawFile each one"
        )

    def test_fetchRawFile_has_path_validation_guard(self, cli_js):
        """#6316 — fetchRawFile must validate repoPath against shell metacharacters."""
        assert "/^[\\w.\\/\\-]+$/" in cli_js, (
            "fetchRawFile must have a regex guard rejecting shell metacharacters "
            "before interpolating repoPath into shell commands"
        )

    def test_writes_files_to_canonical_paths(self, cli_js):
        """Each fetched file must be written to a validated path in the target."""
        assert "assertWithinRoot(gitRoot, filePath)" in cli_js, (
            "CLI must write each fetched file to a validated path "
            "relative to the target git root (via assertWithinRoot)"
        )

    def test_commits_references_directory(self, cli_js):
        """Seed commit must stage the entire references/ directory."""
        commit_block = _extract_commit_block(cli_js)
        assert "references/" in commit_block, (
            "Seed commit must stage references/ (contains all wizard "
            "infrastructure fetched from the manifest)"
        )

    def test_slash_command_points_at_runbook_not_skill_md(self, cli_js):
        """The setup slash command prose must target WIZARD.md, not SKILL.md."""
        cmd = _extract_setup_command_prose(cli_js)
        assert "references/wizard/WIZARD.md" in cmd, (
            "slash command must instruct Claude to read the wizard runbook"
        )
        # And NOT the legacy "read SKILL.md's Setup Instructions" prose
        assert '"Setup Instructions" section' not in cmd, (
            "slash command still references the legacy "
            "'SKILL.md Setup Instructions section' language"
        )

    def test_slash_command_mentions_ephemeral_installer(self, cli_js):
        """Q-new21 — installer lifecycle must be stated in the slash command."""
        cmd = _extract_setup_command_prose(cli_js)
        assert "installer agent" in cmd.lower()
        assert "ephemeral" in cmd.lower()

    def test_slash_command_mentions_nothing_before_step_7(self, cli_js):
        """The 'no writes before Step 7' invariant must be in the slash command."""
        cmd = _extract_setup_command_prose(cli_js)
        assert re.search(r"Step\s*7", cmd)
        assert re.search(r"(abort|no\s+trace|nothing\s+touches)", cmd, re.IGNORECASE)

    def test_cli_still_pre_checks_gh_python_claude(self, cli_js):
        """Existing prereq checks must not regress."""
        assert "checkNodeVersion" in cli_js
        assert "checkGitRepo" in cli_js
        assert "checkPython" in cli_js
        assert "checkGhCli" in cli_js
        assert "checkClaudeCli" in cli_js


# ---------------------------------------------------------------------------
# WIZARD.md — the target must exist at the canonical path
# ---------------------------------------------------------------------------


class TestWizardRunbookExists:
    def test_runbook_file_exists(self):
        assert WIZARD_MD.is_file(), (
            f"Canonical install wizard runbook missing at {WIZARD_MD}"
        )

    def test_runbook_is_non_trivial(self):
        content = WIZARD_MD.read_text(encoding="utf-8")
        # Must be at least 2KB of actual content
        assert len(content) > 2000, (
            f"WIZARD.md is suspiciously short ({len(content)} bytes)"
        )


# ---------------------------------------------------------------------------
# installer-files.txt — the deterministic pre-fetch manifest (#373)
# ---------------------------------------------------------------------------


INSTALLER_MANIFEST = REPO_ROOT / "references" / "installer-files.txt"


class TestInstallerFileManifest:
    @pytest.fixture(scope="class")
    def manifest_entries(self):
        assert INSTALLER_MANIFEST.is_file(), (
            f"Missing installer file manifest at {INSTALLER_MANIFEST}"
        )
        text = INSTALLER_MANIFEST.read_text(encoding="utf-8")
        return [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    def test_manifest_exists(self):
        assert INSTALLER_MANIFEST.is_file()

    def test_manifest_lists_critical_files(self, manifest_entries):
        """Key files the wizard cannot function without."""
        for critical in (
            "SKILL.md",
            "references/wizard/WIZARD.md",
            "references/scripts/wizard.py",
            "references/scripts/manifest.py",
            "references/scripts/compose.py",
            "references/scripts/config.py",
            "references/scripts/tracker.py",
            "references/roles/pm/manifest.yaml",
            "references/roles/pm/instructions.md",
            "references/roles/pm/SOUL.md",
            "references/roles/worker/instructions.md",
            "references/presets/software-dev/manifest.yaml",
            "references/presets/design/manifest.yaml",
        ):
            assert critical in manifest_entries, (
                f"installer-files.txt missing critical file: {critical}"
            )

    def test_every_listed_file_exists_on_disk(self, manifest_entries):
        """Every path in the manifest must exist — no stale entries."""
        missing = [
            f for f in manifest_entries
            if not (REPO_ROOT / f).exists()
        ]
        assert not missing, (
            f"installer-files.txt lists files that don't exist: {missing}"
        )

    def test_no_duplicate_entries(self, manifest_entries):
        dupes = [f for f in manifest_entries if manifest_entries.count(f) > 1]
        assert not dupes, f"Duplicate entries in installer-files.txt: {set(dupes)}"

    def test_l4_subsystem_scripts_listed(self, manifest_entries):
        """#12907: the L4 customization + file-watch subsystem must ship.

        harness.py imports l4_file_watcher (start_l4_watcher) and the L4
        customization pipeline (parser/op-processor/audit-gate/…) is
        driven at runtime — none of these were in the manifest, so fresh
        installs received no L4 subsystem. Lock the whole family so the
        omission can't silently recur.
        """
        l4_scripts = sorted(
            f"references/scripts/{p.name}"
            for p in (REPO_ROOT / "references" / "scripts").glob("l4_*.py")
        )
        assert l4_scripts, "no l4_*.py scripts found on disk — test stale"
        missing = [s for s in l4_scripts if s not in manifest_entries]
        assert not missing, (
            f"installer-files.txt missing L4 subsystem scripts: {missing}"
        )

    def test_header_total_matches_entry_count(self):
        """The '# Total: N files' header must match the real entry count.

        A stale header is the canary for an add-without-counting edit —
        the omission that left the L4 family (#12907) out for so long.
        """
        text = INSTALLER_MANIFEST.read_text(encoding="utf-8")
        m = re.search(r"#\s*Total:\s*(\d+)\s*files", text)
        assert m, "installer-files.txt is missing a '# Total: N files' header"
        declared = int(m.group(1))
        actual = sum(
            1 for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
        assert declared == actual, (
            f"installer-files.txt header says {declared} files but lists "
            f"{actual} — update the '# Total:' line when adding/removing entries"
        )

    # #12909: every references/scripts/*.py must be either shipped (in the
    # manifest) or explicitly excluded here with a reason. This is the
    # general completeness gate — it would have caught both the l4 family
    # (#12907) and this batch. Dev/CI/migration-only scripts that must NOT
    # ship to fresh installs go here; adding a new runtime script without
    # a manifest entry now fails CI instead of silently un-shipping a
    # whole subsystem (as happened with event_poll.py, statusline_data.py).
    MANIFEST_EXCLUDED_SCRIPTS = {
        # one-time #6274 label-rename migration + its verifier — historical,
        # never invoked at runtime; nothing to migrate on a fresh install.
        "references/scripts/migrate_labels_6274.py",
        "references/scripts/verify_dual_label_6274.py",
        # smoke-test helper for the Monitor event poller — dev/CI only.
        "references/scripts/monitor_smoke_poller.py",
    }

    def test_every_runtime_script_listed_or_excluded(self, manifest_entries):
        scripts_dir = REPO_ROOT / "references" / "scripts"
        on_disk = {
            f"references/scripts/{p.name}"
            for p in scripts_dir.glob("*.py")
        }
        listed = set(manifest_entries)
        unaccounted = sorted(
            s for s in on_disk
            if s not in listed and s not in self.MANIFEST_EXCLUDED_SCRIPTS
        )
        assert not unaccounted, (
            "references/scripts/*.py neither in installer-files.txt nor in "
            f"MANIFEST_EXCLUDED_SCRIPTS: {unaccounted}. Add runtime scripts "
            "to the manifest; add dev/CI/migration-only scripts to the "
            "allowlist with a reason."
        )

    def test_excluded_scripts_are_not_also_listed(self, manifest_entries):
        """An allowlisted script must not also be shipped (contradiction)."""
        listed = set(manifest_entries)
        both = sorted(self.MANIFEST_EXCLUDED_SCRIPTS & listed)
        assert not both, (
            f"scripts both allowlisted AND in the manifest: {both} — "
            "decide: ship it (drop from allowlist) or not (drop from manifest)"
        )

    def test_excluded_scripts_exist_on_disk(self):
        """Keep the allowlist honest — no stale entries for deleted scripts."""
        missing = sorted(
            s for s in self.MANIFEST_EXCLUDED_SCRIPTS
            if not (REPO_ROOT / s).exists()
        )
        assert not missing, (
            f"MANIFEST_EXCLUDED_SCRIPTS lists non-existent files: {missing}"
        )

    # #12861: the script-completeness gate above (#12909) protects
    # references/scripts/*.py. The two tests below are its sub-skill
    # analogue — they close the class that silently un-shipped
    # l4-curation / pr-protocol / tracker-protocol / task-pickup: a
    # sub-skill that an agent Reads at runtime (or that compose inlines)
    # but that installer-files.txt never lists, so a fresh `npx
    # squidsquad` install never fetches it and the reference dangles.

    def test_every_marker_referenced_subskill_listed(self, manifest_entries):
        """Every sub-skill reachable from a composed CLAUDE.md via
        `→ run sub-skill: <name>` markers — directly OR through a chain of
        sub-skill bodies — must resolve via the catalog to a source path
        that IS in installer-files.txt.

        Reactive/runtime-loaded sub-skills (l4-curation, pr-protocol,
        harness-restart, the per-role issue-filing variants, …) are NOT
        inlined — the agent Reads the source file from disk when it hits
        the marker. Markers also CHAIN: a composed CLAUDE.md references
        `git-commit`, whose body references `pr-protocol`. So the gate
        walks the transitive closure, not just the top-level references.
        Any file in that closure missing from the manifest would never be
        fetched by a fresh `npx squidsquad` install → the marker dangles.

        Unresolved names (no catalog row) are intentionally skipped here —
        catalog completeness is a separate concern owned by the compose
        catalog gate (test_v2_catalog_gate_d3), and skipping them also
        ignores illustrative markers inside sub-skill bodies (e.g. the
        `security-smoke` example op-block in l4-curation.md, which is never
        a real runtime reference).
        """
        catalog = _catalog_parser.parse_catalog(
            REPO_ROOT / "docs" / "sub-skill-catalog.md"
        )
        composed = sorted((REPO_ROOT / ".squidsquad").glob("*/CLAUDE.md"))
        assert composed, (
            "no composed .squidsquad/<alias>/CLAUDE.md found — expected the "
            "self-hosted install's deployed agent files"
        )

        def markers(text):
            return _SUBSKILL_MARKER_RE.findall(text)

        # Seed the closure with every marker in every composed CLAUDE.md,
        # then walk resolved sub-skill bodies until no new names appear.
        queue = []
        for path in composed:
            queue.extend(markers(path.read_text(encoding="utf-8")))
        resolved = {}  # name -> source_path
        seen = set()
        while queue:
            name = queue.pop()
            if name in seen:
                continue
            seen.add(name)
            source_path = catalog.get(name)
            if source_path is None:
                continue  # catalog-resolution is a separate gate's job
            resolved[name] = source_path
            body = REPO_ROOT / source_path
            if body.is_file():
                queue.extend(markers(body.read_text(encoding="utf-8")))

        listed = set(manifest_entries)
        dangling = sorted(sp for sp in set(resolved.values()) if sp not in listed)
        assert not dangling, (
            "sub-skills reachable from composed CLAUDE.md via `→ run "
            "sub-skill:` markers (incl. chained references) but NOT in "
            "installer-files.txt — a fresh npx install would never fetch "
            f"them, so the markers dangle: {dangling}"
        )

    def test_every_includes_yml_subskill_listed(self, manifest_entries):
        """Every sub-skill inlined at compose time via a role's
        includes.yml must be in installer-files.txt AND exist on disk.

        The wizard composes each agent from the FETCHED source on a fresh
        install (deploy_role_v2). A compose-time include that was never
        fetched fails the install's compose step — the same un-shipped
        class, surfaced at compose rather than at runtime.
        """
        listed = set(manifest_entries)
        problems = []  # (name, source_path, reason)
        for inc_yml in sorted((REPO_ROOT / "references" / "roles").glob("*/includes.yml")):
            data = yaml.safe_load(inc_yml.read_text(encoding="utf-8")) or {}
            for name in (data.get("includes") or []):
                source_path = f"references/sub-skills/{name}.md"
                if not (REPO_ROOT / source_path).is_file():
                    problems.append((source_path, inc_yml.parent.name, "missing-on-disk"))
                elif source_path not in listed:
                    problems.append((source_path, inc_yml.parent.name, "not-in-manifest"))
        assert not problems, (
            "includes.yml sub-skills not shippable on a fresh install: "
            + ", ".join(
                f"{sp} ({reason}, from roles/{role}/includes.yml)"
                for sp, role, reason in sorted(problems)
            )
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_section(text: str, start_heading: str, end_heading: str) -> str:
    """Return the text between two top-level headings, exclusive of the next."""
    start = text.find(start_heading)
    end = text.find(end_heading)
    assert start != -1, f"Missing heading: {start_heading!r}"
    assert end != -1, f"Missing heading: {end_heading!r}"
    assert start < end, f"{start_heading!r} appears after {end_heading!r}"
    return text[start:end]


def _extract_setup_command_prose(cli_js: str) -> str:
    """Return the text of the setupCommand JavaScript array literal."""
    match = re.search(
        r"const setupCommand = \[(.*?)\]\.join\(\"\\n\"\)",
        cli_js,
        re.DOTALL,
    )
    assert match, "packages/cli/index.js missing setupCommand array"
    return match.group(1)


def _extract_commit_block(cli_js: str) -> str:
    """Return the text of the git add block (we check path coverage)."""
    match = re.search(
        r'git add ([^"]+)"',
        cli_js,
    )
    assert match, "packages/cli/index.js missing git add invocation"
    return match.group(1)
