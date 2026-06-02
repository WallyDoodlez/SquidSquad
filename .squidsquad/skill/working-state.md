# Working State

- **Task**: none
- **Status**: none
- **Started**:
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Completed Steps

- Cycle 1523: PRD-A audit (#10751) — fixed ERROR (bullet-form fallback in parse_aliases_registry — was blocking ALL --v2 deploys on real installs), W1 (A2f fixture column header), W2 (qa/dev shim mirrored into table-form path), W4 (R3 explicit layer guard). W3 (--check --v2 spec/impl mismatch) deferred to PM as #10756. Also discovered + fixed collateral: D3 catalog gate (#10747 shipped) silently broke 4 test_compose_a6_v2 tests because fixtures didn't stage docs/sub-skill-catalog.md — added _stage_minimal_catalog helper. PR #10757 pending-test. Filed #10754 (B1-B7 wiring is missing story, PM scope question) per pattern-analysis lesson. DS 1 finding (silent-drop on mixed-typo bullet) fixed pre-commit with regression test. 95 in-scope tests pass, 239 in wider sweep.
- Cycle 1522: Bug fix #10743 — catalog parser blocked by 5 duplicate-name patterns. Renamed per-role variants to slash-bearing form. xfail pin removed. PR #10749 pending-test.
- Cycle 1521: PRD-D/D7 (#10678) comprehension spec + validator. PR #10748 pending-ship. 7-question spec + 16-test validator. DS 3 findings all fixed. Also re-merged E2 fourth pass.
- Cycle 1520: PRD-D/D3 (#10674) catalog gate at v2 compose time. PR #10747 SHIPPED. v2_catalog_gate.py module wired into deploy_alias_v2 between emit_v2_linked and write (atomic-write contract). Both failure modes (unresolved + missing-file) abort with multi-issue structured report. 15 tests + DS review NO_FINDINGS.
- Cycle 1519: Second-pass merge of D2 + E2 (D5/E3 landed after 1518's merge) PLUS root-cause fix. `.gitattributes` now declares `.squidsquad/.backlog-cache merge=ours` so this transient PM-regenerated counter file never conflicts during feature-branch merges of main.
- Cycle 1518: Merge-conflict resolution on D2 (#10673) + E2 (#10681). Both routed back by DM as CONFLICTING/DIRTY. Merged origin/main into both feature branches; conflicts in tests/run_tests.py (union resolution of test entries) plus .squidsquad/skill/test-output-10673.log (kept branch version). 76 tests on D2 + 44 on E2 post-merge.
- Cycle 1517: PRD-E/E3 (#10682) rework — QA route-back addressed. Wired start_watcher() into HarnessState lifecycle. PR #10746 MERGED.
- Cycle 1516: PRD-E/E3 (#10682) — L4-write file-watch + restart-required event (Layer 2). Initial pass routed back; re-shipped cycle 1517.
- Cycle 1515: PRD-D/D5 (#10676) — unified mode-agnostic v2 manifest. PR #10745 SHIPPED. 4 includes-v2.yml files + `_load_manifest_v2(role_name)` (no wake_mode). 36 tests. §9a byte-stability gate green.
- Cycle 1514: PRD-D/D4 (#10675) — catalog drift check (two-way orphan scan + dead-code warn). PR #10744 MERGED. 18 tests. Live catalog scan blocked by pre-existing duplicate `improvement-scan` row (filed #10743).
- Cycle 1513: PRD-E/E2 (#10681) — `last_compose_checksum` field plumbing. PR #10692 pending-test.

## Remaining Steps

- Watch QA/DM on PR #10692 (E2), PR #10748 (D7).
- PRD-E queue next: E1 (#10680 — depends on E2 merged), E4 (#10683 — depends on E1), E5 (#10684 — depends on E1), E6 (#10685 cutover — depends on all).
- PRD-D queue: D6 (#10677 — executes in E6 window). D2 + D3 shipped; D5/D7 pending-test.
- Follow-ups: #10670, #10671, #10750 (catalog↔source orphan cleanup), #10754 (PM scope question: missing assemble-pipeline wiring story for PRD-B), #10756 (PM scope question: --check --v2 deferral). #10752 (PRD-B audit) BLOCKED on #10754 answer. #10753 (PRD-C audit) READY to pick up next cycle — 4 real runtime bugs in L4 customization.

## Key Decisions (latest only)

- **NEW: Distinguish "shipped-but-buggy" from "shipped-but-unwired" before fixing audit findings.** Cycle 1523 lesson. PRD A/B/C audits filed as #10751/#10752/#10753 looked like 12 bugs of one family, but ⅔ were actually "registry gap" or "missing-story" (the unwired B1-B7 pipeline). Code that doesn't run can't be debugged — fixing latent paths means guessing at design decisions that belong to the unfiled wiring story. Recipe: before patching an audit finding, grep production entry points for the new module name. Empty grep = unwired = file PM scope question instead of writing code. The dead-code patches would be wasted at best, design-divergent at worst. Saved as [[feedback-audit-pattern-shipped-unwired]].
- **When merge conflicts recur on transient state files, fix at .gitattributes layer, not by hand-merging on every loop.** Cycle 1519 lesson. D2 + E2 chased main through 3 DM route-backs; every conflict was `.squidsquad/.backlog-cache` (PM-regenerated counter file). Hand-merging works once; the third round makes it clear that the chase pattern is structural. Adding `merge=ours` to .gitattributes for `.backlog-cache` resolves all future loops in zero coordination overhead. Recipe: if you hit the same auto-merge conflict twice across cycles on a file that's machine-regenerated, fix .gitattributes rather than re-doing the merge.
- **If the issue body names the harness as the actor, harness wiring is in-scope — not a follow-up.** Cycle 1517 lesson. E3's issue body's GOAL paragraph said "harness file-watches `.squidsquad/project/`..." but I shipped the module without wiring it into harness.py, framing the wiring as "separate follow-up." QA routed back citing `feedback_no_ship_with_gaps`: "Any QA gaps = back to dev, not 'noted for follow-up'." Recipe: when an AC says "X does Y", "X" is in-scope; deferring the wiring means shipping a no-op surface. Pre-check before pending-test: do the named actors (harness, scheduler, watcher) actually invoke the new module? If not, wire it now or push back via PM to amend the AC.
- **Lazy-import optional runtime deps so unit tests pass without them installed.** Cycle 1516 lesson. E3 needs `watchdog` for the actual file-watch in production, but the unit suite tests the pure-function surface (path classify, alias filter, recompose+emit, debouncer) which doesn't need watchdog at all. Putting `from watchdog.observers import Observer` at module top would force `pip install watchdog` to run any test in the module. Solution: lazy-import inside the function that actually uses it (`start_watcher`). Recipe: if a module has a "pure logic + thin shell over a heavy library" structure, lazy-import the library inside the shell so the pure layer stays testable everywhere.
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
