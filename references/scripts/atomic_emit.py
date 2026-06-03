"""Atomic emit + abort semantics for the assemble pass (#10447, PRD-B B7).

Wraps the whole assemble pipeline. On success: write the §4.6 triple
(``CLAUDE.md`` + ``CLAUDE.linked.md`` + ``CLAUDE.conflicts.md``)
atomically. On any failure: raise an :class:`AssembleError` subclass;
the prior successful triple (if any) on disk is left untouched, and the
current run produces zero partial artifacts.

Failure modes from the TRD §4.6 table (per issue body AC):

- LLM error → :class:`LLMError`
- Preservation fail (B2) → :class:`PreservationFail`
- Floor / parity fail (B3) → :class:`FloorParityFail`
- Cache corruption → :class:`CacheCorruption` (after one LLM retry)
- Conflict-report-write fail → :class:`ConflictReportWriteFail`
- Precedence violation (resolver picked lower L) → :class:`PrecedenceViolation`
- Link-stage fail → no assemble attempted (caller's lane; we raise
  :class:`LinkStageFail` if a malformed linked composite reaches us)

Per the AC: "On any abort: prior successful triple untouched; current
run produces zero partial artifacts." This is enforced by writing all
three artifacts to ``.tmp`` files first, verifying every write succeeded
before any rename, then ``os.replace``-ing each into place.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path


# Slots that bypass the LLM rewrite entirely (B1's VERBATIM_SLOTS). For
# B7, these slots' linked bodies become the assembled bodies verbatim —
# no preservation check, no conflict detection, no resolver pass.
_VERBATIM_SLOTS = frozenset({"project-context", "vault"})

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
    "instructions": "Instructions",
    "project-context": "Project Context",
    "vault": "Vault",
}


class AssembleError(Exception):
    """Base class for assemble-pass failures that trigger §4.6 abort."""

    def __init__(self, message, *, slot=None):
        super().__init__(message)
        self.slot = slot  # optional, names the offending slot


class LLMError(AssembleError):
    """The LLM dispatch failed (model_router non-zero / no output / etc.)."""


class PreservationFail(AssembleError):
    """B2 preservation check failed on the assembled body."""


class FloorParityFail(AssembleError):
    """B3 length-floor or code-block-parity failed on the assembled body."""


class CacheCorruption(AssembleError):
    """The cached assembled body failed preservation; re-run also failed."""


class ConflictReportWriteFail(AssembleError):
    """Writing CLAUDE.conflicts.md failed (disk-full / permission / etc.)."""


class PrecedenceViolation(AssembleError):
    """B5 detected the resolver picked the lower-L position."""


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
    # CLAUDE.md / linked.md / conflicts.md filenames. Pre-cutover the
    # default was ".v2.md" to keep §9a coexistence with v1; the cutover
    # retires that requirement so the default flips.
    filename_suffix="",
    # Injection seams for tests:
    assemble_slot_fn=None,
    parse_output_fn=None,
    resolve_fn=None,
    emit_report_fn=None,
    cache_lookup_fn=None,
    cache_store_fn=None,
):
    """Run the full assemble pass + atomic write of the §4.6 triple.

    Returns the on-disk paths ``(claude_md, claude_linked_md, claude_conflicts_md)``
    on success. Raises an :class:`AssembleError` subclass on any failure
    mode; the output directory is NOT modified on failure (any ``.tmp``
    files are cleaned up before re-raising).

    ``linked_composite`` is the full string from ``emit_v2_linked``
    (A2d). It must contain exactly the six canonical ``## <Slot>``
    headings — anything else raises :class:`LinkStageFail`.

    ``output_dir`` is typically ``.squidsquad/<alias>/`` (the same dir
    A6/A2f's v2 deploy writes to). The three files are written into
    that dir; the dir itself is created lazily.

    ``cache_lookup_fn(slot, linked_slot_body) -> str | None`` and
    ``cache_store_fn(slot, linked_slot_body, assembled_llm_output)``
    integrate B6's per-slot cache. A cache hit whose body fails
    verification is treated as cache-corruption: the LLM is re-run
    ONCE; if the re-run also fails verification, :class:`CacheCorruption`
    is raised (per the §4.6 failure-mode table). A cache miss runs the
    LLM normally; verification failures on a fresh (no-cache) run raise
    :class:`PreservationFail` / :class:`FloorParityFail` /
    :class:`PrecedenceViolation` directly — no retry. Both seams default
    to no-op (cache-disabled mode) so tests and the v2-without-cache
    path keep working unchanged.

    Injection seams take the real modules' callables by default. Tests
    pass stubs to exercise each failure mode without a live LLM.
    """
    if assemble_slot_fn is None or parse_output_fn is None \
            or resolve_fn is None or emit_report_fn is None:
        # Lazy-import the real implementations only when defaults are
        # requested. Tests can supply all four without any of these
        # being importable, which keeps the failure-path test suite
        # tight and fast.
        from assemble_pass import assemble_slot as _assemble_slot
        from conflict_detector import (
            parse_assemble_output as _parse_assemble_output,
            emit_conflict_report as _emit_conflict_report,
        )
        from conflict_resolver import resolve as _resolve
        assemble_slot_fn = assemble_slot_fn or _assemble_slot
        parse_output_fn = parse_output_fn or _parse_assemble_output
        resolve_fn = resolve_fn or _resolve
        emit_report_fn = emit_report_fn or _emit_conflict_report

    slot_inputs = _split_linked_into_slots(linked_composite)
    if not slot_inputs:
        raise LinkStageFail(
            "Linked composite contains no canonical `## <Slot>` headings — "
            "the link stage produced an unusable output. Aborting before "
            "any assemble dispatch."
        )

    assembled_per_slot = {}
    conflicts_per_slot = {}

    for slot in _CANONICAL_SLOTS:
        linked_slot_body = slot_inputs.get(slot, "")

        if slot in _VERBATIM_SLOTS:
            # B1 contract: project-context + vault pass through verbatim.
            # No preservation, no conflict, no resolver.
            assembled_per_slot[slot] = linked_slot_body
            conflicts_per_slot[slot] = []
            continue

        body, conflicts = _assemble_one_slot(
            slot, linked_slot_body,
            assemble_slot_fn=assemble_slot_fn,
            parse_output_fn=parse_output_fn,
            resolve_fn=resolve_fn,
            cache_lookup_fn=cache_lookup_fn,
            cache_store_fn=cache_store_fn,
        )
        assembled_per_slot[slot] = body
        conflicts_per_slot[slot] = conflicts

    # Build the three artifacts.
    claude_md = _build_claude_md(assembled_per_slot)
    claude_linked_md = linked_composite
    all_conflicts = [
        c for slot in _CANONICAL_SLOTS for c in conflicts_per_slot.get(slot, [])
    ]
    claude_conflicts_md = emit_report_fn(
        all_conflicts,
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


def _assemble_one_slot(slot, linked_slot_body, *,
                       assemble_slot_fn, parse_output_fn, resolve_fn,
                       cache_lookup_fn=None, cache_store_fn=None):
    """Produce ``(body, conflicts)`` for one non-verbatim slot.

    Implements the §4.6 cache flow: cache hit + valid → return; cache
    hit + corrupt → re-run LLM once, raise :class:`CacheCorruption` if
    the retry also fails; cache miss → run LLM, raise the per-mode
    exception on verification fail (no retry); store on success.
    """
    cached_output = None
    if cache_lookup_fn is not None:
        try:
            cached_output = cache_lookup_fn(slot, linked_slot_body)
        except Exception:  # noqa: BLE001 — a cache backend error is treated as miss
            cached_output = None

    if cached_output is not None:
        # Verify the cached output. Verification covers parse + resolve;
        # a cached body that parses cleanly AND passes B2/B3/B5 is good.
        if _try_verify(cached_output, linked_slot_body,
                       parse_output_fn=parse_output_fn,
                       resolve_fn=resolve_fn) is not None:
            body, conflicts = parse_output_fn(cached_output)
            return body, conflicts
        # Cache corruption: re-run LLM once.
        try:
            retry_output = assemble_slot_fn(slot, linked_slot_body)
        except Exception as e:  # noqa: BLE001
            raise LLMError(
                f"assemble_slot raised on slot `{slot}` during cache-corruption retry: {e}",
                slot=slot,
            ) from e
        verify_result = _try_verify(retry_output, linked_slot_body,
                                    parse_output_fn=parse_output_fn,
                                    resolve_fn=resolve_fn)
        if verify_result is None:
            raise CacheCorruption(
                f"Cached assembled body failed verification on slot `{slot}` "
                f"AND the one-shot LLM retry also failed verification. "
                f"Aborting per §4.6 cache-corruption table entry.",
                slot=slot,
            )
        # Retry passed — persist the new body and use it.
        if cache_store_fn is not None:
            try:
                cache_store_fn(slot, linked_slot_body, retry_output)
            except Exception:  # noqa: BLE001 — store failure does not invalidate the run
                pass
        body, conflicts = verify_result
        return body, conflicts

    # Cache miss (or cache disabled): run LLM fresh.
    try:
        llm_output = assemble_slot_fn(slot, linked_slot_body)
    except Exception as e:  # noqa: BLE001
        raise LLMError(
            f"assemble_slot raised on slot `{slot}`: {e}",
            slot=slot,
        ) from e
    try:
        body, conflicts = parse_output_fn(llm_output)
    except Exception as e:  # noqa: BLE001
        raise LLMError(
            f"parse_assemble_output failed on slot `{slot}`: {e}",
            slot=slot,
        ) from e
    issues, reverify = resolve_fn(body, conflicts, linked_slot_body)
    if issues:
        raise PrecedenceViolation(
            f"Higher-L-wins violation in slot `{slot}`: "
            f"CONFLICT-{issues[0].conflict_index:03d} "
            f"({issues[0].winner_layer}>{issues[0].loser_layer}): "
            f"{issues[0].detail}",
            slot=slot,
        )
    if not reverify.preservation_ok:
        raise PreservationFail(
            f"Preservation check (B2) failed on slot `{slot}`: "
            f"missing_sub_skills={reverify.preservation.missing_sub_skills}, "
            f"extra_sub_skills={reverify.preservation.extra_sub_skills}, "
            f"missing_step_ids={reverify.preservation.missing_step_ids}, "
            f"extra_step_ids={reverify.preservation.extra_step_ids}",
            slot=slot,
        )
    if not reverify.length_floor_ok or not reverify.code_block_parity_ok:
        raise FloorParityFail(
            f"Length-floor/code-block-parity (B3) failed on slot `{slot}`: "
            f"length_floor_ok={reverify.length_floor_ok}, "
            f"code_block_parity_ok={reverify.code_block_parity_ok}",
            slot=slot,
        )
    if cache_store_fn is not None:
        try:
            cache_store_fn(slot, linked_slot_body, llm_output)
        except Exception:  # noqa: BLE001
            pass
    return body, conflicts


def _try_verify(llm_output, linked_slot_body, *, parse_output_fn, resolve_fn):
    """Internal: verify an LLM output. Returns ``(body, conflicts)`` on
    success or ``None`` on any failure (parse-error, precedence violation,
    B2/B3 fail). Used by the cache-corruption path which needs to know
    whether the body is acceptable WITHOUT raising — the caller decides
    whether to retry or abort based on the answer.
    """
    try:
        body, conflicts = parse_output_fn(llm_output)
    except Exception:  # noqa: BLE001
        return None
    issues, reverify = resolve_fn(body, conflicts, linked_slot_body)
    if issues:
        return None
    if not reverify.preservation_ok:
        return None
    if not reverify.length_floor_ok or not reverify.code_block_parity_ok:
        return None
    return body, conflicts


def _split_linked_into_slots(linked_composite):
    """Split a linked composite into ``{slot_name: per_slot_body_text}``.

    Returns ``{}`` when the composite has no recognized slot headings —
    callers treat that as :class:`LinkStageFail`.
    """
    bodies = {}
    # Match each ## H2 heading and the body up to the next ## or end.
    pattern = re.compile(
        r"^##\s+(.+?)\s*#*\s*\n(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    lookup = {v.lower(): k for k, v in _SLOT_DISPLAY.items()}
    for m in pattern.finditer(linked_composite):
        display = m.group(1).strip()
        slot_key = lookup.get(display.lower())
        if slot_key is None:
            continue
        bodies[slot_key] = m.group(2)
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
