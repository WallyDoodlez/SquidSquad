"""Assemble pass scaffolding — per-slot LLM rewrite (#10444, PRD-B Story B1).

Per [[compose-assemble-stage]] §4.6, after the link stage produces a
per-slot linked composite, each non-skipped slot's linked body passes
through an agent-driven rewrite that collapses the layered prose into a
single coherent voice. B1 wires the per-slot dispatch:

- ``project-context`` and ``vault`` slots are NOT rewritten — they pass
  through verbatim. Project-context is L4-authored as-is and vault is
  framework-owned; both are read by the agent as the human intended.
- Every other slot is dispatched to ``model_router`` with the new
  ``"assemble"`` task type (template at ``references/prompts/assemble.md.j2``).

B1 does NOT enforce preservation (B2 #10441 does), conflict detection
(B4 #10445), cache (B6), or atomic write (B7 #10447). It is the
plumbing PR — the LLM is called, the body comes back, callers (B7 + B2)
own the rest.
"""

import os
import tempfile
from pathlib import Path


VERBATIM_SLOTS = frozenset({"project-context", "vault"})

# Per-call tempfiles live UNDER the repo root (``.squidsquad/tmp/assemble/``)
# so they satisfy ``model_router._is_path_in_sandbox``. The router refuses
# to read input paths resolved outside REPO_ROOT — using the system temp
# dir (``%TEMP%`` / ``/tmp``) made the linked body invisible to the LLM
# (#10444 QA route-back).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ASSEMBLE_TMP_ROOT = _REPO_ROOT / ".squidsquad" / "tmp" / "assemble"


def assemble_slot(slot_name, linked_body, *, task_id=None, model_router=None):
    """Run the assemble pass on one slot. Returns the assembled body as a string.

    ``project-context`` and ``vault`` are returned verbatim per the AC.

    For other slots, ``model_router.route`` is invoked with task_type
    ``"assemble"``, the linked body written to a tempfile (the router's
    file-based input convention), and the response read back from the
    router's output file.

    ``model_router`` — an optional injected reference to the
    ``model_router`` module. Tests pass a stub here so the unit tests
    don't depend on a live LLM. When omitted, the real module is
    imported lazily.

    ``task_id`` — optional id used in router diagnostics. Defaults to
    ``f"assemble-{slot_name}"``.
    """
    if slot_name in VERBATIM_SLOTS:
        return linked_body

    if model_router is None:
        import model_router as _real_router  # noqa: WPS433
        model_router = _real_router

    if task_id is None:
        task_id = f"assemble-{slot_name}"

    # Router uses file-based I/O; write linked body to a temp input file
    # and ask it to produce its response in a temp output file. The temp
    # directory lives UNDER the repo root so the router's sandbox check
    # (`_is_path_in_sandbox`) accepts the input path. Using the system
    # tempdir would resolve outside REPO_ROOT and the router would skip
    # the input with "Path outside repository boundary" (#10444 QA finding).
    _ASSEMBLE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"assemble-{slot_name}-",
                                     dir=str(_ASSEMBLE_TMP_ROOT)) as td:
        td_path = Path(td)
        input_path = td_path / f"linked-{slot_name}.md"
        output_path = td_path / f"assembled-{slot_name}.md"
        input_path.write_text(linked_body, encoding="utf-8")

        # PRD-B SC3 + #10752 W4: the LLM context names all FOUR
        # preservation dimensions the verifier checks (sub-skill refs,
        # step IDs, fenced code blocks verbatim, file paths). Pre-fix
        # the context only mentioned sub-skill + step-ID, so the LLM
        # might rewrite fenced bodies or strip file paths and only be
        # caught at verification time — that path either retries the
        # LLM (cache-corruption fallback) or aborts (fresh-run
        # PreservationFail). Including the full guarantee set upfront
        # is cheaper than the abort cycle.
        context = (
            f"Rewrite the LINKED body for the `{slot_name}` slot into a "
            f"single coherent voice while preserving (a) every "
            f"`→ run sub-skill: <name>` reference verbatim, (b) every "
            f"`step:cycle/<id>` reference verbatim, (c) every fenced "
            f"code block (the lang tag AND the body content) verbatim, "
            f"and (d) every file path token (anything containing a `/` "
            f"and ending in a small extension) verbatim. Higher-layer "
            f"prose wins on contradiction (L4 > L3 > L2 > L1)."
        )

        exit_code = model_router.route(
            task_type="assemble",
            task_id=task_id,
            input_files=str(input_path),
            output_file=str(output_path),
            context=context,
        )

        if exit_code != 0:
            # Per route()'s contract: non-zero = fallback path (Claude
            # via Agent tool / config error / timeout). B1's caller (B7)
            # will own the abort-on-LLM-error path; here we surface a
            # clear error and let the caller decide.
            raise AssembleSlotError(
                f"model_router.route returned exit code {exit_code} for "
                f"assemble task_id={task_id} slot={slot_name}. See router "
                f"diagnostics in .squidsquad/diagnostics/model-routing.log."
            )

        if not output_path.exists():
            raise AssembleSlotError(
                f"model_router.route produced no output file for "
                f"task_id={task_id} slot={slot_name}. Expected at "
                f"{output_path}."
            )

        body = output_path.read_text(encoding="utf-8")

    return body


class AssembleSlotError(RuntimeError):
    """Raised when ``assemble_slot`` cannot obtain an assembled body.

    B7 (#10447) catches this and routes to the abort path per the
    §4.6 atomic-write contract; B1's contract is to raise.
    """
