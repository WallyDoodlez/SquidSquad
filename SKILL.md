---
name: squidsquad
description: "Orchestrates a multi-agent AI development team — handles setup, workflow coordination, role management, and autonomous dev cycles."
version: 0.8.0
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
│              │   ├── bugs/          ← INDEX.md + individual BUG-XXX.md files + archived/
│              │   ├── features/      ← INDEX.md + individual FEAT-XXX.md files + archived/
│              │   └── iterations/                         │
│              └── pm/                                     │
│                  ├── CLAUDE.md                            │
│                  ├── qa-log.md                            │
│                  ├── enhancements.md                      │
│                  └── iterations/                          │
└──────────────────────────────────────────────────────────┘
```

### Roles

SquidSquad always has a **PM** agent. When dev or designer agents are present, a **QA** agent is automatically added to independently verify their work. Dev agents are flexible — you define them at setup time. You can also add a **Designer** agent for projects that need design-to-code workflows.

| Agent | Owns | Loop |
|-------|------|------|
| **[role] Lead** (one per dev role) | Code for that role, `[role]/bugs/`, `[role]/features/` | Ralph Loop (fix bugs → implement features → test → push) |
| **Designer** (optional) | Design specs, tokens, component specs, `designer/` | Ralph Loop (review design requests → interactive design sessions → produce specs → hand off to dev) |
| **QA** (auto-added with dev/designer) | Test results, `qa/qa-log.md`, bug verification, feature testing | Ralph Loop (E2E tests → verify bugs → test features → health checks → push) |
| **PM** | Product backlog, `pm/enhancements.md`, human interaction, feature intake | Ralph Loop (check human → feature intake → backlog management → push) |

**Common team shapes:**

| Shape | Dev agents | Use when |
|-------|-----------|----------|
| `fe, be` | FE Lead + BE Lead + QA + PM | Full-stack app with separate frontend and backend |
| `fe, be, designer` | FE Lead + BE Lead + Designer + QA + PM | Full-stack with design-to-code workflow |
| `be` | BE Lead + QA + PM | API-only, CLI tool, library, or skill repo |
| `api, worker` | API Lead + Worker Lead + QA + PM | Backend split across services |
| `web, ios, api` | Web + iOS + API + QA + PM | Multi-platform product |
| _(any names)_ | Whatever you define + QA + PM | Custom team topology |

---

## File Structure Generated

When you invoke SquidSquad, it creates the following inside your project root. One folder is generated per dev agent — the example below shows a `be`-only setup:

```
.squidsquad/
├── config.md                   ← project config, test commands, counters, git protocol
├── templates/                  ← shared agent instruction templates (build-time substituted)
│   ├── dev-agent-be.md         ← full Ralph Loop instructions for BE Lead
│   ├── pm-agent.md             ← full Ralph Loop instructions for PM
│   ├── qa-agent.md             ← full Ralph Loop instructions for QA
│   └── dm-agent.md             ← full Ralph Loop instructions for Delivery Manager
├── start-be.sh / start-be.ps1  ← boot script: launches BE Lead (autonomous)
├── start-pm.sh / start-pm.ps1  ← boot script: launches PM (interactive)
├── start-qa.sh / start-qa.ps1  ← boot script: launches QA (autonomous)
├── start-dm.sh / start-dm.ps1  ← boot script: launches Delivery Manager (autonomous)
├── be/                         ← one folder per dev agent, named after the role
│   ├── CLAUDE.md               ← bootstrapper (~20 lines): role config + Read instruction to template
│   ├── bugs/                   ← INDEX.md + individual BUG-BE-XXX.md files + archived/
│   ├── features/               ← INDEX.md + individual FEAT-BE-XXX.md files + archived/
│   └── iterations/             ← iter-N.md logs per cycle
├── dm/                         ← Delivery Manager (optional — created when user opts in)
│   ├── CLAUDE.md               ← bootstrapper: role config + Read instruction to template
│   ├── working-state.md        ← crash recovery state
│   └── iterations/             ← iter-N.md logs per cycle
├── pm/                         ← Product Manager (human-facing coordinator)
│   ├── CLAUDE.md               ← bootstrapper (~20 lines): role config + Read instruction to template
│   ├── enhancements.md         ← product backlog / enhancement proposals
│   ├── iterations/             ← iter-N.md logs per cycle
│   └── migrations/             ← migration logs written when tracker schema changes
└── qa/                         ← QA (auto-added when dev/designer present)
    ├── CLAUDE.md               ← bootstrapper: role config + Read instruction to template
    ├── qa-log.md               ← QA test run results
    ├── working-state.md        ← crash recovery state
    └── iterations/             ← iter-N.md logs per cycle
