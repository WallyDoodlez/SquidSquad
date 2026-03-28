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

### [Role] Lead Ralph Loop

Each dev agent follows this loop, substituting its own role name and tracker paths:

```
1. git pull --rebase
2. Scan [role]/bugs.md for Open or Investigating items
   → Fix each bug in code
   → If bug touches another agent's domain, file BUG-[OTHER]-XXX in [other]/bugs.md
   → Update bug status to Fixed, append Discussion entry
3. Scan [role]/features.md for Approved items
   → Implement next feature
   → Update status to In Progress, then Pending Test
   → Append Discussion entry
4. Run [role] test command (from config.md)
5. Log iteration to [role]/iterations/iter-N.md
6. git add -A && git commit && git push
7. Sleep [INTERVAL] minutes (from config.md) → repeat
```

### PM/QA Ralph Loop

```
1. git pull --rebase
2. Check with human: any new requirements, bugs, or priorities?
   → If yes: file new bugs to [role]/bugs.md for the appropriate dev agent
   → If yes: add features to [role]/features.md as Pending
   → Await human approval before marking features Approved
3. Run full e2e test command (from config.md)
4. Log results to pm/qa-log.md
5. If tests fail: file BUG-[ROLE]-XXX to the appropriate dev agent's tracker
6. Scan each dev agent's features.md for Pending Test items → verify → update to Shipped
7. Scan each dev agent's bugs.md for Fixed items → verify → update to Verified/Closed
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

Use the templates in `references/agent-instructions.md` to generate role-specific CLAUDE.md files inside each `[role]/` folder and `pm/`, substituting in the project's actual test commands and repo URL from config.md.

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

All agents run interactively. The boot script writes `.squidsquad/.active-role` (git-ignored) with the role name, then launches `claude --permission-mode auto`. The root `CLAUDE.md` detects this file and auto-starts the correct role.

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

echo "[ROLE]" > .squidsquad/.active-role
claude --permission-mode auto
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

"[ROLE]" | Set-Content .squidsquad/.active-role -NoNewline
claude --permission-mode auto
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

echo "pm" > .squidsquad/.active-role
claude --permission-mode auto
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

"pm" | Set-Content .squidsquad/.active-role -NoNewline
claude --permission-mode auto
```

> **Note:** All agents run interactively with `--permission-mode auto`. The boot script writes `.squidsquad/.active-role` (git-ignored) before launching Claude. The root `CLAUDE.md` detects this file on startup and auto-loads the correct role instructions. The user can observe progress and comment in any agent's terminal.

Make the `.sh` scripts executable (`chmod +x`).

### Step 5b — Generate Status Line Script

Generate `.squidsquad/statusline.sh` — a bash script that powers the Claude Code status bar for all SquidSquad agents. The script reads `.squidsquad/.active-role` to determine the current agent, then displays:

