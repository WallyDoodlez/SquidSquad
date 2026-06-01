# TEST-PLAN-10490 — PRD-A / Story A2d: Six-slot output emitter

**Source**: issue #10490 ACs.
**Derived without reading the worker's diff.**

## Acceptance criteria

- **AC-1**: `emit_v2_linked(role_class: str, l3_domain: str | None) -> str`.
- **AC-2**: Walks L1-L3 sources, groups by slot, sorts each slot by ordinal.
- **AC-3**: Applies A2c L4 op processing per slot.
- **AC-4**: Emits exactly six H2 sections in canonical order (Identity, Responsibility, Soul, Instructions, Project Context, Vault).
- **AC-5**: Byte-stable output across re-runs given unchanged inputs.
- **AC-6**: Unit tests with minimal fixture composing to golden.

## Test Cases

### TC-1 (AC-1): signature returns str
### TC-2 (AC-2): items grouped by slot
### TC-3 (AC-2): within-slot ordering by ordinal
### TC-4 (AC-3): L4 op (replace step) applied per slot
### TC-5 (AC-3): missing L4 file is no-op
### TC-6 (AC-4): exactly six H2 sections, canonical order
### TC-7 (AC-4): absent slot still emits empty header (six is invariant)
### TC-8 (AC-5): two runs against identical input → identical bytes
### TC-9 (AC-6): minimal fixture → expected output (golden-like coverage across grouping/ordering/L4)

## Non-goals
- A2f deploy_alias_v2 wiring (separate)
- A1/A2a frontmatter parsing (already shipped)
- A2b L4Document parsing (shipped)
- A2c L4 op application (shipped)
