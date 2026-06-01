"""Gate 1: DeepSeek audit of an L4 op classification (#10652, PRD-C C3).

Wraps the dispatch to ``model_router`` with task type ``l4-audit``. The
audit reviews the agent's L4 op classification (slot + op + target) and
returns an approve/reject + reason. Rejections may include suggested
corrections.

Per the §7.4 three-gate model, Gate 1 runs BEFORE the mini-CQ (Gate 2)
confirmation; an approval here advances to Gate 2, a rejection routes
back to the agent's elicitation flow with the DS reason surfaced to the
human.

This module is the dispatch + result parser. The integration into the
``l4-curation`` sub-skill prose (composed at v2 emit time) lives in
``references/sub-skills/common/l4-curation.md``; this Python helper is
what the runtime agent calls to perform the dispatch.
"""

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


# Same sandbox constraint as B1: tempfiles for model_router input/output
# must live INSIDE REPO_ROOT or ``_is_path_in_sandbox`` rejects them and
# the LLM never sees the input. Captured as a key decision after the
# #10444 QA route-back; documented here so the audit gate doesn't repeat
# the mistake.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AUDIT_TMP_ROOT = _REPO_ROOT / ".squidsquad" / "tmp" / "l4-audit"


@dataclass
class AuditResult:
    """Parsed result of one Gate 1 audit dispatch.

    ``decision`` is ``"approve"`` or ``"reject"``; any other value (or
    a parse failure) is treated as a failure mode by callers and aborts
    the write per the §7.4 contract (failure-modes table).

    ``reason`` is the one-sentence rationale surfaced to the human on
    rejection (or to the audit log on approval).

    The three ``suggested_*`` fields are optional rejection hints; empty
    strings when not provided by the model.
    """

    decision: str
    reason: str
    suggested_op_type: str = ""
    suggested_target_slot: str = ""
    suggested_target_step_id: str = ""


class AuditGateError(RuntimeError):
    """Raised when the audit dispatch cannot produce a decision.

    Callers (``l4-curation``) treat this as Gate 1 abort per the §7.4
    failure-modes table: write aborted, human surfaced with diagnostic.
    Subclasses distinguish the specific failure mode so the caller can
    render an actionable message.
    """


class AuditModelRouterError(AuditGateError):
    """``model_router.route`` returned non-zero (config / API / etc.)."""


class AuditTimeoutError(AuditGateError):
    """``model_router.route`` returned exit code 3 (timeout)."""


class AuditOutputMissingError(AuditGateError):
    """``model_router`` reported success but produced no output file."""


class AuditParseError(AuditGateError):
    """Output present but does not match the expected ``decision: …`` shape."""


def audit_l4_op(
    *,
    op_type,
    target_slot,
    target_step_id,
    target_role_class,
    body_text,
    source_directive,
    task_id=None,
    model_router=None,
):
    """Dispatch an L4 op for DS audit; return ``AuditResult``.

    Raises an :class:`AuditGateError` subclass on any failure path; the
    sub-skill's prose treats every raise as a Gate 1 abort (per §7.4
    failure-modes table) and surfaces the diagnostic to the human.

    ``model_router`` is an optional injected reference to the
    ``model_router`` module (tests pass a stub). Default lazy-imports the
    real module.
    """
    if model_router is None:
        import model_router as _real_router  # noqa: WPS433
        model_router = _real_router

    if task_id is None:
        task_id = f"l4-audit-{target_role_class}-{op_type.split()[0]}"

    payload = {
        "op_type": op_type,
        "target_slot": target_slot,
        "target_step_id": target_step_id,
        "target_role_class": target_role_class,
        "body_text": body_text,
        "source_directive": source_directive,
    }

    _AUDIT_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"audit-{target_role_class}-",
                                     dir=str(_AUDIT_TMP_ROOT)) as td:
        td_path = Path(td)
        input_path = td_path / "op.json"
        output_path = td_path / "decision.md"
        input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        context = (
            f"Audit the classified L4 op for the `{target_role_class}` role-class. "
            f"Slot `{target_slot}`, op `{op_type}`. "
            f"Reject if the classification does not match the source directive."
        )

        try:
            exit_code = model_router.route(
                task_type="l4-audit",
                task_id=task_id,
                input_files=str(input_path),
                output_file=str(output_path),
                context=context,
            )
        except Exception as e:  # noqa: BLE001 — any router exception is a Gate 1 abort
            raise AuditModelRouterError(
                f"model_router.route raised on l4-audit task_id={task_id}: {e}"
            ) from e

        if exit_code == 3:
            raise AuditTimeoutError(
                f"model_router.route returned exit code 3 (timeout) for "
                f"l4-audit task_id={task_id}. Gate 1 abort per §7.4 failure-modes."
            )
        if exit_code != 0:
            raise AuditModelRouterError(
                f"model_router.route returned exit code {exit_code} for "
                f"l4-audit task_id={task_id}. Gate 1 abort per §7.4 failure-modes."
            )

        if not output_path.exists():
            raise AuditOutputMissingError(
                f"model_router.route produced no output file for "
                f"task_id={task_id}. Expected at {output_path}."
            )

        raw = output_path.read_text(encoding="utf-8")

    return _parse_audit_output(raw)


# `decision: <value>` line is THE branch signal. Tolerant of leading/trailing
# whitespace and case in the field name; the value MUST be exactly
# `approve` or `reject` per the template's contract.
_DECISION_RE = re.compile(r"^\s*decision\s*:\s*(\w+)\s*$", re.MULTILINE | re.IGNORECASE)
_FIELD_RE = re.compile(r"^\s*(\w[\w_]*)\s*:\s*(.*?)\s*$", re.MULTILINE)


def _parse_audit_output(text):
    """Parse the model's structured response into an :class:`AuditResult`.

    The template asks for line-anchored ``key: value`` fields. We extract
    every recognized field tolerantly; missing optional fields default
    to empty strings. The ``decision:`` field is mandatory and constrained
    to ``approve`` or ``reject`` (case-insensitive).
    """
    decision_match = _DECISION_RE.search(text)
    if not decision_match:
        raise AuditParseError(
            f"l4-audit response missing required `decision:` line. "
            f"Raw output: {text[:500]!r}"
        )
    decision = decision_match.group(1).strip().lower()
    if decision not in ("approve", "reject"):
        raise AuditParseError(
            f"l4-audit `decision:` field has invalid value {decision!r}. "
            f"Must be `approve` or `reject`."
        )

    fields = {m.group(1).lower(): m.group(2).strip() for m in _FIELD_RE.finditer(text)}

    return AuditResult(
        decision=decision,
        reason=fields.get("reason", ""),
        suggested_op_type=fields.get("suggested_op_type", ""),
        suggested_target_slot=fields.get("suggested_target_slot", ""),
        suggested_target_step_id=fields.get("suggested_target_step_id", ""),
    )
