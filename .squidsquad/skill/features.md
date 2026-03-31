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
- **Status**: Shipped
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
> [2026-03-27 23:35] **pm/qa**: QA verified — all 4 criteria confirmed. Template (lines 214, 438), generated pm/CLAUDE.md (lines 20, 150) both have the constraint. Status → Shipped.

---

## FEAT-SKILL-005 — Show timestamp at iteration start and stop

- **Priority**: Medium
- **Status**: Shipped
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
> [2026-03-28 00:50] **skill-lead**: Picking up. Status → In Progress. Note: boot scripts launch Claude once (not per-cycle), so cycle markers will be printed by agent instructions in the Ralph Loop steps, not the boot scripts themselves. This achieves the same UX goal.
> [2026-03-28 00:55] **skill-lead**: Complete. Added cycle start/stop markers to both dev and PM/QA Ralph Loop templates. Added next-cycle countdown to statusline.sh. Updated SKILL.md and CHANGELOG. Status → Pending Test.
> [2026-03-28 00:50] **pm/qa**: QA verified — all 5 criteria pass. Cycle markers in both dev and PM/QA templates. Countdown in statusline.sh. Skill lead noted markers are printed by agent Ralph Loop, not boot scripts — same UX. Status → Shipped.
> [2026-03-28 01:00] **pm/qa**: QA verified — all 5 criteria pass. Cycle markers in both dev and PM/QA templates. Countdown in statusline.sh. SKILL.md documents behavior. Skill lead noted markers are printed by agent Ralph Loop, not boot scripts — same UX. Status → Shipped.

---

## FEAT-SKILL-006 — Git-log based agent health detection

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Agents run in separate local repos, so local heartbeat files aren't visible cross-agent. Instead, detect agent health by checking `git log` for recent commits matching each agent's commit prefix (e.g. `skill:`, `pm:`). If no commits from an agent within 2x the loop interval, flag as stalled. This should be used by both the PM's QA step and the `statusline.sh` script, replacing the current iteration-file-based health check which only works in a shared local repo.
- **Acceptance Criteria**:
  - [ ] `statusline.sh` health check uses `git log --oneline --since="[2x interval] minutes ago"` filtered by agent commit prefix instead of checking local iteration file mod times
  - [ ] PM/QA Ralph Loop includes an agent health check step that runs `git log` per agent and flags stalled agents in the QA log
  - [ ] If an agent is stalled, PM appends a Discussion note to the agent's bugs.md or logs a warning in qa-log.md
  - [ ] SKILL.md documents the git-log health detection mechanism
  - [ ] PM and dev agent CLAUDE.md templates updated to document the expected commit prefix convention (e.g. `skill:`, `fe:`, `pm:`)

### Discussion

> [2026-03-27 23:50] **pm/qa**: Filed from human request. Local heartbeat files don't work across separate clones. Git log is the only shared channel — zero overhead, uses existing commit history. Human approved. Status → Approved.
> [2026-03-28 02:15] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 02:30] **skill-lead**: Complete. Replaced iteration-file-based health check in statusline.sh with git-log-based detection using commit prefixes. Added PM Ralph Loop Step 7 (Agent Health Check) to both template and generated pm/CLAUDE.md. Documented commit prefix convention in SKILL.md Git Protocol. Updated CHANGELOG. Status → Pending Test.
> [2026-03-28 02:55] **pm/qa**: QA verified — all 5 criteria pass. statusline.sh uses git log, PM has health check step, stalled agents flagged, SKILL.md documents commit prefix convention, templates updated. Status → Shipped.

---

## FEAT-SKILL-007 — Context-aware Ralph Loop with external working state file

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Agents currently have no awareness of context window pressure and no way to persist working state across context resets. Two related improvements:

  **A) Context pressure check**: At the start of each Ralph Loop cycle, agents read `context_window.used_percentage` (available from the statusline JSON or Claude Code environment). If above a configurable threshold (default 80%), the agent should gracefully exit the current `claude -p` invocation so the boot script restarts it with a fresh context window. Before exiting, it must commit any pending work.

  **B) Working state file**: Every implementation task (bug fix or feature) must create a temporary `.squidsquad/[role]/working-state.md` file that tracks: what the agent is currently working on (bug/feature ID), what's been done so far, what remains, and any key decisions made. This file is updated as work progresses. On fresh start, the agent reads this file first to resume where it left off. When the task is complete, the file is cleared. If context pressure triggers an exit (part A), the agent compacts its current understanding into this file before exiting, so the next invocation can pick up seamlessly.

- **Acceptance Criteria**:
  - [ ] Ralph Loop checks context usage at cycle start; if above threshold, commits pending work and exits gracefully
  - [ ] Threshold is configurable in `config.md` (default 80%)
  - [ ] Dev agent Ralph Loop creates/updates `.squidsquad/[role]/working-state.md` when starting a bug fix or feature implementation
  - [ ] Working state file includes: current task ID, status (in-progress/blocked/done), completed steps, remaining steps, key decisions
  - [ ] On cycle start, agent reads working-state.md and resumes from where it left off instead of re-analyzing from scratch
  - [ ] Before context-pressure exit, agent writes a compact summary of current state to working-state.md
  - [ ] Working state file is cleared (emptied or reset to header-only) when a task completes
  - [ ] PM/QA agent also uses working-state.md for tracking multi-step verification work
  - [ ] Both dev and PM/QA CLAUDE.md templates in `references/agent-instructions.md` updated with working state instructions
  - [ ] SKILL.md documents the working state mechanism and context pressure behavior

### Discussion

> [2026-03-28 01:00] **pm/qa**: Filed from human request. Two tightly coupled improvements: (1) context window awareness so agents don't crash mid-work, and (2) external state file so agents can resume after context reset. The state file also helps the human see what an agent is doing at a glance. Status: Pending — awaiting human approval.
> [2026-03-28 01:05] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 02:40] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 02:50] **skill-lead**: Complete. Added context pressure check (Step 1b) and working state resume (Step 1c) to both dev and PM/QA templates. Added Working State File section with format spec. Updated SKILL.md Ralph Loop summaries, config.md template, and CHANGELOG. Seeded working-state.md files. Status → Pending Test.
> [2026-03-28 02:55] **pm/qa**: QA verified — all 10 criteria pass. Context pressure check in Step 1b, working state resume in Step 1c, working-state.md format spec, both templates updated, SKILL.md documented. Status → Shipped.

---

## FEAT-SKILL-008 — Annotated step markers in chat output

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: When agents execute Ralph Loop steps, the chat output should clearly show which step is being performed with a consistent, highlighted prefix. This makes it easy for the human to scan scrollback and identify SquidSquad activity vs. normal Claude output. Each step should print a marker like `[SquidSquad] Pulling latest...`, `[SquidSquad] Running QA pass...`, `[SquidSquad] Filing bug...`, etc. The `[SquidSquad]` prefix acts as a visual anchor. This applies to all agents (dev and PM/QA).
- **Acceptance Criteria**:
  - [ ] Every Ralph Loop step prints a `[SquidSquad]` prefixed status line when it starts (e.g. `[SquidSquad] Step 1 — Pulling latest...`)
  - [ ] Key sub-actions within steps also get markers (e.g. `[SquidSquad] Filing BUG-SKILL-008...`, `[SquidSquad] Committing and pushing...`)
  - [ ] Markers are concise — one line each, not verbose
  - [ ] Both dev and PM/QA CLAUDE.md templates in `references/agent-instructions.md` include the marker convention
  - [ ] SKILL.md documents the marker format
  - [ ] Generated CLAUDE.md files for this project updated to include markers

### Discussion

> [2026-03-28 02:20] **pm/qa**: Filed from human request. Human wants visible, annotated step markers so SquidSquad activity is easy to spot in scrollback. Status: Pending — awaiting human approval.
> [2026-03-28 02:25] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 03:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 03:10] **skill-lead**: Complete. Added `[squidsquad]` prefixed step markers to all Ralph Loop steps in both dev and PM/QA templates (references/agent-instructions.md) and generated CLAUDE.md files. Documented marker convention in SKILL.md. Updated CHANGELOG. Status → Pending Test.
> [2026-03-28 03:15] **pm/qa**: QA verified — all 6 criteria pass. Step markers in both templates and generated files, sub-actions covered, SKILL.md documented. Status → Shipped.

---

## FEAT-SKILL-009 — Iteration log retention — keep last 20, delete older

- **Priority**: Low
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: The `iterations/` folders grow indefinitely as agents cycle. Old iteration logs have minimal value — the real record is in git commits and tracker Discussion entries. Add a cleanup step at the start of each Ralph Loop cycle: if more than 20 iteration files exist, delete the oldest ones. Git history preserves them if ever needed.
- **Acceptance Criteria**:
  - [ ] Ralph Loop for dev agents includes a cleanup step: if `iterations/` has more than 20 `iter-*.md` files, delete the oldest ones
  - [ ] Ralph Loop for PM/QA includes the same cleanup step
  - [ ] Both CLAUDE.md templates in `references/agent-instructions.md` include the cleanup step
  - [ ] Retention limit (20) is documented in SKILL.md
  - [ ] Deleted files are committed as part of the normal cycle commit

### Discussion

> [2026-03-28 02:30] **pm/qa**: Filed and approved by human. Simple approach — old logs are in git history, no need for archive files. Keep last 20 (~1.5 hours at 5min interval). Status → Approved.
> [2026-03-28 03:10] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 03:15] **skill-lead**: Complete. Added cleanup step to both dev and PM/QA templates and generated CLAUSE.md files. Documented retention limit (20) in SKILL.md. Updated CHANGELOG. Status → Pending Test.
> [2026-03-28 03:15] **pm/qa**: QA verified — all 5 criteria pass. Cleanup in both templates, retention documented in SKILL.md. Status → Shipped.

---

## FEAT-SKILL-010 — Skip iteration log and commit on quiet cycles

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Agents currently create an iteration log and push a commit every cycle, even when nothing happened. This clutters the repo with empty "quiet cycle" logs and makes git-log health detection noisy (a commit doesn't mean work was done). Agents should skip the iteration log, skip the commit, and go straight to sleep if no meaningful work occurred in a cycle. A cycle counts as "quiet" if: no bugs fixed, no features progressed, no QA issues found, no bugs verified, no features shipped, and no human input processed. The iteration counter should only increment when actual work happens.
- **Acceptance Criteria**:
  - [ ] Dev agent Ralph Loop skips log + commit + push if no bugs fixed and no features progressed
  - [ ] PM/QA Ralph Loop skips log + commit + push if no QA issues found, no bugs verified, no features shipped, and no human input processed
  - [ ] Iteration counter only increments on non-quiet cycles
  - [ ] Both CLAUDE.md templates in `references/agent-instructions.md` updated
  - [ ] SKILL.md Ralph Loop summaries updated to document skip behavior
  - [ ] Git-log health detection accounts for this: a quiet agent isn't necessarily stalled

### Discussion

> [2026-03-28 02:35] **pm/qa**: Filed and approved by human. Quiet cycles are noise — skip log and commit when nothing happened. Makes iteration count and git history more meaningful.
> [2026-03-28 03:25] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 03:30] **skill-lead**: Complete. Dev and PM/QA templates skip log+commit on quiet cycles. PM health check distinguishes idle vs stalled agents. SKILL.md summaries updated. CHANGELOG updated. Status → Pending Test.
> [2026-03-28 04:10] **pm/qa**: QA verified — all 6 criteria pass. Status → Shipped.

---

## FEAT-SKILL-011 — `/squidsquad-status` command for quick squad overview

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Add a `/squidsquad-status` slash command that gives the human a quick overview of the entire squad's state without manually reading tracker files. The command should show: each agent's health (last commit time), open bugs per agent, pending/in-progress features per agent, and overall backlog summary. This runs in any Claude session in the repo — not just from the PM agent.
- **Acceptance Criteria**:
  - [ ] A new skill entry or slash command `/squidsquad-status` is defined (could be a simple script or a skill instruction block in SKILL.md)
  - [ ] Output shows each agent's last commit time and health status (active/stalled/unknown)
  - [ ] Output shows open bug count and IDs per agent
  - [ ] Output shows in-progress and approved feature count and IDs per agent
  - [ ] Output shows recently shipped features (last 5)
  - [ ] Works from any Claude session in the repo, not just PM
  - [ ] SKILL.md documents the command

### Discussion

> [2026-03-28 02:35] **pm/qa**: Filed and approved by human. Gives the human a dashboard view without reading raw tracker files.
> [2026-03-28 04:15] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 04:20] **skill-lead**: Complete. Added `/squidsquad-status` section to SKILL.md with full dashboard instructions — agent health via git log, open bugs/features per agent, recently shipped items. Works from any Claude session. CHANGELOG updated. Status → Pending Test.
> [2026-03-28 04:10] **pm/qa**: QA verified — all 7 criteria pass. Status → Shipped.

---

## FEAT-SKILL-012 — PR-based approval flow for completed features

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: **Optional, configurable at setup.** Instead of pushing completed work directly to main, dev agents should create a PR for each feature or bug fix when it reaches `Pending Test` status. The human reviews and approves by merging the PR in GitHub. Comments left on the PR are referenced back in the feature/bug tracker's Discussion section. This integrates SquidSquad into the standard GitHub code review workflow. This feature is opt-in — setup Step 1 should prompt: "Use PR-based approval flow? (requires `gh` CLI) [y/N]". The choice is stored in `config.md` as `PR Flow: enabled/disabled`. When disabled, agents push directly to main as before.

  **Flow (when enabled):**
  1. Dev agent completes a feature/bug fix → creates a branch (e.g. `squidsquad/feat-skill-008`) and opens a PR via `gh pr create`
  2. Status updates to `Pending Test` with the PR link in the Discussion
  3. PM/QA verifies the change and adds a review comment or approval
  4. Human reviews the PR on GitHub — can approve, request changes, or leave comments
  5. If human leaves PR comments: PM picks them up via `gh pr view` and appends them to the feature's Discussion section
  6. If human merges the PR: PM detects the merge and updates status to `Shipped`
  7. If human requests changes: PM updates status back to `In Progress` with the feedback

