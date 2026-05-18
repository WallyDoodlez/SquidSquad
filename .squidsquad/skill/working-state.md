# Working State

- **Task**: #8979
- **Status**: in-progress
- **Started**: 2026-05-15
- **Last Processed Event ID**: 9d7c2489

## Completed Steps

- Phase 1 (data model + force-kill safety net + cooperative-termination routing): shipped on PR #9010 across 3 commits.
- Phase 2 §5.2 (boot_remote.py legacy-sentinel cleanup): commit b340b011.
- Phase 2 §5.3 (reboot_agent.py gut + SIGKILL parity + deprecation stub): commit e30cdd1a.
- Phase 2 §5.5 (cycle_pre.py `harness_status` field + stale-comment refresh): commit b02c86a2.

## Remaining Steps

- Phase 2 §5.4: health_check.py trim (delete `.stop` + `.health` + `.pid` reads; keep `.claude-pid`; docstring note about offline fallback).
- Phase 2 §5.6: cycle_post.py residuals tidy (most done in Phase 1).
- Phase 2 §5.1: harness.py legacy-sentinel cleanup-on-boot (`.stop` / `.restart` / `.health` unlinks before first update_health poll).
- Phase 3: operator entry-point convergence (start_team.py thin shim, boot_remote main() removal, reboot_agent main() removal).
- Phase 4: `.health` legacy fragment edits in references/sub-skills/common/agent-lifecycle.md + recompose.
- Phase 5: upgrade-path cleanup logic on harness boot.

## Key Decisions

- Cycle 1135–1140: #8915 (event-mode L1 base) shipped to pending-test on PR #8996 — 6 commits, 23 review iterations, 38+ correctness fixes. Follow-ups filed: #8998 (manifest wiring + fixture regen), #8999 (integration tests + live CQ run).
- Three high-priority approved tasks (#8950, #8917, #8916) waiting; PM should clarify priority order before pickup.
- #4792 / #8979 Phase 2 is being shipped as a single rolling PR (#9010) with cohesive review-iterated commits per §-section, keeping each section small enough for a single DeepSeek pass.
- §5.5 `harness_status` is strictly informational — fail-open, no gating — so cycle_pre stays robust if the harness is down or slow.
