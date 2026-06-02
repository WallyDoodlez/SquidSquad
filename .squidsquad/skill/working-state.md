# Working State

- **Task**: #10673 — PRD-D Story D2 (v2 link-stage references)
- **Status**: in-progress
- **Branch**: squidsquad/task/10673
- **Started**: 2026-06-02 01:35
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Completed

- v2_link_stage.py: filter `(slot=instructions AND path under references/sub-skills/) → skip` so sub-skill bodies don't inline into the instructions slot. Applied to both `_parse_all_applicable_sources` and `collect_sources_for_validation`.
- D2 tests: synthetic fixture + live-tree invariants + size invariant; 17 tests in test_d2_link_stage_references.py.
- AC verification:
  - AC1: orchestrator files already contain `→ run sub-skill: <name>` per TRD §3.0; bodies now dropped from v2 emission
  - AC2: zero `<!-- sub-skill: -->` markers; `## Boot — Mode Detection` no longer inlined; reference present
  - AC3: avg v2/v1 = 24.9% (pm 22.3% / dm 28.5% / verifier 26.2% / worker 22.7%) — under 30% target
  - AC4: v1 path untouched; v1 byte-stability test stays green
  - AC5: v2 path unchanged (`CLAUDE.linked.v2.md` via existing deploy_alias_v2)
  - AC6: A3 golden fixtures use only orchestrator files so goldens byte-stable
- Full static suite: 2583 passing, exit 0

## Remaining

- Process DS review findings (running in background)
- Commit on `squidsquad/task/10673`
- Open PR; pickup-fidelity check
- Transition in-progress → pending-test

## Key Decisions

- Filter scoped to instructions-slot only (test fixtures putting non-instructions slot under sub-skills paths continue working)
- D2 does NOT consult catalog — catalog gate is D3's job; D2's name is the existing reference text in orchestrator files (TRD §3.0 verbatim-emission contract)
- L4 ops still apply to slot content; cycle-step-targeted ops still match step headings in orchestrator content

- **Vault Writes This Cycle**: 0