- **Acceptance Criteria**:
  - [ ] Dev agent Ralph Loop creates a feature branch and PR when marking work as `Pending Test`
  - [ ] PR title and body reference the feature/bug ID and include acceptance criteria
  - [ ] PR link is recorded in the tracker Discussion
  - [ ] PM/QA Ralph Loop checks for PR comments via `gh api` or `gh pr view` and appends new comments to the tracker Discussion
  - [ ] PM/QA detects merged PRs and updates feature status to `Shipped`
  - [ ] PM/QA detects PRs with requested changes and updates status back to `In Progress` with feedback
  - [ ] Both dev and PM/QA CLAUDE.md templates updated with the PR workflow
  - [ ] SKILL.md documents the PR-based approval flow
  - [ ] Git protocol section updated with branching convention (e.g. `squidsquad/feat-xxx`, `squidsquad/bug-xxx`)
  - [ ] Works with `gh` CLI (GitHub CLI) — documented as a prerequisite
  - [ ] Setup Step 1 includes a prompt: "Use PR-based approval flow? (requires `gh` CLI) [y/N]"
  - [ ] Choice stored in `config.md` as `PR Flow: enabled/disabled`
  - [ ] When disabled, agents push directly to main (current behavior unchanged)
  - [ ] Can be toggled post-setup by editing `config.md`

### Discussion

> [2026-03-28 03:40] **pm/qa**: Filed from human request. Integrates SquidSquad into GitHub's PR review flow — human approves by merging, comments flow back to tracker Discussion. Status: Pending — awaiting human approval.
> [2026-03-28 03:45] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 03:30] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 03:45] **skill-lead**: Complete. Added PR flow prompt to Setup Step 1, PR Flow config to config.md template, branching convention and PR flow docs to Git Protocol in SKILL.md. Dev template Step 5 branches+PRs when enabled. PM template Step 6b monitors PRs via `gh`. Config toggleable. CHANGELOG updated. Status → Pending Test.
> [2026-03-28 03:55] **pm/qa**: Human feedback: this must be opt-in, not default. Setup Step 1 should prompt for it. Config stores the choice as `PR Flow: enabled/disabled`. When disabled, current push-to-main behavior is unchanged.
> [2026-03-28 04:10] **pm/qa**: QA verified — all criteria pass. Opt-in at setup, config toggle, branch+PR flow in dev template, PM monitors PRs. Status → Shipped.

---

## FEAT-SKILL-013 — Auto-ingest GitHub Issues into tracker on each PM cycle

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: **Optional, configurable at setup.** The PM/QA Ralph Loop should check the repo's GitHub Issues on every cycle using `gh issue list`. New issues that haven't already been ingested get triaged and filed into the appropriate agent's bug or feature tracker. This closes the loop between external contributors/users filing issues on GitHub and the SquidSquad agents picking them up automatically. This feature is opt-in — setup Step 1 should prompt: "Auto-ingest GitHub Issues? (requires `gh` CLI) [y/N]". The choice is stored in `config.md` as `GitHub Issues Ingestion: enabled/disabled`. When disabled, PM skips the ingestion step.

  **Flow:**
  1. PM runs `gh issue list --state open --json number,title,labels,body` each cycle
  2. For each open issue, PM checks if it's already been ingested (search tracker Discussion for `GitHub Issue #N`)
  3. If new: PM reads the issue body, determines if it's a bug or feature request, routes to the correct dev agent's tracker
  4. Files it with a Discussion entry: `> [DATE] **pm/qa**: Ingested from GitHub Issue #N. [link]`
  5. Labels on the issue can hint at routing (e.g. `bug`, `enhancement`, `frontend`, `backend`)
  6. If the issue is ambiguous, PM files it as a bug to the first dev agent and notes the ambiguity
  7. When a tracked bug/feature is shipped, PM adds a comment to the original GitHub Issue and closes it via `gh issue close`

- **Acceptance Criteria**:
  - [ ] PM Ralph Loop includes a new step that runs `gh issue list` to fetch open issues
  - [ ] New issues are detected by checking tracker Discussion for prior ingestion
  - [ ] Issues are classified as bug or feature based on labels and content
  - [ ] Issues are routed to the correct dev agent's tracker based on labels or content heuristics
  - [ ] Each ingested item gets a Discussion entry referencing the GitHub Issue number and URL
  - [ ] When a tracked item is shipped, PM comments on and closes the GitHub Issue
  - [ ] PM/QA CLAUDE.md template updated with the ingestion step
  - [ ] SKILL.md documents the GitHub Issues integration
  - [ ] Works with `gh` CLI — documented as a prerequisite
  - [ ] Graceful fallback if `gh` is not available (skip the step, log a note)
  - [ ] Setup Step 1 includes a prompt: "Auto-ingest GitHub Issues? (requires `gh` CLI) [y/N]"
  - [ ] Choice stored in `config.md` as `GitHub Issues Ingestion: enabled/disabled`
  - [ ] When disabled, PM skips the ingestion step entirely
  - [ ] Can be toggled post-setup by editing `config.md`

### Discussion

> [2026-03-28 03:45] **pm/qa**: Filed from human request. Bridges GitHub Issues and SquidSquad trackers — PM auto-ingests new issues each cycle, closes them when shipped. Status: Pending — awaiting human approval.
> [2026-03-28 03:55] **pm/qa**: Human feedback: this must be opt-in, same as FEAT-SKILL-012. Setup prompts for it, config stores the choice. When disabled, PM skips the step.
> [2026-03-28 04:00] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 04:05] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 04:15] **skill-lead**: Complete. Added setup prompt (field 10), config template entry, PM Ralph Loop Step 7b with ingestion logic, close-on-ship behavior, graceful `gh` fallback. Updated SKILL.md, references/agent-instructions.md, generated pm/CLAUDE.md, config.md, CHANGELOG. Status → Pending Test.
> [2026-03-28 04:10] **pm/qa**: QA verified — all criteria pass. Opt-in, PM Step 7b ingests via gh, graceful fallback. Status → Shipped.

---

## FEAT-SKILL-014 — Update README.md to reflect current feature set

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: README.md is stale — still references `--enable-auto-mode`, hardcodes FE/BE three-agent examples in Quick Start, and doesn't mention any features shipped since v0.5.0 (status line, step markers, working state, context pressure, git-log health detection, iteration retention). The README should be updated to accurately reflect the current state of SquidSquad, including all v0.5.1 and v0.5.2 features. It should also be kept up to date going forward — when user-visible features ship, the README should be updated in the same cycle.
- **Acceptance Criteria**:
  - [ ] README reflects current boot script behavior (positional arg, interactive mode, no `--enable-auto-mode`)
  - [ ] Quick Start uses generic `[role]` examples instead of hardcoded FE/BE
  - [ ] Features section covers: status line, step markers `[squidsquad]`, working state file, context pressure exit, git-log health detection, iteration retention
  - [ ] Requirements section updated (mentions `gh` CLI as optional for GitHub integrations)
  - [ ] Architecture diagram and folder structure reflect current state (includes `statusline.sh`, `working-state.md`)
  - [ ] Ralph Loop description mentions non-blocking PM check-in, quiet cycle skipping, step markers
  - [ ] Dev agent CLAUDE.md template includes a note to update README when shipping user-visible features

### Discussion

> [2026-03-28 03:50] **pm/qa**: Filed from human request. README is significantly behind the current feature set. Status: Pending — awaiting human approval.
> [2026-03-28 04:00] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 04:20] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 04:30] **skill-lead**: Complete. Full README rewrite — removed hardcoded FE/BE examples, updated to generic [role], documented all v0.5.2 features (status line, step markers, working state, context pressure, git-log health, quiet cycles, iteration retention, PR flow, GitHub Issues ingestion, /squidsquad-status), updated requirements, boot script behavior, architecture diagram, folder structure. Status → Pending Test.
> [2026-03-28 04:10] **pm/qa**: QA verified — README covers all current features, generic [role] examples, updated folder structure with working-state.md. Status → Shipped.

---

## FEAT-SKILL-015 — Auto version bump and git tag every 10 shipped items

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: When the PM/QA verifies and ships a feature or bug fix, it should track a running count of shipped items since the last version bump. Every 10 shipped items, the PM automatically bumps the minor version number (e.g. `0.5.0` → `0.6.0`), updates `config.md`, `SKILL.md` frontmatter, and `CHANGELOG.md`, creates a git tag (`v0.6.0`), and pushes the tag. This gives the project a natural release cadence tied to actual output rather than arbitrary dates.

  **Mechanics:**
  1. `config.md` gets a new counter: `Shipped Since Last Bump: N`
  2. PM increments the counter each time it marks an item as `Shipped`
  3. When the counter reaches 10: bump minor version, reset counter to 0, update version in `config.md` + `SKILL.md` frontmatter, add a new section to `CHANGELOG.md`, create and push a git tag
  4. The bump is logged in the PM iteration log

- **Acceptance Criteria**:
  - [ ] `config.md` template includes `Shipped Since Last Bump: 0` counter
  - [ ] PM increments the counter when marking any item as `Shipped`
  - [ ] At count 10: PM bumps minor version (e.g. `0.5.x` → `0.6.0`)
  - [ ] PM updates version in `config.md` and `SKILL.md` frontmatter
  - [ ] PM adds a new version section to `CHANGELOG.md` summarizing the 10 shipped items
  - [ ] PM creates and pushes a git tag (e.g. `v0.6.0`)
  - [ ] Counter resets to 0 after bump
  - [ ] PM/QA CLAUDE.md template updated with the version bump logic
  - [ ] SKILL.md documents the auto-versioning behavior

### Discussion

> [2026-03-28 04:00] **pm/qa**: Filed from human request. Auto-version based on shipped output — every 10 items triggers a minor version bump and git tag. Status: Pending — awaiting human approval.
> [2026-03-28 05:00] **pm/qa**: Human wants this feature to be the first test case for FEAT-SKILL-016 (deep feature lifecycle). Do NOT approve yet — wait for 016 to ship, then run 015 through the full research → discussion → planning → execution → QA flow as validation.
> [2026-03-28 06:45] **pm/qa**: Human approved. Status → Planning. Beginning intake process. Running Phase 1 (Research).
> [2026-03-28 08:10] **pm/qa**: Phase 1 (Research) complete — RESEARCH.md written. Phase 2 (Discussion) complete — 7 questions resolved via interactive dialog. Phase 3 (Planning) complete — CONTEXT.md and TEST-PLAN.md written. All planning phases done. Status → Approved.
> [2026-03-28 08:35] **pm/qa**: Verified against TEST-PLAN.md — all criteria pass. Step 6c in PM template with full bump sequence, bug gate, crash recovery, config fields, SKILL.md docs, generated PM CLAUDE.md. Status → Shipped.
> [2026-03-28 08:40] **skill-lead**: Complete. Added Step 6c (Version Bump Check) to PM template and generated pm/CLAUDE.md. Added Ship Threshold + Shipped Since Last Bump to config.md and SKILL.md config template. Documented auto-versioning in SKILL.md and CHANGELOG.md. All TEST-PLAN.md criteria addressed. Status → Pending Test.

---

## FEAT-SKILL-016 — Deep research-driven Feature Intake Process with interactive questioning

- **Priority**: Critical
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Replace the PM's shallow Feature Intake Process with a deep, GSD-inspired 5-phase feature lifecycle. Full design doc: `.squidsquad/pm/FEAT-SKILL-016-design.md`.

  **The 5 phases:**
  1. **Research (PM)** — Spawn research agent: codebase impact, side effects, edge cases, integration risks → RESEARCH.md
  2. **Discussion (PM + Human)** — Present findings, ask targeted questions with WHY, capture locked decisions vs dev discretion → CONTEXT.md
  3. **Planning (PM)** — Write feature entry informed by research + discussion, AND create test cases upfront → TEST-PLAN.md
  4. **Execution (Dev)** — Implement reading RESEARCH.md + CONTEXT.md + TEST-PLAN.md, run smoke tests before Pending Test
  5. **QA (PM)** — Execute test cases from TEST-PLAN.md, record pass/fail per case, only ship when all pass

  **Locked decisions:**
  - Light mode for trivial features (PM judgment — skip research for cosmetic/doc changes)
  - Research agent token cost is acceptable
  - Planning files auto-deleted after ship (git preserves)
  - Bugs excluded — current lightweight flow stays
  - PM can recommend rejection → new `Rejected` status
  - Planning files stored in `.squidsquad/[role]/planning/FEAT-XXX-*.md`

- **Acceptance Criteria**:
  - [ ] PM Feature Intake Process in `references/agent-instructions.md` replaced with 5-phase flow
  - [ ] Phase 1: Research agent produces FEAT-XXX-RESEARCH.md (impact, side effects, edge cases, integration risks, open questions)
  - [ ] Phase 2: PM presents research, asks questions with WHY, captures locked vs discretion decisions in FEAT-XXX-CONTEXT.md
  - [ ] Phase 3: Feature entry references planning artifacts; TEST-PLAN.md created with test cases, smoke tests, regression risks
  - [ ] Phase 4: Dev agent template updated to read planning artifacts and run smoke tests before Pending Test
  - [ ] Phase 5: PM QA step executes test cases from TEST-PLAN.md, records results, only ships on all-pass
  - [ ] Light mode: PM can skip research for trivial/cosmetic features
  - [ ] Rejection path: PM can recommend `Rejected` status with research justification; human can override
  - [ ] Planning files auto-deleted after ship
  - [ ] `.squidsquad/[role]/planning/` directory structure documented in SKILL.md
  - [ ] RESEARCH.md, CONTEXT.md, TEST-PLAN.md file formats documented
  - [ ] Generated PM and dev CLAUDE.md files updated
  - [ ] Bugs excluded from this flow — current process unchanged