```

> **Note:** DM and QA use shared dev agent trackers (no `dm/features/`, `dm/bugs/`, `qa/features/`, or `qa/bugs/`). QA reads `Pending Test` and `Fixed` items from dev agent trackers, verifies them, and writes Discussion entries directly there. DM reads `Pending Ship` items and handles delivery.

For `fe, be` the structure gains a `fe/` folder and `start-fe.sh/.ps1` alongside `be/`.

---

## Tracker Formats

### Bug Format (`bugs/BUG-XXX.md`)

Each bug is stored as its own file (e.g. `bugs/BUG-FE-001.md`). The `bugs/INDEX.md` file is auto-generated and lists all non-archived bugs.

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

### Feature Format (`features/FEAT-XXX.md`)

Each feature is stored as its own file (e.g. `features/FEAT-FE-001.md`). The `features/INDEX.md` file is auto-generated and lists all non-archived features.

```markdown
## FEAT-FE-001 — [Title]

- **Priority**: Critical | High | Medium | Low
- **Status**: Pending | Planning | Approved | In Progress | Pending Test | Pending Ship | Shipped
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
> [2026-01-15 13:00] **pm/qa**: Tested and passing. Status → Pending Ship.
> [2026-01-15 14:00] **dm**: Delivery complete. Docs updated, CHANGELOG prepared. Status → Shipped.
```

Status flow: `Pending` → `Planning` → `Approved` → `In Progress` → `Pending Test` → `Pending Ship` → `Shipped` (or `Rejected`)

> **Note:** `Pending` means awaiting human approval. `Planning` means human approved and PM is running the Feature Intake Process (Research → Discussion → Planning). `Approved` means planning is complete and a dev agent can pick it up. `Pending Ship` means PM verified and DM will handle delivery (docs, CHANGELOG, version bump). `Rejected` means PM recommends against it — human can override.

### Feature Lifecycle (5-Phase)

Features go through a deep, research-driven lifecycle before reaching the dev agent:

1. **Research (PM)** — Spawn research agent: codebase impact, side effects, edge cases, integration risks → `FEAT-XXX-RESEARCH.md`
2. **Discussion (PM + Human)** — Present findings, ask targeted questions with WHY, capture locked decisions vs dev discretion → `FEAT-XXX-CONTEXT.md`
3. **Planning (PM)** — Write feature entry + test cases → `FEAT-XXX-TEST-PLAN.md`
4. **Execution (Dev)** — Implement reading planning artifacts, run smoke tests before Pending Test
5. **QA (PM)** — Execute test cases from TEST-PLAN.md, record pass/fail, only ship when all pass

Planning files live in `.squidsquad/[role]/planning/` and are auto-deleted after ship (git preserves them). Bugs are excluded — they use the current lightweight flow. Trivial/cosmetic features can use light mode (PM skips research).

### INDEX.md Regeneration

`INDEX.md` is auto-generated and must never be hand-edited. It is regenerated after any status change, filing, archival, or deletion of a tracker item.

**Format:**

```markdown
<!-- Generated: YYYY-MM-DD HH:MM -->
# Bug Tracker Index

| ID | Status | Severity | Title |
|----|--------|----------|-------|
| [BUG-ROLE-001](BUG-ROLE-001.md) | Open | High | Some bug title |
| [BUG-ROLE-002](BUG-ROLE-002.md) | Investigating | Critical | Another bug |
```

For features, the third column is `Priority` instead of `Severity`.

**Rules:**
- Only lists non-archived items (items in `archived/` are excluded)
- Sorted by ID in ascending order
- The `<!-- Generated: YYYY-MM-DD HH:MM -->` comment is always the first line
- Agents regenerate INDEX.md by scanning all `.md` files in the directory (excluding `INDEX.md` and `archived/`), extracting ID, Status, Severity/Priority, and Title from each file's frontmatter fields

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
2. Read [role]/bugs/INDEX.md, then read individual files for Open or Investigating items (match `**Status**: Open` — tracker uses markdown bold)
   → Write working state, fix bug, clear state on completion
   → If bug touches another agent's domain, create [other]/bugs/BUG-[OTHER]-XXX.md and regenerate INDEX.md
   → Update bug status to Fixed, append Discussion entry, regenerate INDEX.md
3. Read [role]/features/INDEX.md, then read individual files for Approved items
   → Write working state, implement feature, update state as sub-steps complete
   → Update status to In Progress, then Pending Test
   → Clear working state on completion, append Discussion entry
4. Run [role] test command (from config.md)
5. If quiet cycle (no bugs fixed, no features progressed):
   → If Improvement Scanning enabled and quiet cycle counter ≥ 3: scan target project for domain-specific improvements, file findings through PM (max 2 per scan)
   → Otherwise: skip log/commit, go to sleep
6. Log iteration to [role]/iterations/iter-N.md
7. git add -A && git commit && git push
8. Sleep [INTERVAL] minutes (from config.md) → repeat
```

