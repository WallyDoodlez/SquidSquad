# FEAT-PM-1075 Context — Add Vault Candidates to Phase 1 Research

## Scope

Research subagent adds a `## Vault Candidates` section to RESEARCH.md during Phase 1. Candidates are flagged only — PM vaults them during vault-remember using existing gate system.

## Locked Decisions

- **Section in RESEARCH.md**: Add `## Vault Candidates` after `## Recommendation`
- **Flag only, don't write**: Research agent identifies candidates, PM decides during vault-remember
- **Candidate format**: Each candidate has type (decision/pattern/learning), one-line description, and why it's vault-worthy
- **Update research prompt**: The task-intake sub-skill's Phase 1 research prompt template gets the new section

## Dev Discretion

- Exact prompt wording for the research agent
- Whether model_router research template also needs updating
- How many candidates to cap per research (suggest 3-5 max)

## Out of Scope

- Changing vault-remember logic (it already has gates for dedup, budget, freshness)
- Auto-writing vault notes from research (PM decides)
