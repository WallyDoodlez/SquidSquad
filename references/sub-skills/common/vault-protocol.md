---
slot: instructions
ordinal: 10
---

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

If `.squidsquad/vault/` does not exist, initialize it: create the 5 PARAG directories, add `.gitkeep` to empty dirs, create `BRIEFING.md` from `references/vault-templates/BRIEFING.md`, create `areas/human-profile.md` and `projects/{project-name}.md` from templates, create `.squidsquad/vault/.obsidian/` (add to `.gitignore`). vault-init is **idempotent**.

### Entity Model

Folder mapping: `areas/` = ongoing concerns (human-profile, code-conventions, design-system, company-context), `projects/` = active project context, `galaxy/` = atomic knowledge notes (decision-\*, pattern-\*, learning-\*, style-\*), `resources/` = reference material, `archives/` = historical context. See `references/docs/vault-reference.md` for full entity table.

### Creating Notes (vault-create)

1. Pick the correct folder (see Entity Model). Name using kebab-case; galaxy notes use type prefix: `decision-`, `pattern-`, `learning-`, `style-`.
2. Copy the folder's template from `references/vault-templates/` and fill in:
   - **YAML frontmatter**: type, tags, created, updated, owner, status (`active`), confidence, source, links
   - **`links`**: bare note names as YAML list (no wikilink syntax in frontmatter)
   - **`source`**: `conversation`, `code`, `review`, `observation`, or `research`
   - **Body + Changelog**: fill per template
3. Use **bare wikilinks** `[[note-name]]` in body only — no aliases
4. **Creation threshold**: Only create if reusable across contexts. Transient observations belong in iteration logs.

### Confidence Levels

- **high**: Human explicitly stated or confirmed this
- **medium**: Agent observed this directly (e.g., from code review, conversation patterns)
- **low**: Agent inferred this (e.g., from indirect signals, extrapolation)

### Wikilinks

Use `[[note-name]]` (bare, no aliases) to link related notes in the body. Find inbound links: `grep -rl '\[\[note-name\]\]' .squidsquad/vault/`. Find outbound: `grep -o '\[\[[^]]*\]\]' .squidsquad/vault/galaxy/note.md`.

### BRIEFING.md

`.squidsquad/vault/BRIEFING.md` is a ~50 line summary of active context (priorities, recent decisions, key preferences via `[[human-profile]]`, blockers). Checked for staleness on every cycle (including quiet cycles) — key fields (version, active agents, priorities) are verified against config.md and updated if stale. Token budget applies to new additions, not staleness fixes.

### Concurrent Access

One note per topic — don't append to other agents' notes. Changelogs are append-only. On merge conflict: keep both versions, never discard vault content.

### Note Size Guidance

Galaxy notes: atomic, max ~500 lines (split if larger). Area notes: grow freely. Project notes: keep focused, archive old sections. Resource notes: prefer linking to external sources.

### Updating Notes (vault-update)

1. **Read the full note first** — never update unread notes.
2. **Surgical edit** — modify only targeted section(s), preserve everything else.
3. **Never delete existing content** — add corrections; mark superseded via `status` frontmatter.
4. **Update `updated`** frontmatter to today's date.
5. **Append Changelog**: `- YYYY-MM-DD — Updated by [agent]. [What changed and why].`
6. **Run vault-check Level 1** after updating.

### Searching the Vault (vault-search)

Four search modes: **By tag** (`grep -rl "tags:.*\b<TAG>\b" .squidsquad/vault/ --include="*.md"`), **By type** (`grep -rl "^type: <TYPE>" ...`), **By keyword** (`grep -rl "<KEYWORD>" ...`), **By wikilink traversal** (1-hop outbound+inbound, max 2-hop). Max 10 results, sorted by most recently updated. Cache results within a cycle. See `references/docs/vault-reference.md` for full search examples.

### Checking Vault Health (vault-check)

vault-check validates vault notes for correctness and consistency. Two levels:

#### Level 1 — Single Note + 2-Hop Neighborhood

Runs **automatically after every vault-create or vault-update**. Checks the written note and all notes within 2 wikilink hops.

For each note checked:

1. **Required frontmatter fields**: `type`, `tags`, `created`, `updated`, `owner`, `status`, `confidence`. Warn if any are missing or empty.
2. **Type-folder match**: Galaxy notes (`galaxy/`) must have type `decision`, `pattern`, `learning`, or `style`. Area notes (`areas/`) must have type `area`. Project notes (`projects/`) must have type `project`. Warn on mismatch.
3. **Wikilink resolution**: Parse all `[[note-name]]` in the body. For each, verify a file named `note-name.md` exists somewhere in `.squidsquad/vault/`. Warn for each unresolved wikilink.
4. **Auto-maintain `links` frontmatter**: Parse all `[[note-name]]` from the note's body. Update the `links` field in frontmatter to match (bare names, YAML list). This is automatic — agents do not manually curate the `links` field.
5. **Galaxy note size**: If the note is in `galaxy/` and exceeds 500 lines, warn and suggest splitting. Do NOT warn for notes in `areas/`, `projects/`, or `resources/`.

Print warnings with `[vault-check]` prefix. If no issues found, print nothing (silent pass).

#### Level 2 — Full Vault Sweep

Runs on-demand (invoked explicitly, not automatic). Checks every `.md` file: all Level 1 checks + orphan detection + staleness detection (30+ days) + broken link census + health summary. See `references/docs/vault-reference.md` for details and scripts.

### Rules

- All vault notes are **git-tracked** — full version history
- Galaxy notes should be **atomic** (one idea per note, max ~500 lines)
- Area notes can grow freely (human-profile, design-system, etc.)
- Every note must have the **confidence** field
- Always append to the **Changelog** section when modifying a note
- The vault is browsable in the **Obsidian app** — maintain clean structure
- Empty directories use `.gitkeep` to persist in git
- **vault-check Level 1 runs after every write** — vault-create and vault-update both trigger it
- **vault-update never deletes content** — only adds, corrects, or marks as superseded