### PM Ralph Loop

```
1. git pull --rebase
1b. Context pressure check — if above threshold, save state and exit
1c. Resume from working-state.md if active task exists
2. Non-blocking human check-in (print note, continue immediately)
   → If human has provided input: file bugs to tracker; for features, discuss first (predict intent, surface questions, invite refinement), then file and run Feature Intake Process
   → Await human approval before marking features Approved (approval only offered after planning completes)
3. Backlog management — priority changes, feature status updates
3b. If GitHub Issues ingestion enabled: `gh issue list` → ingest new issues into trackers
4. If quiet cycle (no human input, no intake work): skip log/commit, go to sleep
5. Log iteration to pm/iterations/iter-N.md
6. git add -A && git commit && git push
7. Sleep [INTERVAL] minutes (from config.md) → repeat
```

### QA Ralph Loop

```
1. git pull --rebase
1b. Context pressure check — if above threshold, save state and exit
1c. Resume from working-state.md if active task exists
2. Run full e2e test command (from config.md)
3. Log results to qa/qa-log.md
4. If tests fail: file BUG-[ROLE]-XXX to the appropriate dev agent's tracker
5. Read each dev agent's features/INDEX.md for Pending Test items → read individual files → verify → update to Pending Ship (DM handles delivery → Shipped)
5b. If PR Flow enabled: monitor open PRs, sync comments/merges/changes to trackers
6. Read each dev agent's bugs/INDEX.md for Fixed items → read individual files → verify → update to Verified/Closed
7. Agent health check: git log per agent, flag stalled/idle agents (no commits in 2× interval)
8. If quiet cycle (no issues found, no verifications): skip log/commit, go to sleep
9. Log iteration to qa/iterations/iter-N.md
10. git add -A && git commit && git push
11. Sleep [INTERVAL] minutes (from config.md) → repeat
```

---

## Git Protocol

All agents follow these rules to minimize merge conflicts on shared tracker files:

- Always `git pull --rebase` before starting any work.
- Tracker files (individual bug/feature `.md` files, qa-log.md) are **append-only**: never edit or delete existing entries — only append new entries or update the status field of your own items. Closed/terminal-status items are moved to `archived/` subdirectories. INDEX.md files are auto-generated and never hand-edited.
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
- **PM/QA still pushes to main** — only dev agent feature/bug work goes through PRs. PM tracker updates (individual bug/feature file status changes, INDEX.md regeneration, qa-log, iterations) continue to push directly to main.
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
    bugs/
        archived/
    features/
        archived/
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

## Improvement Scanning

- **Enabled**: [yes/no]  ← if yes, agents scan the target project for improvements during quiet cycles (default yes)

## Auto Versioning

- **Ship Threshold**: 10  ← number of shipped items before auto version bump
- **Shipped Since Last Bump**: 0  ← PM increments when marking items Shipped/Closed
```

### Step 4 — Generate Templates and Bootstrapper CLAUDE.md Files

This step creates two things per agent: a **template** (full instructions with all placeholders substituted) and a **bootstrapper** (small CLAUDE.md that points to the template).

#### Step 4a — Generate Template Files

Read `references/agent-instructions.md`. For each dev agent role, copy Template 1 (Dev Agent) into `.squidsquad/templates/dev-agent-[role].md`, substituting all placeholders (`[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, `[INTERVAL]`) with values from config.md. For PM, copy Template 2 (PM) or Template 2L (PM Lean) into `.squidsquad/templates/pm-agent.md` — use PM Lean when a QA agent is present, full PM otherwise. Substitute `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`, and `[INTERVAL]`. When dev or designer agents are present, generate QA from Template 5 (QA) into `.squidsquad/templates/qa-agent.md`, substituting `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`, and `[INTERVAL]`. For DM, copy Template 3 into `.squidsquad/templates/dm-agent.md`, substituting `[ACTIVE_AGENTS]`, `[INTERVAL]`, and `[ROLE_UPPER]` placeholders. If a `designer` role is defined, copy Template 4 (Designer) into `.squidsquad/templates/designer-agent.md`, substituting `[ACTIVE_AGENTS]` and `[INTERVAL]` placeholders.

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

