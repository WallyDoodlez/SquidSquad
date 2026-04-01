# FEAT-SKILL-051 Test Plan — Tracker Schema 3

## Test Cases

### Happy Path

#### TC-1: Migration from Schema 2 to 3 (splitting monolithic files)
- **Precondition**: Existing install with `Tracker Schema: 2` in config.md, populated `skill/bugs.md` and `skill/features.md` with multiple entries
- **Steps**:
  1. Run the upgrade flow (detect Schema 2, trigger migration)
  2. Migration parses monolithic files by splitting on `^## (BUG|FEAT)-` headings
  3. Each entry is written to its own file in `bugs/` or `features/`
  4. Terminal-status entries go to `archived/` subdirectory
  5. Original monolithic files are deleted
- **Expected**: Each entry exists as an individual `.md` file. File content matches original entry exactly (minus `---` separators and file-level header). No data loss.
- **Verification**:
  ```bash
  ls .squidsquad/skill/bugs/
  ls .squidsquad/skill/features/
  ls .squidsquad/skill/bugs/archived/
  ls .squidsquad/skill/features/archived/
  # Confirm monolithic files are gone:
  test ! -f .squidsquad/skill/bugs.md && echo "PASS" || echo "FAIL"
  test ! -f .squidsquad/skill/features.md && echo "PASS" || echo "FAIL"
  ```

#### TC-2: INDEX.md generation and format
- **Precondition**: `bugs/` directory contains individual bug files with varying statuses
- **Steps**:
  1. Trigger INDEX.md regeneration (or verify it was generated during migration)
  2. Open `bugs/INDEX.md`
- **Expected**: INDEX.md contains a markdown table with columns `| ID | Status | Severity | Title |`. Rows list only non-archived items. Active statuses sort first, then by ID descending. File includes a `<!-- Generated: YYYY-MM-DD HH:MM -->` comment.
- **Verification**:
  ```bash
  cat .squidsquad/skill/bugs/INDEX.md
  # Confirm header row exists:
  grep "| ID | Status | Severity | Title |" .squidsquad/skill/bugs/INDEX.md
  # Confirm no archived items appear:
  # (compare: items in archived/ should NOT have rows in INDEX)
  ```

#### TC-3: Agent reading INDEX to find items by status
- **Precondition**: `bugs/INDEX.md` exists with entries of mixed statuses (Open, Fixed, Investigating)
- **Steps**:
  1. Agent reads `bugs/INDEX.md`
  2. Agent scans table for rows where Status = "Open"
  3. Agent extracts the ID from matching rows
- **Expected**: Agent correctly identifies all Open bug IDs from the table. No false matches from archived items.
- **Verification**:
  ```bash
  grep "| Open |" .squidsquad/skill/bugs/INDEX.md
  ```

#### TC-4: Agent reading/editing individual files
- **Precondition**: Individual bug file exists (e.g., `bugs/BUG-SKILL-038.md`) with Status: Open
- **Steps**:
  1. Agent reads `bugs/BUG-SKILL-038.md`
  2. Agent edits the Status field from Open to Fixed
  3. Agent appends a Discussion entry
  4. Agent regenerates `bugs/INDEX.md`
- **Expected**: Individual file reflects the status change and new Discussion entry. INDEX.md row for BUG-SKILL-038 shows updated status.
- **Verification**:
  ```bash
  grep "**Status**: Fixed" .squidsquad/skill/bugs/BUG-SKILL-038.md
  grep "BUG-SKILL-038.*Fixed" .squidsquad/skill/bugs/INDEX.md
  ```

#### TC-5: Filing a new bug (creates individual file + regenerates INDEX)
- **Precondition**: `bugs/` directory exists with INDEX.md. BUG-SKILL counter in config.md is at N.
- **Steps**:
  1. Agent increments BUG-SKILL counter in config.md to N+1
  2. Agent creates `bugs/BUG-SKILL-{N+1}.md` with standard bug format
  3. Agent regenerates `bugs/INDEX.md`
- **Expected**: New file exists with correct format. INDEX.md includes the new entry. Counter in config.md is incremented.
- **Verification**:
  ```bash
  test -f .squidsquad/skill/bugs/BUG-SKILL-$(cat config_counter).md && echo "PASS"
  grep "BUG-SKILL-.*Open" .squidsquad/skill/bugs/INDEX.md
  ```

