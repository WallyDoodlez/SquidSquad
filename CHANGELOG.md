# Changelog

All notable changes to SquidSquad will be documented in this file. This changelog has been maintained by SquidSquad's own agents since v0.9.0.

---

## [0.22.0] — 2026-04-18

### Added

- #1426 — **Shared filesystem** — API keys and cross-clone config now live in `~/.squidsquad/` with restricted file permissions. No more environment variable pollution — secrets are read automatically by the model router and providers

### Fixed

- #1395 — Research phase now consults the shared vault for existing decisions, patterns, and human preferences before investigating
- #1397 — PRs now start as drafts and convert to ready only after QA passes, preventing premature merges
- #1398 — Context pressure values now come from real statusline data instead of estimates
- #1399 — PRs now auto-close linked GitHub Issues on merge via "Closes #N" in PR body
- #1405 — DM delivery now verifies PR is merged before marking Shipped
- #1428 — QA verification now requires deterministic pytest tests before marking items as verified

---

## [0.21.0] — 2026-04-18

### Added

- #1074 — **Auto-merge PRs** — when QA verifies a task, PM automatically squash-merges the PR so you don't have to. Bug fixes and `merge:manual`-tagged items still require your review
- #1357 — **Pipeline self-healing** — PM's pipeline sentinel now detects 6 types of stuck tasks (orphaned PRs, shipped-without-merge, stalled approvals, dead-agent work) with two-tier response: unstick immediately, then auto-file a root-cause bug for permanent fix

### Fixed

- #1230 — Removed unused import in health_check.py
- #1299 — Fixed boot script session names dropping agent role on Windows (cmd /c quote handling)
- #1301 — Fixed stale agent detection: PID is now the sole liveness check — dead agents are reliably detected and rebooted regardless of .health file state
- #1345 — Fixed self-restart on Windows: boot wrapper watcher now uses absolute paths so .restart sentinel is reliably detected

---

## [0.20.0] — 2026-04-17

### Fixed

- #1078 — Added 31 unit tests for compose.py, covering template composition, placeholder substitution, deployment, and config reading
- #1079 — Added 24 unit tests for boot_remote.py, covering lock management, OS detection, boot script discovery, health polling, and spawn routing

---

## [0.19.0] — 2026-04-17

### Added

- #922 — **SQLite-based scan index** — improvement scanning now uses a local SQLite database to track coverage gaps, git churn, and finding acceptance rates, picking higher-value scan targets each cycle instead of scanning at random
- #942 — **Agent health files** — boot scripts write `.health` status files so PM detects agent state from files, not unreliable timestamp heuristics

### Fixed

- #1022 — Fixed health_check.py crashing on Windows cp1252 terminals due to Unicode emoji in table output
- #960 — Feature branch commits no longer include working-state and iteration files that don't belong in PRs
- #940 — Agents no longer spawn repeatedly due to false-positive staleness detection from mtime checks

---

## [0.18.0] — 2026-04-14

### Added

- #347 — **PM/QA role separation** — PM no longer assumes QA duties. QA runs as an independent agent with its own verification cycle. PM falls back to combined mode when QA is absent.
- #462 — **Adaptive setup questions** — the setup wizard now asks 3 context questions (1 fixed + 2 inferred from your answers) to tailor each agent's personality to your project domain.
- #897 — **Designer agent cleanup** — removed phantom designer config entries and added `.stop` sentinel for clean agent lifecycle management.

### Fixed

- #894 — health_check.py now returns exit 1 when .local-config is missing instead of silently reporting all-healthy
- #893 — Fixed tracker.py unread feedback check failing on non-canonical role names
- #590 — Dev agent planning artifact directory mismatch (pm/planning/ as primary location)
- #887, #895, #896, #919 — Unit test coverage for cycle.py, vault_check.py, config.py, and vault_remember.py

---

## [0.17.0] — 2026-04-13

### Added

- #5 — **Add agent role command** — clone, configure, and boot any role from PM with `add_role.py`. Includes dry-run mode, lock file concurrency protection, role validation against config.md, and duplicate registration checks.
- #401 — **Capability sub-skills** — replaced the old tool concept with a composable sub-skill ecosystem. Roles declare capabilities via manifests; the system validates availability at startup.

### Fixed