For DM (Delivery Manager), generate `.squidsquad/dm/CLAUDE.md`:

```markdown
# SquidSquad — Delivery Manager (DM)

You are the Delivery Manager on the SquidSquad autonomous dev team. You own the "last mile" of shipping — when a feature reaches `Pending Ship` status, you take over to create a delivery package of all user-facing materials before marking the feature `Shipped`.

Read `.squidsquad/templates/dm-agent.md` for your full instructions. Follow the Ralph Loop defined there.
```

Also create `.squidsquad/dm/working-state.md` (empty working state) and `.squidsquad/dm/iterations/` directory.

#### Step 4c — Root CLAUDE.md

Also create or update the **root `CLAUDE.md`** in the project root. If a root `CLAUDE.md` already exists, append the SquidSquad boot block below. If it does not exist, create it with only this content:

```markdown
# SquidSquad Auto-Boot

If your system prompt contains a line matching `SQUIDSQUAD_ROLE=<role>` (e.g. `SQUIDSQUAD_ROLE=skill`, `SQUIDSQUAD_ROLE=pm`), you are running as a SquidSquad agent:

1. Extract the role name from the `SQUIDSQUAD_ROLE=` line.
2. Read `.squidsquad/<role>/CLAUDE.md` for your full instructions.
3. Follow those instructions exactly — begin your first Ralph Loop cycle immediately without waiting for user input.

If no `SQUIDSQUAD_ROLE=` line is present, ignore this section — you are a normal Claude session. The presence of `.squidsquad/` in the repo does NOT mean you should auto-boot.
```

Add runtime files to `.gitignore` (create the file if it doesn't exist):

```
# SquidSquad runtime (not committed)
.squidsquad/.active-role
.squidsquad/*/current-state
.squidsquad/.local-config
```

### Step 5 — Generate Boot Scripts

Generate both a `.sh` (bash) and a `.ps1` (PowerShell) boot script for each dev agent, plus PM/QA. Script names use the role name, e.g. `start-be.sh`, `start-api.sh`, `start-worker.ps1`.

All agents run interactively. The boot script passes the role via `--append-system-prompt "SQUIDSQUAD_ROLE=[ROLE]"` — a session-only signal that never leaks across terminals. The CLAUDE.md auto-boot section detects this in the system prompt and starts the Ralph Loop. The human can observe progress and comment in any agent's terminal.

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

# Inject permissions from template into settings.json
bash .squidsquad/inject-permissions.sh 2>/dev/null || true

# Write role for statusline (not used for auto-boot — system prompt handles that)
echo "[ROLE]" > .squidsquad/.active-role

# Clear and initialize status bar state
rm -f .squidsquad/[ROLE]/current-state
echo "idle|Initializing..." > .squidsquad/[ROLE]/current-state

claude --dangerously-skip-permissions --append-system-prompt "SQUIDSQUAD_ROLE=[ROLE]" "start the loop"
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

# Inject permissions from template into settings.json
& (Join-Path $repoRoot ".squidsquad/inject-permissions.ps1")

# Write role for statusline (not used for auto-boot -- system prompt handles that)
"[ROLE]" | Set-Content .squidsquad/.active-role -NoNewline

# Clear and initialize status bar state
Remove-Item .squidsquad/[ROLE]/current-state -ErrorAction SilentlyContinue
"idle|Initializing..." | Set-Content .squidsquad/[ROLE]/current-state -NoNewline

claude --dangerously-skip-permissions --append-system-prompt "SQUIDSQUAD_ROLE=[ROLE]" "start the loop"
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

# Inject permissions from template into settings.json
bash .squidsquad/inject-permissions.sh 2>/dev/null || true

# Write role for statusline (not used for auto-boot — system prompt handles that)
echo "pm" > .squidsquad/.active-role

# Clear and initialize status bar state
rm -f .squidsquad/pm/current-state
echo "idle|Initializing..." > .squidsquad/pm/current-state

claude --dangerously-skip-permissions --append-system-prompt "SQUIDSQUAD_ROLE=pm" "start the loop"
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
    Write-Host "      ▗▄▖"
    Write-Host "     ▟█ █▙"
    Write-Host "    ▐█• •█▌"
    Write-Host "   ███████"
    Write-Host "   ▐█████▌"
    Write-Host "    ▐▌▐▌▐▌"
    Write-Host "  S Q U I D S Q U A D   v$v  -  PM / QA"
    Write-Host ""
}