### Discussion

> [2026-03-28 04:20] **pm/qa**: Filed from human request. The current intake process is too shallow — the statusLine feature (FEAT-SKILL-003) is a concrete example of an impulse requirement that caused BUG-SKILL-009 because side effects weren't considered. The PM needs to do GSD-level research before writing requirements, then ask the human deep questions. Status: Pending — awaiting human approval.
> [2026-03-28 04:45] **pm/qa**: Design doc created at `.squidsquad/pm/FEAT-SKILL-016-design.md`. Researched GSD's workflow in depth. Mapped GSD phases to SquidSquad roles: research+discussion+planning on PM, execution on dev, QA on PM. Added Phase 5 (QA test execution) per human input. 5 open questions resolved by human: light mode yes, token cost acceptable, auto-cleanup yes, bugs excluded, PM can reject. Human accepted and approved. Status → Approved.
> [2026-03-28 04:50] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 05:00] **skill-lead**: Complete. Replaced 4-step Feature Intake with 5-phase lifecycle in PM template. Phase 1 research agent with structured RESEARCH.md output. Phase 2 interactive discussion with CONTEXT.md. Phase 3 planning with TEST-PLAN.md. Phase 4 dev reads planning artifacts + smoke tests. Phase 5 PM executes test cases. Light mode, rejection path, auto-cleanup. Dev template updated to read artifacts. SKILL.md documented. Generated CLAUDE.md files updated. CHANGELOG updated. Status → Pending Test.
> [2026-03-28 05:10] **pm/qa**: QA verified — all 13 acceptance criteria pass. 5-phase flow in PM template, research/context/test-plan artifacts, dev reads artifacts + smoke tests, PM QA executes test cases, light mode, rejection path, auto-cleanup, bugs excluded. Status → Shipped.

---

## FEAT-SKILL-017 — Externalize agent templates from generated CLAUDE.md files

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Currently, setup generates full CLAUDE.md files for each agent by inlining the entire template from `references/agent-instructions.md` with substitutions. This creates large, duplicated files in the user's repo that are hard to maintain and require full regeneration on every upgrade.

  Instead, externalize the templates:

  **Architecture:**
  1. During setup, copy the template files into `.squidsquad/templates/` (e.g. `dev-agent.md`, `pm-agent.md`) — these are the canonical instructions, shared across all agents of the same type
  2. Each agent's `.squidsquad/[role]/CLAUDE.md` becomes a small bootstrapper that contains only:
     - Role-specific config (role name, test command, other roles, interval)
     - A reference instruction: "Read `.squidsquad/templates/dev-agent.md` for your full Ralph Loop instructions. Substitute the config values above wherever you see `[ROLE]`, `[ROLE_TEST_CMD]`, etc."
  3. The agent reads the template at runtime — Claude pulls the file when it needs the instructions

  **Benefits:**
  - Templates maintained in one place — edit once, all agents pick up changes
  - Upgrades only update `.squidsquad/templates/` — no need to regenerate per-agent CLAUDE.md files
  - Much smaller generated files — less git bloat
  - Cleaner separation between "what this agent is" (config) and "how agents work" (template)
  - Future: templates could be pulled from a remote source for auto-updates

  **Migration:**
  - Existing setups need an upgrade path: detect inline CLAUDE.md, extract config, replace with bootstrapper
  - `references/agent-instructions.md` in the skill repo continues to be the source of truth; setup copies from there into `.squidsquad/templates/`

- **Acceptance Criteria**:
  - [ ] Setup creates `.squidsquad/templates/dev-agent.md` and `.squidsquad/templates/pm-agent.md` from `references/agent-instructions.md`
  - [ ] Generated `[role]/CLAUDE.md` is a small bootstrapper (~20 lines) with role config + reference to template
  - [ ] Agents correctly read and follow the template at runtime
  - [ ] Placeholder substitution works (agent reads config block, applies values to template)
  - [ ] Upgrade process migrates existing inline CLAUDE.md to bootstrapper + template
  - [ ] SKILL.md setup steps updated to reflect the new structure
  - [ ] File structure section updated to show `templates/` directory
  - [ ] Tested with at least two different role names to confirm substitution works

### Discussion

> [2026-03-28 04:25] **pm/qa**: Filed from human request. Architectural improvement — externalize templates so they're maintained once and referenced at runtime. Reduces duplication, simplifies upgrades, and keeps generated files small. Status: Pending — awaiting human approval.
> [2026-03-29 00:00] **pm/qa**: Human approved. Status → Planning. Beginning intake process.
> [2026-03-29 00:30] **pm/qa**: Phase 1 (research), Phase 2 (discussion), Phase 3 (test plan) complete. All decisions locked: build-time substitution, keep [ROLE] placeholders, natural-language Read instruction, auto-detect migration. Human approved. Status → Approved.
> [2026-03-29 02:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 02:10] **skill-lead**: Complete. Updated SKILL.md (Step 2 adds templates/, Step 4 split into 4a/4b/4c for template generation + bootstrapper + root CLAUDE.md, Upgrade Instructions handle migration with auto-detect), File Structure section shows templates/, references/agent-instructions.md header updated, README.md file structure and upgrade section updated, CHANGELOG.md entry added. Status → Pending Test.
> [2026-03-29 02:30] **pm/qa**: QA verified — setup generates templates + bootstrappers, upgrade path handles inline-to-bootstrapper migration via auto-detect heuristic, SKILL.md and README updated. Status → Shipped.

---

## FEAT-SKILL-018 — All planning phases should maximize subagent usage

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: The 5-phase Feature Intake Process (FEAT-SKILL-016) should leverage Claude Code subagents (via the Agent tool) as much as possible across all phases. Currently Phase 1 (Research) spawns a research agent, but the other phases run inline. The PM should delegate heavy lifting to subagents wherever feasible:

  **Potential subagent usage per phase:**
  1. **Phase 1 (Research)** — Already uses a research subagent ✅
  2. **Phase 2 (Discussion)** — Could spawn an agent to prepare question recommendations and option analysis before presenting to human
  3. **Phase 3 (Planning)** — Could spawn an agent to draft the TEST-PLAN.md and feature entry based on locked decisions
  4. **Phase 4 (Execution)** — Dev agent already handles this
  5. **Phase 5 (QA)** — Could spawn an agent to do the file-level verification pass

  Benefits: reduces context pressure on the main PM agent, enables parallel work, and keeps the PM's context window focused on coordination rather than deep file reads.

- **Acceptance Criteria**:
  - [ ] All 5 phases documented with explicit subagent delegation where applicable
  - [ ] PM template in `references/agent-instructions.md` updated with subagent spawn instructions per phase
  - [ ] Phases that remain inline have documented rationale (e.g., Phase 2 discussion must be interactive with human)
  - [ ] Generated PM CLAUDE.md reflects the subagent approach

### Discussion

> [2026-03-28 06:50] **pm/qa**: Filed from human request. Human wants maximum subagent delegation across all planning phases to reduce PM context pressure and enable parallel work. Status: Pending — awaiting human approval.
> [2026-03-28 11:30] **pm/qa**: Human approved. Status → Planning. Beginning intake process. Running Phase 1 (Research).
> [2026-03-28 11:40] **pm/qa**: Phase 1 (Research) complete. Phase 2 (Discussion) complete — 5 questions resolved. Phase 3 (Planning) complete — CONTEXT.md + TEST-PLAN.md written. Status → Approved.
> [2026-03-28 11:50] **skill-lead**: Complete. Added Phase 2A (prep subagent), updated Phase 3 (test plan subagent), updated Phase 5 (QA subagent) in agent-instructions.md. Light mode skips Phase 2A. PM writes feature entries and makes final decisions. Generated pm/CLAUDE.md updated with subagent delegation note. Status → Pending Test.
> [2026-03-28 12:00] **pm/qa**: QA verified — all 4 acceptance criteria pass. Phase 2A, 3, 5 have subagent prompts in agent-instructions.md. Phase 2 stays inline (interactive). Generated pm/CLAUDE.md references subagent delegation. Status → Shipped.

---

## FEAT-SKILL-019 — Remove boot logo section from README.md

- **Priority**: Low
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: Remove the boot logo section from README.md. Likely the ASCII squid art / startup banner section — it's not needed in the GitHub-facing documentation.

- **Acceptance Criteria**:
  - [ ] Boot logo / ASCII art section removed from README.md
  - [ ] No other content affected
  - [ ] README still reads coherently after removal

### Discussion

> [2026-03-28 09:00] **pm/qa**: Filed from human request. Straightforward cleanup — remove the boot logo section from README. Status: Pending — awaiting human approval.
> [2026-03-29 01:20] **pm/qa**: Human approved. Light mode — trivial doc-only change, skipping Research + Phase 2A + abbreviated Discussion. No open questions. Status → Approved.
> [2026-03-29 02:15] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 02:15] **skill-lead**: Complete. Removed "Boot Logo" section (heading + description paragraph) from README.md. No other content affected, README reads coherently. Status → Pending Test.
> [2026-03-29 02:30] **pm/qa**: QA verified — Boot Logo section removed, README reads coherently, no other content affected. Status → Shipped.

---

## FEAT-SKILL-020 — Web-based UI for SquidSquad interaction

- **Priority**: Low
- **Owner**: TBD
- **Status**: Pending
- **Description**: Build a web-based interface for interacting with SquidSquad without directly using the Claude CLI. Claude remains the engine powering the agents, but all human interaction (filing bugs, approving features, answering Phase 2 questions, viewing status, etc.) happens through a web UI.

  **This is a large item requiring significant planning and scoping.** Recorded for now — not ready for implementation planning.

  **High-level vision:**
  - Dashboard showing agent health, open bugs/features, shipped counter, version info
  - Feature request form → files to tracker
  - Bug report form → files to tracker
  - Phase 2 discussion UI (interactive questions)
  - Status/progress view per feature lifecycle
  - Approval workflow via UI instead of CLI conversation
  - Claude API as backend engine — agents still run via Claude Code, UI is the coordination layer

- **Acceptance Criteria**: TBD — requires scoping phase before detailed criteria can be written.

### Discussion

> [2026-03-28 09:30] **pm/qa**: Filed from human request. Large item — web UI for all SquidSquad interaction with Claude as engine. Human noted this needs more planning and scoping. Recorded for future consideration. Status: Pending — awaiting human approval.

---

## FEAT-SKILL-021 — SquidSquad status bar should append to last line only, not replace user's entire status bar

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: The current SquidSquad setup overwrites the user's entire `statusLine` config in `.claude/settings.json`. This replaces whatever custom status bar the user had before (context window usage, repo info, etc.) with the SquidSquad status line. Related to BUG-SKILL-009 which added a "check before overwriting" prompt, but the underlying design is still wrong.

  **The fix:** SquidSquad should only add its status info to the **last line** of the status bar output, preserving whatever the user's existing status bar shows above it. If the user has no custom statusLine, SquidSquad's line is the only one. If they do, SquidSquad appends below.

  **Implementation approach:**
  1. The `statusline.sh` script should first run/include the user's original status bar output (if any was saved during setup)
  2. Then append the SquidSquad line (squid emoji, role, iteration, health, etc.) as the last line
  3. Setup should save the user's existing `statusLine` command before replacing it, so it can be chained
  4. Alternatively, the script reads the JSON stdin and outputs both the default Claude status info AND the SquidSquad line

- **Acceptance Criteria**:
  - [ ] User's original status bar content preserved (context window %, repo info, etc.)
  - [ ] SquidSquad status info appears on the last line only
  - [ ] If user had no custom statusLine before setup, default Claude info + SquidSquad line shown
  - [ ] Setup does not destructively overwrite existing statusLine config
  - [ ] SKILL.md setup steps updated
  - [ ] statusline.sh template in references/agent-instructions.md updated

### Discussion

> [2026-03-28 10:00] **pm/qa**: Filed from human request. The status bar overwrite was flagged before (BUG-009 added a prompt), but the real fix is architectural: SquidSquad should only own the last line of the status bar, not the entire thing. Status: Pending — awaiting human approval.
> [2026-03-28 10:30] **pm/qa**: Human approved. Status → Planning. Beginning intake process. Running Phase 1 (Research).
> [2026-03-28 10:45] **pm/qa**: Phase 1 (Research) complete. Phase 2 (Discussion) complete — 5 questions resolved. Multi-line status bar confirmed working. Option A (chain user command) selected. Phase 3 (Planning) complete — CONTEXT.md + TEST-PLAN.md written. Status → Approved.
> [2026-03-28 11:05] **skill-lead**: Complete. Updated statusline.sh (generated + SKILL.md template) with chaining logic: reads .user-statusline, runs user command with 1s timeout, outputs user content first then SquidSquad line last. Step 5b saves existing statusLine command. Step 7 auto-merges (no prompt). Status → Pending Test.
> [2026-03-28 11:10] **pm/qa**: Verified against TEST-PLAN.md — chaining logic in statusline.sh (lines 10-16), setup saves user command (SKILL.md line 528), auto-merge (line 779), 1s timeout, silent fallback. Status → Shipped.

---

## FEAT-SKILL-022 — Silent message output for quiet/silent cycles

- **Priority**: Low
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: When the Ralph Loop runs a quiet cycle (no work done), the PM currently prints a short text message like `[🦑] Quiet cycle. Cycle N.` This still produces visible output in the conversation. The feature request is to make quiet cycles truly silent — either no output at all, or a minimal non-intrusive indicator that doesn't clutter the conversation.

- **Acceptance Criteria**:
  - [ ] Quiet cycles produce minimal or no visible output
  - [ ] Human can still tell the loop is running (e.g., via status bar, not conversation text)
  - [ ] PM and dev agent templates updated
  - [ ] Non-quiet cycles still print full step markers as before

### Discussion

