"""Tests for references/scripts/l4_conflict_preempt.py (#10657, PRD-C C8).

AC5 mandates at least:
  (a) clean insert → no surfacing
  (b) inserting a constraint that contradicts an L2 instruction →
      surface + reframe offered
  (c) `replace` op never triggers pre-emption (replace supersedes)

Plus the standard C3-shaped failure-mode coverage (model_router
exception / non-zero exit / timeout / missing output / parse error)
and the human-facing formatter.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_conflict_preempt as cp  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_LINKED_COMPOSITE = (
    "## Instructions\n\n"
    "### step:cycle/file-bug\n\n"
    "Always include a reproduction case and the failing test command.\n"
    "Bugs without a reproduction route back to the reporter.\n\n"
    "### step:cycle/cleanup\n\n"
    "Clear working state and write the iteration log entry.\n"
)


def _make_router(*, exit_code=0, output_text=None, raise_exc=None,
                  write_output=True):
    """Build a stub model_router with the `.route` callable shape.

    Records calls in ``calls`` for assertions. Writes ``output_text`` to
    the ``output_file`` argument BEFORE returning ``exit_code`` so the
    helper finds the file. Setting ``write_output=False`` simulates the
    router-reported-success-but-no-output failure mode.
    """
    calls = []

    def route(*, task_type, task_id, input_files, output_file, context):
        calls.append({
            "task_type": task_type,
            "task_id": task_id,
            "input_files": input_files,
            "output_file": output_file,
            "context": context,
        })
        if raise_exc is not None:
            raise raise_exc
        if write_output and output_text is not None:
            Path(output_file).write_text(output_text, encoding="utf-8")
        return exit_code

    return SimpleNamespace(route=route), calls


# ---------------------------------------------------------------------------
# AC5(c) — replace ops short-circuit (no LLM dispatch)
# ---------------------------------------------------------------------------


class TestReplaceOpShortCircuits:
    def test_step_targeted_replace_skips_dispatch(self):
        router, calls = _make_router(output_text="UNUSED")
        result = cp.preempt_conflict(
            op_type="replace step:cycle/file-bug",
            target_slot="instructions",
            target_step_id="file-bug",
            target_role_class="worker",
            body_text="Custom file-bug body.",
            linked_composite=_LINKED_COMPOSITE,
            source_directive="Replace the file-bug step with the new approach.",
            model_router=router,
        )
        assert result.decision == "skip"
        assert result.proceeds_to_gate_1 is True
        assert result.is_contradiction is False
        # The LLM was NOT invoked
        assert calls == []

    def test_whole_slot_replace_also_skips(self):
        router, calls = _make_router(output_text="UNUSED")
        result = cp.preempt_conflict(
            op_type="replace",
            target_slot="responsibility",
            target_step_id=None,
            target_role_class="worker",
            body_text="Wholesale-redefined responsibility block.",
            linked_composite=_LINKED_COMPOSITE,
            source_directive="Replace the worker's responsibility.",
            model_router=router,
        )
        assert result.decision == "skip"
        assert calls == []

    def test_skip_result_reason_explains_why(self):
        router, _ = _make_router(output_text="UNUSED")
        result = cp.preempt_conflict(
            op_type="replace step:cycle/file-bug",
            target_slot="instructions", target_step_id="file-bug",
            target_role_class="worker", body_text="x",
            linked_composite=_LINKED_COMPOSITE, source_directive="x",
            model_router=router,
        )
        assert "supersede" in result.why.lower()

    def test_malformed_replace_does_not_short_circuit(self):
        """B1 fix: ``op_type`` allowlist matches the grammar exactly,
        so ``"replace foo"`` / ``"replace step:not-cycle/x"`` / ``"replace-typo"``
        are NOT routed past Gate 0 as skips. The LLM dispatch fires
        (and will likely raise — that's the right behavior; garbage
        op_types should be caught loudly).
        """
        router, calls = _make_router(output_text=(
            "decision: clean\nwhy: malformed op_type still ran dispatch\n"
        ))
        # "replace foo" — extra-token shape that the old split()[0]
        # check would have wrongly accepted as a skip
        cp.preempt_conflict(
            op_type="replace foo",
            target_slot="instructions", target_step_id=None,
            target_role_class="worker", body_text="x",
            linked_composite=_LINKED_COMPOSITE, source_directive="x",
            model_router=router,
        )
        # The LLM was dispatched (not short-circuited)
        assert len(calls) == 1

    def test_step_targeted_replace_with_non_cycle_target_does_not_short_circuit(self):
        router, calls = _make_router(output_text=(
            "decision: clean\nwhy: non-cycle target still ran dispatch\n"
        ))
        cp.preempt_conflict(
            op_type="replace step:not-cycle/foo",
            target_slot="instructions", target_step_id="foo",
            target_role_class="worker", body_text="x",
            linked_composite=_LINKED_COMPOSITE, source_directive="x",
            model_router=router,
        )
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# AC5(a) — clean insert path
# ---------------------------------------------------------------------------


class TestCleanInsertPath:
    def test_clean_decision_parses_and_advances_to_gate_1(self):
        router, calls = _make_router(output_text=(
            "decision: clean\n"
            "why: The new directive supplements rather than contradicting the existing step.\n"
        ))
        result = cp.preempt_conflict(
            op_type="insert-after step:cycle/file-bug",
            target_slot="instructions",
            target_step_id="file-bug",
            target_role_class="worker",
            body_text="After filing the bug, notify the on-call rotation.",
            linked_composite=_LINKED_COMPOSITE,
            source_directive="After filing any bug, notify on-call.",
            model_router=router,
        )
        assert result.decision == "clean"
        assert result.proceeds_to_gate_1 is True
        assert result.is_contradiction is False
        # All contradiction-specific fields empty on clean
        assert result.quote_new == ""
        assert result.quote_existing == ""
        assert result.suggested_action == ""
        # LLM was dispatched (one call)
        assert len(calls) == 1
        assert calls[0]["task_type"] == "l4-conflict-preempt"

    def test_append_op_also_dispatches(self):
        router, calls = _make_router(output_text=(
            "decision: clean\n"
            "why: Adds a sub-skill reference; no overlap.\n"
        ))
        result = cp.preempt_conflict(
            op_type="append",
            target_slot="instructions", target_step_id=None,
            target_role_class="worker",
            body_text="→ run sub-skill: security-smoke\n\nOnce a week run security smoke.",
            linked_composite=_LINKED_COMPOSITE,
            source_directive="Run security smoke weekly.",
            model_router=router,
        )
        assert result.decision == "clean"
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# AC5(b) — contradiction path with quotes + suggested_action
# ---------------------------------------------------------------------------


class TestContradictionPath:
    _CONTRADICTING_RESPONSE = (
        "decision: contradiction\n"
        "why: The proposed body forbids reproduction cases, but the existing step requires them.\n"
        "quote_new: Bugs are filed without a reproduction case to speed up triage.\n"
        "quote_existing: Always include a reproduction case and the failing test command.\n"
        "suggested_action: replace-reframe\n"
    )

    def test_contradiction_decision_surfaces_quotes(self):
        router, _ = _make_router(output_text=self._CONTRADICTING_RESPONSE)
        result = cp.preempt_conflict(
            op_type="insert-before step:cycle/file-bug",
            target_slot="instructions", target_step_id="file-bug",
            target_role_class="worker",
            body_text="Bugs are filed without a reproduction case to speed up triage.",
            linked_composite=_LINKED_COMPOSITE,
            source_directive="Don't require reproduction cases anymore.",
            model_router=router,
        )
        assert result.decision == "contradiction"
        assert result.is_contradiction is True
        assert result.proceeds_to_gate_1 is False
        assert "reproduction" in result.quote_new.lower()
        assert "reproduction" in result.quote_existing.lower()
        assert result.suggested_action == "replace-reframe"
        assert "forbid" in result.why.lower()

    def test_contradiction_with_reword_suggestion(self):
        router, _ = _make_router(output_text=(
            "decision: contradiction\n"
            "why: Slight overlap; a wording change would lift the contradiction.\n"
            "quote_new: Skip the cleanup step\n"
            "quote_existing: Clear working state and write the iteration log entry.\n"
            "suggested_action: reword\n"
        ))
        result = cp.preempt_conflict(
            op_type="append",
            target_slot="instructions", target_step_id=None,
            target_role_class="worker",
            body_text="Skip the cleanup step on dry runs.",
            linked_composite=_LINKED_COMPOSITE,
            source_directive="Skip cleanup on dry runs.",
            model_router=router,
        )
        assert result.suggested_action == "reword"


# ---------------------------------------------------------------------------
# format_contradiction_for_human
# ---------------------------------------------------------------------------


class TestFormatContradictionForHuman:
    def test_clean_result_renders_empty_string(self):
        result = cp.PreemptResult(decision="clean", why="all good")
        assert cp.format_contradiction_for_human(result) == ""

    def test_skip_result_renders_empty_string(self):
        result = cp.PreemptResult(decision="skip", why="replace supersedes")
        assert cp.format_contradiction_for_human(result) == ""

    def test_contradiction_renders_both_quotes(self):
        result = cp.PreemptResult(
            decision="contradiction",
            why="The new rule conflicts with the existing step.",
            quote_new="Bugs are filed without a reproduction.",
            quote_existing="Always include a reproduction case.",
            suggested_action="replace-reframe",
        )
        out = cp.format_contradiction_for_human(result)
        assert "Bugs are filed without a reproduction." in out
        assert "Always include a reproduction case." in out
        assert "What you're asking to add" in out
        assert "What the role already does" in out
        assert "Why this matters" in out
        assert "Options" in out
        # The model's recommendation is rendered first + tagged
        assert "(recommended)" in out

    def test_quote_with_embedded_newline_renders_as_multi_line_blockquote(self):
        """C2 fix: if the LLM ignores the prompt's single-line
        constraint and emits a multi-line quote, every line gets the
        ``> `` prefix so the blockquote doesn't silently terminate
        and the next prose isn't rendered as a stray paragraph.
        """
        result = cp.PreemptResult(
            decision="contradiction",
            why="x",
            quote_new="Line one of the quote.\nLine two of the quote.",
            quote_existing="Existing line one.",
            suggested_action="reword",
        )
        out = cp.format_contradiction_for_human(result)
        # Both lines of the multi-line quote are blockquoted
        assert "> Line one of the quote." in out
        assert "> Line two of the quote." in out

    def test_missing_quotes_render_as_placeholder(self):
        result = cp.PreemptResult(
            decision="contradiction",
            why="x", quote_new="", quote_existing="",
            suggested_action="reword",
        )
        out = cp.format_contradiction_for_human(result)
        # Both sides get the canonical missing-quote marker
        assert out.count("(no quote provided)") == 2

    def test_contradiction_with_reword_recommends_reword_first(self):
        result = cp.PreemptResult(
            decision="contradiction",
            why="x", quote_new="x", quote_existing="x",
            suggested_action="reword",
        )
        out = cp.format_contradiction_for_human(result)
        # Reword is the recommended option
        reword_line = [l for l in out.splitlines() if "(recommended)" in l][0]
        assert "Rephrase" in reword_line


# ---------------------------------------------------------------------------
# Failure modes — mirror C3 audit-gate shape
# ---------------------------------------------------------------------------


class TestFailureModes:
    def test_model_router_exception_raises_PreemptModelRouterError(self):
        router, _ = _make_router(raise_exc=RuntimeError("API down"))
        with pytest.raises(cp.PreemptModelRouterError) as e:
            cp.preempt_conflict(
                op_type="append", target_slot="instructions",
                target_step_id=None, target_role_class="worker",
                body_text="x", linked_composite=_LINKED_COMPOSITE,
                source_directive="x", model_router=router,
            )
        assert "API down" in str(e.value)

    def test_nonzero_exit_raises_PreemptModelRouterError(self):
        router, _ = _make_router(exit_code=1)
        with pytest.raises(cp.PreemptModelRouterError) as e:
            cp.preempt_conflict(
                op_type="append", target_slot="instructions",
                target_step_id=None, target_role_class="worker",
                body_text="x", linked_composite=_LINKED_COMPOSITE,
                source_directive="x", model_router=router,
            )
        assert "exit code 1" in str(e.value)

    def test_exit_code_3_raises_PreemptTimeoutError(self):
        router, _ = _make_router(exit_code=3)
        with pytest.raises(cp.PreemptTimeoutError):
            cp.preempt_conflict(
                op_type="append", target_slot="instructions",
                target_step_id=None, target_role_class="worker",
                body_text="x", linked_composite=_LINKED_COMPOSITE,
                source_directive="x", model_router=router,
            )

    def test_missing_output_file_raises_PreemptOutputMissingError(self):
        router, _ = _make_router(exit_code=0, write_output=False)
        with pytest.raises(cp.PreemptOutputMissingError):
            cp.preempt_conflict(
                op_type="append", target_slot="instructions",
                target_step_id=None, target_role_class="worker",
                body_text="x", linked_composite=_LINKED_COMPOSITE,
                source_directive="x", model_router=router,
            )

    def test_missing_decision_line_raises_PreemptParseError(self):
        router, _ = _make_router(output_text="why: looks fine\n")
        with pytest.raises(cp.PreemptParseError) as e:
            cp.preempt_conflict(
                op_type="append", target_slot="instructions",
                target_step_id=None, target_role_class="worker",
                body_text="x", linked_composite=_LINKED_COMPOSITE,
                source_directive="x", model_router=router,
            )
        assert "decision:" in str(e.value)

    def test_invalid_decision_value_raises_PreemptParseError(self):
        router, _ = _make_router(output_text="decision: maybe\nwhy: x\n")
        with pytest.raises(cp.PreemptParseError) as e:
            cp.preempt_conflict(
                op_type="append", target_slot="instructions",
                target_step_id=None, target_role_class="worker",
                body_text="x", linked_composite=_LINKED_COMPOSITE,
                source_directive="x", model_router=router,
            )
        assert "maybe" in str(e.value)

    def test_exception_hierarchy(self):
        """Subclasses all inherit from ConflictPreemptError so callers
        can catch the base in one except clause.
        """
        for sub in (cp.PreemptModelRouterError, cp.PreemptTimeoutError,
                    cp.PreemptOutputMissingError, cp.PreemptParseError):
            assert issubclass(sub, cp.ConflictPreemptError)


# ---------------------------------------------------------------------------
# Sandbox + dispatch payload sanity
# ---------------------------------------------------------------------------


class TestDispatchPayload:
    def test_payload_contains_linked_composite(self, tmp_path):
        """The linked composite is the corpus the model checks against;
        verify it's serialized into the input file the router sees.
        """
        captured = {}

        def route(*, task_type, task_id, input_files, output_file, context):
            captured["input"] = Path(input_files).read_text(encoding="utf-8")
            Path(output_file).write_text("decision: clean\nwhy: ok\n", encoding="utf-8")
            return 0

        router = SimpleNamespace(route=route)
        cp.preempt_conflict(
            op_type="append", target_slot="instructions",
            target_step_id=None, target_role_class="worker",
            body_text="Some new rule.",
            linked_composite=_LINKED_COMPOSITE,
            source_directive="Add a new rule.",
            model_router=router,
        )
        payload = json.loads(captured["input"])
        assert "linked_composite" in payload
        assert "Always include a reproduction case" in payload["linked_composite"]
        assert payload["body_text"] == "Some new rule."

    def test_dispatch_input_lives_under_repo_root(self):
        """Sandbox boundary rule: tempfiles for model_router must live
        under REPO_ROOT, not the system tempdir. The helper uses
        _PREEMPT_TMP_ROOT which is REPO_ROOT-relative.
        """
        captured = {}

        def route(*, task_type, task_id, input_files, output_file, context):
            captured["path"] = input_files
            Path(output_file).write_text("decision: clean\nwhy: ok\n", encoding="utf-8")
            return 0

        router = SimpleNamespace(route=route)
        cp.preempt_conflict(
            op_type="append", target_slot="instructions",
            target_step_id=None, target_role_class="worker",
            body_text="x", linked_composite=_LINKED_COMPOSITE,
            source_directive="x", model_router=router,
        )
        assert ".squidsquad" in captured["path"]
        assert "l4-conflict-preempt" in captured["path"]


# ---------------------------------------------------------------------------
# PreemptResult shape
# ---------------------------------------------------------------------------


class TestPreemptResultShape:
    def test_default_optional_fields_are_empty_strings(self):
        result = cp.PreemptResult(decision="clean")
        assert result.why == ""
        assert result.quote_new == ""
        assert result.quote_existing == ""
        assert result.suggested_action == ""

    def test_proceeds_to_gate_1_property(self):
        assert cp.PreemptResult(decision="clean").proceeds_to_gate_1 is True
        assert cp.PreemptResult(decision="skip").proceeds_to_gate_1 is True
        assert cp.PreemptResult(decision="contradiction").proceeds_to_gate_1 is False
