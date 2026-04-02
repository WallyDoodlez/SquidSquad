## FEAT-SKILL-051 — Split tracker files into individual entries with index (Tracker Schema 3)

- **Priority**: High
- **Requested By**: human
- **Status**: Shipped
- **Description**: Replace monolithic `bugs.md` and `features.md` with individual files per item plus a lightweight auto-generated index. Currently tracker files are ~56k tokens combined and growing — agents read/grep large files every cycle to find the few entries they need. Splitting eliminates wasted token consumption while preserving git diff audit trails (non-negotiable project philosophy: "GitHub is the bus").
- **New structure**:
  ```
  .squidsquad/skill/
    bugs/
      INDEX.md              ← auto-generated, ~1 line per item (ID | Status | Severity | Title)
      BUG-SKILL-037.md      ← full entry with Description, Steps, Discussion
      BUG-SKILL-038.md
      archived/             ← closed/verified items moved here
    features/
      INDEX.md
      FEAT-SKILL-050.md
      FEAT-SKILL-051.md
      archived/             ← shipped/rejected items moved here
  ```
- **How agents work with it**:
  - **Find items by status**: Read `INDEX.md` (~50 lines) instead of grepping 1600-line file
  - **Read an item**: `Read(.squidsquad/skill/bugs/BUG-SKILL-038.md)` — ~30 lines, not 1000
  - **Update an item**: `Edit` the individual file — no risk of touching other entries
  - **Append Discussion**: Same protocol, just in the individual file
  - **Archive**: Move closed items to `archived/` subfolder. Git history preserves them. Index auto-excludes archived items.
  - **Index regeneration**: After any status change, agent regenerates INDEX.md from the non-archived files
- **Migration**: Script to split existing `bugs.md` / `features.md` into individual files. Bump tracker schema to 3 in config.md.
- **Scope**:
  - All agent templates (PM, skill, DM) updated to use new file structure
  - SKILL.md setup and upgrade flows updated
  - Discussion protocol unchanged (still append-only, same format)
  - ID counter logic unchanged
  - PM CLAUDE.md grep/verify patterns updated
  - Git diff audit trail fully preserved — every change to every item is a visible diff
- **Acceptance Criteria**:
  - [ ] Individual files per bug and feature entry
  - [ ] Auto-generated INDEX.md with ID, status, severity/priority, title
  - [ ] Archived subfolder for closed/shipped items
  - [ ] Migration script splits existing monolithic files into individual entries
  - [ ] All agent CLAUDE.md templates updated for new structure
  - [ ] SKILL.md setup flow generates new structure for fresh installs
  - [ ] SKILL.md upgrade flow migrates existing installs from schema 2 → 3
  - [ ] config.md tracker schema bumped to 3
  - [ ] Git diffs show meaningful per-item changes (not binary, not monolithic)
  - [ ] Token consumption per cycle reduced by >80% for tracker reads

### Discussion

> [2026-03-31 05:50] **pm/qa**: Human approved. Status → Planning. Beginning intake process.
> [2026-03-31 07:00] **pm/qa**: Phase 1 (research), Phase 2 (discussion), Phase 3 (test plan) complete. Locked decisions: markdown table INDEX, inline regen, no gitignore on archived, delete old files, append migration note. 28 test cases, 16 smoke tests. Human approved. Status → Approved.
> [2026-04-01 01:15] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-31 05:45] **pm/qa**: Filed from human discussion. Human's goal: reduce token consumption from tracker file reads. Explored SQLite (rejected — kills git diffs, violates "GitHub is the bus" philosophy) and status index shim (band-aid, files still grow). Human chose individual files + index as the right balance of token savings and git audit trail. This is a big structural change (tracker schema 3) touching all agent templates — needs proper planning via Feature Intake Process. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
> [2026-04-01 01:30] **skill-lead**: Implementation complete. Migrated 38 bugs + 51 features to individual files. Updated 73 references across 10 files (agent-instructions.md, SKILL.md, statusline.sh, dm-agent.md, skill/CLAUDE.md, pm/CLAUDE.md, README.md, evals.json). All smoke tests passing. Schema bumped to 3. Status → Pending Test.
> [2026-04-02 00:00] **pm/qa**: Verified — 28/28 test cases PASS (QA subagent). Migration complete, INDEX files correct, agent templates updated, archived/ structure valid, no regressions. delivery: skip (internal structural change, no user-facing delivery needed). Status → Pending Ship.
> [2026-04-02 00:15] **dm**: No delivery work needed (delivery: skip). Status → Shipped.
