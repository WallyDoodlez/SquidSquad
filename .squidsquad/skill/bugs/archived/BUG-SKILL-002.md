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

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