# Inject permissions from template into settings.json
& (Join-Path $repoRoot ".squidsquad/inject-permissions.ps1")

# Write role for statusline (not used for auto-boot -- system prompt handles that)
"pm" | Set-Content .squidsquad/.active-role -NoNewline

# Clear and initialize status bar state
Remove-Item .squidsquad/pm/current-state -ErrorAction SilentlyContinue
"idle|Initializing..." | Set-Content .squidsquad/pm/current-state -NoNewline

claude --dangerously-skip-permissions --append-system-prompt "SQUIDSQUAD_ROLE=pm" "start the loop"
```

> **Note:** All agents use a positional arg to send the first message (kickstarting the Ralph Loop) in an interactive session. The user can observe progress and comment in any agent's terminal.

**`start-dm.sh`** (DM uses the same pattern as dev agents — it's autonomous):
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
  S Q U I D S Q U A D   v${V:-?}  —  DM

LOGO
fi

# Inject permissions from template into settings.json
bash .squidsquad/inject-permissions.sh 2>/dev/null || true

# Write role for statusline
echo "dm" > .squidsquad/.active-role

# Clear and initialize status bar state
rm -f .squidsquad/dm/current-state
echo "idle|Initializing..." > .squidsquad/dm/current-state

claude --dangerously-skip-permissions --append-system-prompt "SQUIDSQUAD_ROLE=dm" "start the loop"
```

**`start-dm.ps1`**:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

if (Test-Path .squidsquad) {
    $config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    $v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

    Write-Host ""
    Write-Host "      ▗▄▖"
    Write-Host "     ▟█ █▙"
    Write-Host "    ▐█• •█▌"
    Write-Host "   ███████"
    Write-Host "   ▐█████▌"
    Write-Host "    ▐▌▐▌▐▌"
    Write-Host "  S Q U I D S Q U A D   v$v  -  DM"
    Write-Host ""
}

# Inject permissions from template into settings.json
& (Join-Path $repoRoot ".squidsquad/inject-permissions.ps1")

# Write role for statusline
"dm" | Set-Content .squidsquad/.active-role -NoNewline

# Clear and initialize status bar state
Remove-Item .squidsquad/dm/current-state -ErrorAction SilentlyContinue
"idle|Initializing..." | Set-Content .squidsquad/dm/current-state -NoNewline

claude --dangerously-skip-permissions --append-system-prompt "SQUIDSQUAD_ROLE=dm" "start the loop"
```

Make the `.sh` scripts executable (`chmod +x`).

> **BOM-safe writes on Windows**: PowerShell 5.x `Set-Content -Encoding UTF8` adds a UTF-8 BOM, which breaks JSON parsers (node, jq, Claude). When writing files consumed by other tools (JSON, config files), use `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))` instead. The `inject-permissions.ps1` script already follows this pattern.

### Step 5b — Generate Status Line Script

**Before generating**, check if the user already has a `statusLine` command configured in `.claude/settings.json`. If so, save the exact command string to `.squidsquad/.user-statusline` (one line, as-is, no path resolution). This allows the generated script to chain the user's existing status bar output above the SquidSquad line.

Copy `references/statusline.sh` to `.squidsquad/statusline.sh`. This is the canonical source — the same externalization pattern used for agent templates in `references/agent-instructions.md`.

The script implements the **Emoji Rich** status bar design:

- **🦑** — SquidSquad brand, always present
- **Role + version** — e.g. `PM/QA v0.5.1`, `skill v0.5.1`
- **📦 N/threshold** — ship counter (PM only), 🚀 appears when counter >= threshold - 1
- **📋 FEAT-XXX PN** — planning phase in progress (PM only, shown when a feature is in `Planning` status)
- **↑N / ↓N** — git sync status, only shown when out of sync with remote
- **🐛N ⭐N** — open bugs + actionable features (dev only, when no active task)
- **🔨 FEAT-XXX / BUG-XXX** — active task from working-state.md (dev only, replaces backlog)
- **✅ clear** — dev backlog empty, no active task
- **🧠** — context always shown; 🧠🔥 at 50-74% (yellow text); 🧠💀 at 75%+ (red text); green text < 50%
- **🔄 Nm** — next-cycle countdown; switches to **🔜 <1m** when under 1 minute; switches to **⏰ +Nm** when overdue (agent's cycle exceeded the iteration interval — triggers immediately at boundary, no grace period)
- **Line 1 health icons** — (PM only, right-aligned) 🦑 healthy, 👻 stalled, ❓ unknown/no data + rest nudge emoji
- **Line 2** — current step (emoji + description from `current-state` file, truncated at 60 chars) OR rotating contextual hints when idle (from hint pool files, rotates every 60s, phase-aware)

Output examples:
- Dev idle: `🦑 skill v0.5.1 │ 🐛3 ⭐2 │ 🧠 42% │ 🔄 4m` + line 2: `  Msg me any time to file a bug or request a feature`
- Dev working: `🦑 skill v0.5.1 │ 🔨 FEAT-017 │ 🧠 31% │ 🔄 3m` + line 2: `  🔨 FEAT-SKILL-017...`
- Dev clear: `🦑 be v0.5.1 │ ✅ clear │ 🧠 12% │ 🔄 5m` + line 2: `  All clear — ready for the next task`
- PM: `🦑 PM/QA v0.5.1 │ 📦 9/10 🚀 │ 📋 FEAT-017 P2 │ 🧠 42% │ 🔄 2m │ 🦑🦑🦑` + line 2: `  Running tests to check system health...`

Make the copied script executable (`chmod +x`).

### Step 5c — Copy Hint Pool Files

Copy `references/hints-dev.txt` to `.squidsquad/hints-dev.txt` and `references/hints-pm.txt` to `.squidsquad/hints-pm.txt`. These files contain phase-aware hint pools that the status bar rotates through when agents are idle or between steps. The format is `phase|hint text` — one hint per line, comments start with `#`.

