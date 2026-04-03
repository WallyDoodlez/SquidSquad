# FEAT-SKILL-029 Context — Obsidian Memory Layer (PARAG Vault)

## Scope

Git-tracked Obsidian-compatible memory vault giving ALL agents shared R/W access to institutional knowledge. Follows COG (Claude-Obsidian-Git) philosophy — plain markdown, git-native, no infrastructure. Uses **PARAG** structure (Projects, Areas, Resources, Archives, Galaxy) — inbox dropped since agents classify directly.

**In scope:**
- PARAG vault structure under `.squidsquad/vault/`
- Templates per folder with YAML frontmatter
- Entity model: human profile, company context, design system, code conventions, decisions, patterns, learnings, styles
- 6 composable vault skills: vault-init, vault-create, vault-update, vault-search, vault-check, vault-remember
- vault-optimize as on-demand maintenance
- BRIEFING.md as always-loaded context file (~50 lines, injected at boot)
- Auto-generated README.md for Obsidian homepage
- Wikilinks for bidirectional relationships
- Confidence field (high/medium/low) on every note
- Append-only changelog per note
- Built as common sub-skills under FEAT-SKILL-030 architecture

**Implementation phases:**
- Phase 1: vault-init + structure + templates + vault-create + BRIEFING.md
- Phase 2: vault-update + vault-search (grep) + vault-check
- Phase 3: vault-remember (hooks in all agents, 3 captures/cycle max)
- Phase 4: vault-optimize (full vault sweep, staleness detection, README refresh)

## Locked Decisions (human decided)

- **Grep now, SQLite hybrid RAG later**: vault-search uses ripgrep + wikilink traversal for Phase 1-3. Interface abstracted so SQLite hybrid RAG (FEAT-SKILL-062) can slot in later without changing agent code.
- **Hybrid context injection**: BRIEFING.md (~50 lines active context) injected at session start via hooks. Deeper vault queries happen on-demand during work.
- **BRIEFING.md only as core file**: No USER.md or MEMORY.md trio. BRIEFING.md covers active priorities, recent decisions, human preferences summary. SOUL.md is separate (FEAT-SKILL-059). areas/human-profile.md serves as the detailed human profile.
- **Auto-maintained links**: vault-check parses note content and updates the `links` frontmatter field automatically. No manual link curation.
- **Confidence field**: Every note gets `confidence: high | medium | low`. Human-confirmed = high, agent-observed = medium, agent-inferred = low. Deep dreaming (prune/purge/consolidate using confidence) deferred to FEAT-SKILL-062 when hybrid RAG enables semantic understanding.
- **500 line max for galaxy, no limit for areas**: Galaxy notes are atomic (one idea). vault-check warns at >500 lines. Area notes (human profile, design system) grow freely.
- **Bare wikilinks only**: Always `[[note-name]]`, no Obsidian alias syntax. Simplifies grep-based link tracking.
- **Auto-generated README.md**: vault-init creates it, vault-optimize refreshes with stats (note count, recent updates, health).
- **Drop inbox — PARAG not IPARAG**: Agents are LLMs that can classify at capture time. vault-remember writes directly to the correct folder (projects/, areas/, resources/, archives/, galaxy/). No inbox processing step needed.
- **No daily logs**: Existing iteration logs per agent + vault-remember captures are sufficient. No separate daily log pipeline.
- **Vault and MEMORY.md intentionally separate**: Claude Code's `.claude/projects/*/MEMORY.md` = per-conversation quick notes. Vault = institutional knowledge. Different purposes, no sync.
- **vault-remember as hooks in each agent**: Fires after work steps in every agent's Ralph Loop. Rate-limited to 3 captures per cycle. Distributed capture — each agent writes what it observes. No dedicated vault-agent.
- **End-of-cycle reflection (deterministic)**: On every non-quiet cycle, vault-remember fires one final time at cycle end asking "what did I learn this cycle?" This is not reactive (triggered by an event) but deterministic (triggered by cycle completion). Captures meta-knowledge: process learnings, human preference signals, codebase patterns, pitfalls discovered, what worked/didn't. Goes to `galaxy/learning-*` notes. This is part of vault-remember Phase 3, not a separate feature.

## Dev Discretion (dev agent can choose)

- Exact BRIEFING.md format and what constitutes "active context"
- Template field ordering and optional vs required fields
- vault-check warning thresholds beyond the 500-line galaxy limit
- How vault-remember hook integrates into each role's specific Ralph Loop steps
- Filename conventions for galaxy notes (prefix-based: decision-*, pattern-*, learning-*, style-*)
- vault-search result formatting
- How vault-optimize groups findings (severity levels, auto-fixable vs needs-review)

## Side Effect Mitigations (required)

- All agent templates gain vault sub-skill includes — template size will grow
- PM template gains BRIEFING.md injection at boot via hooks
- vault-remember hooks must not bloat cycle time — rate limit enforced
- Git repo size grows with vault notes — acceptable for markdown files
- vault-check runs on every write — must be fast (single note + 2-hop neighborhood)
- Obsidian `.obsidian/` config directory must be gitignored

## Upgrade Path (required)

- `/squidsquad-upgrade` creates `.squidsquad/vault/` with PARAG structure and templates
- Seeds BRIEFING.md from existing config.md data
- Seeds areas/human-profile.md from any existing context
- Regenerates all agent templates with vault sub-skills composed in
- Existing installs: non-destructive — vault is additive, nothing removed
- Vault data is never overwritten by upgrade — templates and structure only

## Out of Scope

- **Inbox folder** — dropped, agents classify directly
- **Daily logs + reflection pipeline** — existing iteration logs sufficient
- **SQLite hybrid RAG search** — FEAT-SKILL-062
- **Deep dreaming (prune/purge/consolidate)** — FEAT-SKILL-062
- **SOUL.md** — FEAT-SKILL-059
- **Sync with Claude Code MEMORY.md** — intentionally separate
- **Cross-project vaults** — future consideration
- **Dedicated vault-agent** — hooks in each agent instead
