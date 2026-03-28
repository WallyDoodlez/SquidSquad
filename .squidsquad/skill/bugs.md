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
- **Status**: Closed
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
> [2026-03-28 02:10] **skill-lead**: Fixed. Updated PM/QA template in references/agent-instructions.md Step 2 to be non-blocking (print note, continue immediately). Also updated SKILL.md PM/QA Ralph Loop summary. The generated pm/CLAUDE.md was already correct. Status → Fixed.
> [2026-03-28 02:15] **pm/qa**: Verified. Template Step 2 is now non-blocking — prints note, continues immediately. Status → Verified → Closed.

---

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

---

## BUG-SKILL-007 — Boot script templates lack while-loop for multi-cycle execution

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: Neither the SKILL.md boot script templates nor the generated boot scripts have a `while true` loop. The CHANGELOG for v0.5.1 claims "Boot scripts now own the loop via `while true` in the shell", but this was never actually implemented. Both `.sh` and `.ps1` templates run `claude -p` once and then exit. Since `claude -p` handles one Ralph Loop cycle and exits, the agent runs one cycle and dies. The boot scripts need a `while true` loop that restarts `claude -p` after each cycle, with a sleep interval between cycles.
- **Steps to Reproduce**:
  1. Read SKILL.md boot script templates (lines 365-410)
  2. Note there is no loop — just a single `claude` invocation
  3. Start a skill lead — it runs once and exits
- **Expected**: Boot scripts wrap `claude -p` in a `while true` / `while ($true)` loop with a sleep between iterations
- **Actual**: Single `claude -p` call, script exits after one cycle

### Discussion

> [2026-03-28 01:40] **pm/qa**: Found while investigating skill lead inactivity. CHANGELOG says the loop exists but templates don't have it. This affects all agents — both dev and PM boot scripts.
> [2026-03-28 01:45] **pm/qa**: Invalid — dev agents are interactive (`--continue`), so Claude handles the Ralph Loop internally. No external while loop needed. The CHANGELOG entry about `while true` is misleading but the current design (single interactive session) is correct. Status → Closed.

---

## BUG-SKILL-008 — Agents don't reliably self-loop — should use `/loop` command

- **Severity**: Critical
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The Ralph Loop instructs agents to "sleep N minutes, then return to Step 1" but Claude doesn't reliably self-manage repeating cycles in an interactive session. In practice, agents do one burst of work (1-3 cycles) then go silent. This is the root cause of the skill lead repeatedly dying after each work session — observed across multiple restarts.

  The fix is to use Claude Code's built-in `/loop` command to externalize the cycle timing. Instead of the agent manually sleeping and restarting, the CLAUDE.md instructions should tell the agent to invoke `/loop [INTERVAL]m` on startup, with a prompt that executes one Ralph Loop cycle. The `/loop` skill handles the timer and re-invocation reliably.

  **Changes needed:**
  1. CLAUDE.md On Startup section: agent invokes `/loop [INTERVAL]m "execute one Ralph Loop cycle"` (or similar) instead of manually looping
  2. Ralph Loop instructions: remove the "Sleep and repeat" step — `/loop` handles that
  3. Each cycle is a single pass through Steps 1-N, then exits. `/loop` triggers the next cycle.
  4. Both dev and PM/QA templates in `references/agent-instructions.md` updated
  5. Generated CLAUDE.md files updated
  6. SKILL.md documents the `/loop` approach
  7. Boot scripts may need adjustment if the positional arg changes

- **Steps to Reproduce**:
  1. Start the skill lead via `.\.squidsquad\start-skill.ps1`
  2. Observe it does 1-3 cycles of work then goes silent
  3. No further commits appear in git log
- **Expected**: Agent loops reliably every [INTERVAL] minutes indefinitely
- **Actual**: Agent does a burst of work then stops

### Discussion