- #875 — boot_remote.py no longer spawns duplicate agents — PID-based process detection kills stale processes before spawning replacements, with a 2-minute startup grace period
- #632 — .local-config is now created during setup — health checks and auto-boot actually work on fresh installs
- #606 — config.py no longer returns duplicate or phantom agents in list-agents
- #598 — Planning artifact location clarified — dev agents now know to read from pm/planning/
- #591 — All agents now push back on ambiguous context instead of guessing
- #589 — README punchline updated to reflect non-dev team support
- #558 — Dev SOUL.md no longer hardcodes file extensions — works with any project type
- #493 — Skill agent no longer bypasses tracker.py transitions — labels stay in sync
- #492 — PM can now find status:pending-test items via gh issue list
- #470 — Skill agent correctly detects QA-rejected in-progress items without human nudge
- #774 — Fixed triage.py Windows Unicode crash (missing encoding=utf-8)
- #758 — Designer directory now includes working-state.md
- #886 — Added 22 unit tests for health_check.py — critical infrastructure coverage

---

## [0.16.0] — 2026-04-12

### Added

- #328 — **Intent-driven setup wizard** — tell the wizard what you're building and it proposes a team. Role manifest registry (5 roles, 4 tools, 2 presets: software-dev, design). PM and DM always installed. Interactive review screen before any disk writes. Re-run detection with regenerate/rebuild options.
- #4 — **Auto-boot team** — PM automatically spawns all other agents on startup. OS-aware agent launching (macOS Terminal/iTerm, Windows Terminal/PowerShell, Linux tmux).
- #309 — **Unread feedback guard** — tracker blocks pending-test transitions when oversight comments (PM, QA, human) haven't been read, preventing premature status changes.
- #442 — **Vocabulary rename** — "feature" → "task", "bug" → "issue" across labels, commands, templates, and docs. Decouples SquidSquad from code-specific terminology so non-dev teams (design, content, marketing) feel at home.

### Fixed

- #320 — Tracker transitions now enforce role-based authority — agents can only perform transitions they own
- #471 — Issue gate no longer blocked by pending (non-actionable) items — only status:open items block task pickup
- #472 — Dev SOUL.md now requires test coverage for shipped code
- #436 — Improvement scan criteria moved from hardcoded sub-skill to SOUL.md templates — each role scans with its own lens
- #376 — Context-pressure exit replaced with continue — agents no longer kill themselves mid-task
- #378 — Default context pressure threshold lowered from 80% to 70% for earlier, safer exits
- #390 — Fixed Windows UTF-8 encoding crash in tracker.py subprocess calls
- #389 — Status bar no longer shows ghost agents for roles in registry but not installed
- #373 — npx installer now pre-fetches wizard scripts via deterministic manifest
- #335 — PM health check rewritten as Python script (health_check.py) — no more prose-based stale-reporting drift
- #463 — Fixed shell injection risk in boot_remote.py path handling
- #468 — Fixed path traversal vulnerability in vault_remember.py
- #360 — Sub-skill developer guide updated for new role directory layout
- #321, #327 — npx installer stability fixes (dirty worktree abort, --dangerously-skip-permissions)
- #403 — Tracker no longer creates double-prefixed issue titles
- #429, #430, #464, #465, #466, #469 — Internal script hardening and test coverage improvements

---

## [0.15.0] — 2026-04-08

### Added

- #269 — **`npx squidsquad` installer** — bootstrap SquidSquad onto any project with a single command. Checks prerequisites, seeds the skill and setup wizard, and offers to launch immediately. Zero dependencies.

### Fixed

- #280 — README and SKILL.md no longer reference non-existent QA boot scripts — launch instructions now show available scripts depend on your setup
- #281 — SKILL.md file structure diagram updated to match actual repo layout — uses placeholder notation instead of hardcoded paths
- #277 — README Team Shapes table now correctly shows QA and DM as optional add-ons
- #278 — CONTRIBUTING.md bug reports and feature requests now link directly to GitHub Issue templates
- #262 — Vault briefing and project notes updated from v0.11.0 to v0.14.0
- #261 — GitHub Issue templates now use correct SquidSquad label taxonomy (`type:bug`, `type:feature`)
- #260 — Sub-skill guide now documents the `{{runtime:}}` directive for editable agent personalities
- #258 — Architecture docs now cover Runtime SOUL.md and self-diagnostic systems (v0.14.0 additions)
- #257 — CONTRIBUTING.md now mentions `/squidsquad-bug` command for in-session bug reporting
- #210, #194, #193, #197 — Stale documentation references resolved (some already fixed by README overhaul)

