# FEAT-SKILL-018 Context — Vault Phase 4: vault-optimize

## Scope

On-demand vault maintenance covering 5 areas: prune, consolidate, reindex, confidence decay, relevance scoring. Hybrid implementation — Python script for deterministic work, sub-skill for agent judgment calls. Decentralized execution (any idle agent), centralized notification (PM).

## Locked Decisions (human decided)

- **Triggering**: Threshold-triggered (runs when vault hits size milestones, e.g., 20+ notes). Not on-demand only, not scheduled.
- **Auto-archive**: Stale+orphan notes auto-archive. Everything else surfaces as a non-blocking question.
- **Minimum vault size**: 20 notes. Below that, skip optimization entirely.
- **Relevance scores**: Stored in separate index file (`.squidsquad/vault/.relevance-index.json`), not in frontmatter.
- **Backend**: Grep-based now, SQLite-ready interface for future #19 swap.
- **Consolidation**: Same-type only. Cross-type relationships use wikilinks.
- **Non-blocking everywhere**: Vault operations never block any agent's loop. All human prompts are skippable ("Skip for now" always available).
- **Decentralized execution**: Any agent on a quiet cycle can do vault optimization work, not just PM.
- **Pending question queue**: `.squidsquad/vault/.pending-questions` — agents write findings, PM notifies human.
- **PM notification**: PM mentions pending count in check-in, non-blocking. Tone escalates with count.
- **Status bar icon**: Shows pending vault question count with exponential urgency:
  - 1-2: `📝N` (calm)
  - 3: `📝3🔥` (1 fire)
  - 4: `📝4🔥🔥` (2 fires)
  - 5: `📝5🔥🔥🔥🔥` (4 fires)
  - 6+: `📝6🔥🔥🔥🔥🔥🔥🔥🔥` (8 fires, capped)
  - Formula: 2^(count-3) fires when count >= 3
- **Plain language prompts**: Never expose vault internals (galaxy, frontmatter, wikilinks, PARAG). Describe notes by topic. Match project domain language.
- **Human answers flow through PM**: Human tells PM, PM writes answer back, originating agent picks it up next cycle.

## Dev Discretion (dev agent can choose)

- Pending questions file format (JSON lines, markdown, etc.)
- Exact staleness threshold for auto-archive (recommend 60 days + orphan)
- Status bar icon placement and truncation behavior
- How to cap fire emojis at status bar width
- Internal naming of vault_optimize.py functions

## Side Effect Mitigations (required)

- Lock file (`.optimize-lock`) during file moves to prevent concurrent writes
- Grace period: never optimize notes created today
- Use `git mv` for all archive operations to preserve history
- Reindex always runs last (after all moves and merges)
- Test with seeded vault fixtures (current vault too small)

## Upgrade Path (required)

- New script: `references/scripts/vault_optimize.py`
- New sub-skill: `references/sub-skills/common/vault-optimize.md`
- New config section: `## Vault Optimize` with enable flag and threshold
- Status bar update: read `.pending-questions` and render icon
- Existing vaults: no migration needed, optimize runs on first threshold hit
- Graceful degradation: non-upgraded installs have no optimize, vault grows unchecked (current behavior)

## Out of Scope

- SQLite/RAG backend (#19)
- Cross-type consolidation
- Automatic schedule (threshold-triggered covers this)
- Vault evaluation and tuning (#20)