### Step 5d — Guided Agent Clone Setup + .local-config

Each agent runs in its own clone of the repository. This step guides the user through cloning and configuring paths so agents can detect each other's health via cross-clone file reads.

Create `.squidsquad/.local-config` (gitignored, machine-specific) with the following format:

```markdown
# Agent clone paths (machine-specific, gitignored)
# Each agent reads other agents' current-state files via these absolute paths.

## Agent Paths
- **pm**: [ABSOLUTE_PATH_TO_PM_CLONE]
- **[role]**: [ABSOLUTE_PATH_TO_ROLE_CLONE]
```

For each agent (dev agents + PM/QA):

1. **Ask for clone path**: Suggest a default sibling directory (e.g., `../SquidSquad-[role]` relative to the current repo). The user can accept the default or provide a custom absolute path.
2. **Clone the repo**: `git clone <repo-url> <path>`. Skip if the directory already exists (user may have cloned manually).
3. **Write the path to `.local-config`**: Append `- **[role]**: [absolute-path]` to the Agent Paths section.
4. **Offer to open a terminal**: Ask if the user wants to launch the agent now. If yes:
   - **Windows (PowerShell)**: `Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '[path]'; .\.squidsquad\start-[role].ps1"`
   - **macOS/Linux (bash)**: `open -a Terminal '[path]'` or `gnome-terminal -- bash -c 'cd [path] && bash .squidsquad/start-[role].sh'`
   - If the terminal command fails, print the path and boot command for the user to run manually.

The user goes from "I want a skill agent" to "skill agent is running" in one flow. PM is typically the last agent launched (since the user interacts with PM directly).

### Step 6 — Seed Tracker Files

Initialize tracker directories with INDEX.md files:

**`[role]/bugs/INDEX.md`** (one per dev agent):
```markdown
<!-- Generated: YYYY-MM-DD HH:MM -->
# Bug Tracker Index

_Bugs are filed as individual BUG-[TEAM]-XXX.md files. This index is auto-generated._

| ID | Status | Severity | Title |
|----|--------|----------|-------|
```