> [2026-03-28 04:05] **pm/qa**: Root cause of repeated skill lead inactivity. Self-managed sleep loops don't work reliably in Claude interactive sessions. The `/loop` command is purpose-built for this — externalizes timing so the agent just needs to execute one cycle per invocation.
> [2026-03-28 04:40] **skill-lead**: Fixed. Added On Startup section to both dev and PM/QA templates — agents read interval from config.md and invoke `/loop [INTERVAL]m`. Replaced Sleep step with Done step. Updated all generated CLAUDE.md files. SKILL.md documents the `/loop` approach. Status → Fixed.
> [2026-03-28 05:10] **pm/qa**: Verified. Both templates and generated CLAUDE.md files use `/loop`. Ralph Loop is single-cycle, `/loop` handles re-invocation. Status → Verified → Closed.

---

## BUG-SKILL-009 — Setup overwrites user's existing statusLine and settings.json config

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The setup Step 7 writes a `statusLine` config to `.claude/settings.json`. If the user already has a custom `statusLine` configured (e.g. their own status bar script), the setup overwrites it. The merge logic says "do not overwrite existing hooks" for SessionStart, but there's no equivalent protection for `statusLine`. The user's personalized settings get wiped.

  The fix should:
  1. Check if `statusLine` already exists in settings.json before writing
  2. If it exists, warn the user and ask whether to replace, merge, or skip
  3. If merging, chain the scripts (e.g. run both and combine output)
  4. Same check needed for `permissions.allow` — don't duplicate or remove existing entries
  5. Document this behavior in SKILL.md setup Step 7

- **Steps to Reproduce**:
  1. Have a custom `.claude/settings.json` with a `statusLine` config
  2. Run SquidSquad setup
  3. Observe your statusLine config is overwritten
- **Expected**: Setup detects existing statusLine and asks the user how to handle it
- **Actual**: Setup silently overwrites the user's statusLine config

### Discussion

> [2026-03-28 04:15] **pm/qa**: Reported by human. The status line feature was an impulse requirement that didn't consider users with existing settings.json customizations. Setup must be non-destructive.
> [2026-03-28 04:45] **skill-lead**: Fixed. SKILL.md Step 7 merge logic now explicitly checks for existing statusLine — prompts user to replace or skip. permissions.allow deduplicates. Status → Fixed.
> [2026-03-28 05:10] **pm/qa**: Verified. Step 7 checks for existing statusLine, prompts user. permissions.allow deduplicates. Status → Verified → Closed.

---

## BUG-SKILL-010 — Phase 2 (Discussion) dumps all questions at once instead of interactive flow

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The FEAT-SKILL-016 Feature Intake Process Phase 2 (Discussion) is supposed to be interactive — walking through questions one at a time with the human. But the current PM template doesn't specify the interaction format clearly enough, resulting in the PM dumping all research questions as a wall of text.

  The fix should specify that Phase 2 questions are presented **one at a time**, with each question formatted as:

  ```
  Q1: [Question text]
  Why this matters: [consequence of getting it wrong]

  (a) [Suggestion 1 — PM's recommended option]
  (b) [Suggestion 2 — alternative approach]
  (c) Type your own answer
  (d) Let's discuss this further

  Your choice:
  ```

  - If human picks (a) or (b): lock decision, move to next question
  - If human picks (c): human types freeform, PM captures it as a locked decision
  - If human picks (d): PM enters a longer back-and-forth discussion about this question until the human is satisfied, then locks the decision and moves on

  It's fine to present the full research summary first (Phase 1 output), but Phase 2 questions must be one-at-a-time interactive.

- **Steps to Reproduce**:
  1. Request a feature as human
  2. PM runs Phase 1 research
  3. PM enters Phase 2 — dumps all 7 questions with answers needed
- **Expected**: Questions presented one at a time with (a)(b)(c)(d) format
- **Actual**: All questions listed at once as a wall of text

### Discussion

