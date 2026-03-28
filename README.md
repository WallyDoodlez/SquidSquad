```
      ▗▄▄▄▄▖
     ▟██████▙
      ▐▌▀  ▀▐▌
    ▝▜████▛▘
      ▐████▌
     ▗██████▖
    ▐███    ███▌
   ▐██▘      ▝██▌
  ▐▛▘          ▝▜▌
  ▌▖            ▗▌
  ▝▘            ▝▘

  S Q U I D S Q U A D
```

# SquidSquad

**Your AI dev team that coordinates through markdown, not meetings.**

SquidSquad is a Claude Code skill that spins up three autonomous AI agents — a Frontend Lead, a Backend Lead, and a PM/QA — that work on your codebase in parallel and coordinate through a shared `.squidsquad/` folder. No message queues. No orchestration servers. Just markdown files and git.

---

## What It Is

SquidSquad turns a single git repository into a multi-agent development environment. Each agent runs as a separate Claude Code CLI instance, loops autonomously, and communicates with the other agents by reading and appending to shared tracker files — bugs, features, QA logs — that live alongside your code.

The result: bugs get filed, triaged, fixed, and verified. Features move from backlog to shipped. The PM checks in with you each cycle to surface blockers and get approvals. Everything is traceable in git history.

---

## How It Works

### Three Agents

| Agent | Role | Loop |
|-------|------|------|
| **FE Lead** | Owns frontend code. Fixes FE bugs. Implements FE features. | Fix bugs → implement features → run FE tests → push |
| **BE Lead** | Owns backend code. Fixes BE bugs. Implements BE features. | Fix bugs → implement features → run BE tests → push |
| **PM/QA** | Runs e2e tests. Files bugs. Verifies fixes. Checks in with you. | Human check-in → e2e tests → file bugs → verify work → push |

### The Ralph Loop

Every agent runs the Ralph Loop — an autonomous work cycle that repeats every 10 minutes:

```
pull → scan for work → do work → run tests → log iteration → push → sleep
```

FE and BE leads pick up the highest-priority open bugs first, then move to approved features. PM/QA runs the full test suite, files bugs to the right team, and verifies completed work.

### Shared `.squidsquad/` Folder

All coordination happens through markdown files committed to your repo:

```
.squidsquad/
├── config.md              ← project config, test commands, ID counters
├── start-fe.sh            ← launch FE Lead
├── start-be.sh            ← launch BE Lead
├── start-pm.sh            ← launch PM/QA
├── fe/
│   ├── CLAUDE.md          ← FE Lead instructions
│   ├── bugs.md            ← BUG-FE-XXX tracker
│   ├── features.md        ← FEAT-FE-XXX tracker
│   └── iterations/        ← per-cycle logs
├── be/
│   ├── CLAUDE.md          ← BE Lead instructions
│   ├── bugs.md            ← BUG-BE-XXX tracker
│   ├── features.md        ← FEAT-BE-XXX tracker
│   └── iterations/        ← per-cycle logs
└── pm/
    ├── CLAUDE.md          ← PM/QA instructions
    ├── qa-log.md          ← test run results
    ├── enhancements.md    ← product backlog
    └── iterations/        ← per-cycle logs
```

### Architecture

```
                        ┌──────────────────────┐
                        │   You (the human)    │
                        └──────────┬───────────┘
                                   │ check-ins every cycle
                                   ▼
┌───────────────┐        ┌──────────────────┐        ┌───────────────┐
│   FE Lead     │        │    PM / QA       │        │   BE Lead     │
│  Claude CLI   │◄──────►│   Claude CLI     │◄──────►│  Claude CLI   │
└───────┬───────┘        └────────┬─────────┘        └───────┬───────┘
        │                         │                          │
        └─────────────────────────┼──────────────────────────┘
                                  │
                           .squidsquad/
                          (shared via git)
```

Agents communicate asynchronously — each agent reads the latest state on `git pull` and writes new entries on `git push`. No direct agent-to-agent communication is needed.

---

## Quick Start

### 1. Install the Skill

Add SquidSquad as a Claude Code skill by placing `SKILL.md` in your Claude Code skills directory, or reference it directly.

### 2. Set Up Your Project

In a Claude Code session, say:

```
Set up Squidsquad for my project.
```

Claude will ask for your project name, repo URL, FE/BE frameworks, and test commands, then generate the full `.squidsquad/` folder structure.

### 3. Launch the Agents

Open three terminal windows and run:

```bash
# Terminal 1 — FE Lead
bash .squidsquad/start-fe.sh

# Terminal 2 — BE Lead
bash .squidsquad/start-be.sh

# Terminal 3 — PM/QA
bash .squidsquad/start-pm.sh
```

The agents will start their Ralph Loops immediately. Check `.squidsquad/fe/bugs.md`, `.squidsquad/be/features.md`, and `.squidsquad/pm/qa-log.md` to see activity as it accumulates.

