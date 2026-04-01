# FEAT-SKILL-051 Research — Tracker Schema 3 (Individual Files + Index)

## Summary

SquidSquad currently stores all bug and feature entries in two monolithic files per agent role: `bugs.md` (1023 lines, ~80KB) and `features.md` (1690 lines, ~151KB). Combined, these consume ~56k tokens when read in full. Agents grep or read these files every cycle to find the few active entries (currently 4 open bugs and ~12 non-shipped features out of 38 bugs and 51 features total). The proposed Schema 3 splits each entry into its own file inside `bugs/` and `features/` directories, with a lightweight auto-generated `INDEX.md` per directory. This reduces per-cycle token consumption by >80% — agents read only the ~50-line index to find items by status, then read only the specific 20-40 line files they need to act on.

The migration touches every agent template, the SKILL.md setup/upgrade flow, the statusline script, the README, and the evals. This research documents every reference, the entry formats, migration strategy, and all edge cases. The core risk is that missing even one reference to `bugs.md` or `features.md` in an agent template will produce a broken agent post-migration. A secondary risk is git merge conflicts on INDEX.md when multiple agents write to the same role's tracker simultaneously (currently rare — only PM writes to skill's tracker for Discussion entries).

The change is feasible with careful execution. The "never delete tracker entries" rule is preserved because moving to `archived/` retains the file in git (git tracks the rename), and the old monolithic files remain in git history. The ID counter mechanism in `config.md` is unchanged.

## Current Format Analysis

### Bug Entry Format

Each bug entry in `bugs.md` follows this exact format:

```markdown
---

## BUG-SKILL-XXX — [Title]

- **Severity**: Critical | High | Medium | Low
- **Status**: Open | Investigating | Fixed | Verified | Closed
- **Reported By**: pm/qa | skill-lead | human
- **Assigned To**: skill-lead
- **Description**: [Multi-line description of what is broken]
- **Steps to Reproduce**:
  1. [Step]
  2. [Step]
- **Expected**: [Expected behavior]
- **Actual**: [Actual behavior]

### Discussion

> [YYYY-MM-DD HH:MM] **[author]**: [message]
> [YYYY-MM-DD HH:MM] **[author]**: [message]

---
```

**Required fields**: Severity, Status, Reported By, Assigned To, Description. Steps to Reproduce, Expected, Actual are standard but some entries omit them (especially quick self-filed bugs by skill-lead). Discussion is always present (at minimum one entry).

**Entry separator**: `---` (horizontal rule) between entries. The file begins with a header block:
```markdown
# Bug Tracker

_Bugs are filed in BUG-SKILL-XXX format. Each entry includes a Discussion section for cross-team communication._

---
```

### Feature Entry Format

```markdown
---

## FEAT-SKILL-XXX — [Title]

- **Priority**: Critical | High | Medium | Low
- **Requested By**: human | pm/qa | skill-lead | dm
- **Status**: Pending | Planning | Approved | In Progress | Pending Test | Pending Ship | Shipped | Rejected | On Hold
- **Owner**: skill-lead
- **Description**: [Multi-line description]
- **Acceptance Criteria**:
  - [ ] Criterion one
  - [ ] Criterion two

### Discussion

> [YYYY-MM-DD HH:MM] **[author]**: [message]

---
```

**Required fields**: Priority, Status, Owner (or Requested By), Description, Acceptance Criteria. Some early entries use `Owner` while later ones use `Requested By` — both patterns exist. Discussion is always present.

**Note**: Some features have additional custom fields in the description like `- **New structure**:` with code blocks, `- **Scope**:` with bullet lists, `- **How agents work with it**:`, and `- **Migration**:`. These are part of the Description section, not separate top-level fields.

### Discussion Entry Format

```markdown
> [YYYY-MM-DD HH:MM] **[role]**: [message]. Status -> [new status].
```

Discussion entries are append-only. Roles include: `pm/qa`, `skill-lead`, `dm`, `human`, `migration` (used by schema migration scripts). Some Discussion entries are multi-line (the `>` continues on subsequent lines). Cross-references between items appear as plain text mentions like `BUG-SKILL-029`, `FEAT-SKILL-037`.

## Impact Analysis — Exhaustive Reference Audit

### references/agent-instructions.md (19 references)

This is the master template from which all agent CLAUDE.md files are generated. It contains three template sections (Dev Agent, PM/QA, DM).

