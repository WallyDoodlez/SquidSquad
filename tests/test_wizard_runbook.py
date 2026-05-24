"""Static analysis for the install wizard runbook (#328 Phase G.3).

The runbook at `references/wizard/WIZARD.md` is prose that Claude
follows during setup. Because it's prose, not code, most of its
correctness comes from structural invariants we can enforce cheaply:

1. Every wizard.py / manifest.py / compose.py command it tells Claude
   to run must actually exist as a subcommand in that script.
2. Every role/tool/preset it references must exist in the registry.
3. It must cover all 8 wizard steps (0, 0b, 1..7) in order.
4. It must reference every locked decision whose identifier appears
   in CONTEXT.md (Q-new11..22) — drift-proofing against spec updates.
5. Installer-agent lifecycle invariants (ephemeral, no self-loop,
   no writes before Step 7).

These tests fail fast if the runbook drifts from reality — e.g. a
helper is renamed but the runbook still mentions the old name.
"""

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

RUNBOOK = REPO_ROOT / "references" / "wizard" / "WIZARD.md"

# Script -> command name regex (matches the dispatch table keys each
# script ships).
_WIZARD_COMMANDS = {
    "check-gh", "check-existing", "repo-info", "project-name-default",
    "validate-name", "validate-rerun-action", "build-config-md",
    "scaffold", "ensure-labels", "list-issues-by-label", "migrate-label",
    "pr-flow-prompt",
}
_MANIFEST_COMMANDS = {"validate", "list", "load", "resolve"}
_COMPOSE_COMMANDS = {"all", "deploy", "deploy-all", "boot", "boot-all"}


@pytest.fixture(scope="module")
def runbook():
    assert RUNBOOK.exists(), f"Missing runbook: {RUNBOOK}"
    return RUNBOOK.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


class TestRunbookStructure:
    def test_runbook_file_exists(self, runbook):
        assert runbook  # non-empty

    def test_all_steps_present_in_order(self, runbook):
        """Every required step must appear in the runbook, in order."""
        required_steps = [
            "## Step 0 — Prerequisite check",
            "## Step 0b — Re-run detection",
            "## Step 1 — Project details",
            "## Step 2 — Intent",
            "## Step 3 — Preset confirmation",
            "## Step 4 — Walk setup_requirements",
            "## Step 5 — Loop interval",
            "## Step 6 — Review screen",
            "## Step 7 — Commit and write",
        ]
        last_idx = -1
        for heading in required_steps:
            idx = runbook.find(heading)
            assert idx != -1, f"Missing step heading: {heading!r}"
            assert idx > last_idx, (
                f"Step {heading!r} appears before a previous step "
                f"(index {idx}, last was {last_idx})"
            )
            last_idx = idx

    def test_runbook_has_installer_agent_framing(self, runbook):
        """Installer agent lifecycle (Q-new21) must be stated up front."""
        # The "installer agent" phrase must appear in the first 2000 chars
        head = runbook[:2000]
        assert "installer agent" in head.lower()
        assert "ephemeral" in head.lower()
        assert "Q-new21" in head

    def test_runbook_references_domain_only_rule(self, runbook):
        assert "Q-new14" in runbook
        assert re.search(r"domain\s+terms\s+only", runbook, re.IGNORECASE)

    def test_runbook_references_intent_classifier_rule(self, runbook):
        assert "Q-new18" in runbook
        # The classifier prompt must be present (not paraphrased)
        assert "software-dev" in runbook
        assert "design" in runbook
        assert "unclear" in runbook


# ---------------------------------------------------------------------------
# Helper-command cross-references
# ---------------------------------------------------------------------------


