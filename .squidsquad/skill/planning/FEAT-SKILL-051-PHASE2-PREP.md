# FEAT-SKILL-051 Phase 2 Prep — Open Question Analysis

## Optimal Question Order

Questions should be resolved in this order (dependencies first, controversial last):

1. **Q7** (convention) — Heading format in individual files. Zero dependencies, trivial to resolve, affects file schema used by everything else.
2. **Q4** (migration) — What happens to old monolithic files. Must be decided before writing migration logic.
3. **Q5** (migration) — Whether to append migration Discussion entries. Must be decided before writing migration logic.
4. **Q1** (format) — INDEX.md format. Must be decided before writing agent templates and statusline.
5. **Q6** (safety) — Atomic writes for INDEX.md. Must be decided before writing agent template instructions.
6. **Q2** (architecture) — INDEX regeneration: script vs inline. Affects every agent template. Slightly more controversial.
7. **Q3** (convention) — Gitignore for archived items. Least impactful, most likely to provoke bikeshedding.

**Rationale**: Q7/Q4/Q5 are migration prerequisites with obvious answers. Q1/Q6 define the runtime contract. Q2 is the only genuine architecture decision. Q3 is already answered in the research (No) but included for completeness.

---

## Q1 — INDEX.md Format

**Category**: Format

Should INDEX.md use a markdown table or a simpler pipe-separated format?

### Option A: Markdown Table (RECOMMENDED)

```markdown
| ID | Status | Severity | Title |
|----|--------|----------|-------|
| BUG-SKILL-038 | Open | High | PS1 boot scripts fail |
```

**Pros**:
- Renders natively in GitHub, VS Code, and any markdown viewer
- Human-readable without tooling
- Consistent with other SquidSquad markdown files
- Agents already parse markdown tables in other contexts

**Cons**:
- Slightly more characters per line (~10 chars of table formatting overhead)
- Requires header separator row (`|----|---...`)

### Option B: Simple Pipe-Separated (No Table Header)

```
BUG-SKILL-038 | Open | High | PS1 boot scripts fail
```

**Pros**:
- Marginally fewer tokens (~50 tokens saved across a 50-item index)
- Trivial to grep

**Cons**:
- Does not render as a table in GitHub/editors
- Looks unprofessional in markdown viewers
- Inconsistent with project conventions
- Agents still need to split on `|` — same parsing complexity

### Option C: YAML Front Matter + List

```yaml
---
generated: 2026-03-31 12:00
---
- BUG-SKILL-038: {status: Open, severity: High, title: "PS1 boot scripts fail"}
```

**Pros**:
- Machine-parseable with standard YAML tooling
- Extensible (easy to add fields)

**Cons**:
- SquidSquad uses no YAML anywhere — inconsistent
- YAML quoting rules add complexity for titles with special chars
- Agents are optimized for markdown, not YAML
- More tokens than markdown table for same content

### Recommendation: **Option A (Markdown Table)**

The token savings of Option B are negligible (~50 tokens). The markdown table renders well everywhere and matches project conventions. The research already recommends this.

---

## Q2 — INDEX Regeneration: Script vs Inline

**Category**: Architecture

Should INDEX.md regeneration be a helper script or inline logic in each agent template?

### Option A: Inline Logic in Agent Templates (RECOMMENDED)

Each agent template contains 5-10 lines of instructions describing how to regenerate INDEX.md after modifying a tracker entry.

**Pros**:
- Zero external dependencies — agents are self-contained
- No script to install, copy, or keep in sync
- Agent can adapt to edge cases (e.g., malformed files) using LLM reasoning
- Consistent with existing pattern: all tracker manipulation is already inline in templates
- One fewer file to maintain in `references/`

**Cons**:
- Duplicated across 3 agent templates (dev, PM, DM)
- If regeneration logic changes, must update all templates
- Slight increase in template size (~200 tokens per template)

### Option B: Shared Helper Script (`references/regen-index.sh`)

A bash script that scans a directory and regenerates INDEX.md.

**Pros**:
- Single source of truth for regeneration logic
- Testable independently
- Changes propagate via `references/` copy mechanism

**Cons**:
- New script to maintain, test on Windows (bash-on-Windows edge cases)
- Agents must invoke it correctly (path, arguments)
- Breaks if script is missing or not executable
- statusline.sh already has Windows compatibility issues — adding another script increases surface area
- Agents lose the ability to reason about edge cases

### Option C: Hybrid — Script with Inline Fallback

Agent templates say: "Run `regen-index.sh [dir]` if it exists, otherwise regenerate inline."

**Pros**:
- Best of both worlds in theory
- Graceful degradation

**Cons**:
- Dual-path logic in every template — most complex option
- More template tokens than either pure option
- Testing burden doubles
- The "fallback" path rarely exercises, so bugs hide there