**Dev Agent template references:**
- Line 31: `Fix bugs filed in .squidsquad/[ROLE]/bugs.md.` (responsibility)
- Line 32: `Implement features listed in .squidsquad/[ROLE]/features.md with status Approved.` (responsibility)
- Line 135: `Open .squidsquad/[ROLE]/bugs.md. For each bug with status Open or Investigating:` (Step 2 triage)
- Line 151: `File a new bug in .squidsquad/[OTHER_ROLE]/bugs.md as BUG-[OTHER_ROLE_UPPER]-XXX.` (cross-filing)
- Line 162: `Open .squidsquad/[ROLE]/features.md. Pick the next feature with status Approved` (Step 3 features)
- Line 265: `Self-file to [ROLE]/bugs.md` (filing bugs section)
- Line 267: `Cross-file to [OTHER_ROLE]/bugs.md` (cross-filing section)
- Line 324: `Your tracker files: .squidsquad/[ROLE]/bugs.md, .squidsquad/[ROLE]/features.md` (file conventions)
- Line 328: `Other agent trackers (write only when cross-filing): .squidsquad/[OTHER_ROLE]/bugs.md` (file conventions)

**PM/QA template references:**
- Line 525: `For each active agent, open their bugs.md. For each bug with status Fixed:` (Step 5 verify)
- Line 539: `For each active agent, open their features.md. For each feature with status Pending Test:` (Step 6 verify)
- Line 633: `append a Discussion note to the agent's bugs.md` (agent health stalled)
- Line 904: `Feature entry in features.md — written by PM directly` (Phase 3 planning)
- Line 1035: `You may write Discussion entries in any agent's bugs.md or features.md.` (discussion protocol)
- Line 1069: `All agent trackers: .squidsquad/[ROLE]/bugs.md, .squidsquad/[ROLE]/features.md` (file conventions)

**DM template references:**
- Line 1214: `Read each dev agent's features.md` (Step 2 scan Pending Ship)
- Line 1336: `You may write Discussion entries in any agent's bugs.md or features.md.` (discussion protocol)
- Line 1378: `Dev agent trackers: .squidsquad/[ROLE]/features.md, .squidsquad/[ROLE]/bugs.md` (file conventions)
- Line 1380: `You do NOT have your own features.md or bugs.md` (file conventions)

### SKILL.md (22 references)

- Line 32: ASCII diagram shows `bugs.md` in directory tree
- Line 33: ASCII diagram shows `features.md` in directory tree
- Line 49: Role table: `[role]/bugs.md, [role]/features.md` ownership
- Line 80-81: Directory structure showing `bugs.md` and `features.md`
- Line 95: Note about DM using shared trackers (no `dm/features.md` or `dm/bugs.md`)
- Line 103: Section header `### Bug Format (bugs.md)`
- Line 129: Section header `### Feature Format (features.md)`
- Line 190: Ralph Loop step: `Scan [role]/bugs.md for Open or Investigating items`
- Line 192: Ralph Loop step: `file BUG-[OTHER]-XXX in [other]/bugs.md`
- Line 194: Ralph Loop step: `Scan [role]/features.md for Approved items`
- Line 217: PM Loop step: `Scan each dev agent's features.md for Pending Test items`
- Line 219: PM Loop step: `Scan each dev agent's bugs.md for Fixed items`
- Line 235: Shared rules: `Tracker files (bugs.md, features.md, qa-log.md) are append-only`
- Line 251: PR flow note: `PM tracker updates (bugs.md, features.md status changes...)`
- Line 345: Setup Step 6 directory: `bugs.md`
- Line 346: Setup Step 6 directory: `features.md`
- Line 757: Step 6 seeding: `[role]/bugs.md (one per dev agent)`
- Line 766: Step 6 seeding: `[role]/features.md (one per dev agent)`
- Line 799: Seed routing: `Route each item to the correct [role]/bugs.md or [role]/features.md`
- Line 928: Setup Step 4b (long line with multiple references)
- Line 999: `/squidsquad-status` command: `read their bugs.md and features.md`

### .squidsquad/skill/CLAUDE.md (6 references)

- Line 10: `Fix bugs filed in .squidsquad/skill/bugs.md.`
- Line 11: `Implement features listed in .squidsquad/skill/features.md with status Approved.`
- Line 113: `Open .squidsquad/skill/bugs.md. For each bug with status Open or Investigating`
- Line 132: `Open .squidsquad/skill/features.md. Pick the next feature with status Approved`
- Line 233: `Self-file to skill/bugs.md`
- Line 288: `Your tracker files: .squidsquad/skill/bugs.md, .squidsquad/skill/features.md`

