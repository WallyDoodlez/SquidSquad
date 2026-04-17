# FEAT-PM-475 Context — Token Efficiency Audit

## Scope

Reduce token consumption across all composed CLAUDE.md agent templates by ~11% (~4,082 tokens) through three targeted changes: removing dead code (boot-remote-agents from non-PM roles), extracting reference data (Label Taxonomy), and condensing reference-heavy sections (vault-protocol). No behavioral changes to agents — only instruction density changes.

## Locked Decisions (human decided)

- **Validation gate**: Comprehension testing — spawn a fresh agent per changed sub-skill, quiz it on the trimmed instructions to verify it still knows what to do. Human emphasized testing must be very thorough.
- **Boot-remote-agents**: Remove from non-PM role includes. Saves 640 words across 4 roles. Zero behavioral risk (PM-only gate was already preventing execution).
- **Label Taxonomy**: Extract from tracker-protocol to a reference file (e.g. `references/docs/label-taxonomy.md`). Agents can `cat` if needed. tracker.py enforces labels programmatically. Saves ~1,500 words across 5 roles.
- **Vault-protocol**: Compress inline — condense entity model table, search modes, vault-check Level 2 into terse summaries pointing to a reference file for details. Keep as one sub-skill. Saves ~1,000 words across 2 roles.
- **Subagent prompts**: Keep as-is. Quality of subagent output is more important than word savings.

## Dev Discretion (dev agent can choose)

- Exact wording of condensed vault-protocol sections (as long as comprehension tests pass)
- Reference file naming and location within `references/`
- Whether to use `cat` instruction or just remove the inline content with no explicit read instruction (tracker.py already handles labels)

## Side Effect Mitigations (required)

- Prohibitions section must NOT be touched — safety-critical
- Zero-gap gate and approval gates must NOT be touched — process-critical
- All existing tests must pass after changes
- Comprehension testing must be run per changed sub-skill BEFORE shipping
- compose.py deploy-all must be run after sub-skill changes to regenerate CLAUDE.md files

## Upgrade Path (required)

- Existing installs: `compose.py deploy-all` regenerates templates. No manual migration.
- No new config values. No new files in `.squidsquad/` (reference files go in `references/`).
- Graceful degradation: old templates continue working, just less efficient.

## Out of Scope

- Medium-risk changes (condensing tracker-protocol further, trimming task-intake process) — deferred to a follow-up task after low-risk changes are validated
- Script output optimization — research confirmed scripts are already lean
- Planning artifact template changes — already concise
- vault-protocol-slim changes — already minimal at 44 lines
