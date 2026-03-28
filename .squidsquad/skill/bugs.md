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
> [2026-03-27 23:00] **skill-lead**: Fixed. Replaced hardcoded FE/BE references in opening paragraph, ASCII diagram, and Step 9 confirm message with generic `[role]`/`[N]` placeholders. Also fixed the Ralph Loop section which had the same issue (separate FE and BE loops replaced with single generic `[role]` loop). Status → Fixed.

---

## BUG-SKILL-002 — Ralph Loop section hardcodes FE/BE instead of generic [role]

- **Severity**: Medium
- **Status**: Fixed
- **Reported By**: skill-lead
- **Assigned To**: skill-lead
- **Description**: The Ralph Loop section in SKILL.md had two separate hardcoded loops ("FE Lead Ralph Loop" and "BE Lead Ralph Loop") instead of a single generic `[role] Lead Ralph Loop`. The PM/QA loop also hardcoded `fe/` and `be/` paths instead of using `[role]/`.
- **Steps to Reproduce**:
  1. Read SKILL.md Ralph Loop section
  2. Note the FE and BE specific headings and paths
- **Expected**: A single generic `[role] Lead Ralph Loop` section, and PM/QA loop referencing `[role]/` paths
- **Actual**: Two hardcoded FE/BE loops and hardcoded fe/be paths in PM loop

### Discussion

> [2026-03-27 23:00] **skill-lead**: Discovered while fixing BUG-SKILL-001. Fixed in the same changeset — merged two FE/BE loops into one generic `[role]` loop and updated PM/QA loop references. Status → Fixed.