### .squidsquad/pm/CLAUDE.md (6 references)

- Line 180: `For each active agent, open their bugs.md. For each bug with status Fixed:`
- Line 194: `For each active agent, open their features.md. For each feature with status Pending Test:`
- Line 288: `append a Discussion note to the agent's bugs.md`
- Line 559: `Feature entry in features.md`
- Line 690: `You may write Discussion entries in any agent's bugs.md or features.md.`
- Line 724: `All agent trackers: .squidsquad/[ROLE]/bugs.md, .squidsquad/[ROLE]/features.md`

### .squidsquad/templates/dm-agent.md (4 references)

- Line 110: `Read each dev agent's features.md`
- Line 232: `You may write Discussion entries in any agent's bugs.md or features.md.`
- Line 280: `Dev agent trackers: .squidsquad/[ROLE]/features.md, .squidsquad/[ROLE]/bugs.md`
- Line 282: `You do NOT have your own features.md or bugs.md`

### statusline.sh (references/statusline.sh + .squidsquad/statusline.sh) (4 refs each, 8 total)

- Line 189: `FEATS_FILE="$SQDIR/$AGENT/features.md"` (PM planning phase check)
- Line 299: `FEATS_FILE="$SQDIR/$AGENT/features.md"` (DM Pending Ship count)
- Line 339: `BUGS_FILE="$SQDIR/$ROLE/bugs.md"` (dev agent backlog)
- Line 340: `FEATS_FILE="$SQDIR/$ROLE/features.md"` (dev agent backlog)

These use `grep -cE` to count statuses — they grep the raw files for patterns like `**Status**: Open`.

### README.md (7 references)

- Line 84-85: Mermaid diagram referencing `bugs.md + features.md`
- Line 116: Directory tree: `bugs.md <- BUG-[ROLE]-XXX tracker`
- Line 117: Directory tree: `features.md <- FEAT-[ROLE]-XXX tracker`
- Line 256-258: Bug routing table: `[role]/bugs.md`

### evals/evals.json (1 reference)

- Line 12: `expected_output` mentioning `fe/bugs.md, be/bugs.md`

### CHANGELOG.md (2 references)

- Line 153-154: Historical entry mentioning `fe/bugs.md`, `fe/features.md` etc. (historical, no update needed)

### Other files (historical/planning — no updates needed)

- `.squidsquad/pm/qa-log.md`: Multiple historical "Files Reviewed" entries (7 refs) — log entries, no update needed
- `.squidsquad/pm/FEAT-SKILL-016-design.md`: 2 refs — historical design doc
- `.squidsquad/skill/bugs.md`: Self-references in bug descriptions (3 refs) — will be split into individual files anyway
- `.squidsquad/skill/features.md`: Self-references in feature descriptions (4 refs) — same
- `.squidsquad/skill/planning/` various research files: Historical references, no update needed
- `.squidsquad/skill/iterations/`: Historical iteration logs, no update needed

### Total References to Update

| File | Count | Type |
|------|-------|------|
| references/agent-instructions.md | 19 | Template (critical) |
| SKILL.md | 22 | Setup/docs (critical) |
| .squidsquad/skill/CLAUDE.md | 6 | Generated agent (regenerated from template) |
| .squidsquad/pm/CLAUDE.md | 6 | Generated agent (regenerated from template) |
| .squidsquad/templates/dm-agent.md | 4 | Template (critical) |
| references/statusline.sh | 4 | Script (critical) |
| .squidsquad/statusline.sh | 4 | Live copy (regenerated from references/) |
| README.md | 7 | Documentation |
| evals/evals.json | 1 | Test expectations |
| **Total actionable** | **73** | |

**Note**: Generated files (skill/CLAUDE.md, pm/CLAUDE.md, .squidsquad/statusline.sh) are regenerated from templates during upgrade, so the critical updates are to the source templates (references/agent-instructions.md, SKILL.md, references/statusline.sh, .squidsquad/templates/dm-agent.md). However, the live generated files must ALSO be updated for the current install.

## INDEX.md Design

### Format

```markdown
# Bug Index

| ID | Status | Severity | Title |
|----|--------|----------|-------|
| BUG-SKILL-038 | Open | High | PS1 boot scripts fail on Windows due to emoji |
| BUG-SKILL-035 | Open | Medium | Statusline timer shows stale overdue value |
| BUG-SKILL-034 | Fixed | Medium | Context pressure exit incomplete |
```

