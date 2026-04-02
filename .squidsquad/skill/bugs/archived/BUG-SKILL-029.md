## BUG-SKILL-029 — Boot scripts use `--permission-mode auto` instead of `--enable-auto-mode`

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: All 4 generated boot scripts and the SKILL.md boot script templates use `claude --permission-mode auto` to launch agents. The correct flag for auto permission mode is `--enable-auto-mode`. This means agents may not be launching with the intended permission level.
- **Steps to Reproduce**:
  1. Read `.squidsquad/start-skill.sh` line 22
  2. Read `.squidsquad/start-pm.ps1` line 23
  3. All use `--permission-mode auto` instead of `--enable-auto-mode`
- **Expected**: `claude --enable-auto-mode --append-system-prompt "SQUIDSQUAD_ROLE=<role>" "start the loop"`
- **Actual**: `claude --permission-mode auto --append-system-prompt "SQUIDSQUAD_ROLE=<role>" "start the loop"`
- **Affected Files**:
  - `.squidsquad/start-skill.sh`
  - `.squidsquad/start-skill.ps1`
  - `.squidsquad/start-pm.sh`
  - `.squidsquad/start-pm.ps1`
  - `SKILL.md` (all boot script templates)

### Discussion

> [2026-03-29 22:35] **pm/qa**: Filed from human report. The correct CLI flag is `--enable-auto-mode`, not `--permission-mode auto`. Affects all boot scripts (generated and templates). High severity — agents may not run with correct permissions.
> [2026-03-29 23:20] **skill-lead**: Fixed all 4 boot scripts (start-skill.sh/ps1, start-pm.sh/ps1), all SKILL.md templates (4 occurrences + 1 docs reference), and README.md (3 occurrences). All now use `--enable-auto-mode`. Status → Fixed.
> [2026-03-30 01:00] **pm/qa**: Verified — all 4 boot scripts use --enable-auto-mode, old flag only in historical references. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
