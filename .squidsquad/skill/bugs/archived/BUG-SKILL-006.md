## BUG-SKILL-006 — Boot script templates use `-p` which makes agents non-interactive

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The SKILL.md boot script templates for dev agents (`.sh` version, line 386) use `claude --permission-mode auto -p "..." --continue`. The `-p` flag runs Claude in non-interactive print mode — it processes the prompt and exits. `--continue` only resumes from a previous conversation, it doesn't make the session interactive. All agents should be interactive so the human can interrupt anytime. The correct approach is `claude --permission-mode auto` (no `-p`, no `--continue`) and rely on the `CLAUDE.md` auto-boot section to detect the role and start the Ralph Loop. The generated `.ps1` script already does this correctly. The `.sh` templates and generated `.sh` scripts need to be fixed to match.
- **Steps to Reproduce**:
  1. Run `bash .squidsquad/start-skill.sh`
  2. Claude processes the `-p` prompt, runs one cycle, and exits — not interactive
- **Expected**: `claude --permission-mode auto` — interactive session, auto-boot handles the rest
- **Actual**: `claude --permission-mode auto -p "..." --continue` — non-interactive, exits after one response

### Discussion

> [2026-03-28 01:40] **pm/qa**: Originally filed as "PS1 missing -p". After discussion with human, clarified that `-p` is wrong — all agents must be interactive. PS1 is actually correct; the `.sh` templates need fixing to remove `-p` and `--continue`.
> [2026-03-28 01:50] **pm/qa**: Revised bug description. The fix is: (1) remove `-p "..." --continue` from `.sh` boot script templates in SKILL.md, (2) update generated `.sh` scripts to just use `claude --permission-mode auto`, (3) ensure CLAUDE.md auto-boot section is present so agents self-start.
> [2026-03-28 01:55] **pm/qa**: Further correction from human. `claude "message"` (positional arg, no `-p`) starts an interactive session with that message sent immediately. The fix for all boot scripts (both `.sh` and `.ps1`, both templates and generated) is: `claude --permission-mode auto "Read .squidsquad/.active-role to find your role, then read .squidsquad/<role>/CLAUDE.md and execute your first Ralph Loop cycle now."` — no `-p`, no `--continue`, just a positional arg. This gives instructions AND stays interactive. The `.sh` scripts need `-p` and `--continue` removed, replaced with positional arg. The `.ps1` scripts need the positional arg added.
> [2026-03-28 02:10] **skill-lead**: Fixed. Replaced `-p "..." --continue` with positional arg `"start the loop"` in all 4 SKILL.md boot script templates and all 4 generated scripts. Updated explanatory text to match. Status → Fixed.
> [2026-03-28 02:15] **pm/qa**: Verified. All 4 boot scripts (generated + templates) use `claude --permission-mode auto "start the loop"`. Interactive + immediate start. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
