## BUG-SKILL-021 — statusline.sh template inlined in SKILL.md instead of externalized as a file

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: human (via pm/qa)
- **Assigned To**: skill-lead
- **Description**: The statusline.sh script is embedded as a code block inside SKILL.md rather than stored as a standalone file in `references/` (e.g. `references/statusline.sh`). This means:
  1. The script cannot be directly copied during setup/upgrade — it must be extracted from markdown
  2. It's inconsistent with the template externalization approach (FEAT-SKILL-017) where CLAUDE.md templates live in `references/agent-instructions.md`
  3. The upgrade flow regenerates boot scripts and templates but has no clean source for statusline.sh
  4. Editing a bash script inside markdown is error-prone (indentation, escaping)

  The fix: move the statusline.sh script to `references/statusline.sh` as a standalone file. SKILL.md setup/upgrade steps reference this file as the source. Setup copies it into `.squidsquad/statusline.sh`. Upgrade regenerates it from the source.
- **Steps to Reproduce**:
  1. Read SKILL.md Step 5b — the entire bash script is inlined in markdown
  2. Run upgrade — statusline.sh is not regenerated because there's no clean source file
- **Expected**: statusline.sh lives as a standalone file in `references/`, setup/upgrade copies it
- **Actual**: Script is embedded in SKILL.md markdown, no standalone source file exists

### Discussion

> [2026-03-29 04:30] **pm/qa**: Filed from human observation. The new Emoji Rich statusline.sh (FEAT-SKILL-031) was implemented in SKILL.md but the live .squidsquad/statusline.sh wasn't regenerated because there's no clean externalized source. Same externalization principle as FEAT-SKILL-017 should apply to statusline.sh.
> [2026-03-29 12:20] **skill-lead**: Fixed. Extracted statusline.sh from SKILL.md into `references/statusline.sh` as standalone source file. Updated SKILL.md Step 5b to copy from `references/statusline.sh` instead of inlining. Updated upgrade flow to regenerate by copying from `references/`. Also regenerated live `.squidsquad/statusline.sh` from new source. Status → Fixed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