**`[role]/features/INDEX.md`** (one per dev agent):
```markdown
<!-- Generated: YYYY-MM-DD HH:MM -->
# Feature Tracker Index

_Features are filed as individual FEAT-[TEAM]-XXX.md files. This index is auto-generated._

| ID | Status | Priority | Title |
|----|--------|----------|-------|
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

If the user provided seed items (field 8) or imported items (from the import step), create individual files in the appropriate tracker directories using the full bug or feature format:

- Bugs get status `Open`, features get status `Pending`.
- Each entry gets an initial Discussion note from `pm/qa`:
  - Seed items: `> [YYYY-MM-DD HH:MM] **pm/qa**: Seeded at setup.`
  - Imported items: `> [YYYY-MM-DD HH:MM] **pm/qa**: Imported from [source] at setup.`
- Create each item as an individual file (e.g. `[role]/bugs/BUG-[ROLE]-001.md` or `[role]/features/FEAT-[ROLE]-001.md`) based on the owner assigned during import/seeding.
- Regenerate `INDEX.md` for each affected directory after all items are created.
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

> **Why these permissions?** Dev agents run with `--enable-auto-mode` but still need explicit allow rules for writing tracker files and running git commands without being prompted mid-cycle. Without these, the agent will pause and ask for permission on every file write.

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
║   Terminal N →  bash .squidsquad/start-dm.sh  ← delivery    ║
║   Terminal N →  bash .squidsquad/start-pm.sh  ← interactive ║
║                                                            ║
║   PowerShell:                                              ║
║   [one line per dev agent]  .\.squidsquad\start-[role].ps1  ║
║   Terminal N →  .\.squidsquad\start-dm.ps1   ← delivery    ║
║   Terminal N →  .\.squidsquad\start-pm.ps1   ← interactive ║
║                                                            ║
║   PM/QA is interactive — it will check in with you.        ║
║   DM handles delivery (docs, CHANGELOG, version bumps).    ║
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
> Regenerate `.squidsquad/templates/dev-agent-[role].md` from the Dev Agent template in `references/agent-instructions.md`, substituting `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, and `[INTERVAL]` with values from `config.md`. Also regenerate `.squidsquad/start-[role].sh` and `.squidsquad/start-[role].ps1`. **Migration**: if `.squidsquad/[role]/CLAUDE.md` contains `## The Ralph Loop` (inline format, >50 lines), replace it with the bootstrapper format (see Step 4b in Setup Instructions). If it is already a bootstrapper (<50 lines, no `## The Ralph Loop`), leave it untouched. Do not touch `bugs/`, `features/`, or `iterations/`.

**One agent for PM/QA:**
> Regenerate `.squidsquad/templates/pm-agent.md` from the PM/QA template in `references/agent-instructions.md`, substituting `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`, and `[INTERVAL]` from `config.md`. Also regenerate `.squidsquad/start-pm.sh` and `.squidsquad/start-pm.ps1`. **Migration**: if `.squidsquad/pm/CLAUDE.md` contains `## The Ralph Loop` (inline format), replace it with the bootstrapper format (see Step 4b in Setup Instructions). If already a bootstrapper, leave it untouched. Do not touch `qa-log.md`, `enhancements.md`, `iterations/`, or `migrations/`.

**One agent for DM (Delivery Manager) — optional:**
> DM is optional. The `dm/` directory is the sole presence indicator — if it exists, DM is enabled; if not, PM handles delivery via Step 6d fallback. **Only create/update DM artifacts if `.squidsquad/dm/` already exists** (user previously opted in). If `dm/` exists: regenerate `.squidsquad/templates/dm-agent.md` from Template 3 in `references/agent-instructions.md`, substituting `[ACTIVE_AGENTS]`, `[INTERVAL]`, and `[ROLE_UPPER]`. Regenerate `.squidsquad/start-dm.sh` and `.squidsquad/start-dm.ps1`. If `dm/` does NOT exist: skip DM setup entirely. Do not create the directory, do not add DM to config.

> **Note:** Create `.squidsquad/templates/` if it does not exist (first upgrade from pre-template architecture).

**One agent for settings:**
> Update `.claude/settings.json`: ensure `permissions.allow` contains `Edit(.squidsquad/**)`, `Write(.squidsquad/**)`, and the four git commands. Ensure the `SessionStart` hook is present and matches the current template. Ensure the `statusLine` key is present and points to `bash .squidsquad/statusline.sh`. Regenerate `.squidsquad/statusline.sh` by copying `references/statusline.sh`. Remove `.squidsquad/heartbeat.sh` if it exists (heartbeat system replaced by cross-clone file reads). Copy `references/hints-dev.txt` to `.squidsquad/hints-dev.txt`, `references/hints-pm.txt` to `.squidsquad/hints-pm.txt`, and `references/hints-dm.txt` to `.squidsquad/hints-dm.txt`. Merge into existing content — never remove unrelated keys.

#### If tracker schema differs — additionally spawn:

**One agent per affected tracker directory:**
> Apply the schema migration documented in the Schema Changelog for the detected version gap. For file-splitting migrations (e.g. Schema 2→3), read all existing entries from monolithic files, create individual files, generate INDEX.md, move terminal-status items to `archived/`, and delete the original monolithic files. Append a `> [DATE] **migration**: schema N→M applied.` Discussion note to each modified entry, and write a log to `pm/migrations/schema-N-to-M.md`.

### Step 3 — Update config.md (orchestrator)

After all agents complete, update `.squidsquad/config.md`:
- Set `SquidSquad Version` to current skill version
- Set `Tracker Schema` to current schema version
- If `## Heartbeat` section exists, remove it (heartbeat system replaced by cross-clone file reads in v0.8.0+).

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

