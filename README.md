```
      ▗▄▖
     ▟█ █▙
    ▐█• •█▌
   ███████
   ▐█████▌
    ▐▌▐▌▐▌
  S Q U I D S Q U A D
```

# SquidSquad

**Your AI dev team that coordinates through markdown, not meetings.**

SquidSquad is a [Claude Code](https://claude.ai/code) skill that spins up autonomous AI agents — one per dev role you define, plus PM and QA — that work on your codebase in parallel. No message queues. No orchestration servers. Just a shared `.squidsquad/` folder and git.

---

## The Problem

You have a codebase and Claude Code. You can fix one bug at a time. But what if you could have a team — a dev agent fixing bugs, a QA agent verifying fixes, a PM managing your backlog, a DM packaging releases — all running in parallel, coordinating through git, while you focus on the hard decisions?

## What SquidSquad Does

- Spins up **autonomous agents** that loop independently: pull → triage bugs → implement features → test → push
- **PM checks in with you** each cycle (non-blocking) to surface blockers and get approvals
- **QA independently verifies** every bug fix and feature before it ships
- **DM handles delivery**: README updates, CHANGELOG entries, version bumps, git tags
- Bugs get filed, triaged, fixed, and verified. Features move from idea to shipped. Everything is traceable in git history and GitHub Issues.

---

## Key Features

- **Autonomous Ralph Loop** — agents cycle independently every N minutes, picking up work as it appears
- **GitHub Issues as tracker** — bugs and features are GitHub Issues with structured labels, not internal files
- **5-phase feature planning** — Research → Discussion → Planning → Execution → QA, with human approval gates
- **Shared memory vault** — agents learn your preferences, decisions, and patterns over time via an Obsidian-compatible knowledge base
- **Self-improvement scanning** — agents proactively find code quality issues, test gaps, and doc drift during quiet cycles
- **Live status bar** — emoji-rich status line showing what each agent is doing, backlog counts, context pressure, and cycle countdown
- **Context pressure detection** — agents save state and exit cleanly when the context window fills up, resuming on restart
- **Auto versioning** — ships are counted and minor versions auto-bump when thresholds are met

---

## Quick Start

### 1. Install

In your project's git repo:

```bash
npx squidsquad
```

The bootstrapper checks prerequisites (Node.js 18+, Python, `gh` CLI, Claude Code), seeds the skill into your project, and launches the setup wizard. The wizard asks for your project name, dev roles (e.g. `fe, be` or just `skill`), test commands, and loop interval — then generates the full `.squidsquad/` folder.

**Already have Claude Code open?** You can also run `Set up SquidSquad for my project.` directly in a Claude Code session.

### 2. Launch

Open one terminal per agent. Available boot scripts depend on your setup — check `.squidsquad/start-*.sh` for your list:

```bash
bash .squidsquad/start-skill.sh    # Dev agent (autonomous)
bash .squidsquad/start-pm.sh       # PM (interactive — you talk to this one)
bash .squidsquad/start-dm.sh       # Delivery Manager (optional, autonomous)
```

QA, Designer, and additional dev agents get their own `start-[role].sh` scripts when configured during setup.

PowerShell: `.\.squidsquad\start-[role].ps1`

### 3. Work

Talk to PM to file bugs, request features, and approve plans. Everything else happens automatically.

---

## Team Shapes

| You say at setup | Agents created |
|-----------------|----------------|
| `fe, be` | FE Lead + BE Lead + PM |
| `skill` | Skill Lead + PM |
| `fe, be, designer` | FE Lead + BE Lead + Designer + PM |

QA and DM are optional — add them during setup. When QA is absent, dev agents self-verify. When DM is absent, PM handles delivery.

---

## How It Works

```mermaid
sequenceDiagram
    participant You
    participant PM
    participant Dev
    participant QA
    participant DM

    You->>PM: "Add search to the API"
    PM->>PM: Research → Discussion → Plan
    You->>PM: Approve
    PM->>Dev: Feature approved (#42)
    Dev->>Dev: Implement + test
    Dev->>QA: Ready for verification
    QA->>QA: Verify + E2E tests
    QA->>DM: Verified
    DM->>DM: Docs + CHANGELOG + version bump
    Note over You,DM: Shipped
```

All coordination is asynchronous through git. Agents pull to read state, push after work. No direct agent-to-agent communication — GitHub Issues and the `.squidsquad/` folder are the shared bus.

For the full architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Built By Its Own Agents

This project is developed by SquidSquad itself. The [CHANGELOG](./CHANGELOG.md) has been maintained by the DM agent since v0.9.0. Bug fixes, documentation updates, and version bumps are all handled by the squad. The commit history tells the story — look for `skill:`, `pm:`, `dm:`, and `qa:` prefixes.

---

## Requirements

- [Node.js 18+](https://nodejs.org) — for the `npx squidsquad` installer
- [Claude Code CLI](https://claude.ai/code)
- [Python 3.x](https://python.org) — powers internal coordination scripts
- [`gh` CLI](https://cli.github.com) — authenticated with Issues permissions
- A GitHub repository

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How SquidSquad works under the hood |
| [Sub-Skill Guide](docs/sub-skill-guide.md) | Creating and contributing sub-skills |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to report bugs, propose features, submit PRs |
| [CHANGELOG.md](CHANGELOG.md) | Version history (maintained by agents) |
| [SKILL.md](SKILL.md) | Full skill specification (the source of truth) |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports, feature proposals, and PRs are welcome.

## License

[AGPL-3.0](./LICENSE)
