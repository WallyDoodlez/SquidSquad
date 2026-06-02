"""Seven link-stage validation rules R1-R7 (#10491, PRD-A Story A2e).

Implements the seven per-slot constraint rules from PRD-A §3 success
criterion 6 (the per-slot subset of §3.3 + §4.2). Each rule aborts
compose BEFORE any disk write — A2e's contract is to raise; A2f's
caller orchestrates "validate then emit" so failure produces zero
partial artifacts.

R1: L4 file containing ``## Vault`` H2 → abort (Vault is L1-exclusive).
R2: L2/L3 source with ``slot: vault`` frontmatter → abort.
R3: L1-L3 source with ``slot: project-context`` frontmatter → abort.
R4: L4 ``### append`` under ``## Instructions`` with no
    ``→ run sub-skill: <name>`` reference → abort.
R5: L4 op references non-existent step-id → abort with offending
    step-id named in the diagnostic.
R6: Whole-slot ``replace`` mixed with other ops in same slot → abort
    (per-slot scope, NOT per-file).
R7: Two ``### replace step:cycle/<id>`` blocks targeting the same
    step ID → abort (per TRD §4.2 step 3).

A2e is pure validation — no I/O, no compose. Callers provide already-
parsed inputs: an ``L4Document`` (via A2b) and a list of
``LinkStageSource`` records (built by A2f from A2d's walk output).
"""

import re
from dataclasses import dataclass


# Same regex as assemble_verifier._SUB_SKILL_RE — kept local so the
# validator doesn't reach across PRDs. Updates to one should be mirrored.
_SUB_SKILL_REF_RE = re.compile(r"→\s*run\s+sub-skill:\s*([A-Za-z0-9_-]+)")

# Step heading in an L1-L3 source body. Mirrors l4_op_processor._STEP_HEADING_RE
# but matched against the BODY (not the L4 op grammar). Same id grammar.
_SOURCE_STEP_HEADING_RE = re.compile(
    r"^### step:cycle/([A-Za-z0-9_-]+)\s*$", re.MULTILINE
)


@dataclass
class LinkStageSource:
    """One L1-L3 source with the metadata A2e needs to validate it.

    - ``layer``: ``"L1"`` / ``"L2"`` / ``"L3"`` (per LAYERS.md).
    - ``path``: posix-string path relative to repo root (used in diagnostics).
    - ``slot``: the slot value from frontmatter (``"identity"`` / etc.).
    - ``body``: file body with frontmatter stripped.
    """
    layer: str
    path: str
    slot: str
    body: str


class LinkStageValidationError(ValueError):
    """Raised when one of the R1-R7 rules is violated.

    The ``rule`` attribute carries the rule label (e.g. ``"R5"``).
    ``file_path`` and ``step_id`` are set when the diagnostic names them.
    """

    def __init__(self, rule, message, *, file_path=None, step_id=None):
        self.rule = rule
        self.file_path = file_path
        self.step_id = step_id
        prefix = f"[{rule}] "
        if file_path:
            prefix += f"({file_path}) "
        super().__init__(prefix + message)


def validate_link_stage(l4_doc, sources, *, l4_path=None):
    """Run all seven rules. Raise ``LinkStageValidationError`` on first violation.

    Rules run in declaration order R1 → R7 so the first message points
    at the rule the operator should fix first when multiple are wrong.

    Parameters
    ----------
    l4_doc : :class:`l4_parser.L4Document`
        Parsed L4 file (or ``L4Document.empty()`` when there is no L4).
    sources : list[LinkStageSource]
        L1-L3 source records. Order doesn't matter to validation.
    l4_path : str | None
        Optional path for inclusion in R1/R4/R5/R6/R7 diagnostics.
    """
    _check_r1_l4_no_vault_h2(l4_doc, l4_path)
    _check_r2_l2_l3_no_vault_slot(sources)
    _check_r3_l1_l3_no_project_context_slot(sources)
    _check_r4_instructions_append_has_sub_skill_ref(l4_doc, l4_path)
    _check_r5_l4_step_ids_resolve(l4_doc, sources, l4_path)
    _check_r6_no_mixed_whole_slot_replace(l4_doc, l4_path)
    _check_r7_no_duplicate_replace_step_targets(l4_doc, l4_path)


