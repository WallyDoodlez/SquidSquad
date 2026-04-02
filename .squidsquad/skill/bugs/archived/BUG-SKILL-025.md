## BUG-SKILL-025 — Skill agent doesn't copy updated references to live .squidsquad/ after feature implementation

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: When the skill agent implements features that change `references/statusline.sh` or add new reference files (like hint pool files), it updates the reference files but does not copy them to the live `.squidsquad/` location. This means the changes don't take effect in the running installation until a manual copy or upgrade is performed. FEAT-SKILL-037 updated `references/statusline.sh` and added `references/hints-*.txt` but the live `statusline.sh` was stale and hint files were missing.
- **Steps to Reproduce**:
  1. Skill agent implements FEAT-SKILL-037
  2. `references/statusline.sh` updated, `references/hints-*.txt` created
  3. `.squidsquad/statusline.sh` still has old version, no hint files in `.squidsquad/`
  4. Status bar shows no line 2
- **Expected**: After implementing features that change reference files, skill agent should also update the live copies in `.squidsquad/`
- **Actual**: Only reference files updated; live copies stale

### Discussion

> [2026-03-29 17:00] **pm/qa**: Filed after human reported no line 2 in status bar post FEAT-SKILL-037 ship. PM manually copied the files. Skill agent's Step 3 (implement features) or its CLAUDE.md should instruct it to also update live copies when changing reference files.
> [2026-03-29 17:50] **skill-lead**: Fixed. Added Step 9 "Copy changed references to live" in both `references/agent-instructions.md` (dev template) and `skill/CLAUDE.md`. Step instructs agents to copy any modified `references/` files to `.squidsquad/` after implementation. Also copied current reference files to live location now. Status → Fixed.
> [2026-03-29 18:40] **pm/qa**: Verified. New Step 9 in agent-instructions.md dev template and skill/CLAUDE.md instructs agents to copy modified references/ files to .squidsquad/. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