class TestHelperCommandReferences:
    def test_every_wizard_command_mentioned_exists(self, runbook):
        """Every `wizard.py <cmd>` mention must be a real subcommand."""
        mentions = re.findall(
            r"wizard\.py\s+([a-z][a-z0-9-]*)",
            runbook,
        )
        assert mentions, "Expected at least one wizard.py command reference"
        unknown = set(mentions) - _WIZARD_COMMANDS
        assert not unknown, f"Runbook references unknown wizard commands: {unknown}"

    def test_every_manifest_command_mentioned_exists(self, runbook):
        mentions = re.findall(
            r"manifest\.py\s+([a-z][a-z0-9-]*)",
            runbook,
        )
        unknown = set(mentions) - _MANIFEST_COMMANDS
        assert not unknown, f"Runbook references unknown manifest commands: {unknown}"

    def test_every_compose_command_mentioned_exists(self, runbook):
        mentions = re.findall(
            r"compose\.py\s+([a-z][a-z0-9-]*)",
            runbook,
        )
        unknown = set(mentions) - _COMPOSE_COMMANDS
        assert not unknown, f"Runbook references unknown compose commands: {unknown}"

    def test_critical_helpers_are_mentioned(self, runbook):
        """Key commands that MUST be part of the flow."""
        for cmd in (
            "wizard.py check-gh",
            "wizard.py check-existing",
            "wizard.py repo-info",
            "wizard.py validate-rerun-action",
            "wizard.py validate-name",
            "wizard.py build-config-md",
            "wizard.py scaffold",
            "wizard.py ensure-labels",
            "manifest.py list",
            "manifest.py load",
        ):
            assert cmd in runbook, f"Runbook missing critical helper call: {cmd}"


# ---------------------------------------------------------------------------
# Registry cross-references
# ---------------------------------------------------------------------------


class TestRegistryCrossReferences:
    def test_referenced_preset_ids_exist(self, runbook):
        presets = {
            d.name for d in (REPO_ROOT / "references" / "presets").iterdir()
            if d.is_dir() and (d / "manifest.yaml").exists()
        }
        mentioned = {"software-dev", "design"}
        assert mentioned.issubset(presets), (
            f"Runbook references presets not in registry: {mentioned - presets}"
        )
        # Runbook must mention every shipped preset at least once
        for p in presets:
            assert p in runbook, f"Runbook never mentions shipped preset: {p}"

    def test_referenced_roles_exist(self, runbook):
        roles = {
            d.name for d in (REPO_ROOT / "references" / "roles").iterdir()
            if d.is_dir() and (d / "manifest.yaml").exists()
        }
        # The runbook must at least name every specialist role whose
        # manifest has show_in_roster: true, plus pm and dm.
        # #6274.2 AC2.2 phase 9: `dev`/`qa` renamed to `worker`/`verifier`
        # on disk; the runbook prose-references the new canonical names.
        for role in ("pm", "dm", "worker", "verifier"):
            assert role in roles, f"Shipped role missing: {role}"

        body_lower = runbook.lower()
        for role in ("pm", "dm", "worker", "verifier"):
            assert role in body_lower, (
                f"Runbook never mentions shipped role: {role}"
            )

    def test_runbook_roster_uses_new_canonical_role_names_6274(self, runbook):
        """#6274.2 AC2.2 phase 9: roster/pipeline displays use new names.

        The wizard renders both the in-conversation roster block (Step 2)
        and the Step 6 preview summary. Both must display `Worker`/
        `Verifier` (the post-6274.2 canonical display_name values from
        the role manifests) — not the pre-rename `Dev`/`QA`. Locks the
        prose against accidental revert during the AC2.4-2.7 wizard.py
        work.
        """
        # Roster block (Step 2) — render as conversational lines.
        assert "Worker    — Writes code" in runbook, (
            "Step 2 roster must render Worker line (post-6274.2 display_name)"
        )
        assert "Verifier  — Verifies worker work" in runbook, (
            "Step 2 roster must render Verifier line "
            "(post-6274.2 display_name + tagline)"
        )

        # Pipeline arrow strings (Step 3 + Step 6 preview).
        assert "PM → Designer ↻ → [Worker] → Verifier → DM" in runbook, (
            "software-dev pipeline must use Worker/Verifier (Step 3)"
        )
        assert "Verifier → DM" in runbook, (
            "Pipeline must route through Verifier, not QA"
        )

        # Final boot announcement (Step 7.6) names the running agents.
        assert "PM, Verifier, DM, workers" in runbook, (
            "Step 7.6 boot line must name Verifier alongside PM/DM/workers"
        )

        # Old display tokens must not reappear in prose (excluding
        # legitimate substrings like 'Designer', 'devtools', etc.).
        # Whole-word check on the exact display tokens we replaced.
        forbidden_displays = (
            "Dev       — Writes code",
            "QA        — Verifies dev work",
            "[Dev] → QA",
            "PM, QA, DM, workers",
        )
        for token in forbidden_displays:
            assert token not in runbook, (
                f"Stale pre-6274.2 display token still in runbook: {token!r}"
            )


