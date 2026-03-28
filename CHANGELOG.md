# Changelog

All notable changes to SquidSquad will be documented here.

---

## [0.5.0] — 2026-03-27

Initial release.

### Core

- Three-agent coordination model: FE Lead, BE Lead, PM/QA
- Shared `.squidsquad/` folder as the coordination layer — no message queues, no servers
- All communication through append-only markdown tracker files committed to git

### Agents

- **FE Lead** — owns frontend code, fixes `fe/bugs.md`, implements `fe/features.md`, runs FE tests
- **BE Lead** — owns backend code, fixes `be/bugs.md`, implements `be/features.md`, runs BE tests
- **PM/QA** — runs e2e tests, files bugs to either team directly, verifies completed work, checks in with human interactively
- Ralph Loop for each agent: pull → work → test → log iteration → push → sleep 10min

### Bug & Feature Tracking

- `BUG-[TEAM]-XXX` format with severity, status flow, and `### Discussion` sections for cross-team threading
- `FEAT-[TEAM]-XXX` format with acceptance criteria and human approval gate (`Pending` → `Approved`)
- Any agent can self-file bugs to their own tracker or cross-file to the other team — no routing bottleneck

### Setup

- Step 0: clean worktree check before initializing
- Steps 1–6: gather project details, generate full `.squidsquad/` folder, config, CLAUDE.md templates, boot scripts, seed trackers
- Step 7: writes or merges `SessionStart` hook into `.claude/settings.json`
- Step 8: auto-commits and pushes `.squidsquad/` so agents can pull immediately on boot
- Step 9: dramatic launch sequence confirm message

### Boot Scripts

- `.sh` (bash/zsh) and `.ps1` (PowerShell) variants for all three agents
- FE and BE use `--permission-mode auto --enable-auto-mode -p` (fully autonomous)
- PM uses `--permission-mode auto` (interactive — you talk to this one)

### Versioning

- Skill version (`0.5.0`) and tracker schema version (`1`) stored separately in `config.md`
- Upgrade path distinguishes scaffolding-only upgrades (safe to regenerate) from schema migrations (targeted rewrite of tracker files with migration log)
- Schema migrations logged to `pm/migrations/` with a discussion note on each modified entry
- Schema changelog in SKILL.md documents all fields and status values for schema 1

### SessionStart Hook

- `.claude/settings.json` hook prints the squid logo + version number on every Claude Code boot in a SquidSquad repo
- Version read dynamically from `.squidsquad/config.md`