### Recommendation: **Option A (Inline Logic)**

The regeneration logic is simple (list files, extract metadata, sort, write table). Duplicating 5-10 lines across 3 templates is far less risky than maintaining a cross-platform bash script. This matches the existing project pattern where agents contain all their tracker logic inline.

---

## Q3 — Gitignore Archived Items

**Category**: Convention

Should `archived/` directories be excluded from git tracking via `.gitignore`?

### Option A: Do NOT Gitignore — Keep Tracked (RECOMMENDED)

Archived files remain fully tracked in git.

**Pros**:
- Consistent with "GitHub is the bus" philosophy
- Full audit trail without needing `git log` archaeology
- Agents can read archived items directly when needed (e.g., checking if a bug was previously fixed)
- Simple — no `.gitignore` changes needed

**Cons**:
- One-time git noise during migration (30+ file moves show in `git status`)
- Archived directory grows over time (but files are small, ~1-2KB each)

### Option B: Gitignore `archived/`

Add `**/archived/` to `.gitignore`.

**Pros**:
- Cleaner `git status` after archival operations
- Slightly smaller repo clone size over time

**Cons**:
- Violates "GitHub is the bus" — archived items not available on clone
- Cannot reference archived items across machines
- Recovery requires manual re-creation
- Loss of audit trail for closed items

### Option C: Gitignore with Periodic Archive Commits

Gitignore day-to-day but periodically commit archived items in batch.

**Pros**:
- Reduces day-to-day noise
- Eventually everything is tracked

**Cons**:
- Complex workflow for marginal benefit
- Window where archived items are untracked and at risk
- Requires a scheduled "archive commit" mechanism

### Recommendation: **Option A (Keep Tracked)**

This is already effectively decided by the research doc. "GitHub is the bus" is a core project principle. The git noise is a one-time migration cost.

---

## Q4 — Handling Old Monolithic Files After Migration

**Category**: Migration

What happens to `bugs.md` and `features.md` after entries are split into individual files?

### Option A: Delete (RECOMMENDED)

Remove the monolithic files entirely. Git history preserves them.

**Pros**:
- No confusion — agents cannot accidentally read the old file
- Cannot have both `bugs.md` (file) and `bugs/` (directory) causing path ambiguity
- Clean directory listing
- Git history is the backup — always recoverable via `git show HEAD~1:path/bugs.md`

**Cons**:
- No quick "look at the old format" without git commands
- Slightly higher perceived risk (though git history fully mitigates this)

### Option B: Rename to `.bak`

Rename to `bugs.md.schema2-backup`.

**Pros**:
- Immediately accessible backup without git commands
- Psychological comfort during migration

**Cons**:
- Clutter in the directory
- Risk of agents or grep accidentally reading the backup
- `.bak` files in repos are an anti-pattern
- Must eventually be cleaned up anyway

### Option C: Move to a `_migration-backup/` Directory

Move old files to `.squidsquad/[role]/_migration-backup/bugs.md`.

**Pros**:
- Out of the way but accessible
- Clear naming signals purpose

**Cons**:
- Yet another directory to manage
- Same risk of accidental reads as Option B
- Adds complexity for temporary benefit

### Recommendation: **Option A (Delete)**

The research already recommends this. Git history is the backup. Keeping stale files around creates confusion and potential for agents to read the wrong source. The old files literally cannot coexist cleanly with the new directory structure.

---

## Q5 — Migration Discussion Entry

**Category**: Migration

Should each migrated item get a Discussion entry noting the migration?

### Option A: Yes, Append Migration Note (RECOMMENDED)

```
> [2026-03-31 12:00] **migration**: Migrated from monolithic tracker to individual file (Schema 2 -> 3).
```

**Pros**:
- Clear audit trail of when and why the file was created
- Consistent with Discussion-as-changelog convention
- Helps agents understand file provenance
- Only ~1 line per file — negligible token cost

**Cons**:
- Adds ~80 chars per file (trivial)
- Every individual file has a "migration" entry that provides no actionable info post-migration

### Option B: No Migration Note

Individual files contain only the original entry content.

**Pros**:
- Cleaner files
- No "noise" entries in Discussion

**Cons**:
- No record of when the file was created vs when the entry was originally filed
- Harder to debug migration issues
- Inconsistent with the append-only Discussion philosophy

### Option C: Migration Note Only in INDEX.md

Add a comment to INDEX.md: `<!-- Migrated from Schema 2 on YYYY-MM-DD -->`.

**Pros**:
- Single migration note rather than N duplicates
- Keeps individual files clean

**Cons**:
- INDEX.md is auto-generated — the comment would be lost on regeneration unless the regeneration logic explicitly preserves it
- Does not provide per-item provenance

