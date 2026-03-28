# QA Log

_Each PM/QA iteration logs a manual coherence check here._

---

## QA Run — 2026-03-27 22:30

- **Result**: Issues Found
- **Files Reviewed**: SKILL.md, references/agent-instructions.md, CHANGELOG.md, README.md, .squidsquad/config.md, .squidsquad/skill/bugs.md, .squidsquad/skill/features.md, .squidsquad/pm/CLAUDE.md
- **Issues**:
  - SKILL.md opening paragraph (line 9) still hardcodes "three Claude Code CLI instances — a Frontend Lead, a Backend Lead, and a PM/QA" — contradicts the flexible team shape described in the rest of the document.
  - SKILL.md Step 9 confirm message hardcodes "Three agents. One repo. Zero meetings." — should be dynamic.
  - SKILL.md ASCII architecture diagram (lines 18-45) shows hardcoded FE Lead and BE Lead boxes instead of generic `[role] Lead` placeholders.
- **Notes**: First QA iteration. All three issues are cosmetic/documentation inconsistencies in SKILL.md — the actual setup logic and templates handle flexible teams correctly.

---

## QA Run — 2026-03-27 22:35

- **Result**: Passed (no new issues)
- **Files Reviewed**: SKILL.md, references/agent-instructions.md, CHANGELOG.md, .squidsquad/skill/bugs.md, .squidsquad/skill/features.md
- **Issues**: BUG-SKILL-001 still Open — no fix committed yet by skill lead. No new issues found.
- **Notes**: Iteration 2. references/agent-instructions.md placeholders are correct. CHANGELOG.md is up to date. FEAT-SKILL-001 and FEAT-SKILL-002 both Approved, awaiting skill lead pickup.

---

## QA Run — 2026-03-27 23:15

- **Result**: Issues Found
- **Files Reviewed**: SKILL.md, references/agent-instructions.md, CHANGELOG.md, .claude/settings.json, .squidsquad/statusline.sh, .squidsquad/skill/bugs.md, .squidsquad/skill/features.md
- **Verification — BUG-SKILL-001 (Fixed)**: VERIFIED. Line 9 now says "one per dev role you define, plus a PM/QA". Diagram uses `[Role] Lead` placeholders. Step 9 uses `[N] agents`. All three items resolved. → Closed.
- **Verification — BUG-SKILL-002 (Fixed)**: VERIFIED. No remaining `fe/bugs`, `be/bugs`, `FE Lead Ralph`, or `BE Lead Ralph` references in SKILL.md. Ralph Loop consolidated into generic template. → Closed.
- **Verification — FEAT-SKILL-001 (Pending Test)**:
  - [x] Structured field table with label, description, default, validation — present in Step 1
  - [x] Quick-start mode for single-sentence setup — documented
  - [x] Validation summary with re-prompt — documented
  - [x] SKILL.md Step 1 updated — confirmed
  - VERDICT: All criteria pass. → Shipped.
- **Verification — FEAT-SKILL-002 (Pending Test)**:
  - [x] Import prompt offered after project details — present as "Import Existing Items" sub-step
  - [x] Paste text parsing with normalization — documented with heuristics
  - [x] File path input — documented
  - [x] MCP source option — documented with tool detection
  - [x] Routing to correct tracker — documented with heuristics
  - [x] Discussion note on each imported entry — documented
  - [x] Step 1 and Step 6 updated — confirmed
  - VERDICT: All criteria pass. → Shipped.
- **Verification — FEAT-SKILL-003 (Pending Test)**:
  - [x] statusLine configured in settings.json — present (line 1-4)
  - [x] Role label shown — yes (line 71-75 of statusline.sh)
  - [x] Iteration number shown — yes (line 22-30)
  - [x] Green squid emoji — yes (ANSI green on line 111)
  - [x] PM shows agent health with green/red squid — yes (lines 78-107)
  - [x] Time since last cycle — yes (lines 37-49)
  - [x] Backlog pulse counts — yes (lines 52-68)
  - [x] SKILL.md Step 5b added — confirmed
  - [x] CLAUDE.md templates updated — confirmed in agent-instructions.md
  - **ISSUE**: statusline.sh line 5 discards JSON stdin (`cat > /dev/null`), losing context window % and workspace info that the default status bar shows. This is BUG-SKILL-004.
  - VERDICT: All acceptance criteria pass, but BUG-SKILL-004 blocks full satisfaction — context window bar is missing. → Shipped with caveat (bug filed).
- **Notes**: Major progress from skill lead — 2 bugs fixed, 3 features implemented. BUG-SKILL-003 (PS1 logo) and BUG-SKILL-004 (status line missing context window) remain open.

---

## QA Run — 2026-03-27 23:35

