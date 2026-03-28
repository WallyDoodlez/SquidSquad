---
name: squidsquad
description: "Your AI dev team that coordinates through markdown, not meetings."
version: 0.5.0
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

| Agent | Owns | Loop |
|-------|------|------|
| **FE Lead** | Frontend code, `fe/bugs.md`, `fe/features.md` | Ralph Loop (fix bugs → implement features → test → push) |
| **BE Lead** | Backend code, `be/bugs.md`, `be/features.md` | Ralph Loop (fix bugs → implement features → test → push) |
| **PM/QA** | Product backlog, `pm/qa-log.md`, `pm/enhancements.md`, human interaction | Ralph Loop (check human → run e2e → log → file bugs → verify → push) |

---

## File Structure Generated

When you invoke SquidSquad, it creates the following inside your project root:

```
.squidsquad/
├── config.md                  ← project config, test commands, counters, git protocol
├── start-fe.sh / start-fe.ps1 ← boot script: launches FE Lead via `claude -p`
├── start-be.sh / start-be.ps1 ← boot script: launches BE Lead via `claude -p`
├── start-pm.sh / start-pm.ps1 ← boot script: launches PM/QA via `claude -p`
├── fe/
│   ├── CLAUDE.md              ← FE Lead role instructions + Ralph Loop
│   ├── bugs.md                ← BUG-FE-XXX tracker with Discussion sections
│   ├── features.md            ← FEAT-FE-XXX tracker with Discussion sections
│   └── iterations/            ← iter-N.md logs per cycle
├── be/
│   ├── CLAUDE.md              ← BE Lead role instructions + Ralph Loop
│   ├── bugs.md                ← BUG-BE-XXX tracker
│   ├── features.md            ← FEAT-BE-XXX tracker
│   └── iterations/            ← iter-N.md logs per cycle
└── pm/
    ├── CLAUDE.md              ← PM/QA role instructions + Ralph Loop
    ├── qa-log.md              ← QA test run results
    ├── enhancements.md        ← product backlog / enhancement proposals
    ├── iterations/            ← iter-N.md logs per cycle
    └── migrations/            ← migration logs written when tracker schema changes
```

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
7. Sleep 10 minutes → repeat
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
7. Sleep 10 minutes → repeat
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
10. Sleep 10 minutes → repeat
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
3. **Frontend framework** — e.g. Next.js, React, Vue
4. **Backend framework** — e.g. FastAPI, Express, Rails, Rust/Axum
5. **FE test command** — e.g. `cd frontend && npx playwright test`
6. **BE test command** — e.g. `cd backend && pytest tests/`
7. **E2E / full-stack test command** — e.g. `cd e2e && npx playwright test`
8. **Any seed items** — bugs or features to pre-populate into the trackers

### Step 2 — Create `.squidsquad/` Folder Structure

Create the full directory tree as specified above.

### Step 3 — Generate `config.md`

```markdown
# SquidSquad Config

- **SquidSquad Version**: 0.5.0
- **Tracker Schema**: 1

## Project

- **Name**: [PROJECT_NAME]
- **Repo**: [REPO_URL]

## Test Commands

- **FE Tests**: [FE_TEST_CMD]
- **BE Tests**: [BE_TEST_CMD]
- **E2E Tests**: [E2E_TEST_CMD]

## ID Counters

- **BUG-FE**: 0
- **BUG-BE**: 0
- **FEAT-FE**: 0
- **FEAT-BE**: 0

## Git Protocol

- Always `git pull --rebase` before starting work.
- Tracker files are append-only.
- Discussion entries are append-only.
- Push after every completed work unit.

## Iteration Interval

- Default: 10 minutes between loop cycles.
```

### Step 4 — Generate CLAUDE.md Files

Use the templates in `references/agent-instructions.md` to generate role-specific CLAUDE.md files inside `fe/`, `be/`, and `pm/`, substituting in the project's actual test commands and repo URL from config.md.

### Step 5 — Generate Boot Scripts

Generate both a `.sh` (bash) and a `.ps1` (PowerShell) version of each boot script so the squad can be launched on any platform.

**`start-fe.sh`**:
```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
claude --permission-mode auto --enable-auto-mode -p "$(cat .squidsquad/fe/CLAUDE.md)"
```

**`start-fe.ps1`**:
```powershell
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot
$prompt = Get-Content .squidsquad/fe/CLAUDE.md -Raw
claude --permission-mode auto --enable-auto-mode -p $prompt
```

**`start-be.sh`**:
```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
claude --permission-mode auto --enable-auto-mode -p "$(cat .squidsquad/be/CLAUDE.md)"
```

**`start-be.ps1`**:
```powershell
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot
$prompt = Get-Content .squidsquad/be/CLAUDE.md -Raw
claude --permission-mode auto --enable-auto-mode -p $prompt
```

**`start-pm.sh`**:
```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
claude --permission-mode auto
```

**`start-pm.ps1`**:
```powershell
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot
claude --permission-mode auto
```

