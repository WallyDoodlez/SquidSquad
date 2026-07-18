"""Tests for #13515 — status:blocked (owned-but-parked, distinct from in-progress).

status:blocked is a doc-first change. Phase-1 (SOUL.md, event-mode-contract.md,
SKILL.md, pipeline-sentinel.md) is content-verification only — no standalone
Python script backs the instruction prose. Phase-2 (tracker.py legal
transitions + authority) has its own dedicated coverage in
test_tracker_authority.py::TestBlockedStatus; this file covers the doc surfaces
(AC1, AC2, AC4) plus a cross-file consistency check that the status name
landed as "blocked" everywhere (not the earlier "parked" working name).
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SOUL_FILE = REPO_ROOT / "references" / "roles" / "SOUL.md"
EVENT_MODE_CONTRACT_FILE = (
    REPO_ROOT / "references" / "sub-skills" / "common-events" / "event-mode-contract.md"
)
SKILL_MD_FILE = REPO_ROOT / "SKILL.md"
SENTINEL_FILE = REPO_ROOT / "references" / "sub-skills" / "roles" / "pm" / "pipeline-sentinel.md"
TRACKER_FILE = REPO_ROOT / "references" / "scripts" / "tracker.py"


@pytest.fixture
def soul_text():
    assert SOUL_FILE.exists(), f"SOUL.md missing: {SOUL_FILE}"
    return SOUL_FILE.read_text(encoding="utf-8")


@pytest.fixture
def event_mode_contract_text():
    assert EVENT_MODE_CONTRACT_FILE.exists()
    return EVENT_MODE_CONTRACT_FILE.read_text(encoding="utf-8")


@pytest.fixture
def skill_md_text():
    assert SKILL_MD_FILE.exists()
    return SKILL_MD_FILE.read_text(encoding="utf-8")


@pytest.fixture
def sentinel_text():
    assert SENTINEL_FILE.exists()
    return SENTINEL_FILE.read_text(encoding="utf-8")


@pytest.fixture
def tracker_text():
    assert TRACKER_FILE.exists()
    return TRACKER_FILE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC2 — 4a: Soul block-and-continue guidance
# ---------------------------------------------------------------------------


class TestSoulBlockedGuidance:
    """#13515 4a: Never Stop While Work Is Pending must instruct parking to
    `status:blocked` for a still-owned task blocked on another party."""

    def test_blocked_status_named(self, soul_text):
        assert "status:blocked" in soul_text

    def test_lives_in_never_stop_section(self, soul_text):
        section_start = soul_text.index("### Never Stop While Work Is Pending")
        next_section = soul_text.index("###", section_start + 1)
        section = soul_text[section_start:next_section]
        assert "status:blocked" in section

    def test_distinguishes_from_in_progress_and_pending(self, soul_text):
        section_start = soul_text.index("### Never Stop While Work Is Pending")
        next_section = soul_text.index("###", section_start + 1)
        section = soul_text[section_start:next_section]
        assert "blocked on another party" in section
        assert "left at `in-progress`" in section
        assert "`pending-*`" in section

    def test_continue_to_next_item_still_required(self, soul_text):
        """Parking is block-AND-continue, not block-and-stop."""
        section_start = soul_text.index("### Never Stop While Work Is Pending")
        next_section = soul_text.index("###", section_start + 1)
        section = soul_text[section_start:next_section]
        blocked_sentence_idx = section.index("transition it to `status:blocked`")
        distinct_idx = section.index("relates to the human-handoff rule below")
        tail = section[blocked_sentence_idx:distinct_idx]
        assert "immediately continue" in tail

    def test_distinguishes_blocked_from_pending_human_star(self, soul_text):
        """DS-review Finding 1: `status:blocked`'s 'a human decision' trigger
        collided with the adjacent pending-human-* human-handoff rule. Fixed
        by an explicit discriminator: not-yet-asked -> pending-human-*;
        already-asked-and-waiting -> blocked."""
        section_start = soul_text.index("### Never Stop While Work Is Pending")
        next_section = soul_text.index("###", section_start + 1)
        section = soul_text[section_start:next_section]
        assert "relates to the human-handoff rule below" in section
        assert "no one has asked the human yet" in section
        assert "once the ask has been made and you are simply waiting" in section

    def test_documents_resume_path(self, soul_text):
        """DS-review Finding 3: the park instruction had no resume-path
        guidance (contrast the detailed pending-human-* return path a few
        sentences later). Fixed with an explicit resume sentence."""
        section_start = soul_text.index("### Never Stop While Work Is Pending")
        next_section = soul_text.index("###", section_start + 1)
        section = soul_text[section_start:next_section]
        assert "you resume the task from `blocked` back to `in-progress`" in section


# ---------------------------------------------------------------------------
# AC2 — 4b: event-mode-contract.md Case D mirror
# ---------------------------------------------------------------------------


class TestEventModeContractCaseD:
    """#13515 4b: Case D (mid-task) must mirror the parking rule."""

    def test_case_d_mentions_blocked(self, event_mode_contract_text):
        case_d_start = event_mode_contract_text.index("### Case D")
        case_e_start = event_mode_contract_text.index("### Case E")
        case_d = event_mode_contract_text[case_d_start:case_e_start]
        assert "status:blocked" in case_d

    def test_case_d_does_not_fall_through_to_completion_on_park(self, event_mode_contract_text):
        case_d_start = event_mode_contract_text.index("### Case D")
        case_e_start = event_mode_contract_text.index("### Case E")
        case_d = event_mode_contract_text[case_d_start:case_e_start]
        assert "task completion" in case_d and "status:blocked" in case_d
        park_idx = case_d.index("2a.")
        completion_idx = case_d.index("3.", park_idx)
        assert park_idx < completion_idx

    def test_step_2_carves_out_the_2a_exception(self, event_mode_contract_text):
        """DS-review Finding 1: step 2 ('Note but do NOT act... runs
        atomically to completion') contradicted step 2a's instruction to
        act (transition to blocked) without completing. Fixed by an
        explicit exception clause in step 2 pointing at 2a."""
        case_d_start = event_mode_contract_text.index("### Case D")
        case_e_start = event_mode_contract_text.index("### Case E")
        case_d = event_mode_contract_text[case_d_start:case_e_start]
        step2_idx = case_d.index("2. **Note but do NOT act")
        step2a_idx = case_d.index("2a.")
        step2 = case_d[step2_idx:step2a_idx]
        assert "unless you become blocked" in step2

    def test_2a_clears_working_state_before_work_queue(self, event_mode_contract_text):
        """DS-review Finding 2: 2a referenced only Case C's work_queue() step
        (step 3), silently skipping Case C step 2 (clear Task field + write
        the idle marker) — leaving working-state.md naming a task that's no
        longer the current activity (the #12854 defect). Fixed by an
        explicit reference to Case C step 2's handoff."""
        case_d_start = event_mode_contract_text.index("### Case D")
        case_e_start = event_mode_contract_text.index("### Case E")
        case_d = event_mode_contract_text[case_d_start:case_e_start]
        step2a_idx = case_d.index("2a.")
        step3_idx = case_d.index("3. On task completion", step2a_idx)
        step2a = case_d[step2a_idx:step3_idx]
        assert "clear the Task field and write the `idle` marker" in step2a
        assert "Case C step 2" in step2a

    def test_2a_not_gated_on_event_arrival(self, event_mode_contract_text):
        """DS-review Finding 3: 2a's blocking condition isn't caused by the
        NUDGE that triggers Case D, so placing it only under 'Mid-task,
        event arrives' risked reading as event-gated. Fixed with an explicit
        note that becoming blocked is event-independent."""
        case_d_start = event_mode_contract_text.index("### Case D")
        case_e_start = event_mode_contract_text.index("### Case E")
        case_d = event_mode_contract_text[case_d_start:case_e_start]
        assert "event-independent condition" in case_d
        assert "whether or not a `NUDGE` is present" in case_d