#### TC-6: Filing a new feature (creates individual file + regenerates INDEX)
- **Precondition**: `features/` directory exists with INDEX.md. FEAT-SKILL counter in config.md is at M.
- **Steps**:
  1. Agent increments FEAT-SKILL counter in config.md to M+1
  2. Agent creates `features/FEAT-SKILL-{M+1}.md` with standard feature format
  3. Agent regenerates `features/INDEX.md`
- **Expected**: New file exists with correct format. INDEX.md includes the new entry with status Pending. Counter incremented.
- **Verification**:
  ```bash
  test -f .squidsquad/skill/features/FEAT-SKILL-$(cat config_counter).md && echo "PASS"
  grep "FEAT-SKILL-.*Pending" .squidsquad/skill/features/INDEX.md
  ```

#### TC-7: Archiving a closed bug (mv to archived/, INDEX excludes it)
- **Precondition**: `bugs/BUG-SKILL-029.md` exists in root directory with Status: Closed. INDEX.md lists it.
- **Steps**:
  1. PM marks bug as Closed
  2. PM moves file: `mv bugs/BUG-SKILL-029.md bugs/archived/BUG-SKILL-029.md`
  3. PM regenerates INDEX.md
- **Expected**: File exists in `archived/`. File does NOT exist in root `bugs/`. INDEX.md does NOT list BUG-SKILL-029.
- **Verification**:
  ```bash
  test -f .squidsquad/skill/bugs/archived/BUG-SKILL-029.md && echo "PASS"
  test ! -f .squidsquad/skill/bugs/BUG-SKILL-029.md && echo "PASS"
  grep -v "BUG-SKILL-029" .squidsquad/skill/bugs/INDEX.md > /dev/null && echo "PASS"
  ```

#### TC-8: Archiving a shipped feature (mv to archived/, INDEX excludes it)
- **Precondition**: `features/FEAT-SKILL-001.md` exists with Status: Shipped
- **Steps**:
  1. Agent moves file: `mv features/FEAT-SKILL-001.md features/archived/FEAT-SKILL-001.md`
  2. Agent regenerates INDEX.md
- **Expected**: File exists in `archived/`. INDEX.md does NOT list FEAT-SKILL-001.
- **Verification**:
  ```bash
  test -f .squidsquad/skill/features/archived/FEAT-SKILL-001.md && echo "PASS"
  ! grep "FEAT-SKILL-001" .squidsquad/skill/features/INDEX.md && echo "PASS"
  ```

#### TC-9: statusline.sh reads from INDEX instead of monolithic files
- **Precondition**: Schema 3 migration complete. Updated statusline.sh deployed. INDEX.md files exist with known counts.
- **Steps**:
  1. Run statusline.sh
  2. Inspect output for bug/feature counts
- **Expected**: statusline.sh correctly reports counts of Open bugs and actionable features by parsing INDEX.md tables (not monolithic files). No errors about missing `bugs.md` or `features.md`.
- **Verification**:
  ```bash
  bash .squidsquad/statusline.sh 2>&1 | grep -v "No such file"
  # Confirm counts match manual INDEX.md grep:
  grep -c "| Open |" .squidsquad/skill/bugs/INDEX.md
  ```

#### TC-10: Cross-agent writes (PM writes Discussion to skill's tracker)
- **Precondition**: `skill/bugs/BUG-SKILL-035.md` exists. PM agent has write access.
- **Steps**:
  1. PM reads `skill/bugs/INDEX.md` to find the bug
  2. PM reads `skill/bugs/BUG-SKILL-035.md`
  3. PM appends a Discussion entry to the individual file
  4. PM regenerates `skill/bugs/INDEX.md` (if status changed)
- **Expected**: Discussion entry is appended correctly. File is well-formed. No corruption of other entries (since each entry is its own file, cross-agent writes cannot corrupt unrelated entries).
- **Verification**:
  ```bash
  grep "pm/qa" .squidsquad/skill/bugs/BUG-SKILL-035.md
  ```

---

### Edge Cases

#### TC-11: Empty tracker (zero entries, INDEX has header only)
- **Precondition**: Fresh install with no bugs or features filed yet
- **Steps**:
  1. Agent reads `bugs/INDEX.md`
  2. Agent attempts to find Open bugs
- **Expected**: INDEX.md contains the header and column row but zero data rows. Agent handles empty result gracefully (no errors, proceeds to next step).
- **Verification**:
  ```bash
  wc -l .squidsquad/skill/bugs/INDEX.md
  # Should be ~4 lines (header, blank, column header, separator)
  ```