> [2026-03-28 10:50] **pm/qa**: Filed from human request. Quiet cycles currently print text that clutters the conversation. Should be truly silent or minimal. Status: Pending — awaiting human approval.
> [2026-03-28 11:00] **pm/qa**: Human approved. Trivial feature — fast-tracking through planning. No research needed. Quiet cycles should produce no text output at all. The loop is still running (visible via status bar or git log). Status → Approved.
> [2026-03-28 11:08] **skill-lead**: Complete. Updated all 4 templates (agent-instructions.md dev + PM, skill/CLAUDE.md, pm/CLAUDE.md) — quiet cycles now produce no text output, skip silently to Done. Status → Pending Test.
> [2026-03-28 11:10] **pm/qa**: Verified. Dev template line 159 and PM template line 605 both say "Produce no text output — skip silently to Done." All 4 templates updated. Status → Shipped.

---

## FEAT-SKILL-023 — Smart resume for interrupted planning — skip or re-research based on state

- **Priority**: Medium
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: When the Feature Intake Process is interrupted (e.g., context reset, PM restart) and planning resumes, the PM should intelligently handle already-completed phases:

  **Two scenarios:**

  1. **Research done but not yet committed/pushed**: RESEARCH.md exists locally but hasn't been pushed to git. On resume, PM should detect the file exists and **skip re-research automatically** — proceed directly to Phase 2.

  2. **Research done and already committed**: RESEARCH.md exists in git history. On resume (new context), PM should **ask the user via AskUserQuestion** whether to re-research (research may be stale or context may have changed) or reuse the existing RESEARCH.md.

  **Same logic applies to other planning artifacts:**
  - CONTEXT.md exists → skip Phase 2 discussion, go to Phase 3
  - TEST-PLAN.md exists → skip Phase 3, feature is ready for Approved

  **Implementation:**
  At the start of each planning phase, PM checks if the output artifact already exists:
  - If exists and uncommitted → skip phase silently
  - If exists and committed → ask user via AskUserQuestion: "RESEARCH.md already exists from a previous session. Re-research or reuse?"
  - If doesn't exist → run the phase normally

- **Acceptance Criteria**:
  - [ ] PM checks for existing planning artifacts before starting each phase
  - [ ] Uncommitted artifacts → skip phase automatically
  - [ ] Committed artifacts with no code changes since → auto-reuse silently
  - [ ] Committed artifacts with code changes since → AskUserQuestion prompt to re-run or reuse
  - [ ] Code change detection: `git log --oneline <artifact_commit>..HEAD -- references/ SKILL.md CHANGELOG.md` — if commits found, code changed
  - [ ] Works for RESEARCH.md, PHASE2-PREP.md, CONTEXT.md, TEST-PLAN.md
  - [ ] PM template in `references/agent-instructions.md` updated
  - [ ] Generated PM CLAUDE.md reflects the resume logic

### Discussion

> [2026-03-28 12:00] **pm/qa**: Filed from human request. Smart resume for interrupted planning — detect existing artifacts and either skip or ask user. Two behaviors: uncommitted = auto-skip, committed = prompt user. Status: Pending — awaiting human approval.
> [2026-03-29 21:10] **pm/qa**: Human approved. Refined staleness logic: auto-reuse if no code changes since artifact commit (check git log for commits touching references/, SKILL.md, CHANGELOG.md). Only ask user if code has changed since the artifact was created. Status → Approved.
> [2026-03-29 21:35] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 21:40] **skill-lead**: Complete. Added "Artifact Resume Logic" section to `references/agent-instructions.md` before Phase 1, defining the 3-case check (uncommitted→skip, committed+no changes→reuse, committed+changes→ask user). Added resume check references to all 4 phases (Phase 1, 2A, 2, 3). Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 22:10] **pm/qa**: Verified all acceptance criteria. Artifact Resume Logic section defines 3 cases. All 4 phases have resume checks. Code change detection via git log on references/, SKILL.md, CHANGELOG.md. CHANGELOG updated. Status → Shipped.

---

## FEAT-SKILL-024 — Offer to open planning artifacts in VS Code after each phase

- **Priority**: Low
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: After each planning phase produces an artifact (RESEARCH.md after Phase 1, CONTEXT.md after Phase 2, TEST-PLAN.md after Phase 3), the PM should ask the user if they want to open it in VS Code for review. Use `AskUserQuestion` with options: "Yes, open in VS Code", "No thanks", and "Never ask again". If "Never ask again" is selected, persist the preference in `config.md` (e.g. `Open Artifacts in Editor: no`) and skip the prompt in future cycles.

- **Acceptance Criteria**:
  - [ ] After Phase 1, PM asks user if they want to view RESEARCH.md in VS Code
  - [ ] After Phase 2, PM asks user if they want to view CONTEXT.md in VS Code
  - [ ] After Phase 3, PM asks user if they want to view TEST-PLAN.md in VS Code
  - [ ] "Yes" opens the file via `code <path>` command
  - [ ] "Never ask again" saves preference to `config.md` and suppresses future prompts
  - [ ] Preference is checked before prompting — if disabled, skip silently
  - [ ] PM template in `references/agent-instructions.md` updated with this behavior
  - [ ] Generated PM CLAUDE.md reflects the new prompt

### Discussion

> [2026-03-29 00:45] **pm/qa**: Filed from human request. QoL improvement — let the user review planning artifacts in their editor with one click, with a persistent opt-out. Status: Pending — awaiting human approval.
> [2026-03-29 00:46] **pm/qa**: Human approved. Light-mode intake (trivial feature). Status → Planning.
> [2026-03-29 00:50] **pm/qa**: Scope revised — apply to all phases (RESEARCH.md, CONTEXT.md, TEST-PLAN.md), not just TEST-PLAN.md. Context and test plan updated. Human approved. Status → Approved.
> [2026-03-29 02:20] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 02:25] **skill-lead**: Complete. Added "Open Artifacts in Editor" section to PM template in agent-instructions.md with AskUserQuestion prompt, config.md persistence for "Never ask again", and code CLI fallback. Added per-phase callouts after Phase 1, 2, and 3. CHANGELOG updated. Status → Pending Test.
> [2026-03-29 02:30] **pm/qa**: QA verified — all 3 phases have "Open in editor" callouts, dedicated section in agent-instructions.md with AskUserQuestion flow, config persistence for opt-out. Status → Shipped.

---

## FEAT-SKILL-025 — Track token usage per agent per cycle

- **Priority**: Medium
- **Owner**: skill-lead
- **Description**: SquidSquad agents should track token usage each cycle. Each agent logs its token consumption (input + output tokens) in its iteration log. The PM aggregates token usage across all agents in its own iteration log and maintains a running total in `config.md` or a dedicated `pm/token-usage.md` file. This gives the human visibility into how much each agent costs per cycle and over time.

- **Acceptance Criteria**:
  - [ ] Each agent's iteration log includes token usage (input tokens, output tokens, total)
  - [ ] PM iteration log includes per-agent token usage and a cycle total
  - [ ] Running totals are maintained and accessible (cumulative usage over time)
  - [ ] Token data is sourced from Claude's usage metadata (not estimated)
  - [ ] PM template in `references/agent-instructions.md` updated
  - [ ] Dev agent template in `references/agent-instructions.md` updated
  - [ ] SKILL.md documents the token tracking behavior

### Discussion

> [2026-03-29 01:00] **pm/qa**: Filed from human request. Observability improvement — track how many tokens each agent consumes per cycle and cumulatively. Status: Pending — awaiting human approval.

---

## FEAT-SKILL-026 — `/squidsquad-pending` slash command to list pending items from tracker

- **Priority**: Medium
- **Owner**: skill-lead
- **Status**: Pending
- **Description**: Create a `/squidsquad-pending` slash command that reads the actual tracker files and displays a summary of all pending work. This prevents stale answers from memory — the command always reads the live files. Should show: pending features (awaiting approval), approved features (ready for dev), open bugs, features pending test, and any items in Planning status.

- **Acceptance Criteria**:
  - [ ] `/squidsquad-pending` command defined in SKILL.md
  - [ ] Command reads `[role]/features.md` and `[role]/bugs.md` for all agents
  - [ ] Output groups items by status: Pending, Planning, Approved, In Progress, Pending Test, Open bugs
  - [ ] Each item shows ID, title, priority, and owner
  - [ ] Empty groups are omitted from output
  - [ ] Works from any Claude session (not just PM/QA)

### Discussion

> [2026-03-29 01:15] **pm/qa**: Filed from human feedback. PM answered "what's pending" from conversation memory and gave stale data. A slash command ensures the tracker files are always read fresh. Status: Pending — awaiting human approval.

---

## FEAT-SKILL-027 — Designer agent template with external design tool integration

- **Priority**: High
- **Owner**: skill-lead
- **Description**: Add a new agent template type — **Designer** — alongside the existing Dev and PM/QA templates. The designer agent works with external design tools (Figma, Google Stitch, and others) and bridges design output into frontend implementation.

  **Key capabilities:**
  1. **External tool integration**: The designer agent should support connecting to design tools via MCP or API (Figma API, Google Stitch, etc.). The architecture should be generalized — not hard-coded to one tool — so any design platform can be plugged in.
  2. **Design-to-code handoff**: The designer produces design artifacts (component specs, tokens, layout specs, asset references) that the FE agent can consume to produce UI. The handoff format should be structured and live in `.squidsquad/designer/` or a shared `design-specs/` directory.
  3. **Designer Ralph Loop**: Different from the dev loop — instead of fix bugs → implement features, the designer loop would be: pull latest → review design requests → fetch/update designs from external tool → produce/update design specs → hand off to FE agent → commit.
  4. **Cross-agent coordination**: The designer files design specs, the FE agent implements them. PM/QA verifies visual fidelity. Needs a new tracker flow: design request → design spec → FE implementation → visual QA.
  5. **Setup integration**: During setup, if user adds a `designer` role, use the Designer template instead of the generic Dev template. Auto-detect by role name or let user choose template type.

  **Generalized design tool abstraction:**
  - A `design-tools.md` config or section in `config.md` listing connected tools and their access method (MCP tool name, API endpoint, etc.)
  - The designer template references this config — "use whichever design tool is configured" rather than hard-coding Figma
  - Support for: fetching component specs, exporting design tokens (colors, spacing, typography), downloading assets, reading annotations/comments

- **Acceptance Criteria**:
  - [ ] New Template 3 (Designer Agent) added to `references/agent-instructions.md`
  - [ ] Designer template has its own Ralph Loop optimized for design workflows
  - [ ] Design tool integration is generalized — works with Figma, Google Stitch, or any MCP-connected design tool
  - [ ] Design-to-FE handoff format defined (component specs, tokens, layout specs)
  - [ ] Cross-agent flow documented: designer → FE → PM/QA visual verification
  - [ ] Setup detects `designer` role and uses Designer template
  - [ ] SKILL.md updated with designer role documentation
  - [ ] Works even without an external tool connected (manual design spec mode)

### Discussion

> [2026-03-29 01:30] **pm/qa**: Filed from human request. Major new capability — a designer agent type that integrates with external design tools (Figma, Google Stitch, etc.) and produces structured design specs for FE agents to implement. Generalized architecture, not locked to one tool. Status: Pending — awaiting human approval.

---

## FEAT-SKILL-028 — VS Code extension for SquidSquad

- **Priority**: Low
- **Owner**: TBD
- **Status**: Pending
- **Description**: Build a VS Code extension that integrates SquidSquad directly into the editor. This is a large, distant-future initiative — recorded here for later consideration. The extension would provide a GUI for SquidSquad interaction: viewing agent status, tracker state, approving features, monitoring loops, and managing the squad — all from within VS Code rather than the CLI.

- **Acceptance Criteria**: TBD — requires extensive scoping before detailed criteria can be written.

### Discussion

> [2026-03-29 02:50] **pm/qa**: Filed from human request. Distant future initiative — VS Code extension wrapping SquidSquad. Large scope, parked for later ideation. Status: Pending — awaiting human approval.

---

## FEAT-SKILL-029 — Obsidian memory layer for institutional knowledge and archives

- **Priority**: Low
- **Owner**: TBD
- **Status**: Pending
- **Description**: Add an Obsidian-compatible note vault directly in the repo (e.g. `.squidsquad/knowledge/` or a dedicated `knowledge/` directory) that serves two purposes:

  1. **Institutional knowledge base**: Store project decisions, architectural rationale, design patterns, onboarding context, and cross-session learnings in an Obsidian vault. Agents can read from and write to this vault, building up organizational memory that persists beyond conversation context windows and individual sessions. Uses Obsidian's wiki-link format (`[[note]]`) for cross-referencing.

  2. **Archive storage**: SquidSquad's archived files (completed milestone plans, old iteration logs, shipped feature planning artifacts, closed bug context) get stored here instead of being deleted or lost to git history. Browsable in Obsidian with backlinks and graph view.

  **Potential sub-skill design**: This may be implemented as a separate Claude Code skill (`squidsquad-knowledge` or similar) that SquidSquad can invoke, keeping the core skill lean. The sub-skill would handle vault initialization, note creation/linking, search, and archive ingestion.

- **Acceptance Criteria**: TBD — requires extensive scoping. May be designed as a sub-skill of SquidSquad rather than built into the core.

### Discussion

> [2026-03-29 03:00] **pm/qa**: Filed from human request. Distant future initiative — Obsidian vault as institutional knowledge layer + archive storage. Human noted this may be a sub-skill rather than core feature. Large scope, parked for later. Status: Pending — awaiting human approval.

---

## FEAT-SKILL-030 — Sub-skill plugin system with hardened phase execution