> [2026-03-28 05:20] **pm/qa**: Found during first real test of FEAT-SKILL-016 (planning FEAT-SKILL-015). The research output is good — listing everything together first is fine. But the discussion phase needs to be truly interactive: one question at a time, two suggestions per question, option for freeform, option for deeper discussion.
> [2026-03-28 05:38] **skill-lead**: Fixed in agent-instructions.md Phase 2 section. Replaced generic numbered list with explicit one-at-a-time Q[N] format including (a)(b)(c)(d) options and handling rules for each response type. Added "Do NOT present all questions at once" directive. Status → Fixed.
> [2026-03-28 06:15] **pm/qa**: Verified. agent-instructions.md line 672 has "Do NOT present all questions at once" directive. Q[N] format with (a)(b)(c)(d) options confirmed at lines 653-670. Handling rules for each response type present. Status → Verified → Closed.

---

## BUG-SKILL-011 — Feature requests go straight to `Pending` approval instead of requiring planning flow first

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: When a human mentions a feature request, the PM currently files it as `Pending` (awaiting human approval) and once approved, the dev agent can immediately pick it up. This bypasses the entire 5-phase planning flow introduced in FEAT-SKILL-016. Features should not be implementable until they've gone through research → discussion → planning.

  The fix: add a new status `Planning` that sits between `Pending` and `Approved`:

  ```
  Pending → Planning → Approved → In Progress → Pending Test → Shipped
  ```

  **Flow:**
  1. Human mentions a feature → PM files it as `Pending`
  2. Human says "approve" → PM changes status to `Planning` (NOT `Approved`)
  3. PM runs Phase 1 (Research) → Phase 2 (Discussion) → Phase 3 (Planning + TEST-PLAN.md)
  4. Only after all planning phases complete does PM change status to `Approved`
  5. Dev agent only picks up features with status `Approved` (this rule already exists)

  This ensures no feature reaches a dev agent without having gone through the full research, discussion, and test planning process. The `Planning` status is visible in the tracker so everyone knows which features are being planned.

  Light mode (trivial features): PM can fast-track through planning with abbreviated research, but status still transitions through `Planning` → `Approved`.

- **Steps to Reproduce**:
  1. Human requests a feature
  2. PM files as `Pending`
  3. Human approves
  4. PM changes to `Approved` — dev agent immediately picks it up
  5. No research, discussion, or test planning happened
- **Expected**: After human approval, status goes to `Planning`. PM runs full intake flow. Only then → `Approved`.
- **Actual**: `Pending` → `Approved` directly, skipping the planning flow.

### Discussion

> [2026-03-28 05:25] **pm/qa**: Found during FEAT-SKILL-015 planning. The 5-phase lifecycle (FEAT-SKILL-016) added the research/discussion/planning process but didn't gate the status flow. A feature can still go from Pending → Approved → picked up by dev without any planning. Need a `Planning` status to enforce the gate.
> [2026-03-28 05:42] **skill-lead**: Fixed. Added `Planning` status between `Pending` and `Approved` in: (1) agent-instructions.md — approval flow now goes to `Planning`, Feature Approval Gate updated with full status descriptions, (2) SKILL.md — all 4 status flow references updated, (3) generated pm/CLAUDE.md — approval action updated. Flow is now Pending → Planning → Approved. Status → Fixed.
> [2026-03-28 06:15] **pm/qa**: Verified. `Planning` status present in SKILL.md (lines 124, 140, 142, 687, 891), agent-instructions.md (lines 423, 771), and generated pm/CLAUDE.md (lines 83, 85, 87). Approval flow correctly gates through Planning before Approved. Status → Verified → Closed.

---

