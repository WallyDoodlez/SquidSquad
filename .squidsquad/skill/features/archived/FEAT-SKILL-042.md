## FEAT-SKILL-042 — SquidSquad only activates when launched via boot scripts, never on normal Claude sessions

- **Priority**: High
- **Status**: Shipped
- **Requested By**: human
- **Description**: Change the auto-boot mechanism so SquidSquad ONLY activates when launched via a boot script (`start-*.sh` / `start-*.ps1`). A normal `claude` session in the same repo must never trigger SquidSquad auto-boot — no Ralph Loop, no status bar override, no heartbeat. Currently the auto-boot block in CLAUDE.md checks for `.squidsquad/.active-role`, which can be left over from another terminal's boot script, causing unintended SquidSquad activation.
- **Rationale**: The user should be able to open Claude in a SquidSquad-enabled repo and get a normal Claude session. Only explicitly launching via boot scripts should activate SquidSquad. The current file-based trigger (`.active-role`) leaks across terminals.
- **Acceptance Criteria**:
  - [x] Normal `claude` sessions in a SquidSquad repo do NOT auto-boot into SquidSquad
  - [x] Boot scripts are the ONLY way to activate SquidSquad agents
  - [x] No leftover files from one session can trigger auto-boot in another
  - [x] Boot scripts set a session-only signal (e.g. env var `SQUIDSQUAD=1`) that CLAUDE.md checks instead of a file
  - [x] CLAUDE.md auto-boot block updated to check the new signal
  - [x] `.active-role` file no longer used as the trigger (may still be used internally after boot)
  - [x] Status bar, heartbeat, and all SquidSquad features only activate in boot-script sessions
  - [x] SKILL.md boot script templates updated
  - [x] Upgrade steps migrate existing installs

### Discussion

> [2026-03-29 21:50] **pm/qa**: Filed from human request. Original filing was about a "normal mode" boot script, but human clarified: the issue is that SquidSquad should NEVER activate on normal Claude sessions — only via boot scripts. Reframed as an auto-boot mechanism change. Recommended approach: boot scripts set env var `SQUIDSQUAD=1`, CLAUDE.md checks env var instead of `.active-role` file. No file = no leakage across terminals.
> [2026-03-29 21:55] **pm/qa**: Human approved. Status → Approved.
> [2026-03-29 22:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 22:10] **skill-lead**: Complete. Changed auto-boot to use `--append-system-prompt "SQUIDSQUAD_ROLE=<role>"` — session-only, no cross-terminal leakage. Updated CLAUDE.md to check system prompt instead of `.active-role` file. Updated all 4 boot script templates in SKILL.md and all 4 generated scripts in `.squidsquad/`. Boot scripts still write `.active-role` for statusline use only. Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 22:30] **pm/qa**: QA verified — all 9 acceptance criteria pass. CLAUDE.md checks system prompt, boot scripts use `--append-system-prompt`, `.active-role` only for statusline, SKILL.md templates updated, upgrade regenerates scripts. Minor doc issue: README.md line 218 still references old `.active-role` auto-detect — filed as BUG-SKILL-027. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
