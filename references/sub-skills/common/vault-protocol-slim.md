## Vault — Shared Memory Layer (Read-Only)

All agents have read access to the shared knowledge vault at `.squidsquad/vault/`. The vault stores institutional knowledge — decisions, patterns, learnings, preferences, and context that shapes the squad's behavior over time. It follows the **PARAG** structure:

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

### BRIEFING.md

`.squidsquad/vault/BRIEFING.md` is a ~50 line summary of active context. Read it at session start for current priorities, recent decisions, and key human preferences.

### Searching the Vault (vault-search)

Find notes by tag, type, keyword, or wikilink traversal:

1. **By tag**: `grep -rl "tags:.*\b<TAG>\b" .squidsquad/vault/ --include="*.md"`
2. **By type**: `grep -rl "^type: <TYPE>" .squidsquad/vault/ --include="*.md"`
3. **By keyword**: `grep -rl "<KEYWORD>" .squidsquad/vault/ --include="*.md"`
4. **By wikilink traversal** (1-hop):
   - Outbound: `grep -o '\[\[[^]]*\]\]' .squidsquad/vault/<path>`
   - Inbound: `grep -rl '\[\[<note-name>\]\]' .squidsquad/vault/ --include="*.md"`

**Max 10 results** — return the most recently updated. Cache results within a cycle.

### Confidence Levels

- **high**: Human explicitly stated or confirmed
- **medium**: Agent observed directly
- **low**: Agent inferred

### Rules

- Vault notes are **git-tracked** — full version history
- Galaxy notes are **atomic** (one idea per note)
- This role has **read-only** vault access — vault writes are handled by PM and worker agents
- Use `[[note-name]]` wikilinks to reference vault notes in Discussion entries
