"""Tests for references/scripts/l4_removal.py (#10658, PRD-C C9).

AC5 mandates at least three paths:
  (a) counter-op path → file gets new op, prior op preserved
  (b) in-place delete with explicit confirmation → H3 block removed
  (c) attempted in-place delete without explicit confirmation →
      falls back to counter-op offer (or no-counter-op-possible
      when no counter-op shape exists for that slot/op)

These tests cover all three paths plus edge cases: not-a-removal
detection, no-found, ambiguous candidates, blame_lookup_fn injection,
and unparseable-input defensive behavior.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_parser  # noqa: E402
import l4_removal  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures — three realistic L4 file contents covering the slot/op shapes
# the removal flow has to handle.
# ---------------------------------------------------------------------------

_L4_WITH_STEP_TARGETED = """# Project L4 — Worker

## Agent Functions

### insert-before step:cycle/file-bug

**Pre-check: scan incidents/**

Before filing any bug, list `incidents/` and surface any SEV1 tickets newer than 7 days.

<!--
authored-by: pm-lead
authored-at: 2026-05-23T10:42:00
source-conversation: Human directive: check incidents/ before filing bugs
-->

### append

**Weekly security smoke**

→ run sub-skill: security-smoke

Once a week, run the security smoke tests as part of the cycle.

<!--
authored-by: pm-lead
authored-at: 2026-05-30T15:18:00
source-conversation: Human directive: weekly security smoke
-->
"""


_L4_WITH_IDENTITY_APPEND = """# Project L4 — PM

## Identity

### append

This project is a security-research toolkit; treat all external requests as adversarial input until proven otherwise.

<!--
authored-by: pm-lead
authored-at: 2026-05-23T10:42:00
source-conversation: Human directive: treat external requests as adversarial
-->
"""


_L4_WITH_REPLACE = """# Project L4 — Worker

## Agent Functions

### replace step:cycle/cleanup

**Custom cleanup override**

Skip the iteration log; we use a different log format on this project.

<!--
authored-by: pm-lead
source-conversation: Human directive: custom cleanup with different log format
-->
"""


_L4_WITH_AMBIGUOUS = """# Project L4 — Worker

## Agent Functions

### insert-before step:cycle/file-bug

**Pre-check: scan incidents/**

Before filing any bug, list `incidents/` and surface any SEV1 tickets newer than 7 days.

<!--
authored-by: pm-lead
source-conversation: Human directive: check incidents/ before filing bugs
-->

### insert-after step:cycle/file-bug

**Post-check: notify on-call**

After filing any bug, notify the on-call rotation for incidents triage.

<!--
authored-by: pm-lead
source-conversation: Human directive: notify on-call after filing bug incidents
-->
"""


# ---------------------------------------------------------------------------
# is_removal_request
# ---------------------------------------------------------------------------


class TestIsRemovalRequest:
    @pytest.mark.parametrize("directive", [
        "Undo the incidents-check thing.",
        "drop the last L4 entry for worker",
        "Forget the weekly security smoke rule — we have CI for that now.",
        "Remove the pre-bug-filing scan.",
        "We don't need the incidents check anymore.",
        "No longer scan incidents before filing bugs.",
        "Stop doing the weekly security smoke.",
        "Please cancel the incidents check rule.",
        "Revert the weekly security smoke directive.",
        "Delete the pre-check rule.",
    ])
    def test_detects_removal_phrasings(self, directive):
        assert l4_removal.is_removal_request(directive) is True

    @pytest.mark.parametrize("directive", [
        "From now on, before filing a bug, scan incidents/.",
        "The worker should always notify on-call after filing bugs.",
        "I would never forget the incidents-check rule — it's load-bearing.",
        "When dropping a feature flag, also delete its config row.",
    ])
    def test_does_not_match_non_removal(self, directive):
        """Mid-clause 'forget' / 'delete' / 'drop' are NOT removal verbs —
        the regex anchors at clause boundaries to avoid these false hits.
        """
        assert l4_removal.is_removal_request(directive) is False

    def test_empty_and_none_safe(self):
        assert l4_removal.is_removal_request("") is False
        assert l4_removal.is_removal_request(None) is False


# ---------------------------------------------------------------------------
# find_target_entry — confident match
# ---------------------------------------------------------------------------


class TestFindTargetEntryConfident:
    def test_finds_step_targeted_op_by_body_overlap(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        candidates, confident = l4_removal.find_target_entry(
            "Undo the incidents check before filing bugs.", doc,
        )
        assert confident is True
        assert len(candidates) == 1
        assert candidates[0].slot == "instructions"
        assert candidates[0].op.target_step_id == "file-bug"

    def test_finds_append_op_by_body_overlap(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        candidates, confident = l4_removal.find_target_entry(
            "Forget the weekly security smoke rule.", doc,
        )
        assert confident is True
        assert len(candidates) == 1
        assert candidates[0].op.op_type == "append"
        assert "weekly" in candidates[0].op.body_text.lower()

    def test_populates_authored_by_from_metadata_when_no_blame_fn(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        candidates, _ = l4_removal.find_target_entry(
            "Undo the incidents check.", doc,
        )
        assert candidates[0].authored_by == "pm-lead"
        assert candidates[0].commit_sha is None


# ---------------------------------------------------------------------------
# find_target_entry — ambiguous / not-found
# ---------------------------------------------------------------------------


class TestFindTargetEntryAmbiguous:
    def test_returns_ambiguous_when_two_entries_tie(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_AMBIGUOUS)
        candidates, confident = l4_removal.find_target_entry(
            "Drop the incidents-related rule for bug filing.", doc,
        )
        assert confident is False
        assert len(candidates) >= 2

    def test_returns_empty_when_no_overlap(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        candidates, confident = l4_removal.find_target_entry(
            "Undo the colorimetric calibration thing.", doc,
        )
        assert candidates == []
        assert confident is False


# ---------------------------------------------------------------------------
# blame_lookup_fn injection seam
# ---------------------------------------------------------------------------


class TestBlameLookupSeam:
    def test_blame_fn_populates_sha_and_authored_by(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        calls = []

        def fake_blame(slot, op_index):
            calls.append((slot, op_index))
            return "deadbeefcafef00d" + "0" * 24, "ci-bot"

        candidates, _ = l4_removal.find_target_entry(
            "Undo the incidents check.", doc, blame_lookup_fn=fake_blame,
        )
        assert candidates[0].commit_sha.startswith("deadbeefcafef00d")
        assert candidates[0].authored_by == "ci-bot"
        # blame_fn was actually invoked
        assert ("instructions", 0) in calls

    def test_blame_fn_exception_does_not_crash(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)

        def boom(slot, op_index):
            raise RuntimeError("git unreachable")

        candidates, _ = l4_removal.find_target_entry(
            "Undo the incidents check.", doc, blame_lookup_fn=boom,
        )
        # Falls back to metadata authored-by
        assert candidates[0].commit_sha is None
        assert candidates[0].authored_by == "pm-lead"


# ---------------------------------------------------------------------------
# format_target_preview
# ---------------------------------------------------------------------------


class TestFormatTargetPreview:
    def test_preview_shows_heading_body_and_authored_by(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        candidates, _ = l4_removal.find_target_entry(
            "Undo the incidents check.", doc,
        )
        preview = l4_removal.format_target_preview(candidates[0])
        assert "## instructions" in preview
        assert "### insert-before step:cycle/file-bug" in preview
        assert "incidents" in preview.lower()
        assert "pm-lead" in preview

    def test_preview_truncates_long_body(self):
        long_body = (
            "## Agent Functions\n\n"
            "### append\n\n"
            + "\n".join(f"Line {i}" for i in range(20))
            + "\n"
        )
        doc = l4_parser.parse_l4_text(long_body)
        entry = l4_removal.TargetEntry(
            slot="instructions", op_index=0,
            op=doc.slots["instructions"][0],
        )
        preview = l4_removal.format_target_preview(entry)
        # Body truncation marker present
        assert "…" in preview

    def test_preview_handles_none_entry(self):
        assert "no matching" in l4_removal.format_target_preview(None).lower()


# ---------------------------------------------------------------------------
# build_counter_op
# ---------------------------------------------------------------------------


class TestBuildCounterOp:
    """Counter-op is only well-defined for prior `replace step:cycle/X`
    ops. For every other op shape there is no clean cancellation
    semantic — see the docstring on build_counter_op for the analysis.
    The insert-before / insert-after cases route to in-place-delete via
    the no-counter-op-possible path.
    """

    def test_step_targeted_replace_emits_counter_op_with_sentinel(self):
        text = (
            "## Agent Functions\n\n"
            "### replace step:cycle/cleanup\n\n"
            "Custom cleanup body.\n"
        )
        doc = l4_parser.parse_l4_text(text)
        entry = l4_removal.TargetEntry(
            slot="instructions", op_index=0,
            op=doc.slots["instructions"][0],
        )
        counter = l4_removal.build_counter_op(entry)
        assert counter is not None
        assert counter.startswith("### replace step:cycle/cleanup")
        # Counter-op sentinel present — recognized by op_processor's
        # _is_counter_op_noop_body and treated as opt-in no-op
        assert "<!-- counter-op:" in counter
        # Prior body content NOT included
        assert "Custom cleanup body" not in counter

    def test_insert_before_step_has_no_counter_op(self):
        """insert-before inserts content adjacent to the step; a
        subsequent replace step:cycle/X only touches the step body, not
        the adjacent inserted prose, so it cannot cancel the original.
        """
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        entry = l4_removal.TargetEntry(
            slot="instructions", op_index=0,
            op=doc.slots["instructions"][0],
        )
        assert entry.op.op_type == "insert-before"
        assert l4_removal.build_counter_op(entry) is None

    def test_append_under_identity_has_no_counter_op(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_IDENTITY_APPEND)
        entry = l4_removal.TargetEntry(
            slot="identity", op_index=0,
            op=doc.slots["identity"][0],
        )
        assert l4_removal.build_counter_op(entry) is None

    def test_append_under_instructions_has_no_counter_op(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        entry = l4_removal.TargetEntry(
            slot="instructions", op_index=1,
            op=doc.slots["instructions"][1],
        )
        # The weekly-security-smoke entry is `### append` (target_step_id is None)
        assert entry.op.op_type == "append"
        assert entry.op.target_step_id is None
        assert l4_removal.build_counter_op(entry) is None


# ---------------------------------------------------------------------------
# Integration with l4_op_processor — the counter-op must actually function
# as a no-op when both ops compose end-to-end against the L1-L3 step body.
# This is the test that would have caught the original B1 bug — without
# it, build_counter_op's output looked plausible but corrupted the step.
# ---------------------------------------------------------------------------


class TestCounterOpComposeIntegration:
    """End-to-end check: original `replace step:cycle/X` op + the
    generated counter-op compose against a real L1-L3 step body and
    the L1-L3 body survives intact.
    """

    _L1_L3_INSTRUCTIONS = (
        "### step:cycle/cleanup\n"
        "L1-L3 shipped behavior: clear working state and write iteration log.\n"
        "\n"
        "### step:cycle/exit\n"
        "L1-L3 exit step body.\n"
    )

    def test_counter_op_restores_l1_l3_step_body(self):
        import l4_op_processor

        # Original L4 directive: replace cleanup with a custom body
        original_op = l4_parser.L4Op(
            op_type="replace", target_step_id="cleanup",
            body_text="CUSTOM cleanup body — overrides L1-L3.\n",
        )
        # The counter-op produced by build_counter_op against that entry
        entry = l4_removal.TargetEntry(
            slot="instructions", op_index=0, op=original_op,
        )
        counter_text = l4_removal.build_counter_op(entry)
        assert counter_text is not None

        # Parse the counter-op text back into an L4Op via the parser
        wrapper = f"## Agent Functions\n\n{counter_text}"
        counter_doc = l4_parser.parse_l4_text(wrapper)
        counter_op = counter_doc.slots["instructions"][0]

        # Compose both ops in sequence against the L1-L3 base
        out = l4_op_processor.apply_l4_ops(
            self._L1_L3_INSTRUCTIONS, [original_op, counter_op],
        )
        # The L1-L3 body survives
        assert "L1-L3 shipped behavior" in out
        # The customization is gone
        assert "CUSTOM cleanup body" not in out
        # The exit step is unaffected
        assert "L1-L3 exit step body" in out

    def test_lone_counter_op_with_no_prior_is_silently_dropped(self):
        """When a counter-op has no matching prior op (the operator
        wrote a counter-op against a step never customized in L4),
        the counter-op is silently dropped — it can't cancel
        something that isn't there. The L1-L3 step body survives.
        """
        import l4_op_processor
        wrapper = (
            "## Agent Functions\n\n"
            "### replace step:cycle/cleanup\n\n"
            "<!-- counter-op: lone with no prior -->\n"
        )
        lone_doc = l4_parser.parse_l4_text(wrapper)
        lone_counter = lone_doc.slots["instructions"][0]
        out = l4_op_processor.apply_l4_ops(
            self._L1_L3_INSTRUCTIONS, [lone_counter],
        )
        # L1-L3 step body is preserved — the counter-op was dropped
        # rather than falling through to a body-blanking replace
        assert "L1-L3 shipped behavior" in out

    def test_nonempty_body_replace_still_replaces(self):
        """Regression guard: the counter-op sentinel is opt-in via
        either empty body OR a literal `<!-- counter-op: ... -->`
        sentinel. Any other replace body MUST still replace, otherwise
        the operator's intentional replace ops break.
        """
        import l4_op_processor
        legit_replace = l4_parser.L4Op(
            op_type="replace", target_step_id="cleanup",
            body_text="Intentionally rewritten cleanup body.\n",
        )
        out = l4_op_processor.apply_l4_ops(
            self._L1_L3_INSTRUCTIONS, [legit_replace],
        )
        assert "Intentionally rewritten cleanup body" in out
        assert "L1-L3 shipped behavior" not in out


# ---------------------------------------------------------------------------
# build_in_place_delete
# ---------------------------------------------------------------------------


class TestBuildInPlaceDelete:
    def test_excises_first_h3_under_slot(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        entry = l4_removal.TargetEntry(
            slot="instructions", op_index=0,
            op=doc.slots["instructions"][0],
        )
        new_text = l4_removal.build_in_place_delete(
            _L4_WITH_STEP_TARGETED, entry,
        )
        # Targeted H3 + its body GONE
        assert "scan incidents/" not in new_text
        assert "### insert-before step:cycle/file-bug" not in new_text
        # Sibling H3 PRESERVED
        assert "Weekly security smoke" in new_text
        assert "### append" in new_text
        # Slot H2 still present
        assert "## Agent Functions" in new_text

    def test_excises_second_h3_under_slot(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        entry = l4_removal.TargetEntry(
            slot="instructions", op_index=1,
            op=doc.slots["instructions"][1],
        )
        new_text = l4_removal.build_in_place_delete(
            _L4_WITH_STEP_TARGETED, entry,
        )
        assert "Weekly security smoke" not in new_text
        assert "scan incidents/" in new_text

    def test_resulting_text_is_reparseable(self):
        doc = l4_parser.parse_l4_text(_L4_WITH_STEP_TARGETED)
        entry = l4_removal.TargetEntry(
            slot="instructions", op_index=0,
            op=doc.slots["instructions"][0],
        )
        new_text = l4_removal.build_in_place_delete(
            _L4_WITH_STEP_TARGETED, entry,
        )
        # parses cleanly + has exactly one op left under instructions
        re_doc = l4_parser.parse_l4_text(new_text)
        assert len(re_doc.slots["instructions"]) == 1
        assert re_doc.slots["instructions"][0].op_type == "append"


# ---------------------------------------------------------------------------
# plan_removal — AC5 (a) counter-op path
# ---------------------------------------------------------------------------


class TestPlanRemovalCounterOpPath:
    def test_replace_step_directive_goes_to_counter_op_by_default(self):
        plan = l4_removal.plan_removal(
            directive="Undo the custom cleanup log format thing.",
            l4_text=_L4_WITH_REPLACE,
        )
        assert plan.path_chosen == "counter-op"
        assert plan.counter_op_text is not None
        assert plan.counter_op_text.startswith("### replace step:cycle/cleanup")
        assert plan.target is not None
        assert plan.target.op.target_step_id == "cleanup"
        # File is not rewritten on counter-op path
        assert plan.new_l4_text is None

    def test_counter_op_diagnostic_names_target(self):
        plan = l4_removal.plan_removal(
            directive="Undo the custom cleanup log format thing.",
            l4_text=_L4_WITH_REPLACE,
        )
        assert "replace step:cycle/cleanup" in plan.diagnostic
        assert "preserved" in plan.diagnostic.lower()

    def test_insert_before_falls_back_to_no_counter_op(self):
        """B1 lesson: insert-before ops can NOT be cancelled by a
        subsequent empty-body replace because the inserted content is
        adjacent-to (not part-of) the step body. The planner correctly
        surfaces no-counter-op-possible so the upstream dialog asks for
        explicit delete confirmation.
        """
        plan = l4_removal.plan_removal(
            directive="Undo the incidents check before filing bugs.",
            l4_text=_L4_WITH_STEP_TARGETED,
        )
        assert plan.path_chosen == "no-counter-op-possible"
        assert plan.requires_explicit_confirmation is True
        assert plan.target is not None
        assert plan.target.op.op_type == "insert-before"


# ---------------------------------------------------------------------------
# plan_removal — AC5 (b) in-place delete with explicit confirmation
# ---------------------------------------------------------------------------


class TestPlanRemovalInPlaceDeletePath:
    def test_in_place_delete_when_explicitly_confirmed(self):
        plan = l4_removal.plan_removal(
            directive="Undo the incidents check.",
            l4_text=_L4_WITH_STEP_TARGETED,
            in_place_delete_confirmed=True,
        )
        assert plan.path_chosen == "in-place-delete"
        assert plan.new_l4_text is not None
        assert "scan incidents/" not in plan.new_l4_text
        # Counter-op text is NOT populated on the delete path
        assert plan.counter_op_text is None

    def test_in_place_delete_diagnostic_names_excised_entry(self):
        plan = l4_removal.plan_removal(
            directive="Undo the incidents check.",
            l4_text=_L4_WITH_STEP_TARGETED,
            in_place_delete_confirmed=True,
        )
        assert "insert-before step:cycle/file-bug" in plan.diagnostic


# ---------------------------------------------------------------------------
# plan_removal — AC5 (c) no-counter-op-possible fallback
# ---------------------------------------------------------------------------


class TestPlanRemovalNoCounterOpFallback:
    def test_append_under_identity_falls_back_to_no_counter_op(self):
        """A removal targeting an Identity ## append (no step target,
        append-only slot) has no clean counter-op shape. Without
        explicit delete confirmation, the planner returns
        ``no-counter-op-possible`` so the upstream dialog re-asks the
        human to explicitly confirm in-place delete.
        """
        plan = l4_removal.plan_removal(
            directive="Drop the security-research toolkit adversarial-input thing.",
            l4_text=_L4_WITH_IDENTITY_APPEND,
        )
        assert plan.path_chosen == "no-counter-op-possible"
        assert plan.requires_explicit_confirmation is True
        assert plan.target is not None
        # File untouched
        assert plan.new_l4_text is None
        assert plan.counter_op_text is None
        # Diagnostic explains the fallback
        assert "in-place delete" in plan.diagnostic.lower()
        assert "in_place_delete_confirmed=True" in plan.diagnostic

    def test_append_under_identity_proceeds_when_confirmed(self):
        """Once the upstream dialog re-asks and the human confirms,
        the same call with confirmed=True goes through in-place delete.
        """
        plan = l4_removal.plan_removal(
            directive="Drop the security-research toolkit adversarial-input thing.",
            l4_text=_L4_WITH_IDENTITY_APPEND,
            in_place_delete_confirmed=True,
        )
        assert plan.path_chosen == "in-place-delete"
        assert "adversarial" not in plan.new_l4_text.lower()


# ---------------------------------------------------------------------------
# plan_removal — backoff / failure modes
# ---------------------------------------------------------------------------


class TestPlanRemovalBackoffs:
    def test_not_a_removal_request_diagnoses_and_backs_off(self):
        plan = l4_removal.plan_removal(
            directive="From now on, scan incidents/ before filing bugs.",
            l4_text=_L4_WITH_STEP_TARGETED,
        )
        assert plan.path_chosen == "not-a-removal-request"
        assert plan.target is None
        assert plan.counter_op_text is None
        assert plan.new_l4_text is None

    def test_not_found_when_directive_does_not_match_any_entry(self):
        plan = l4_removal.plan_removal(
            directive="Undo the colorimetric calibration policy.",
            l4_text=_L4_WITH_STEP_TARGETED,
        )
        assert plan.path_chosen == "not-found"
        assert plan.target is None
        # Diagnostic gives the human actionable next-step guidance
        assert "name" in plan.diagnostic.lower()

    def test_ambiguous_when_multiple_entries_match(self):
        plan = l4_removal.plan_removal(
            directive="Drop the incidents-related rule for bug filing.",
            l4_text=_L4_WITH_AMBIGUOUS,
        )
        assert plan.path_chosen == "ambiguous"
        assert plan.candidates is not None
        assert len(plan.candidates) >= 2
        # No staged content on ambiguous — the upstream dialog has to
        # disambiguate first
        assert plan.counter_op_text is None
        assert plan.new_l4_text is None

    def test_unparseable_l4_returns_not_found_not_raises(self):
        """Defensive: a malformed L4 file should NOT crash the planner
        — return ``not-found`` with the parse error in the diagnostic.

        #10987 update: H3 lines that don't start with a reserved op keyword
        are now treated as prose, not as malformed ops, so a heading like
        ``### gibberish-not-a-real-op`` parses cleanly into an implicit
        append body. Pick an *op-like* malformed heading instead — the
        strict op-grammar still rejects those.
        """
        plan = l4_removal.plan_removal(
            directive="Undo the something thing.",
            l4_text="## Agent Functions\n\n### replace step:cycle/\n\nbody\n",
        )
        assert plan.path_chosen == "not-found"
        assert "unparseable" in plan.diagnostic.lower()


# ---------------------------------------------------------------------------
# RemovalPlan dataclass — convenience surface
# ---------------------------------------------------------------------------


class TestRemovalPlanShape:
    def test_default_plan_has_no_staged_content(self):
        plan = l4_removal.RemovalPlan(path_chosen="not-found")
        assert plan.target is None
        assert plan.counter_op_text is None
        assert plan.new_l4_text is None
        assert plan.requires_explicit_confirmation is False
        assert plan.candidates is None

    def test_path_choice_literal_round_trip(self):
        for path in ("counter-op", "in-place-delete", "ambiguous",
                     "not-found", "no-counter-op-possible",
                     "not-a-removal-request"):
            plan = l4_removal.RemovalPlan(path_chosen=path)
            assert plan.path_chosen == path
