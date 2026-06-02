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
    # #10753 W3 / DS-10753 review additions. The W3 relaxation
    # (approval-prefix + suffix match) needs these in the rejection
    # set so an approval head like "go" / "y" / "ok" doesn't promote
    # a dismissal or questioning reply to approve.
    #
    # - "away"/"back": dismissals ("go away" / "go back" mean stop or
    #   undo, not proceed).
    # - "not": standalone "not" after an approval prefix is
    #   overwhelmingly a negation in mini-CQ context ("y not" = "why
    #   not?" = questioning, "do it not" = negation).
    # - "never": same shape as "not" but uses "never mind" multi-word
    #   token already; add the single-word form for consistency.
    "away", "back", "not", "never",
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


def _has_rejection_in_rest(parts):
    """True iff any single-word OR contiguous two-word slice of
    ``parts[1:]`` is in ``_REJECTION_TOKENS``."""
    rest_tokens = set(parts[1:])
    if rest_tokens & _REJECTION_TOKENS:
        return True
    return any(
        rt in _REJECTION_TOKENS for rt in
        [" ".join(parts[i:i + 2]) for i in range(1, len(parts) - 1)]
    )


def _starts_with_approval_prefix(parts):
    """True iff ``parts`` begins with an ``_APPROVAL_TOKENS`` entry.

    Covers the "approval head + politeness/intensifier suffix" case
    the audit flagged (#10753 W3) — e.g. ``"do it now"`` (matches
    ``"do it"`` prefix + intensifier ``"now"``), ``"ship it please"``
    (``"ship it"`` + politeness ``"please"``), ``"y please"`` (``"y"``
    + politeness). The single-word-head allowlist on the previous
    implementation rejected all three despite each being a clear
    approval, hurting Gate 2 throughput.

    Per DS-10753 review F3: ``cleaned`` parameter dropped — only
    ``parts`` is read; the prior signature was misleading.
    """
    n = len(parts)
    # Check 1-word through 4-word prefixes of the reply against the
    # approval set so 3-word approvals like ``"go for it"`` and
    # 4-word ``"looks good to me"`` are also covered.
    for prefix_len in range(min(n, 4), 0, -1):
        prefix = " ".join(parts[:prefix_len])
        if prefix in _APPROVAL_TOKENS:
            return True
    return False


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

    Approval matches whichever is widest:

    1. ``cleaned`` is exactly an approval token (``"yes"`` / ``"do it"``).
    2. ``cleaned`` STARTS WITH an approval token (1-4 word prefix) and
       the remainder contains no rejection token. Covers
       ``"do it now"`` / ``"ship it please"`` / ``"y please"`` —
       #10753 W3 regression.

    The classifier stays CONSERVATIVE: any negation in the rest of the
    reply (whether as a single token or a two-word slice) demotes the
    match to ``"ambiguous"``. False approvals are worse than a
    re-prompt because they commit an L4 write the human didn't intend.
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

    # Exact match against the full cleaned reply (handles multi-word
    # approvals like "do it" / "looks good"). Single-word approvals
    # like "yes" also match because the cleaned reply equals the token.
    # We do NOT do substring matching against the token set because
    # that would treat "no thanks" as a rejection AND "yes I'd like
    # to but" as an approval — both wrong.
    if cleaned in _APPROVAL_TOKENS:
        return "approve"
    if cleaned in _REJECTION_TOKENS:
        return "reject"

    parts = cleaned.split()
    if not parts:
        return "ambiguous"

    # #10753 W3: approval prefix + suffix. ``"do it now"`` /
    # ``"ship it please"`` / ``"y please"`` all match here when the
    # rest contains no negation. The narrow head-only allowlist the
    # previous implementation used incorrectly rejected these as
    # ambiguous, hurting Gate 2 throughput on the very interaction
    # it's supposed to validate.
    if _starts_with_approval_prefix(parts) and not _has_rejection_in_rest(parts):
        return "approve"

    # Rejection head check stays narrow — it only fires for the
    # explicit one-word negatives so we don't surface a "stop me if I'm
    # wrong" or "wait, do it" as a rejection.
    head = parts[0]
    if head in _REJECTION_TOKENS and head in (
        "no", "cancel", "abort", "stop", "nope", "nah", "wait",
    ):
        return "reject"

    return "ambiguous"
