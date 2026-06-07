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
#
# #11144 indexed step headings: agents read better with numbered step
# headings ("### Step 1 — step:cycle/boot"). The regex accepts an
# optional indexing prefix BEFORE the step ID — either ``Step N(.M)? — ``
# (em-dash, en-dash, or hyphen separator; the optional ``.M`` is the
# hierarchical sub-step ordinal applied by ``_apply_hierarchical_step_numbering``
# to L2/L3 sub-steps nested under an L1 parent step) or ``N(.M)?. ``. Op
# directives (``insert-after``, ``insert-before``, ``replace`` keywords)
# do not match this prefix grammar so there's no collision; the
# ``_INLINE_OP_DIRECTIVE_RE`` in v2_link_stage still uniquely identifies
# them.
_STEP_HEADING_RE = re.compile(
    r"^#{3,6}\s+"
    r"(?:Step\s+\d+(?:\.\d+)?\s*[—–-]\s+|\d+(?:\.\d+)?\.\s+)?"
    r"step:cycle/([A-Za-z0-9_-]+)\s*$",
    re.MULTILINE,
)

# Match an L1 parent step heading (H3, `Step N — step:cycle/<id>`) and
# capture the parent ordinal. Used by ``_apply_hierarchical_step_numbering``
# to find the boundaries of each parent's sub-step block. The trailing
# bound is ``[ \t]*$`` (horizontal whitespace only) — using ``\s`` would
# also match the line's terminating ``\n`` and let greedy matching
# swallow line boundaries, which would corrupt the surrounding content
# when we rewrite the heading in place.
_L1_PARENT_STEP_RE = re.compile(
    r"^###[ \t]+Step[ \t]+(\d+)[ \t]*[—–-][ \t]+step:cycle/([A-Za-z0-9_-]+)[ \t]*$",
    re.MULTILINE,
)

