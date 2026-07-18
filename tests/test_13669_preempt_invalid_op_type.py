"""Regression test for #13669 — l4_conflict_preempt.preempt_conflict()'s
own module docstring promises "every unrecoverable path raises a typed
ConflictPreemptError subclass," but the replace-op short-circuit guard
(``if op_type and _REPLACE_OP_RE.match(op_type):``) let a falsy op_type
fall through to ``op_type.split()[0]`` at task_id construction. Empirically
reproduced (unmocked call): op_type="" raised IndexError, op_type=None
raised AttributeError — neither a ConflictPreemptError.

Fix: an explicit ``if not op_type:`` guard at the top of preempt_conflict()
raises the new PreemptInvalidOpTypeError(ConflictPreemptError) before the
replace-op short-circuit, so this failure mode is a typed exception like
every other unrecoverable path in the module.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_conflict_preempt as cp


_KWARGS = dict(
    target_slot="instructions",
    target_step_id=None,
    target_role_class="pm",
    body_text="new rule text",
    linked_composite="existing prose",
    source_directive="from now on...",
)


class TestEmptyOrNoneOpTypeRaisesTypedError13669:
    def test_empty_string_raises_typed_error(self):
        with pytest.raises(cp.PreemptInvalidOpTypeError):
            cp.preempt_conflict(op_type="", model_router=object(), **_KWARGS)

    def test_none_raises_typed_error(self):
        with pytest.raises(cp.PreemptInvalidOpTypeError):
            cp.preempt_conflict(op_type=None, model_router=object(), **_KWARGS)

    def test_typed_error_is_a_conflict_preempt_error(self):
        assert issubclass(cp.PreemptInvalidOpTypeError, cp.ConflictPreemptError)

    def test_never_reaches_model_router_dispatch(self):
        """The guard must fire BEFORE any model_router call -- a poisoned
        model_router stub that raises on any attribute access proves the
        dispatch path was never reached."""
        class _PoisonRouter:
            def __getattr__(self, name):
                raise AssertionError(
                    f"model_router.{name} should never be touched for an "
                    "invalid op_type"
                )

        with pytest.raises(cp.PreemptInvalidOpTypeError):
            cp.preempt_conflict(op_type="", model_router=_PoisonRouter(), **_KWARGS)

    def test_error_message_names_the_bad_value(self):
        with pytest.raises(cp.PreemptInvalidOpTypeError, match="op_type"):
            cp.preempt_conflict(op_type="", model_router=object(), **_KWARGS)


class TestValidOpTypesStillWork13669:
    """Guard against over-tightening: legal grammar shapes must be unaffected."""

    def test_replace_still_short_circuits(self):
        result = cp.preempt_conflict(
            op_type="replace", model_router=object(), **_KWARGS
        )
        assert result.decision == "skip"

    def test_step_targeted_replace_still_short_circuits(self):
        result = cp.preempt_conflict(
            op_type="replace step:cycle/file-bug", model_router=object(), **_KWARGS
        )
        assert result.decision == "skip"
