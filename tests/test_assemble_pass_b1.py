"""Tests for references/scripts/assemble_pass.py (#10444, PRD-B Story B1)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import assemble_pass  # noqa: E402


# ---------------------------------------------------------------------------
# A simple stub router that records calls and produces a canned response.
# ---------------------------------------------------------------------------

class _StubRouter:
    """Minimal stand-in for the real model_router module.

    Records each ``route()`` invocation and writes a canned response to
    the output file so the caller's ``read_text`` succeeds.
    """

    def __init__(self, response="ASSEMBLED BODY\n", exit_code=0):
        self.response = response
        self.exit_code = exit_code
        self.calls = []

    def route(self, task_type, task_id, input_files, output_file, context):
        self.calls.append({
            "task_type": task_type,
            "task_id": task_id,
            "input_files": input_files,
            "output_file": output_file,
            "context": context,
        })
        if self.exit_code == 0:
            Path(output_file).write_text(self.response, encoding="utf-8")
        return self.exit_code


# ---------------------------------------------------------------------------
# AC: verbatim pass-through for project-context + vault
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("verbatim_slot", ["project-context", "vault"])
def test_assemble_slot_returns_verbatim_for_special_slots(verbatim_slot):
    """project-context and vault skip the LLM call entirely — returned verbatim."""
    linked = "Some L4-authored project-context body.\n"
    router = _StubRouter()
    out = assemble_pass.assemble_slot(verbatim_slot, linked, model_router=router)
    assert out == linked
    # AC: 'no live LLM calls' — verbatim slots must not invoke the router.
    assert router.calls == []


def test_assemble_slot_verbatim_pass_through_with_empty_body():
    """Empty body for a verbatim slot is still legal — pass through."""
    out = assemble_pass.assemble_slot("vault", "", model_router=_StubRouter())
    assert out == ""


# ---------------------------------------------------------------------------
# AC: assemble_slot calls model_router with task_type="assemble"
# ---------------------------------------------------------------------------

def test_assemble_slot_dispatches_to_router_for_normal_slots():
    router = _StubRouter(response="rewritten identity\n")
    out = assemble_pass.assemble_slot("identity", "Layered identity prose.\n",
                                      model_router=router)
    assert out == "rewritten identity\n"
    assert len(router.calls) == 1
    assert router.calls[0]["task_type"] == "assemble"


def test_assemble_slot_uses_default_task_id_for_slot():
    router = _StubRouter()
    assemble_pass.assemble_slot("instructions", "body", model_router=router)
    assert router.calls[0]["task_id"] == "assemble-instructions"


def test_assemble_slot_honors_custom_task_id():
    router = _StubRouter()
    assemble_pass.assemble_slot(
        "soul", "body", task_id="custom-soul-task", model_router=router,
    )
    assert router.calls[0]["task_id"] == "custom-soul-task"


def test_assemble_slot_writes_linked_body_to_input_file_for_router():
    """The router gets a file path. Verify the file contains the linked body."""
    linked = "MUST APPEAR IN INPUT FILE\n"
    captured_input = {}

    def route(task_type, task_id, input_files, output_file, context):
        # Capture file contents at call time (before TemporaryDirectory unlinks).
        captured_input["contents"] = Path(input_files).read_text(encoding="utf-8")
        Path(output_file).write_text("ok", encoding="utf-8")
        return 0

    router = type("R", (), {"route": staticmethod(route)})()
    assemble_pass.assemble_slot("instructions", linked, model_router=router)
    assert captured_input["contents"] == linked


def test_assemble_slot_passes_slot_name_into_router_context():
    router = _StubRouter()
    assemble_pass.assemble_slot("instructions", "body", model_router=router)
    assert "instructions" in router.calls[0]["context"]


def test_assemble_slot_returns_router_output_verbatim():
    """The assembled body comes from what the router wrote to output_file."""
    expected = "THE ROUTER'S RESPONSE\nLINE TWO\n"
    router = _StubRouter(response=expected)
    out = assemble_pass.assemble_slot("identity", "linked", model_router=router)
    assert out == expected


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_assemble_slot_raises_when_router_returns_nonzero():
    router = _StubRouter(exit_code=1)
    with pytest.raises(assemble_pass.AssembleSlotError) as exc:
        assemble_pass.assemble_slot("identity", "linked", model_router=router)
    assert "exit code 1" in str(exc.value)
    assert "identity" in str(exc.value)


def test_assemble_slot_raises_when_router_writes_no_output():
    """A 'success' return with no output file is still a failure — protect downstream."""
    class NoOutputRouter:
        def route(self, task_type, task_id, input_files, output_file, context):
            # Intentionally do not write output_file.
            return 0

    with pytest.raises(assemble_pass.AssembleSlotError) as exc:
        assemble_pass.assemble_slot("identity", "linked",
                                    model_router=NoOutputRouter())
    assert "no output file" in str(exc.value)


# ---------------------------------------------------------------------------
# Template + task_type registration in model_router (AC: 'new model_router task type')
# ---------------------------------------------------------------------------

def test_model_router_recognizes_assemble_task_type():
    """The 'assemble' task type must be registered in _load_prompt_template."""
    import model_router
    template = model_router._load_prompt_template("assemble")
    assert template is not None
    assert "sub-skill" in template  # the preservation guidance


def test_assemble_template_exists_at_canonical_path():
    """AC: 'prompt template at references/prompts/assemble.md.j2'."""
    repo_root = Path(__file__).resolve().parent.parent
    template_path = repo_root / "references" / "prompts" / "assemble.md.j2"
    assert template_path.exists()


def test_assemble_template_includes_required_preservation_directives():
    """The template MUST direct the LLM to preserve sub-skill refs and step IDs.

    B2's preservation pass relies on these being preserved; if the
    prompt doesn't say so, B2 will routinely fail and trigger aborts.
    """
    repo_root = Path(__file__).resolve().parent.parent
    template_path = repo_root / "references" / "prompts" / "assemble.md.j2"
    text = template_path.read_text(encoding="utf-8")
    # Sub-skill references (verbatim in the template — escaped vs plain
    # doesn't matter, the string is what gets sent to the LLM).
    assert "sub-skill" in text.lower()
    assert "step:cycle" in text
    # Conflict resolution direction.
    assert "L4 > L3 > L2 > L1" in text or "higher" in text.lower()
