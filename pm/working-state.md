# Working State

- **Task**: #7630 (EPIC: Event-driven agent architecture)
- **Status**: in-progress
- **Phase**: test-planning FEAT-PM-7630
- **Started**: 2026-05-12 18:31
- **Last Processed Event ID**: e7d24eda

## Completed Steps
- Human approved for planning
- Phase 1: Research (RESEARCH.md written)
- Phase 2A: Discussion prep (PHASE2-PREP.md written)
- Phase 2: Discussion with human (CONTEXT.md — 10 locked decisions)
- Phase 2 approval gate passed
- DeepSeek gap review completed (GAP-REVIEW.md)
- Phase 2B: Re-research with updated scope (RESEARCH.md v2 written)
- Phase 3: Test plan (46 items — Claude + DeepSeek cross-referenced)
- Phase 3B: Draft PR #7692 created with all planning artifacts
- PRD created (DeepSeek-generated, PM-corrected for locked decisions)
- L1-L4 event reaction mapping research + PRD/CONTEXT update
- Filed #7690 (setup flow update), #7691 (statusline redesign)
- Closed #510, #5159 (superseded by #7630)
- Bug filed: #7637 (stale stopping intent — skill picked up, at pending-test)
- Phase 3C: Monitor tool smoke test (MONITOR-SMOKE-RESULT.json) — 4/4 async events confirmed on v2.1.140
- Unclosed-event handling design proposed (Decisions #11-13: lifecycle/timeouts, idempotency, two-phase closure)

## Remaining Steps
- Human locks Decisions #11-13 (unclosed events) — then update CONTEXT.md and PR #7692
- Human reviews PR #7692 and approves for execution
- Task breakdown from PRD into implementable sub-tasks for skill

## Key Decisions
- Wake model: Persistent session + Monitor tool (validated on v2.1.140 via smoke test)
- Stop signal: Event bus stop event
- Kill cycles entirely — pure event-driven, no /loop, no cycle_pre/post
- Output contract: Event closure via harness API callback (POST /events/{id}/complete)
- Scan trigger: scan-due event on 10-min idle timeout
- Terminal cleanup: Harness closes windows on clean stop
- Prerequisites: Event bus persistence, clone discovery fix, thread safety, in-flight queues
- Event reactions follow L1-L4 layers (soul = personality only)
- Harness filters 18 mechanical events; agents see 14 creative
- Role terminology: PM, Technical Worker, Verifier, DM
- (Proposed) Event lifecycle: soft/hard timeouts per event class, diagnosis matrix, 3-attempt cap
- (Proposed) Idempotency: event_id markers on comments / commit trailers / API caches
- (Proposed) Closure atomicity: two-phase received→closed with fsync, agent retries non-200
