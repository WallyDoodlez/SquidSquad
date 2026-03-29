---
name: squidsquad
description: "Your AI dev team that coordinates through markdown, not meetings."
version: 0.5.1
---

# SquidSquad

You are activating the SquidSquad multi-agent development coordination system. SquidSquad spins up Claude Code CLI instances — one per dev role you define, plus a PM/QA — that work autonomously on a shared codebase by coordinating through markdown files in a `.squidsquad/` folder.

No meetings. No message queues. Just markdown.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Git Repository                       │
│                                                          │
│  ┌──────────────┐        ┌──────────────┐  ┌──────────┐ │
│  │  [Role] Lead │  ...   │  [Role] Lead │  │  PM / QA │ │
│  │ (Claude CLI) │        │ (Claude CLI) │  │(Claude CLI│ │
│  └──────┬───────┘        └──────┬───────┘  └─────┬────┘ │
│         │                       │                │      │
│         └───────────┬───────────┘                │      │
│                     ▼                            │      │
│              .squidsquad/                        │      │
│              ├── config.md  ◄────────────────────┘      │
│              ├── [role]/          ← one per dev agent    │
│              │   ├── CLAUDE.md                           │
│              │   ├── bugs.md                             │
│              │   ├── features.md                         │
│              │   └── iterations/                         │
│              └── pm/                                     │
│                  ├── CLAUDE.md                            │
│                  ├── qa-log.md                            │
│                  ├── enhancements.md                      │
│                  └── iterations/                          │
└──────────────────────────────────────────────────────────┘
```

### Roles

SquidSquad always has a **PM/QA** agent. Dev agents are flexible — you define them at setup time.

| Agent | Owns | Loop |
|-------|------|------|
| **[role] Lead** (one per dev role) | Code for that role, `[role]/bugs.md`, `[role]/features.md` | Ralph Loop (fix bugs → implement features → test → push) |
| **PM/QA** | Product backlog, `pm/qa-log.md`, `pm/enhancements.md`, human interaction | Ralph Loop (check human → run e2e → log → file bugs → verify → push) |

**Common team shapes:**

| Shape | Dev agents | Use when |
|-------|-----------|----------|
| `fe, be` | FE Lead + BE Lead | Full-stack app with separate frontend and backend |
| `be` | BE Lead only | API-only, CLI tool, library, or skill repo |
| `api, worker` | API Lead + Worker Lead | Backend split across services |
| `web, ios, api` | Web + iOS + API | Multi-platform product |
| _(any names)_ | Whatever you define | Custom team topology |

---

## File Structure Generated

When you invoke SquidSquad, it creates the following inside your project root. One folder is generated per dev agent — the example below shows a `be`-only setup:

```
.squidsquad/
├── config.md                   ← project config, test commands, counters, git protocol
├── templates/                  ← shared agent instruction templates (build-time substituted)
│   ├── dev-agent-be.md         ← full Ralph Loop instructions for BE Lead
│   └── pm-agent.md             ← full Ralph Loop instructions for PM/QA
├── start-be.sh / start-be.ps1  ← boot script: launches BE Lead (autonomous)
├── start-pm.sh / start-pm.ps1  ← boot script: launches PM/QA (interactive)
├── be/                         ← one folder per dev agent, named after the role
│   ├── CLAUDE.md               ← bootstrapper (~20 lines): role config + Read instruction to template
│   ├── bugs.md                 ← BUG-BE-XXX tracker with Discussion sections
│   ├── features.md             ← FEAT-BE-XXX tracker with Discussion sections
│   └── iterations/             ← iter-N.md logs per cycle
└── pm/
    ├── CLAUDE.md               ← bootstrapper (~20 lines): role config + Read instruction to template
    ├── qa-log.md               ← QA test run results
    ├── enhancements.md         ← product backlog / enhancement proposals
    ├── iterations/             ← iter-N.md logs per cycle
    └── migrations/             ← migration logs written when tracker schema changes
```

For `fe, be` the structure gains a `fe/` folder and `start-fe.sh/.ps1` alongside `be/`.

---

## Tracker Formats

### Bug Format (`bugs.md`)

```markdown
## BUG-FE-001 — [Title]

- **Severity**: Critical | High | Medium | Low
- **Status**: Open | Investigating | Fixed | Verified | Closed
- **Reported By**: pm/qa | be-lead | human
- **Assigned To**: fe-lead
- **Description**: What is broken and where.
- **Steps to Reproduce**:
  1. Step one
  2. Step two
- **Expected**: What should happen
- **Actual**: What actually happens

### Discussion

> [2026-01-15 09:00] **pm/qa**: Reproduced on Chrome 120 and Safari 17.
> [2026-01-15 09:45] **fe-lead**: Looks like a race condition in the auth hook. Investigating.
> [2026-01-15 10:30] **fe-lead**: Fixed in commit abc1234. Status → Fixed.
> [2026-01-15 11:00] **pm/qa**: Verified. Status → Closed.
```

Status flow: `Open` → `Investigating` → `Fixed` → `Verified` → `Closed`

### Feature Format (`features.md`)

```markdown
## FEAT-FE-001 — [Title]

- **Priority**: Critical | High | Medium | Low
- **Status**: Pending | Planning | Approved | In Progress | Pending Test | Shipped
- **Owner**: fe-lead
- **Description**: What to build.
- **Acceptance Criteria**:
  - [ ] Criterion one
  - [ ] Criterion two

### Discussion

> [2026-01-15 09:00] **pm/qa**: Proposed for this sprint.
> [2026-01-15 09:30] **human**: Approved. Go ahead.
> [2026-01-15 10:00] **fe-lead**: Picking this up. Status → In Progress.
> [2026-01-15 12:00] **fe-lead**: Complete. Status → Pending Test.
> [2026-01-15 13:00] **pm/qa**: Tested and passing. Status → Shipped.
```

Status flow: `Pending` → `Planning` → `Approved` → `In Progress` → `Pending Test` → `Shipped` (or `Rejected`)

> **Note:** `Pending` means awaiting human approval. `Planning` means human approved and PM is running the Feature Intake Process (Research → Discussion → Planning). `Approved` means planning is complete and a dev agent can pick it up. `Rejected` means PM recommends against it — human can override.

### Feature Lifecycle (5-Phase)

Features go through a deep, research-driven lifecycle before reaching the dev agent:

1. **Research (PM)** — Spawn research agent: codebase impact, side effects, edge cases, integration risks → `FEAT-XXX-RESEARCH.md`
2. **Discussion (PM + Human)** — Present findings, ask targeted questions with WHY, capture locked decisions vs dev discretion → `FEAT-XXX-CONTEXT.md`
3. **Planning (PM)** — Write feature entry + test cases → `FEAT-XXX-TEST-PLAN.md`
4. **Execution (Dev)** — Implement reading planning artifacts, run smoke tests before Pending Test
5. **QA (PM)** — Execute test cases from TEST-PLAN.md, record pass/fail, only ship when all pass

Planning files live in `.squidsquad/[role]/planning/` and are auto-deleted after ship (git preserves them). Bugs are excluded — they use the current lightweight flow. Trivial/cosmetic features can use light mode (PM skips research).

---

## The Ralph Loop

Each agent runs its own Ralph Loop — an autonomous work cycle that repeats on an interval. On startup, agents invoke `/loop [INTERVAL]m execute one Ralph Loop cycle` to schedule repeating cycles. The `/loop` command handles timing and re-invocation reliably — agents do NOT manually sleep or self-loop. Each cycle prints visible start/stop markers with timestamps (e.g. `[🦑] ---- cycle 3 started at 14:32:07 ----`) so the human can spot cycle boundaries in terminal scrollback.

Every step within the loop also prints a `[🦑]` prefixed marker (e.g. `[🦑] Pulling latest...`, `[🦑] Triaging bugs...`). Key sub-actions (filing bugs, verifying fixes, committing) get their own markers too. This makes SquidSquad activity easy to scan in scrollback.

**Iteration log retention**: each agent keeps the last 20 iteration files in its `iterations/` directory. After logging a new iteration, older files beyond this limit are deleted. Git history preserves them if ever needed.

All agents maintain a **working state file** (`.squidsquad/[role]/working-state.md`) that tracks the current task, completed steps, and remaining work. This file is read on startup to resume mid-task after a context window reset. Agents also check **context pressure** at the start of each cycle — if `context_window.used_percentage` exceeds the threshold in `config.md` (default 80%), they save state, commit, and exit so the boot script can restart them with a fresh context.

**Auto versioning**: PM tracks a `Shipped Since Last Bump` counter in `config.md`. Each time an item is marked `Shipped` (features) or `Closed` (bugs), the counter increments. When the counter reaches `Ship Threshold` (default 10) AND zero open bugs exist across all trackers, PM automatically bumps the minor version (e.g. `0.5.1` → `0.6.0`), updates `config.md` and `SKILL.md` frontmatter, adds a CHANGELOG section, creates a git tag, and pushes. Version bumps bypass PR flow.

### [Role] Lead Ralph Loop

Each dev agent follows this loop, substituting its own role name and tracker paths:

```
1. git pull --rebase
1b. Context pressure check — if above threshold, save state and exit
1c. Resume from working-state.md if active task exists
2. Scan [role]/bugs.md for Open or Investigating items
   → Write working state, fix bug, clear state on completion
   → If bug touches another agent's domain, file BUG-[OTHER]-XXX in [other]/bugs.md
   → Update bug status to Fixed, append Discussion entry
3. Scan [role]/features.md for Approved items
   → Write working state, implement feature, update state as sub-steps complete
   → Update status to In Progress, then Pending Test
   → Clear working state on completion, append Discussion entry
4. Run [role] test command (from config.md)
5. If quiet cycle (no bugs fixed, no features progressed): skip log/commit, go to sleep
6. Log iteration to [role]/iterations/iter-N.md
7. git add -A && git commit && git push
8. Sleep [INTERVAL] minutes (from config.md) → repeat
```

### PM/QA Ralph Loop

```
1. git pull --rebase
1b. Context pressure check — if above threshold, save state and exit
1c. Resume from working-state.md if active task exists
2. Non-blocking human check-in (print note, continue immediately)
   → If human has provided input: file bugs/features to appropriate tracker
   → Await human approval before marking features Approved
3. Run full e2e test command (from config.md)
4. Log results to pm/qa-log.md
5. If tests fail: file BUG-[ROLE]-XXX to the appropriate dev agent's tracker
6. Scan each dev agent's features.md for Pending Test items → verify → update to Shipped
6b. If PR Flow enabled: monitor open PRs, sync comments/merges/changes to trackers
7. Scan each dev agent's bugs.md for Fixed items → verify → update to Verified/Closed
7b. If GitHub Issues ingestion enabled: `gh issue list` → ingest new issues into trackers
8. Agent health check: git log per agent, flag stalled/idle agents (no commits in 2× interval)
9. If quiet cycle (no issues found, no verifications, no human input): skip log/commit, go to sleep
10. Log iteration to pm/iterations/iter-N.md
11. git add -A && git commit && git push
12. Sleep [INTERVAL] minutes (from config.md) → repeat
```

---

## Git Protocol

All agents follow these rules to minimize merge conflicts on shared tracker files:

- Always `git pull --rebase` before starting any work.
- Tracker files (bugs.md, features.md, qa-log.md) are **append-only**: never edit or delete existing entries — only append new entries or update the status field of your own items.
- Discussion sections are append-only: always add new lines at the bottom of the `### Discussion` block.
- Push after completing each work unit (bug fix, feature, test run).
- **Commit prefix convention**: every commit message must start with the agent's role name followed by a colon (e.g. `skill: fix bug`, `fe: add button`, `pm: verify features`). This prefix is used by the status line and PM health checks to detect agent activity via `git log --grep`.
- If a rebase conflict occurs: keep both versions of the conflicted tracker section by appending, never discard.

### PR-Based Approval Flow (optional)

When `PR Flow: yes` is set in `config.md`, dev agents create PRs instead of pushing directly to main:

- **Branching convention**: `squidsquad/feat-[role]-NNN` or `squidsquad/bug-[role]-NNN` (e.g. `squidsquad/feat-skill-008`)
- **Dev agent workflow**: when marking work as `Pending Test`, create a branch, push it, and open a PR via `gh pr create`. Record the PR link in the tracker Discussion.
- **PM/QA workflow**: each cycle, check open SquidSquad PRs via `gh pr list`. For each PR:
  - If merged: update the tracker item status to `Shipped`
  - If changes requested: update status back to `In Progress` and append the feedback to Discussion
  - If new comments: append them to the tracker Discussion
- **PM/QA still pushes to main** — only dev agent feature/bug work goes through PRs. PM tracker updates (bugs.md, features.md status changes, qa-log, iterations) continue to push directly to main.
- When `PR Flow: no` (default), agents push directly to main as before.

---

## Setup Instructions

When this skill is invoked, perform the following steps:

### Step 0 — Clean Worktree Check

Run:
```bash
git status --porcelain
```

If the output is non-empty, stop immediately and tell the user:

```
SquidSquad setup aborted: your working tree has uncommitted changes.

Please commit or stash your changes before initializing SquidSquad.
This ensures the .squidsquad/ setup commit is clean and isolated.

  git stash        (to stash changes temporarily)
  git commit -am   (to commit changes first)

Then re-run SquidSquad setup.
```

Do not proceed until `git status --porcelain` returns no output.

### Step 1 — Gather Project Details

**Quick-start mode:** If the user provides all details in a single sentence (e.g. "Set up SquidSquad for kubex, BE only, 5 min interval"), extract all values from it. Fill any missing fields with defaults and skip straight to validation. Only prompt for fields that cannot be inferred.

**Interactive mode:** If the user does not provide details upfront, prompt for each field using the structured format below. Present each prompt with its label, description, and default value so the user can accept defaults by pressing Enter or provide a custom value.

Collect these fields:

| # | Field | Description | Default | Validation |
|---|-------|-------------|---------|------------|
| 1 | **Project name** | Used in config.md and commit messages | Name of the current git repo directory | Must be non-empty |
| 2 | **Repository URL** | e.g. `github.com/alice/myapp` | Infer from `git remote get-url origin` if available | Must be non-empty |
| 3 | **Dev agents** | Comma-separated role names, e.g. `fe, be` / `be` / `api, worker` | `fe, be` | At least one role required; each name must be a simple lowercase identifier |
| 4 | **Framework / language** | One per dev agent, e.g. BE: FastAPI, FE: Next.js | _(none)_ | Optional per agent |
| 5 | **Test command** | One per dev agent, e.g. `cd backend && pytest tests/` | _(none)_ | Optional per agent |
| 6 | **E2E test command** | Full-stack test command run by PM/QA each cycle | _(none)_ | Optional — if none, PM skips the test step |
| 7 | **Loop interval** | Minutes between Ralph Loop cycles | `10` | Must be an integer >= 1; re-prompt if invalid |
| 8 | **Seed items** | Bugs or features to pre-populate into trackers | _(none)_ | Optional |
| 9 | **PR-based approval flow** | Create PRs instead of pushing to main? Requires `gh` CLI. | `N` (disabled) | `y`/`n` — if `y`, verify `gh auth status` succeeds |
| 10 | **GitHub Issues ingestion** | Auto-ingest GitHub Issues into trackers each PM cycle? Requires `gh` CLI. | `N` (disabled) | `y`/`n` — if `y`, verify `gh auth status` succeeds |

#### Import Existing Items

After collecting the fields above (and before the validation summary), offer to import existing bugs or features from an external source:

```
Do you have existing bugs or features to import?
  (1) Paste text — I'll parse and normalize it
  (2) File path  — point to a local file (markdown, CSV, plain text)
  (3) MCP source — pull from GitHub Issues, Jira, Linear, etc. (if connected)
  (4) Skip
```

**Handling each source:**

- **Pasted text / File path**: Parse each item, inferring title, severity/priority, description, and owner (which dev agent). Use heuristics — e.g. items mentioning "UI", "frontend", "CSS" route to `fe`; items mentioning "API", "database", "server" route to `be`. If the team shape has only one dev agent, route everything there. If ambiguous, default to the first dev agent and note it in the Discussion entry.
- **MCP source**: Check if relevant MCP tools are available in the session (e.g. `mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql`, GitHub Issues via `gh`, etc.). If available, prompt the user for a query or project filter, fetch items, and map each to the tracker format. If no MCP tools are available, inform the user and offer the other import options instead.

**Normalization rules:**

- Each imported item is assigned the next available `BUG-[ROLE]-XXX` or `FEAT-[ROLE]-XXX` ID based on the counters that will be set in `config.md`.
- Bugs get status `Open`, features get status `Pending`.
- Each imported entry gets an initial Discussion note:
  ```
  > [YYYY-MM-DD HH:MM] **pm/qa**: Imported from [source] at setup.
  ```
- Increment the corresponding ID counters in `config.md` for each imported item.
- Imported items are merged with any manually provided seed items from field 8.

**Validation:** After collecting all fields (including any imported items), display a summary table and ask the user to confirm or correct any values before proceeding. If any required field is empty or any value fails validation (e.g. interval < 1), highlight the issue and re-prompt for that specific field. If items were imported, include a count (e.g. "Imported: 3 bugs, 2 features → be/").

### Step 2 — Create `.squidsquad/` Folder Structure

Create the shared templates directory:
```
.squidsquad/templates/
```

For each dev agent role defined in Step 1, create:
```
.squidsquad/[role]/
    CLAUDE.md
    bugs.md
    features.md
    iterations/
```

Always create `.squidsquad/pm/` with its full structure regardless of team shape.

### Step 3 — Generate `config.md`

```markdown
# SquidSquad Config

- **SquidSquad Version**: 0.5.1
- **Tracker Schema**: 1

## Project

- **Name**: [PROJECT_NAME]
- **Repo**: [REPO_URL]

## Agents

- **Dev Agents**: [ROLE1], [ROLE2], ...  ← one entry per dev role defined at setup
- **PM/QA**: always present

## Test Commands

- **[ROLE1] Tests**: [ROLE1_TEST_CMD]
- **[ROLE2] Tests**: [ROLE2_TEST_CMD]  ← one entry per dev agent; omit if none
- **E2E Tests**: [E2E_TEST_CMD]  ← omit if none

## ID Counters

- **BUG-[ROLE1]**: 0
- **FEAT-[ROLE1]**: 0
- **BUG-[ROLE2]**: 0  ← one pair per dev agent
- **FEAT-[ROLE2]**: 0

## Git Protocol

- Always `git pull --rebase` before starting work.
- Tracker files are append-only.
- Discussion entries are append-only.
- Push after every completed work unit.

## Iteration Interval

- **Minutes**: [INTERVAL]  ← minimum 1, default 10

## Context Pressure

- **Threshold**: [THRESHOLD]  ← percentage (1-99), default 80

## PR Flow

- **Enabled**: [yes/no]  ← if yes, dev agents create PRs instead of pushing to main; requires `gh` CLI

## GitHub Issues Ingestion

- **Enabled**: [yes/no]  ← if yes, PM auto-ingests new GitHub Issues each cycle; requires `gh` CLI

## Auto Versioning

- **Ship Threshold**: 10  ← number of shipped items before auto version bump
- **Shipped Since Last Bump**: 0  ← PM increments when marking items Shipped/Closed
```

### Step 4 — Generate Templates and Bootstrapper CLAUDE.md Files

This step creates two things per agent: a **template** (full instructions with all placeholders substituted) and a **bootstrapper** (small CLAUDE.md that points to the template).

#### Step 4a — Generate Template Files

Read `references/agent-instructions.md`. For each dev agent role, copy Template 1 (Dev Agent) into `.squidsquad/templates/dev-agent-[role].md`, substituting all placeholders (`[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, `[INTERVAL]`) with values from config.md. For PM/QA, copy Template 2 into `.squidsquad/templates/pm-agent.md`, substituting `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`, and `[INTERVAL]`.

The resulting template files contain the complete Ralph Loop instructions with no remaining placeholders — agents never see `[ROLE]` syntax.

#### Step 4b — Generate Bootstrapper CLAUDE.md Files

For each dev agent role, generate a short bootstrapper at `.squidsquad/[role]/CLAUDE.md` (~20 lines):

```markdown
# SquidSquad — [ROLE] Lead

## Role Config

- **Role**: [role]
- **Role Upper**: [ROLE_UPPER]
- **Test Command**: [ROLE_TEST_CMD]
- **Other Roles**: [OTHER_ROLES]
- **Interval**: [INTERVAL] minutes
- **Template**: `.squidsquad/templates/dev-agent-[role].md`

## Instructions

You MUST read `.squidsquad/templates/dev-agent-[role].md` NOW for your complete Ralph Loop instructions. Follow them exactly — begin your first cycle immediately.

If the template file cannot be read, print: "ERROR: Template file `.squidsquad/templates/dev-agent-[role].md` not found. Run `/squidsquad-upgrade` to regenerate templates." and stop.
```

For PM/QA, generate `.squidsquad/pm/CLAUDE.md`:

```markdown
# SquidSquad — PM/QA

## Role Config

- **Role**: pm
- **Active Agents**: [ACTIVE_AGENTS]
- **E2E Test Command**: [E2E_TEST_CMD]
- **Interval**: [INTERVAL] minutes
- **Template**: `.squidsquad/templates/pm-agent.md`

## Instructions

You MUST read `.squidsquad/templates/pm-agent.md` NOW for your complete Ralph Loop instructions. Follow them exactly — begin your first cycle immediately.

If the template file cannot be read, print: "ERROR: Template file `.squidsquad/templates/pm-agent.md` not found. Run `/squidsquad-upgrade` to regenerate templates." and stop.
```

#### Step 4c — Root CLAUDE.md

Also create or update the **root `CLAUDE.md`** in the project root. If a root `CLAUDE.md` already exists, append the SquidSquad boot block below. If it does not exist, create it with only this content:

```markdown
# SquidSquad Auto-Boot

If the file `.squidsquad/.active-role` exists, you are running as a SquidSquad agent:

1. Read `.squidsquad/.active-role` to get your role name (e.g. `fe`, `be`, `skill`, `pm`).
2. Read `.squidsquad/<role>/CLAUDE.md` for your full instructions.
3. Follow those instructions exactly — begin your first Ralph Loop cycle immediately without waiting for user input.

If `.squidsquad/.active-role` does not exist, ignore this section — you are a normal Claude session.
```

Add `.squidsquad/.active-role` to `.gitignore` (create the file if it doesn't exist):

```
# SquidSquad runtime (not committed)
.squidsquad/.active-role
```

### Step 5 — Generate Boot Scripts

Generate both a `.sh` (bash) and a `.ps1` (PowerShell) boot script for each dev agent, plus PM/QA. Script names use the role name, e.g. `start-be.sh`, `start-api.sh`, `start-worker.ps1`.

All agents run interactively. The boot script writes `.squidsquad/.active-role` (git-ignored) with the role name, then launches `claude` with a positional arg message. The CLAUDE.md auto-boot section detects the role and starts the Ralph Loop. The human can observe progress and comment in any agent's terminal.

**`start-[role].sh`**:
```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

if [ -d .squidsquad ]; then
  V=$(grep -o '[0-9][0-9.]*[0-9]' .squidsquad/config.md 2>/dev/null | head -1)
  cat << LOGO

      ▗▄▖
     ▟█ █▙
    ▐█• •█▌
   ███████
   ▐█████▌
    ▐▌▐▌▐▌
  S Q U I D S Q U A D   v${V:-?}  —  [ROLE]

LOGO
fi

echo "[ROLE]" > .squidsquad/.active-role
claude --permission-mode auto "start the loop"
```

**`start-[role].ps1`**:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8
$v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

Write-Host ""
Write-Host "      ▗▄▖"
Write-Host "     ▟█ █▙"
Write-Host "    ▐█• •█▌"
Write-Host "   ███████"
Write-Host "   ▐█████▌"
Write-Host "    ▐▌▐▌▐▌"
Write-Host "  S Q U I D S Q U A D   v$v  -  [ROLE]"
Write-Host ""

"[ROLE]" | Set-Content .squidsquad/.active-role -NoNewline
claude --permission-mode auto "start the loop"
```

**`start-pm.sh`**:
```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

if [ -d .squidsquad ]; then
  V=$(grep -o '[0-9][0-9.]*[0-9]' .squidsquad/config.md 2>/dev/null | head -1)
  cat << LOGO

      ▗▄▖
     ▟█ █▙
    ▐█• •█▌
   ███████
   ▐█████▌
    ▐▌▐▌▐▌
  S Q U I D S Q U A D   v${V:-?}  —  PM / QA

LOGO
fi

echo "pm" > .squidsquad/.active-role
claude --permission-mode auto "start the loop"
```

**`start-pm.ps1`**:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

if (Test-Path .squidsquad) {
    $config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    $v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

    Write-Host ""
    Write-Host "    ▗▄▄▄▄▖"
    Write-Host "   ▟██████▙"
    Write-Host "    ▐▌▀ ▀▐▌"
    Write-Host "  ▜██████▛▘"
    Write-Host "   ▐██████"
    Write-Host "    ▌▌▌▌▌▌"
    Write-Host "  S Q U I D S Q U A D   v$v  -  PM / QA"
    Write-Host ""
}

"pm" | Set-Content .squidsquad/.active-role -NoNewline
claude --permission-mode auto "start the loop"
```

> **Note:** All agents use a positional arg to send the first message (kickstarting the Ralph Loop) in an interactive session. The user can observe progress and comment in any agent's terminal.

Make the `.sh` scripts executable (`chmod +x`).

### Step 5b — Generate Status Line Script

**Before generating**, check if the user already has a `statusLine` command configured in `.claude/settings.json`. If so, save the exact command string to `.squidsquad/.user-statusline` (one line, as-is, no path resolution). This allows the generated script to chain the user's existing status bar output above the SquidSquad line.

Generate `.squidsquad/statusline.sh` — a bash script that powers the Claude Code status bar for all SquidSquad agents. The script first chains the user's original status bar command (from `.user-statusline`, if it exists, with a 1-second timeout and silent fallback), then appends the SquidSquad status line(s).

**Emoji Rich design:**

- **🦑** — SquidSquad brand, always present
- **Role + version** — e.g. `PM/QA v0.5.1`, `skill v0.5.1`
- **📦 N/threshold** — ship counter (PM only), 🚀 appears when counter >= threshold - 1
- **📋 FEAT-XXX PN** — planning phase in progress (PM only, shown when a feature is in `Planning` status)
- **↑N / ↓N** — git sync status, only shown when out of sync with remote
- **🐛N ⭐N** — open bugs + actionable features (dev only, when no active task)
- **🔨 FEAT-XXX / BUG-XXX** — active task from working-state.md (dev only, replaces backlog)
- **✅ clear** — dev backlog empty, no active task
- **🧠** — context always shown; 🧠🔥 at 50-74% (yellow text); 🧠💀 at 75%+ (red text); green text < 50%
- **🔄 Nm** — next-cycle countdown; switches to **🔜 <1m** when under 1 minute
- **PM line 2** — team health icons (🦑 healthy, 👻 stalled, 🥚 never started) + rest nudge (🌙 late 10pm-12am, 😴 rest? 12am-2am, 🛏️ sleep! 2am-6am)

Output examples:
- Dev idle: `🦑 skill v0.5.1 │ 🐛3 ⭐2 │ 🧠 42% │ 🔄 4m`
- Dev working: `🦑 skill v0.5.1 │ 🔨 FEAT-017 │ 🧠 31% │ 🔄 3m`
- Dev clear: `🦑 be v0.5.1 │ ✅ clear │ 🧠 12% │ 🔄 5m`
- PM: `🦑 PM/QA v0.5.1 │ 📦 9/10 🚀 │ 📋 FEAT-017 P2 │ 🧠 42% │ 🔄 2m` + line 2: `  🦑🦑🦑`

```bash
#!/bin/bash
# SquidSquad Status Line — Emoji Rich design
# Receives JSON session data on stdin; prints status to stdout

INPUT=$(cat)

SQDIR=".squidsquad"
[ ! -d "$SQDIR" ] && exit 0

# Chain user's original status bar (if saved during setup)
USER_STATUSLINE="$SQDIR/.user-statusline"
if [ -f "$USER_STATUSLINE" ] && [ -s "$USER_STATUSLINE" ]; then
  USER_CMD=$(cat "$USER_STATUSLINE")
  USER_OUTPUT=$(echo "$INPUT" | timeout 1 bash -c "$USER_CMD" 2>/dev/null) || true
  [ -n "$USER_OUTPUT" ] && echo "$USER_OUTPUT"
fi

# Read role
ROLE_FILE="$SQDIR/.active-role"
[ ! -f "$ROLE_FILE" ] && exit 0
ROLE=$(cat "$ROLE_FILE" | tr -d '[:space:]')
[ -z "$ROLE" ] && exit 0

# ANSI colors
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
RESET='\033[0m'

# Read version from config
VERSION=$(grep 'SquidSquad Version' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+[.0-9]*')
VERSION=${VERSION:-'?'}

# Parse context window usage from JSON stdin
CTX_PCT=$(echo "$INPUT" | grep -oE '"used_percentage"[[:space:]]*:[[:space:]]*[0-9.]+' | head -1 | grep -oE '[0-9.]+$')
CTX_PCT=${CTX_PCT%%.*}
CTX_PCT=${CTX_PCT:-0}

# Context emoji + colored percentage text
if [ "$CTX_PCT" -ge 75 ]; then
  CTX_STR="🧠💀 ${RED}${CTX_PCT}%${RESET}"
elif [ "$CTX_PCT" -ge 50 ]; then
  CTX_STR="🧠🔥 ${YELLOW}${CTX_PCT}%${RESET}"
else
  CTX_STR="🧠 ${GREEN}${CTX_PCT}%${RESET}"
fi

# Get interval from config
INTERVAL=$(grep 'Minutes' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+')
INTERVAL=${INTERVAL:-10}

# Time since last iteration → countdown timer
ITER_DIR="$SQDIR/$ROLE/iterations"
LATEST=""
if [ -d "$ITER_DIR" ]; then
  LATEST=$(ls "$ITER_DIR"/iter-*.md 2>/dev/null | sort -t- -k2 -n | tail -1)
fi

TIMER_STR="🔄 ${INTERVAL}m"
NOW=$(date +%s)
if [ -n "$LATEST" ]; then
  if stat --version >/dev/null 2>&1; then
    LAST_MOD=$(stat -c %Y "$LATEST" 2>/dev/null)
  else
    LAST_MOD=$(stat -f %m "$LATEST" 2>/dev/null)
  fi
  if [ -n "$LAST_MOD" ]; then
    ELAPSED=$(( (NOW - LAST_MOD) / 60 ))
    REMAINING=$(( INTERVAL - ELAPSED ))
    if [ "$REMAINING" -le 0 ]; then
      TIMER_STR="🔜 <1m"
    elif [ "$REMAINING" -le 1 ]; then
      TIMER_STR="🔜 <1m"
    else
      TIMER_STR="🔄 ${REMAINING}m"
    fi
  fi
fi

# Git sync: ↑N unpushed / ↓N behind remote
GIT_SYNC=""
AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null)
BEHIND=$(git rev-list --count HEAD..@{u} 2>/dev/null)
[ -n "$AHEAD" ] && [ "$AHEAD" -gt 0 ] && GIT_SYNC="↑${AHEAD}"
if [ -n "$BEHIND" ] && [ "$BEHIND" -gt 0 ]; then
  [ -n "$GIT_SYNC" ] && GIT_SYNC="${GIT_SYNC} "
  GIT_SYNC="${GIT_SYNC}↓${BEHIND}"
fi

# Role label
if [ "$ROLE" = "pm" ]; then
  ROLE_LABEL="PM/QA"
else
  ROLE_LABEL="$ROLE"
fi

# === PM-specific segments ===
if [ "$ROLE" = "pm" ]; then
  # Ship counter: 📦 N/threshold, 🚀 if near bump
  SHIPPED=$(grep 'Shipped Since Last Bump' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+')
  SHIP_THRESHOLD=$(grep 'Ship Threshold' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+')
  SHIPPED=${SHIPPED:-0}
  SHIP_THRESHOLD=${SHIP_THRESHOLD:-10}
  SHIP_STR="📦 ${SHIPPED}/${SHIP_THRESHOLD}"
  NEAR_BUMP=$(( SHIP_THRESHOLD - 1 ))
  [ "$SHIPPED" -ge "$NEAR_BUMP" ] && SHIP_STR="${SHIP_STR} 🚀"

  # Planning phase: 📋 FEAT-XXX PN — check all dev agent features for Planning status
  PLANNING_STR=""
  AGENTS=$(grep 'Dev Agents' "$SQDIR/config.md" 2>/dev/null | sed 's/.*: //' | tr ',' ' ')
  for AGENT in $AGENTS; do
    AGENT=$(echo "$AGENT" | tr -d '[:space:]')
    [ -z "$AGENT" ] && continue
    FEATS_FILE="$SQDIR/$AGENT/features.md"
    if [ -f "$FEATS_FILE" ]; then
      PLANNING_FEAT=$(grep -B5 'Status\*\*: Planning' "$FEATS_FILE" 2>/dev/null | grep -oE 'FEAT-[A-Z]+-[0-9]+' | head -1)
      if [ -n "$PLANNING_FEAT" ]; then
        # Detect which phase by checking for existing artifacts
        PLAN_DIR="$SQDIR/$AGENT/planning"
        PHASE="P1"
        [ -f "$PLAN_DIR/${PLANNING_FEAT}-RESEARCH.md" ] && PHASE="P2"
        [ -f "$PLAN_DIR/${PLANNING_FEAT}-CONTEXT.md" ] && PHASE="P3"
        [ -f "$PLAN_DIR/${PLANNING_FEAT}-TEST-PLAN.md" ] && PHASE="P3✓"
        PLANNING_STR="📋 ${PLANNING_FEAT} ${PHASE}"
        break
      fi
    fi
  done

  # Build PM line 1
  LINE1="🦑 ${ROLE_LABEL} v${VERSION} │ ${SHIP_STR}"
  [ -n "$PLANNING_STR" ] && LINE1="${LINE1} │ ${PLANNING_STR}"
  [ -n "$GIT_SYNC" ] && LINE1="${LINE1} │ ${GIT_SYNC}"
  LINE1="${LINE1} │ ${CTX_STR} │ ${TIMER_STR}"

  # Agent health icons for line 2: 🦑 healthy, 👻 stalled, 🥚 never started
  HEALTH=""
  THRESHOLD_SECS=$(( INTERVAL * 2 * 60 ))
  for AGENT in $AGENTS; do
    AGENT=$(echo "$AGENT" | tr -d '[:space:]')
    [ -z "$AGENT" ] && continue
    RECENT=$(git log --oneline --since="${INTERVAL}2 minutes ago" --grep="^${AGENT}:" 2>/dev/null | head -1)
    if [ -n "$RECENT" ]; then
      HEALTH="${HEALTH}🦑"
    else
      EVER=$(git log --oneline --grep="^${AGENT}:" -1 2>/dev/null)
      if [ -n "$EVER" ]; then
        HEALTH="${HEALTH}👻"
      else
        HEALTH="${HEALTH}🥚"
      fi
    fi
  done

  # Rest nudge (right-aligned on line 2)
  HOUR=$(date +%H)
  REST=""
  if [ "$HOUR" -ge 22 ] || [ "$HOUR" -lt 0 ]; then
    REST="🌙 late"
  elif [ "$HOUR" -ge 0 ] && [ "$HOUR" -lt 2 ]; then
    REST="😴 rest?"
  elif [ "$HOUR" -ge 2 ] && [ "$HOUR" -lt 6 ]; then
    REST="🛏️ sleep!"
  fi
  # Handle 10pm-midnight (hour 22-23)
  if [ "$HOUR" -ge 22 ]; then
    REST="🌙 late"
  elif [ "$HOUR" -ge 0 ] && [ "$HOUR" -lt 2 ]; then
    REST="😴 rest?"
  elif [ "$HOUR" -ge 2 ] && [ "$HOUR" -lt 6 ]; then
    REST="🛏️ sleep!"
  fi

  LINE2="  ${HEALTH}"
  [ -n "$REST" ] && LINE2="${LINE2}                                    ${REST}"

  echo -e "${LINE1}"
  echo -e "${LINE2}"

# === Dev agent segments ===
else
  # Check working state for active task
  WS_FILE="$SQDIR/$ROLE/working-state.md"
  ACTIVE_TASK=""
  if [ -f "$WS_FILE" ]; then
    WS_STATUS=$(grep '^\- \*\*Status\*\*:' "$WS_FILE" 2>/dev/null | head -1)
    if echo "$WS_STATUS" | grep -q 'in-progress'; then
      ACTIVE_TASK=$(grep '^\- \*\*Task\*\*:' "$WS_FILE" 2>/dev/null | sed 's/.*: //' | tr -d '[:space:]')
    fi
  fi

  if [ -n "$ACTIVE_TASK" ] && [ "$ACTIVE_TASK" != "none" ]; then
    WORK_STR="🔨 ${ACTIVE_TASK}"
  else
    # Backlog counts
    BUGS_FILE="$SQDIR/$ROLE/bugs.md"
    FEATS_FILE="$SQDIR/$ROLE/features.md"
    BUG_COUNT=0
    FEAT_COUNT=0
    [ -f "$BUGS_FILE" ] && BUG_COUNT=$(grep -cE '^\- \*\*Status\*\*: (Open|Investigating)' "$BUGS_FILE" 2>/dev/null) || true
    [ -f "$FEATS_FILE" ] && FEAT_COUNT=$(grep -cE '^\- \*\*Status\*\*: (Approved|In Progress)' "$FEATS_FILE" 2>/dev/null) || true
    BUG_COUNT=${BUG_COUNT:-0}
    FEAT_COUNT=${FEAT_COUNT:-0}

    if [ "$BUG_COUNT" -eq 0 ] && [ "$FEAT_COUNT" -eq 0 ]; then
      WORK_STR="✅ clear"
    else
      WORK_STR=""
      [ "$BUG_COUNT" -gt 0 ] && WORK_STR="🐛${BUG_COUNT}"
      if [ "$FEAT_COUNT" -gt 0 ]; then
        [ -n "$WORK_STR" ] && WORK_STR="${WORK_STR} "
        WORK_STR="${WORK_STR}⭐${FEAT_COUNT}"
      fi
    fi
  fi

  LINE1="🦑 ${ROLE_LABEL} v${VERSION} │ ${WORK_STR}"
  [ -n "$GIT_SYNC" ] && LINE1="${LINE1} │ ${GIT_SYNC}"
  LINE1="${LINE1} │ ${CTX_STR} │ ${TIMER_STR}"

  echo -e "${LINE1}"
fi
```

Make the script executable (`chmod +x`).

### Step 6 — Seed Tracker Files

Initialize empty tracker files with headers:

**`[role]/bugs.md`** (one per dev agent):
```markdown
# Bug Tracker

_Bugs are filed in BUG-[TEAM]-XXX format. Each entry includes a Discussion section for cross-team communication._

---
```

**`[role]/features.md`** (one per dev agent):
```markdown
# Feature Tracker

_Features start as Pending (awaiting human approval) and move through Planning → Approved → In Progress → Pending Test → Shipped._

---
```

**`pm/qa-log.md`**:
```markdown
# QA Log

_Each PM/QA iteration logs a test run result here._

---
```

**`pm/enhancements.md`**:
```markdown
# Enhancement Proposals

_Product ideas and enhancement proposals surfaced during QA cycles or human check-ins._

---
```

If the user provided seed items (field 8) or imported items (from the import step), add them to the appropriate tracker files using the full bug or feature format:

- Bugs get status `Open`, features get status `Pending`.
- Each entry gets an initial Discussion note from `pm/qa`:
  - Seed items: `> [YYYY-MM-DD HH:MM] **pm/qa**: Seeded at setup.`
  - Imported items: `> [YYYY-MM-DD HH:MM] **pm/qa**: Imported from [source] at setup.`
- Route each item to the correct `[role]/bugs.md` or `[role]/features.md` based on the owner assigned during import/seeding.
- Update ID counters in `config.md` to reflect all seeded and imported items.

### Step 7 — Configure SessionStart Hook

Create or update `.claude/settings.json` in the project root to add a `SessionStart` hook that prints the SquidSquad logo whenever Claude Code boots in this repo.

**If `.claude/settings.json` does not exist**, create it:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash .squidsquad/statusline.sh"
  },
  "permissions": {
    "allow": [
      "Edit(.squidsquad/**)",
      "Write(.squidsquad/**)",
      "Bash(git pull*)",
      "Bash(git add*)",
      "Bash(git commit*)",
      "Bash(git push*)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'if [ -d .squidsquad ]; then V=$(grep -o [0-9][0-9.]*[0-9] .squidsquad/config.md 2>/dev/null | head -1); cat <<LOGO\n\n      ▗▄▖\n     ▟█ █▙\n    ▐█• •█▌\n   ███████\n   ▐█████▌\n    ▐▌▐▌▐▌\n  S Q U I D S Q U A D   v${V:-?}\n\nLOGO\nfi'"
          }
        ]
      }
    ]
  }
}
```

> **Why these permissions?** Dev agents run with `--permission-mode auto` but still need explicit allow rules for writing tracker files and running git commands without being prompted mid-cycle. Without these, the agent will pause and ask for permission on every file write.

**If `.claude/settings.json` already exists**, merge carefully:

1. **`SessionStart` hooks**: append the SquidSquad hook to the existing array. If the key doesn't exist, create it. Never remove existing hooks.
2. **`statusLine`**: if the user already has a `statusLine` configured, the existing command was already saved to `.squidsquad/.user-statusline` in Step 5b. Replace the `statusLine` with SquidSquad's version — it chains the user's original command automatically. No prompt needed.
   If no existing `statusLine` exists, add the SquidSquad one silently.
3. **`permissions.allow`**: append the SquidSquad entries without removing or duplicating existing entries. Check for each entry before adding.

### Step 8 — Commit and Push

Commit the entire `.squidsquad/` folder and push so the other agents can pull the setup the moment they boot:

```bash
git add .squidsquad/
git commit -m "squidsquad: initialize coordination folder"
git push
```

If the push fails, surface the error to the user and ask them to resolve it (e.g. `git push --set-upstream origin main`) before proceeding. Do not skip this step — agents that boot before the setup is pushed will be working from a stale state.

### Step 9 — Confirm Setup

Print a summary:
```
      ▗▄▖
     ▟█ █▙
    ▐█• •█▌
   ███████
   ▐█████▌
    ▐▌▐▌▐▌

╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   🦑  SQUIDSQUAD IS READY TO DEPLOY  🦑                    ║
║                                                            ║
║   Project  : [PROJECT_NAME]                                ║
║   Repo     : [REPO_URL]                                    ║
║   Pushed   : ✓ .squidsquad/ committed to origin           ║
║                                                            ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║   [N] agents. One repo. Zero meetings.                     ║
║                                                            ║
║   Open [N] terminals and launch your squad:                ║
║                                                            ║
║   bash / zsh:                                              ║
║   [one line per dev agent]  bash .squidsquad/start-[role].sh ║
║   Terminal N →  bash .squidsquad/start-pm.sh  ← interactive ║
║                                                            ║
║   PowerShell:                                              ║
║   [one line per dev agent]  .\.squidsquad\start-[role].ps1  ║
║   Terminal N →  .\.squidsquad\start-pm.ps1   ← interactive ║
║                                                            ║
║   PM/QA is interactive — it will check in with you.        ║
║   Dev agents run autonomously in the background.           ║
║   Loop interval: [INTERVAL] minutes                        ║
║                                                            ║
║   The squad takes it from here.                            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

## Upgrade Instructions

When the user invokes upgrade (via `/squidsquad-upgrade` or "upgrade squidsquad"), use the following agent-based parallel approach.

### Step 1 — Detect Version Gap (orchestrator)

Read `.squidsquad/config.md` to get installed `SquidSquad Version` and `Tracker Schema`.
Read `SKILL.md` frontmatter and Schema Changelog for current versions.

If both match: tell the user they're up to date and stop.

Also read the `Agents` section of `config.md` to get the list of active dev role names.

### Step 2 — Fan Out Agents in Parallel

Spawn all applicable agents simultaneously. Each agent writes only its assigned files and does not commit.

#### If skill version differs — spawn these agents in parallel:

**One agent per active dev role:**
> Regenerate `.squidsquad/templates/dev-agent-[role].md` from the Dev Agent template in `references/agent-instructions.md`, substituting `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, and `[INTERVAL]` with values from `config.md`. Also regenerate `.squidsquad/start-[role].sh` and `.squidsquad/start-[role].ps1`. **Migration**: if `.squidsquad/[role]/CLAUDE.md` contains `## The Ralph Loop` (inline format, >50 lines), replace it with the bootstrapper format (see Step 4b in Setup Instructions). If it is already a bootstrapper (<50 lines, no `## The Ralph Loop`), leave it untouched. Do not touch `bugs.md`, `features.md`, or `iterations/`.

**One agent for PM/QA:**
> Regenerate `.squidsquad/templates/pm-agent.md` from the PM/QA template in `references/agent-instructions.md`, substituting `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`, and `[INTERVAL]` from `config.md`. Also regenerate `.squidsquad/start-pm.sh` and `.squidsquad/start-pm.ps1`. **Migration**: if `.squidsquad/pm/CLAUDE.md` contains `## The Ralph Loop` (inline format), replace it with the bootstrapper format (see Step 4b in Setup Instructions). If already a bootstrapper, leave it untouched. Do not touch `qa-log.md`, `enhancements.md`, `iterations/`, or `migrations/`.

> **Note:** Create `.squidsquad/templates/` if it does not exist (first upgrade from pre-template architecture).

**One agent for settings:**
> Update `.claude/settings.json`: ensure `permissions.allow` contains `Edit(.squidsquad/**)`, `Write(.squidsquad/**)`, and the four git commands. Ensure the `SessionStart` hook is present and matches the current template. Ensure the `statusLine` key is present and points to `bash .squidsquad/statusline.sh`. Regenerate `.squidsquad/statusline.sh` from the current template. Merge into existing content — never remove unrelated keys.

#### If tracker schema differs — additionally spawn:

**One agent per affected tracker file:**
> Apply the schema migration documented in the Schema Changelog for the detected version gap. Read all existing entries, rewrite the file with updated structure, append a `> [DATE] **migration**: schema N→M applied.` Discussion note to each modified entry, and write a log to `pm/migrations/schema-N-to-M.md`.

### Step 3 — Update config.md (orchestrator)

After all agents complete, update `.squidsquad/config.md`:
- Set `SquidSquad Version` to current skill version
- Set `Tracker Schema` to current schema version

### Step 4 — Commit and Push

```bash
git add .squidsquad/ .claude/
git commit -m "squidsquad: upgrade to [VERSION]"
git push
```

### Step 5 — Report

Tell the user: version upgraded from → to, files regenerated per agent, any schema migrations applied, any failures.

---

## Schema Changelog

### Schema 1 (current — introduced in v0.5.0)

**Bug fields**: ID, Title, Severity, Status, Reported By, Assigned To, Description, Steps to Reproduce, Expected, Actual, Discussion

**Feature fields**: ID, Title, Priority, Status, Owner, Description, Acceptance Criteria, Discussion

**Bug status values**: `Open` → `Investigating` → `Fixed` → `Verified` → `Closed`

**Feature status values**: `Pending` → `Planning` → `Approved` → `In Progress` → `Pending Test` → `Shipped`

Future schema changes will be documented here with their migration instructions before being released.

---

## `/squidsquad-status` — Squad Overview Command

When the user says `/squidsquad-status` (or "squad status", "show me the squad", etc.), generate a quick dashboard of the entire SquidSquad team. This works from any Claude session in the repo — not just the PM agent.

**Instructions:**

1. Read `.squidsquad/config.md` to get the list of dev agents and the loop interval.
2. For each agent (dev agents + PM):
   - Check health via `git log --oneline --since="[2×interval] minutes ago" --grep="^[agent]:"` — if commits found, show as `active`; if prior commits exist but none recent, show as `stalled`; else `unknown`.
   - Show last commit time: `git log --oneline --grep="^[agent]:" -1 --format="%ar"`
3. For each dev agent, read their `bugs.md` and `features.md`:
   - Count and list open bugs (status `Open` or `Investigating`)
   - Count and list in-progress/approved features
4. List the last 5 shipped features across all agents (status `Shipped`), most recent first.
5. Format as a clean dashboard:

```
🦑 SquidSquad Status — [project name]
══════════════════════════════════════

Agent        Health     Last Commit
─────        ──────     ───────────
skill        active     2 minutes ago
pm           active     3 minutes ago

Backlog
───────
skill: 2 open bugs (BUG-SKILL-005, BUG-SKILL-006), 1 approved feat (FEAT-SKILL-007)

Recently Shipped
────────────────
1. FEAT-SKILL-006 — Git-log based agent health detection
2. FEAT-SKILL-005 — Show timestamp at iteration start and stop
3. ...
```
