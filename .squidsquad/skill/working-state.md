# Working State

- **Task**: #8979
- **Status**: in-progress (Phase 1 data model shipped via PR #9010; #8915 back to pending-test)
- **Started**: 2026-05-18 15:33
- **Last Processed Event ID**: 9d7c2489

## Completed Steps
- Cycle 1141: #8979 Phase 1 data model — intent_set_at field + persistence + 7 flip sites + two-case migration + idempotence guards. PR #9010, 18 tests, 4-iter review (14 fixes).
- Cycle 1142: #8915 QA-rejection fix — wired event-mode L1 fragments into all 4 includes-events.yml manifests AND all 4 instructions.md templates (compose.py is template-driven). PR #8996 commit f8c88dd9, 48 wiring tests, 2-iter review (5 fixes incl. critical template-vs-manifest distinction). Re-transitioned #8915 to pending-test.

## Remaining Steps for #8979
- Phase 1 remainder: 60s force-kill safety net in update_health; /quit instruction fragment in common/self-restart.md (or new graceful-stop.md) + recompose; context-pressure /restart routing in cycle_post.py.
- Phase 2: sentinel cleanup in scripts.
- Phase 3: operator entry-point convergence.
- Phase 4: .health legacy fragment edits + recompose.
- Phase 5: upgrade-path cleanup logic.

## Key Decisions
- Cycle 1142 detour fixed the QA blocker on #8915 before continuing #8979 — QA-rejected items take precedence.
- compose.py is template-driven, not manifest-driven — manifest entries are an allow-list filter; the template instructions.md drives composition.
- Following CONTEXT-4792.md §9 sequencing for #8979 — 4-PR split.
