# Feature Tracker

_Features start as Pending (awaiting human approval) and move through Approved → In Progress → Pending Test → Shipped._

---

## FEAT-SKILL-001 — Use structured prompts during setup

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: The current setup flow asks freeform questions. Replace it with Claude's `prompt_user` skill (or equivalent structured prompting pattern) so inputs are gathered cleanly, validated, and defaults are offered inline. This makes setup more reliable and easier to script.
- **Acceptance Criteria**:
  - [ ] Each setup question uses a structured prompt with a clear label, description, and default value shown
  - [ ] Invalid inputs (e.g. interval < 1, empty project name) are caught and re-prompted rather than silently accepted
  - [ ] Setup can be completed from a single natural-language sentence if all info is provided upfront (e.g. "Set up SquidSquad for kubex, BE only, 5 min interval")
  - [ ] SKILL.md Step 1 updated to reflect the new prompting approach

### Discussion

> [2026-03-27 20:00] **pm/qa**: Seeded at initialization. Approved by human at setup time.
> [2026-03-27 23:16] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-27 23:20] **skill-lead**: Complete. Step 1 rewritten with structured field table (label, description, default, validation per field), quick-start mode for single-sentence setup, and confirmation summary before proceeding. Status → Pending Test.
> [2026-03-27 23:15] **pm/qa**: QA verified — all 4 acceptance criteria confirmed in SKILL.md Step 1. Status → Shipped.

---

## FEAT-SKILL-002 — Import existing bugs and features from external sources during setup

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: During setup Step 1, after gathering project details, offer to import existing bugs or features from an external source. Sources should include: pasting raw text, pointing to a local file, or pulling from a connected MCP (e.g. GitHub Issues, Jira, Linear, Notion) if one is available in the session. Each imported item gets normalized into the standard BUG-XXX or FEAT-XXX format and seeded into the correct tracker.
- **Acceptance Criteria**:
  - [ ] Setup offers an import prompt after project details are gathered: "Do you have existing bugs or features to import? (paste text, file path, or MCP source — or skip)"
  - [ ] Pasted text is parsed and normalized into tracker entries with reasonable field inference (title, severity/priority, description)
  - [ ] File path input reads the file and parses it the same way
  - [ ] If an MCP tool is available in the session (e.g. GitHub Issues, Jira), it is offered as an import option and items are fetched and mapped to the tracker format
  - [ ] Imported items are filed to the correct tracker (fe/, be/, skill/, etc.) based on inferred or stated owner
  - [ ] Each imported entry gets a Discussion note: `> **pm/qa**: Imported from [source] at setup.`
  - [ ] SKILL.md Step 1 and Step 6 updated to document the import flow

### Discussion

> [2026-03-27 20:00] **pm/qa**: Seeded at initialization. Approved by human at setup time.
> [2026-03-27 23:45] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-27 23:50] **skill-lead**: Complete. Added import sub-step to Step 1 with three source options (paste, file, MCP), normalization rules, and routing heuristics. Updated Step 6 to handle imported items alongside seeds. CHANGELOG updated. Status → Pending Test.
> [2026-03-27 23:15] **pm/qa**: QA verified — all 7 acceptance criteria confirmed in SKILL.md Step 1 and Step 6. Status → Shipped.

---

## FEAT-SKILL-003 — PM status bar shows iteration number and squid emoji

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Add a Claude Code status line for all SquidSquad agents using the `statusLine` setting in `settings.json`. The status line gives the human a quick glance at squad activity without reading logs. Uses ANSI colors for state indication (animation not supported — status line only refreshes on assistant messages).
- **Acceptance Criteria**:
  - [ ] A `statusLine` command/script is configured in `.claude/settings.json` (or generated during setup)
  - [ ] Status line shows agent role label (e.g. `PM/QA`, `skill`)
  - [ ] Status line shows current iteration number (read from latest `iter-N.md`)
  - [ ] Status line shows squid emoji `🦑` in green (ANSI) when agent is active
  - [ ] PM status line shows other agents' health: `🦑` green if pushed recently, `🦑✖` red if silent for N+ cycles
  - [ ] Status line shows time since last cycle started
  - [ ] Status line shows open bug/feature counts as a backlog pulse (e.g. `2 bugs 1 feat`)
  - [ ] SKILL.md setup steps updated to generate the status line script and configure settings.json
  - [ ] PM and dev agent CLAUDE.md templates updated to document status line behavior