> **Note:** PM/QA runs in interactive mode (no `-p`) so it can check in with you each cycle. `-p` is non-interactive print mode and would prevent any back-and-forth. The `.squidsquad/pm/CLAUDE.md` role instructions are loaded automatically by Claude Code. `--permission-mode auto` is kept so tracker file operations don't prompt.

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
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'if [ -d .squidsquad ]; then V=$(grep -o [0-9][0-9.]*[0-9] .squidsquad/config.md 2>/dev/null | head -1); cat <<LOGO\n\n      ▗▄▄▄▄▖\n     ▟██████▙\n      ▐▌▀  ▀▐▌\n    ▝▜████▛▘\n      ▐████▌\n     ▗██████▖\n    ▐███    ███▌\n   ▐██▘      ▝██▌\n  ▐▛▘          ▝▜▌\n  ▌▖            ▗▌\n  ▝▘            ▝▘\n\n  S Q U I D S Q U A D   v${V:-?}\n\nLOGO\nfi'"
          }
        ]
      }
    ]
  }
}
```

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
      ▐▌▀  ▀▐▌
     ▝▜████▛▘
     ▗██████▖
    ▐███    ███▌
   ▐██      ▝██▌
  ▐▛▘         ▜▌
  ▌▖           ▗▌
  ▝▘          ▝▘

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
║   Terminal 1 →  bash .squidsquad/start-fe.sh               ║
║   Terminal 2 →  bash .squidsquad/start-be.sh               ║
║   Terminal 3 →  bash .squidsquad/start-pm.sh  ← interactive ║
║                                                            ║
║   PowerShell:                                              ║
║   Terminal 1 →  .\.squidsquad\start-fe.ps1                 ║
║   Terminal 2 →  .\.squidsquad\start-be.ps1                 ║
║   Terminal 3 →  .\.squidsquad\start-pm.ps1   ← interactive ║
║                                                            ║
║   PM/QA is interactive — it will check in with you.        ║
║   FE + BE run autonomously in the background.              ║
║                                                            ║
║   The squad takes it from here.                            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

## Upgrade Instructions

When the user says "upgrade squidsquad" (or similar), perform the following:

### Step 1 — Read Installed Versions

Read `.squidsquad/config.md` and extract:
- `SquidSquad Version` — the skill version that last ran setup or upgrade
- `Tracker Schema` — the schema version of the tracker files

Compare both against the current skill version (`0.5.0`) and current schema version (`1`).

If both match, tell the user their installation is already up to date and stop.

### Step 2 — Skill Upgrade (if SquidSquad Version differs)

Regenerate all scaffolding files unconditionally. These contain no user data:

- `.squidsquad/start-fe.sh` and `start-fe.ps1`
- `.squidsquad/start-be.sh` and `start-be.ps1`
- `.squidsquad/start-pm.sh` and `start-pm.ps1`
- `.squidsquad/fe/CLAUDE.md`
- `.squidsquad/be/CLAUDE.md`
- `.squidsquad/pm/CLAUDE.md`
- `.claude/settings.json` (merge only — never overwrite unrelated hooks)

Do **not** touch:
- Any `bugs.md`, `features.md`, `qa-log.md`, `enhancements.md`, or `iterations/` files
- The project values in `config.md` (Name, Repo, Test Commands, ID Counters)

Update `SquidSquad Version` in `config.md` to the current skill version.

### Step 3 — Schema Migration (if Tracker Schema differs)

Schema migrations are the only time tracker files may be rewritten. Each migration is documented below under its version number. If no migration exists for the detected gap, skip this step.

For each migration applied:

1. Read all existing entries from the affected tracker file.
2. Rewrite the file with the updated structure.
3. Append a `> [DATE] **migration**: schema N→M applied. [What changed.]` note to the `### Discussion` section of any modified entries.
4. Write a log to `pm/migrations/schema-N-to-M.md`:

```markdown
# Schema Migration N → M

- **Date**: YYYY-MM-DD
- **Files Modified**: [list]
- **Changes**: [what fields were added, renamed, or removed]
- **Entries Updated**: [count]
```

Update `Tracker Schema` in `config.md` to the new schema version.

### Step 4 — Commit and Push

```bash
git add .squidsquad/ .claude/
git commit -m "squidsquad: upgrade to [VERSION]"
git push
```

Tell the user what was upgraded and whether any schema migrations ran.

---

## Schema Changelog

### Schema 1 (current — introduced in v0.5.0)

**Bug fields**: ID, Title, Severity, Status, Reported By, Assigned To, Description, Steps to Reproduce, Expected, Actual, Discussion

**Feature fields**: ID, Title, Priority, Status, Owner, Description, Acceptance Criteria, Discussion

**Bug status values**: `Open` → `Investigating` → `Fixed` → `Verified` → `Closed`

**Feature status values**: `Pending` → `Approved` → `In Progress` → `Pending Test` → `Shipped`

Future schema changes will be documented here with their migration instructions before being released.
