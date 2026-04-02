## FEAT-SKILL-032 — Auto-configure permissions during setup and learn from prompt pressure

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Pending
- **Description**: Two-part feature to eliminate permission prompt friction for SquidSquad agents:

  **1. Pre-configure common permissions at setup:**
  During setup, the boot scripts (`.sh`/`.ps1`) automatically add known-required permissions to `.claude/settings.json` `permissions.allow`. This includes:
  - `Edit(.squidsquad/**)`, `Write(.squidsquad/**)` — tracker/config writes
  - `Bash(git *)` — pull, push, commit, log, status, diff, stash, tag
  - `Bash(code *)` — open files in VS Code (FEAT-SKILL-024)
  - Any test commands from `config.md`
  The boot script handles this via `jq` or sed — no agent involvement, runs before Claude starts.

  **2. Learn from permission prompts:**
  When an agent hits a permission prompt during operation, capture the denied/prompted tool pattern and auto-add it to `.claude/settings.json` via the boot script on next startup. Mechanism:
  - Agent writes prompted permissions to `.squidsquad/[role]/.permission-requests` (gitignored)
  - Boot script reads the file on next start, merges new patterns into `settings.json`, clears the file
  - Over time, the permission set converges to what agents actually need — zero prompts after a few cycles

- **Acceptance Criteria**:
  - [ ] Boot scripts (`.sh`/`.ps1`) auto-add baseline permissions to `settings.json` before launching Claude
  - [ ] Baseline permissions cover all standard SquidSquad operations (git, file edits, test commands)
  - [ ] Permission learning: agents write unrecognized permission requests to a gitignored file
  - [ ] Boot script reads learned permissions on next start and merges into `settings.json`
  - [ ] No duplicate permission entries created
  - [ ] SKILL.md setup documentation updated
  - [ ] Works on both bash and PowerShell

### Discussion

> [2026-03-29 04:10] **pm/qa**: Filed from human request. Two parts: (1) boot scripts pre-configure baseline permissions at setup, (2) agents log permission prompts to a gitignored file, boot script learns and adds them on next startup. Both via shell script, not agent-driven. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