## BUG-SKILL-012 — Step markers inconsistent and not visually distinct enough

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: Two issues with the `[squidsquad]` step markers from FEAT-SKILL-008:

  1. **Not all actions are prefixed** — Some PM and dev actions (filing bugs, updating trackers, research spawning, discussion questions) happen without a marker. Every SquidSquad action should have one.

  2. **Not visually distinct** — Plain `[squidsquad]` text blends in with normal Claude output. The markers should use ANSI styling to stand out:
     - Replace `[squidsquad]` with `[🦑]`
     - Background: pink/magenta (`\033[45m`)
     - Foreground: black (`\033[30m`)
     - Reset after the prefix

  **Example output:**
  ```
  \033[45m\033[30m[🦑]\033[0m Pulling latest...
  \033[45m\033[30m[🦑]\033[0m Triaging bugs...
  \033[45m\033[30m[🦑]\033[0m Filing BUG-SKILL-012...
  ```

  The ANSI styling makes SquidSquad actions immediately scannable in scrollback — pink background with squid emoji is unmistakable.

- **Steps to Reproduce**:
  1. Run any SquidSquad agent
  2. Observe some actions have `[squidsquad]` prefix, others don't
  3. The prefixed ones blend in with normal text
- **Expected**: Every SquidSquad action prefixed with `[🦑]` in pink background / black foreground ANSI
- **Actual**: Inconsistent prefixing, plain text styling

### Discussion

> [2026-03-28 05:30] **pm/qa**: Reported by human. The markers need to be both complete (every action) and visually outstanding (ANSI pink bg + black fg + squid emoji). Shortening to `[🦑]` also saves horizontal space.
> [2026-03-28 05:58] **skill-lead**: Fixed. Replaced all `[squidsquad]` markers with ANSI-styled `\033[45m\033[30m[🦑]\033[0m` across: agent-instructions.md (both dev and PM templates), skill/CLAUDE.md, pm/CLAUDE.md, SKILL.md, and README.md. All step markers and sub-action markers now use the styled format. Status → Fixed.
> [2026-03-28 06:25] **pm/qa**: Verified. ANSI-styled markers confirmed: agent-instructions.md (38), skill/CLAUDE.md (10), pm/CLAUDE.md (16), SKILL.md (2). No old-style `[squidsquad]` markers remain in any file. Status → Verified → Closed.

---

## BUG-SKILL-013 — `bash.exe.stackdump` committed to repo

- **Severity**: Low
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: A `bash.exe.stackdump` file was committed in `f8d0b14`. This is a Windows/MSYS crash dump artifact — not a project file. It should be removed from tracking and added to `.gitignore`.

  **Fix needed:**
  1. `git rm bash.exe.stackdump`
  2. Add `*.stackdump` to `.gitignore`

- **Steps to Reproduce**:
  1. `ls bash.exe.stackdump` — file exists in repo root
- **Expected**: Crash dumps not tracked in git
- **Actual**: `bash.exe.stackdump` is tracked

### Discussion

> [2026-03-28 06:15] **pm/qa**: Found during QA review of commit f8d0b14. Crash dump artifact accidentally committed alongside BUG-010/011 fixes.
> [2026-03-28 06:20] **skill-lead**: Fixed. Ran `git rm bash.exe.stackdump` and added `*.stackdump` to `.gitignore`. Status → Fixed.
> [2026-03-28 06:30] **pm/qa**: Verified. File removed from repo, `*.stackdump` in .gitignore line 5. Status → Verified → Closed.

---

## BUG-SKILL-014 — ANSI escape codes in step markers render as mangled text

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: skill-lead
- **Assigned To**: skill-lead
- **Description**: BUG-SKILL-012 replaced `[squidsquad]` markers with ANSI-styled `\033[45m\033[30m[🦑]\033[0m`. However, Claude Code cannot render ANSI escape sequences in text output — they display as literal mangled text. The fix is to use plain `[🦑]` without ANSI wrapping. The squid emoji is visually distinctive on its own.

  **Fix needed:**
  1. Replace all `\033[45m\033[30m[🦑]\033[0m` with `[🦑]` across all templates and generated files
  2. Update SKILL.md and README.md references

- **Steps to Reproduce**:
  1. Run any SquidSquad agent
  2. Observe step markers show raw escape codes instead of colored text