- **Priority**: High
- **Owner**: TBD
- **Status**: Pending
- **Description**: Foundational architectural redesign enabling SquidSquad to be extended via sub-skills (plugins) while maintaining execution integrity. This is a large, multi-faceted initiative covering several interconnected concerns:

  **1. Plugin system / Sub-skills:**
  Define extension points in SquidSquad where sub-skills can hook in and modify behavior — e.g., custom agent templates (designer, devops), custom Ralph Loop steps, custom QA checks, custom tracker fields, custom intake phases. Sub-skills register via a manifest and are discovered at setup/runtime. Core SquidSquad remains lean; capabilities are added through plugins.

  **2. Hardened phase execution:**
  Current phases run as conversational prompts — an agent (or user) can override instructions just by talking to it. This is fragile. Explore running phases in Claude's **non-interactive mode** (`--print` / headless) where the agent executes a fixed prompt and produces structured output, with no opportunity for conversational drift. The orchestrator (PM or a runner script) chains phase outputs together. This makes the pipeline deterministic and tamper-resistant.

  **3. Interaction layer outside Claude CLI:**
  If phases run non-interactively, human interaction (Phase 2 discussions, approvals, bug triage) needs to happen through an external interface. Explore:
  - Standalone web interface (ties into FEAT-SKILL-020)
  - VS Code extension (ties into FEAT-SKILL-028)
  - GitHub Issues / PR comments as interaction surface
  - A hybrid: non-interactive execution with interactive breakpoints that pause and wait for external input

  **4. Claude API/SDK considerations:**
  Running agents non-interactively at scale may require using the Claude API directly (via Anthropic SDK or Agent SDK) rather than spawning CLI instances. Need to explore: API usage agreements, rate limits, cost implications, how sub-skills would work in an API-driven architecture vs CLI-driven, and whether the Claude Code Agent SDK is the right foundation.

  **Key design questions to explore:**
  - What are the natural extension points in SquidSquad today?
  - How do we prevent prompt injection from overriding phase behavior?
  - Can we mix interactive and non-interactive phases in one pipeline?
  - What's the right boundary between "core" and "plugin"?
  - How do sub-skills declare dependencies on each other?

- **Acceptance Criteria**: TBD — requires deep architectural research and scoping. This is a platform-level change that affects everything.

### Discussion

> [2026-03-29 03:10] **pm/qa**: Filed from human request. Foundational platform initiative — plugin system, hardened non-interactive phase execution, external interaction surfaces, and Claude API considerations. Human specifically called out: (1) preventing conversational override of phase behavior, (2) exploring non-interactive mode + structured output, (3) interaction outside Claude CLI, (4) navigating Claude API agreements. Ties into FEAT-SKILL-020 (web UI), FEAT-SKILL-028 (VS Code extension). Large scope, parked for planning. Status: Pending — awaiting human approval.

---

## FEAT-SKILL-031 — Status bar redesign (Emoji Rich style)

- **Priority**: Medium
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: Redesign the status bar (`statusline.sh`) with an emoji-rich visual style. Replaces the current ANSI-only design with expressive emoji indicators. PM gets a two-line bar with team health and optional rest nudge on a separate line.

  **PM — all healthy, mid-planning, normal hours:**
  ```
  🦑 PM/QA v0.5.1 │ 📦 9/10 🚀 │ 📋 FEAT-017 P2 │ 🧠 [green]42%[/green] │ 🔄 2m
    🦑🦑🦑
  ```

  **PM — one stalled, no planning, late night (10pm-12am):**
  ```
  🦑 PM/QA v0.5.1 │ 📦 5/10 │ 🧠🔥 [yellow]62%[/yellow] │ 🔄 3m
    🦑🦑👻                                    🌙 late
  ```

  **PM — one never started, high context, very late (12am-2am):**
  ```
  🦑 PM/QA v0.5.1 │ 📦 7/10 │ 🧠💀 [red]85%[/red] │ 🔜 <1m
    🦑👻🥚                                    😴 rest?
  ```

  **PM — behind remote, bump ready, should be in bed (2am-6am):**
  ```
  🦑 PM/QA v0.5.1 │ 📦 10/10 🚀 │ ↓3 │ 🧠 [green]38%[/green] │ 🔄 4m
    🦑🦑                                      🛏️ sleep!
  ```

  **Dev — idle, bugs + features:**
  ```
  🦑 skill v0.5.1 │ 🐛3 ⭐2 │ 🧠 [green]25%[/green] │ 🔄 4m
  ```

  **Dev — working on feature:**
  ```
  🦑 skill v0.5.1 │ 🔨 FEAT-017 │ 🧠 [green]31%[/green] │ 🔄 3m
  ```

  **Dev — fixing bug, unpushed, caution context:**
  ```
  🦑 fe v0.5.1 │ ↑2 │ 🔨 BUG-FE-004 │ 🧠🔥 [yellow]68%[/yellow] │ 🔄 2m
  ```

  **Dev — danger context, cycle imminent:**
  ```
  🦑 skill v0.5.1 │ 🔨 FEAT-031 │ 🧠💀 [red]91%[/red] │ 🔜 <1m
  ```

  **Dev — backlog clear:**
  ```
  🦑 be v0.5.1 │ ✅ clear │ 🧠 [green]12%[/green] │ 🔄 5m
  ```

  **Locked design decisions:**
  - **Style**: Emoji Rich — emoji for all indicators, ANSI colors used for context percentage text
  - **Ship counter**: 📦 N/threshold shown on PM bar. 🚀 appears when counter >= 9 (one away from bump)
  - **Context display**: Brain emoji always shown. Stacked indicator emoji at higher tiers. Percentage text is ANSI-colored:
    - 🧠 `\033[32mNN%\033[0m` — <50% (green text)
    - 🧠🔥 `\033[33mNN%\033[0m` — 50-74% (yellow text)
    - 🧠💀 `\033[31mNN%\033[0m` — 75%+ (red text)
  - **Agent health**: 🦑 healthy, 👻 stalled (was alive, now gone), 🥚 never started — displayed on PM's **second line** as a row of icons (no agent names). User digs in if they see a 👻 or 🥚
  - **Rest nudge**: Right-aligned on PM line 2, time-based: 🌙 late (10pm-12am), 😴 rest? (12am-2am), 🛏️ sleep! (2am-6am). Hidden 6am-10pm
  - **Active task**: 🔨 FEAT-XXX or BUG-XXX shown on dev bar when working-state has an in-progress task, replaces backlog counts
  - **Version**: shown after role name, always present
  - **Ship counter position**: 📦 is position 2 (right after identity), before planning phase
  - **Git sync**: ↑N (unpushed) / ↓N (behind remote) — only shown when out of sync, hidden when clean
  - **Planning phase**: 📋 FEAT-XXX PN — shown on PM bar only during active feature intake, hidden otherwise
  - **Timer**: 🔄 Nm for normal countdown, 🔜 <1m when under 1 minute (replaces ⏳)
  - **Dropped**: iteration number (low value), "time since last" (replaced by countdown only)
  - **Emoji key** (for reference in docs):
    - 🦑 = SquidSquad brand + healthy agent
    - 👻 = stalled agent (was alive, now gone)
    - 🥚 = agent never started
    - 📦 = ship counter
    - 🚀 = version bump imminent
    - 🐛 = open bugs
    - ⭐ = actionable features
    - 🔨 = active task
    - 🧠 = context (always shown)
    - 🔥 = context caution (50-74%, stacked with 🧠)
    - 💀 = context danger (75%+, stacked with 🧠)
    - green/yellow/red ANSI = context percentage text color
    - 🔄 = next cycle countdown (normal)
    - 🔜 = next cycle imminent (<1m)
    - 📋 = planning phase in progress (PM only)
    - ↑N/↓N = git sync status (only when out of sync)
    - 🌙 = late night nudge (10pm-12am)
    - 😴 = rest nudge (12am-2am)
    - 🛏️ = sleep nudge (2am-6am)
    - ✅ = backlog clear (dev only)

- **Acceptance Criteria**:
  - [ ] `statusline.sh` rewritten with emoji-rich output matching the design above
  - [ ] PM bar outputs two lines: main info + team health (🦑/👻/🥚 icons, no names)
  - [ ] Rest nudge right-aligned on PM line 2: 🌙 late (10pm-12am), 😴 rest? (12am-2am), 🛏️ sleep! (2am-6am), hidden otherwise
  - [ ] Dev bar shows active task (from working-state.md) when in-progress, backlog counts otherwise
  - [ ] Ship counter reads from config.md `Shipped Since Last Bump` and `Ship Threshold`
  - [ ] 🚀 appears when ship counter >= threshold - 1
  - [ ] Context: 🧠 always shown, 🔥 stacked at 50-74%, 💀 stacked at 75%+
  - [ ] Context percentage text colored: green <50%, yellow 50-74%, red 75%+
  - [ ] Version read from config.md
  - [ ] Timer: 🔄 Nm for countdown, switches to 🔜 <1m when under 1 minute
  - [ ] Git sync: ↑N/↓N shown only when out of sync with remote
  - [ ] Planning phase: 📋 FEAT-XXX PN shown on PM bar during active intake
  - [ ] Ship counter at position 2 (after identity, before planning/git sync)
  - [ ] Iteration number removed from display
  - [ ] SKILL.md status bar documentation updated
  - [ ] README status bar section updated with new examples

### Discussion

> [2026-03-29 03:20] **pm/qa**: Filed with full design locked by human. Style: Emoji Rich. Key decisions: PM gets two-line bar with team health on line 2, ship counter with 🚀 at 9+, three-tier context emoji (🧠/⚠️/🔥), active task display replaces backlog when working, version always shown, iteration number dropped, timer condensed to countdown only. Status: Pending — awaiting human approval.
> [2026-03-29 03:30] **pm/qa**: Design refinement — context display updated: 🧠 always shown, 🔥 stacked at 50-74% (caution), 💀 stacked at 75%+ (danger). Percentage text ANSI-colored: green <50%, yellow 50-74%, red 75%+. Locked, not yet approved.
> [2026-03-29 03:40] **pm/qa**: Design refinement batch — added: git sync (↑N/↓N, hidden when clean), planning phase (📋 FEAT-XXX PN on PM bar), timer changed to 🔄 with 🔜 <1m when imminent, ship counter moved to position 2. All locked, not yet approved.
> [2026-03-29 04:00] **pm/qa**: Final design refinements — agent health: 🦑 healthy, 👻 stalled, 🥚 never started (no names, just icons). Rest nudge on PM line 2: 🌙 late (10pm-12am), 😴 rest? (12am-2am), 🛏️ sleep! (2am-6am). ✅ clear for empty dev backlog. Human approved. Status → Approved.
> [2026-03-29 04:05] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 04:15] **skill-lead**: Complete. Full rewrite of statusline.sh in SKILL.md with Emoji Rich design. PM two-line output with team health + rest nudge. Dev shows active task/backlog/clear. Ship counter, planning phase, git sync, context tiers, countdown timer all implemented. SKILL.md docs, README status line section, CHANGELOG updated. Status → Pending Test.
> [2026-03-29 04:20] **pm/qa**: QA verified — all acceptance criteria pass. Full Emoji Rich script in SKILL.md, PM two-line with 🦑/👻/🥚 health + rest nudge, dev shows 🔨/🐛⭐/✅, ship counter pos 2 with 🚀, 📋 planning phase, ↑↓ git sync, 🧠🔥💀 context tiers with ANSI colors, 🔄/🔜 timer. README and SKILL.md docs updated. Status → Shipped.

---

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

---

## FEAT-SKILL-033 — Heartbeat branches for agent health detection

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: Replace git-commit-based agent health detection with lightweight heartbeat branches. Each agent force-pushes a single-commit orphan branch (`heartbeat/<role>`) every cycle with a timestamp. The PM fetches and reads these branches to determine agent health, instead of relying on `git log --grep` which only detects agents that have work to commit. This solves the false-stalled problem where agents on quiet cycles (nothing to commit) appear dead.
- **Rationale**: Current health detection requires agents to push commits to main. Agents on quiet cycles produce no commits and appear stalled indefinitely. Heartbeat branches are git-native, work across machines, don't pollute main branch history, and unprotected branches allow force-push by default on GitHub (no repo config needed).
- **Acceptance Criteria**:
  - [ ] `references/heartbeat.sh` — standalone shell script that pushes orphan `heartbeat/<role>` branch on a loop (no agent involvement)
  - [ ] Boot scripts (`start-<role>.sh`) launch `heartbeat.sh` as a background process with role and interval args
  - [ ] Heartbeat script uses `git mktree` + `git commit-tree` + `git push -f` (no checkout, no working tree impact)
  - [ ] PM reads `heartbeat/<role>` via `git fetch` + `git log` to check agent liveness
  - [ ] No commits added to main branch for heartbeat purposes
  - [ ] Heartbeat interval is configurable in `config.md` (e.g. `Heartbeat Interval Seconds: 10`), default 10 seconds
  - [ ] SKILL.md setup flow includes a step asking the user to configure heartbeat interval (default 10s), explaining that agents will push lightweight `heartbeat/<role>` branches
  - [ ] PM uses configured heartbeat interval as the staleness threshold (agent stalled if heartbeat older than configured interval)
  - [ ] PM CLAUDE.md Step 7 updated to use heartbeat branches instead of `git log --grep`
  - [ ] Dev agent CLAUDE.md does NOT reference heartbeat — it's entirely handled by shell script
  - [ ] SKILL.md setup/templates updated accordingly
  - [ ] SKILL.md upgrade steps populate `Heartbeat Interval Seconds` in existing config.md (default 10s if missing)
  - [ ] Works across machines (agents on different hosts)
  - [ ] README.md includes a dedicated section explaining heartbeat branches (what they are, how they work, how to configure interval, how PM uses them for health detection)

### Discussion

