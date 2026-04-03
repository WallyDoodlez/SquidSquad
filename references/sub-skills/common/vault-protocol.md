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
2. Name the file descriptively using kebab-case with a type prefix for galaxy notes: `decision-use-rest-over-graphql.md`, `pattern-error-handling.md`, `learning-cache-invalidation.md`
3. Copy the folder's template (from `references/vault-templates/`) and fill in:
   - **YAML frontmatter**: type, tags, created (today), updated (today), owner (your role), status (`active`), confidence (`high` if human-confirmed, `medium` if observed, `low` if inferred), links (wikilinks to related notes as `[[note-name]]`)
   - **Body sections**: fill per template structure
   - **Changelog**: initial entry with date, your role, and brief context
4. Use **bare wikilinks** only: `[[note-name]]` — no alias syntax

### Confidence Levels

- **high**: Human explicitly stated or confirmed this
- **medium**: Agent observed this directly (e.g., from code review, conversation patterns)
- **low**: Agent inferred this (e.g., from indirect signals, extrapolation)

### Wikilinks

Use `[[note-name]]` (bare, no aliases) to link related notes. Links create a knowledge graph browsable in Obsidian and traversable via grep:

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
- Key human preferences summary
- Active constraints or blockers

BRIEFING.md is auto-maintained — agents update it when significant context changes. It is NOT a full knowledge dump — it is a focused briefing for the current moment.

### Rules

- All vault notes are **git-tracked** — full version history
- Galaxy notes should be **atomic** (one idea per note, max ~500 lines)
- Area notes can grow freely (human-profile, design-system, etc.)
- Every note must have the **confidence** field
- Always append to the **Changelog** section when modifying a note
- The vault is browsable in the **Obsidian app** — maintain clean structure
