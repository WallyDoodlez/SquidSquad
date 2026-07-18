"""Regression test for #13666 — task-intake.md's Phase 2 wrote CONTEXT.md to
disk but never explicitly committed+pushed it, relying on the mechanical
post-cycle commit/push that runs at cycle END. In event mode, a task filed,
planned, and approved within one PM cycle fires the `Approved` transition's
nudge BEFORE that end-of-cycle commit lands — the worker wakes on the very
next cycle and can't find the CONTEXT file the issue body's AUTHORITATIVE
SCOPE banner points at. Live-reproduced this session: #13563 was filed/
planned/approved in one PM sitting, skill picked it up on the next event and
immediately bailed because CONTEXT-13563.md didn't exist on origin/main yet.

Two-part fix:
1. task-intake.md Phase 2 now commits+pushes CONTEXT.md immediately after
   writing it (mirrors Phase 3B, which already commits the plan body
   explicitly rather than trusting the wrapper).
2. task-approval.md's pre-approval body-vs-CONTEXT sync check (step 6) now
   also confirms the CONTEXT artifact is present in `git log origin/main`
   before allowing the `planned -> approved` transition -- a hard gate, not
   just a should-do instruction, so the race class is caught even if a
   future PM session skips the Phase 2 commit step.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TASK_INTAKE = REPO_ROOT / "references" / "sub-skills" / "roles" / "pm" / "task-intake.md"
TASK_APPROVAL = REPO_ROOT / "references" / "sub-skills" / "roles" / "pm" / "task-approval.md"


@pytest.fixture
def task_intake_text():
    assert TASK_INTAKE.exists(), f"task-intake.md missing: {TASK_INTAKE}"
    return TASK_INTAKE.read_text(encoding="utf-8")


@pytest.fixture
def task_approval_text():
    assert TASK_APPROVAL.exists(), f"task-approval.md missing: {TASK_APPROVAL}"
    return TASK_APPROVAL.read_text(encoding="utf-8")


class TestTaskIntakeCommitsContextImmediately13666:
    def test_explicit_commit_step_present(self, task_intake_text):
        idx = task_intake_text.index("#13666")
        section = task_intake_text[idx:idx + 800]
        assert "git add" in section
        assert "git commit" in section
        assert "git push" in section

    def test_commit_step_placed_right_after_context_written(self, task_intake_text):
        """The commit step must come between CONTEXT.md's template block and
        the 'Open in editor' step -- immediately after the write, not later."""
        context_template_idx = task_intake_text.index("## Out of Scope")
        commit_idx = task_intake_text.index("#13666")
        open_editor_idx = task_intake_text.index(
            '**Open in editor**: After CONTEXT.md is created'
        )
        assert context_template_idx < commit_idx < open_editor_idx

    def test_explains_the_race(self, task_intake_text):
        idx = task_intake_text.index("#13666")
        section = task_intake_text[idx:idx + 600]
        assert "race" in section.lower()
        assert "nudge" in section.lower()


class TestTaskApprovalGatesOnOriginMain13666:
    def test_origin_main_check_present(self, task_approval_text):
        idx = task_approval_text.index("#13666")
        section = task_approval_text[idx:idx + 900]
        assert "git log origin/main" in section

    def test_check_is_inside_pre_approval_sync_step(self, task_approval_text):
        """The origin/main confirmation must be a sub-step of step 6 (the
        pre-approval body-vs-CONTEXT sync), not a disconnected addition."""
        step6_idx = task_approval_text.index("Pre-approval body-vs-CONTEXT sync check")
        gate_idx = task_approval_text.index("#13666")
        step7_idx = task_approval_text.index(
            "Only after human explicitly approves execution"
        )
        assert step6_idx < gate_idx < step7_idx

    def test_step7_references_the_new_check(self, task_approval_text):
        idx = task_approval_text.index("Only after human explicitly approves execution")
        line = task_approval_text[idx:idx + 300]
        assert "origin/main" in line.lower() or "artifact confirmation" in line.lower()

    def test_never_approve_with_artifact_unpushed(self, task_approval_text):
        idx = task_approval_text.index("#13666")
        section = task_approval_text[idx:idx + 900]
        assert "never transition" in section.lower() or "before proceeding" in section.lower()