---

## [0.14.0] — 2026-04-06

### Added

- #251 — **Self-diagnostic bug reporting** — `/squidsquad-bug` slash command lets users report bugs to the upstream SquidSquad repo with sanitized config + diagnostic context. Automated anomaly detection logs errors from tracker, git, and composition operations locally (JSON Lines, 1MB rotation). Public repos default ON, private repos opt-in.
- #149 — **Runtime SOUL.md** — agent personalities are now separate files (`.squidsquad/[role]/SOUL.md`) read at session start, not compiled into CLAUDE.md. Edit personality directly without redeploying templates.
- #239 — **CONTRIBUTING.md and CODE_OF_CONDUCT.md** — community governance docs for going public. Contributor Covenant v2.1.
- #232 — **Community infrastructure** — AGPL-3.0 LICENSE, GitHub Issue templates (bug report, feature request), SKILL.md license field.
- #189 — **Sub-skill developer guide** — comprehensive guide at `docs/sub-skill-guide.md` covering anatomy, composition, testing, and contribution model.
- #190 — **Architecture overview** — `docs/ARCHITECTURE.md` with Mermaid diagrams covering Ralph Loop, feature lifecycle, sub-skill composition, vault, coordination.
- #233 — **CHANGELOG polish** — rewritten for public readability, no internal jargon.
- #2 — **README overhaul** — 151-line lean landing page with developer-to-developer tone.
- #240 — **Boot-time agent registration** — agents auto-register in config.md Agents section on boot via `config.py sync-agents`.
- #211 — **Phantom fix prevention** — `git_ops.py has-changes` gate in dev agent template prevents marking pending-test without actual code changes.

---

## [0.13.0] — 2026-04-06

### Fixed

- Security: eliminated shell injection risks in internal scripts (subprocess list form throughout).
- Status bar: DM agent uses configured alias instead of hardcoded label.
- Status bar: QA role now has its own hint pool instead of reusing dev hints.
- `/squidsquad-status` command now includes DM in the agent health dashboard.
- Internal test reliability improvements.

---

## [0.12.0] — 2026-04-06

### Added

- **Vault Phase 3: vault-remember** — agents automatically reflect at the end of each productive cycle, capturing decisions, patterns, learnings, and human preferences to the shared vault. Your squad learns and remembers across sessions.
- **Templatized boot scripts** — single template per platform (`.ps1` / `.sh`) generated by `compose.py boot`. Eliminates drift between boot scripts when roles are added or updated.

### Fixed

- Security: eliminated shell injection risk in git operations and label handling.
- Git pull now warns on stash pop failure instead of silently succeeding.
- Documentation updated to match current CLI flags and version.
- Pre-launch `.gitignore` gaps closed (`.obsidian/`, `__pycache__/`).

---

## [0.11.0] — 2026-04-05

### Added

- **Start script test coverage** — 51 static tests validating CLI flags, role injection, and argument handling across all boot scripts.

### Fixed

- Documentation updated to use GitHub Issue numbers instead of old internal IDs.
- Boot scripts fixed: correct `--name` flag and PowerShell argument handling.

---

## [0.10.0] — 2026-04-04

### Added

- **Vault Phase 2: search and validation** — you can now search the vault by tag, type, or keyword. Notes auto-validate on save (broken links, missing fields). Agents update existing notes surgically instead of rewriting them.
- **Common sub-skills** — shared behaviors (git commits, bug filing, discussion protocol, iteration logs) extracted into reusable sub-skills for cleaner, more consistent agent behavior.
- **Sub-skill names in status bar** — line 2 now shows which sub-skill is active (e.g. `git-commit — Pushing changes...`), making agent behavior transparent during operation.

### Fixed

- Agents correctly prioritize bugs over features and block feature pickup when open bugs exist.
- Feature workflow includes "Planned" state between Planning and Approved, giving you a clear approval gate before execution begins.
- Improvement scan correctly classifies findings as bugs or features.
- Timestamped step markers (`[🦑 HH:MM:SS]`) on all Ralph Loop steps for easier scrollback scanning.
- Numerous documentation consistency fixes after GitHub Issues migration.

