# FEAT-SKILL-051 Context — Tracker Schema 3 (Individual Files + Index)

## Scope

Replace monolithic `bugs.md` and `features.md` with individual files per entry plus auto-generated INDEX.md. Migrate all existing entries. Update all agent templates, SKILL.md, statusline, and README. Bump tracker schema to 3 in config.md. Token savings >80% per cycle.

## Locked Decisions (human decided)

- **INDEX.md format**: Markdown table (`| ID | Status | Severity | Title |`). Renders on GitHub, agents parse by splitting lines.
- **INDEX regeneration**: Inline in agent templates (5-10 lines of logic per template). No external script dependency. Matches existing pattern where agents handle all tracker manipulation inline.
- **Archived items in git**: Tracked. No `.gitignore` on `archived/`. Git tracks all tracker files — non-negotiable project philosophy ("GitHub is the bus").
- **Old monolithic files after migration**: Delete. Git history is the backup. Can't have `bugs.md` file alongside `bugs/` directory without confusion.
- **Migration Discussion entry**: Yes. Append `> [DATE] **migration**: Migrated from monolithic tracker to individual file (Schema 2 -> 3).` to each migrated item.

## Dev Discretion (dev agent can choose)

- **Parsing approach for migration**: How to split the monolithic files (regex, line-by-line, etc.) — as long as all entries are correctly extracted.
- **INDEX.md sorting**: Active statuses first, then by ID descending (recommended in research) — dev can adjust if a different sort is more practical.
- **Atomic write pattern for INDEX**: tmp+mv recommended but dev can use direct write if race conditions are negligible.
- **Order of template updates**: Dev decides which files to update first, as long as all 73 references are covered.

## Side Effect Mitigations (required)

- **statusline.sh must be updated**: Currently greps `bugs.md`/`features.md` for status counts. Must change to grep INDEX.md. Critical path — runs every assistant message.
- **All 73 references must be updated**: Missing one reference breaks an agent. Dev must verify every reference from the research doc is addressed.
- **Migration is atomic**: Templates and data must be updated together. No partial migration.
- **INDEX.md regeneration after every status change**: Every agent operation that modifies a tracker item must regenerate the relevant INDEX.md.

## Upgrade Path (required)

- Detect `Tracker Schema: 2` in config.md
- For each dev agent role: split monolithic files into individual files, terminal-status items go to `archived/`
- Generate INDEX.md for each directory
- Delete original monolithic files
- Regenerate all agent CLAUDE.md files from updated templates
- Regenerate statusline.sh from updated references/statusline.sh
- Update config.md: set `Tracker Schema` to 3
- Write migration log

## Out of Scope

- SQLite or other database backends (rejected — kills git diffs)
- Dual-path logic for Schema 2 + 3 coexistence (atomic migration, no fallback)
- ARCHIVE-INDEX.md for archived items (low priority, git history suffices)
- Changes to ID counter mechanism (stays in config.md, unchanged)
- Changes to Discussion entry format (unchanged)
- Changes to planning artifact paths (stay in `planning/`, unaffected)
