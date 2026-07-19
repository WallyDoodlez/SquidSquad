"""Regression test for #13565 — composed-prompt re-diet + sub-skill
re-read discipline.

Three phases:
- Phase A: trimmed the shared cycle contract (`references/roles/
  instructions.md`, boot-read by every role) and extracted the rare
  `deploy-signal` Case-E handling out of `event-mode-contract.md` (~9KB
  of an ~25KB file, previously boot-read by every role every session
  regardless of whether it would ever fire) into a new reactively-read
  fragment. Also removed a dead `### append` H3 heading (a leftover
  L4-op-merge artifact) from 6 role source files.
- Phase B: split PM's `task-intake.md` (5-phase task lifecycle) into a
  lean hot-path core + a cold-path `task-intake-phases.md` reference,
  and extracted verifier's TEST-PLAN.md/subagent-prompt templates out of
  `verification.md` into `verification-templates.md`.
- Phase C: added a re-read-discipline rule to the shared cycle contract
  — skip re-Reading a sub-skill only when its text is already VISIBLE in
  current context, never from memory; explicit re-read required after a
  context-compaction summary or a session restart.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ROLES = REPO_ROOT / "references" / "roles"
SUBSKILLS = REPO_ROOT / "references" / "sub-skills"


def _read(path):
    assert path.exists(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase A: dead-heading removal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    ROLES / "dm" / "SOUL.md",
    ROLES / "pm" / "SOUL.md",
    ROLES / "verifier" / "SOUL.md",
    ROLES / "worker" / "SOUL.md",
    ROLES / "verifier" / "instructions.md",
    ROLES / "worker" / "instructions.md",
])
def test_dead_append_heading_removed(path):
    text = _read(path)
    for line in text.splitlines():
        assert line.strip() != "### append", (
            f"{path} still has the dead L4-op-merge-artifact heading")


def test_dead_heading_removal_did_not_drop_surrounding_content():
    """The disclaimer line that used to follow the dead heading in every
    SOUL.md must still be present -- this was a heading-only removal."""
    for path in [ROLES / "dm" / "SOUL.md", ROLES / "pm" / "SOUL.md",
                 ROLES / "verifier" / "SOUL.md", ROLES / "worker" / "SOUL.md"]:
        text = _read(path)
        assert "Human instructions always override these defaults" in text


# ---------------------------------------------------------------------------
# Phase A: deploy-signal extraction
# ---------------------------------------------------------------------------

class TestDeploySignalExtraction13565:
    def test_new_fragment_exists_and_has_content(self):
        path = SUBSKILLS / "common-events" / "deploy-signal-handling.md"
        text = _read(path)
        assert len(text) > 5000
        assert "deploy-signal" in text

    def test_new_fragment_preserves_critical_invariants(self):
        text = _read(SUBSKILLS / "common-events" / "deploy-signal-handling.md")
        assert "Do NOT self-assess drift" in text
        assert "Do NOT `ack-cursor` past it" in text
        assert "NEVER honored where you reach it mid-drain" in text

    def test_event_mode_contract_no_longer_inlines_full_handling(self):
        text = _read(SUBSKILLS / "common-events" / "event-mode-contract.md")
        # The detailed deferral procedure moved out -- must not still be here.
        assert "Stop the boot drain here." not in text
        assert "Hold it" not in text

    def test_event_mode_contract_still_has_pointer_and_invariants(self):
        text = _read(SUBSKILLS / "common-events" / "event-mode-contract.md")
        assert "run sub-skill: `deploy-signal-handling`" in text
        assert "never `ack-cursor` a deploy-signal yourself" in text
        assert "never honor one mid-boot-drain" in text

    def test_catalog_and_installer_manifest_registered(self):
        catalog = _read(REPO_ROOT / "docs" / "sub-skill-catalog.md")
        assert "deploy-signal-handling" in catalog
        manifest = _read(REPO_ROOT / "references" / "installer-files.txt")
        assert "references/sub-skills/common-events/deploy-signal-handling.md" in manifest


# ---------------------------------------------------------------------------
# Phase C: re-read discipline
# ---------------------------------------------------------------------------

class TestReReadDiscipline13565:
    @pytest.fixture
    def text(self):
        return _read(ROLES / "instructions.md")

    def test_rule_present(self, text):
        assert "Re-read discipline" in text

    def test_tied_to_visibility_not_memory(self, text):
        assert "already visible in your current conversation context" in text
        assert "never because you remember reading it" in text

    def test_requires_reread_after_compaction(self, text):
        assert "After a context-compaction summary" in text
        assert "no longer visible, so re-read it" in text

    def test_requires_reread_after_restart(self, text):
        assert "After a session restart" in text
        assert "nothing from before is visible" in text

    def test_allows_skip_only_within_same_session_no_compaction(self, text):
        assert "Within the same session, with no compaction since" in text
        assert "is a skip" in text


# ---------------------------------------------------------------------------
# Phase B: task-intake hot/cold split
# ---------------------------------------------------------------------------

class TestTaskIntakeSplit13565:
    HOT = SUBSKILLS / "roles" / "pm" / "task-intake.md"
    COLD = SUBSKILLS / "roles" / "pm" / "task-intake-phases.md"

    def test_hot_core_under_8kb_target(self):
        assert self.HOT.stat().st_size <= 8 * 1024

    def test_hot_core_has_dispatch_table_pointing_at_cold(self):
        text = _read(self.HOT)
        assert "Phase Dispatch" in text
        assert "run sub-skill: `roles/pm/task-intake-phases`" in text

    def test_hot_core_retains_artifact_resume_logic_verbatim(self):
        text = _read(self.HOT)
        assert "Artifact Resume Logic" in text
        assert "File exists but uncommitted" in text

    @pytest.mark.parametrize("phase_marker", [
        "Phase 1 — Research",
        "Phase 2A — Discussion Prep",
        "Phase 2 — Discussion",
        "Phase 2B — Re-Research Gate",
        "Phase 3 — AC Drafting",
        "Phase 3B — Plan-in-PR",
        "Phase 4 — Execution",
        "Phase 5 — Verification",
    ])
    def test_every_phase_reachable_in_cold_path(self, phase_marker):
        """Every phase named in the hot dispatch table must have a full
        section in the cold-path file -- nothing dropped in the split."""
        text = _read(self.COLD)
        assert phase_marker in text

    def test_cold_path_retains_research_md_template(self):
        text = _read(self.COLD)
        assert "# FEAT-[ROLE_UPPER]-XXX Research" in text
        assert "## Vault Context" in text

    def test_cold_path_retains_context_md_template(self):
        text = _read(self.COLD)
        assert "# FEAT-[ROLE_UPPER]-XXX Context" in text
        assert "## Locked Decisions (human decided)" in text

    def test_cold_path_retains_plan_in_pr_git_sequence(self):
        text = _read(self.COLD)
        assert "git_ops.py task-begin" in text
        assert "plan(#[NUMBER])" in text

    def test_catalog_and_installer_manifest_registered(self):
        catalog = _read(REPO_ROOT / "docs" / "sub-skill-catalog.md")
        assert "task-intake-phases" in catalog
        manifest = _read(REPO_ROOT / "references" / "installer-files.txt")
        assert "references/sub-skills/roles/pm/task-intake-phases.md" in manifest


# ---------------------------------------------------------------------------
# Phase B: verification.md cuts
# ---------------------------------------------------------------------------

class TestVerificationCuts13565:
    HOT = SUBSKILLS / "roles" / "verifier" / "verification.md"
    TEMPLATES = SUBSKILLS / "roles" / "verifier" / "verification-templates.md"

    def test_health_check_now_calls_script_not_prose_algorithm(self):
        text = _read(self.HOT)
        assert "python references/scripts/health_check.py" in text
        # The old hand-rolled algorithm description must be gone.
        assert "Read `.squidsquad/.local-config` to get each agent's clone path" not in text

    def test_health_check_still_logs_and_escalates(self):
        text = _read(self.HOT)
        assert "qa/qa-log.md" in text
        assert "Discussion note" in text

    def test_templates_extracted_with_pointer_left_behind(self):
        text = _read(self.HOT)
        assert "run sub-skill: `roles/verifier/verification-templates`" in text
        assert "# TEST-PLAN-<NUMBER>" not in text  # template body itself moved out

    def test_templates_file_has_full_content(self):
        text = _read(self.TEMPLATES)
        assert "# TEST-PLAN-<NUMBER>" in text
        assert "## Comprehension Questions" in text
        assert "HUMAN-REQUIRED gate" in text

    def test_catalog_and_installer_manifest_registered(self):
        catalog = _read(REPO_ROOT / "docs" / "sub-skill-catalog.md")
        assert "verification-templates" in catalog
        manifest = _read(REPO_ROOT / "references" / "installer-files.txt")
        assert "references/sub-skills/roles/verifier/verification-templates.md" in manifest
