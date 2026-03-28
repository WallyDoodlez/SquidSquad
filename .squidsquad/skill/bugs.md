# Bug Tracker

_Bugs are filed in BUG-SKILL-XXX format. Each entry includes a Discussion section for cross-team communication._

---

## BUG-SKILL-001 — SKILL.md opening text and ASCII diagram still hardcode FE/BE three-agent setup

- **Severity**: Medium
- **Status**: Fixed
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

---

## BUG-SKILL-002 — Ralph Loop section and setup Steps 4/6 still hardcode FE/BE references

- **Severity**: Medium
- **Status**: Fixed
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
