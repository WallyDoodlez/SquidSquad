"""Static analysis for the installer's operating manual (#328 G.3 → #13336).

The manual at `docs/INSTALLER-RUNTIME.md` is prose that the installer Claude
session follows during setup. It replaced the step-by-step runbook at
`references/wizard/WIZARD.md` (retired in #13336); the runbook's surviving
mechanics live in the manual's §9 helper playbook. Because the manual is
prose, not code, most of its correctness comes from structural invariants we
can enforce cheaply:

1. Every wizard.py / manifest.py / compose.py / model_router.py /
   forgejo_setup.py / shared_fs.py command it tells the installer to run
   must actually exist as a subcommand of that script.
2. Every preset/role it references must exist in the registry.
3. Its behavioral spine must be present in order — the top-level sections,
   the §4 flow steps 0–9, and the §9 playbook step sections.
4. Installer-agent lifecycle invariants (ephemeral, no self-loop, no writes
   before step 7 / Apply, no --force, verbatim consent).

These tests fail fast if the manual drifts from reality — e.g. a helper is
renamed but the manual still mentions the old name.
"""

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

MANUAL = REPO_ROOT / "docs" / "INSTALLER-RUNTIME.md"

# Script -> command name allowlists (matching the dispatch table keys each
# script ships). A mention outside these sets means the manual references a
# subcommand that does not exist.
_WIZARD_COMMANDS = {
    "check-gh", "check-existing", "repo-info", "project-name-default",
    "validate-name", "validate-rerun-action", "build-config-md",
    "scaffold", "ensure-labels", "list-issues-by-label", "migrate-label",
    # pr-flow-prompt retired in #13355 (PR flow is a §3 invariant, never a
    # choice) — the command no longer exists, so a manual mention of it now
    # fails this suite's exists-check instead of passing an allowlist.
    # #11613 §4.1 Phase 0 gather-all dependency provisioning.
    "gather-deps", "provision-deps",
    # #12419 §10 existing-install migration walk.
    "migration-plan", "stamp-version",
    # #12420 §10.3 post-commit harness restart.
    "restart-agents",
    # #12450 test-strategy detection + undetectable ask-human.
    "scan-summary", "set-test-strategy",
    # #13337 §9 Step 0 consent deny-list merge-writer.
    "merge-deny-list",
}
_MANIFEST_COMMANDS = {"validate", "list", "load", "resolve"}
_COMPOSE_COMMANDS = {"all", "deploy", "deploy-all", "boot", "boot-all"}
_MODEL_ROUTER_COMMANDS = {"list-providers", "setup-provider", "validate"}
_FORGEJO_COMMANDS = {"check-docker", "deploy", "create-token"}
_SHARED_FS_COMMANDS = {"init", "write-secret"}


@pytest.fixture(scope="module")
def manual():
    assert MANUAL.exists(), f"Missing installer manual: {MANUAL}"
    return MANUAL.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Structure — the manual's behavioral spine
# ---------------------------------------------------------------------------


def _assert_in_order(text, markers, what):
    last_idx = -1
    for marker in markers:
        idx = text.find(marker)
        assert idx != -1, f"Missing {what}: {marker!r}"
        assert idx > last_idx, (
            f"{what} {marker!r} appears out of order "
            f"(index {idx}, last was {last_idx})"
        )
        last_idx = idx


