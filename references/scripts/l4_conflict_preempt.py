"""C8: conflict pre-emption — checks proposed L4 op against the linked composite (#10657, PRD-C C8).

Per §7.1 + §4.6 pairing, before drafting an L4 op the agent reads the
LINKED composite for the target ``(slot, role-class)`` and runs a
conflict pre-emption check. If the new body would MATERIALLY
CONTRADICT existing L1-L3 prose, the agent surfaces both sides to the
human and offers reframe options (replace-reframe / abandon / reword)
instead of silently writing the conflicting op.

This module is the dispatch + result parser for that check. The check
is a model_router LLM call (task_type ``l4-conflict-preempt``); the
prompt template lives in ``references/prompts/l4-conflict-preempt.md.j2``.

Per AC2 the vocabulary ("materially contradicting prose between
layers") mirrors B4 (PRD-B #10445, ``conflict_detector.py``), so a
reader who knows B4's contract reads the same words here.

Per AC5(c) ``replace`` ops (whole-slot OR step-targeted) NEVER reach
the LLM — they supersede prior prose by construction. The dispatch
short-circuits to ``PreemptResult(decision="skip", ...)`` and the
caller proceeds to Gates 1-3 without burning an LLM call.

Aligns with C3 (l4_audit_gate.py) on failure-mode shape: every
unrecoverable path raises a typed :class:`ConflictPreemptError`
subclass; the upstream dialog renders a stage-specific human message
on each.
"""

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PREEMPT_TMP_ROOT = _REPO_ROOT / ".squidsquad" / "tmp" / "l4-conflict-preempt"


@dataclass
class PreemptResult:
    """Parsed result of one Gate-0 (pre-emption) dispatch.

    ``decision`` is one of:

    - ``"clean"`` — no material contradiction; advance to Gate 1.
    - ``"contradiction"`` — surface ``quote_new`` / ``quote_existing``
      + ``why`` + ``suggested_action`` to the human and re-walk the
      dialog with their reframe choice.
    - ``"skip"`` — ``op_type`` was a ``replace`` (whole-slot or
      step-targeted), so no LLM was dispatched. Caller proceeds to
      Gate 1 directly per AC5(c).

    The four detail fields are populated on the ``contradiction``
    decision and empty otherwise.
    """

    decision: str
    why: str = ""
    quote_new: str = ""
    quote_existing: str = ""
    suggested_action: str = ""

    @property
    def is_contradiction(self):
        return self.decision == "contradiction"

    @property
    def proceeds_to_gate_1(self):
        return self.decision in ("clean", "skip")


class ConflictPreemptError(RuntimeError):
    """Raised when the pre-emption dispatch cannot produce a decision.

    The upstream dialog treats every raise as a pre-emption abort: the
    write does NOT advance to Gate 1, the human is surfaced with the
    diagnostic, and they can retry the dialog (or skip pre-emption
    explicitly if they accept the residual risk that the assemble-pass
    will paper over a contradiction).

    Subclasses mirror :mod:`l4_audit_gate`'s shape so callers can
    render stage-specific human messages.
    """


class PreemptModelRouterError(ConflictPreemptError):
    """``model_router.route`` returned non-zero (config / API / etc.)."""


class PreemptTimeoutError(ConflictPreemptError):
    """``model_router.route`` returned exit code 3 (timeout)."""


class PreemptOutputMissingError(ConflictPreemptError):
    """``model_router`` reported success but produced no output file."""


class PreemptParseError(ConflictPreemptError):
    """Output present but does not match the expected ``decision: …`` shape."""


def preempt_conflict(
    *,
    op_type,
    target_slot,
    target_step_id,
    target_role_class,
    body_text,
    linked_composite,
    source_directive,
    task_id=None,
    model_router=None,
):
    """Run the conflict pre-emption check; return :class:`PreemptResult`.

    ``op_type`` follows the legal-grammar shapes (``append`` /
    ``replace`` / ``replace step:cycle/<id>`` / ``insert-before step:cycle/<id>``
    / ``insert-after step:cycle/<id>``). Any op whose first word is
    ``replace`` short-circuits to ``decision="skip"`` per AC5(c) — replace
    supersedes prior prose by construction so the linked-composite check
    is not needed.

    ``linked_composite`` is the existing LINKED-composite prose for
    ``(target_slot, target_role_class)`` with L1, L2, L3 (and any prior
    L4 entries) already merged. The check runs the new ``body_text``
    against this corpus.

    Raises a :class:`ConflictPreemptError` subclass on any failure
    path; the sub-skill's prose treats every raise as a pre-emption
    abort (human is surfaced with the diagnostic, the write does not
    advance to Gate 1).

    ``model_router`` is an optional injected reference to the
    ``model_router`` module (tests pass a stub). Default lazy-imports
    the real module.
    """
    if op_type and op_type.split()[0] == "replace":
        # AC5(c): replace ops supersede prior prose; no LLM dispatch.
        return PreemptResult(
            decision="skip",
            why=(
                f"`{op_type}` supersedes prior prose at compose time; "
                f"conflict pre-emption is not needed for replace ops."
            ),
        )

    if model_router is None:
        import model_router as _real_router  # noqa: WPS433
        model_router = _real_router

    if task_id is None:
        task_id = f"l4-conflict-preempt-{target_role_class}-{op_type.split()[0]}"

    payload = {
        "op_type": op_type,
        "target_slot": target_slot,
        "target_step_id": target_step_id,
        "target_role_class": target_role_class,
        "body_text": body_text,
        "source_directive": source_directive,
        "linked_composite": linked_composite,
    }

    _PREEMPT_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"preempt-{target_role_class}-",
                                     dir=str(_PREEMPT_TMP_ROOT)) as td:
        td_path = Path(td)
        input_path = td_path / "op.json"
        output_path = td_path / "decision.md"
        input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        context = (
            f"Pre-emption check for proposed L4 op on `{target_role_class}` "
            f"role-class, slot `{target_slot}`, op `{op_type}`. Decide whether "
            f"the proposed body materially contradicts existing prose in the "
            f"linked composite."
        )

        try:
            exit_code = model_router.route(
                task_type="l4-conflict-preempt",
                task_id=task_id,
                input_files=str(input_path),
                output_file=str(output_path),
                context=context,
            )
        except Exception as e:  # noqa: BLE001
            raise PreemptModelRouterError(
                f"model_router.route raised on l4-conflict-preempt task_id={task_id}: {e}"
            ) from e

        if exit_code == 3:
            raise PreemptTimeoutError(
                f"model_router.route returned exit code 3 (timeout) for "
                f"l4-conflict-preempt task_id={task_id}. Pre-emption abort."
            )
        if exit_code != 0:
            raise PreemptModelRouterError(
                f"model_router.route returned exit code {exit_code} for "
                f"l4-conflict-preempt task_id={task_id}. Pre-emption abort."
            )

        if not output_path.exists():
            raise PreemptOutputMissingError(
                f"model_router.route produced no output file for "
                f"task_id={task_id}. Expected at {output_path}."
            )

        raw = output_path.read_text(encoding="utf-8")

    return _parse_preempt_output(raw)


