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
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = REPO_ROOT / "SKILL.md"
WIZARD_MD = REPO_ROOT / "references" / "wizard" / "WIZARD.md"
CLI_JS = REPO_ROOT / "packages" / "cli" / "index.js"


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
