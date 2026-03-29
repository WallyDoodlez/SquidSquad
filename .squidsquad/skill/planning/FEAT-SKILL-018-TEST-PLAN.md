# FEAT-SKILL-018 Test Plan — Maximize Subagent Usage

## Verification Criteria

### Phase 2A (Prep Subagent)
- [ ] PM template has Phase 2A section with subagent spawn instructions
- [ ] Subagent prompt specifies: read RESEARCH.md, categorize questions, suggest 3 options each, recommend order
- [ ] Phase 2A is mandatory for non-trivial features, skipped for light-mode
- [ ] Output file: PHASE2-PREP.md in planning directory
- [ ] PHASE2-PREP.md deleted after Phase 2 completes

### Phase 3 (Test Plan Subagent)
- [ ] PM template has subagent spawn for TEST-PLAN.md drafting
- [ ] Subagent prompt specifies: read RESEARCH.md + CONTEXT.md, produce test cases + smoke tests + regression risks
- [ ] PM reviews and finalizes before saving (not auto-accepted)
- [ ] Feature entry in features.md still written by PM (not subagent)

### Phase 5 (QA Subagent)
- [ ] PM template has subagent spawn for test verification
- [ ] Subagent prompt specifies: read TEST-PLAN.md, execute each test case, report PASS/FAIL
- [ ] Output file: QA-RESULTS.md in planning directory
- [ ] PM reviews results and makes final ship/back-to-dev decision (not auto-decided)

### Template Updates
- [ ] `references/agent-instructions.md` updated with subagent instructions for all 3 new phases
- [ ] Generated `.squidsquad/pm/CLAUDE.md` reflects the subagent approach
- [ ] Phases that stay inline (Phase 2B interactive, Phase 4 dev) have documented rationale

### Light Mode
- [ ] Light-mode features skip Phase 1 + Phase 2A (go straight to Phase 2 discussion)
- [ ] Light-mode features still use Phase 3 (test plan) and Phase 5 (QA) subagents