class TestManualStructure:
    def test_manual_non_empty(self, manual):
        assert manual  # non-empty

    def test_top_level_sections_present_in_order(self, manual):
        _assert_in_order(manual, [
            "## 1. You are an agent, not a wizard",
            "## 2. Your soul",
            "## 3. Know both worlds, then bridge them",
            "## 4. The flow",
            "## 5. The runtime model — convey it correctly",
            "## 6. What an installed SquidSquad looks like",
            "## 7. Customization is an everyday affordance",
            "## 8. Do / don't",
            "## 9. The helper playbook",
            "## 10. Cross-references",
        ], "section heading")

    def test_flow_steps_present_in_order(self, manual):
        """The §4 flow must carry steps 0-9, in order."""
        _assert_in_order(manual, [
            "**0. Consent & guardrails",
            "**1. Basics.**",
            "**2. Understand the project",
            "**3. Understand how they work.**",
            "**4. Reconcile what's already there.**",
            "**5. Introduce the team.**",
            "**6. Confirm each agent, one at a time.**",
            "**7. Apply.**",
            "**8. Verify",
            "**9. Commit & hand off.**",
        ], "flow step")

    def test_playbook_sections_present_in_order(self, manual):
        """§9 must map every flow stage to its helper mechanics."""
        _assert_in_order(manual, [
            "### The helper contract",
            "### Write discipline",
            "### Step 0 — Consent & deny list",
            "### Step 1 — Basics",
            "### Steps 2–3",
            "### Steps 3 & 5–6",
            "### Step 7 — Apply",
            "### Step 9 — Commit & hand off",
            "### When something breaks",
        ], "playbook section")

    def test_step0_playbook_binds_deny_list_helper(self, manual):
        """§9 Step 0 binds the consent conversation to the deterministic
        merge-writer (#13337): preview via --dry-run BEFORE any write,
        write on confirmation, deny rules only — never ask."""
        start = manual.find("### Step 0 — Consent & deny list")
        assert start != -1, "§9 must carry a Step 0 playbook entry"
        step0 = manual[start:manual.find("### Step 1 — Basics")]
        assert "merge-deny-list" in step0, (
            "Step 0 playbook must name the wizard.py merge-deny-list helper"
        )
        assert "--dry-run" in step0, (
            "Step 0 playbook must show the --dry-run preview (inform-"
            "before-write is deterministic, not narrated)"
        )
        assert step0.find("--dry-run") < step0.find("without `--dry-run`"), (
            "the preview must come before the write in the documented "
            "sequence"
        )
        assert "deny" in step0 and "`ask`" in step0, (
            "Step 0 playbook must state the deny-vs-ask rule (deny rules "
            "only, never ask)"
        )

    def test_consent_wording_is_verbatim_scripted(self, manual):
        """Consent moments are fixed scripts — the one place phrasing is
        not adaptive (operator carve-out on #13336: bucket-3 UX artifacts
        retired, consent stays VERBATIM). Locks the exact script."""
        assert "### Consent wording — verbatim" in manual
        # Step 0 must bind to the script explicitly, before the flow moves on.
        step0 = manual[manual.find("**0. Consent & guardrails"):manual.find("**1. Basics.**")]
        assert "verbatim from § Consent wording" in step0, (
            "Step 0 must direct the installer to present the consent text "
            "verbatim from § Consent wording"
        )
        # The exact consent script — any rewording is a consent-drift reject.
        for line in (
            "> Before we begin, one important thing about how your team works.",
            "> So the agents can get on with the work without stopping to ask "
            "you about every little step, they run with broad access to this "
            "project. I want to be upfront about that.",
            '> You stay in control of the limits. I\'ll always honor a "please '
            "don't touch this\" list — for **every** agent, permanently. If "
            "there's anything you'd rather they never read or change — "
            "passwords, API keys, `.env` files, private notes, a whole folder "
            "— tell me now and I'll lock it off.",
            "> How would you like to go ahead?",
            "> - **Yes** — I'm good with this. *(List any files or folders to "
            'keep off-limits, or say "nothing for now.")*',
            "> - **No** — I'd rather not. *(That's completely fine — we'll "
            "stop here, nothing is changed.)*",
        ):
            assert line in manual, (
                f"Verbatim consent script line missing or reworded: {line!r}"
            )

    def test_event_driven_model_is_the_default(self, manual):
        """§5: event-driven is the reality; the loop is only a fallback."""
        assert "The loop is a fallback" in manual
        assert re.search(r"woken by events", manual)

    def test_roster_invariant_names_all_four_role_types(self, manual):
        assert "PM, Worker, Verifier, DM — none missing" in manual

    def test_pr_flow_is_invariant_not_a_choice(self, manual):
        """PR flow is a §3 invariant (change lands through review); the manual
        must never offer a PR-flow on/off choice — only the merge gate is a
        variable. `pr-flow-prompt` was drifted wizard.py surface (#9478 D2),
        retired in #13355 — the manual must not carry it."""
        assert "pr-flow-prompt" not in manual, (
            "Manual offers the retired 'PR flow on/off' choice — PR flow is "
            "an invariant; only the merge gate (Auto Merge) is a variable"
        )
        assert "Change lands through review" in manual

    def test_silent_config_defaults_match_code(self, manual):
        """The silent defaults must match wizard.py's (30m interval / 70
        context threshold) — a doc-vs-code contradiction here misleads the
        installer into writing wrong config."""
        assert "context-pressure threshold (default 70)" in manual, (
            "Context-threshold silent default must read 70 (wizard.py "
            "context_threshold) — not 80 or any other value"
        )
        assert "default 30 minutes" in manual