- **Squid emoji** `🦑` in green (ANSI `\033[32m`) when the agent is active
- **Role label** (e.g. `PM/QA`, `be`, `fe`)
- **Iteration number** (read from the highest `iter-N.md` in the role's `iterations/` folder)
- **Backlog pulse** (dev agents): count of open bugs + actionable features (e.g. `2 bugs 1 feat` or `clear`)
- **Agent health** (PM only): for each dev agent, show `🦑` green if their latest iteration is within 2× the loop interval, or `🦑✖` red if silent for longer
- **Time since last cycle** (file modification time of latest iteration log)

Output format (single line, ANSI-colored):
- Dev agent: `🦑 be │ iter 5 │ 2 bugs 1 feat │ 3m ago`
- PM/QA: `🦑 PM/QA │ iter 3 │ 🦑be 🦑✖fe │ 1m ago`

```bash
#!/bin/bash
# SquidSquad Status Line — shown in Claude Code's status bar
# Receives JSON session data on stdin; prints ANSI-colored status to stdout

cat > /dev/null &  # consume stdin (not used — we read from .squidsquad/ files)

SQDIR=".squidsquad"
[ ! -d "$SQDIR" ] && exit 0

# Read role
ROLE_FILE="$SQDIR/.active-role"
[ ! -f "$ROLE_FILE" ] && exit 0
ROLE=$(cat "$ROLE_FILE" | tr -d '[:space:]')
[ -z "$ROLE" ] && exit 0

# ANSI colors
GREEN='\033[32m'
RED='\033[31m'
DIM='\033[2m'
RESET='\033[0m'

# Get iteration number from latest iter-N.md
ITER_DIR="$SQDIR/$ROLE/iterations"
ITER_NUM=0
if [ -d "$ITER_DIR" ]; then
  LATEST=$(ls "$ITER_DIR"/iter-*.md 2>/dev/null | sort -t- -k2 -n | tail -1)
  if [ -n "$LATEST" ]; then
    ITER_NUM=$(echo "$LATEST" | grep -oE '[0-9]+\.md$' | grep -oE '[0-9]+')
  fi
fi

# Get interval from config
INTERVAL=$(grep 'Minutes' "$SQDIR/config.md" 2>/dev/null | grep -oE '[0-9]+')
INTERVAL=${INTERVAL:-10}

# Time since last iteration (file modification time)
TIME_STR="-"
NOW=$(date +%s)
if [ -n "$LATEST" ]; then
  if stat --version >/dev/null 2>&1; then
    LAST_MOD=$(stat -c %Y "$LATEST" 2>/dev/null)
  else
    LAST_MOD=$(stat -f %m "$LATEST" 2>/dev/null)
  fi
  if [ -n "$LAST_MOD" ]; then
    ELAPSED=$(( (NOW - LAST_MOD) / 60 ))
    TIME_STR="${ELAPSED}m ago"
  fi
fi

# Count open bugs and actionable features
BUGS_FILE="$SQDIR/$ROLE/bugs.md"
FEATS_FILE="$SQDIR/$ROLE/features.md"
BUG_COUNT=0
FEAT_COUNT=0
[ -f "$BUGS_FILE" ] && BUG_COUNT=$(grep -cE '^\- \*\*Status\*\*: (Open|Investigating)' "$BUGS_FILE" 2>/dev/null) || true
[ -f "$FEATS_FILE" ] && FEAT_COUNT=$(grep -cE '^\- \*\*Status\*\*: (Approved|In Progress)' "$FEATS_FILE" 2>/dev/null) || true
BUG_COUNT=${BUG_COUNT:-0}
FEAT_COUNT=${FEAT_COUNT:-0}

# Build backlog string
BACKLOG=""
[ "$BUG_COUNT" -gt 0 ] && BACKLOG="${BUG_COUNT} bug$([ "$BUG_COUNT" -gt 1 ] && echo s)"
if [ "$FEAT_COUNT" -gt 0 ]; then
  [ -n "$BACKLOG" ] && BACKLOG="$BACKLOG "
  BACKLOG="${BACKLOG}${FEAT_COUNT} feat$([ "$FEAT_COUNT" -gt 1 ] && echo s)"
fi
[ -z "$BACKLOG" ] && BACKLOG="clear"

# Role label
if [ "$ROLE" = "pm" ]; then
  ROLE_LABEL="PM/QA"
else
  ROLE_LABEL="$ROLE"
fi

# PM: show other agents' health
HEALTH=""
if [ "$ROLE" = "pm" ]; then
  AGENTS=$(grep 'Dev Agents' "$SQDIR/config.md" 2>/dev/null | sed 's/.*: //' | tr ',' ' ')
  THRESHOLD=$(( INTERVAL * 2 ))
  for AGENT in $AGENTS; do
    AGENT=$(echo "$AGENT" | tr -d '[:space:]')
    [ -z "$AGENT" ] && continue
    A_DIR="$SQDIR/$AGENT/iterations"
    A_LATEST=$(ls "$A_DIR"/iter-*.md 2>/dev/null | sort -t- -k2 -n | tail -1)
    if [ -n "$A_LATEST" ]; then
      if stat --version >/dev/null 2>&1; then
        A_MOD=$(stat -c %Y "$A_LATEST" 2>/dev/null)
      else
        A_MOD=$(stat -f %m "$A_LATEST" 2>/dev/null)
      fi
      if [ -n "$A_MOD" ]; then
        A_ELAPSED=$(( (NOW - A_MOD) / 60 ))
        if [ "$A_ELAPSED" -le "$THRESHOLD" ]; then
          HEALTH="${HEALTH} ${GREEN}🦑${RESET}${AGENT}"
        else
          HEALTH="${HEALTH} ${RED}🦑✖${RESET}${AGENT}"
        fi
      else
        HEALTH="${HEALTH} ${DIM}🦑?${RESET}${AGENT}"
      fi
    else
      HEALTH="${HEALTH} ${DIM}🦑?${RESET}${AGENT}"
    fi
  done
fi

# Output
if [ "$ROLE" = "pm" ]; then
  echo -e "${GREEN}🦑${RESET} ${ROLE_LABEL} │ iter ${ITER_NUM} │${HEALTH} │ ${DIM}${TIME_STR}${RESET}"
else
  echo -e "${GREEN}🦑${RESET} ${ROLE_LABEL} │ iter ${ITER_NUM} │ ${BACKLOG} │ ${DIM}${TIME_STR}${RESET}"
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
            "command": "bash -c 'if [ -d .squidsquad ]; then V=$(grep -o [0-9][0-9.]*[0-9] .squidsquad/config.md 2>/dev/null | head -1); cat <<LOGO\n\n    ▗▄▄▄▄▖\n   ▟██████▙\n    ▐▌▀ ▀▐▌\n  ▜██████▛▘\n   ▐██████\n    ▌▌▌▌▌▌\n  S Q U I D S Q U A D   v${V:-?}\n\nLOGO\nfi'"
          }
        ]
      }
    ]
  }
}
```

> **Why these permissions?** Dev agents run with `--permission-mode auto` but still need explicit allow rules for writing tracker files and running git commands without being prompted mid-cycle. Without these, the agent will pause and ask for permission on every file write.

**If `.claude/settings.json` already exists**, merge the SquidSquad hook into the existing `SessionStart` array (or create the `SessionStart` key if absent). Also add the `statusLine` key if not already present. Do not overwrite any existing hooks or status line config — append or add only.

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
> Regenerate `.squidsquad/[role]/CLAUDE.md`, `.squidsquad/start-[role].sh`, and `.squidsquad/start-[role].ps1` using the Dev Agent template from `references/agent-instructions.md`. Substitute `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, and `[INTERVAL]` with values from `config.md`. Do not touch `bugs.md`, `features.md`, or `iterations/`.

**One agent for PM/QA:**
> Regenerate `.squidsquad/pm/CLAUDE.md`, `.squidsquad/start-pm.sh`, and `.squidsquad/start-pm.ps1` using the PM/QA template from `references/agent-instructions.md`. Substitute `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`, and `[INTERVAL]` from `config.md`. Do not touch `qa-log.md`, `enhancements.md`, `iterations/`, or `migrations/`.

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

**Feature status values**: `Pending` → `Approved` → `In Progress` → `Pending Test` → `Shipped`

Future schema changes will be documented here with their migration instructions before being released.
