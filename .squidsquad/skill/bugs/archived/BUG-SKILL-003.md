## BUG-SKILL-003 — PowerShell boot script logo renders mangled Unicode characters

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The squid logo in `.squidsquad/start-skill.ps1` and `.squidsquad/start-pm.ps1` renders with mangled/garbled Unicode block characters in PowerShell. The `.sh` versions display correctly. This is likely an encoding issue — PowerShell's `Write-Host` may not handle the Unicode block-drawing characters properly without explicit UTF-8 encoding or the PS1 file itself may need a BOM or `[Console]::OutputEncoding` set.
- **Steps to Reproduce**:
  1. Run `.\.squidsquad\start-skill.ps1` in PowerShell
  2. Observe the squid logo output
- **Expected**: Clean squid logo matching the .sh output
- **Actual**: Garbled/mangled Unicode characters in the logo

### Discussion

> [2026-03-27 23:00] **pm/qa**: Reported by human. The .sh scripts render fine — PS1 scripts need encoding fix.
> [2026-03-27 23:20] **pm/qa**: Scope clarification from human: the fix must cover both the generated `.squidsquad/start-*.ps1` files AND the PS1 boot script templates in SKILL.md (lines ~393-405 and ~442-452). The `.sh` templates and generated `.sh` scripts should also be verified as rendering correctly. The fix likely needs `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` at the top of each PS1 script, and the SKILL.md templates must include this line too.
> [2026-03-28 00:30] **skill-lead**: Fixed. Added `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` to both generated PS1 scripts and both PS1 templates in SKILL.md. Also added `-Encoding UTF8` to `Get-Content` calls. Status → Fixed.
> [2026-03-27 23:35] **pm/qa**: Verified. Both generated PS1 files and both SKILL.md PS1 templates have UTF-8 encoding line. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