#### TC-12: Entry with code blocks in description (parser does not split on `---` inside code blocks)
- **Precondition**: Monolithic `bugs.md` contains an entry whose Description includes a fenced code block with `---` inside it (e.g., YAML front matter or markdown separators in examples)
- **Steps**:
  1. Run migration
  2. Check the resulting individual file
- **Expected**: The entire entry (including the code block with `---`) is kept intact in a single file. The parser splits only on `^## BUG-` or `^## FEAT-` headings, NOT on `---`.
- **Verification**:
  ```bash
  # The individual file should contain the code block with --- intact:
  grep -A2 '```' .squidsquad/skill/bugs/BUG-SKILL-XXX.md
  # File should NOT be truncated at the --- inside the code block
  ```

#### TC-13: Entry with multi-line Discussion entries
- **Precondition**: An entry has Discussion entries spanning multiple lines (continuation `>` lines)
- **Steps**:
  1. Run migration
  2. Read the resulting individual file
- **Expected**: Multi-line Discussion entries are preserved intact. All continuation lines are included in the same file.
- **Verification**:
  ```bash
  # Count Discussion entries in original vs individual file — should match
  grep -c "^>" .squidsquad/skill/bugs/BUG-SKILL-XXX.md
  ```

#### TC-14: Multiple agents regenerating INDEX near-simultaneously
- **Precondition**: Two agents both modify different items in the same tracker directory at roughly the same time
- **Steps**:
  1. Agent A edits `BUG-SKILL-035.md` and regenerates INDEX.md
  2. Agent B edits `BUG-SKILL-038.md` and regenerates INDEX.md (shortly after)
- **Expected**: The last INDEX.md write wins, but since INDEX is fully regenerated from all source files on disk, it reflects BOTH changes. No data loss. Git merge on pull handles any commit conflicts.
- **Verification**:
  ```bash
  # After both agents push and pull, INDEX should contain both updated entries:
  grep "BUG-SKILL-035" .squidsquad/skill/bugs/INDEX.md
  grep "BUG-SKILL-038" .squidsquad/skill/bugs/INDEX.md
  ```

#### TC-15: Archived directory listing
- **Precondition**: Multiple items have been archived
- **Steps**:
  1. List contents of `bugs/archived/`
  2. Confirm all terminal-status items are present
- **Expected**: `archived/` contains all Closed/Verified bugs. Files are intact and readable. No files are missing.
- **Verification**:
  ```bash
  ls .squidsquad/skill/bugs/archived/
  # Each file should have a terminal status:
  grep "**Status**:" .squidsquad/skill/bugs/archived/*.md
  ```

---

### Side Effect Regression Tests

#### TC-16: ID counter mechanism still works (config.md counters)
- **Precondition**: Schema 3 migration complete. config.md has BUG-SKILL and FEAT-SKILL counters.
- **Steps**:
  1. Read current counter values from config.md
  2. File a new bug
  3. Read counter values again
- **Expected**: Counter increments by 1. Counter format and location in config.md unchanged. No migration touched the counter fields.
- **Verification**:
  ```bash
  grep "BUG-SKILL" .squidsquad/config.md
  grep "FEAT-SKILL" .squidsquad/config.md
  ```

#### TC-17: Discussion entry format unchanged
- **Precondition**: Individual files exist post-migration
- **Steps**:
  1. Read Discussion section of any individual file
  2. Agent appends a new Discussion entry
- **Expected**: Discussion entries still use the format `> [YYYY-MM-DD HH:MM] **[role]**: [message]`. No format changes from Schema 2.
- **Verification**:
  ```bash
  grep "^> \[" .squidsquad/skill/bugs/BUG-SKILL-038.md
  ```

#### TC-18: Planning artifacts unaffected (still in planning/)
- **Precondition**: Planning files exist in `.squidsquad/skill/planning/` (e.g., FEAT-SKILL-051-RESEARCH.md)
- **Steps**:
  1. Verify planning directory structure unchanged after migration
  2. Verify agents still reference planning files by the same path convention
- **Expected**: All files in `planning/` are untouched. Planning artifacts are NOT moved to `features/`. Path convention `planning/FEAT-SKILL-XXX-*.md` unchanged.
- **Verification**:
  ```bash
  ls .squidsquad/skill/planning/
  test -f .squidsquad/skill/planning/FEAT-SKILL-051-RESEARCH.md && echo "PASS"
  ```

#### TC-19: Working state file references (task IDs, not paths)
- **Precondition**: `working-state.md` references a task by ID (e.g., `BUG-SKILL-038`)
- **Steps**:
  1. Read working-state.md
  2. Verify it uses task IDs, not file paths
- **Expected**: Working state uses string IDs like `BUG-SKILL-038`, not paths like `bugs/BUG-SKILL-038.md`. No changes needed to working-state format.
- **Verification**:
  ```bash
  grep "Task" .squidsquad/skill/working-state.md
  # Should show an ID, not a path
  ```

#### TC-20: Git diffs show meaningful per-item changes
- **Precondition**: Schema 3 is active. Agent edits a single bug file.
- **Steps**:
  1. Edit `bugs/BUG-SKILL-038.md` (change status)
  2. Run `git diff`
- **Expected**: Git diff shows changes only in the single file that was edited. No diff noise from other entries (unlike monolithic file where changing one entry showed the entire file in diff context).
- **Verification**:
  ```bash
  git diff --stat
  # Should show only the edited file and INDEX.md, not dozens of entries
  ```

---

### Upgrade Verification Tests

#### TC-21: Schema 2 install migrates cleanly to Schema 3
- **Precondition**: Fresh clone of a Schema 2 install with populated trackers
- **Steps**:
  1. Run upgrade flow
  2. Verify no errors during migration
- **Expected**: Migration completes without errors. All directories created. All files written. config.md updated.
- **Verification**:
  ```bash
  grep "Tracker Schema.*3" .squidsquad/config.md
  ```

#### TC-22: All entries preserved (count before = count after)
- **Precondition**: Count total entries in monolithic files before migration
- **Steps**:
  1. Before migration: `grep -c "^## BUG-SKILL-" skill/bugs.md` and `grep -c "^## FEAT-SKILL-" skill/features.md`
  2. Run migration
  3. After migration: count files in `bugs/` + `bugs/archived/` and `features/` + `features/archived/`
- **Expected**: Total file count (root + archived) equals original entry count for both bugs and features. Zero entries lost.
- **Verification**:
  ```bash
  # Count individual files (exclude INDEX.md):
  ls .squidsquad/skill/bugs/*.md .squidsquad/skill/bugs/archived/*.md 2>/dev/null | grep -v INDEX | wc -l
  ls .squidsquad/skill/features/*.md .squidsquad/skill/features/archived/*.md 2>/dev/null | grep -v INDEX | wc -l
  ```

#### TC-23: Terminal-status items land in archived/
- **Precondition**: Monolithic bugs.md contains entries with Status: Closed and Status: Verified
- **Steps**:
  1. Run migration
  2. Check archived/ directories
- **Expected**: All Closed and Verified bugs are in `bugs/archived/`. All Shipped and Rejected features are in `features/archived/`. On Hold features are NOT archived.
- **Verification**:
  ```bash
  # All archived bugs should have terminal status:
  for f in .squidsquad/skill/bugs/archived/*.md; do grep "**Status**:" "$f"; done
  # No On Hold features in archived:
  grep -l "On Hold" .squidsquad/skill/features/archived/*.md 2>/dev/null && echo "FAIL" || echo "PASS"
  ```

#### TC-24: Active items land in root directory
- **Precondition**: Monolithic files contain entries with non-terminal statuses (Open, Investigating, In Progress, Approved, etc.)
- **Steps**:
  1. Run migration
  2. Check root directories (not archived/)
- **Expected**: All non-terminal-status entries are in the root `bugs/` or `features/` directory, not in `archived/`.
- **Verification**:
  ```bash
  # All root-level bugs should have non-terminal status:
  for f in .squidsquad/skill/bugs/BUG-*.md; do grep "**Status**:" "$f"; done
  # None should be Closed or Verified
  ```

#### TC-25: Migration Discussion entry appended to each file
- **Precondition**: Migration has run
- **Steps**:
  1. Read any individual file
  2. Check for migration Discussion entry
- **Expected**: Each migrated file contains: `> [DATE] **migration**: Migrated from monolithic [bugs|features].md to individual file (Schema 2 -> 3).`
- **Verification**:
  ```bash
  grep "migration.*Schema 2" .squidsquad/skill/bugs/BUG-SKILL-038.md
  grep "migration.*Schema 2" .squidsquad/skill/features/FEAT-SKILL-001.md
  ```

#### TC-26: Old monolithic files deleted
- **Precondition**: Migration has run
- **Steps**:
  1. Check for `bugs.md` and `features.md` in role directory
- **Expected**: Neither `bugs.md` nor `features.md` exists in the role root. The `bugs/` and `features/` directories have replaced them.
- **Verification**:
  ```bash
  test ! -f .squidsquad/skill/bugs.md && echo "PASS" || echo "FAIL"
  test ! -f .squidsquad/skill/features.md && echo "PASS" || echo "FAIL"
  ```

#### TC-27: config.md schema bumped to 3
- **Precondition**: Migration has run
- **Steps**:
  1. Read config.md
- **Expected**: `Tracker Schema` field shows `3` (previously `2`).
- **Verification**:
  ```bash
  grep "Tracker Schema" .squidsquad/config.md
  ```

#### TC-28: Agent CLAUDE.md files regenerated correctly
- **Precondition**: Migration has run. Updated templates in `references/agent-instructions.md` are available.
- **Steps**:
  1. Read `.squidsquad/skill/CLAUDE.md`
  2. Read `.squidsquad/pm/CLAUDE.md`
  3. Verify references point to new paths
- **Expected**: All 6 references in skill/CLAUDE.md now point to `bugs/INDEX.md`, `bugs/BUG-SKILL-XXX.md`, `features/INDEX.md`, `features/FEAT-SKILL-XXX.md` patterns. All 6 references in pm/CLAUDE.md similarly updated. No remaining references to monolithic `bugs.md` or `features.md` (as file paths for reading/writing).
- **Verification**:
  ```bash
  # Should find zero references to monolithic paths:
  grep -c "skill/bugs\.md" .squidsquad/skill/CLAUDE.md
  grep -c "skill/features\.md" .squidsquad/skill/CLAUDE.md
  # Both should return 0
  ```

---

## Smoke Tests

- [ ] `bugs/` directory exists for each dev agent role
- [ ] `features/` directory exists for each dev agent role
- [ ] `bugs/archived/` subdirectory exists
- [ ] `features/archived/` subdirectory exists
- [ ] `bugs/INDEX.md` exists and is non-empty
- [ ] `features/INDEX.md` exists and is non-empty
- [ ] INDEX.md has valid markdown table header
- [ ] At least one individual bug file exists in `bugs/`
- [ ] At least one individual feature file exists in `features/`
- [ ] `config.md` shows `Tracker Schema: 3`
- [ ] `bugs.md` monolithic file does NOT exist
- [ ] `features.md` monolithic file does NOT exist
- [ ] `statusline.sh` runs without errors
- [ ] `statusline.sh` reports correct Open bug count
- [ ] Filing a new bug creates a file and updates INDEX
- [ ] Archiving an item removes it from INDEX

---

## Regression Risks

- **statusline.sh breakage**: Runs every assistant message. If it still references `bugs.md`/`features.md`, all agents lose their status bar. Watch for: grep errors, "No such file" warnings, incorrect counts.
- **Missing template reference**: 73 references across 10 files. A single missed reference means an agent looks for a file that does not exist. Watch for: agents reporting "file not found" during triage or feature pickup.
- **INDEX.md staleness**: If an agent modifies a tracker item but forgets to regenerate INDEX, subsequent agents see stale data. Watch for: INDEX showing "Open" for an item that was already Fixed.
- **Partial migration**: If migration crashes mid-way, some entries may be split while others remain in the monolithic file (which may have been partially consumed). Watch for: entry count mismatch, duplicate entries.
- **Windows path handling**: `mv` and directory creation behave differently on Windows bash vs native. Watch for: permission errors, path separator issues in statusline.sh.
- **Git merge conflicts on INDEX.md**: When PM and skill both push changes to the same role's INDEX.md, rebase may conflict. Watch for: merge conflict markers in INDEX.md. Mitigation: regenerate INDEX after resolving.
- **Evals regression**: `evals/evals.json` references `fe/bugs.md` and `be/bugs.md`. If not updated, eval assertions fail. Watch for: eval test failures post-migration.
- **DM template not updated**: `.squidsquad/templates/dm-agent.md` has 4 references. If missed, DM agent breaks when activated. Watch for: DM looking for monolithic files.
- **On Hold features incorrectly archived**: On Hold is NOT a terminal state. If the migration parser treats it as terminal, active items disappear from INDEX. Watch for: On Hold features missing from root directory.
- **Code blocks with `## ` headings**: If an entry's description contains a line starting with `## ` inside a code block, the parser could incorrectly split the entry. Watch for: truncated entries, orphaned file fragments.