# The `decision:` line is the branch signal. Tolerant of leading /
# trailing whitespace and case in the field name; the value MUST be
# exactly `clean` or `contradiction` per the template's contract.
_DECISION_RE = re.compile(r"^\s*decision\s*:\s*(\w+)\s*$", re.MULTILINE | re.IGNORECASE)
_FIELD_RE = re.compile(r"^\s*([\w_]+)\s*:\s*(.*?)\s*$", re.MULTILINE)


def _parse_preempt_output(text):
    """Parse the model's structured response into a :class:`PreemptResult`.

    The template asks for line-anchored ``key: value`` fields. Missing
    optional fields default to empty strings; the mandatory ``decision:``
    field must be exactly ``clean`` or ``contradiction`` (case-insensitive).
    Any other value or a missing field raises :class:`PreemptParseError`.
    """
    decision_match = _DECISION_RE.search(text)
    if not decision_match:
        raise PreemptParseError(
            f"l4-conflict-preempt response missing required `decision:` line. "
            f"Raw output: {text[:500]!r}"
        )
    decision = decision_match.group(1).strip().lower()
    if decision not in ("clean", "contradiction"):
        raise PreemptParseError(
            f"l4-conflict-preempt `decision:` field has invalid value "
            f"{decision!r}. Must be `clean` or `contradiction`."
        )

    fields = {m.group(1).lower(): m.group(2).strip() for m in _FIELD_RE.finditer(text)}

    return PreemptResult(
        decision=decision,
        why=fields.get("why", ""),
        quote_new=fields.get("quote_new", ""),
        quote_existing=fields.get("quote_existing", ""),
        suggested_action=fields.get("suggested_action", ""),
    )


def format_contradiction_for_human(result):
    """Render a contradiction-decision result as human-facing prose.

    Per AC3, the agent surfaces quotes from both sides + reframe
    options. This helper produces that block; the upstream dialog
    intersperses it with the per-instance plain-language framing.

    Returns ``""`` for non-contradiction results — the dialog has
    nothing to surface on ``clean`` / ``skip``.
    """
    if result.decision != "contradiction":
        return ""
    parts = [
        "The proposed rule would conflict with how this role is already configured:",
        "",
        f"**What you're asking to add:**",
        f"> {result.quote_new}" if result.quote_new else "> (no quote provided)",
        "",
        f"**What the role already does:**",
        f"> {result.quote_existing}" if result.quote_existing else "> (no quote provided)",
        "",
    ]
    if result.why:
        parts.append(f"Why this matters: {result.why}")
        parts.append("")
    if result.suggested_action:
        parts.append(
            "Options:\n"
            + _format_action_options(result.suggested_action)
        )
    return "\n".join(parts)


def _format_action_options(suggested_action):
    """Translate the LLM's suggested-action token into human-facing options.

    The model emits one of ``replace-reframe`` / ``abandon`` /
    ``reword``; we render all three options every time but highlight
    the model's recommendation so the human knows the preferred path.
    The user-facing rule (per l4-curation.md "Talking to the user")
    forbids naming op shapes, slots, or other SquidSquad internals —
    these strings are deliberately worded in role-behavior terms.
    """
    options = {
        "replace-reframe": "  - Replace the existing behavior wholesale with the new rule (recommended)",
        "reword": "  - Rephrase the new rule so it adds to the existing behavior without overriding (recommended)",
        "abandon": "  - Drop the new rule — the existing behavior already covers this (recommended)",
    }
    primary = options.get(suggested_action, "")
    others = [v for k, v in options.items() if k != suggested_action]
    # Strip the "(recommended)" tag from the non-primary entries
    others = [o.replace(" (recommended)", "") for o in others]
    return "\n".join([primary] + others) if primary else "\n".join(o.replace(" (recommended)", "") for o in options.values())
