# FEAT-SKILL-018 Context — Maximize Subagent Usage Across Planning Phases

## Scope
Add subagent delegation to Phases 2, 3, and 5 of the Feature Intake Process. Phase 1 already uses a subagent. Phase 4 stays with dev agent.

## Locked Decisions

### Q1: Phase 2A prep — mandatory for non-trivial
**Decision**: Auto-spawn Phase 2A prep subagent for all non-trivial features. Light-mode (trivial) features skip it.
**Why**: Ensures PM always enters discussion prepared. Trivial features don't need it.

### Q2: Prep files — delete after Phase 2
**Decision**: PHASE2-PREP.md is a scratch file, deleted after Phase 2 completes. CONTEXT.md captures final decisions.
**Why**: Less artifact clutter. Prep files are intermediate, not permanent records.

### Q3: QA failures — PM decides
**Decision**: QA subagent reports results. PM reviews and manually decides: ship, send back to dev, or consult human.
**Why**: PM has oversight on quality decisions. Prevents auto-escalation mishaps.

### Q4: TEST-PLAN.md — subagent drafts, PM finalizes
**Decision**: Phase 3 subagent reads RESEARCH + CONTEXT, produces TEST-PLAN.md draft. PM reviews, adjusts, saves final version.
**Why**: Best of both worlds — subagent suggests comprehensive coverage, PM applies judgment.

### Q5: Cost — 4 subagents per feature acceptable
**Decision**: Up to 4 subagent spawns per feature (Research + Phase2A-prep + TestPlan + QA). Light-mode may use fewer.
**Why**: ~4500 tokens total, saves ~5000-8000 of PM context. Net positive.

## Dev Discretion Areas
- Exact subagent prompt wording for Phases 2A, 3, and 5
- Whether QA-RESULTS.md is deleted after shipping or kept
- How to handle subagent timeout or failure (retry once or fall back to inline)
- Whether to add quality guidelines to subagent prompts
