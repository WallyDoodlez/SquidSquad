# FEAT-SKILL-018 Research — Maximize Subagent Usage Across Planning Phases

## Executive Summary

Currently only Phase 1 (Research) uses a subagent. Phases 2, 3, and 5 can benefit from subagent delegation. Phase 4 stays with dev agent. Key insight: PM's bottleneck is artifact generation and verification, not decision-making — perfect for subagents.

## Per-Phase Delegation Plan

| Phase | Current | Proposed | Subagent Task |
|-------|---------|----------|---------------|
| 1 Research | Subagent ✅ | Keep as-is | Impact analysis, side effects, edge cases |
| 2 Discussion | Inline | Add Phase 2A prep subagent | Analyze research, suggest questions + 3 options each, recommend order |
| 3 Planning | Inline | Subagent drafts TEST-PLAN.md | Design test cases from RESEARCH + CONTEXT |
| 4 Execution | Dev agent ✅ | Keep as-is | Dev implements |
| 5 QA | Inline | Subagent runs verification | Execute test cases, report PASS/FAIL |

## Phase 2A (NEW — Prep Subagent)

Before interactive discussion, spawn subagent to:
1. Categorize research findings (must-ask-human vs PM-can-answer)
2. Recommend question order (highest impact first)
3. Suggest 3 options per question with PM recommendation
4. Draft decision templates for CONTEXT.md

PM uses output as a script for AskUserQuestion calls. Phase 2B (interactive) stays with PM.

## Phase 3 (NEW — Test Plan Subagent)

Subagent reads RESEARCH.md + CONTEXT.md + feature description, produces TEST-PLAN.md with:
- Test cases (happy path + edge cases + regression)
- Smoke tests
- Regression risks

PM reviews, adjusts, finalizes. Feature entry in features.md stays with PM.

## Phase 5 (NEW — QA Subagent)

Subagent reads TEST-PLAN.md, executes verification (bash, file reads, grep), produces QA-RESULTS.md. PM reviews results and makes final ship/back-to-dev decision.

## Context Pressure Analysis

- PM savings: ~5000-8000 tokens per feature (offloaded to subagents)
- Subagent cost: ~4500 tokens total (4 subagent spawns)
- Net benefit: PM context shifts from "analyzing files" to "making decisions"

## Risks

| Risk | Mitigation |
|------|-----------|
| Poor subagent output | PM reviews + adjusts; can regenerate |
| Phase 2A prep doesn't match human thinking | Prep is optional; PM adapts |
| QA subagent misses failure | PM still reviews results |
| API cost (4 calls/feature) | Acceptable for Medium+ priority; light mode skips some |

## Open Questions

1. Phase 2A prep: mandatory or optional? Recommend: optional (PM decides per-feature)
2. Delete prep files after Phase 2? Recommend: yes, scratch files
3. QA failures: auto-file Discussion or PM decides? Recommend: PM decides (Option A)
4. TEST-PLAN.md: subagent drafts or PM writes? Recommend: subagent drafts, PM finalizes
5. 4 subagents/feature acceptable? Recommend: yes for non-trivial; light mode skips Phase 1 + 2A