### Columns

**Bug INDEX.md**: ID, Status, Severity, Title
**Feature INDEX.md**: ID, Status, Priority, Title

### Generation Rules

1. INDEX.md is **auto-generated** — never hand-edited.
2. Regenerated after any status change, new item filing, or archival operation.
3. Lists only non-archived items (files in the directory root, not `archived/`).
4. Sorted by: Open/active statuses first, then by ID number descending (newest first).
5. Does NOT include file sizes or token counts — keeping it minimal reduces its own token cost. A 50-item index at ~80 chars/line = ~4000 chars = ~1000 tokens (vs 56k tokens for full files).

### Regeneration Procedure

The agent that modifies a tracker item is responsible for regenerating the INDEX after each change:

```
1. List all *.md files in the directory (excluding INDEX.md and archived/)
2. For each file, extract: ID (from filename), Status, Severity/Priority, Title (from ## heading)
3. Sort: active statuses first (Open > Investigating > In Progress > Approved > Planning > Pending > Pending Test > Pending Ship > Fixed), then by ID desc
4. Write INDEX.md with the table
```

### Considerations

- INDEX.md should include a generation timestamp comment: `<!-- Generated: YYYY-MM-DD HH:MM -->`
- If two agents regenerate simultaneously, the last write wins — but since INDEX is fully regenerated from source files (not incrementally edited), the result is always correct regardless of who wins.

## Individual File Schema

### BUG-SKILL-XXX.md

```markdown
## BUG-SKILL-XXX — [Title]

- **Severity**: [Critical|High|Medium|Low]
- **Status**: [Open|Investigating|Fixed|Verified|Closed]
- **Reported By**: [pm/qa|skill-lead|human|dm]
- **Assigned To**: [skill-lead]
- **Description**: [description text]
- **Steps to Reproduce**:
  1. [step]
- **Expected**: [expected]
- **Actual**: [actual]

### Discussion

> [YYYY-MM-DD HH:MM] **[author]**: [message]
```

The format is identical to the current entry format, minus the `---` separators and the file-level header. Each file is a single self-contained entry.

### FEAT-SKILL-XXX.md

```markdown
## FEAT-SKILL-XXX — [Title]

- **Priority**: [Critical|High|Medium|Low]
- **Requested By**: [human|pm/qa|skill-lead|dm]
- **Status**: [Pending|Planning|Approved|In Progress|Pending Test|Pending Ship|Shipped|Rejected|On Hold]
- **Owner**: [skill-lead]
- **Description**: [description text]
- **Acceptance Criteria**:
  - [ ] Criterion one

### Discussion

> [YYYY-MM-DD HH:MM] **[author]**: [message]
```

### File Naming Convention

- Filename matches the entry ID exactly: `BUG-SKILL-038.md`, `FEAT-SKILL-051.md`
- Case-sensitive on Linux, case-insensitive on Windows/macOS — use uppercase as defined in the ID format
- No spaces, no special characters beyond the hyphen

## Migration Strategy

### Splitting Algorithm

For each monolithic tracker file (`bugs.md` or `features.md`):

1. Create the target directory: `.squidsquad/[role]/bugs/` or `.squidsquad/[role]/features/`
2. Create the `archived/` subdirectory inside it
3. Parse the file by splitting on `^## (BUG|FEAT)-` patterns — each match starts a new entry
4. For each entry:
   a. Extract the ID from the `## ID — Title` line
   b. Extract the Status from `**Status**: [value]`
   c. Write the entry content to `[ID].md` (including the `## ID — Title` heading)
   d. If the status is a terminal state (`Closed` for bugs, `Shipped` or `Rejected` for features), place the file in `archived/` instead of the root directory
5. Generate `INDEX.md` from the non-archived files
6. Append a migration Discussion entry to each individual file:
   ```
   > [YYYY-MM-DD HH:MM] **migration**: Migrated from monolithic [bugs|features].md to individual file (Schema 2 -> 3).
   ```
7. Rename the original file to `bugs.md.schema2-backup` (or remove it — git history preserves it). Recommendation: **remove it** to avoid confusion, since git history is the backup.
8. Write a migration log to `.squidsquad/pm/migrations/schema-2-to-3.md`

### Edge Cases