### 4. Interact Via PM

The PM/QA agent will check in with you each cycle. You can:
- Report a new bug → it gets filed to the right team
- Request a new feature → it enters the backlog as `Pending`
- Approve a pending feature → it becomes `Approved` and the team picks it up
- Change priorities → the PM updates the tracker

---

## Tracker Formats

### Bugs

```markdown
## BUG-FE-001 — Safari login page crashes on submit

- **Severity**: High
- **Status**: Open
- **Reported By**: pm/qa
- **Assigned To**: fe-lead
- **Description**: Clicking submit on the login form in Safari 17 causes a JS exception.
- **Steps to Reproduce**:
  1. Open the app in Safari 17
  2. Enter valid credentials
  3. Click Submit
- **Expected**: User is redirected to dashboard
- **Actual**: Uncaught TypeError in console, page does not navigate

### Discussion

> [2026-01-15 09:00] **pm/qa**: Reproduced on Safari 17.2, macOS 14.3.
> [2026-01-15 09:45] **fe-lead**: Race condition in useAuthSubmit hook. Fixing.
> [2026-01-15 10:30] **fe-lead**: Fixed in commit abc1234. Status → Fixed.
> [2026-01-15 11:00] **pm/qa**: Verified. No regression. Status → Closed.
```

### Features

```markdown
## FEAT-BE-001 — Rate limiting on auth endpoints

- **Priority**: High
- **Status**: Approved
- **Owner**: be-lead
- **Description**: Add rate limiting to /api/auth/* endpoints to prevent brute force.
- **Acceptance Criteria**:
  - [ ] Max 10 requests per minute per IP on auth endpoints
  - [ ] Returns 429 with Retry-After header when limit exceeded
  - [ ] Rate limit state survives server restart (Redis-backed)

### Discussion

> [2026-01-15 09:00] **pm/qa**: Proposed for this sprint. Security priority.
> [2026-01-15 09:30] **human**: Approved. Go ahead.
> [2026-01-15 09:35] **pm/qa**: Status → Approved.
> [2026-01-15 10:00] **be-lead**: Picking this up. Status → In Progress.
```

---

## Cross-Team Bug Filing

One of SquidSquad's core design principles: **any agent can file a bug to any team — including their own — directly, with no routing bottleneck.**

| Who discovers the bug | Files to | Format |
|-----------------------|----------|--------|
| FE Lead (FE issue found during feature work) | `fe/bugs.md` | `BUG-FE-XXX` |
| FE Lead (root cause is in BE) | `be/bugs.md` | `BUG-BE-XXX` |
| BE Lead (BE issue found during feature work) | `be/bugs.md` | `BUG-BE-XXX` |
| BE Lead (root cause is in FE) | `fe/bugs.md` | `BUG-FE-XXX` |
| PM/QA (FE failure) | `fe/bugs.md` | `BUG-FE-XXX` |
| PM/QA (BE failure) | `be/bugs.md` | `BUG-BE-XXX` |
| PM/QA (unclear boundary) | both trackers | cross-linked via Discussion |

### How it plays out

**FE Lead hits a backend wall:**
The FE Lead is fixing a login bug and discovers the session token validation logic is wrong on the server. Rather than leaving a comment and hoping someone notices, they file `BUG-BE-XXX` directly in `be/bugs.md`, append a Discussion note to the original FE bug linking the two, and move on. The BE Lead picks it up on their next pull.

**PM/QA sees an API failure in e2e tests:**
The PM doesn't need to ask the FE Lead to relay the issue to the BE Lead. They file `BUG-BE-XXX` directly, with full reproduction steps from the test output. Zero hops.

**BE Lead exposes a contract mismatch:**
The BE Lead ships a new endpoint but notices the expected request shape doesn't match what the FE is sending. They file `BUG-FE-XXX` in `fe/bugs.md` describing the contract, without touching any frontend code themselves.

### Why this matters

In traditional team setups, cross-team bugs get stuck in handoff — someone has to triage, assign, and re-explain the issue at every boundary. SquidSquad eliminates this: the agent that discovers the problem has full write access to both trackers and files the bug with complete context, right then. The receiving agent picks it up on their next pull with everything they need.

No standup required.

---

## Requirements

- [Claude Code CLI](https://claude.ai/code) with `claude -p` support
- Claude Code auto mode (`--permission-mode auto --enable-auto-mode`) — agents run unattended and need permission to read/write files and run tests without prompting
- A git repository with a remote (GitHub, GitLab, etc.)
- FE, BE, and e2e test commands that can be run from the repo root

---

## Git Protocol

SquidSquad agents follow strict append-only conventions to minimize conflicts:

- Always `git pull --rebase` before starting work
- Tracker files are **append-only** — never edit or delete existing entries
- Discussion sections are append-only — always add at the bottom
- Push after every completed work unit
- Rebase conflicts in tracker files are resolved by keeping both versions

---

## License

MIT
