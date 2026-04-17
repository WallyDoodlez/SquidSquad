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

Use `[[note-name]]` (bare, no aliases) to link related notes in the body. Find inbound links: `grep -rl '\[\[note-name\]\]' .squidsquad/vault/`. Find outbound: `grep -o '\[\[[^]]*\]\]' .squidsquad/vault/galaxy/note.md`.

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

Galaxy notes: atomic, max ~500 lines (split if larger). Area notes: grow freely. Project notes: keep focused, archive old sections. Resource notes: prefer linking to external sources.

### Updating Notes (vault-update)

To update an existing vault note:

1. **Read the full note first** — never update a note you haven't read in this cycle.
2. **Modify only the targeted section(s)** — preserve all other sections exactly as they are. vault-update is a surgical edit, not a rewrite.
3. **Never delete existing content** — add to sections, don't remove from them. If content is wrong, add a correction; if superseded, mark it as such in the body and update `status` in frontmatter.
4. **Update the `updated` frontmatter field** to today's date.
5. **Append a Changelog entry** describing what changed and why:
   ```
   - YYYY-MM-DD — Updated by [agent]. [What changed and why].
   ```
6. **Run vault-check Level 1** on the note after updating (see vault-check below).

vault-update preserves the note's identity — same filename, same `created` date, same `owner`. Only `updated`, the targeted body section(s), and the Changelog grow.

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
