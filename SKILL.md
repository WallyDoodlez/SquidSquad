---
name: squidsquad
description: "Your AI dev team that coordinates through markdown, not meetings."
version: 0.5.1
---

# SquidSquad

You are activating the SquidSquad multi-agent development coordination system. SquidSquad spins up three Claude Code CLI instances — a Frontend Lead, a Backend Lead, and a PM/QA — that work autonomously on a shared codebase by coordinating through markdown files in a `.squidsquad/` folder.

No meetings. No message queues. Just markdown.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Git Repository                    │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   FE Lead    │  │   BE Lead    │  │  PM / QA  │ │
│  │ (Claude CLI) │  │ (Claude CLI) │  │(Claude CLI│ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                 │                │       │
│         └────────┬────────┘                │       │
│                  ▼                         │       │
│           .squidsquad/                     │       │
│           ├── config.md  ◄─────────────────┘       │
│           ├── fe/                                   │
│           │   ├── CLAUDE.md                         │
│           │   ├── bugs.md                           │
│           │   ├── features.md                       │
│           │   └── iterations/                       │
│           ├── be/                                   │
│           │   ├── CLAUDE.md                         │
│           │   ├── bugs.md                           │
│           │   ├── features.md                       │
│           │   └── iterations/                       │
│           └── pm/                                   │
│               ├── CLAUDE.md                         │
│               ├── qa-log.md                         │
│               ├── enhancements.md                   │
│               └── iterations/                       │
└─────────────────────────────────────────────────────┘
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
├── start-be.sh / start-be.ps1  ← boot script: launches BE Lead (autonomous)
├── start-pm.sh / start-pm.ps1  ← boot script: launches PM/QA (interactive)
├── be/                         ← one folder per dev agent, named after the role
│   ├── CLAUDE.md               ← BE Lead role instructions + Ralph Loop
│   ├── bugs.md                 ← BUG-BE-XXX tracker with Discussion sections
│   ├── features.md             ← FEAT-BE-XXX tracker with Discussion sections
│   └── iterations/             ← iter-N.md logs per cycle
└── pm/
    ├── CLAUDE.md               ← PM/QA role instructions + Ralph Loop
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
- **Status**: Pending | Approved | In Progress | Pending Test | Shipped
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

Status flow: `Pending` → `Approved` → `In Progress` → `Pending Test` → `Shipped`

> **Note:** `Pending` means it needs human approval via a PM discussion entry before any agent picks it up. `Approved` means it is ready to be implemented.

---

## The Ralph Loop

Each agent runs its own Ralph Loop — an autonomous work cycle that repeats on an interval.

### FE Lead Ralph Loop

```
1. git pull --rebase
2. Scan fe/bugs.md for Open or Investigating items
   → Fix each bug in code
   → If bug touches BE, open BUG-BE-XXX in be/bugs.md
   → Update bug status to Fixed, append Discussion entry
3. Scan fe/features.md for Approved items
   → Implement next feature
   → Update status to In Progress, then Pending Test
   → Append Discussion entry
4. Run FE test command (from config.md)
5. Log iteration to fe/iterations/iter-N.md
6. git add -A && git commit && git push
7. Sleep [INTERVAL] minutes (from config.md) → repeat
```

### BE Lead Ralph Loop

```
1. git pull --rebase
2. Scan be/bugs.md for Open or Investigating items
   → Fix each bug in code
   → Update bug status to Fixed, append Discussion entry
3. Scan be/features.md for Approved items
   → Implement next feature
   → Update status to In Progress, then Pending Test
   → Append Discussion entry
4. Run BE test command (from config.md)
5. Log iteration to be/iterations/iter-N.md
6. git add -A && git commit && git push
7. Sleep [INTERVAL] minutes (from config.md) → repeat
```

### PM/QA Ralph Loop

```
1. git pull --rebase
2. Check with human: any new requirements, bugs, or priorities?
   → If yes: file new bugs to fe/bugs.md or be/bugs.md directly
   → If yes: add features to fe/features.md or be/features.md as Pending
   → Await human approval before marking features Approved
3. Run full e2e test command (from config.md)
4. Log results to pm/qa-log.md
5. If tests fail: file BUG-FE-XXX or BUG-BE-XXX as appropriate
6. Scan fe/ and be/ features.md for Pending Test items → verify → update to Shipped
7. Scan fe/ and be/ bugs.md for Fixed items → verify → update to Verified/Closed
8. Log iteration to pm/iterations/iter-N.md
9. git add -A && git commit && git push
10. Sleep [INTERVAL] minutes (from config.md) → repeat
```

---

## Git Protocol

All agents follow these rules to minimize merge conflicts on shared tracker files:

- Always `git pull --rebase` before starting any work.
- Tracker files (bugs.md, features.md, qa-log.md) are **append-only**: never edit or delete existing entries — only append new entries or update the status field of your own items.
- Discussion sections are append-only: always add new lines at the bottom of the `### Discussion` block.
- Push after completing each work unit (bug fix, feature, test run).
- If a rebase conflict occurs: keep both versions of the conflicted tracker section by appending, never discard.

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

Ask the user (or read from context) for:

1. **Project name** — used in config.md and commit messages
2. **Repository URL** — e.g. `github.com/alice/myapp`
3. **Dev agents** — comma-separated role names, e.g. `fe, be` / `be` / `api, worker`. Default: `fe, be`. Each role gets its own folder, tracker files, CLAUDE.md, and boot scripts.
4. **Framework / language for each dev agent** — e.g. BE: FastAPI, FE: Next.js
5. **Test command for each dev agent** — e.g. `cd backend && pytest tests/`
6. **E2E / full-stack test command** — run by PM/QA each cycle. Optional — if none, PM skips the test step.
7. **Loop interval** — how many minutes between Ralph Loop cycles. Default: 10. Minimum: 1.
8. **Any seed items** — bugs or features to pre-populate into the trackers

### Step 2 — Create `.squidsquad/` Folder Structure

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
```

### Step 4 — Generate CLAUDE.md Files

Use the templates in `references/agent-instructions.md` to generate role-specific CLAUDE.md files inside `fe/`, `be/`, and `pm/`, substituting in the project's actual test commands and repo URL from config.md.

### Step 5 — Generate Boot Scripts

Generate both a `.sh` (bash) and a `.ps1` (PowerShell) boot script for each dev agent, plus PM/QA. Script names use the role name, e.g. `start-be.sh`, `start-api.sh`, `start-worker.ps1`.

The shell owns the loop — each `claude -p` invocation handles one Ralph Loop cycle. Substitute `[ROLE]` with the actual role name and `[INTERVAL]` from `config.md`.

**`start-[role].sh`**:
```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

if [ -d .squidsquad ]; then
  V=$(grep -o '[0-9][0-9.]*[0-9]' .squidsquad/config.md 2>/dev/null | head -1)
  cat << LOGO

    ▗▄▄▄▄▖
   ▟██████▙
    ▐▌▀ ▀▐▌
  ▜██████▛▘
   ▐██████
    ▌▌▌▌▌▌
  S Q U I D S Q U A D   v${V:-?}  —  [ROLE]

LOGO
fi

claude --dangerously-skip-permissions --append-system-prompt-file .squidsquad/[ROLE]/CLAUDE.md -p "Begin your first Ralph Loop cycle now."
```

**`start-[role].ps1`**:
```powershell
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$config = Get-Content .squidsquad/config.md -Raw
$v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

Write-Host ""
Write-Host "    ▗▄▄▄▄▖"
Write-Host "   ▟██████▙"
Write-Host "    ▐▌▀ ▀▐▌"
Write-Host "  ▜██████▛▘"
Write-Host "   ▐██████"
Write-Host "    ▌▌▌▌▌▌"
Write-Host "  S Q U I D S Q U A D   v$v  -  [ROLE]"
Write-Host ""

claude --dangerously-skip-permissions --append-system-prompt-file .squidsquad/[ROLE]/CLAUDE.md -p "Begin your first Ralph Loop cycle now."
```

**`start-pm.sh`**:
```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

if [ -d .squidsquad ]; then
  V=$(grep -o '[0-9][0-9.]*[0-9]' .squidsquad/config.md 2>/dev/null | head -1)
  cat << LOGO

    ▗▄▄▄▄▖
   ▟██████▙
    ▐▌▀ ▀▐▌
  ▜██████▛▘
   ▐██████
    ▌▌▌▌▌▌
  S Q U I D S Q U A D   v${V:-?}  —  PM / QA

LOGO
fi

claude --permission-mode auto --append-system-prompt-file .squidsquad/pm/CLAUDE.md
```

**`start-pm.ps1`**:
```powershell
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

if (Test-Path .squidsquad) {
    $config = Get-Content .squidsquad/config.md -Raw -ErrorAction SilentlyContinue
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

claude --permission-mode auto --append-system-prompt-file .squidsquad/pm/CLAUDE.md
```

> **Note:** All agents run interactively. PM/QA uses `--permission-mode auto` so it can check in with you. Dev agents use `--dangerously-skip-permissions` to run fully autonomous. Both load their instructions via `--system-prompt-file`.

Make the `.sh` scripts executable (`chmod +x`).

### Step 6 — Seed Tracker Files

Initialize empty tracker files with headers:

**`fe/bugs.md`** and **`be/bugs.md`**:
```markdown
# Bug Tracker

_Bugs are filed in BUG-[TEAM]-XXX format. Each entry includes a Discussion section for cross-team communication._

---
```

**`fe/features.md`** and **`be/features.md`**:
```markdown
# Feature Tracker

_Features start as Pending (awaiting human approval) and move through Approved → In Progress → Pending Test → Shipped._

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

If the user provided seed items, add them to the appropriate tracker files using the full bug or feature format, with `Open` / `Pending` status and an initial Discussion entry from `pm/qa` noting when it was seeded.

### Step 7 — Configure SessionStart Hook

Create or update `.claude/settings.json` in the project root to add a `SessionStart` hook that prints the SquidSquad logo whenever Claude Code boots in this repo.

**If `.claude/settings.json` does not exist**, create it:

```json
{
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
            "command": "bash -c 'if [ -d .squidsquad ]; then V=$(grep -o [0-9][0-9.]*[0-9] .squidsquad/config.md 2>/dev/null | head -1); cat <<LOGO\n\n    ▗▄▄▄▄▖\n   ▟██████▙\n    ▐▌▀ ▀▐▌\n  ▜██████▛▘\n   ▐██████\n    ▌▌▌▌▌▌\n  S Q U I D S Q U A D   v${V:-?}\n\nLOGO\nfi'"
          }
        ]
      }
    ]
  }
}
```

> **Why these permissions?** Dev agents run with `--permission-mode auto` but still need explicit allow rules for writing tracker files and running git commands without being prompted mid-cycle. Without these, the agent will pause and ask for permission on every file write.

**If `.claude/settings.json` already exists**, merge the SquidSquad hook into the existing `SessionStart` array (or create the `SessionStart` key if absent). Do not overwrite any existing hooks — append the new entry.

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
    ▗▄▄▄▄▖
   ▟██████▙
    ▐▌▀ ▀▐▌
  ▜██████▛▘
   ▐██████
    ▌▌▌▌▌▌

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
║   Three agents. One repo. Zero meetings.                   ║
║                                                            ║
║   Open 3 terminals and launch your squad:                  ║
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
> Regenerate `.squidsquad/[role]/CLAUDE.md`, `.squidsquad/start-[role].sh`, and `.squidsquad/start-[role].ps1` using the Dev Agent template from `references/agent-instructions.md`. Substitute `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, and `[INTERVAL]` with values from `config.md`. Do not touch `bugs.md`, `features.md`, or `iterations/`.

**One agent for PM/QA:**
> Regenerate `.squidsquad/pm/CLAUDE.md`, `.squidsquad/start-pm.sh`, and `.squidsquad/start-pm.ps1` using the PM/QA template from `references/agent-instructions.md`. Substitute `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`, and `[INTERVAL]` from `config.md`. Do not touch `qa-log.md`, `enhancements.md`, `iterations/`, or `migrations/`.

**One agent for settings:**
> Update `.claude/settings.json`: ensure `permissions.allow` contains `Edit(.squidsquad/**)`, `Write(.squidsquad/**)`, and the four git commands. Ensure the `SessionStart` hook is present and matches the current template. Merge into existing content — never remove unrelated keys.

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

**Feature status values**: `Pending` → `Approved` → `In Progress` → `Pending Test` → `Shipped`

Future schema changes will be documented here with their migration instructions before being released.
