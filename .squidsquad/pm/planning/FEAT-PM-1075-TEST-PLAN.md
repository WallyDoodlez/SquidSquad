# FEAT-PM-1075 Test Plan — Vault Candidates in Research

## Test Cases

### TC-1: RESEARCH.md template includes Vault Candidates section
- **Precondition**: Read task-intake sub-skill
- **Steps**: Check the RESEARCH.md format template in task-intake
- **Expected**: `## Vault Candidates` section present after `## Recommendation`
- **Verification**: grep for "Vault Candidates" in task-intake sub-skill

### TC-2: Research agent prompt requests vault candidates
- **Precondition**: Read research prompt in task-intake or model_router template
- **Steps**: Check prompt includes instruction to identify vault-worthy discoveries
- **Expected**: Prompt mentions vault candidates with format guidance
- **Verification**: grep for "vault" in research prompt section

### TC-3: Candidate format is structured
- **Precondition**: Sample RESEARCH.md with Vault Candidates section
- **Steps**: Check each candidate has type, description, rationale
- **Expected**: Format: `- **Type**: [decision/pattern/learning] — [description] — **Why**: [rationale]`
- **Verification**: Manual review of format

### TC-4: Cap on candidates
- **Precondition**: Research prompt
- **Steps**: Check if prompt limits candidates
- **Expected**: Max 3-5 candidates per research
- **Verification**: grep for limit/max in prompt

## Smoke Tests
- [ ] task-intake sub-skill contains "Vault Candidates" in RESEARCH.md template
- [ ] Research prompt mentions vault candidates

## Regression Risks
- Research output format change breaking existing parsing (if any)

## Comprehension Questions
### CQ-1: Where do vault candidates appear in the planning lifecycle?
- **Files**: task-intake sub-skill
- **Expected**: In Phase 1 RESEARCH.md output, after Recommendation. PM processes them during vault-remember, not the research agent.