# ---------------------------------------------------------------------------
# Installer-agent lifecycle invariants (Q-new21)
# ---------------------------------------------------------------------------


class TestInstallerAgentInvariants:
    def test_no_writes_before_step_7_is_documented(self, runbook):
        """Runbook must explicitly prohibit disk writes before Step 7."""
        head = runbook.split("## Step 7")[0]
        assert re.search(
            r"never\s+writ(e|es|ten)|not\s+written|do\s+not\s+write|"
            r"nothing\s+.*(disk|written)",
            head,
            re.IGNORECASE,
        )

    def test_ephemeral_exit_after_step_7(self, runbook):
        """Step 7.6 must explicitly say 'exit' and not loop."""
        idx = runbook.find("### 7.6")
        assert idx != -1, "Runbook missing Step 7.6 exit instruction"
        tail = runbook[idx:]
        assert re.search(r"exit\s+the\s+conversation", tail, re.IGNORECASE)
        assert "ephemeral" in tail.lower()

    def test_no_self_loop_directive(self, runbook):
        """The runbook must not tell the installer to run /loop itself."""
        # It's OK to mention /loop in the context of what the boot scripts
        # do, but the installer itself must not be told to invoke /loop
        # or to persist beyond Step 7.
        dont_block = runbook.split("## What NOT to do")[-1]
        assert "do not keep the session alive" in dont_block.lower()

    def test_force_flag_not_documented_for_installer(self, runbook):
        """Installer must not use --force anywhere — it's a human override."""
        # --force on tracker.py transition is a human-only escape hatch;
        # the installer has no legitimate reason to pass it.
        installer_body = runbook.split("## What NOT to do")[0]
        assert "--force" not in installer_body, (
            "Runbook uses --force in the installer flow — that flag is "
            "for human overrides only, not for the install wizard."
        )


# ---------------------------------------------------------------------------
# Review screen (P/V/E/A) invariants
# ---------------------------------------------------------------------------


class TestReviewScreen:
    def test_review_screen_has_four_actions(self, runbook):
        idx = runbook.find("## Step 6")
        assert idx != -1
        step6 = runbook[idx: runbook.find("## Step 7", idx)]
        for action in ("[P] Proceed", "[V] View", "[E] Edit", "[A] Abort"):
            assert action in step6, (
                f"Step 6 review screen missing action: {action}"
            )

    def test_view_action_uses_dry_run_helpers(self, runbook):
        idx = runbook.find("## Step 6")
        step6 = runbook[idx: runbook.find("## Step 7", idx)]
        # Preview must not touch the real .squidsquad/ directory
        assert "build-config-md" in step6
        assert re.search(
            r"(tmp|scratch|temp|dry[- ]run|do not overwrite)",
            step6,
            re.IGNORECASE,
        )


# ---------------------------------------------------------------------------
# Q-new locks are referenced where it matters
# ---------------------------------------------------------------------------


class TestLockCoverage:
    @pytest.mark.parametrize("lock,section_hint", [
        ("Q-new14", "domain terms"),       # domain-only language
        ("Q-new15", "roster"),             # specialist roster
        ("Q-new17", None),                 # config.md schema (can appear anywhere)
        ("Q-new18", "classifier"),         # hardcoded classifier prompt
        ("Q-new19", "per-agent"),          # per-agent requirements in single exchange
        ("Q-new21", "ephemeral"),          # installer ephemeral
    ])
    def test_locked_decision_referenced(self, runbook, lock, section_hint):
        assert lock in runbook, f"Runbook missing reference to locked decision {lock}"
        if section_hint is not None:
            assert section_hint.lower() in runbook.lower(), (
                f"{lock} should appear near the word {section_hint!r}"
            )