# ---------------------------------------------------------------------------
# Helper-command cross-references
# ---------------------------------------------------------------------------


def _mentions(manual, script):
    return re.findall(rf"{script}\s+([a-z][a-z0-9-]*)", manual)


class TestHelperCommandReferences:
    def test_every_wizard_command_mentioned_exists(self, manual):
        """Every `wizard.py <cmd>` mention must be a real subcommand."""
        mentions = _mentions(manual, r"wizard\.py")
        assert mentions, "Expected at least one wizard.py command reference"
        unknown = set(mentions) - _WIZARD_COMMANDS
        assert not unknown, f"Manual references unknown wizard commands: {unknown}"

    def test_every_manifest_command_mentioned_exists(self, manual):
        unknown = set(_mentions(manual, r"manifest\.py")) - _MANIFEST_COMMANDS
        assert not unknown, f"Manual references unknown manifest commands: {unknown}"

    def test_every_compose_command_mentioned_exists(self, manual):
        unknown = set(_mentions(manual, r"compose\.py")) - _COMPOSE_COMMANDS
        assert not unknown, f"Manual references unknown compose commands: {unknown}"

    def test_every_model_router_command_mentioned_exists(self, manual):
        unknown = set(_mentions(manual, r"model_router\.py")) - _MODEL_ROUTER_COMMANDS
        assert not unknown, f"Manual references unknown model_router commands: {unknown}"

    def test_every_forgejo_command_mentioned_exists(self, manual):
        unknown = set(_mentions(manual, r"forgejo_setup\.py")) - _FORGEJO_COMMANDS
        assert not unknown, f"Manual references unknown forgejo_setup commands: {unknown}"

    def test_every_shared_fs_command_mentioned_exists(self, manual):
        unknown = set(_mentions(manual, r"shared_fs\.py")) - _SHARED_FS_COMMANDS
        assert not unknown, f"Manual references unknown shared_fs commands: {unknown}"

    def test_critical_helpers_are_mentioned(self, manual):
        """Key commands that MUST be part of the playbook."""
        for cmd in (
            "wizard.py gather-deps",
            "wizard.py provision-deps",
            "wizard.py check-existing",
            "wizard.py repo-info",
            "wizard.py migration-plan",
            "wizard.py stamp-version",
            "wizard.py validate-name",
            "wizard.py scan-summary",
            "wizard.py set-test-strategy",
            "wizard.py build-config-md",
            "wizard.py scaffold",
            "wizard.py ensure-labels",
            "wizard.py restart-agents",
            "manifest.py list",
            "manifest.py load",
            "shared_fs.py init",
        ):
            assert cmd in manual, f"Manual missing critical helper call: {cmd}"