**Entry with weird formatting**: Some entries have code blocks, multi-level bullet lists, or custom fields embedded in the description. The parser must split on the `## BUG-` / `## FEAT-` heading pattern only, not on `---` separators (which may appear inside code blocks).

**Cross-references between entries**: Entries reference each other by ID (e.g., "See BUG-SKILL-029"). These are plain text — no file path references — so they work unchanged. The IDs remain the same.

**Discussion entries that mention other items**: Same — plain text IDs, no paths. No changes needed.

**Empty Discussion section**: Some entries may have `### Discussion` with no entries below. Handle gracefully — write the heading even if empty.

**File header**: The monolithic file starts with a header (`# Bug Tracker` + description + `---`). This header is NOT included in individual files. It is conceptually replaced by INDEX.md's header.

**Entries with `---` in their content**: Code blocks or description text may contain `---`. The parser must NOT use `---` as a delimiter. Split only on `^## (BUG|FEAT)-` at the start of a line.

**Multi-line "Suggested Fix" or custom fields**: Some bugs have `- **Suggested Fix**: ...` or features have `- **Scope**: ...` with multi-line content. These are part of the entry and must be kept intact.

**On Hold features**: `On Hold` is not a terminal state — these stay in the root directory, not archived.

### Script Approach

The migration should be implemented as a section in the Schema Changelog of SKILL.md, with instructions for the upgrade agent to execute. The splitting logic itself is straightforward string manipulation that an LLM agent can perform by reading the file and writing individual files. No external script is needed — the upgrade agent reads the monolithic file, parses entries, and writes individual files.

## Archiving Protocol

### When

An item is archived when it reaches a terminal status:
- **Bugs**: `Closed` (after verification) or `Verified` (if skipping the Closed step)
- **Features**: `Shipped` or `Rejected`

### Who

The agent that transitions an item to its terminal status moves the file:
- PM moves bugs to archived after marking `Closed` (Step 5 verify)
- PM moves features to archived after marking `Shipped` (Step 6d delivery fallback)
- DM moves features to archived after marking `Shipped` (Step 2c delivery)
- Skill agent does NOT archive — it marks bugs as `Fixed`, PM verifies and closes

### How

```bash
mv .squidsquad/skill/bugs/BUG-SKILL-029.md .squidsquad/skill/bugs/archived/BUG-SKILL-029.md
```

Then regenerate INDEX.md (which excludes archived items).

### Interaction with "Never Delete Tracker Entries"

**Moving is not deleting.** The file still exists in `archived/`. Git tracks the rename (`git mv` or plain `mv` + `git add`). The full history of every edit to every entry is preserved in git. This is strictly better than the current system where entries accumulate indefinitely in a growing file — archived entries are still accessible via `archived/BUG-SKILL-029.md` or via git history, but they don't consume tokens every cycle.

The rule should be updated to: "Never delete tracker entries — archive closed items to `archived/`, never remove files from `archived/`."

### Does INDEX.md Include Archived Items?

**No.** INDEX.md only lists active (non-archived) items. To find archived items, agents read the `archived/` directory listing or use git history. This is the key token savings mechanism — the index stays small.

However, consider adding an optional `ARCHIVE-INDEX.md` inside `archived/` for rare cases where an agent needs to look up a closed item. This could be auto-generated on each archival. Low priority — git history and directory listing suffice.

## Agent Workflow Changes

### PM Cycle (before -> after)

**Step 5 — Verify Fixed Bugs:**
- Before: `Open .squidsquad/skill/bugs.md` -> grep for `**Status**: Fixed` -> read/edit the monolithic file
- After: `Read .squidsquad/skill/bugs/INDEX.md` -> find entries with Status=Fixed -> `Read .squidsquad/skill/bugs/BUG-SKILL-XXX.md` for each -> `Edit` the individual file -> regenerate INDEX.md -> `mv` file to `archived/` if marking Closed

**Step 6 — Verify Pending Test Features:**
- Before: `Open .squidsquad/skill/features.md` -> grep for `**Status**: Pending Test`
- After: `Read .squidsquad/skill/features/INDEX.md` -> find Pending Test entries -> `Read` + `Edit` individual files -> regenerate INDEX.md

**Step 6d — PM Delivery Fallback:**
- Before: Read `features.md` for Pending Ship items
- After: Read `features/INDEX.md` for Pending Ship items -> read individual files

