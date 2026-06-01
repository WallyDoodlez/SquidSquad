"""C9: L4 removal flow — counter-op (default) or in-place delete (with explicit confirmation).

When the human says "undo the incidents-check thing" or "forget that
weekly security smoke rule", this module:

  1. detects the removal-shaped request (``is_removal_request``);
  2. finds the targeted existing L4 entry by token-overlap scoring
     against the directive (``find_target_entry``);
  3. surfaces a human-readable preview of the entry that's about to be
     touched (``format_target_preview``);
  4. picks one of two paths via ``plan_removal``:

       - **counter-op** (default): generates a new H3 op text that
         cancels the prior behavior. For step-targeted ops, that is
         ``### replace step:cycle/<id>`` with an empty body — when the
         compose pipeline replays the L4 ops in order, the no-op
         replacement wipes the earlier targeted op's effect while the
         underlying L1-L3 step's behavior remains. Additive history:
         the prior H3 block stays in the file, git blame still shows
         the original directive.
       - **in-place delete** (requires explicit human confirmation):
         excises the targeted H3 block from the L4 file in place. The
         git commit shows the deletion in the diff. No history rewrite
         — additive in git terms, even though the file lost content.

  5. composes the resulting ``RemovalPlan`` that the caller hands to
     gates 1-3 (l4_audit_gate → l4_mini_cq → l4_compose_dryrun) and
     then to C6 (l4_write_commit) just like a normal customization.

The planner NEVER raises — every failure mode lands in
``RemovalPlan.path_chosen`` so the caller branches on the data:
``not-found`` / ``ambiguous`` / ``no-counter-op-possible`` /
``counter-op`` / ``in-place-delete``.

Per the §7.5 / §7.7 removal contract (l4-curation 'What this sub-skill
does NOT do'): silent autonomous deletion is forbidden. The detection
+ targeting + preview + confirmation dialog is mandatory; this module
just produces the staged text — the upstream dialog runs in the
calling sub-skill's prose.
"""

import re
from dataclasses import dataclass
from typing import Literal

import l4_parser


# Removal-verb detection — sentence-anchored to avoid false matches on
# "I would never forget X" (a non-removal directive that mentions
# "forget"). Matches at the start of the directive OR right after a
# clause break (./?/!/;) or "let's" / "let us" prefix. Words are listed
# broadly because operators phrase removals many ways: ``undo`` /
# ``remove`` / ``drop`` / ``delete`` / ``kill`` / ``scrap`` / ``ditch`` /
# ``rip out`` are the explicit verbs; ``forget`` is the colloquial
# pattern; ``cancel`` / ``revert`` / ``back out`` cover "we don't need
# that anymore"; ``stop doing`` / ``no longer`` / ``get rid of`` are
# idiom variants.
_REMOVAL_RE = re.compile(
    r"(?:^|[.;!?]\s+|let[''']?s\s+|let\s+us\s+)"
    r"(?:please\s+)?"
    r"(?:undo|remove|drop|delete|forget|cancel|revert|kill|scrap|ditch"
    r"|rip\s+out|back\s+out|get\s+rid\s+of|stop\s+doing|stop\s+\w+ing"
    r"|no\s+longer|we\s+don'?t\s+need)"
    r"\b",
    re.IGNORECASE,
)

# Tokens we always strip from a directive before content-scoring, so
# "forget the weekly security smoke rule" matches an L4 op whose body
# mentions "weekly security smoke" without being misled by "forget" /
# "the" / "rule".
_REMOVAL_STEM_RE = re.compile(
    r"\b(?:please|undo|remove|drop|delete|forget|cancel|revert|stop|doing"
    r"|no|longer|we|don'?t|need|the|that|those|this|these|rule|thing|"
    r"entry|op|customization|directive|behavior|behaviour|policy|step|"
    r"about|for|of|on|to|and|or|a|an|in|at|by|all|any)\b",
    re.IGNORECASE,
)

