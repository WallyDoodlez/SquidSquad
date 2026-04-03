## FEAT-SKILL-029 — Obsidian memory layer for institutional knowledge and archives

- **Priority**: Low
- **Owner**: TBD
- **Status**: Pending
- **Description**: Add an Obsidian-compatible note vault directly in the repo (e.g. `.squidsquad/knowledge/` or a dedicated `knowledge/` directory) that serves two purposes:

  1. **Institutional knowledge base**: Store project decisions, architectural rationale, design patterns, onboarding context, and cross-session learnings in an Obsidian vault. Agents can read from and write to this vault, building up organizational memory that persists beyond conversation context windows and individual sessions. Uses Obsidian's wiki-link format (`[[note]]`) for cross-referencing.

  2. **Archive storage**: SquidSquad's archived files (completed milestone plans, old iteration logs, shipped feature planning artifacts, closed bug context) get stored here instead of being deleted or lost to git history. Browsable in Obsidian with backlinks and graph view.

  **Potential sub-skill design**: This may be implemented as a separate Claude Code skill (`squidsquad-knowledge` or similar) that SquidSquad can invoke, keeping the core skill lean. The sub-skill would handle vault initialization, note creation/linking, search, and archive ingestion.

- **Acceptance Criteria**: TBD — requires extensive scoping. May be designed as a sub-skill of SquidSquad rather than built into the core.

### Discussion

> [2026-03-29 03:00] **pm/qa**: Filed from human request. Distant future initiative — Obsidian vault as institutional knowledge layer + archive storage. Human noted this may be a sub-skill rather than core feature. Large scope, parked for later. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
> [2026-04-02 08:00] **pm/qa**: Major scope expansion from human during FEAT-SKILL-027 (designer agent) planning. The memory layer is not just archive storage — it's a **global shared memory** that ALL agents have R/W access to. Purpose: build institutional knowledge about the human's/company's values, styles, preferences, and decisions. This shapes the entire squad to be closer to the human over time. Key insight from human: dev agents need this less because code itself defines style and values, but as SquidSquad introduces more roles (designer, etc.), the need for a shared memory layer becomes critical. The designer agent is the first role where style/values can't be inferred from code alone. Priority should be reconsidered — this is becoming a platform need, not a distant future nice-to-have.
