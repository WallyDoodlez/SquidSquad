# Working State

- **Task**: none
- **Status**: none
- **Started**:
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Completed Steps

- Cycle 1513: PRD-E/E2 (#10681) — `last_compose_checksum` field plumbing in `.harness-state.json` shipped to pending-test on PR #10692. Foundational dep for E1 + E5. 11 tests + 2585 static passing.
- Cycle 1512: PRD-D/D2 (#10673) — v2 link-stage filter for sub-skill bodies. PR #10691 pending-test. avg 24.9% v2/v1 size.
- Cycle 1511: PRD-D/D8 (#10679) — row schema validation folded into catalog_parser. PR #10689 pending-test.
- Cycle 1510: PRD-D/D1 (#10672) — sub-skill catalog parser. PR #10688 MERGED.

## Remaining Steps

- Watch QA on PR #10691 (D2), PR #10689 (D8), PR #10692 (E2).
- PRD-E queue next: E1 (#10680 boot-time freshness check — depends on E2 merged), E3 (#10682), E4 (#10683), E5 (#10684 — depends on E1).
- PRD-D queue: D3 (#10674 catalog gate — depends on D2 merged), D4 (#10675), D5 (#10676), D7 (#10678).
- Open follow-ups: #10670, #10671.

## Key Decisions (latest only)

- **NEW: PRD-E pickup order: foundation first.** Cycle 1513 lesson. Queue showed E5 first (medium) but E5 depends on E1 which depends on E2. The right pickup is the foundation (E2), not the queue-top. Reading issue bodies for "Dependencies:" before pickup keeps the gate chain from getting stuck. Recipe: when queue has multiple items at the same priority and you suspect dependencies, fetch issue bodies BEFORE picking up.
- D2 source-migration vs code-transformation distinction (cycle 1512)
- Path-prefix filter scoped to slot, not path alone (cycle 1512)
- Parallel-reviewer pattern when DS is slow (cycle 1512)
- Context-budget-driven story selection beats strict queue priority for small follow-on stories
- Skip code-review for trivial fold-in stories where the diff mirrors an existing pattern
- 'Never raises' for multi-failure-mode orchestrators; raise-on-failure for LLM gates
- Sentinel-default dataclass fields beat None-defaults
- pytest.mark.xfail(strict=True) for defect-dependency tests
- Allowlist over denylist for emit-or-skip decisions

- **Vault Writes This Cycle**: 0