---

## [0.9.0] — 2026-04-04

### Added

- **Sub-skill architecture** — decomposed monolithic agent templates into composable sub-skills. Main skill orchestrates; roles are independent sub-skills with common behaviors auto-included. Build-time composition keeps templates maintainable.
- **Suppress PM cycles during planning** — PM performs silent pull + health check during active planning phases instead of full noisy cycles. Auto-resumes when planning completes.
- **Designer agent** — new agent type for design-to-code workflows. Interactive design sessions with you, feasibility assessment, structured design specs. Supports Figma, Google Stitch, or any MCP-connected design tool.
- **Separate QA from PM** — PM (human-facing coordinator, feature intake, backlog) and QA (E2E tests, bug verification, feature testing) are now distinct agents. QA is auto-added when dev or designer agents are present.
- **Self-improvement scanning** — agents scan your project for improvements during quiet cycles. Dev finds code issues, QA finds test gaps, designer spots design inconsistencies, DM catches doc gaps, PM identifies process improvements. Rate-limited (max 2 per scan), routed through PM for your review.
- **Vault memory layer Phase 1** — git-tracked, Obsidian-compatible shared memory vault (`.squidsquad/vault/`). PARAG structure (Projects, Areas, Resources, Archives, Galaxy). Agents build knowledge about your preferences, decisions, and patterns over time. Browsable in Obsidian.
- **Agent personalities** — each role has a distinct personality shaping communication, decisions, and collaboration. PM is the diplomat, QA the skeptic, dev the pragmatist, designer the creative, DM the closer.
- **GitHub Issues as tracker** — replaced internal markdown tracker files with GitHub Issues. Labels for type, priority, status, and role. Discussion entries as Issue comments. External contributors can file Issues and PM triages them into the workflow.

### Fixed

- PM no longer ships features with open QA gaps.
- Dev agent picks up QA-rejected features correctly.

---

## [0.8.0] — 2026-03-31

### Added

- **Delivery Manager (DM) role** — new optional agent that owns the "last mile" of shipping: user-facing docs, CHANGELOG entries, version bumps, git tags. Feature lifecycle gains `Pending Ship` status. When DM is absent, PM handles delivery automatically.
- **Granular status phases** — status bar shows exactly what each agent is working on, including the specific bug or feature ID.
- **Overdue indicator** — status bar shows `⏰ +Nm` when an agent's cycle exceeds the configured interval.
- **Bug discussion flow** — PM investigates root cause and discusses the problem with you before filing bugs to dev. You can steer the fix approach.
- **Cross-clone health detection** — agents detect each other's health by reading files across clones. No background processes, no API calls. Health icons: 🦑 healthy, 👻 stalled, ❓ unknown.
- **Philosophy section in README** — documents core design principles: git as the bus, complete audit trail, no external dependencies.

### Fixed

- DM role is fully optional with seamless PM fallback.
- Overdue timer no longer shows stale values on quiet cycles.
- Atomic file writes prevent stale status bar from file locking races on Windows.

---

## [0.7.0] — 2026-03-30

### Fixed

- Boot scripts include all required initialization steps.
- README updated to reflect current boot mechanism.
- All boot scripts use correct CLI flags.
- Dev agent bug triage pattern now correctly matches open bugs.

---

## [0.6.0] — 2026-03-29

### Added

