"""Atomic emit of the verbatim §4.6 triple (post-#11011 / #11050).

Wraps what used to be the LLM assemble pipeline. The pipeline was
retired by commit ``8da22e25`` (#11011 cutover unblock) which expanded
``_VERBATIM_SLOTS`` to cover all six canonical slots; #11050 then
pruned the dead LLM / verifier / conflict / cache modules along with
their injection seams.

What remains: split the linked composite into canonical slots, pass
each through verbatim, write ``CLAUDE.md`` + ``CLAUDE.linked.md`` +
``CLAUDE.conflicts.md`` (the latter is an empty header — there are no
conflicts in verbatim mode) atomically. On any write failure raise
:class:`AssembleError` (or :class:`ConflictReportWriteFail` for the
conflicts artifact); the output dir is left as it was on failure.

Reinstating LLM rewrite on a per-slot basis is a future opt-in: remove
the slot from ``_VERBATIM_SLOTS`` AND wire the dispatcher / verifier /
resolver back into ``assemble_and_emit``. The cache key contract that
folded ``model_id`` into a SHA256 is gone with the rest of the
pipeline; a re-introduction needs to revisit that design.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path


# Slots that bypass the LLM rewrite entirely (B1's VERBATIM_SLOTS). For
# B7, these slots' linked bodies become the assembled bodies verbatim —
# no preservation check, no conflict detection, no resolver pass.
#
# Post-#11011: all six canonical slots are verbatim. The LLM assemble
# pass is retired pending #11000 Phase 2 decision on whether to
# reinstate it. Rationale (per #11011 + #11000 Phase 1 research):
#  - Bug 1 (sonnet model lock has no Anthropic provider): skipped — no
#    LLM dispatch occurs in verbatim mode.
#  - Bug 2 (claude branch returns exit 1 with no file): skipped — same.
#  - Bug 4 (preservation verifier counts tokens inside HTML comments):
#    skipped — preservation check only runs for non-verbatim slots.
#  - D2 (#10691) link-stage filter remains active: sub-skill bodies
#    are still dropped from the instructions slot, so output stays in
#    the 22-29% size band PR #10691 promised.
# To re-enable LLM rewrite for a slot, remove it from this set AND
# ensure the Anthropic provider (or equivalent for the routed model)
# is wired in references/scripts/providers/.
_VERBATIM_SLOTS = frozenset({
    "identity", "responsibility", "soul",
    "instructions", "project-context", "vault",
})

# Canonical slot ordering from A2d. Kept local so B7 doesn't import
# v2_link_stage at module load time (v2_link_stage transitively loads
# yaml etc., heavy for tests).
_CANONICAL_SLOTS = (
    "identity",
    "responsibility",
    "soul",
    "instructions",
    "project-context",
    "vault",
)
_SLOT_DISPLAY = {
    "identity": "Identity",
    "responsibility": "Responsibility",
    "soul": "Soul",
    # #11144 Finding 5b: kept in sync with v2_link_stage.SLOT_DISPLAY.
    "instructions": "Agent Functions",
    "project-context": "Project Context",
    "vault": "Vault",
}


class AssembleError(Exception):
    """Base class for atomic-write failures (post-#11050: LLM-pipeline subclasses removed)."""

    def __init__(self, message, *, slot=None):
        super().__init__(message)
        self.slot = slot  # optional, names the offending slot


class ConflictReportWriteFail(AssembleError):
    """Writing CLAUDE.conflicts.md failed (disk-full / permission / etc.)."""


class LinkStageFail(AssembleError):
    """The linked composite handed to us is malformed (no slot headings)."""


@dataclass
class AssembleTriple:
    """The three artifacts emitted atomically per §4.6."""

    claude_md: str
    claude_linked_md: str
    claude_conflicts_md: str


def assemble_and_emit(
    linked_composite,
    output_dir,
    *,
    role_class,
    model_id="<unknown>",
    commit_sha="<unknown>",
    generated_at=None,
    # PRD-B B9 (#10763 AC3): filename family selector. Post-E6 cutover
    # (#10685) the default is "" — v2 outputs land at the canonical
    # CLAUDE.md / linked.md / conflicts.md filenames. The ".v2.md"
    # value is retained for legacy callers / coexistence-era tests.
    filename_suffix="",
):
    """Atomic write of the §4.6 verbatim triple.

    Returns ``(claude_md, claude_linked_md, claude_conflicts_md)`` on-disk
    paths. Raises :class:`LinkStageFail` if ``linked_composite`` has no
    canonical ``## <Slot>`` headings; raises :class:`AssembleError` or
    :class:`ConflictReportWriteFail` on write failure. On any failure no
    artifacts are produced — ``.tmp`` files are unlinked before re-raise.

    ``linked_composite`` is the full string from ``v2_link_stage.emit_v2_linked``.
    ``output_dir`` is typically ``.squidsquad/<alias>/``.

    Post-#11050: every slot is verbatim, so there is no LLM dispatch,
    no preservation/floor/parity check, and no per-slot cache. The
    conflicts artifact is always an empty-header marker (no conflict
    records to report).
    """
    slot_inputs = _split_linked_into_slots(linked_composite)
    if not slot_inputs:
        raise LinkStageFail(
            "Linked composite contains no canonical `## <Slot>` headings — "
            "the link stage produced an unusable output. Aborting before "
            "the triple write."
        )

    assembled_per_slot = {
        slot: slot_inputs.get(slot, "") for slot in _CANONICAL_SLOTS
    }

    claude_md = _build_claude_md(assembled_per_slot)
    claude_linked_md = linked_composite
    claude_conflicts_md = _empty_conflicts_report(
        role_class=role_class,
        model_id=model_id,
        commit_sha=commit_sha,
        generated_at=generated_at,
    )

    return _atomic_write_triple(
        Path(output_dir),
        AssembleTriple(
            claude_md=claude_md,
            claude_linked_md=claude_linked_md,
            claude_conflicts_md=claude_conflicts_md,
        ),
        filename_suffix=filename_suffix,
    )


def _empty_conflicts_report(*, role_class, model_id, commit_sha, generated_at):
    """Empty-conflicts CLAUDE.conflicts.md (post-#11050 verbatim mode).

    Replaces ``conflict_detector.emit_conflict_report`` for the always-zero
    case. Format kept compact and self-describing so an operator opening
    the file sees why it's empty.
    """
    stamp = generated_at if generated_at is not None else "<unset>"
    return (
        "# Assemble conflicts\n\n"
        f"- role_class: {role_class}\n"
        f"- model_id: {model_id}\n"
        f"- commit_sha: {commit_sha}\n"
        f"- generated_at: {stamp}\n\n"
        "No conflict records — every canonical slot is verbatim "
        "(`_VERBATIM_SLOTS` = all 6) so no LLM dispatch or resolver "
        "pass runs. See atomic_emit module docstring for reinstatement.\n"
    )


def _split_linked_into_slots(linked_composite):
    """Split a linked composite into ``{slot_name: per_slot_body_text}``.

    Returns ``{}`` when the composite has no recognized slot headings —
    callers treat that as :class:`LinkStageFail`.

    #11011 Bug 3 fix: only canonical slot H2s ("## Soul", "## Identity",
    etc.) terminate a slot body. Role-suffixed variants like
    "## Soul — PM" or "## Soul — Base Agent" — which the source SOUL.md
    files open with — are NOT slot boundaries and their contents stay
    inside the parent canonical slot. Previously the splitter terminated
    on any "## " line, so the canonical "## Soul\\n" wrapper that
    v2_link_stage emits picked up an empty body and the role-suffixed
    bodies were silently discarded.
    """
    bodies = {}
    lookup = {v.lower(): k for k, v in _SLOT_DISPLAY.items()}
    # Build the canonical-headings-only boundary regex: match a "## <name>"
    # line where <name> (case-insensitive, trailing whitespace + trailing #
    # tolerated for setext/closed-atx variants) is exactly one of the six
    # canonical slot display names. Anything else (e.g. "## Soul — PM") is
    # treated as ordinary body content, not a slot boundary.
    canonical_alts = "|".join(re.escape(v) for v in _SLOT_DISPLAY.values())
    canonical_pat = re.compile(
        rf"^##\s+({canonical_alts})\s*#*\s*\n",
        re.MULTILINE | re.IGNORECASE,
    )
    matches = list(canonical_pat.finditer(linked_composite))
    if not matches:
        return bodies
    for i, m in enumerate(matches):
        display = m.group(1).strip()
        slot_key = lookup.get(display.lower())
        if slot_key is None:
            continue
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(linked_composite)
        bodies[slot_key] = linked_composite[body_start:body_end]
    return bodies


def _build_claude_md(assembled_per_slot):
    """Concatenate assembled per-slot bodies into the final CLAUDE.md."""
    chunks = []
    for slot in _CANONICAL_SLOTS:
        body = assembled_per_slot.get(slot, "").strip()
        chunks.append(f"## {_SLOT_DISPLAY[slot]}\n\n{body}".rstrip() + "\n")
    return "\n".join(chunks)


def _atomic_write_triple(output_dir, triple, *, filename_suffix=""):
    """Write all three artifacts to ``.tmp`` files first, then rename.

    If any ``.tmp`` write fails, ALL ``.tmp`` files are unlinked and the
    failure is raised — the output dir is left as it was. If all writes
    succeed, ``os.replace`` swaps each ``.tmp`` into place. A rename
    failure at this stage is rare (atomic-replace within the same dir);
    we surface it as ``ConflictReportWriteFail`` for the conflicts
    artifact and as ``AssembleError`` otherwise — the operator's
    intervention is the safer answer than a half-rolled-back state.

    ``filename_suffix`` (PRD-B B9 / #10763 AC3) selects the output
    filename family:

    - Default empty string ``""`` lands the triple at canonical names
      (``CLAUDE.md`` / ``CLAUDE.linked.md`` / ``CLAUDE.conflicts.md``).
      Post-E6 cutover (#10685) this is the only intended value — v2
      outputs ARE the canonical CLAUDE.md.
    - ``".v2.md"`` lands the triple at the pre-cutover §9a coexistence
      filenames (``CLAUDE.v2.md`` etc.). Pre-cutover this was the default;
      retained as a parameter so legacy callers / tests can opt into
      coexistence-era paths if needed.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Default branch is empty-suffix → canonical CLAUDE.md filenames
    # (post-E6 cutover). The ``.v2.md`` branch is retained for legacy
    # callers / coexistence-era tests. Empty string takes the explicit
    # canonical branch rather than literal-appending (which would produce
    # extensionless ``CLAUDE`` etc.).
    if filename_suffix == "":
        base_md = "CLAUDE.md"
        linked_md = "CLAUDE.linked.md"
        conflicts_md = "CLAUDE.conflicts.md"
    else:
        base_md = f"CLAUDE{filename_suffix}"
        linked_md = f"CLAUDE.linked{filename_suffix}"
        conflicts_md = f"CLAUDE.conflicts{filename_suffix}"
    targets = {
        base_md: triple.claude_md,
        linked_md: triple.claude_linked_md,
        conflicts_md: triple.claude_conflicts_md,
    }
    tmp_paths = {name: output_dir / (name + ".tmp") for name in targets}

    # Phase 1: write every .tmp. Roll back on any failure.
    try:
        for name, content in targets.items():
            tmp_paths[name].write_text(content, encoding="utf-8")
    except OSError as e:
        for tp in tmp_paths.values():
            try:
                tp.unlink(missing_ok=True)
            except OSError:
                pass
        # Conflict-report-write fail gets its own type for AC clarity.
        # Use ``conflicts_md`` (the suffix-aware basename) so the error
        # discrimination still works under ``filename_suffix=""``.
        if conflicts_md in str(e) or (e.filename and conflicts_md in str(e.filename)):
            raise ConflictReportWriteFail(
                f"Failed to write {conflicts_md}.tmp: {e}"
            ) from e
        raise AssembleError(f"Failed to stage assemble triple: {e}") from e

    # Phase 2: rename .tmp into place.
    final_paths = {}
    for name in targets:
        final = output_dir / name
        try:
            os.replace(tmp_paths[name], final)
        except OSError as e:
            # Leave any successful renames in place — surfacing the
            # exact failure is more useful than half-rolling-back.
            if name == conflicts_md:
                raise ConflictReportWriteFail(
                    f"Failed to rename {conflicts_md}.tmp into place: {e}"
                ) from e
            raise AssembleError(
                f"Failed to rename {name}.tmp into place: {e}"
            ) from e
        final_paths[name] = final

    return (
        final_paths[base_md],
        final_paths[linked_md],
        final_paths[conflicts_md],
    )
