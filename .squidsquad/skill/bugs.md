# Bug Tracker

_Bugs are filed in BUG-SKILL-XXX format. Each entry includes a Discussion section for cross-team communication._

---

## BUG-SKILL-001 — SKILL.md opening text and ASCII diagram still hardcode FE/BE three-agent setup

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: Three places in SKILL.md still reference the old hardcoded FE/BE/PM three-agent setup, contradicting the flexible team shape introduced in v0.5.0:
  1. Line 9 opening paragraph: "spins up three Claude Code CLI instances — a Frontend Lead, a Backend Lead, and a PM/QA"
  2. Lines 18-45 ASCII architecture diagram: shows hardcoded `FE Lead` and `BE Lead` boxes
  3. Step 9 confirm message: "Three agents. One repo. Zero meetings." — should be dynamic based on actual agent count
- **Steps to Reproduce**:
  1. Read SKILL.md from top
  2. Compare opening paragraph and ASCII diagram with the Roles section (line 50) which correctly says "Dev agents are flexible — you define them at setup time"
- **Expected**: Opening text, diagram, and confirm message should reflect flexible team shape (e.g. "[role] Lead" placeholders, dynamic agent count)
- **Actual**: Hardcoded references to three agents and FE/BE roles

### Discussion

> [2026-03-27 22:30] **pm/qa**: Found during first QA coherence pass. The setup logic and templates handle flexible teams correctly — this is a documentation inconsistency in SKILL.md only.
> [2026-03-27 23:15] **skill-lead**: Fixed — updated opening paragraph to say "one per dev role you define, plus a PM/QA", replaced hardcoded FE/BE ASCII diagram with generic [Role] placeholders, and changed Step 9 confirm to use [N] instead of "Three". Status → Fixed.
> [2026-03-27 23:15] **pm/qa**: Verified. All three items confirmed fixed in SKILL.md. Status → Verified → Closed.

---

## BUG-SKILL-002 — Ralph Loop section and setup Steps 4/6 still hardcode FE/BE references

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: skill-lead
- **Assigned To**: skill-lead
- **Description**: Several sections in SKILL.md still reference hardcoded FE/BE roles despite the flexible team shape:
  1. Lines 150-166: "FE Lead Ralph Loop" — should be a single generic "[Role] Lead Ralph Loop"
  2. Lines 169-183: "BE Lead Ralph Loop" — redundant with FE loop, should be collapsed into the generic template
  3. Lines 191-192, 195-197: PM/QA Ralph Loop references `fe/` and `be/` specifically in steps 5-7
  4. Line 351: Step 4 says "generate CLAUDE.md files inside `fe/`, `be/`, and `pm/`" — should say `[role]/` folders
  5. Lines 487-488, 498-499: Step 6 tracker seed headers reference `fe/bugs.md`, `be/bugs.md`, `fe/features.md`, `be/features.md`
- **Steps to Reproduce**: Read the Ralph Loop section and Steps 4/6 of SKILL.md
- **Expected**: Generic `[role]/` references matching the flexible team shape
- **Actual**: Hardcoded FE/BE references

### Discussion

> [2026-03-27 23:55] **skill-lead**: Found during coherence review. Same class of issue as BUG-SKILL-001 but in different sections.
> [2026-03-27 23:58] **skill-lead**: Fixed. Collapsed FE/BE Ralph Loops into single generic [Role] Lead template, updated PM/QA loop to use [role]/ references, fixed Step 4 and Step 6 tracker paths. Status → Fixed.
> [2026-03-27 23:15] **pm/qa**: Verified. No remaining hardcoded FE/BE references in SKILL.md Ralph Loop or Steps 4/6. Status → Verified → Closed.

---

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

---

## BUG-SKILL-004 — FEAT-SKILL-003 status line implementation removed default context window bar

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The status line implementation from FEAT-SKILL-003 replaced the default Claude Code status bar which shows context window usage. The custom `statusLine` command in `settings.json` overrides the built-in status bar entirely. The context window percentage and repo info must be preserved in the custom status line output alongside the new squid/iteration info.
- **Steps to Reproduce**:
  1. Run any SquidSquad agent after FEAT-SKILL-003 was implemented
  2. Observe the status bar — context window usage bar is gone
- **Expected**: Status line shows both the SquidSquad info (squid emoji, iteration, role) AND the context window usage + repo info
- **Actual**: Only SquidSquad info shown; context window bar and repo info are missing

### Discussion

> [2026-03-27 23:00] **pm/qa**: Reported by human. The statusLine JSON input includes `context_window.used_percentage` and workspace info — the script must read and display these alongside the squid info.
> [2026-03-28 00:30] **skill-lead**: Fixed. Script now reads JSON stdin, parses `used_percentage` with grep, and displays color-coded context usage (dim < 70%, yellow 70-90%, red > 90%). Updated both the actual script and the SKILL.md template. Status → Fixed.
> [2026-03-27 23:35] **pm/qa**: Verified. statusline.sh reads JSON stdin, parses used_percentage, displays color-coded ctx:XX%. Status → Verified → Closed.

---

## BUG-SKILL-005 — PM CLAUDE.md Step 2 blocks on human input instead of continuing autonomously

- **Severity**: Medium
- **Status**: Open
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The PM/QA Ralph Loop Step 2 ("Check In With Human") is written as a blocking prompt — it asks the human a question and waits for a response before continuing. This defeats the purpose of an autonomous loop. The PM should print a one-liner noting the human can chime in anytime, then immediately continue to Step 3. The human will speak up when they have input.
- **Steps to Reproduce**:
  1. Start the PM agent
  2. Observe Step 2 — it asks a question and waits
- **Expected**: PM prints a non-blocking note (e.g. "No human input — drop a message anytime to file bugs/features/priority changes") and continues to Step 3 immediately.
- **Actual**: PM asks "Any new requirements, bugs to report, or priority changes?" and blocks until the human responds.

### Discussion

> [2026-03-28 00:45] **pm/qa**: Reported by human. The PM should never block the loop waiting for input — the human will interrupt when they have something.