def _check_r1_l4_no_vault_h2(l4_doc, l4_path):
    if "vault" in l4_doc.slots:
        raise LinkStageValidationError(
            "R1",
            "L4 file contains `## Vault` slot. Vault is L1-exclusive "
            "per §3.3 + §5.6 — projects do not author vault content.",
            file_path=l4_path,
        )


def _check_r2_l2_l3_no_vault_slot(sources):
    for src in sources:
        if src.layer in ("L2", "L3") and src.slot == "vault":
            raise LinkStageValidationError(
                "R2",
                "L2/L3 source declares `slot: vault` in its frontmatter. "
                "Vault is L1-exclusive per §3.3.",
                file_path=src.path,
            )


def _check_r3_l1_l3_no_project_context_slot(sources):
    # #10751 W4: explicit layer guard for self-documenting symmetry
    # with `_check_r2_l2_l3_no_vault_slot` above. Today the source
    # collector pre-filters to L1-L3 so the guard is functionally
    # equivalent, but pinning the layer set inline means R3 stays
    # correct if the collector ever yields L4 (or any new layer) —
    # the maintenance hazard the audit called out.
    for src in sources:
        if src.slot == "project-context" and src.layer in ("L1", "L2", "L3"):
            raise LinkStageValidationError(
                "R3",
                "L1-L3 source declares `slot: project-context` in its "
                "frontmatter. Project Context is L4-exclusive per §3.3.",
                file_path=src.path,
            )


def _check_r4_instructions_append_has_sub_skill_ref(l4_doc, l4_path):
    instructions_ops = l4_doc.slots.get("instructions", [])
    for op in instructions_ops:
        if op.op_type != "append":
            continue
        if not _SUB_SKILL_REF_RE.search(op.body_text):
            raise LinkStageValidationError(
                "R4",
                "L4 `### append` under `## Instructions` has no "
                "`→ run sub-skill: <name>` reference. The thin-orchestration "
                "invariant requires every appended block under Instructions "
                "to reference at least one sub-skill (§4.5).",
                file_path=l4_path,
            )


def _check_r5_l4_step_ids_resolve(l4_doc, sources, l4_path):
    known_step_ids = _collect_source_step_ids(sources)
    for slot_name, ops in l4_doc.slots.items():
        for op in ops:
            if op.target_step_id is None:
                continue
            if op.target_step_id not in known_step_ids:
                raise LinkStageValidationError(
                    "R5",
                    f"L4 op `{op.op_type} step:cycle/{op.target_step_id}` "
                    f"in slot `## {slot_name}` references a step ID that "
                    f"is not present in any L1-L3 source.",
                    file_path=l4_path,
                    step_id=op.target_step_id,
                )


def _check_r6_no_mixed_whole_slot_replace(l4_doc, l4_path):
    for slot_name, ops in l4_doc.slots.items():
        has_whole_slot_replace = any(
            op.op_type == "replace" and op.target_step_id is None for op in ops
        )
        if has_whole_slot_replace and len(ops) > 1:
            raise LinkStageValidationError(
                "R6",
                f"Slot `## {slot_name}` mixes a whole-slot `### replace` "
                f"(no step target) with other ops. Whole-slot replace is "
                f"terminal per §4.2 step 2.i.",
                file_path=l4_path,
            )


def _check_r7_no_duplicate_replace_step_targets(l4_doc, l4_path):
    for slot_name, ops in l4_doc.slots.items():
        seen = set()
        for op in ops:
            if op.op_type != "replace" or op.target_step_id is None:
                continue
            if op.target_step_id in seen:
                raise LinkStageValidationError(
                    "R7",
                    f"Two `### replace step:cycle/{op.target_step_id}` "
                    f"blocks target the same step ID in slot `## {slot_name}`. "
                    f"Per TRD §4.2 step 3, each step ID may be the target "
                    f"of at most one `replace` op per slot.",
                    file_path=l4_path,
                    step_id=op.target_step_id,
                )
            seen.add(op.target_step_id)


def _collect_source_step_ids(sources):
    """Build the set of step IDs declared by any L1-L3 source body."""
    ids = set()
    for src in sources:
        for m in _SOURCE_STEP_HEADING_RE.finditer(src.body):
            ids.add(m.group(1))
    return ids
