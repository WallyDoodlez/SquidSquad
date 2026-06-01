"""Tests for references/scripts/l4_audit_gate.py (#10652, PRD-C C3)."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_audit_gate  # noqa: E402


# ---------------------------------------------------------------------------
# Stub model_router — records each route() call and writes a canned response
# ---------------------------------------------------------------------------

class _StubRouter:
    """Minimal stand-in for the real model_router module."""

    def __init__(self, response="decision: approve\nreason: looks fine\n",
                 exit_code=0, write_output=True, raise_exception=None):
        self.response = response
        self.exit_code = exit_code
        self.write_output = write_output
        self.raise_exception = raise_exception
        self.calls = []

    def route(self, task_type, task_id, input_files, output_file, context):
        self.calls.append({
            "task_type": task_type,
            "task_id": task_id,
            "input_files": input_files,
            "output_file": output_file,
            "context": context,
        })
        if self.raise_exception is not None:
            raise self.raise_exception
        if self.write_output and self.exit_code == 0:
            Path(output_file).write_text(self.response, encoding="utf-8")
        return self.exit_code


def _audit(**overrides):
    """Default audit_l4_op invocation with sensible test defaults."""
    base = dict(
        op_type="insert-before step:cycle/file-bug",
        target_slot="instructions",
        target_step_id="file-bug",
        target_role_class="pm",
        body_text="Before filing any bug, list incidents/.",
        source_directive="From now on, before filing a bug, also check incidents/.",
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# AC6(a): happy-path approve + proceed
# ---------------------------------------------------------------------------

def test_happy_path_approve_returns_audit_result():
    router = _StubRouter(
        response="decision: approve\nreason: classification matches the directive\n",
    )
    result = l4_audit_gate.audit_l4_op(**_audit(), model_router=router)
    assert result.decision == "approve"
    assert "classification matches" in result.reason
    assert result.suggested_op_type == ""
    assert len(router.calls) == 1
    assert router.calls[0]["task_type"] == "l4-audit"


def test_happy_path_writes_payload_json_as_input_file():
    """The op JSON sent to the model contains all 6 classification inputs."""
    captured = {}

    def route(task_type, task_id, input_files, output_file, context):
        captured["payload"] = json.loads(Path(input_files).read_text(encoding="utf-8"))
        Path(output_file).write_text("decision: approve\nreason: ok\n", encoding="utf-8")
        return 0

    router = type("R", (), {"route": staticmethod(route)})()
    l4_audit_gate.audit_l4_op(**_audit(), model_router=router)
    payload = captured["payload"]
    assert payload["op_type"].startswith("insert-before")
    assert payload["target_slot"] == "instructions"
    assert payload["target_step_id"] == "file-bug"
    assert payload["target_role_class"] == "pm"
    assert "incidents" in payload["body_text"]
    assert "incidents" in payload["source_directive"]


def test_default_task_id_is_derived_from_role_and_op():
    router = _StubRouter()
    l4_audit_gate.audit_l4_op(**_audit(target_role_class="worker"), model_router=router)
    assert router.calls[0]["task_id"] == "l4-audit-worker-insert-before"


def test_custom_task_id_honored():
    router = _StubRouter()
    l4_audit_gate.audit_l4_op(
        **_audit(), task_id="custom-audit-id", model_router=router,
    )
    assert router.calls[0]["task_id"] == "custom-audit-id"


# ---------------------------------------------------------------------------
# AC6(b): DS rejection — agent re-prompts
# ---------------------------------------------------------------------------

def test_rejection_returns_reason_and_suggested_fields():
    router = _StubRouter(response=(
        "decision: reject\n"
        "reason: \"stop doing X\" should be a replace, not an append\n"
        "suggested_op_type: replace step:cycle/deploy-log-check\n"
        "suggested_target_slot: instructions\n"
        "suggested_target_step_id: deploy-log-check\n"
    ))
    result = l4_audit_gate.audit_l4_op(**_audit(), model_router=router)
    assert result.decision == "reject"
    assert "should be a replace" in result.reason
    assert result.suggested_op_type == "replace step:cycle/deploy-log-check"
    assert result.suggested_target_slot == "instructions"
    assert result.suggested_target_step_id == "deploy-log-check"


def test_rejection_without_suggested_fields_is_legal():
    """Suggested fields are optional — a bare rejection is still parseable."""
    router = _StubRouter(response="decision: reject\nreason: too vague\n")
    result = l4_audit_gate.audit_l4_op(**_audit(), model_router=router)
    assert result.decision == "reject"
    assert result.reason == "too vague"
    assert result.suggested_op_type == ""


def test_decision_field_case_insensitive():
    router = _StubRouter(response="Decision: REJECT\nreason: caps don't matter\n")
    result = l4_audit_gate.audit_l4_op(**_audit(), model_router=router)
    assert result.decision == "reject"


def test_decision_field_invalid_value_raises():
    router = _StubRouter(response="decision: maybe\nreason: model dithered\n")
    with pytest.raises(l4_audit_gate.AuditParseError):
        l4_audit_gate.audit_l4_op(**_audit(), model_router=router)


def test_decision_field_missing_raises():
    router = _StubRouter(response="reason: model forgot the decision\n")
    with pytest.raises(l4_audit_gate.AuditParseError):
        l4_audit_gate.audit_l4_op(**_audit(), model_router=router)


# ---------------------------------------------------------------------------
# AC6(c): model_router timeout / failure modes (write aborted)
# ---------------------------------------------------------------------------

def test_router_timeout_raises_audit_timeout_error():
    router = _StubRouter(exit_code=3, write_output=False)
    with pytest.raises(l4_audit_gate.AuditTimeoutError) as exc:
        l4_audit_gate.audit_l4_op(**_audit(), model_router=router)
    assert "exit code 3" in str(exc.value)
    assert "Gate 1 abort" in str(exc.value)


def test_router_non_zero_exit_raises_router_error():
    router = _StubRouter(exit_code=1, write_output=False)
    with pytest.raises(l4_audit_gate.AuditModelRouterError) as exc:
        l4_audit_gate.audit_l4_op(**_audit(), model_router=router)
    assert "exit code 1" in str(exc.value)


def test_router_raises_exception_classified_as_router_error():
    router = _StubRouter(raise_exception=RuntimeError("connection refused"))
    with pytest.raises(l4_audit_gate.AuditModelRouterError) as exc:
        l4_audit_gate.audit_l4_op(**_audit(), model_router=router)
    assert "connection refused" in str(exc.value)


def test_router_success_with_no_output_raises_output_missing():
    router = _StubRouter(exit_code=0, write_output=False)
    with pytest.raises(l4_audit_gate.AuditOutputMissingError):
        l4_audit_gate.audit_l4_op(**_audit(), model_router=router)


def test_audit_gate_error_subclasses_runtimeerror():
    """All four failure-mode types share a base class so callers can catch broadly."""
    for cls in (
        l4_audit_gate.AuditModelRouterError,
        l4_audit_gate.AuditTimeoutError,
        l4_audit_gate.AuditOutputMissingError,
        l4_audit_gate.AuditParseError,
    ):
        assert issubclass(cls, l4_audit_gate.AuditGateError)
        assert issubclass(cls, RuntimeError)


# ---------------------------------------------------------------------------
# Template + task type registration
# ---------------------------------------------------------------------------

def test_model_router_recognizes_l4_audit_task_type():
    import model_router
    template = model_router._load_prompt_template("l4-audit")
    assert template is not None
    assert "decision:" in template  # the parser's anchor


def test_l4_audit_template_exists_at_canonical_path():
    repo_root = Path(__file__).resolve().parent.parent
    assert (repo_root / "references" / "prompts" / "l4-audit.md.j2").exists()


def test_l4_audit_template_documents_reject_for_vault():
    """Vault is L1-exclusive; the template must instruct rejection."""
    repo_root = Path(__file__).resolve().parent.parent
    text = (repo_root / "references" / "prompts" / "l4-audit.md.j2").read_text(encoding="utf-8")
    assert "vault" in text.lower()
    assert "REJECT" in text or "reject" in text


def test_l4_audit_template_enumerates_all_five_op_types():
    """The template's parser depends on the model emitting one of the 5 legal ops."""
    repo_root = Path(__file__).resolve().parent.parent
    text = (repo_root / "references" / "prompts" / "l4-audit.md.j2").read_text(encoding="utf-8")
    assert "append" in text
    assert "replace step:cycle" in text
    assert "insert-before step:cycle" in text
    assert "insert-after step:cycle" in text
