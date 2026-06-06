"""L4 op processor — per-slot op application (#10489, PRD-A Story A2c).

Given a slot's L1-L3 source body and an ordered list of ``L4Op`` records
(from ``l4_parser.parse_l4_file``), produce the per-slot LINKED composite
by applying each op in source order.

Pure additive — no compose.py wiring this PR. A2f (#10492) wires this into
``deploy_alias_v2``.

Op semantics (TRD §3.3 + §4.2):

- ``append`` — appends ``op.body_text`` to the end of the slot.
- ``replace`` (whole-slot, no target) — replaces the entire slot body
  with ``op.body_text``. Per PRD-A §3.3 this is legal only on the
  Responsibility slot AND mutually exclusive with other ops in the same
  slot; A2c does NOT enforce either constraint (deferred to A2e).
- ``replace step:cycle/<id>`` — substitutes the targeted step's body
  verbatim. The step heading line is preserved; only the body between
  it and the next ``### step:cycle/...`` line (or slot end) is replaced.
- ``insert-before step:cycle/<id>`` — inserts ``op.body_text`` BEFORE
  the targeted ``### step:cycle/<id>`` heading line.
- ``insert-after step:cycle/<id>`` — inserts ``op.body_text`` AFTER
  the targeted step's body (i.e., before the next ``### step:cycle/...``
  heading or slot end).

If a step-targeted op names a step ID that isn't present in the current
slot content, ``L4OpTargetNotFound`` is raised — this is a hard error
because the L1-L3 source has diverged from the L4 file's expectations.
A2e is expected to validate target-step presence pre-application; A2c's
raise here is the runtime backstop.

Multi-op ordering: ops are applied sequentially in source order. Each op
sees the result of the previous op. This means an ``insert-after`` on a
step can land BETWEEN an earlier ``insert-after`` and the next step — by
design, source-order is the contract.
"""

import re


class L4OpTargetNotFound(KeyError):
    """Raised when a step-targeted op names a step_id not in slot content."""


# A step heading is ``### step:cycle/<id>`` (or H4/H5/H6 — see #11227)
# at line start, where <id> is the same alphanumeric+``_-`` grammar
# enforced by l4_parser._OP_RE. The heading consumes its trailing
# newline so slicing leaves the body clean.
#
# #11227 multi-level anchor support: L1 cycle steps live at H3 (top-level
# cycle anchors). L2 step extensions sit at H4 as sub-steps under their
# L1 parent. L3 extensions sit at H5 under L2. The op processor needs
# to find step IDs regardless of nesting depth, so the regex accepts
# H3-H6. The op DIRECTIVES (the ``### insert-after step:cycle/<id>``
# lines that get extracted by ``l4_parser`` / ``v2_link_stage``) are
# always H3 — that's the grammar contract; only the TARGET step heading
# that the op anchors to may live at any depth.
_STEP_HEADING_RE = re.compile(
    r"^#{3,6} step:cycle/([A-Za-z0-9_-]+)\s*$", re.MULTILINE
)


def apply_l4_ops(slot_content, l4_ops):
    """Apply ``l4_ops`` to ``slot_content`` in source order.

    Returns the resulting per-slot LINKED body as a string. Pure and
    deterministic — no I/O, no side effects.

    Pre-processing: C9 counter-op pairs (``replace step:cycle/X`` with
    the ``<!-- counter-op: ... -->`` sentinel body, paired with the
    most-recent prior ``replace step:cycle/X`` for the same step_id)
    are stripped before application so neither op fires. The L1-L3
    step body is preserved. See :func:`_strip_counter_op_pairs`.
    """
    content = slot_content
    for op in _strip_counter_op_pairs(l4_ops):
        op_type = op.op_type
        target = op.target_step_id
        body = op.body_text

        if op_type == "replace" and target is None:
            content = body
        elif op_type == "append":
            content = _apply_append(content, body)
        elif op_type == "replace":
            content = _apply_replace_step(content, target, body)
        elif op_type == "insert-before":
            content = _apply_insert_before_step(content, target, body)
        elif op_type == "insert-after":
            content = _apply_insert_after_step(content, target, body)
        else:
            # Defensive: l4_parser only produces the four legal op_types,
            # so this branch is unreachable from parsed input. Raising
            # here makes a future grammar-extension error loud rather
            # than silently dropping the op.
            raise ValueError(f"unknown L4 op_type: {op_type!r}")
    return content


def _apply_append(content, body):
    """Append ``body`` to end of slot with a blank-line paragraph break.

    Markdown requires two consecutive newlines for a paragraph break; a
    single newline collapses adjacent prose into one paragraph (#11144
    Finding 7). Normalize the join: strip trailing newlines from
    ``content`` and emit exactly one blank line before ``body``.
    """
    if not content:
        return body
    return content.rstrip("\n") + "\n\n" + body


