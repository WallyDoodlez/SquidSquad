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
- PRD L1-L4 audit via DeepSeek — 2 critical, 4 major findings (L3 mislabeled, missing domain variants)
- Event model redesign: 14 event types consolidated to 5 (all L1)
- Behavioral tuning defaults locked (event-sensitivity: 10, scan-cooldown: 15m, events-atomic: true)
- Monitor tool research: events queue behind current work, events are atomic units

## Remaining Steps
- Discuss per-event instructions for the 5 events
- Human locks Decisions #11-13 (unclosed events) — then update CONTEXT.md and PR #7692
- Update PRD with new event model (5 events, all L1, no L2 event-reaction sub-skills)
- Human reviews PR #7692 and approves for execution
- Task breakdown from PRD into implementable sub-tasks for skill

## Key Decisions
- Wake model: Persistent session + Monitor tool (validated on v2.1.140 via smoke test)
- Stop signal: Event bus stop event
- Kill cycles entirely — pure event-driven, no /loop, no cycle_pre/post
- Output contract: Event closure via harness API callback (POST /events/{id}/complete)
- Terminal cleanup: Harness closes windows on clean stop
- Prerequisites: Event bus persistence, clone discovery fix, thread safety, in-flight queues
- Role terminology: PM, Technical Worker, Verifier, DM
- (Proposed) Event lifecycle: soft/hard timeouts per event class, diagnosis matrix, 3-attempt cap
- (Proposed) Idempotency: event_id markers on comments / commit trailers / API caches
- (Proposed) Closure atomicity: two-phase received→closed with fsync, agent retries non-200
- EVENT MODEL REDESIGN (2026-05-13): 5 events total, all L1:
  - assigned-to: {role, issue/pr} — all creative work assignment
  - stop-requested: {role} — graceful shutdown request
  - stopped: {role} — shutdown confirmation (agent → harness)
  - shipped: {issue/pr} — DM delivery announcement
  - version-bump: {version} — DM version announcement
- No L2 event-reaction sub-skills needed — roles handle issues from existing instructions
- L3 domain variants: no event overrides — resolved naturally by simplified model
- L4 tuning knobs: event-sensitivity (10 behind tip), scan-cooldown (15m), events-atomic (true)
- L4 tuning defaults defined at L1 (universal), L4 overrides per-project
- Reaction latency: not a knob — Monitor naturally queues, events are atomic (never interrupted)
- Chat event: future task, not in #7630 scope