### Recommendation: **Option A (Yes, Append)**

One line per file is negligible cost. The audit trail is valuable during and after migration. This matches the existing convention where every status change gets a Discussion entry.

---

## Q6 — Atomic Writes for INDEX.md

**Category**: Safety

Should agents use atomic writes (write to `.tmp` then `mv`) when regenerating INDEX.md?

### Option A: Yes, Atomic Writes (RECOMMENDED)

```bash
# Write to temp file, then move atomically
echo "..." > .squidsquad/skill/bugs/INDEX.md.tmp && mv -f .squidsquad/skill/bugs/INDEX.md.tmp .squidsquad/skill/bugs/INDEX.md
```

**Pros**:
- Prevents partial reads by statusline.sh (which runs on every assistant message)
- Prevents corruption if agent is interrupted mid-write
- Consistent with existing `current-state` atomic write pattern
- Proven pattern in the codebase — agents already do this for `current-state`

**Cons**:
- Slightly more complex write instructions in templates
- Two filesystem operations instead of one

### Option B: No, Direct Write

```bash
echo "..." > .squidsquad/skill/bugs/INDEX.md
```

**Pros**:
- Simpler instructions
- One fewer filesystem operation

**Cons**:
- Risk of statusline.sh reading a partially written INDEX
- Risk of corruption on interrupt
- Inconsistent with the atomic write pattern already established for `current-state`

### Option C: Atomic Writes Only on Windows

Use atomic writes only when `$OS` indicates Windows, direct write on Linux/macOS.

**Pros**:
- Avoids overhead on Unix where `>` redirect is more atomic

**Cons**:
- Platform-conditional logic in agent templates is fragile
- Adds complexity for marginal benefit
- `mv` is atomic on all platforms — no reason to special-case

### Recommendation: **Option A (Yes, Atomic Writes)**

This is consistent with the existing `current-state` pattern. The cost is minimal (one extra line in the write instruction). The benefit is real — statusline.sh reads INDEX.md frequently and a partial read would produce garbled status output.

---

## Q7 — Keep `##` Heading in Individual Files

**Category**: Convention

Should individual entry files keep the `## ID - Title` heading or drop it?

### Option A: Keep `##` Heading (RECOMMENDED)

```markdown
## BUG-SKILL-038 — PS1 boot scripts fail on Windows due to emoji

- **Severity**: High
...
```

**Pros**:
- Format is identical to current entry format — migration is a straight copy
- Files render correctly as standalone markdown documents
- The heading provides context when reading the file (you see the ID and title immediately)
- Consistent with planning artifacts (`## FEAT-SKILL-XXX — Title` in RESEARCH/CONTEXT files)

**Cons**:
- 4 characters of "waste" (the `## ` prefix)
- ID is duplicated (filename + heading) — but this is standard practice

### Option B: Drop `##`, Start with Metadata

```markdown
- **Severity**: High
- **Status**: Open
...
```

**Pros**:
- Saves 1 line per file
- No duplication between filename and heading

**Cons**:
- File does not render as a proper markdown document (no heading)
- Breaks consistency with current entry format
- Migration requires stripping the heading — additional parsing
- Harder to read when opened directly

### Option C: Use `#` (H1) Instead of `##` (H2)

```markdown
# BUG-SKILL-038 — PS1 boot scripts fail on Windows due to emoji
```

**Pros**:
- More semantically correct — it is the top-level heading of the document
- Renders with proper hierarchy

**Cons**:
- Breaks format compatibility with current entries (which use `##`)
- Migration requires changing `##` to `#`
- Agents' grep patterns use `^## BUG-` — would need updating
- Inconsistent with planning artifacts which also use `##`

### Recommendation: **Option A (Keep `##`)**

The research already recommends this. The format identity between old entries and new individual files makes migration trivial (straight copy, no transformation). The `##` heading is the de facto standard in this project.

---

## Summary Table

| Q# | Category | Recommended | Confidence | Controversy |
|----|----------|-------------|------------|-------------|
| Q7 | Convention | Keep `##` heading | Very High | None |
| Q4 | Migration | Delete old files | High | Low |
| Q5 | Migration | Append migration note | High | Low |
| Q1 | Format | Markdown table | High | Low |
| Q6 | Safety | Yes, atomic writes | High | None |
| Q2 | Architecture | Inline in templates | Medium-High | Medium |
| Q3 | Convention | Do NOT gitignore | Very High | None |

**Key observation**: All 7 questions have clear recommended answers, most of which were already suggested in the research document. The only question with genuine design tension is Q2 (script vs inline), and even there the inline approach aligns better with existing project patterns. This feature is ready to move to CONTEXT.md with locked decisions.