# Stop-words filtered out of the target's body when computing content
# tokens for the overlap score. The same set is used on both sides of
# the comparison so the score reflects topic overlap, not boilerplate.
_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "of", "in",
    "on", "at", "by", "for", "to", "from", "with", "without", "is", "are",
    "was", "were", "be", "been", "being", "do", "does", "did", "have", "has",
    "had", "this", "that", "these", "those", "it", "its", "as", "so", "not",
    "no", "yes", "any", "all", "some", "each", "every", "into", "out", "up",
    "down", "than", "such", "when", "where", "why", "how", "what", "which",
    "who", "whom", "whose", "before", "after", "during", "while", "between",
    "step", "cycle", "via", "run", "running", "use", "using", "used",
    "should", "shall", "must", "may", "might", "would", "could", "can",
    "rule", "entry", "thing", "policy", "directive", "customization",
})

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")

# Strong-confidence threshold for ``find_target_entry``: the best-match
# entry must overlap on at least this many distinct content tokens with
# the directive to count as a confident hit. Below this we return the
# top candidates as ambiguous (so the caller asks the human).
_MIN_OVERLAP = 2

# Margin the top candidate must beat the runner-up by. Below this margin
# we treat the result as ambiguous and let the caller surface candidates.
_AMBIGUITY_MARGIN = 1


@dataclass
class TargetEntry:
    """The L4 H3 op block targeted for removal."""
    slot: str
    op_index: int
    op: "l4_parser.L4Op"
    overlap_score: int = 0
    commit_sha: str | None = None
    authored_by: str | None = None


PathChoice = Literal[
    "counter-op",
    "in-place-delete",
    "ambiguous",
    "not-found",
    "no-counter-op-possible",
    "not-a-removal-request",
]


@dataclass
class RemovalPlan:
    """Outcome of one ``plan_removal`` invocation.

    Callers branch on ``path_chosen`` to decide whether to dispatch the
    staged content into gates 1-3 + C6 (the happy paths
    ``counter-op`` / ``in-place-delete``), to ask the human to
    disambiguate (``ambiguous``), or to back off (``not-found`` /
    ``no-counter-op-possible`` / ``not-a-removal-request``).
    """
    path_chosen: PathChoice
    target: TargetEntry | None = None
    counter_op_text: str | None = None
    new_l4_text: str | None = None
    diagnostic: str = ""
    candidates: list[TargetEntry] | None = None
    requires_explicit_confirmation: bool = False


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def is_removal_request(directive):
    """Return True when ``directive`` reads as a removal-shaped request.

    Matches removal verbs (undo / remove / drop / delete / forget /
    cancel / revert / stop doing / no longer / we don't need) at the
    start of the directive or after a clause break. False on
    "I would never forget the X rule" — the word ``forget`` is not at
    a clause boundary so the removal pattern doesn't fire.
    """
    if not directive or not isinstance(directive, str):
        return False
    return _REMOVAL_RE.search(directive) is not None


# ---------------------------------------------------------------------------
# Targeting
# ---------------------------------------------------------------------------


def _content_tokens(text):
    if not text:
        return set()
    raw = _TOKEN_RE.findall(text.lower())
    return {t for t in raw if t not in _STOP_WORDS and len(t) > 2}


def _directive_content_tokens(directive):
    """Strip removal stems first, then return content tokens.

    "forget the weekly security smoke rule" → {"weekly", "security",
    "smoke"} (the removal stem ``forget`` + ``the`` + ``rule`` are
    pruned by ``_REMOVAL_STEM_RE`` before tokenization).
    """
    stripped = _REMOVAL_STEM_RE.sub(" ", directive)
    return _content_tokens(stripped)