- **Expected**: Clean `[🦑]` prefix
- **Actual**: `\033[45m\033[30m[🦑]\033[0m` displayed as literal text

### Discussion

> [2026-03-28 07:15] **skill-lead**: Self-filed. Human reported mangled output. ANSI codes don't work in Claude Code text output.
> [2026-03-28 07:16] **skill-lead**: Fixed. Replaced all ANSI-wrapped markers with plain `[🦑]` across agent-instructions.md, skill/CLAUDE.md, pm/CLAUDE.md, and SKILL.md. Status → Fixed.
> [2026-03-28 07:20] **pm/qa**: Verified. Zero `\033` escape sequences remain in any template or generated file. Plain `[🦑]` markers confirmed (35 in agent-instructions.md). Status → Verified → Closed.

---

## BUG-SKILL-015 — Phase 2 discussion should present all questions at once, then let human respond naturally

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: BUG-SKILL-010 introduced a one-at-a-time (a)(b)(c)(d) format for Phase 2 discussion questions. In practice this is too rigid — it blocks the PM loop waiting for individual answers and doesn't leverage Claude's natural conversation flow.

  The correct approach is a **two-part flow**:

  **Part 1 — Overview**: Present the full research summary AND all open questions together in a single output, so the human sees the full picture upfront.

  **Part 2 — Interactive walk-through**: Immediately start walking through questions one at a time. Each question gets 3 suggestions (PM's recommendations based on research) plus a "discuss more" option. Human picks one or types freeform. PM locks the decision, moves to next question.

  **Current (broken):**
  ```
  Q1: [question] ... (a)(b)(c)(d) Your choice:
  [wait — human never saw Q2-Q7]
  ```

  **Expected:**
  ```
  [Research summary]

  Open questions:
  Q1: [question] — Why it matters: [risk]
  Q2: [question] — Why it matters: [risk]
  ...Q7: [question] — Why it matters: [risk]

  Let's walk through these one at a time.

  Q1: [question]
  Why this matters: [consequence]

  (a) [Suggestion 1 — recommended]
  (b) [Suggestion 2]
  (c) [Suggestion 3]
  (d) Let's discuss this more

  Your choice:
  ```

  Key difference from BUG-010: the human sees ALL questions listed first for context, THEN the interactive walk-through begins with 3 suggestions (not 2) per question plus a discuss option.

- **Steps to Reproduce**:
  1. Approve a feature for planning
  2. PM runs Phase 1 research
  3. PM enters Phase 2 — presents Q1 with (a)(b)(c)(d) and waits
- **Expected**: All questions presented at once, human responds via normal prompt
- **Actual**: Rigid one-at-a-time (a)(b)(c)(d) format that blocks on each question

### Discussion

> [2026-03-28 07:25] **pm/qa**: Reported by human. The one-at-a-time format from BUG-010 was overcorrection — went from "dump everything" to "too rigid". The right balance is: present all questions together with recommendations, then let the human respond naturally. This supersedes BUG-SKILL-010's (a)(b)(c)(d) format.
> [2026-03-28 07:30] **pm/qa**: Human clarified: two-part flow. Part 1: show all questions at once for context. Part 2: immediately start interactive walk-through, one question at a time with 3 suggestions (not 2) + "discuss more" option. Human picks or types freeform. Updated description.
> [2026-03-28 07:35] **skill-lead**: Fixed in agent-instructions.md Phase 2 section. Restructured into two parts: Part 1 presents research summary + all questions listed together for context. Part 2 walks through one at a time with 3 suggestions + "discuss more" option + freeform. Status → Fixed.
> [2026-03-28 07:40] **pm/qa**: Verified. agent-instructions.md lines 653-684: Part 1 overview with all questions listed, Part 2 interactive walk-through with 3 suggestions (a)(b)(c) + (d) discuss + freeform. Handling rules correct. Status → Verified → Closed.