- **Externalized agent templates** — agent instruction files are no longer 200+ line monoliths. Setup generates shared templates with all values substituted at build time. Each agent's CLAUDE.md is a small bootstrapper pointing to the template. Upgrades only regenerate templates without touching your config.
- **Open planning artifacts in VS Code** — after each planning phase, PM offers to open the artifact in VS Code. "Never ask again" persists across sessions.
- **Status bar redesign (Emoji Rich)** — complete rewrite with expressive emoji indicators. Dev bar: active task (🔨) or backlog (🐛/⭐/✅), context pressure (🧠/🧠🔥/🧠💀), countdown (🔄/🔜). PM bar adds ship counter (📦), planning phase (📋), team health icons (🦑/👻), and rest nudge (🌙/😴).
- **Current step + contextual hints** — status bar line 2 shows the active Ralph Loop step or rotating contextual hints when idle (e.g. "Msg me any time to file a bug").
- **Change loop interval on the fly** — `/squidsquad-interval <Nm>` changes the interval for all agents without restarting.
- **Upgrade & migration analysis** — feature planning always includes upgrade impact analysis, even for trivial features.
- **Smart resume for interrupted planning** — when planning resumes after an interruption, each phase checks if its artifact already exists and reuses it when appropriate.
- **Explicit approval gate after discussion** — PM presents a summary of all locked decisions and asks you to confirm before proceeding to test planning.
- **SquidSquad only activates via boot scripts** — normal `claude` sessions in a SquidSquad repo no longer trigger auto-boot.

### Fixed

- PM no longer asks for approval immediately after filing a feature — now completes the full planning process first.
- Status bar shows full squad health, not just dev agents.
- Git commands in status bar have timeouts to prevent hangs during concurrent operations.

---

## [0.5.2] — 2026-03-28

### Added

- **Status line** for all agents via Claude Code's `statusLine` setting. Shows role, version, backlog counts, context pressure, and cycle countdown. PM additionally shows team health icons and rest nudge.
- **Step markers** — every Ralph Loop step prints a `[🦑]` prefixed status line for easy scanning in terminal scrollback.
- **Context pressure detection** — agents check context window usage at cycle start. If above threshold (default 70%), they save state, commit, and exit for a fresh context. Boot scripts restart them automatically.
- **Working state file** — agents persist current task progress. On restart, they resume from saved state instead of starting over.
- **Quiet cycle skipping** — agents skip logging and committing when no work was done. Keeps git history meaningful.
- **Iteration log retention** — agents keep the last 20 iteration files. Git history preserves older ones.
- **PR-based approval flow** (optional) — dev agents create PRs instead of pushing to main. You review and merge on GitHub.
- **GitHub Issues ingestion** (optional) — PM auto-ingests open GitHub Issues into agent trackers each cycle.
- **`/squidsquad-status` command** — type in any Claude session for a dashboard of agent health, backlogs, and recently shipped items.
- **Deep 5-phase feature lifecycle** — Research, Discussion, Planning, Execution, QA. PM spawns research agents, asks targeted questions, creates test plans. Light mode for trivial features.
- **Reliable cycling via `/loop`** — agents use cron-based cycling instead of self-managed sleep loops.
- **Auto versioning** — PM tracks shipped items and auto-bumps the minor version every N items (configurable, default 10) when zero open bugs exist.
- **Status bar chaining** — SquidSquad no longer replaces your existing status bar. Your output appears first, SquidSquad appends as the last line.

### Fixed

- Status line parses context window usage with color coding.
- PowerShell boot scripts render Unicode correctly.
- PM check-in is non-blocking — prints a note and continues immediately.
- Setup no longer silently overwrites existing settings.
- Feature approval gates through full planning process.

---

## [0.5.1] — 2026-03-27

### Added

- **Structured setup prompts** — labeled fields with defaults, validation, and examples instead of freeform questions.
- **Single-sentence setup** — "Set up SquidSquad for kubex, BE only, 5 min interval" extracts all values and only prompts for gaps.
- **Bug/feature import during setup** — import from pasted text, local files, or connected tools (GitHub Issues, Jira, Linear).

### Fixed

- Setup and templates no longer hardcode specific role names — fully flexible team shapes.
- Boot scripts own the loop correctly.
- Pre-granted file permissions so agents never pause mid-cycle.

---

## [0.5.0] — 2026-03-27

Initial release.

- Flexible multi-agent coordination: user-defined dev roles + PM/QA
- Shared `.squidsquad/` folder as the coordination layer — no message queues, no servers
- All communication through append-only markdown tracker files committed to git
- Ralph Loop for each agent: pull, work, test, log, push, sleep
- Bug and feature tracking with severity, status flow, and discussion threads
- Any agent can file bugs to any team — no routing bottleneck
- Full setup wizard: generates folder structure, config, templates, boot scripts
- Boot scripts for bash/zsh and PowerShell
- Semver versioning with upgrade path for future releases
- SessionStart hook shows squid logo on every Claude Code boot