def find_target_entry(directive, l4_doc, *, blame_lookup_fn=None):
    """Locate the existing L4 op that best matches ``directive``.

    Scoring: count of distinct content-token overlap between the
    directive (stems pruned) and the op's body text + H3 heading text
    + ``source-conversation`` metadata. Including the H3 heading
    means operator phrasings like "undo the file-bug pre-check"
    match `replace step:cycle/file-bug` ops via the step-id token,
    not just by body overlap.

    Single-entry fast path: when only ONE L4 op exists across all
    slots and the operator's directive is a removal-shape request,
    score threshold drops to 1 — the user can't be ambiguous about
    which entry to remove if there's only one. This handles the
    operator's common case (the first removal after one prior
    customization) without forcing them to repeat distinctive body
    phrases.

    Returns one of:

      - **single match** — ``([entry], confident=True)`` when the top
        entry beats ``_MIN_OVERLAP`` (or the single-entry threshold)
        AND beats the runner-up by at least ``_AMBIGUITY_MARGIN``.
      - **ambiguous** — ``(candidates, confident=False)`` when two or
        more entries score above threshold but no single winner.
      - **empty** — ``([], confident=False)`` when no entry crosses
        threshold.

    ``blame_lookup_fn`` is an optional injection seam taking
    ``(slot, op_index)`` and returning ``(sha, authored_by)`` — tests
    pass a stub to populate the audit-trail preview without invoking
    git. Real callers wire it to a git-blame helper.
    """
    directive_tokens = _directive_content_tokens(directive)
    total_ops = sum(len(ops) for ops in (l4_doc.slots or {}).values())
    min_overlap = 1 if total_ops <= 1 else _MIN_OVERLAP
    candidates = []
    for slot, ops in (l4_doc.slots or {}).items():
        for i, op in enumerate(ops):
            heading_text = _format_op_heading(op).replace("step:cycle/", " ").replace("-", " ")
            sc = op.metadata.get("source-conversation", "") if op.metadata else ""
            scoring_text = f"{op.body_text} {heading_text} {sc}"
            body_tokens = _content_tokens(scoring_text)
            score = len(directive_tokens & body_tokens)
            if score < min_overlap:
                continue
            sha, authored_by = None, None
            if blame_lookup_fn is not None:
                try:
                    sha, authored_by = blame_lookup_fn(slot, i)
                except Exception:
                    sha, authored_by = None, None
            if authored_by is None and op.metadata:
                authored_by = op.metadata.get("authored-by")
            candidates.append(TargetEntry(
                slot=slot,
                op_index=i,
                op=op,
                overlap_score=score,
                commit_sha=sha,
                authored_by=authored_by,
            ))
    if not candidates:
        return [], False
    candidates.sort(key=lambda c: c.overlap_score, reverse=True)
    if len(candidates) == 1:
        return [candidates[0]], True
    if candidates[0].overlap_score - candidates[1].overlap_score >= _AMBIGUITY_MARGIN:
        return [candidates[0]], True
    above_threshold = [c for c in candidates if c.overlap_score >= min_overlap]
    return above_threshold[:5], False


# ---------------------------------------------------------------------------
# Preview formatting (human-facing — surfaced in the upstream dialog)
# ---------------------------------------------------------------------------


def format_target_preview(entry):
    """One-screen preview of the L4 op that's about to be touched.

    Shows the H3 heading, the body excerpt (first 6 lines), the commit
    SHA short-prefix, and the ``authored-by`` field — enough audit
    context for the human to confirm "yes, that's the one".
    """
    if entry is None:
        return "(no matching L4 entry)"
    heading = _format_op_heading(entry.op)
    body_lines = entry.op.body_text.splitlines()
    body_excerpt = "\n".join(body_lines[:6])
    if len(body_lines) > 6:
        body_excerpt += "\n…"
    parts = [
        f"Under `## {entry.slot}`:",
        "",
        f"### {heading}",
        "",
        body_excerpt,
        "",
    ]
    if entry.authored_by or entry.commit_sha:
        sha = entry.commit_sha[:8] if entry.commit_sha else "?"
        author = entry.authored_by or "?"
        parts.append(f"(authored-by `{author}` @ commit `{sha}`)")
    return "\n".join(parts)


