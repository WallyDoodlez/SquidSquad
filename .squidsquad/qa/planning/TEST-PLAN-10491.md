# TEST-PLAN-10491 — PRD-A / Story A2e: 7 link-stage validation rules R1-R7

**Source**: issue #10491 ACs (PRD-A §3 criterion 6).
**Derived without reading the worker's diff.**

## Acceptance criteria

Seven rules — each must abort with a diagnostic naming the rule + offending file/path/step-id; all rules run BEFORE any disk write; pre-write zero-partial-artifact contract.

- **R1**: L4 file with `## Vault` H2 → abort (Vault is L1-exclusive).
- **R2**: L2/L3 source with `slot: vault` frontmatter → abort.
- **R3**: L1-L3 source with `slot: project-context` frontmatter → abort.
- **R4**: L4 `### append` under `## Instructions` with no `→ run sub-skill: <name>` → abort.
- **R5**: L4 op referencing non-existent step-id → abort, name the offending step-id.
- **R6**: Whole-slot `replace` mixed with other ops in same slot → abort (per-slot scope, not per-file).
- **R7**: Two `### replace step:cycle/<id>` blocks on same step → abort.

## Test Cases

For each rule R1-R7:
- **Negative**: violating fixture aborts.
- **Positive boundary**: a near-miss that should pass (e.g. R2 allows L1 vault; R6 solo whole-slot-replace passes; R7 replace+insert-before same target legal).

Plus diagnostic-shape coverage: exception carries `.rule`, `.file_path`, `.step_id` attributes (R5 names offending step-id).

Plus pre-write contract: validator is pure function (no I/O), so abort-before-write is intrinsic — verified by absence of file-system side-effect calls.

## Non-goals
- Validator wiring into v2 emit path (A2f).
- Whole-PRD scope (covered by A2a-A2d's own tests).
