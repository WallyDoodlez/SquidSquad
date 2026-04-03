## FEAT-SKILL-029 — Obsidian memory layer for institutional knowledge and archives

- **Priority**: High
- **Owner**: TBD
- **Status**: Planning
- **Description**: Git-tracked Obsidian-compatible memory vault that gives ALL agents shared R/W access to institutional knowledge. Follows the **COG (Claude-Obsidian-Git)** philosophy — plain markdown, git-native, no infrastructure, agent-agnostic. Uses **IPARAG** organizational structure adapted for SquidSquad's multi-agent context.

  **Core purpose**: Build institutional knowledge about the human's/company's values, styles, preferences, decisions, and patterns. Shapes the entire squad to be closer to the human over time. All agents read from and write to the same vault.

  **IPARAG structure (adapted for SquidSquad):**
  ```
  .squidsquad/vault/
  ├── inbox/              # Unprocessed captures from any agent
  ├── projects/           # Active project context, goals, constraints
  ├── areas/              # Ongoing concerns: design system, code conventions,
  │                       # human preferences, company values, team culture
  ├── resources/          # Reference material, external docs, research
  ├── archives/           # Shipped features, closed decisions, historical context,
  │                       # old planning artifacts, completed iteration logs
  └── galaxy/             # Atomic knowledge notes (Zettelkasten):
                          # individual decisions, patterns, learnings, styles
  ```

  **Entity model (SquidSquad-specific):**
  | Entity | Vault Location | Purpose |
  |--------|---------------|---------|
  | Human profile | `areas/human-profile.md` | Preferences, values, communication style, decision patterns |
  | Company/team context | `areas/company-context.md` | Culture, standards, brand guidelines |
  | Design system | `areas/design-system.md` | Colors, tokens, typography, component patterns |
  | Code conventions | `areas/code-conventions.md` | Style, patterns, architecture decisions |
  | Project context | `projects/{project-name}.md` | Goals, constraints, architecture, tech stack |
  | Decisions | `galaxy/decision-*.md` | Individual architectural/design/process decisions |
  | Patterns | `galaxy/pattern-*.md` | Recurring patterns, conventions, established approaches |
  | Learnings | `galaxy/learning-*.md` | Lessons learned, bug root causes, what worked/didn't |
  | Styles | `galaxy/style-*.md` | Visual style preferences, writing tone, code style |

  **Key features:**
  1. **Wikilinks** (`[[note-name]]`) for bidirectional relationships between notes
  2. **YAML frontmatter** per note for structured metadata (type, tags, dates)
  3. **Changelog per note** — append-only audit trail, git provides full diff history
  4. **Templates** per folder — enforce consistent structure
  5. **Graph traversal via grep** — single-hop (`grep [[entity]]`), multi-hop (sequential grep + follow links)
  6. **Two-level integrity** — Level 1 (per-note + 2-hop neighborhood) on every write, Level 2 (full vault sweep) on demand
  7. **Auto-remember** — agents proactively capture decisions, patterns, learnings without being asked
  8. **Browsable in Obsidian** — team can use Obsidian app for visual graph exploration

  **Skill inventory (sub-skills or slash commands):**
  | Skill | Purpose |
  |-------|---------|
  | `/vault-init` | One-time vault setup |
  | `/vault-create` | Create note from template |
  | `/vault-update` | Update note + changelog |
  | `/vault-search` | Graph-like query via grep + wikilink traversal |
  | `/vault-check` | Level 1 integrity (per-note + neighborhood) |
  | `/vault-optimize` | Level 2 full vault sweep |
  | `/vault-remember` | Auto-detect noteworthy context and persist |

  **Implementation phases:**
  - **Phase 1**: Vault init + structure + templates
  - **Phase 2**: Core skills (check, create, update, search)
  - **Phase 3**: Auto-remember (proactive capture)
  - **Phase 4**: Optimize (full vault health)

  **Retrieval**: COG approach — file operations (grep/ripgrep) for search, wikilink traversal for relationships. Fast, no infrastructure. Semantic search via OpenSearch is a separate future feature (see FEAT-SKILL-062).

- **Acceptance Criteria**:
  - [ ] IPARAG vault structure created under `.squidsquad/vault/`
  - [ ] Templates per folder enforcing consistent frontmatter and structure
  - [ ] All agents have R/W access to the vault
  - [ ] Wikilinks for bidirectional relationships
  - [ ] Changelog per note (append-only)
  - [ ] `/vault-create`, `/vault-update`, `/vault-search` skills working
  - [ ] `/vault-check` validates note integrity on every write
  - [ ] `/vault-remember` proactively captures decisions and learnings
  - [ ] Git-tracked — full version history, diff-able, merge-able
  - [ ] Browsable in Obsidian app
  - [ ] Built as sub-skill(s) under FEAT-SKILL-030 architecture

### Discussion

> [2026-03-29 03:00] **pm/qa**: Filed from human request. Distant future initiative — Obsidian vault as institutional knowledge layer + archive storage. Human noted this may be a sub-skill rather than core feature. Large scope, parked for later. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
> [2026-04-02 08:00] **pm/qa**: Major scope expansion.
> [2026-04-02 12:00] **pm/qa**: Complete redesign from human's external research.
> [2026-04-02 12:15] **pm/qa**: Human approved. Status → Planning. Beginning Phase 1 Research. Large effort — deep research required on multi-agent vault concurrency, IPARAG adaptation, entity model, per-role auto-remember triggers, and phased implementation. Approach: COG (Claude-Obsidian-Git) philosophy — git-tracked vault, file operations, no infrastructure. Structure: IPARAG (Inbox, Projects, Areas, Resources, Archives, Galaxy) adapted for SquidSquad multi-agent context. Entity model mapped to SquidSquad domain (human profile, company context, design system, code conventions, decisions, patterns, learnings, styles). 7 composable skills for vault operations. Two-level integrity system. Auto-remember for proactive capture. Retrieval via grep + wikilink traversal (COG approach). Semantic search via OpenSearch filed separately as FEAT-SKILL-062. Priority bumped to High — this is a platform need, not a nice-to-have. Large effort, plan accordingly. from human during FEAT-SKILL-027 (designer agent) planning. The memory layer is not just archive storage — it's a **global shared memory** that ALL agents have R/W access to. Purpose: build institutional knowledge about the human's/company's values, styles, preferences, and decisions. This shapes the entire squad to be closer to the human over time. Key insight from human: dev agents need this less because code itself defines style and values, but as SquidSquad introduces more roles (designer, etc.), the need for a shared memory layer becomes critical. The designer agent is the first role where style/values can't be inferred from code alone. Priority should be reconsidered — this is becoming a platform need, not a distant future nice-to-have.