**Step 7 — Agent Health (stalled agent):**
- Before: `append a Discussion note to the agent's bugs.md`
- After: File a new bug to `bugs/BUG-SKILL-XXX.md` (same as normal bug filing, just to the directory)

**Phase 3 — Planning (writing feature entry):**
- Before: Append feature entry to `features.md`
- After: Create new file `features/FEAT-SKILL-XXX.md` -> regenerate INDEX.md

**Version bump check:**
- Before: `check all agent bug trackers for open bugs (grep bugs.md)`
- After: `Read bugs/INDEX.md` -> count Open/Investigating entries

**Discussion Protocol:**
- Before: `You may write Discussion entries in any agent's bugs.md or features.md.`
- After: `You may write Discussion entries in any agent's bugs/BUG-XXX.md or features/FEAT-XXX.md.`

### Skill Cycle (before -> after)

**Step 2 — Triage Bugs:**
- Before: `Open .squidsquad/skill/bugs.md` -> scan for `**Status**: Open`
- After: `Read .squidsquad/skill/bugs/INDEX.md` -> find Open entries -> `Read .squidsquad/skill/bugs/BUG-SKILL-XXX.md` for each -> fix -> `Edit` individual file -> regenerate INDEX.md

**Step 3 — Implement Features:**
- Before: `Open .squidsquad/skill/features.md` -> find next Approved feature
- After: `Read .squidsquad/skill/features/INDEX.md` -> find Approved entries -> `Read .squidsquad/skill/features/FEAT-SKILL-XXX.md` -> implement -> `Edit` individual file -> regenerate INDEX.md

**Filing Bugs:**
- Before: Append to `skill/bugs.md`
- After: Create new file `skill/bugs/BUG-SKILL-XXX.md` -> regenerate `skill/bugs/INDEX.md`

**File Conventions:**
- Before: `Your tracker files: .squidsquad/skill/bugs.md, .squidsquad/skill/features.md`
- After: `Your tracker files: .squidsquad/skill/bugs/ (INDEX.md + individual files), .squidsquad/skill/features/ (INDEX.md + individual files)`

### DM Cycle (before -> after)

**Step 2 — Scan for Pending Ship:**
- Before: `Read each dev agent's features.md` -> grep for `**Status**: Pending Ship`
- After: `Read each dev agent's features/INDEX.md` -> find Pending Ship entries -> `Read features/FEAT-XXX.md` for each

**Filing:**
- Before: Append to `[role]/bugs.md` or `[role]/features.md`
- After: Create file in `[role]/bugs/` or `[role]/features/` -> regenerate INDEX.md

**File Conventions:**
- Before: `Dev agent trackers: .squidsquad/[ROLE]/features.md, .squidsquad/[ROLE]/bugs.md`
- After: `Dev agent trackers: .squidsquad/[ROLE]/features/, .squidsquad/[ROLE]/bugs/`

## Side Effects

- **Risk 1**: Git conflicts on INDEX.md when two agents modify the same role's tracker simultaneously (e.g., PM verifies a bug while skill files a new one). — Severity: **L** — Mitigation: INDEX.md is fully regenerated from source files, so a conflict is easily resolved by re-running regeneration. Also, SquidSquad currently has only one dev agent (`skill`), and agents run on different cycle intervals so true simultaneity is rare. The `git pull --rebase` step at cycle start handles most timing issues.

- **Risk 2**: statusline.sh breaks because it greps `bugs.md` and `features.md` directly for status counts. — Severity: **H** — Mitigation: Update statusline.sh to grep INDEX.md instead (simpler pattern matching on the table format), or grep across all individual files in the directory. INDEX.md grep is preferred — it's a known-format table.

- **Risk 3**: Windows file locking on individual files when statusline.sh reads while an agent writes. — Severity: **L** — Mitigation: Agents already use atomic writes (tmp+mv) for `current-state`. Individual tracker files are small and writes are infrequent. Git operations handle locking internally. No special mitigation needed beyond existing patterns.

- **Risk 4**: `.gitignore` implications — the `archived/` directories must not be gitignored. — Severity: **L** — Mitigation: Verify `.gitignore` does not contain patterns matching `archived/`. Currently `.gitignore` does not have any such pattern.

- **Risk 5**: Git handles directory renames via `mv` — `git add -A` (used in commit steps) will detect the move and record it as a rename. No special handling needed. — Severity: **L**

- **Risk 6**: Evals test expectations reference `fe/bugs.md` and `be/bugs.md`. — Severity: **M** — Mitigation: Update evals.json expected output to reference the new directory structure.