### Discussion

> [2026-03-27 22:40] **pm/qa**: Filed from human request. Status: Pending — awaiting human approval.
> [2026-03-27 22:50] **pm/qa**: Updated scope after research. Animation not feasible (status line only refreshes on events, no timer). Revised to use ANSI color-based state indicators instead. Added agent health monitoring, cycle timer, backlog counts, and coverage for all agents (not just PM). Human approved. Status → Approved.
> [2026-03-28 00:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 00:15] **skill-lead**: Complete. Created `.squidsquad/statusline.sh` with role detection, iteration tracking, backlog pulse, PM agent health, and ANSI coloring. Updated `settings.json` template with `statusLine` config. Updated SKILL.md Step 5b and Step 7. Updated dev and PM/QA CLAUDE.md templates with Status Line section. CHANGELOG updated. Status → Pending Test.
> [2026-03-27 23:15] **pm/qa**: QA verified — all 9 acceptance criteria pass. However, statusline.sh discards JSON stdin (context window %, repo info) — filed as BUG-SKILL-004. Status → Shipped (with caveat).

---

## FEAT-SKILL-004 — PM/QA agent must never implement code directly

- **Priority**: High
- **Status**: Pending Test
- **Owner**: skill-lead
- **Description**: The PM/QA agent should be explicitly prohibited from implementing code or making direct changes to skill files, application code, or any non-tracker files. When PM/QA identifies something that needs changing, it must always file a bug or feature request to the appropriate dev agent's tracker instead of making the change itself. This should be enforced in both the PM/QA CLAUDE.md template (in `references/agent-instructions.md`) and the generated PM CLAUDE.md files.
- **Acceptance Criteria**:
  - [ ] PM/QA CLAUDE.md template in `references/agent-instructions.md` explicitly states PM/QA must never implement code changes
  - [ ] "What You Must Never Do" section includes: "Never implement fixes or features directly — always file to the appropriate agent's bug or feature tracker"
  - [ ] Ralph Loop steps reinforce this: if PM/QA finds an issue during QA, it files a bug rather than fixing it
  - [ ] Generated `pm/CLAUDE.md` files include this constraint

### Discussion

> [2026-03-27 23:05] **pm/qa**: Filed from human request. PM/QA's role is coordination and verification, not implementation. Any code-level fix must go through a dev agent's tracker.
> [2026-03-27 23:10] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 00:35] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 00:40] **skill-lead**: Complete. Added "never implement code directly" to PM/QA Responsibilities, "What You Must Never Do" in both the template (`references/agent-instructions.md`) and the generated `pm/CLAUDE.md`. Status → Pending Test.

---

## FEAT-SKILL-005 — Show timestamp at iteration start and stop

- **Priority**: Medium
- **Status**: Approved
- **Owner**: skill-lead
- **Description**: Each Ralph Loop iteration should print a visible timestamp when it starts and when it finishes, so the human can see cycle timing in the terminal output. This applies to all agents (dev and PM/QA). The timestamps should be printed by the boot scripts (`.sh` and `.ps1`) that wrap each cycle, making cycle boundaries easy to spot in scrollback. Additionally, the status bar should show a countdown estimate to the next iteration.
- **Acceptance Criteria**:
  - [ ] Boot scripts print a start timestamp at the beginning of each cycle (e.g. `[squidsquad] ---- cycle 3 started at 14:32:07 ----`)
  - [ ] Boot scripts print a stop timestamp when the cycle ends (e.g. `[squidsquad] ---- cycle 3 complete at 14:33:42 ----`)
  - [ ] Both `.sh` and `.ps1` boot script templates in SKILL.md include this behavior
  - [ ] Generated boot scripts include this behavior
  - [ ] Status line script (`statusline.sh`) shows estimated time until next cycle (e.g. `next in ~2m`) by calculating `interval - elapsed`. Note: only updates on assistant messages, not live.

### Discussion

> [2026-03-27 23:25] **pm/qa**: Filed from human request.
> [2026-03-27 23:25] **pm/qa**: Human approved. Status → Approved.
> [2026-03-27 23:30] **pm/qa**: Folded in human request for next-iteration countdown in status bar. Added acceptance criterion for `next in ~Xm` display in statusline.sh.
