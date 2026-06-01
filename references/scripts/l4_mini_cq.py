"""Gate 2: mini-CQ confirmation parser + formatter (#10653, PRD-C C4).

After Gate 1 (DS audit) approves, the agent formats a one-line
confirmation message back to the human and waits for a positive reply
before triggering Gate 3 (compose dry-run) + commit. This module owns
both halves:

- :func:`format_confirmation` produces the canonical message shape per
  the C4 AC1 spec.
- :func:`classify_reply` parses the human's free-text response into
  one of three buckets: ``"approve"`` (positive), ``"reject"``
  (negative), or ``"ambiguous"`` (re-prompt).

The 2-strike ambiguous-response rule (re-ask once, then abandon on a
second ambiguous reply) lives in the ``l4-curation`` sub-skill prose,
not here -- this module is a stateless parser/formatter so callers
keep the conversation loop.
"""

import re
from typing import Literal


# Approval words / phrases. Case-insensitive, leading/trailing whitespace
# tolerant, punctuation tolerant. Order matters only for tests that
# enumerate expected matches.
_APPROVAL_TOKENS = frozenset({
    "yes", "y",
    "approved", "approve",
    "go", "do it", "do that", "go ahead", "go for it",
    "ok", "okay", "k",
    "confirm", "confirmed",
    "sure", "sure thing",
    "yep", "yeah", "yup",
    "lgtm", "looks good", "looks good to me",
    "ship it", "ship",
})

# Negative / cancellation words. Same tolerance rules.
_REJECTION_TOKENS = frozenset({
    "no", "n",
    "nope", "nah",
    "cancel", "abort", "stop",
    "never mind", "nevermind",
    "don't", "do not",
    "wait",
})


# Reply classification result. Using Literal so type-checkers catch
# stringly-typed branch comparisons that aren't one of the three values.
Decision = Literal["approve", "reject", "ambiguous"]


def format_confirmation(op_type, target, slot, role_class):
    """Produce the canonical mini-CQ confirmation message.

    Per C4 AC1 the message is:
    ``Adding ``<op-type> <target>`` under ``<slot>`` of ``<role-class>`` — OK?``

    The double-backticks render as inline code in markdown when surfaced
    in chat-style channels. The em-dash before ``OK?`` keeps the message
    consistent with the §7.4 example wording.

    ``target`` may be empty for ``append`` and whole-slot ``replace`` ops
    that have no step anchor — the formatter handles that case by
    rendering ``op-type`` alone (no trailing space-and-target).
    """
    op_type = (op_type or "").strip()
    target = (target or "").strip()
    slot = (slot or "").strip()
    role_class = (role_class or "").strip()
    if target:
        op_phrase = f"{op_type} {target}"
    else:
        op_phrase = op_type
    return f"Adding `{op_phrase}` under `{slot}` of `{role_class}` — OK?"


def classify_reply(reply):
    """Classify a free-text reply as approve / reject / ambiguous.

    Recognition rules:

    - ``"yes"`` / ``"approved"`` / ``"go"`` / ``"ok"`` / ``"confirm"`` /
      ``"do it"`` and other clear-approval synonyms (case-insensitive,
      whitespace + punctuation tolerant) → ``"approve"``.
    - ``"no"`` / ``"cancel"`` / ``"abort"`` / ``"stop"`` and similar
      negatives → ``"reject"``.
    - Anything else (empty string, mixed signal, follow-up question,
      partial sentence, the human asking for clarification, etc.) →
      ``"ambiguous"``. The caller's 2-strike rule decides whether to
      re-prompt or abandon.

    The classifier is intentionally CONSERVATIVE — when in doubt, return
    ``"ambiguous"`` rather than approve. False approvals are worse than
    a re-prompt because they commit an L4 write the human didn't actually
    intend.
    """
    if reply is None:
        return "ambiguous"
    # Lowercase + strip outer whitespace + strip trailing punctuation
    # commonly attached to one-word replies ("yes!", "ok.", "no?").
    cleaned = reply.strip().lower()
    cleaned = re.sub(r"[\s\.\!\?,;:]+$", "", cleaned)
    cleaned = re.sub(r"^[\s\.\!\?,;:]+", "", cleaned)
    if not cleaned:
        return "ambiguous"

    # Approval / rejection match against the full cleaned reply (handles
    # multi-word approvals like "do it" / "looks good"). Single-word
    # approvals like "yes" also match because the cleaned reply equals
    # the token. We do NOT do substring matching against the token set
    # because that would treat "no thanks" as a rejection AND "yes I'd
    # like to but" as an approval — both wrong.
    if cleaned in _APPROVAL_TOKENS:
        return "approve"
    if cleaned in _REJECTION_TOKENS:
        return "reject"

    # Multi-word approvals: the first whitespace-delimited token must be
    # an unambiguous approval head AND no rejection token can appear
    # anywhere in the remainder. "yes please" approves; "yes but no"
    # surfaces the conflict and falls through to ambiguous.
    parts = cleaned.split()
    head = parts[0] if parts else ""
    rest_tokens = set(parts[1:])

    has_negation_in_rest = bool(rest_tokens & _REJECTION_TOKENS) or any(
        rt in _REJECTION_TOKENS for rt in
        [" ".join(parts[i:i + 2]) for i in range(1, len(parts) - 1)]
    )

    if head in _APPROVAL_TOKENS and head in ("yes", "ok", "okay", "go", "sure",
                                              "yep", "yeah", "approve",
                                              "approved", "confirm",
                                              "confirmed", "lgtm"):
        if not has_negation_in_rest:
            return "approve"
        # Mixed signal — fall through to ambiguous.
    if head in _REJECTION_TOKENS and head in ("no", "cancel", "abort", "stop",
                                               "nope", "nah", "wait"):
        return "reject"

    return "ambiguous"
