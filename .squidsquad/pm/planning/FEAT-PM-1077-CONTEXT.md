# FEAT-PM-1077 Context — Comprehension Testing for QA

## Scope

Standardize comprehension testing as a QA verification method for template/instruction changes. Add it to the QA verification sub-skill and the PM test plan template. Comprehension testing = spawn a fresh agent, point it at the modified files, quiz it on expected behavior.

## Locked Decisions (human decided)

- **Agent prompt style**: Neutral with file-scope constraint — "Read these files and answer ONLY from what you find." Prevents training-data contamination. Agent must derive answers from the actual template.
- **Spawn strategy**: Adaptive — single spawn by default, split into multiple spawns when 4+ sub-skills are affected by the change. Balances cost vs thoroughness.
- **Results format**: Separate section `## Comprehension Tests` within QA-RESULTS.md. All results in one file, unified zero-gap gate.

## Dev Discretion (dev agent can choose)

- Exact prompt template wording for the comprehension agent
- How QA determines whether a task needs comprehension testing (heuristic for "touches LLM-consumed instructions")
- Whether to include a "confidence" field in comprehension results
- Exact threshold for the 4+ sub-skill split trigger

## Side Effect Mitigations (required)

- Comprehension testing is conditionally mandatory — only for tasks that touch CLAUDE.md, sub-skills, SOUL.md, or other LLM-consumed instruction files
- Tasks that only touch scripts/config skip comprehension testing (they use unit tests)
- 100% pass rate required (zero-gap gate applies)
- A comprehension test failure is a legitimate finding — either the implementation is wrong or the instructions are ambiguous (both worth catching)
- Pair comprehension tests with at least one real smoke test for happy path

## Upgrade Path (required)

- Template changes only: QA verification sub-skill + PM test plan template
- compose.py deploy-all regenerates all CLAUDE.md files
- No new config values, scripts, or migration steps
- Graceful degradation: old QA templates still verify, just without comprehension step

## Out of Scope

- Automated comprehension question generation (PM writes them in Phase 3)
- Changes to the Agent tool itself
- Comprehension testing for non-template changes
- Token cost optimization beyond the adaptive spawn strategy
