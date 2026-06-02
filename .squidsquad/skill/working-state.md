# Working State

- **Task**: none
- **Status**: none
- **Started**:
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Completed Steps

- Cycle 1512: PRD-D/D2 (#10673) — v2 link-stage stops inlining sub-skill bodies → references only. PR #10691 pending-test. Filter scoped to (slot=instructions AND path under references/sub-skills/). Both common/ and common-events/ subtrees covered. Measured size: avg 24.9% v2/v1 (target ≤30%).
- Cycle 1511: PRD-D/D8 (#10679) row schema validation folded into catalog_parser. PR #10689 pending-test.
- Cycle 1510: PRD-D/D1 (#10672) sub-skill catalog parser shipped to PR #10688 → MERGED.
- Cycles 1502-1509: post-PRD-C wind-down + 5 quiet cycles.

## Remaining Steps

- Watch QA on PR #10691 (D2) and PR #10689 (D8).
- PRD-D queue next: D3 (#10674 catalog gate, depends on D2/MERGED), D4 (#10675), D5 (#10676), D7 (#10678).
- PRD-E queue: E1-E5 approved + actionable; E6+E7 cutover-gated.
- Open follow-ups: #10670, #10671.

## Key Decisions (latest only)

- **NEW: D2 source-migration vs code-transformation distinction.** Cycle 1512 lesson. AC1's "emit `→ run sub-skill: <name>` instead of inlining bodies" sounds like a code transformation but per TRD §3.0 it's a source-migration step + a filter — orchestrator files already author reference text verbatim; D2 only stops walking sub-skill BODIES into the instructions slot. Filter is one line of structural intent, not a parsing rewrite.
- **NEW: Path-prefix filter scoped to slot, not path alone.** Filter is (slot=instructions AND path-under-sub-skills/). This locks the intent: sub-skill bodies are runtime-loaded by reference; only the instructions slot is reference-grammar; other slots under sub-skill paths (synthetic test pattern) still flow. Both common/ and common-events/ subtrees correctly suppressed — common-events are also runtime-loaded per boot Step 3.
- **NEW: Parallel-reviewer pattern when DS is slow.** When model_router takes 10+ min, spawn a Claude subagent review IN PARALLEL with the still-running DS. Both come back; consolidate findings. Saves a cycle vs polling.
- **NEW: DS findings on filter-broadness map directly to docstring updates, not code changes.** DS flagged the filter's coverage of common-events/ as "could be wrong if common-events ever gets slot:instructions" — but they ALREADY do (6 files), and the filter is correctly suppressing them. Disposition: document the breadth as intentional rather than narrow the predicate.
- Context-budget-driven story selection beats strict queue priority for small follow-on stories
- Skip code-review for trivial fold-in stories where the diff is one new helper + tests mirroring existing pattern
- 'Never raises' for multi-failure-mode orchestrators (C5/C6/C7/C9); raise-on-failure for LLM gates (C3/C8)
- Sentinel-default dataclass fields beat None-defaults for never-raises orchestrators
- pytest.mark.xfail(strict=True) for defect-dependency tests
- Markdown catalog conventions can encode source-paths inside name columns
- Allowlist over denylist for emit-or-skip decisions
- DM DIRTY-PR workflow: git merge origin/main + force-transition past stale QA flag

- **Vault Writes This Cycle**: 0
