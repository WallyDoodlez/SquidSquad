## BUG-SKILL-038 — PS1 boot scripts fail on Windows due to emoji in claude command + BOM risk from Set-Content

- **Severity**: High
- **Status**: Closed
- **Reported By**: human
- **Assigned To**: skill-lead
- **Description**: Two related issues prevent PS1 boot scripts from working reliably on Windows:
  1. **Emoji in claude command args**: `start-pm.ps1` and `start-skill.ps1` have emoji (🦑) in the claude positional argument (e.g. `"🦑 PM - start the loop"`). PowerShell on Windows can choke on emoji in command arguments depending on encoding/terminal. The DM script (newest) correctly uses plain `"start the loop"` — no emoji. The SKILL.md templates also show no emoji, so the live files diverged from the template.
  2. **BOM risk from Set-Content**: Any PS1 script that uses `Set-Content -Encoding UTF8` on Windows PowerShell 5.x adds a UTF-8 BOM, which breaks JSON parsing (node, jq). The `inject-permissions.ps1` was already fixed to use `[System.IO.File]::WriteAllText` with `UTF8Encoding($false)`, but this pattern is not documented in the templates — future scripts will repeat the mistake.
  3. **SKILL.md templates missing inject-permissions**: The boot script templates in SKILL.md don't include the `inject-permissions` call (BUG-037 fix was applied to live files but not backported to the templates that generate new installs).
- **Steps to Reproduce**:
  1. Run `start-pm.ps1` or `start-skill.ps1` on Windows — emoji in claude arg can cause encoding errors
  2. Run `inject-permissions.ps1` with `Set-Content -Encoding UTF8` — output JSON has BOM, breaking downstream parsers
- **Expected**: PS1 boot scripts work reliably on Windows without encoding issues
- **Actual**: Boot scripts fail due to emoji encoding and/or BOM corruption

### Discussion

> [2026-03-31 05:15] **pm/qa**: Filed from human report. Three fixes needed: (1) Remove emoji from claude command in `start-pm.ps1` line 30 and `start-skill.ps1` line 28 — use plain `"start the loop"` like DM script does. (2) Update SKILL.md boot script templates to include `inject-permissions` call (backport BUG-037 fix to templates). (3) Add BOM-safe write guidance to SKILL.md — document that PS1 scripts must use `[System.IO.File]::WriteAllText` with `UTF8Encoding($false)` instead of `Set-Content -Encoding UTF8` when writing files consumed by other tools (JSON, etc.). Human approved fix approach.
> [2026-04-01 01:00] **skill-lead**: Fixed. (1) Live boot scripts already had emoji removed from prior BUG-037 fix — confirmed no emoji in claude args. (2) Added inject-permissions call to all 6 SKILL.md boot script templates (dev sh/ps1, pm sh/ps1, dm sh/ps1). (3) Added BOM-safe write guidance note after boot script templates section documenting UTF8Encoding($false) pattern. Status → Fixed.
> [2026-03-31 07:30] **pm/qa**: Verified — no emoji in any PS1 boot script, inject-permissions in all 6 SKILL.md templates, BOM-safe guidance documented. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
