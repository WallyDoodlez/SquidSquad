# Working State

- **Task**: none
- **Status**: none
- **Started**:
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Completed Steps

- Cycle 1516: PRD-E/E3 (#10682) — L4-write file-watch + restart-required event (Layer 2). PR #10746 pending-test. 22 tests. Pure-function surface (path classify, alias filter, recompose+emit, debounce) testable without watchdog installed; start_watcher() lazy-imports. AC5 failure-mode locked: success→restart-required, failure→compose-failed (NEVER restart-required for failed alias). DS review 2 findings addressed (F1 debouncer race→generation counter, F2 test off-by-one).
- Cycle 1515: PRD-D/D5 (#10676) — unified mode-agnostic v2 manifest. PR #10745 SHIPPED. 4 includes-v2.yml files + `_load_manifest_v2(role_name)` (no wake_mode). 36 tests. §9a byte-stability gate green.
- Cycle 1514: PRD-D/D4 (#10675) — catalog drift check (two-way orphan scan + dead-code warn). PR #10744 MERGED. 18 tests. Live catalog scan blocked by pre-existing duplicate `improvement-scan` row (filed #10743).
- Cycle 1513: PRD-E/E2 (#10681) — `last_compose_checksum` field plumbing. PR #10692 pending-test.

## Remaining Steps

- Watch QA on PR #10691 (D2), PR #10692 (E2), PR #10746 (E3).
- PRD-E queue next: E1 (#10680 — depends on E2 merged), E4 (#10683 — depends on E1), E5 (#10684 — depends on E1), E6 (#10685 cutover — depends on all).
- PRD-D queue: D3 (#10674 catalog gate — depends on D2 merged), D6 (#10677 — executes in E6 window), D7 (#10678 — depends on D2/D3 stable).
- Follow-ups: harness wiring for E3 file-watcher Observer lifecycle (deferred from E3 PR), #10670, #10671, #10743 (catalog duplicate).

## Key Decisions (latest only)

- **NEW: Lazy-import optional runtime deps so unit tests pass without them installed.** Cycle 1516 lesson. E3 needs `watchdog` for the actual file-watch in production, but the unit suite tests the pure-function surface (path classify, alias filter, recompose+emit, debouncer) which doesn't need watchdog at all. Putting `from watchdog.observers import Observer` at module top would force `pip install watchdog` to run any test in the module. Solution: lazy-import inside the function that actually uses it (`start_watcher`). Recipe: if a module has a "pure logic + thin shell over a heavy library" structure, lazy-import the library inside the shell so the pure layer stays testable everywhere.
- **Two-sided union semantics for additive manifest unification.** Cycle 1515 lesson. D5 ships an "additive includes-v2.yml" whose AC says "union of polling + events". A naïve test asserts `v2 ⊇ union` but misses accidental extras. Two-sided check (`v2 ⊇ union` AND `v2 ⊆ union`) catches both forgotten entries AND silent scope-widening. Recipe: any "union" or "equivalence" AC needs both directions tested — single-direction `<=`/`>=` is half a guard.
- **File pre-existing drift as separate issue; never let it block the gate that surfaced it.** Cycle 1514 lesson. D4 surfaced a real catalog defect (duplicate `improvement-scan` row) when run against the live catalog. The right move is file the defect (#10743) and ship D4 against fixtures, NOT delay D4 to fix the catalog first. The "tools that surface drift" and "tools that fix drift" are separate concerns — the surfacer's correctness shouldn't depend on a clean live tree. Recipe: if a new check runs against fixtures and surfaces a real-world abort against live state, file the live-state defect and ship the check.
- **PRD-E pickup order: foundation first.** Cycle 1513 lesson. Queue showed E5 first (medium) but E5 depends on E1 which depends on E2. The right pickup is the foundation (E2), not the queue-top. Reading issue bodies for "Dependencies:" before pickup keeps the gate chain from getting stuck. Recipe: when queue has multiple items at the same priority and you suspect dependencies, fetch issue bodies BEFORE picking up.
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