def _format_op_heading(op):
    if op.target_step_id is None:
        return op.op_type
    return f"{op.op_type} step:cycle/{op.target_step_id}"


# ---------------------------------------------------------------------------
# Counter-op generation
# ---------------------------------------------------------------------------


def build_counter_op(entry):
    """Return the staged H3 op text that cancels ``entry``'s effect, or None.

    Counter-op is only well-defined for prior ``replace step:cycle/X``
    ops. In that case we emit ``### replace step:cycle/X`` with a
    counter-op HTML sentinel; the op-processor's
    ``_apply_replace_step`` treats sentinel-only bodies as opt-in
    no-ops, so the underlying L1-L3 step body survives both the
    original op and its counter-op. Additive history: the prior H3
    block stays in the file.

    For every other op shape there is NO clean counter-op:

    - ``insert-before step:cycle/X`` / ``insert-after step:cycle/X``
      — the inserted body survives a subsequent ``replace step:cycle/X``
      because replace only touches the step body, not adjacent
      inserted prose. Counter-op would not actually cancel the
      inserted content.
    - whole-slot ``replace`` (Responsibility only) and non-targeted
      ``append`` — there is no "delete-append" in the grammar.

    For all of these the caller's only path is in-place delete with
    explicit human confirmation; we return ``None`` so
    ``plan_removal`` surfaces ``no-counter-op-possible`` and the
    upstream dialog re-asks the human.
    """
    op = entry.op
    if op.op_type != "replace" or op.target_step_id is None:
        return None
    return (
        f"### replace step:cycle/{op.target_step_id}\n"
        f"\n"
        f"<!-- counter-op: removes the prior `replace step:cycle/{op.target_step_id}` entry -->\n"
        f"\n"
    )


# ---------------------------------------------------------------------------
# In-place delete (requires explicit human confirmation)
# ---------------------------------------------------------------------------


def build_in_place_delete(l4_text, entry):
    """Return ``l4_text`` with ``entry``'s H3 block excised.

    Finds the Nth H3 op heading under the targeted ``## <Slot>`` H2
    and removes lines from that heading up to (but not including) the
    next H3, the next H2, or end-of-file — whichever comes first.
    Leading blank lines that immediately precede the H3 are also
    consumed so the resulting file doesn't accumulate empty blocks.
    """
    lines = l4_text.splitlines(keepends=True)
    target_heading = f"### {_format_op_heading(entry.op)}"
    target_slot_norm = entry.slot
    current_slot = None
    h3_index_in_slot = -1
    start, end = None, None

    for i, raw in enumerate(lines):
        stripped = raw.rstrip("\n").rstrip()
        # Exact-prefix check using regex anchors so ``#### subhead``
        # in a body is not mistaken for an H2 / H3 boundary.
        is_h2 = bool(re.match(r"^##\s+\S", stripped)) and not stripped.startswith("### ")
        is_h3 = bool(re.match(r"^###\s+\S", stripped)) and not stripped.startswith("#### ")
        if is_h2:
            # H2 boundary; reset per-slot H3 counter
            current_slot = _normalize_slot(stripped[3:])
            h3_index_in_slot = -1
            if start is not None and end is None:
                end = i
                break
            continue
        if is_h3 and current_slot == target_slot_norm:
            h3_index_in_slot += 1
            if h3_index_in_slot == entry.op_index and start is None:
                # Consume immediately-preceding blank lines so we don't
                # leave a hole.
                start = i
                while start > 0 and lines[start - 1].strip() == "":
                    start -= 1
            elif start is not None and end is None:
                end = i
                break

    if start is None:
        # Couldn't locate the target — defensively no-op rather than
        # corrupting the file.
        return l4_text
    if end is None:
        end = len(lines)
    return "".join(lines[:start] + lines[end:])