### Schema 3 (current — introduced in v0.9.0): Individual Tracker Files

Replaced monolithic `bugs.md` and `features.md` files with individual files in `bugs/` and `features/` directories. Each bug/feature is its own `.md` file. An auto-generated `INDEX.md` provides a summary table. Terminal-status items are moved to `archived/` subdirectories.

**Migration from Schema 2:**
- For each dev agent role: split monolithic `bugs.md` and `features.md` into individual files
- Terminal-status items (`Closed` bugs, `Shipped`/`Rejected` features) go to `archived/` subdirectory
- Generate `INDEX.md` for each directory
- Delete original monolithic files
- Regenerate agent `CLAUDE.md` files from updated templates
- Update `statusline.sh`
- Bump `Tracker Schema` to `3` in `config.md`

### Schema 2 (introduced in v0.8.0)

Added `Pending Ship` status to the feature lifecycle. After PM/QA verifies a feature (`Pending Test`), it transitions to `Pending Ship` where the Delivery Manager (DM) handles user-facing delivery (docs, CHANGELOG, version bump, git tag). DM then marks it `Shipped`.

**Migration from Schema 1**: No data migration needed. Existing `Shipped` items remain `Shipped`. Existing `Pending Test` items flow through `Pending Ship` naturally. PM's version bump logic (Step 6c) moves to DM. PM fallback: if no `dm/` directory exists, PM treats `Pending Ship` as `Shipped` (old behavior).

**Feature status values**: `Pending` → `Planning` → `Approved` → `In Progress` → `Pending Test` → `Pending Ship` → `Shipped`

### Schema 1 (introduced in v0.5.0)

**Bug fields**: ID, Title, Severity, Status, Reported By, Assigned To, Description, Steps to Reproduce, Expected, Actual, Discussion

**Feature fields**: ID, Title, Priority, Status, Owner, Description, Acceptance Criteria, Discussion

**Bug status values**: `Open` → `Investigating` → `Fixed` → `Verified` → `Closed`

**Feature status values**: `Pending` → `Planning` → `Approved` → `In Progress` → `Pending Test` → `Shipped`

---

## `/squidsquad-status` — Squad Overview Command

When the user says `/squidsquad-status` (or "squad status", "show me the squad", etc.), generate a quick dashboard of the entire SquidSquad team. This works from any Claude session in the repo — not just the PM agent.

**Instructions:**

1. Read `.squidsquad/config.md` to get the list of dev agents and the loop interval.
2. For each agent (dev agents + PM):
   - Check health via `git log --oneline --since="[2×interval] minutes ago" --grep="^[agent]:"` — if commits found, show as `active`; if prior commits exist but none recent, show as `stalled`; else `unknown`.
   - Show last commit time: `git log --oneline --grep="^[agent]:" -1 --format="%ar"`
3. For each dev agent, read their `bugs/INDEX.md` and `features/INDEX.md`:
   - Count and list open bugs (status `Open` or `Investigating`)
   - Count and list in-progress/approved features
4. List the last 5 shipped features across all agents (read individual feature files for `Shipped` status), most recent first.
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

## `/squidsquad-interval` — Change Loop Interval On The Fly

When the user says `/squidsquad-interval <Nm>` (e.g. `/squidsquad-interval 10m`), change the Ralph Loop interval for all agents without restarting.

**Instructions:**

1. **Parse input**: Extract the number and validate:
   - Must be an integer followed by `m` (e.g. `5m`, `10m`, `15m`). The `m` suffix is optional — bare integers are accepted (e.g. `10` is treated as `10m`).
   - Must be >= 5 (minimum enforced to prevent git conflicts between concurrent agents).
   - If invalid or missing, print usage: `/squidsquad-interval <Nm>` (e.g. `/squidsquad-interval 10m`). Minimum 5 minutes.
2. **Read current interval** from `.squidsquad/config.md` under `Iteration Interval > Minutes`.
3. **Update config.md**: Replace the `Minutes` value with the new interval.
4. **Reschedule current agent's cron**:
   - Call `CronDelete` with the existing cron job ID.
   - Call `CronCreate` with `*/N * * * *` (or appropriate cron expression for larger intervals), the same prompt (`execute one Ralph Loop cycle`), and `recurring: true`.
5. **Print confirmation**: `Interval changed from [old]m to [new]m. All agents will pick up the change on their next cycle.`

Other agents detect the change automatically: each agent re-reads `config.md` at the start of every cycle (Step 1d — Interval Sync) and re-schedules its cron if the interval has changed.