def _find_step_region(content, step_id):
    """Locate ``### step:cycle/<step_id>`` and return slice indices.

    Returns ``(heading_start, body_start, body_end)`` where:
    - ``heading_start`` — index of the ``#`` that starts the heading line.
    - ``body_start`` — index just past the heading's trailing newline.
    - ``body_end`` — index of the next ``### step:cycle/...`` heading
      line OR the end of ``content`` if this is the last step.

    Raises ``L4OpTargetNotFound`` if no heading matching ``step_id`` is
    found in ``content``.
    """
    for m in _STEP_HEADING_RE.finditer(content):
        if m.group(1) == step_id:
            heading_start = m.start()
            # Body starts just past the heading line's newline. If the
            # heading is the last line and has no trailing newline,
            # m.end() already points past it.
            body_start = m.end()
            if body_start < len(content) and content[body_start] == "\n":
                body_start += 1
            # Body ends at the next step heading (any step_id) or end.
            next_m = _STEP_HEADING_RE.search(content, body_start)
            body_end = next_m.start() if next_m else len(content)
            return heading_start, body_start, body_end
    raise L4OpTargetNotFound(
        f"L4 op targets `step:cycle/{step_id}` but no such step heading "
        f"is present in slot content."
    )


def _apply_replace_step(content, step_id, new_body):
    """Replace the targeted step's body, preserving its heading line."""
    _, body_start, body_end = _find_step_region(content, step_id)
    return content[:body_start] + _ensure_trailing_newline(new_body) + content[body_end:]


# Matches a body whose only non-whitespace content is one or more
# ``<!-- counter-op: ... -->`` HTML-comment sentinels. Anchored on the
# ``counter-op:`` key so unrelated HTML comments do not register.
_COUNTER_OP_RE = re.compile(
    r"\A\s*(?:<!--\s*counter-op:[\s\S]*?-->\s*)+\Z"
)


def _is_counter_op_body(body):
    """True iff ``body`` is the C9 counter-op sentinel and nothing else.

    Used by :func:`_strip_counter_op_pairs` to identify ops that
    should be removed together with their matching prior op. A
    ``replace step:cycle/X`` whose body is genuinely empty (no
    sentinel) is left alone — it represents an operator intentionally
    blanking the step.
    """
    if not body or not body.strip():
        return False
    return _COUNTER_OP_RE.match(body) is not None


def _strip_counter_op_pairs(l4_ops):
    """Return ``l4_ops`` with C9 counter-op + prior-op pairs removed.

    A C9 counter-op is a ``replace step:cycle/X`` op whose body is the
    ``<!-- counter-op: ... -->`` sentinel. When the op processor sees
    one, it pairs it with the most-recent prior ``replace step:cycle/X``
    op targeting the same step_id and drops BOTH from the application
    sequence — the net effect is that neither the original nor the
    counter-op fires at compose time, so the underlying L1-L3 step
    body is what survives.

    If a counter-op has no matching prior op (the operator authored
    a counter-op against a step never customized in L4), the
    counter-op is silently dropped — it can't cancel something that
    isn't there, and falling through to the standard replace would
    blank a real L1-L3 step body via the empty-after-strip behavior.
    """
    keep = list(l4_ops)
    i = 0
    while i < len(keep):
        op = keep[i]
        if (op.op_type == "replace"
                and op.target_step_id is not None
                and _is_counter_op_body(op.body_text)):
            # Find most-recent prior op (in keep[0:i]) with op_type=replace
            # AND same target_step_id, then drop both.
            prior_idx = None
            for j in range(i - 1, -1, -1):
                prior = keep[j]
                if (prior.op_type == "replace"
                        and prior.target_step_id == op.target_step_id):
                    prior_idx = j
                    break
            if prior_idx is not None:
                del keep[i]
                del keep[prior_idx]
                # Continue from the position of the dropped prior op
                i = prior_idx
                continue
            # No prior to pair with — drop just the counter-op.
            del keep[i]
            continue
        i += 1
    return keep


def _apply_insert_before_step(content, step_id, body):
    """Insert ``body`` before the targeted step's heading line."""
    heading_start, _, _ = _find_step_region(content, step_id)
    return content[:heading_start] + _ensure_trailing_newline(body) + content[heading_start:]


def _apply_insert_after_step(content, step_id, body):
    """Insert ``body`` after the targeted step's body (before next step or slot end)."""
    _, _, body_end = _find_step_region(content, step_id)
    # body_end points at the next ``### step:cycle/...`` heading start
    # (or len(content)). Inserting right at body_end places the new
    # content between this step's body and the next step's heading.
    insertion = _ensure_trailing_newline(body)
    return content[:body_end] + insertion + content[body_end:]


def _ensure_trailing_newline(text):
    """Guarantee ``text`` ends with a newline so adjacent content stays on its own line."""
    if not text:
        return text
    if text.endswith("\n"):
        return text
    return text + "\n"