> [2026-03-29 12:40] **pm/qa**: Filed from human discussion. Human identified that git-commit-based health detection causes false stalls on quiet cycles. Explored options: gitignored files (local only), GitHub Issues (API abuse), git notes (not pushed by default), heartbeat branches (git-native, cross-machine). Human approved heartbeat branches approach. Status: Pending — awaiting human approval.
> [2026-03-29 12:45] **pm/qa**: Human requested heartbeat interval be configurable in config.md, independent of iteration interval. Added to acceptance criteria.
> [2026-03-29 12:48] **pm/qa**: Human wants heartbeat setup as an explicit step in SKILL.md setup flow so the user is aware agents will push heartbeat branches. Default interval 10 seconds. Updated acceptance criteria.
> [2026-03-29 12:50] **pm/qa**: Human requested upgrade steps also populate the heartbeat interval config var for existing installs. Added to acceptance criteria.
> [2026-03-29 12:55] **pm/qa**: Human: heartbeat must NOT be done by agents — must be a standalone shell script launched by boot scripts as background process. Updated acceptance criteria: `references/heartbeat.sh` runs independently, agents are unaware. Human approved. Status → Planning. Beginning intake process.
> [2026-03-29 13:00] **pm/qa**: Planning complete. RESEARCH.md, CONTEXT.md, TEST-PLAN.md created. All key decisions locked by human during discussion. Status → Approved.
> [2026-03-29 13:04] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 13:10] **skill-lead**: Complete. Created `references/heartbeat.sh`, updated boot script templates with heartbeat launch + PID management, added `Heartbeat Interval Seconds` to config.md template and live config, added Step 5c to SKILL.md setup, updated PM Step 7 in agent-instructions.md to use heartbeat branches, updated statusline.sh health icons to read heartbeat branches, added upgrade migration for heartbeat config, updated CHANGELOG.md and README.md. Status → Pending Test.
> [2026-03-29 13:15] **pm/qa**: Human requested heartbeat branches get their own dedicated section in README.md documentation. Added to acceptance criteria.
> [2026-03-29 13:35] **pm/qa**: Verified all 13 acceptance criteria. heartbeat.sh exists and matches reference, boot scripts launch it with PID management, uses mktree+commit-tree+push-f, PM reads heartbeat branches via fetch+log with 3× staleness threshold, config.md has Heartbeat Interval Seconds, SKILL.md Step 5c added, agent-instructions.md PM Step 7 updated, dev CLAUDE.md has no heartbeat references, upgrade migration included, README.md has dedicated section. Status → Shipped.

---

## FEAT-SKILL-034 — Planning process must always consider upgrade and migration paths

- **Priority**: High
- **Status**: Shipped
- **Requested By**: human
- **Description**: The Feature Intake Process (Phases 1-3) must always include upgrade and migration path analysis as a required section. Every feature that adds config values, new files, template changes, or behavioral changes must have explicit upgrade/migration steps documented in RESEARCH.md and CONTEXT.md. This should be baked into the research subagent prompt and the CONTEXT.md template so it's never forgotten.
- **Rationale**: FEAT-SKILL-033 needed multiple rounds of human feedback to add upgrade steps. This should be automatic — the planning process should always ask: "How do existing installs get this?"
- **Acceptance Criteria**:
  - [ ] Research subagent prompt (Phase 1) includes explicit instruction to analyze upgrade/migration impact
  - [ ] RESEARCH.md template includes an "Upgrade & Migration" section
  - [ ] CONTEXT.md template includes a "Locked Decisions — Upgrade Path" section
  - [ ] TEST-PLAN.md template includes upgrade verification tests
  - [ ] `references/agent-instructions.md` Phase 1 and Phase 2 updated with upgrade/migration requirements

### Discussion

> [2026-03-29 13:05] **pm/qa**: Filed from human feedback during FEAT-SKILL-033 planning. Human noted that upgrade/migration paths should be a standard part of every feature's planning process, not something added after human prompting. Status: Pending — awaiting human approval.
> [2026-03-29 20:10] **pm/qa**: Human approved. Decision: Upgrade & Migration section is ALWAYS required in RESEARCH.md — even trivial features get "N/A — no upgrade impact." This ensures nothing slips through. Light-mode intake — no separate RESEARCH/CONTEXT files needed, feature is self-contained. Status → Approved.
> [2026-03-29 20:30] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 20:35] **skill-lead**: Complete. Updated `references/agent-instructions.md`: (1) Phase 1 research list now includes item 5 "Upgrade & migration" as always-required, (2) RESEARCH.md template has new "Upgrade & Migration" section with 5 sub-fields, (3) CONTEXT.md template has new "Upgrade Path (required)" section, (4) Phase 3 test plan subagent prompt includes "Upgrade verification tests" as item 4. Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 20:40] **pm/qa**: Verified all 5 acceptance criteria. Phase 1 research prompt has "Upgrade & migration" as item 5 (always required). RESEARCH.md template has 5-field Upgrade & Migration section. CONTEXT.md template has "Upgrade Path (required)". TEST-PLAN.md subagent prompt has "Upgrade verification tests" as item 4. CHANGELOG updated. Status → Shipped.

---

## FEAT-SKILL-035 — Delivery Manager (DM) hardcoded role with "Pending Ship" status

- **Priority**: High
- **Status**: In Progress
- **Requested By**: human
- **Description**: Introduce a Delivery Manager (DM) as a hardcoded role in SquidSquad. The DM owns the "last mile" of shipping — when a feature reaches a new `Pending Ship` status, the DM takes over to create a delivery package of all user-facing materials before the feature is marked `Shipped`. This offloads documentation work from PM (reducing context pressure so PM can run longer) and from dev agents (who focus on code). The feature lifecycle becomes: `Approved → In Progress (dev) → Pending Test (PM verifies) → Pending Ship (DM packages) → Shipped`.
- **Rationale**: PM currently handles too much — check-ins, QA, planning, version bumps, AND documentation review. The Feature Intake Process alone is a major context hog. By splitting out the shipping/docs role, PM stays lightweight and can run indefinitely. Dev agents stay focused on implementation. DM handles everything needed for external users to consume the change.
- **DM Responsibilities**:
  - All client-facing / user-facing work that isn't implementation code
  - README updates, CHANGELOG entries, user documentation
  - Configuration changes (config files, settings, CMS entries)
  - Migration/upgrade steps for existing installs
  - Content work requested by the client (e.g. CMS entries, copy changes)
  - Delivery packaging — ensuring everything a user needs is ready before marking Shipped
- **NOT DM Responsibilities** (stays with dev):
  - Implementation code
  - Bug fixes
- **Acceptance Criteria**:
  - [ ] New `Pending Ship` status added to feature lifecycle in tracker schema
  - [ ] DM role defined in `references/agent-instructions.md` as a new template
  - [ ] DM CLAUDE.md template created with Ralph Loop focused on Pending Ship items
  - [ ] PM CLAUDE.md updated — PM no longer marks features Shipped, instead marks Pending Ship after verification
  - [ ] DM picks up Pending Ship features, creates delivery package, marks Shipped
  - [ ] Boot script for DM (`start-dm.sh` / `.ps1`) added
  - [ ] SKILL.md setup flow updated to always create DM (hardcoded, not user-configured)
  - [ ] config.md updated to list DM as a permanent role
  - [ ] statusline.sh updated to show DM health icon
  - [ ] SKILL.md upgrade flow handles adding DM to existing installs

### Discussion

> [2026-03-29 13:25] **pm/qa**: Filed from human request. Human wants PM to stay lean and run forever. Key insight: shipping (docs, README, CHANGELOG) is a distinct concern from QA verification. DM is hardcoded (always present, like PM), not user-configured. Upgrade/migration stays with dev — DM only owns user-facing delivery materials. Status: Pending — awaiting human approval.
> [2026-03-29 22:15] **pm/qa**: Human clarified: DM also owns configuration changes (config.md, settings.json, new config values) and migration/upgrade steps — not just docs. Updated responsibilities. Dev only owns implementation code and bug fixes. With FEAT-043 (QA split), the full role picture is: PM (talks), QA (tests), DM (ships + configures), Dev (builds).
> [2026-03-29 22:20] **pm/qa**: Human further clarified: DM owns ALL client-facing work that isn't code. Not just shipping features — also direct client requests like CMS entries, content updates, configuration changes. DM is the "everything the client sees" agent. Updated responsibilities.
> [2026-03-29 22:25] **pm/qa**: Human clarified filing permissions: ALL agents can file bugs. DM and PM can file features. Only PM approves features (with human confirmation). DM proactively files features when it spots client-facing gaps.
> [2026-03-30 00:00] **pm/qa**: Human approved. Status → Planning. Beginning intake process.
> [2026-03-30 00:30] **pm/qa**: Phase 1 (research), Phase 2 (discussion), Phase 3 (test plan) complete. All decisions locked: single shared tracker, audience-based doc split (dev=tech, DM=user-story), PM zero delivery responsibilities, DM owns full delivery pipeline (CHANGELOG + version bump + git tag + release), delivery:skip tag for internal features, same loop interval, ship 035 before 043. Human approved. Status → Approved.
> [2026-03-30 01:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-30 01:30] **skill-lead**: Implementation complete. Created DM template (Template 3 in agent-instructions.md + live dm-agent.md), DM CLAUDE.md bootstrapper, DM boot scripts (start-dm.sh/.ps1), hints-dm.txt. Updated PM template: removed version bump (Step 6c), changed Shipped→Pending Ship in Steps 6/6b, added DM to health check. Updated dev template: Step 8 now tech docs only with delivery notes. Updated statusline.sh: DM segments + DM health icon. Updated SKILL.md: setup flow, upgrade flow, Schema 2, status flow, file structure. Updated config.md: Schema 2, DM always present. All 15 smoke tests pass. Delivery notes: DM is a new hardcoded role — user-facing docs needed for README (role descriptions, launch instructions, delivery workflow). Status → Pending Test.
> [2026-03-30 02:45] **pm/qa**: QA verified — 24/25 TCs PASS, 1 FAIL (TC-17: boot scripts not on disk yet, generated by setup/upgrade — same pattern as all agents). DM template solid, PM updated to Pending Ship, dev restricted to tech docs, version bump moved to DM, statusline has DM icon, Schema 2, config updated. Minor gap: PM lacks delivery:skip guidance (filed as follow-up). Status → Shipped.
> [2026-03-30 03:00] **pm/qa**: Reverted to In Progress — TC-17 failed (boot scripts not on disk). No shipping with failed TCs, no exceptions. Dev must fix TC-17 (generate boot scripts) before re-submitting. delivery:skip PM guidance gap filed as BUG-SKILL-032. Status → In Progress.

---

## FEAT-SKILL-036 — Boot script first message includes role for terminal title

- **Priority**: Low
- **Status**: On Hold
- **Requested By**: human
- **Description**: Change the boot scripts' first message to Claude so the first line is `🦑 [role] — [project]` and the second line is `start the loop`. This way the terminal title/tab shows which SquidSquad agent is running in that terminal (e.g. "🦑 skill — MyProject", "🦑 pm — MyProject"). Currently all agents send the same `"start the loop"` message, making terminal tabs indistinguishable.
- **Rationale**: When running multiple SquidSquad agents in separate terminals, there's no way to tell which tab is which agent at a glance. Terminal emulators typically show the command arguments in the tab title, so putting the role identifier in the first line of the message makes tabs self-identifying.
- **Acceptance Criteria**:
  - [ ] Boot script templates (`.sh` and `.ps1` for both dev and PM) send multi-line first message with `🦑 [role] — [project]` on line 1 and `start the loop` on line 2
  - [ ] CLAUDE.md auto-boot section updated to handle the new message format (still reads role from `.active-role`, ignores the first line)
  - [ ] Terminal tab/title shows the role identifier in Windows Terminal
  - [ ] SKILL.md boot script templates updated
  - [ ] Upgrade steps update existing boot scripts

### Discussion

> [2026-03-29 13:50] **pm/qa**: Filed from human request. Human wants terminal tabs to identify which SquidSquad role is running. Approach: change the first positional argument in boot scripts from `"start the loop"` to a two-line message with role on line 1. Status: Pending — awaiting human approval.
> [2026-03-29 15:30] **pm/qa**: Human wants role + project name (e.g. "🦑 skill — MyProject"). PM advised against ANSI escape sequences — Windows Terminal already picks up command arguments for tab title, ANSI escapes may conflict with Claude Code's own title management. Skip ANSI for now, add as follow-up if needed. Updated description and criteria.

---

## FEAT-SKILL-037 — Show current Ralph Loop step in status bar line 2

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: Display the agent's current Ralph Loop step in the status bar's second line. Currently line 2 shows agent health icons and rest nudge, but not what the agent is actively doing. Adding the current step (e.g. "Step 3 — QA Check", "Step 5 — Verify Bugs") would give the human real-time visibility into each agent's progress without needing to read scrollback.
- **Rationale**: When multiple agents are running, the human can't tell at a glance what each agent is doing. The `[🦑]` step markers scroll by in the terminal output, but the status bar is always visible. Showing the current step there gives persistent visibility.
- **Acceptance Criteria**:
  - [ ] Agent writes current state to `.squidsquad/<role>/current-state` on each phase/step change (step name, phase, state flags)
  - [ ] `statusline.sh` reads THIS agent's current-state file and displays active step on line 2
  - [ ] Active step format: emoji + description (e.g. "🔨 Planning for FEAT-SKILL-033..."), truncated at 60 chars with "..."
  - [ ] Health icons moved from line 2 to line 1 (right-aligned) — line 2 fully dedicated to step/hint
  - [ ] Boot scripts clear current-state on startup (`rm -f`) and agent writes "Initializing..." as first action
  - [ ] When no active step, line 2 shows rotating contextual HINTS
  - [ ] Hints are human-facing friendly prompts (not metric dumps) — e.g. "Msg me any time to talk about a feature"
  - [ ] Hints rotate every 60 seconds (timestamp modulo), phase-aware
  - [ ] Each role has its own hint pool; each phase within a role has its own sub-pool
  - [ ] Hint selection is state-driven — current-state file provides enough granularity for hints to make sense
  - [ ] Hint pools defined in templates (`references/`) — copied during setup, not hardcoded in statusline.sh
  - [ ] `statusline.sh` reads hint pools and current-state, picks the matching pool, rotates through it
  - [ ] Falls back gracefully if current-state file is missing or empty
  - [ ] CLAUDE.md templates updated to write current state at each `[🦑]` marker
  - [ ] SKILL.md templates and references updated
  - [ ] All roles covered (PM, dev agents, future DM)

