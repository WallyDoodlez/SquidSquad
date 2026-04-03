## Vault — Shared Memory Layer

All agents have read/write access to the shared knowledge vault at `.squidsquad/vault/`. The vault stores institutional knowledge — decisions, patterns, learnings, preferences, and context that shapes the squad's behavior over time. It follows the **PARAG** structure:

```
.squidsquad/vault/
├── projects/       # Active project context, goals, constraints
├── areas/          # Ongoing concerns: human preferences, code conventions,
│                   # design system, company values, team culture
├── resources/      # Reference material, external docs, research
├── archives/       # Shipped features, closed decisions, historical context
└── galaxy/         # Atomic knowledge notes (Zettelkasten):
                    # decisions, patterns, learnings, styles
```

### Vault Initialization (vault-init)

If `.squidsquad/vault/` does not exist, initialize it:

1. Create the 5 PARAG directories: `projects/`, `areas/`, `resources/`, `archives/`, `galaxy/`
2. Add `.gitkeep` files to empty directories (`resources/.gitkeep`, `archives/.gitkeep`) so git tracks them
3. Create `BRIEFING.md` from the template at `references/vault-templates/BRIEFING.md` — pre-populate with current project context from `config.md`
4. Create initial `areas/human-profile.md` from the areas template — seed with any known human preferences (can be minimal stub initially)
5. Create `projects/{project-name}.md` from the projects template — seed with project info from `config.md`
6. Create `.squidsquad/vault/.obsidian/` directory and add it to `.gitignore` (Obsidian's config is per-user, not shared)

vault-init is **idempotent** — re-running it creates missing directories and files but never overwrites existing vault content.

### Entity Model

| Entity | Location | Purpose |
|--------|----------|---------|
| Human profile | `areas/human-profile.md` | Preferences, values, communication style |
| Company context | `areas/company-context.md` | Culture, standards, brand guidelines |
| Design system | `areas/design-system.md` | Colors, tokens, typography, component patterns |
| Code conventions | `areas/code-conventions.md` | Style, patterns, architecture decisions |
| Project context | `projects/{name}.md` | Goals, constraints, architecture, tech stack |
| Decisions | `galaxy/decision-*.md` | Individual architectural/design/process decisions |
| Patterns | `galaxy/pattern-*.md` | Recurring approaches, established conventions |
| Learnings | `galaxy/learning-*.md` | Lessons learned, what worked/didn't |
| Styles | `galaxy/style-*.md` | Visual style, writing tone, code style preferences |

### Creating Notes (vault-create)

To create a vault note:

1. Determine the correct folder based on note type (galaxy/ for atomic knowledge, areas/ for ongoing concerns, etc.)
2. Name the file descriptively using kebab-case with a type prefix for galaxy notes: `decision-use-rest-over-graphql.md`, `pattern-error-handling.md`, `learning-cache-invalidation.md`. Valid galaxy type prefixes: `decision-`, `pattern-`, `learning-`, `style-`. Agents may introduce new prefixes if needed — document them in the Changelog.
3. Copy the folder's template (from `references/vault-templates/`) and fill in:
   - **YAML frontmatter**: type, tags, created (today), updated (today), owner (your role), status (`active`), confidence, source, links
   - **`links` field format**: Use bare note names as a YAML list: `links: [note-name-a, note-name-b]`. Do NOT use wikilink syntax in frontmatter. Wikilinks (`[[note-name]]`) go in the body's Related section only. The `links` field is for machine parsing; the Related section is for human reading.
   - **`source` field**: How this knowledge was captured. Values: `conversation` (from human discussion), `code` (observed in codebase), `review` (from code/design review), `observation` (inferred from patterns), `research` (from external sources). Not exhaustive — use the closest match.
   - **Body sections**: fill per template structure
   - **Changelog**: initial entry with date, your role, and brief context
4. Use **bare wikilinks** only in the body: `[[note-name]]` — no alias syntax
5. **Creation threshold**: Only create a note if the insight is reusable across contexts. Transient observations (one-time debugging steps, ephemeral state) belong in iteration logs, not the vault.

### Confidence Levels

- **high**: Human explicitly stated or confirmed this
- **medium**: Agent observed this directly (e.g., from code review, conversation patterns)
- **low**: Agent inferred this (e.g., from indirect signals, extrapolation)

### Wikilinks

Use `[[note-name]]` (bare, no aliases) to link related notes in the body. Links create a knowledge graph browsable in Obsidian and traversable via grep:

```bash
# Find all notes linking TO a given note
grep -rl '\[\[note-name\]\]' .squidsquad/vault/

# Find what a note links TO
grep -o '\[\[[^]]*\]\]' .squidsquad/vault/galaxy/decision-example.md
```

### BRIEFING.md

`.squidsquad/vault/BRIEFING.md` is a ~50 line summary of active context, injected at session start. It contains:
- Current project priorities and active work
- Recent important decisions
- Key human preferences summary (reference `[[human-profile]]` if it exists — this link is optional during early vault setup)
- Active constraints or blockers

BRIEFING.md is auto-maintained — agents update it when **significant** context changes (new project priorities, major decisions, constraint changes). Minor cycle-to-cycle updates do NOT warrant a BRIEFING.md edit. It is NOT a full knowledge dump — it is a focused briefing for the current moment.

### Concurrent Access

Multiple agents may write to the vault simultaneously. Git handles merge conflicts at the file level. To minimize conflicts:

- **One note per topic** — don't append to other agents' notes. Create your own note and link to theirs.
- **Append-only changelogs** — like Discussion entries, Changelog entries are append-only. Git can auto-merge appends to the same file.
- **If a merge conflict occurs**: Keep both versions. Append the conflicting section below the existing one. Never discard vault content.

### Note Size Guidance

- **Galaxy notes**: Atomic — one idea per note, max ~500 lines. If a note grows beyond this, split it.
- **Area notes** (human-profile, design-system, etc.): Can grow freely — these are living documents.
- **Project notes**: Keep focused on active context. Archive historical sections to `archives/` when no longer current.
- **Resource notes**: No hard limit, but prefer linking to external sources over copying large amounts of content.

### Rules

- All vault notes are **git-tracked** — full version history
- Galaxy notes should be **atomic** (one idea per note, max ~500 lines)
- Area notes can grow freely (human-profile, design-system, etc.)
- Every note must have the **confidence** field
- Always append to the **Changelog** section when modifying a note
- The vault is browsable in the **Obsidian app** — maintain clean structure
- Empty directories use `.gitkeep` to persist in git