# ---------------------------------------------------------------------------
# AC1 — 4c: canonical taxonomy (SKILL.md + tracker.py docstring)
# ---------------------------------------------------------------------------


class TestCanonicalTaxonomyDocumentsBlocked:
    """#13515 4c: SKILL.md label taxonomy + tracker.py docstring."""

    def test_skill_md_label_taxonomy_lists_blocked(self, skill_md_text):
        taxonomy_start = skill_md_text.index("### Label Taxonomy")
        bug_flow_start = skill_md_text.index("### Bug Flow")
        taxonomy_section = skill_md_text[taxonomy_start:bug_flow_start]
        assert "status:blocked" in taxonomy_section

    def test_skill_md_documents_semantics(self, skill_md_text):
        note_idx = skill_md_text.index("`pending` = awaiting human approval")
        note_line = skill_md_text[note_idx:note_idx + 800]
        assert "`blocked`" in note_line
        assert "blocked on another party" in note_line

    def test_skill_md_legal_transitions_documented(self, skill_md_text):
        assert "in-progress" in skill_md_text and "blocked" in skill_md_text
        # The side-branch sentence documents both directions.
        idx = skill_md_text.index("side-branch")
        segment = skill_md_text[idx:idx + 500]
        assert "resumes to `in-progress`" in segment or "resume" in segment.lower()

    def test_tracker_docstring_documents_blocked(self, tracker_text):
        docstring_end = tracker_text.index('"""', tracker_text.index('"""') + 3)
        docstring = tracker_text[: docstring_end + 3]
        assert "status:blocked" in docstring
        assert "in-progress -> blocked" in docstring
        assert "blocked -> in-progress" in docstring
        assert "_assignee" in docstring


