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
- **Status**: Pending
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

---

## FEAT-SKILL-018 — All planning phases should maximize subagent usage

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Pending
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

---

## FEAT-SKILL-019 — Remove boot logo section from README.md

- **Priority**: Low
- **Owner**: skill-lead
- **Status**: Pending
- **Description**: Remove the boot logo section from README.md. Likely the ASCII squid art / startup banner section — it's not needed in the GitHub-facing documentation.

- **Acceptance Criteria**:
  - [ ] Boot logo / ASCII art section removed from README.md
  - [ ] No other content affected
  - [ ] README still reads coherently after removal

### Discussion

> [2026-03-28 09:00] **pm/qa**: Filed from human request. Straightforward cleanup — remove the boot logo section from README. Status: Pending — awaiting human approval.

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
- **Status**: Approved
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

---

## FEAT-SKILL-022 — Silent message output for quiet/silent cycles

- **Priority**: Low
- **Owner**: skill-lead
- **Status**: Pending
- **Description**: When the Ralph Loop runs a quiet cycle (no work done), the PM currently prints a short text message like `[🦑] Quiet cycle. Cycle N.` This still produces visible output in the conversation. The feature request is to make quiet cycles truly silent — either no output at all, or a minimal non-intrusive indicator that doesn't clutter the conversation.

- **Acceptance Criteria**:
  - [ ] Quiet cycles produce minimal or no visible output
  - [ ] Human can still tell the loop is running (e.g., via status bar, not conversation text)
  - [ ] PM and dev agent templates updated
  - [ ] Non-quiet cycles still print full step markers as before

### Discussion

> [2026-03-28 10:50] **pm/qa**: Filed from human request. Quiet cycles currently print text that clutters the conversation. Should be truly silent or minimal. Status: Pending — awaiting human approval.