# ---------------------------------------------------------------------------
# Registry cross-references
# ---------------------------------------------------------------------------


class TestRegistryCrossReferences:
    def test_referenced_preset_ids_exist(self, manual):
        presets = {
            d.name for d in (REPO_ROOT / "references" / "presets").iterdir()
            if d.is_dir() and (d / "manifest.yaml").exists()
        }
        mentioned = {"software-dev", "design"}
        assert mentioned.issubset(presets), (
            f"Manual references presets not in registry: {mentioned - presets}"
        )
        # Manual must mention every shipped preset at least once
        for p in presets:
            assert p in manual, f"Manual never mentions shipped preset: {p}"

    def test_referenced_roles_exist(self, manual):
        roles = {
            d.name for d in (REPO_ROOT / "references" / "roles").iterdir()
            if d.is_dir() and (d / "manifest.yaml").exists()
        }
        # #6274.2: canonical role names are worker/verifier (not dev/qa).
        for role in ("pm", "dm", "worker", "verifier"):
            assert role in roles, f"Shipped role missing: {role}"

        body_lower = manual.lower()
        for role in ("pm", "dm", "worker", "verifier"):
            assert role in body_lower, (
                f"Manual never mentions shipped role: {role}"
            )

    def test_no_stale_pre_6274_role_tokens(self, manual):
        """The pre-rename display tokens (`Dev`/`QA`) must not appear as
        roster/pipeline vocabulary in the manual."""
        for token in ("→ QA →", "[Dev] → QA", "PM, QA, DM"):
            assert token not in manual, (
                f"Stale pre-6274.2 display token in manual: {token!r}"
            )


# ---------------------------------------------------------------------------
# Installer-agent lifecycle invariants
# ---------------------------------------------------------------------------


class TestInstallerAgentInvariants:
    def test_no_writes_before_apply_is_documented(self, manual):
        """The manual must explicitly prohibit project writes before step 7."""
        assert re.search(
            r"Nothing is written to the target project before step 7",
            manual,
        ), "Manual missing the no-writes-before-Apply write-discipline rule"

    def test_full_rebuild_requires_typed_confirmation(self, manual):
        assert "delete and rebuild" in manual, (
            "Full rebuild must require the typed `delete and rebuild` confirmation"
        )

    def test_one_consent_question_for_provisioning(self, manual):
        assert re.search(r"\*\*one\*\* permission question", manual), (
            "Dependency provisioning must ask exactly ONE permission question"
        )

    def test_ephemeral_exit_documented(self, manual):
        """The installer must hand off and exit — never persist or cycle."""
        assert "hand off and exit" in manual
        assert re.search(r"ephemeral", manual, re.IGNORECASE)
        assert re.search(r"end the session", manual, re.IGNORECASE)

    def test_no_self_loop_or_squad_work(self, manual):
        assert "Persist, cycle, or pick up squad work" in manual, (
            "The Don't list must forbid persisting/cycling/picking up squad work"
        )

    def test_force_flag_not_documented_for_installer(self, manual):
        """--force is a human override — the installer must never use it.

        The helper contract's own prohibition sentence ("--force flags are
        human escape hatches, never yours") is the one sanctioned mention;
        any other occurrence means an instruction actually uses the flag.
        """
        offending = [
            line for line in manual.splitlines()
            if "--force" in line and "human escape hatch" not in line
        ]
        assert not offending, (
            "Manual uses --force in the installer flow — that flag is "
            f"for human overrides only, not for the installer: {offending}"
        )

    def test_preview_never_touches_real_install(self, manual):
        assert re.search(
            r"[Nn]ever write the real `\.squidsquad/` during a preview",
            manual,
        ), "Preview mechanics must forbid writing the real .squidsquad/"

    def test_never_auto_spawn_the_team(self, manual):
        assert re.search(r"\*\*Never start the team yourself\*\*", manual), (
            "Hand-off mechanics must forbid the installer booting the squad"
        )