# ---------------------------------------------------------------------------
# AC4 — 4d: pipeline-sentinel consumes the new status
# ---------------------------------------------------------------------------


class TestPipelineSentinelBlockedConsumption:
    """#13515 4d: pipeline-sentinel must not stall-nudge blocked items, and
    must flag >=2 status:in-progress for one role as a double-pickup anomaly
    (the consumption side of the section-5 observability payoff)."""

    def test_blocked_excluded_from_halt_detection(self, sentinel_text):
        halt_start = sentinel_text.index("**2.1 Detect a halt")
        halt_end = sentinel_text.index("**2.2 Investigate")
        halt_section = sentinel_text[halt_start:halt_end]
        assert "status:blocked" in halt_section
        assert "excluded from halt detection" in halt_section

    def test_double_pickup_check_present(self, sentinel_text):
        assert "Double-pickup anomaly" in sentinel_text

    def test_double_pickup_check_is_new_stuck_state_item(self, sentinel_text):
        """4g sits among the other stuck-state detections (4a-4f), after 4f."""
        four_f_idx = sentinel_text.index("**4f. In-progress on dead agent**")
        double_pickup_idx = sentinel_text.index("**4g. Double-pickup anomaly**")
        assert four_f_idx < double_pickup_idx

    def test_double_pickup_threshold_is_two(self, sentinel_text):
        section_idx = sentinel_text.index("**4g. Double-pickup anomaly**")
        next_hr = sentinel_text.index("<!--", section_idx)
        section = sentinel_text[section_idx:next_hr]
        assert ">=2" in section

    def test_double_pickup_references_blocked_as_the_resolution(self, sentinel_text):
        """A role legitimately doing one active task never shows 2+ in-progress
        now that parking uses status:blocked — so 2+ is genuinely anomalous."""
        section_idx = sentinel_text.index("**4g. Double-pickup anomaly**")
        next_hr = sentinel_text.index("<!--", section_idx)
        section = sentinel_text[section_idx:next_hr]
        assert "status:blocked" in section


# ---------------------------------------------------------------------------
# Cross-file consistency — the name is "blocked" everywhere, not "parked"
# ---------------------------------------------------------------------------


class TestStatusNameConsistency:
    """#13515 §2/§6: operator confirmed the name is `blocked` (not `parked`).
    Every Phase-1 surface must use the same label string."""

    @pytest.mark.parametrize("fixture_name", [
        "soul_text", "event_mode_contract_text", "skill_md_text",
        "sentinel_text", "tracker_text",
    ])
    def test_uses_blocked_label(self, request, fixture_name):
        text = request.getfixturevalue(fixture_name)
        assert "status:blocked" in text