- **Risk 7**: Large number of individual files in directory — with 38 bugs and 51 features, most will be in `archived/`. Active directory will typically have 5-15 files. Not a filesystem concern. — Severity: **L**

## Edge Cases

- **Empty tracker**: A fresh install has zero entries. `bugs/` and `features/` directories exist with only `INDEX.md` (which has a header and empty table). Agents must handle empty INDEX gracefully.

- **Agent reads INDEX while another agent is mid-regeneration**: Since INDEX is written atomically (write tmp, then mv), the reader gets either the old or new version — never a partial write. Both are valid.

- **Feature with On Hold status**: Not archived — stays in root directory. INDEX shows it. Agent skips it during triage (On Hold is not Approved).

- **Cross-filing bugs**: PM files a bug to skill's tracker. PM creates `skill/bugs/BUG-SKILL-XXX.md` and regenerates `skill/bugs/INDEX.md`. Same mechanism, different author.

- **Very long Discussion section**: Some entries have 10+ Discussion entries. Individual files can grow to 50-100 lines. Still far smaller than the 1000-line monolithic file. No special handling needed.

- **Concurrent archival**: PM archives BUG-SKILL-029 while skill is reading it. Git handles this — the file moves but if skill already has it open in context, it can still edit (git tracks the final state at commit time). Practically impossible since agents pull before acting.

- **Working state file references**: `working-state.md` references task IDs like `BUG-SKILL-029` — these are string IDs, not file paths. No changes needed.

- **Planning artifacts**: Planning files (`FEAT-SKILL-XXX-RESEARCH.md`, etc.) live in `planning/`, not in `features/`. No changes to planning workflow.

## Integration Risks

- **statusline.sh is critical path**: The statusline runs on every assistant message. If it breaks due to missing `bugs.md`/`features.md`, the agent experience degrades visibly. The statusline must be updated to read from INDEX.md or scan the directory. Testing on Windows (PowerShell calling bash) is essential.

- **Feature Intake Process references**: PM Phase 3 writes a feature entry to `features.md`. This must change to creating a file in `features/`. The RESEARCH/CONTEXT/TEST-PLAN subagent prompts reference `features.md` indirectly — they reference planning files which are separate. No impact there.

- **`/squidsquad-status` command**: Reads `bugs.md` and `features.md` for dashboard. Must be updated to read INDEX.md files instead. This is in SKILL.md (line 999).

- **Version bump "zero open bugs" check**: PM and DM both check all agent bug trackers for open bugs before allowing a version bump. Currently they grep `bugs.md`. Must change to reading `bugs/INDEX.md`.

## Upgrade & Migration

- **New config values**:
  - `Tracker Schema`: 2 -> 3

- **New files** (per dev agent role):
  - `.squidsquad/[role]/bugs/INDEX.md`
  - `.squidsquad/[role]/bugs/archived/` (directory)
  - `.squidsquad/[role]/bugs/BUG-[ROLE]-XXX.md` (one per existing entry)
  - `.squidsquad/[role]/features/INDEX.md`
  - `.squidsquad/[role]/features/archived/` (directory)
  - `.squidsquad/[role]/features/FEAT-[ROLE]-XXX.md` (one per existing entry)

- **Removed files** (per dev agent role):
  - `.squidsquad/[role]/bugs.md` (replaced by directory)
  - `.squidsquad/[role]/features.md` (replaced by directory)

- **Template changes**:
  - `references/agent-instructions.md`: 19 path references updated
  - `.squidsquad/templates/dm-agent.md`: 4 path references updated
  - `references/statusline.sh`: 4 file path references + grep patterns updated
  - `SKILL.md`: 22 references updated, Schema Changelog section added, setup Step 6 rewritten, upgrade instructions updated

- **Upgrade steps** (what `/squidsquad-upgrade` must do):
  1. Detect `Tracker Schema: 2` in config.md, current schema is 3
  2. For each dev agent role:
     a. Read the monolithic `bugs.md` and `features.md`
     b. Create `bugs/` and `features/` directories with `archived/` subdirectories
     c. Split each entry into individual files (terminal-status items go to `archived/`)
     d. Generate `INDEX.md` for each directory
     e. Remove the original monolithic files
  3. Regenerate all agent CLAUDE.md files from updated templates
  4. Regenerate statusline.sh from updated references/statusline.sh
  5. Update config.md: set `Tracker Schema` to 3
  6. Write migration log to `pm/migrations/schema-2-to-3.md`

