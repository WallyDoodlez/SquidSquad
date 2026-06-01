"""Assemble-pass conflict detection + report emit (#10445, PRD-B Story B4).

Per [[compose-assemble-stage]] §4.6, the assemble pass collapses layered
prose into a single coherent voice. When layers materially contradict,
the higher layer's prose prevails (L4 > L3 > L2 > L1). The lower-layer
prose is not silently erased — every reconciled contradiction is
recorded in ``CLAUDE.conflicts.md`` as the operator's audit surface.

B4 is the DETECTION + REPORT-EMIT half:

- The LLM, in a single pass, produces the assembled body AND lists any
  conflicts it reconciled in a delimited section at the end of its
  output (template directive in ``assemble.md.j2``).
- ``parse_assemble_output`` splits the LLM output on the delimiter and
  parses the trailing conflicts block into structured ``Conflict``
  records.
- ``emit_conflict_report`` produces the §4.6 canonical-format report
  markdown from a list of ``Conflict`` records.

B5 (#10446) is the higher-L-wins RESOLVER. B7 (#10447) wires the report
into the atomic-emit pipeline (CLAUDE.md + CLAUDE.linked.md +
CLAUDE.conflicts.md triple).

This module is pure — no I/O beyond what callers do with the returned
strings.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


# HTML-comment delimiter marking the start of the conflicts section in
# LLM output. Kept stable across releases so older composes can parse
# newer outputs.
CONFLICTS_DELIMITER = "<!-- ASSEMBLE_CONFLICTS -->"

# Maximum length the §4.6 spec allows for a verbatim quote in the
# report. Longer quotes are truncated with an ellipsis. Applied at
# report-emit time so detection can keep the full quote in memory.
MAX_QUOTE_CHARS = 200


@dataclass
class Conflict:
    """One reconciled contradiction from an assemble pass.

    Field names mirror the §4.6 canonical report format. ``winner_*``
    is the higher-L source whose position the assembled body aligns
    with; ``loser_*`` is the lower-L source whose prose was overridden.
    ``ordinal`` is optional — the LLM does not always know the source
    file's frontmatter ordinal, and the report renders ``?`` when None.
    """

    slot: str
    winner_layer: str  # "L1" | "L2" | "L3" | "L4"
    loser_layer: str
    winner_path: str
    loser_path: str
    winner_quote: str
    loser_quote: str
    why: str
    resolution: str
    winner_ordinal: int | None = None
    loser_ordinal: int | None = None
    winner_op: str | None = None  # e.g. "replace step:cycle/work"


def parse_assemble_output(llm_output):
    """Split LLM output into ``(assembled_body, conflicts)``.

    The delimiter ``CONFLICTS_DELIMITER`` separates the rewritten slot
    body (above) from the conflict records (below). Outputs without the
    delimiter are treated as having zero conflicts.

    Each conflict record is a bullet group keyed ``- slot: <name>`` with
    indented continuation lines carrying the remaining fields. A literal
    ``(none)`` placeholder under the delimiter is supported for the
    common zero-conflict case.
    """
    parts = llm_output.split(CONFLICTS_DELIMITER, 1)
    if len(parts) == 1:
        return llm_output.rstrip() + "\n", []
    body = parts[0].rstrip() + "\n"
    conflicts_block = parts[1].strip()
    if not conflicts_block or conflicts_block.lower().startswith("(none)"):
        return body, []
    return body, _parse_conflict_records(conflicts_block)


def _parse_conflict_records(block):
    """Parse the trailing conflict bullet list into ``Conflict`` records.

    Permissive: unknown keys are ignored, the first ``- slot:`` line
    starts a record, and a record ends at the next ``- slot:`` line or
    end of block. Required fields default to ``""`` when the LLM omits
    them so partial records still surface in the report (operators get
    "Resolution: " rather than a parse error blocking the whole report).
    """
    records = []
    current = None
    field_re = re.compile(r"^[\s-]+([A-Za-z_]+):\s*(.*)$")
    for line in block.splitlines():
        # Strip BOM/zero-width chars that occasionally appear in LLM output.
        line = line.replace("﻿", "").rstrip()
        if not line.strip():
            continue
        m = field_re.match(line)
        if not m:
            # Continuation of the prior field's value (long quote wrapped).
            if current is not None and current["_last_key"]:
                current[current["_last_key"]] += " " + line.strip()
            continue
        key, value = m.group(1), m.group(2).strip().strip('"').strip()
        if key == "slot" and (current is None or current.get("slot")):
            if current is not None:
                records.append(_finalize_record(current))
            current = {"_last_key": "slot", "slot": value}
            continue
        if current is None:
            current = {"_last_key": key, key: value}
        else:
            current[key] = value
            current["_last_key"] = key
    if current is not None:
        records.append(_finalize_record(current))
    return records


def _finalize_record(d):
    """Build a Conflict from a parsed record dict. Missing fields default to ""."""
    def _opt_int(key):
        raw = d.get(key)
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return Conflict(
        slot=d.get("slot", "") or "",
        winner_layer=d.get("winner_layer", "") or "",
        loser_layer=d.get("loser_layer", "") or "",
        winner_path=d.get("winner_path", "") or "",
        loser_path=d.get("loser_path", "") or "",
        winner_quote=d.get("winner_quote", "") or "",
        loser_quote=d.get("loser_quote", "") or "",
        why=d.get("why", "") or "",
        resolution=d.get("resolution", "") or "",
        winner_ordinal=_opt_int("winner_ordinal"),
        loser_ordinal=_opt_int("loser_ordinal"),
        winner_op=d.get("winner_op") or None,
    )


def _truncate(text, limit=MAX_QUOTE_CHARS):
    """Truncate ``text`` to ``limit`` chars, adding ellipsis when shortened."""
    if len(text) <= limit:
        return text
    # Keep limit-3 chars + "..." per §4.6 "max 200 chars + ellipsis".
    return text[: limit - 3].rstrip() + "..."


def _ordinal_str(ordinal):
    return str(ordinal) if ordinal is not None else "?"


def emit_conflict_report(conflicts, *, role_class, model_id="<unknown>",
                          commit_sha="<unknown>", generated_at=None):
    """Produce ``CLAUDE.conflicts.md`` per §4.6 canonical format.

    Zero conflicts is a valid input — the report is still emitted with
    ``Total conflicts resolved: 0`` and no CONFLICT sections (per the
    spec; presence confirms the pass ran cleanly).

    ``generated_at`` accepts an explicit ``datetime`` for deterministic
    tests; defaults to ``datetime.now(timezone.utc)``.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)
    iso = generated_at.isoformat(timespec="seconds")

    lines = [
        f"# Compose Conflict Report — {role_class}",
        f"Generated: {iso}",
        f"Compose run: {commit_sha}",
        f"Assemble model: {model_id}",
        f"Total conflicts resolved: {len(conflicts)}",
        "",
    ]
    for idx, c in enumerate(conflicts, start=1):
        winner_op_suffix = f" + op: {c.winner_op}" if c.winner_op else ""
        lines.extend([
            f"## CONFLICT-{idx:03d} — slot: {c.slot} — "
            f"precedence: {c.winner_layer} > {c.loser_layer}",
            f"- **{c.loser_layer} source**: `{c.loser_path}` "
            f"(ordinal {_ordinal_str(c.loser_ordinal)})",
            f"  > {_truncate(c.loser_quote)}",
            f"- **{c.winner_layer} source**: `{c.winner_path}` "
            f"(ordinal {_ordinal_str(c.winner_ordinal)}{winner_op_suffix})",
            f"  > {_truncate(c.winner_quote)}",
            f"- **Why this is a conflict**: {c.why}",
            f"- **Resolution in assembled output**: {c.resolution}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"