# Match an H4 sub-step heading with or without an existing index prefix.
# Same horizontal-whitespace discipline as above so the trailing newline
# stays outside the match (``m.end()`` lands at the newline position and
# the in-place rewrite preserves the line boundary).
_L2_SUBSTEP_HEADING_RE = re.compile(
    r"^####[ \t]+"
    r"(?:Step[ \t]+\d+(?:\.\d+)?[ \t]*[—–-][ \t]+|\d+(?:\.\d+)?\.[ \t]+)?"
    r"step:cycle/([A-Za-z0-9_-]+)[ \t]*$",
    re.MULTILINE,
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
    # Post-process: renumber L2/L3 sub-step headings hierarchically under
    # their L1 parent step. Runs AFTER all ops are applied so the final
    # sub-step ordering (including L4 customizations) drives the numbers.
    content = _apply_hierarchical_step_numbering(content)
    # Render the hydrated cycle diagram from the (now-numbered) step
    # hierarchy. The agent only ever sees ONE cycle diagram — the
    # generated one — so the L1 source can't carry a stale hand-authored
    # variant alongside it.
    content = _render_hydrated_cycle_diagram(content)
    return content


def _apply_hierarchical_step_numbering(content):
    """Renumber H4 step:cycle sub-step headings as ``Step <parent_N>.<M>``
    based on their position under each L1 parent step.

    Walks the slot content, finds each ``### Step N — step:cycle/<id>`` L1
    parent heading, and for the H4 step:cycle sub-step headings between
    it and the next L1 parent (or slot end), rewrites them as
    ``#### Step N.M — step:cycle/<sub-id>`` where M is the 1-based
    insertion-order position of the sub-step under that parent.

    Idempotent: an existing ``Step N.M — `` (or any other prefix) on the
    sub-step heading is stripped and replaced with the recomputed form.
    The author's hand-numbering — if any — is overwritten, so L2/L3 ops
    can reorder freely without manual renumber.

    No-op if there are no L1 parent step headings (e.g. on slots that
    aren't instructions, or instructions slots where L1 hasn't been
    numbered yet).
    """
    parents = [
        (m.start(), m.end(), int(m.group(1)), m.group(2))
        for m in _L1_PARENT_STEP_RE.finditer(content)
    ]
    if not parents:
        return content

    # Walk parents in REVERSE order so earlier indices remain valid as
    # we rewrite later parts of the content.
    result = content
    for i in range(len(parents) - 1, -1, -1):
        _, parent_end, parent_n, _ = parents[i]
        if i + 1 < len(parents):
            range_end = parents[i + 1][0]
        else:
            range_end = len(result)
        section = result[parent_end:range_end]
        substeps = list(_L2_SUBSTEP_HEADING_RE.finditer(section))
        if not substeps:
            continue
        # Rewrite sub-step headings in REVERSE order within the section
        # so earlier match offsets stay valid.
        new_section = section
        for m_idx in range(len(substeps) - 1, -1, -1):
            m = substeps[m_idx]
            sub_id = m.group(1)
            new_heading = f"#### Step {parent_n}.{m_idx + 1} — step:cycle/{sub_id}"
            new_section = new_section[: m.start()] + new_heading + new_section[m.end() :]
        result = result[:parent_end] + new_section + result[range_end:]
    return result


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
    """Insert ``body`` before the targeted step's heading line.

    Uses ``_ensure_paragraph_break`` (two trailing newlines) for the same
    reason ``_apply_insert_after_step`` does: markdown needs a blank line
    between a paragraph and the heading that follows it; a single ``\\n``
    visually crams the inserted body's final paragraph into the next
    heading line (#11144 Finding 7 — same fix here).
    """
    heading_start, _, _ = _find_step_region(content, step_id)
    return content[:heading_start] + _ensure_paragraph_break(body) + content[heading_start:]


def _apply_insert_after_step(content, step_id, body):
    """Insert ``body`` after the targeted step's body (before next step or slot end)."""
    _, _, body_end = _find_step_region(content, step_id)
    # body_end points at the next ``### step:cycle/...`` heading start
    # (or len(content)). Inserting right at body_end places the new
    # content between this step's body and the next step's heading.
    # We need TWO trailing newlines so there's a blank line between the
    # inserted body's last paragraph and the next step heading —
    # markdown collapses single-newline-separated lines into one
    # paragraph, which produced a visually-crammed cycle in composed
    # output (#11144: "...vault posture notes.### step:cycle/exit").
    insertion = _ensure_paragraph_break(body)
    return content[:body_end] + insertion + content[body_end:]


def _ensure_trailing_newline(text):
    """Guarantee ``text`` ends with a newline so adjacent content stays on its own line."""
    if not text:
        return text
    if text.endswith("\n"):
        return text
    return text + "\n"


# Marker the L1 source carries in place of a hand-authored cycle diagram.
# Compose replaces it with a generated mermaid flowchart whose contents
# reflect the actual hydrated step hierarchy (L1 parents + their L2/L3
# sub-steps in insertion order).
_HYDRATED_DIAGRAM_MARKER = "<!-- compose:hydrated-cycle-diagram -->"

# Boot-phase parent step IDs land in the SessionBoot subgraph; everything
# else lands in the WalkLoop subgraph. Per L1: boot + resume run ONCE at
# session start; pickup → work → checkpoint → cleanup → exit run per
# cared event during the nudge walk.
_SESSION_BOOT_STEP_IDS = ("boot", "resume")


def _render_hydrated_cycle_diagram(content):
    """Replace ``_HYDRATED_DIAGRAM_MARKER`` with a generated mermaid
    flowchart of the actual step hierarchy in ``content``.

    Walks the (already-numbered) step headings and emits one node per
    parent step and one per sub-step, edges linking them in document
    order. Parents whose ID is in ``_SESSION_BOOT_STEP_IDS`` go into the
    SessionBoot subgraph; the rest go into WalkLoop.

    No-op if the marker isn't present (e.g. on slots that aren't the
    instructions slot, or on legacy L1 source that still carries a
    hand-authored diagram).
    """
    if _HYDRATED_DIAGRAM_MARKER not in content:
        return content

    parents = [
        (m.end(), int(m.group(1)), m.group(2))
        for m in _L1_PARENT_STEP_RE.finditer(content)
    ]
    if not parents:
        # Marker present but no parents found — leave the marker so the
        # composed output makes the gap visible rather than silently
        # emitting an empty diagram.
        return content

    # Build the (parent, [sub_id...]) list in document order.
    hierarchy = []
    for i, (parent_end, parent_n, parent_id) in enumerate(parents):
        range_end = parents[i + 1][0] if i + 1 < len(parents) else len(content)
        # _L1_PARENT_STEP_RE.match yields parent_end at end of line; need
        # to slice from there to next parent's start for the sub-step
        # scan. The next parent's start is one char before its end (the
        # start of its `###`), but we already have parent_end of THIS
        # parent — sub-steps live between this parent and the next.
        section_start = parent_end
        # Recover the next-parent start position to bound the scan.
        if i + 1 < len(parents):
            # parent[i+1][0] is end-of-line of next parent heading; back
            # off to the start of that heading line by re-searching.
            section_end_match = _L1_PARENT_STEP_RE.search(
                content, section_start
            )
            section_end = section_end_match.start() if section_end_match else len(content)
        else:
            section_end = len(content)
        section = content[section_start:section_end]
        sub_ids = [m.group(1) for m in _L2_SUBSTEP_HEADING_RE.finditer(section)]
        hierarchy.append((parent_n, parent_id, sub_ids))

    diagram = _emit_mermaid_flowchart(hierarchy)
    return content.replace(_HYDRATED_DIAGRAM_MARKER, diagram, 1)


def _emit_mermaid_flowchart(hierarchy):
    """Render a mermaid flowchart string from a ``[(parent_n, parent_id, sub_ids)]`` list.

    Edges connect each node to its successor in document order so the
    rendered diagram reads as a single linear cycle. Sub-graph membership
    is driven by ``_SESSION_BOOT_STEP_IDS`` — boot-phase parents and
    their sub-steps live in the SessionBoot subgraph; the rest live in
    WalkLoop.
    """
    boot_nodes = []
    walk_nodes = []
    all_nodes = []  # (node_id, label, is_boot) — flat order for edge chain

    for parent_n, parent_id, sub_ids in hierarchy:
        is_boot = parent_id in _SESSION_BOOT_STEP_IDS
        node_id = f"S{parent_n}"
        label = f"{parent_n}. step:cycle/{parent_id}"
        all_nodes.append((node_id, label, is_boot))
        (boot_nodes if is_boot else walk_nodes).append((node_id, label))
        for sub_idx, sub_id in enumerate(sub_ids, start=1):
            sub_node_id = f"S{parent_n}_{sub_idx}"
            sub_label = f"{parent_n}.{sub_idx} {sub_id}"
            all_nodes.append((sub_node_id, sub_label, is_boot))
            (boot_nodes if is_boot else walk_nodes).append((sub_node_id, sub_label))

    def _render_subgraph(name, title, nodes):
        if not nodes:
            return ""
        lines = [f'    subgraph {name}["{title}"]']
        for node_id, label in nodes:
            lines.append(f'        {node_id}["{label}"]')
        lines.append("    end")
        return "\n".join(lines)

    parts = ["```mermaid", "flowchart LR"]
    boot_block = _render_subgraph(
        "SessionBoot", "Session boot (once per session)", boot_nodes
    )
    walk_block = _render_subgraph(
        "WalkLoop", "Per cared event (repeats per nudge)", walk_nodes
    )
    if boot_block:
        parts.append(boot_block)
    if walk_block:
        parts.append(walk_block)

    # Edges: connect each node to its successor across the full sequence,
    # then bridge SessionBoot → WalkLoop at the transition point.
    last_boot_node = None
    first_walk_node = None
    for i in range(len(all_nodes) - 1):
        cur_id, _, cur_is_boot = all_nodes[i]
        next_id, _, next_is_boot = all_nodes[i + 1]
        if cur_is_boot and not next_is_boot:
            # Boundary handled by the subgraph-level edge below.
            last_boot_node = cur_id
            first_walk_node = next_id
            continue
        parts.append(f"    {cur_id} --> {next_id}")

    if boot_block and walk_block:
        parts.append("    SessionBoot --> WalkLoop")

    parts.append("```")
    return "\n".join(parts)


def _ensure_paragraph_break(text):
    """Guarantee ``text`` ends with exactly two newlines (a markdown paragraph break).

    Used by `_apply_insert_after_step` so the inserted body has a blank
    line between its last paragraph and whatever heading follows in the
    surviving content. Idempotent — a body that already ends with two
    or more newlines is normalized to exactly two.
    """
    if not text:
        return text
    return text.rstrip("\n") + "\n\n"
