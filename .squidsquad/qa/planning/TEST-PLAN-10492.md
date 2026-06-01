# TEST-PLAN-10492 — PRD-A / Story A2f: Wire v2 link stage into deploy_alias_v2

**Source**: issue #10492 ACs.
**Derived without reading the worker's diff.**

## Acceptance criteria

- **AC-1**: `deploy_alias_v2` calls `emit_v2_linked(role_class, l3_domain)` instead of v1 placeholder `deploy_role`.
- **AC-2**: A2e validation (R1-R7) runs before write; zero partial artifacts on validation failure.
- **AC-3**: Output lands at `.squidsquad/<alias>/CLAUDE.linked.v2.md`.
- **AC-4**: v1 `compose.py deploy <role>` (no `--v2`) regenerates byte-identical outputs (coexistence per [[feedback_v1_coexistence_pattern]]).
- **AC-5**: Existing A6 tests in `tests/test_compose_a6_v2.py` still pass.
- **AC-6**: New integration test: `compose.py deploy pm --v2` produces a `CLAUDE.linked.v2.md` containing the six canonical H2 slots in order.

## Test Cases
- AC1 — `deploy_alias_v2` call-site uses emit_v2_linked (live introspection or integration test producing v2 output).
- AC2 — Validation failure path: invalid L4 fixture → exception raised, no file written.
- AC3 — Successful write lands at the canonical CLAUDE.linked.v2.md path.
- AC4 — v1 deploy signature/behavior unchanged; existing A6 byte-equivalence test still passes.
- AC5 — All 29 A6 tests pass on the integration commit.
- AC6 — `compose.py deploy pm --v2` integration: output has six canonical H2 in order.

## Non-goals
- Wiring beyond A6's --v2 flag (already shipped).
- Real v2 sub-skill resolution (still uses A2a-A2e parse + emit; LLM polish is B1).