def _normalize_slot(raw):
    """Same shape as :func:`l4_parser._normalize_slot`. Inlined to avoid
    importing a private helper across modules; if the parser's
    normalization ever evolves, update both call sites.
    """
    return re.sub(r"\s+", "-", raw.strip().lower())


# ---------------------------------------------------------------------------
# Orchestrator — never raises; failure modes carried in RemovalPlan.
# ---------------------------------------------------------------------------


def plan_removal(*, directive, l4_text,
                 in_place_delete_confirmed=False,
                 blame_lookup_fn=None):
    """Detect → target → choose path → stage content. Returns :class:`RemovalPlan`.

    ``in_place_delete_confirmed`` is the upstream dialog's explicit
    confirmation flag. When False (default), the planner prefers the
    counter-op path and only falls back to in-place-delete when no
    counter-op is possible (and even then, returns
    ``no-counter-op-possible`` so the upstream dialog re-asks the
    human for delete confirmation rather than silently deleting).

    When True, the planner takes the in-place-delete path
    unconditionally (the upstream dialog has already secured human
    consent).

    ``blame_lookup_fn`` plumbs through to ``find_target_entry`` for
    audit-trail population.
    """
    if not is_removal_request(directive):
        return RemovalPlan(
            path_chosen="not-a-removal-request",
            diagnostic=(
                "Directive does not match removal-shape patterns "
                "(undo / remove / drop / forget / cancel / revert / "
                "stop doing / no longer). Route through the normal "
                "customization-detection dialog instead."
            ),
        )

    try:
        l4_doc = l4_parser.parse_l4_text(l4_text)
    except l4_parser.L4ParseError as e:
        return RemovalPlan(
            path_chosen="not-found",
            diagnostic=(
                f"L4 file is unparseable, so no entries can be matched "
                f"for removal: {e}"
            ),
        )

    candidates, confident = find_target_entry(
        directive, l4_doc, blame_lookup_fn=blame_lookup_fn,
    )
    if not candidates:
        return RemovalPlan(
            path_chosen="not-found",
            diagnostic=(
                "No existing L4 entry overlaps enough with the removal "
                "directive to confidently identify the target. Ask the "
                "human to name the entry more specifically (e.g. quote "
                "a distinctive phrase from the original rule)."
            ),
        )
    if not confident:
        return RemovalPlan(
            path_chosen="ambiguous",
            candidates=candidates,
            diagnostic=(
                "Multiple existing L4 entries match the removal "
                "directive with similar confidence. Surface the "
                "candidates to the human and ask which one to undo."
            ),
        )

    target = candidates[0]

    if in_place_delete_confirmed:
        new_text = build_in_place_delete(l4_text, target)
        return RemovalPlan(
            path_chosen="in-place-delete",
            target=target,
            new_l4_text=new_text,
            diagnostic=(
                f"In-place delete confirmed. Excised "
                f"`{_format_op_heading(target.op)}` from `## {target.slot}`."
            ),
            requires_explicit_confirmation=False,
        )

    counter_op_text = build_counter_op(target)
    if counter_op_text is None:
        return RemovalPlan(
            path_chosen="no-counter-op-possible",
            target=target,
            diagnostic=(
                f"The targeted entry is `{_format_op_heading(target.op)}` "
                f"under `## {target.slot}`. There is no clean counter-op "
                f"shape for `{target.op.op_type}` ops in this slot — "
                f"the only path is in-place delete. Ask the human to "
                f"explicitly confirm the delete (then re-call with "
                f"`in_place_delete_confirmed=True`)."
            ),
            requires_explicit_confirmation=True,
        )

    return RemovalPlan(
        path_chosen="counter-op",
        target=target,
        counter_op_text=counter_op_text,
        diagnostic=(
            f"Counter-op generated against "
            f"`{_format_op_heading(target.op)}` under `## {target.slot}`. "
            f"Prior entry preserved in the file; the new op cancels its "
            f"effect at compose time."
        ),
    )