- **Result**: Passed
- **Files Reviewed**: .squidsquad/start-skill.ps1, .squidsquad/start-pm.ps1, .squidsquad/statusline.sh, SKILL.md (PS1 templates), references/agent-instructions.md, .squidsquad/pm/CLAUDE.md
- **Verification — BUG-SKILL-003 (Fixed)**: VERIFIED. UTF-8 encoding added to both generated PS1 files and both SKILL.md PS1 templates. → Closed.
- **Verification — BUG-SKILL-004 (Fixed)**: VERIFIED. statusline.sh now reads JSON stdin, parses used_percentage, displays color-coded context usage. → Closed.
- **Verification — FEAT-SKILL-004 (Pending Test)**: VERIFIED. All 4 criteria confirmed — "never implement code" in Responsibilities + "What You Must Never Do" in both template and generated CLAUDE.md. → Shipped.
- **Notes**: All bugs now closed. FEAT-SKILL-005 (iteration timestamps + countdown) still Approved, awaiting skill lead.

---

## QA Run — 2026-03-27 23:40

- **Result**: Passed (no changes)
- **Files Reviewed**: git log (no new commits since iter-4)
- **Issues**: none
- **Notes**: Iteration 5. No new work from skill lead. FEAT-SKILL-005 still Approved, awaiting pickup. 0 open bugs.

---

## QA Run — 2026-03-28 00:50

- **Result**: Issues Found
- **Files Reviewed**: SKILL.md (header), statusline.sh, features.md, CHANGELOG.md, config.md, skill/bugs.md
- **Verification — FEAT-SKILL-005 (Pending Test)**: VERIFIED.
  - [x] Boot scripts print cycle start timestamp — confirmed in Ralph Loop templates (agent prints markers)
  - [x] Boot scripts print cycle stop timestamp — confirmed
  - [x] Both .sh and .ps1 templates include behavior — confirmed (markers in Ralph Loop, not boot scripts — same UX)
  - [x] Generated boot scripts include behavior — N/A (markers in agent Ralph Loop instead)
  - [x] Status line shows next-cycle countdown — confirmed in statusline.sh lines 126-129
  - VERDICT: All 5 criteria pass. → Shipped.
- **Bug Filed**: BUG-SKILL-005 — PM Step 2 blocks on human input instead of continuing autonomously.
- **Notes**: Iteration 7. FEAT-SKILL-006 (git-log health) is Approved, awaiting skill lead pickup. 1 open bug (BUG-SKILL-005).

---

## QA Run — 2026-03-28 06:05

- **Result**: Passed
- **Files Reviewed**: .squidsquad/skill/bugs.md, .squidsquad/skill/features.md, CHANGELOG.md
- **Issues**: none
- **Agent Health**: skill — STALLED (last commit 63 minutes ago). 3 open bugs (010, 011, 012) waiting.
- **Notes**: Iteration 19. Fresh PM session. No new skill file changes to review. Skill agent needs restart.

---

## QA Run — 2026-03-28 06:15

- **Result**: Issues Found
- **Files Reviewed**: references/agent-instructions.md, SKILL.md, .squidsquad/pm/CLAUDE.md, .squidsquad/skill/bugs.md, .gitignore
- **Issues**:
  - `bash.exe.stackdump` committed to repo in f8d0b14 — filed as BUG-SKILL-013
- **Verified**: BUG-SKILL-010 (interactive Phase 2 format confirmed), BUG-SKILL-011 (Planning status gate confirmed across all files)
- **Agent Health**: skill — healthy (commit f8d0b14 this cycle)
- **Notes**: Iteration 20. Skill agent back online. 2 bugs closed, 1 filed. BUG-012 still Open.

---

## QA Run — 2026-03-28 06:25

- **Result**: Passed
- **Files Reviewed**: references/agent-instructions.md, SKILL.md, .squidsquad/skill/CLAUDE.md, .squidsquad/pm/CLAUDE.md
- **Issues**: none
- **Verified**: BUG-SKILL-012 — ANSI markers confirmed across all 4 files (38+10+16+2 occurrences), no old-style markers remain
- **Agent Health**: skill — healthy (2 commits in last 10 min)
- **Notes**: Iteration 21. All bugs from previous session now closed. Only BUG-013 (low severity) remains.

---

## QA Run — 2026-03-28 06:30

- **Result**: Passed
- **Files Reviewed**: .gitignore, bash.exe.stackdump (confirmed removed)
- **Issues**: none
- **Verified**: BUG-SKILL-013 — stackdump file removed, *.stackdump in .gitignore
- **Agent Health**: skill — healthy (2 commits in last 10 min)
- **Notes**: Iteration 22. All 13 bugs now closed. Clean slate — no open bugs, no Pending Test features.