### Discussion

> [2026-03-29 13:57] **pm/qa**: Filed from human request. Human wants real-time step visibility in the status bar. Approach: agents write current step to a file, statusline.sh reads it. Status: Pending — awaiting human approval.
> [2026-03-29 14:20] **pm/qa**: Human clarified: show current step of THIS agent only (not all agents). Format: emoji + description, e.g. "🔨 Planning for FEAT-SKILL-033..." — truncate with "..." if too long. Also wants contextual HINTS on line 2 when idle (role-specific). Updating acceptance criteria to reflect.
> [2026-03-29 14:40] **pm/qa**: Human clarified hints further: hints are for HUMANS, not system status. They should be friendly prompts reminding the human what they can do — e.g. "Msg me any time to talk about a feature". NOT metric dumps like "3 bugs open". Think of them as gentle nudges to interact. Updated acceptance criteria.
> [2026-03-29 15:10] **pm/qa**: Human clarified hint behavior: (1) hints ROTATE each cycle, not static, (2) each role AND each phase has its own hint pool, (3) state-driven — hint selection considers current state, (4) shell-driven — statusline.sh handles all hint logic, not the agent. Open questions: rotation mechanism (minute-based modulo vs counter file), performance of reading tracker state in shell, hint pools hardcoded in script vs config file, granularity of state awareness for hint selection.
> [2026-03-29 15:15] **pm/qa**: Human resolved open questions: (1) Agents write state to file on each phase change — statusline.sh reads it (no tracker parsing in shell). (2) Hint pools live in templates (references/) — copied during setup. (3) Enough granularity in the state file so hints always make sense for what's happening. Architecture: agent writes `.squidsquad/<role>/current-state` → statusline.sh reads state + hint pool file → picks matching pool → rotates via timestamp modulo. Updated acceptance criteria.
> [2026-03-29 16:00] **pm/qa**: Human approved. FEAT-SKILL-036 put on hold (wt dependency not wanted). Status → Planning. Beginning intake process.
> [2026-03-29 16:25] **pm/qa**: Phase 2 complete. All 5 decisions locked: (D1) health icons → line 1 right-aligned, (D2) hints rotate every 60s phase-aware, (D3) 60 chars truncation all roles, (D4) DM hints deferred, (D5) boot clear + Initializing write. RESEARCH.md, CONTEXT.md, TEST-PLAN.md created. Status → Approved.

> [2026-03-29 16:30] **skill-lead**: Picking up. Status → In Progress.

> [2026-03-29 16:45] **skill-lead**: Complete. Created `references/hints-dev.txt` and `references/hints-pm.txt` hint pool files. Updated `references/agent-instructions.md` with current-state writing protocol for both dev and PM templates. Rewrote `references/statusline.sh`: health icons moved to PM line 1 (right-aligned), line 2 shows current step from `current-state` file or rotating phase-aware hints from hint pools (60s rotation via timestamp modulo, 60 char truncation). Updated boot script templates in SKILL.md to clear and initialize `current-state` on startup. Added Step 5d for hint file copying during setup. Added `current-state` to `.gitignore`. Updated upgrade flow, CHANGELOG.md, README.md. Status → Pending Test.
> [2026-03-29 17:00] **pm/qa**: Verified all acceptance criteria. statusline.sh: current-state read (L98-105), get_line2 function with 60-char truncation (L114), 60s rotation (L156), phase-aware with idle fallback (L141). Health icons on PM line 1 (L240). Boot scripts clear+initialize in all 4 templates. Hint pools in references/ with pipe-delimited format (dev discretion — simpler than @section). .gitignore updated. agent-instructions.md both templates have state write protocol. CHANGELOG, README, SKILL.md all updated. Note: state file uses 2-field format (phase|desc) instead of 3-field (timestamp|step|desc) from research — acceptable, staleness handled by heartbeat system. Status → Shipped.

---

## FEAT-SKILL-038 — Add emoji prefixes to status bar line 2 (hints and progress)

- **Priority**: Low
- **Status**: Shipped
- **Owner**: skill-lead
- **Requested By**: human
- **Description**: Add emoji prefixes to status bar line 2 content to make hints and progress visually distinct at a glance. Use 💡 before hints (e.g. `💡 Try /squidsquad-status for a quick overview`) and 🚧 before progress/phase indicators (e.g. `🚧 Triaging bugs...`).
- **Acceptance Criteria**:
  - [ ] Hint lines in status bar line 2 are prefixed with 💡
  - [ ] Progress/phase lines in status bar line 2 are prefixed with 🚧
  - [ ] Emojis render correctly in the terminal status bar
  - [ ] 60-char truncation still applies (including emoji width)

### Discussion

> [2026-03-29 17:30] **skill-lead**: Filed per human request. Human chose 💡 for hints and 🚧 for progress after discussing options. Awaiting approval.
> [2026-03-29 17:30] **skill-lead**: Human approved directly. Status → Approved. Will pick up on next cycle.
> [2026-03-29 17:35] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 17:40] **skill-lead**: Complete. Updated `get_line2()` in both `.squidsquad/statusline.sh` and `references/statusline.sh`: hints prefixed with 💡, progress/steps prefixed with 🚧. Truncation reduced to 58 chars to account for emoji width. Smoke tested both paths — renders correctly. Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 18:00] **pm/qa**: Verified. 💡 prefix on hints (L164), 🚧 prefix on steps (L117), truncation adjusted to 58 chars (L113, L159). Both live and reference statusline updated. Process note: this feature was filed, approved, and implemented by skill agent directly with human in skill terminal — bypassed PM intake. Acceptable for trivial cosmetic change but should go through PM for anything non-trivial. Status → Shipped.

---

## FEAT-SKILL-039 — Slash command to change loop interval on the fly

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: Add a `/squidsquad-interval` slash command that changes the Ralph Loop interval for the current agent mid-session. Currently the interval is set at setup and baked into the cron job on startup — changing it requires manually editing config.md and restarting. The command should update config.md, cancel the existing cron, and create a new one with the new interval. Usage: `/squidsquad-interval 3m` or `/squidsquad-interval 10m`.
- **Rationale**: During active development the human may want faster cycles (2-3m), during quiet periods slower cycles (10-15m). Changing this should be instant without restarting agents.
- **Acceptance Criteria**:
  - [ ] New slash command `/squidsquad-interval <Nm>` defined in SKILL.md
  - [ ] Command updates `Iteration Interval > Minutes` in config.md
  - [ ] Command cancels existing cron job (CronDelete) and creates new one (CronCreate) with new interval
  - [ ] Validates input (integer >= 1, suffix m)
  - [ ] Prints confirmation with old and new interval
  - [ ] Works for both PM and dev agents
  - [ ] All agents detect interval change at cycle start and re-schedule (no restart needed)
  - [ ] Minimum 5 minutes enforced, no max
  - [ ] SKILL.md documents the command

### Discussion

> [2026-03-29 18:50] **pm/qa**: Filed from human request. Human approved immediately. Status → Planning. Beginning intake process.
> [2026-03-29 18:55] **pm/qa**: Light-mode intake complete. Decisions locked: (D1) all agents immediately via file-based signal, (D2) minimum 5 minutes. CONTEXT.md and TEST-PLAN.md (17 tests) created. Status → Approved.
> [2026-03-29 19:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 19:05] **skill-lead**: Complete. Added `/squidsquad-interval` slash command section to SKILL.md
> [2026-03-29 19:05] **pm/qa**: Verified all acceptance criteria. Slash command in SKILL.md with validation (>= 5, optional m suffix), config.md update, CronDelete+CronCreate. Step 1d (Interval Sync) in agent-instructions.md, skill/CLAUDE.md, and pm/CLAUDE.md. CHANGELOG updated. Status → Shipped.

---

## FEAT-SKILL-040 — Explicit approval gate after Phase 2 discussion before proceeding to Phase 3

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: After all Phase 2 interactive questions are completed and CONTEXT.md is written, PM should present an explicit confirmation prompt via AskUserQuestion before moving to Phase 3 (test plan). Options: "Approve — proceed to test plan", "More discussion needed", or "Reject this feature". Currently PM moves directly from Phase 2 to Phase 3 without a final check, which means the human can't pause to reconsider or add more context after seeing the full picture of locked decisions.
- **Rationale**: The Phase 2 discussion can cover many questions quickly. After all decisions are locked, the human should see a summary of what was decided and explicitly confirm they're ready to proceed. This prevents the PM from rushing into Phase 3 when the human might want to revisit a decision or add something they forgot.
- **Acceptance Criteria**:
  - [ ] After Phase 2 discussion completes and CONTEXT.md is written, PM uses AskUserQuestion to confirm
  - [ ] Options: "Approve — proceed to test plan" / "More discussion needed" / "Reject feature"
  - [ ] "More discussion" re-opens Phase 2 — PM asks what the human wants to revisit
  - [ ] "Reject" sets feature status to Rejected with reason
  - [ ] Confirmation includes a summary of locked decisions from CONTEXT.md
  - [ ] `references/agent-instructions.md` Phase 2 updated with the gate

### Discussion

> [2026-03-29 21:15] **pm/qa**: Filed from human request. Human wants an explicit checkpoint between Phase 2 and Phase 3 to confirm all decisions before test planning begins. Status: Pending — awaiting human approval.
> [2026-03-29 21:15] **pm/qa**: Human approved. Straightforward — add AskUserQuestion gate at end of Phase 2 in agent-instructions.md. Status → Approved.
> [2026-03-29 21:45] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 21:45] **skill-lead**: Complete. Added "Phase 2 Approval Gate" to `references/agent-instructions.md` between CONTEXT.md creation and Phase 3. PM presents summary of locked decisions via AskUserQuestion with 3 options: Approve, More discussion, Reject. Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 22:40] **pm/qa**: Verified all 6 acceptance criteria. Approval gate added between Phase 2 and Phase 3 with AskUserQuestion, 3 options (Approve/More discussion/Reject), locked decision summary, re-open and reject flows. Status → Shipped.

---

## FEAT-SKILL-041 — Setup flow improvements: project context gathering + guided agent selection

- **Priority**: Medium
- **Status**: Pending
- **Owner**: skill-lead
- **Requested By**: human
- **Description**: Two improvements to the setup flow:

  **Part A — Project context gathering**: During setup, help the user create a comprehensive `CLAUDE.md` project context file so all agents (and normal Claude sessions) understand the codebase and the user's goals from day one. Detect whether a project-level `CLAUDE.md` already exists — if it does, skip (context already provided). If not, guide the user through context gathering: (1) **Auto-explore**: use agents to scan repo structure, key files, tech stack, patterns, and summarize findings, (2) **User interview**: ask about project goals, what they're trying to accomplish, current priorities, architecture decisions, team conventions, and any context that would help Claude work effectively. Combine both into a well-structured `CLAUDE.md` — not just a tech summary, but a full picture of what the user is building, why, and how they want to work.

  **Part B — Guided agent selection**: Replace the current freeform "list your dev agents" prompt (Step 1) with a guided walkthrough of all supported role types. For each role type SquidSquad supports, ask the user if they want one. Currently supported: dev agents (named, e.g. BE/FE/skill). Future roles (DM, Designer) should be wired in as they ship. Example flow: "Add a dev agent? → Name? → Add another? → Add a DM agent? → Add a designer agent?" Each role type uses its own template from `references/agent-instructions.md`.

- **Acceptance Criteria**:
  - [ ] Setup detects existing `CLAUDE.md` — if present, skips context gathering with a note
  - [ ] If no `CLAUDE.md`, runs auto-explore (subagent scans repo: file structure, manifest files, key directories, README) and presents findings
  - [ ] Asks user about project goals, current priorities, architecture decisions, coding conventions, and any other context
  - [ ] Combines auto-explored tech context with user-provided project context into a structured `CLAUDE.md`
  - [ ] `CLAUDE.md` includes sections: Project Overview, Goals & Priorities, Tech Stack, Architecture, Conventions, Key Files/Directories
  - [ ] User can skip context gathering entirely if they prefer to write CLAUDE.md themselves
  - [ ] Step 1 agent selection walks through each supported role type (dev, DM, designer) instead of freeform input
  - [ ] Each dev agent gets a name prompt (e.g. BE, FE, skill)
  - [ ] Non-dev roles (DM, designer) are yes/no — they use predefined templates
  - [ ] Setup only offers role types that have templates available (future-proof for new roles)
  - [ ] SKILL.md setup flow updated with both changes
  - [ ] Works for any project type (not just JS/TS)

### Discussion

> [2026-03-29 21:20] **skill-lead**: Filed per human request. Key design question: should auto-explore be a subagent or inline? Subagent is better for context isolation. Status: Pending — awaiting human approval.
> [2026-03-29 21:25] **skill-lead**: Updated per human feedback. Expanded scope: not just codebase scanning but also interviewing the user about their goals, priorities, and how they want to work. CLAUDE.md becomes a full project context doc, not just a tech summary. Added skip option.
> [2026-03-29 21:30] **skill-lead**: Updated again per human feedback. Added Part B — guided agent selection. Current Step 1 asks for dev agents as freeform list; should instead walk through each role type SquidSquad supports (dev, DM, designer) one at a time. Dev agents are named (BE/FE/etc.), other roles are yes/no. Human redirecting to PM for further discussion and approval.
> [2026-03-29 21:45] **pm/qa**: Human feedback on Part B role descriptions. Each role step should briefly describe the role so the user understands what they're adding:
> - **Dev agent**: All-around developer. Just give it a name (e.g. FE, BE, DevOps, skill). Can add multiple.
> - **Delivery Manager (DM)**: Owns the "last mile" of shipping — README updates, CHANGELOG entries, user-facing documentation. Takes over after PM verifies a feature, packages it for users.
> - **Designer**: (description TBD when FEAT-SKILL-027 is designed)
>
> **Dependency note**: DM role (FEAT-SKILL-035) and Designer role (FEAT-SKILL-027) are both Pending. Part B of this feature can only fully offer those roles once their templates exist. Options: (1) ship Part B with dev-only now, add DM/designer prompts as those features ship, or (2) wait until at least FEAT-035 ships. Recommend option 1 — ship dev-only guided selection now, wire in new roles as they land.