- **Graceful degradation** (what happens if user doesn't upgrade):
  - If agent templates are updated but tracker files are not migrated: **BROKEN** — agents look for `bugs/INDEX.md` which doesn't exist. This is not a graceful scenario.
  - If tracker files are migrated but agent templates are not updated: **BROKEN** — agents look for `bugs.md` which no longer exists.
  - **Both must happen together.** The upgrade is atomic — all template regeneration and file migration happen in one upgrade pass.
  - If a user is on Schema 2 with an older skill version, nothing changes — they keep using monolithic files until they upgrade.

- **Schema 2 fallback check (IMPORTANT)**: Consider adding a fallback to agent templates: "If `bugs/INDEX.md` exists, use Schema 3 workflow. If `bugs.md` exists, use Schema 2 workflow." This adds complexity but provides graceful degradation during the transition window. **Recommendation: Do NOT add fallback.** The upgrade is a single atomic operation — either it completes or it doesn't. Adding dual-path logic to every agent template doubles the maintenance surface for a transient benefit.

## Open Questions

- **Q1**: Should INDEX.md use a markdown table or a simpler format (one line per item, pipe-separated)? — **Why**: Markdown tables are human-readable but slightly harder to parse with grep. A simpler format like `BUG-SKILL-038 | Open | High | PS1 boot scripts fail` is grep-friendly. The table format is recommended because it renders nicely in GitHub and editors, and agents can parse it with simple line splitting.

- **Q2**: Should the INDEX regeneration be a helper script (like statusline.sh) or inline logic in each agent template? — **Why**: A helper script means one place to maintain the logic. Inline means more robust (no dependency on a script existing). Recommendation: inline in agent templates — it's 5-10 lines of logic, and agent templates already contain all other tracker manipulation logic.

- **Q3**: Should archived items be excluded from the git working tree (via `.gitignore`) to reduce `git status` noise? — **Why**: With 30+ archived files, `git status` after moves will show many changes. However, gitignoring archived/ would mean git doesn't track those files, violating "GitHub is the bus." **Answer: No.** Archived files must remain tracked. The git noise is a one-time migration cost.

- **Q4**: How should the existing `bugs.md` and `features.md` be handled after migration — delete or rename to `.bak`? — **Why**: A `.bak` file in the repo creates confusion. Git history is the backup. **Recommendation: Delete.** The file cannot coexist with the directory of the same base name anyway (you can't have both `bugs.md` and `bugs/` confuse agents, though technically they can coexist in a filesystem).

- **Q5**: Should the migration append a Discussion entry to each migrated item? — **Why**: Provides an audit trail of when migration happened. Adds ~1 line per file. **Recommendation: Yes** — append `> [DATE] **migration**: Migrated from monolithic tracker to individual file (Schema 2 -> 3).`

- **Q6**: When regenerating INDEX.md, should agents use atomic writes (tmp+mv)? — **Why**: Prevents partial reads by statusline.sh or concurrent agents. **Recommendation: Yes** — same pattern as current-state writes.

- **Q7**: Should the `## ` heading prefix be kept in individual files or dropped (since the file only has one entry)? — **Why**: Keeping `##` means the format is identical to the current entry format, making migration trivial and individual files renderable as markdown. Dropping it saves 4 characters. **Recommendation: Keep `##`** — consistency and readability outweigh the trivial savings.

## Recommendation

**Feasible with caveats.**

The change is well-scoped and the token savings are substantial (>80% reduction in tracker-related token consumption per cycle). The main caveats are:

1. **Breadth of impact**: 73 actionable references across 10 files must be updated simultaneously. Missing one breaks an agent. This requires careful, file-by-file verification during implementation.

2. **Atomic upgrade**: The migration must be atomic — templates and data must be updated together. No graceful degradation is practical.

3. **statusline.sh**: Must be carefully tested on Windows (bash-on-Windows, PowerShell calling bash) since it's the most time-sensitive consumer of tracker data.

4. **INDEX.md regeneration discipline**: Every agent operation that changes tracker state must regenerate INDEX. Missing a regeneration means INDEX goes stale. The discipline is similar to the existing "always increment counter in config.md" rule, so agents are already trained for this pattern.

The implementation should be done as a single, large commit that updates all templates, migrates all data, and regenerates all agent files. The upgrade agent (from SKILL.md) handles the migration for existing installs.
