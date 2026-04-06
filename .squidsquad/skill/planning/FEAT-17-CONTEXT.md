# FEAT-17 Context — Vault Phase 3: vault-remember + End-of-Cycle Reflection

## Scope

Add a `vault-remember` step to every agent's Ralph Loop that promotes cycle insights to vault notes. The system uses maximum determinism: Python-scripted gates for all mechanical checks, LLM judgment only for reusability assessment, categorization, and content writing. Also seeds the missing `human-profile.md` area note.

**Delivers:**
1. `vault_remember.py` — deterministic gate script (quiet-cycle check, write counter, dedup search, BRIEFING.md budget, effective confidence calculation, note count guard)
2. `vault-remember.md` — new common sub-skill defining the end-of-cycle reflection step with structured 5-category prompt
3. `cycle.py is-quiet` — implement the documented but missing command
4. `vault_check.py dedup-check` — new command for near-duplicate detection
5. human-profile.md seeding from existing BRIEFING.md/memory data
6. Config additions for vault-remember settings
7. Entry file changes for all agent roles (dev, pm, dm)

## Locked Decisions (human decided)

- **Enabled by default**: Yes. New installs get vault-remember active from cycle 1. Users can disable via `vault-remember: no` in config.md. Why: deterministic gates prevent noise; opt-in would hide the feature.

- **All agents from day one**: Dev, PM, and DM all get vault-remember. Same sub-skill include, same budget. No phased rollout. Why: DM insights about docs/releases are valuable, and the sub-skill is identical — no extra implementation work.

- **human-profile.md seeding**: Pre-seed from known data in BRIEFING.md and existing memory/feedback files with `confidence: medium`. Then present to human for review. Why: immediate value without blocking, but human gets final say on accuracy.

- **Write budget**: Max 2 writes per cycle normally. Allow burst to 3 if all candidates are high-priority (human preferences or architectural decisions). Why: prevents bloat while not losing critical insights on productive cycles.

- **Overflow handling**: Accept the loss for items beyond budget. Overflow candidates noted in iteration log only. Start simple — add deferred-item tracking later if monitoring shows consistent loss of high-value insights.

- **Confidence decay**: Automatic, calculated at read time. Base confidence stays in frontmatter unchanged. `vault_remember.py effective-confidence <note-path>` computes effective level based on age since last update. No file modification for decay — the original confidence is always preserved. Re-confirming a note (any vault-update) resets the age. Notes tagged `evergreen` exempt from decay. Why: self-maintaining, reversible, clean frontmatter.

- **Designer agent**: No special handling. The 5 reflection categories (decisions, patterns, learnings, human preferences, project context) already cover design. Agents can use the existing escape hatch for new galaxy prefixes if needed.

## Dev Discretion (dev agent can choose)

- Implementation details of `vault_remember.py` (function signatures, internal structure)
- Exact keyword matching algorithm for dedup-check (TF-IDF, simple word overlap, etc.)
- How to count tokens for BRIEFING.md budget (words * 1.3 approximation or another heuristic)
- Effective confidence decay curve (linear, step-based, etc.) — as long as the interface returns high/medium/low
- Unit test structure and organization for new scripts
- Whether to add `is-quiet` as a new function in cycle.py or a separate module

## Side Effect Mitigations (required)

- **Config gate**: vault-remember sub-skill MUST check `vault-remember: yes/no` in config.md before executing. If key is missing, default to `yes` (enabled by default). If `no`, skip entirely.
- **Graceful degradation**: If `vault_remember.py` script doesn't exist (pre-upgrade install), the sub-skill text in CLAUDE.md references it but the script call fails — agent must catch the error and skip vault-remember for that cycle, not crash.
- **Step numbering**: Adding vault-remember between iteration-log and git-commit shifts step numbers. Dev agent: Step 4b (between 4 and 5). PM agent: Step 8b (between 8 and 9). All existing step references in documentation must be audited.
- **Context pressure exits**: Accepted that insights from context-pressure-exit cycles may be lost. Iteration log preserves raw data. No deferred-reflection mechanism in Phase 3.
- **Manifest update**: `references/sub-skills/manifest.md` must include the new vault-remember sub-skill entry.

## Upgrade Path (required)

- **New files**: `references/sub-skills/common/vault-remember.md`, `references/scripts/vault_remember.py`, `references/vault-templates/human-profile-seed.md`
- **Modified files**: `references/sub-skills/roles/dev-agent.md`, `references/sub-skills/roles/pm-agent.md`, `references/sub-skills/roles/dm-agent.md` (add `{{include: common/vault-remember}}`), `references/scripts/vault_check.py` (add dedup-check), `references/scripts/cycle.py` (implement is-quiet)
- **Config additions**: `## Vault Remember` section with Enabled, Writes Per Cycle, BRIEFING Token Budget, Confidence Decay Days
- **Regenerate**: `compose.py deploy` for all active roles after upgrade
- **Idempotent seed**: Create `vault/areas/human-profile.md` if missing (vault-init already specifies this but it was never done)
- **Graceful degradation**: Non-upgraded installs simply don't have the sub-skill or script. No errors, no crashes.

## Out of Scope

- SQLite/RAG backend (Phase 5, #19)
- Deferred reflection on context pressure exits (future follow-up if needed)
- Improvement scan → vault note bridge (keep separate pipelines)
- Vault pruning/archival of old notes (Phase 4, #18)
- Cross-agent memory propagation beyond shared vault (already handled by git)
- Batch rename of existing vault notes