---

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

---

## FEAT-SKILL-043 — Separate QA from PM into its own hardcoded agent role

- **Priority**: High
- **Status**: Pending
- **Requested By**: human
- **Description**: Split the current PM/QA agent into two distinct hardcoded roles:

  **PM (Product Manager)** — the talker. Owns:
  - Human check-ins and communication
  - Feature intake process (Phases 1-3: research, discussion, test plan)
  - Backlog management, priority changes
  - Feature filing from human input
  - Version bump decisions

  **QA (Quality Assurance)** — the tester. Owns:
  - QA coherence pass (reading skill files for issues)
  - Bug verification (Fixed → Verified → Closed)
  - Feature testing (Pending Test → Shipped)
  - Agent health checks
  - Filing bugs from QA findings

  PM does NO testing. PM is primarily the interface between the human and the squad. QA runs its own Ralph Loop independently, testing and verifying work.

- **Rationale**: PM's context gets consumed by QA work (reading lots of files for coherence checks, verifying features against acceptance criteria). Splitting them keeps PM lean and focused on human interaction. QA can run at its own pace with its own interval.
- **Acceptance Criteria**:
  - [ ] QA is a hardcoded role (always present, like PM), not user-configured
  - [ ] QA has its own Ralph Loop template in `references/agent-instructions.md`
  - [ ] QA has its own boot script (`start-qa.sh` / `start-qa.ps1`)
  - [ ] QA owns: QA pass, bug verification, feature testing, agent health checks, filing bugs
  - [ ] PM owns: human check-ins, feature intake, backlog management, priority changes, version bumps
  - [ ] PM does NO testing or verification — hands off after Phase 3
  - [ ] PM is primarily the human-facing conversational agent
  - [ ] QA has its own tracker directory (`.squidsquad/qa/`) or shares PM's trackers (design decision)
  - [ ] QA can have its own loop interval independent of PM
  - [ ] Setup generates QA agent alongside PM automatically
  - [ ] SKILL.md updated with QA role definition, templates, boot scripts
  - [ ] Upgrade steps add QA to existing installs

### Discussion

> [2026-03-29 22:15] **pm/qa**: Filed from human request. Human wants PM to be "primarily the talker" — no testing. QA becomes its own hardcoded agent that runs independently. Key design decisions needed: does QA share PM's trackers or have its own? Does QA report findings to PM (who relays to human) or directly to dev agents? How does version bump work — PM decides but QA provides the ship count?

---

## FEAT-SKILL-044 — Granular status phases with item names across all agents

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: Replace generic status phases with distinct, granular phases that include the specific item being worked on. The status bar should telegraph the real status — not just "verifying" but "verifying BUG-SKILL-029". Applies to all agent roles (PM, dev, future DM/QA). PM currently has generic phases (`pulling`, `checkin`, `testing`, `verifying`, `planning`, `health`, `idle`); these should be expanded with distinct phases like `researching`, `discussing`, `test-planning` for the Feature Intake flow. Dev agents should similarly include item names in all phases.
- **Current PM phases**: `pulling`, `checkin`, `testing`, `verifying`, `planning`, `health`, `idle`
- **Proposed PM additions**: `researching` (Phase 1), `discussing` (Phase 2), `test-planning` (Phase 3), plus item names in all existing phases (e.g. `verifying|Verifying BUG-SKILL-029...`)
- **Scope**: All agent CLAUDE.md templates, agent-instructions.md, statusline.sh (if phase display needs updating)
- **Acceptance Criteria**:
  - [ ] PM status phases expanded: `researching`, `discussing`, `test-planning` added as distinct phases
  - [ ] All PM status writes include item name (e.g. `verifying|Verifying BUG-SKILL-029...`, `researching|Researching FEAT-SKILL-035...`)
  - [ ] Dev agent status writes include item name (e.g. `implementing|🔨 FEAT-SKILL-037...`, `triaging|Fixing BUG-SKILL-029...`)
  - [ ] Future DM/QA templates follow the same pattern
  - [ ] statusline.sh handles new phase values correctly (display, colors if applicable)
  - [ ] SKILL.md templates updated with new phase vocabulary
  - [ ] agent-instructions.md updated with new phase examples

### Discussion

> [2026-03-30 00:05] **pm/qa**: Filed from human request. Human wants the status bar to "telegram the real status" — distinct phases with item names, not generic labels. Applies to all agents. Status: Pending — awaiting human approval.
> [2026-03-30 00:10] **pm/qa**: Human approved. Light mode — cosmetic/template change, no behavioral risk. Skipping Phase 1 (Research) and Phase 2A. Status → Planning. Beginning intake process.
> [2026-03-30 00:15] **pm/qa**: Phase 2 complete. Locked: all agents, distinct phases (researching/discussing/test-planning), uniform styling, per-item updates. Phase 3 complete — TEST-PLAN.md created (20 TCs, 9 smoke, 6 regression risks). Status → Approved.
> [2026-03-30 00:45] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-30 00:50] **skill-lead**: Implementation complete. Updated: references/agent-instructions.md (dev + PM templates — new phases, item names in all examples), live .squidsquad/pm/CLAUDE.md (phase list + Feature Intake phase writes), live .squidsquad/skill/CLAUDE.md (item names in examples). statusline.sh already handles unknown phases gracefully — no changes needed. All smoke tests passing. Status → Pending Test.
> [2026-03-30 01:30] **pm/qa**: QA verified — 19/19 verifiable TCs PASS, 9/9 smoke tests PASS. PM template has all 10 phases including researching/discussing/test-planning with item IDs. Dev template has item IDs in examples. statusline.sh handles new phases gracefully. Status → Shipped.

---

## FEAT-SKILL-045 — Overdue emoji on status bar when loop iteration is delayed

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: When an agent's Ralph Loop cycle runs longer than the configured iteration interval (e.g. 30 minutes) because it's blocked on work (long Feature Intake discussion, big implementation, etc.), show an overdue emoji in the statusline next to the countdown timer. This gives the human an at-a-glance indicator that an agent is running long and the next cycle is delayed.
- **Behavior**:
  - Overdue triggers immediately when elapsed time exceeds the iteration interval (no grace period)
  - Emoji appears at/near the countdown timer position in the statusline
  - Applies to all agents (PM, dev, future DM/QA)
  - When not overdue, no indicator shown (clean default state)
- **Acceptance Criteria**:
  - [ ] statusline.sh detects when an agent's current cycle has exceeded the iteration interval
  - [ ] Overdue emoji displayed next to the countdown/timer area when interval exceeded
  - [ ] Works for all agent roles
  - [ ] No indicator shown when cycle is within normal interval
  - [ ] Triggers immediately at interval boundary (no grace period)
  - [ ] SKILL.md statusline documentation updated
  - [ ] agent-instructions.md statusline section updated

### Discussion

> [2026-03-30 00:20] **pm/qa**: Filed from human request. Human wants visibility into when agents are running long. Overdue emoji at the countdown timer, all agents, immediate trigger at interval boundary. Status: Pending — awaiting human approval.
> [2026-03-30 00:25] **pm/qa**: Human approved. Light mode — statusline-only change, low risk. Skipping Research + Phase 2A. No open questions (behavior fully specified). CONTEXT.md and TEST-PLAN.md to follow. Status → Planning.
> [2026-03-30 00:35] **pm/qa**: Phase 2 (no open questions) and Phase 3 complete. CONTEXT.md and TEST-PLAN.md created (13 TCs, 9 smoke, 5 regression risks). Status → Approved.
> [2026-03-30 02:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-30 02:10] **skill-lead**: Implementation complete. Modified statusline.sh timer logic: when REMAINING <= 0, shows ⏰ +Nm (overdue by N minutes) instead of 🔜 <1m. Applies to all roles (shared timer section). Updated SKILL.md and agent-instructions.md docs. All smoke tests pass. Delivery notes: overdue emoji (⏰) appears when agent cycle exceeds iteration interval, shows overage time (+Nm), triggers at boundary with no grace period. Status → Pending Test.
> [2026-03-30 02:30] **pm/qa**: QA verified — 13/13 TCs PASS. Overdue emoji ⏰ +Nm at REMAINING<=0, all roles use shared TIMER_STR, boundary correct, clean default, docs updated in SKILL.md and agent-instructions.md. Status → Shipped.

---

## FEAT-SKILL-046 — Bug discussion flow: PM investigates and presents fix before filing to dev

- **Priority**: High
- **Status**: Approved
- **Requested By**: human
- **Description**: Currently when a bug is identified (from test failures, human reports, or QA), PM files it directly to the dev agent's tracker with no discussion. The human has no chance to weigh in on the fix approach. This feature adds a discussion step: when a bug is mentioned or discovered, PM immediately investigates the root cause, presents the problem and proposed fix to the human, and asks if more discussion is needed. Only after the human is satisfied with the approach does PM file it to the dev agent.
- **Current Flow**: Bug discovered → PM files to dev tracker → Dev picks up and fixes however it sees fit
- **Proposed Flow**: Bug discovered → PM investigates root cause and possible fixes → PM presents problem + proposed fix to human → Human confirms or discusses further → PM files to dev tracker with the agreed-upon fix approach
- **Scope**: PM CLAUDE.md template, agent-instructions.md PM template (Steps 4, 2 — bug filing from test failures and human reports)
- **Acceptance Criteria**:
  - [ ] PM investigates the root cause when a bug is reported or discovered
  - [ ] PM presents the problem and proposed fix to the human before filing
  - [ ] Human can discuss the fix further or approve it
  - [ ] Only after human approval does the bug get filed to the dev tracker
  - [ ] Filed bug includes the agreed-upon fix approach in the Description or Discussion
  - [ ] Works for all bug sources: human reports, test failures, QA findings
  - [ ] PM CLAUDE.md template updated with bug discussion flow
  - [ ] agent-instructions.md PM template updated

### Discussion

> [2026-03-30 14:00] **pm/qa**: Filed from human request. Human wants a chance to discuss and steer bug fixes before they go to dev. Currently bugs go straight to dev with no human input on the approach. New flow: investigate → present → discuss → file. Status: Pending — awaiting human approval.
> [2026-03-31 00:05] **pm/qa**: Human approved. Light mode — PM template behavior change, low technical risk. Status → Planning. Beginning intake process.
> [2026-03-31 00:10] **pm/qa**: Phase 2 (no open questions) and Phase 3 complete. CONTEXT.md and TEST-PLAN.md created (11 TCs, 8 smoke, 6 regression risks). Status → Approved.

---

## FEAT-SKILL-047 — Replace heartbeat branches with GitHub commit statuses for agent health

- **Priority**: High
- **Status**: Planning
- **Requested By**: human
- **Description**: Replace the current heartbeat branch system (FEAT-SKILL-033) with GitHub commit statuses via `gh api`. Heartbeat branches require `git fetch` which is slow and conflicts with active git work. Commit statuses are sub-second HTTP calls that bypass git entirely.
- **How It Works**:
  - Each agent posts a commit status to HEAD at the end of every cycle (including quiet cycles):
    ```
    gh api repos/OWNER/REPO/statuses/$(git rev-parse HEAD) -f state=success -f context="squidsquad/<role>" -f description="cycle N — <phase> — <timestamp>"
    ```
  - PM reads all statuses on HEAD to check agent health:
    ```
    gh api repos/OWNER/REPO/commits/HEAD/statuses
    ```
  - statusline.sh reads commit statuses instead of heartbeat branches
  - No background process needed — agents post status inline at cycle end
  - **Also fixes BUG-SKILL-035** (stale timer): statusline reads the timestamp from the commit status instead of iteration file mtime
- **Replaces**: heartbeat.sh background process, heartbeat branches, `git fetch origin heartbeat/<role>`
- **Acceptance Criteria**:
  - [ ] Agents post commit status at end of every cycle (quiet and productive)
  - [ ] PM reads commit statuses for health check (Step 7) instead of heartbeat branches
  - [ ] statusline.sh reads commit status timestamps for timer instead of iteration file mtime
  - [ ] heartbeat.sh removed or deprecated
  - [ ] Boot scripts no longer launch heartbeat background process
  - [ ] Health detection works without any git fetch/pull
  - [ ] Config: repo owner/name available for API calls (or derived from `gh repo view`)
  - [ ] Graceful fallback if `gh` CLI not available — agent continues, health shows ❓
  - [ ] Health icons updated: 🦑 healthy, 👻 stalled, ❓ unknown/no data (replaces 🥚)
  - [ ] PM scans statuses on last 2-3 commits (not just HEAD) to handle SHA divergence between agents
  - [ ] SKILL.md, agent-instructions.md, README updated
  - [ ] Fixes BUG-SKILL-035 (stale timer on quiet cycles)

### Discussion

> [2026-03-31 00:00] **pm/qa**: Filed from human request. Human wants faster, more reliable health detection using GitHub API instead of git operations. Chose commit statuses (Option 1) over GitHub Issues or Gists — purpose-built for status reporting, sub-second, visible in GitHub UI. Also fixes the stale timer bug (BUG-035) since status is posted every cycle including quiet ones.
> [2026-03-31 00:20] **pm/qa**: Human chose Option 2 for SHA convergence — agents re-post to current HEAD each cycle. PM scans last 2-3 commits as belt-and-suspenders. Edge cases discussed: simultaneous pushes (scan handles it), fresh repo (skip if no HEAD), gh failure (graceful fallback, show ❓), rate limits (not a concern at ~12 req/hr). Health icon ❓ replaces 🥚 for unknown/no data state.
> [2026-03-31 00:25] **pm/qa**: Human approved. Status → Planning. Beginning intake process.
