# TEST-PLAN-10489 — PRD-A / Story A2c: L4 op processor

**Source**: issue #10489 ACs.
**Derived without reading the worker's diff.**

## Acceptance criteria

- **AC-1**: `apply_l4_ops(slot_content: str, l4_ops: list[L4Op]) -> str`.
- **AC-2**: `### replace step:cycle/<id>` substitutes the targeted step's body verbatim.
- **AC-3**: `### insert-before step:cycle/<id>` inserts L4 body before the targeted step.
- **AC-4**: `### insert-after step:cycle/<id>` inserts L4 body after the targeted step.
- **AC-5**: `### append` adds L4 body to end of slot.
- **AC-6**: Multiple ops in same slot applied in source order (per L4 file order).
- **AC-7**: Whole-slot `### replace` (no step-id, Responsibility-only) replaces entire body; enforcement of "mutually exclusive with other ops" deferred to A2e.
- **AC-8**: Unit tests for each op type + multi-op scenarios + order-independence on disjoint targets.

## Test Cases

### TC-1 (AC-1, signature): live introspection
- Probe: `apply_l4_ops(slot_content, l4_ops)` accepts two positional args, returns str.

### TC-2 (AC-2): replace targeted step body
- Step body replaced; sibling steps untouched.

### TC-3 (AC-3): insert-before places body before step heading
- Inserted body precedes the targeted `### step:cycle/<id>` line.

### TC-4 (AC-4): insert-after places body after targeted step
- Inserted body trails the targeted step's body (before the next step's heading).

### TC-5 (AC-5): append adds body to slot end

### TC-6 (AC-6): two ops on same target apply in source order (later wins on replace)

### TC-7 (AC-7): whole-slot `### replace` replaces entire slot body

### TC-8 (AC-8): order-independence for disjoint targets
- Reordering ops that target different steps produces same result.

### TC-9 (defensive): missing target raises (each of replace/insert-before/insert-after)

### TC-10 (defensive): hyphenated and underscored step IDs targetable.

## Non-goals (not tested here)

- A2b L4Document parsing (covered by TEST-PLAN-10488 — shipped)
- A2e exclusivity validation (mutually-exclusive op enforcement)
- A1 frontmatter (#10487 — shipped)
