# Changelog

All notable changes to SquidSquad will be documented here.

---

## [0.10.0] — 2026-04-04

### Added

- #16 — **Vault Phase 2**: You can now search the vault by tag, type, or keyword. Notes auto-validate on save (broken links, missing fields). Agents update existing notes surgically instead of rewriting them.
- #30 — **Common sub-skills**: Shared behaviors (git commits, bug filing, discussion protocol, iteration logs) are now extracted into reusable sub-skills — cleaner templates, consistent behavior across all agents.
- #31 — **Sub-skill names in status bar**: Line 2 of the status bar now shows which sub-skill is active (e.g. `git-commit — Pushing changes...`), making agent behavior transparent during operation.

### Fixed

- #23 — Agent CLAUDE.md bootstrappers now regenerate correctly after GitHub Issues migration.
- #24 — Status bar reads bug/feature counts from GitHub Issues instead of stale local files.
- #25 — Agent instructions no longer reference old local markdown tracker.
- #26 — SKILL.md architecture diagram updated to show GitHub Issues as tracker.
- #27 — README folder structure now includes all agent types (DM, Designer) with templates and boot scripts.
- #28 — Dev agent correctly prioritizes bugs over features and blocks feature pickup when open bugs exist.
- #32 — SKILL.md Bug Flow uses correct status labels matching the Label Taxonomy.
- #33 — SKILL.md Ralph Loop descriptions reference `gh issue list` instead of old INDEX.md files.
- #34 — Feature workflow now includes "Planned" state between Planning and Approved, giving you a clear approval gate.
- #36 — Improvement scan now correctly classifies findings as bugs or features instead of filing everything as a feature.
- #37 — SKILL.md no longer refers to PM/QA as a combined role — PM and QA are separate agents.
- #38 — SKILL.md architecture diagram shows all five agent roles (Dev, Designer, QA, PM, DM).
- #39 — SKILL.md Label Taxonomy corrected to show actual label names used on GitHub Issues.
- #40 — SKILL.md Feature Flow includes the new "planned" status with corrected descriptions.
- #41 — SKILL.md config template updated to current version and field structure.
- #42 — SKILL.md setup no longer creates obsolete markdown tracker directories.
- #43 — SKILL.md setup now generates QA and Designer directories, bootstrappers, and boot scripts.
- #46 — Status bar correctly labels PM and QA as separate roles with QA-specific display logic.
- #47 — Vault project note updated to reflect current version and GitHub Issues tracker.

---

## [0.9.0] — 2026-04-04

### Added

- **Sub-skill architecture** (FEAT-SKILL-030): Decomposed monolithic agent templates into composable sub-skills — main skill as orchestrator, role sub-skills, common sub-skills (auto-included by all roles), and role-specific sub-skills. Build-time composition via manifest. Architecture Version 1.
- **Suppress PM cycles during planning** (FEAT-SKILL-058): PM performs silent pull + health check during active planning phases instead of full noisy cycles. Auto-resumes when planning artifact is written.
- **Designer agent template** (FEAT-SKILL-027): New agent type for design-to-code workflows. Interactive design sessions with human, feasibility assessment, structured design specs (component specs, tokens, layout specs). Supports external design tools (Figma, Google Stitch, etc.) via MCP. `Design` field routing in PM feature intake.
- **Separate QA from PM** (FEAT-SKILL-043): Split PM/QA into distinct PM (human-facing coordinator, feature intake, backlog) and QA (E2E tests, bug verification, feature testing, health checks) agents. QA auto-added when dev/designer present. PM Lean template when QA exists.
- **Self-improvement scanning** (FEAT-SKILL-063): Agents scan the target project for improvements during quiet cycles — dev finds code issues, QA finds test gaps, designer spots design inconsistencies, DM catches doc gaps, PM identifies process improvements. Rate-limited, PM-routed. Config toggle: `Improvement Scanning`.
- **Vault memory layer Phase 1** (FEAT-SKILL-029): Git-tracked Obsidian-compatible shared memory vault (`.squidsquad/vault/`). PARAG structure (Projects, Areas, Resources, Archives, Galaxy). Vault-create protocol, BRIEFING.md, wikilinks, YAML frontmatter, changelogs per note. All agents have R/W access.
- **Agent personalities (SOUL.md)** (FEAT-SKILL-059): Distinct personality per role — PM diplomat, QA skeptic, dev pragmatist, designer creative, DM closer. Defines tone, communication style, boundaries, decision-making. Composed as first include in every template.
- **GitHub Issues as tracker** (FEAT-SKILL-068): Replaced internal markdown tracker files with GitHub Issues. Labels for type, priority, status, role. `gh` CLI for all CRUD. Discussion entries as Issue comments. Status transitions as label changes. Prerequisite for going public.

### Fixed

- PM no longer attempts to ship features with open QA gaps (BUG-SKILL-039).
- Dev agent now picks up QA-rejected In Progress features (BUG-SKILL-040).

---

## [0.8.0] — 2026-03-31

### Added

- **Delivery Manager (DM) role** (FEAT-SKILL-035): New optional agent role that owns the "last mile" of shipping — user-facing docs, CHANGELOG, version bumps, git tags, releases. Feature lifecycle gains `Pending Ship` status between `Pending Test` and `Shipped`. DM is optional: when absent, PM automatically activates delivery capabilities (Step 6d fallback). DM presence detected by `dm/` directory existence — no config flag needed. Includes `delivery:skip` tag for internal-only features.
- **Granular status phases with item names** (FEAT-SKILL-044): All agents write distinct phases with specific item IDs to `current-state`. PM gets `researching`, `discussing`, `test-planning` phases for Feature Intake. Dev phases include item IDs (e.g. `triaging|Fixing BUG-SKILL-029...`). Per-item updates during batch operations.
- **Overdue emoji on status bar** (FEAT-SKILL-045): Shows `⏰ +Nm` when an agent's cycle exceeds the iteration interval. Triggers immediately at boundary, no grace period. All agent roles.
- **Bug discussion flow** (FEAT-SKILL-046): PM now investigates root cause and presents problem + proposed fix to human before filing bugs to dev tracker. Human can discuss and steer the fix approach. Non-blocking — PM continues loop if human hasn't responded.
- **Cross-clone health detection + guided setup** (FEAT-SKILL-047): Replaces heartbeat branches with direct file reads across agent clones. Agent paths stored in gitignored `.local-config`. Setup guides user through cloning repos and launching agents. Health icons updated: 🦑 healthy, 👻 stalled, ❓ unknown (replaces 🥚). Heartbeat.sh removed.
- **Philosophy section in README** (FEAT-SKILL-048): Documents core design principles — git as the communication bus, complete audit trail, Discussion sections as project archive, no external dependencies for coordination.

### Fixed

- PM template now includes `delivery:skip` guidance for internal-only features (BUG-SKILL-032).
- DM role is optional with full PM delivery fallback when absent (BUG-SKILL-033).
- Statusline only shows DM health icon when `dm/` directory exists (BUG-SKILL-034).
- Overdue timer no longer shows stale +183m on quiet cycles — reads `current-state` mtime instead of iteration file (BUG-SKILL-035).
- Current-state file writes use atomic pattern (`echo > tmp && mv`) to prevent stale statusline from file locking races (BUG-SKILL-031).

---

## [0.7.0] — 2026-03-30

### Added

- **Granular status phases with item names** (FEAT-SKILL-044): All agents now write distinct, specific phases to their `current-state` file including the item ID being worked on. PM gets new phases: `researching`, `discussing`, `test-planning` for Feature Intake steps. Dev phases include item IDs (e.g. `triaging|Fixing BUG-SKILL-029...`, `implementing|🔨 FEAT-SKILL-037...`). Status bar telegraphs exactly what each agent is doing in real time. Per-item updates during batch operations.
- **Overdue emoji on status bar** (FEAT-SKILL-045): When an agent's Ralph Loop cycle runs longer than the configured interval, the statusline shows `⏰ +Nm` (overdue by N minutes) instead of the normal countdown. Triggers immediately at the interval boundary with no grace period. Works for all agent roles (PM, dev, DM).
- **Current-state atomic writes** (BUG-SKILL-031): Agent `current-state` file writes now use atomic `echo > tmp && mv tmp file` pattern to prevent stale statusline from file locking race conditions on Windows.

### Fixed

- Boot scripts now include heartbeat launch and current-state initialization — previously stale after FEAT-033 and FEAT-037 shipped (BUG-SKILL-027).
- README.md no longer references old `.active-role` file-based auto-boot mechanism — updated to reflect `--append-system-prompt` flow (BUG-SKILL-028).
- All boot scripts and SKILL.md templates use correct `--enable-auto-mode` flag instead of invalid `--permission-mode auto` (BUG-SKILL-029).
- Dev agent grep pattern for open bugs now matches markdown bold formatting (`**Status**: Open`) — previously skipped all open bugs silently (BUG-SKILL-030).

---

## [0.6.0] — 2026-03-29

### Added

- **Externalized agent templates** (FEAT-SKILL-017): Agent CLAUDE.md files are no longer 200+ line monoliths. Setup now generates shared template files in `.squidsquad/templates/` (e.g. `dev-agent-fe.md`, `pm-agent.md`) with all placeholders substituted at build time. Each agent's `.squidsquad/[role]/CLAUDE.md` is a small ~20-line bootstrapper containing role config and a Read instruction pointing to the template. Benefits: templates maintained in one place, upgrades only regenerate `templates/` without touching bootstrappers, much smaller per-agent files, cleaner separation of config and instructions. Upgrade auto-detects inline CLAUDE.md files (by checking for `## The Ralph Loop` heading) and migrates them to bootstrapper + template format.
- **Open planning artifacts in VS Code** (FEAT-SKILL-024): After each planning phase (Research, Discussion, Planning), PM offers to open the artifact in VS Code via `AskUserQuestion` with three options: "Yes, open in VS Code", "No thanks", "Never ask again". "Never ask again" persists to `config.md` (`Open Artifacts in Editor: no`) and suppresses all future prompts. Falls back to printing the file path if `code` CLI is not available.
- **Status bar redesign — Emoji Rich** (FEAT-SKILL-031): Complete rewrite of `statusline.sh`. Replaces ANSI-only design with expressive emoji indicators. Dev bar shows active task (🔨) or backlog (🐛/⭐/✅), version, context (🧠/🧠🔥/🧠💀 with colored text), countdown (🔄/🔜), git sync (↑N/↓N). PM bar adds ship counter (📦 with 🚀 near bump), planning phase (📋), and a second line with team health icons (🦑/👻/🥚) plus time-based rest nudge (🌙/😴/🛏️). Iteration number dropped; "time since" replaced by countdown only.
- **Externalized statusline.sh** (BUG-SKILL-021): `statusline.sh` moved from inline code block in SKILL.md to `references/statusline.sh` as a standalone source file. Setup copies it to `.squidsquad/statusline.sh`; upgrade regenerates from the source. Consistent with the agent template externalization pattern.
- **Heartbeat branches for agent health detection** (FEAT-SKILL-033): Replaces git-commit-based health detection with lightweight heartbeat branches. Each agent's boot script launches `heartbeat.sh` as a background process that force-pushes an orphan `heartbeat/<role>` branch every N seconds (configurable, default 10s) using `git mktree` + `git commit-tree` + `git push -f` — no checkout, no working tree impact, no commits on main. PM reads heartbeat timestamps to detect agent liveness. Solves false-stalled problem where agents on quiet cycles appeared dead. Works across machines.
- **Current step + contextual hints in status bar** (FEAT-SKILL-037): Agents write their current Ralph Loop step to `.squidsquad/<role>/current-state` at each phase change. Status bar line 2 shows the active step (emoji + description, truncated at 60 chars) or rotating contextual hints when idle. Hints are human-facing prompts (e.g. "Msg me any time to file a bug"), rotate every 60 seconds, and are phase-aware. Hint pools defined in `references/hints-dev.txt` and `references/hints-pm.txt`, copied during setup. PM health icons moved from line 2 to line 1 (right-aligned). Boot scripts clear and initialize current-state on startup.
- **Emoji prefixes on status bar line 2** (FEAT-SKILL-038): Hints now display with a 💡 prefix and progress/phase indicators with a 🚧 prefix, making the two content types visually distinct at a glance. Truncation adjusted to 58 chars to account for emoji width.
- **Change loop interval on the fly** (FEAT-SKILL-039): New `/squidsquad-interval <Nm>` slash command changes the Ralph Loop interval for all agents without restarting. Updates `config.md`, cancels the old cron, creates a new one. Other agents detect the change via Step 1d (Interval Sync) at their next cycle start. Minimum 5 minutes enforced.
- **Upgrade & migration paths in planning** (FEAT-SKILL-034): Feature Intake Process now always includes upgrade/migration analysis. Phase 1 research subagent prompt requires analyzing upgrade impact. RESEARCH.md template has a dedicated "Upgrade & Migration" section (new config values, new files, template changes, upgrade steps, graceful degradation). CONTEXT.md template has a required "Upgrade Path" section. TEST-PLAN.md subagent prompt includes upgrade verification tests. Even trivial features must state "N/A — no upgrade impact."
- **Smart resume for interrupted planning** (FEAT-SKILL-023): When the Feature Intake Process resumes after an interruption (context reset, PM restart), each phase checks if its output artifact already exists. Uncommitted artifacts are auto-skipped. Committed artifacts with no code changes since are auto-reused. Committed artifacts with code changes trigger an `AskUserQuestion` prompt to re-run or reuse. Applies to RESEARCH.md, PHASE2-PREP.md, CONTEXT.md, and TEST-PLAN.md.
- **Explicit approval gate after Phase 2** (FEAT-SKILL-040): After Phase 2 discussion completes and CONTEXT.md is written, PM now presents a summary of all locked decisions and asks the human to confirm via `AskUserQuestion` before proceeding to Phase 3 (test plan). Options: "Approve — proceed to test plan", "More discussion needed" (re-opens questions), or "Reject this feature" (sets status to Rejected).
- **SquidSquad only activates via boot scripts** (FEAT-SKILL-042): Auto-boot now uses `--append-system-prompt "SQUIDSQUAD_ROLE=<role>"` instead of checking `.active-role` file. Normal `claude` sessions in a SquidSquad repo no longer trigger auto-boot. Boot scripts still write `.active-role` for statusline use, but CLAUDE.md only checks the system prompt signal — no cross-terminal leakage.

### Fixed

- PM no longer asks "approve?" immediately after filing a feature — now predicts user intent, surfaces questions, and invites discussion first. Approval only offered after full planning process completes (BUG-SKILL-024).
- Status bar line 2 now shows full squad (PM + all dev agents) instead of dev agents only (BUG-SKILL-022).
- Status bar git commands now have 2-second timeouts to prevent line 2 disappearing during concurrent git operations (BUG-SKILL-023).

- Boot logo in `settings.json` startup hook and all SKILL.md boot script templates now uses the canonical README squid design (BUG-SKILL-019).
- Generated `skill/CLAUDE.md` and `pm/CLAUDE.md` now include cycle start/complete markers (`[🦑] ---- cycle N started/complete ----`) and feature pickup marker, matching the template spec (BUG-SKILL-018).
- README.md updated with 5 missing shipped features: Subagent Delegation, Status Bar Chaining, Auto Versioning, Externalized Agent Templates, Open Planning Artifacts in VS Code. Quiet Cycle Skipping updated to mention silent output (BUG-SKILL-020).

---

## [0.5.2] — 2026-03-28

### Added

- Status line for all SquidSquad agents via Claude Code's `statusLine` setting. Shows squid emoji (green ANSI), role label, iteration number, backlog pulse (open bugs + features), and time since last cycle. PM/QA status line additionally shows agent health — green squid for recently active agents, red squid with `✖` for silent agents.
- `.squidsquad/statusline.sh` generated during setup (Step 5b) and referenced from `.claude/settings.json`.
- Dev agent and PM/QA CLAUDE.md templates now document status line behavior.
- Ralph Loop cycle markers: agents print `[squidsquad] ---- cycle N started/complete at HH:MM:SS ----` for visible cycle boundaries in scrollback.
- Status line shows next-cycle countdown (e.g. `next in ~2m`) when within the interval window.
- PM/QA explicitly prohibited from implementing code — must always file bugs/features to dev agents.

- Agent health detection via `git log` commit prefixes — replaces local iteration-file-based health check. PM status line and new Ralph Loop Step 7 both use `git log --since` filtered by agent commit prefix (e.g. `skill:`, `fe:`) to detect stalled agents. Works across separate clones.
- Commit prefix convention documented in Git Protocol: every commit must start with `role:` prefix.
- Context pressure check (Step 1b): agents check `context_window.used_percentage` at cycle start. If above threshold (configurable in `config.md`, default 80%), they save state, commit, and exit for a fresh context.
- Working state file (`.squidsquad/[role]/working-state.md`): agents persist current task, completed steps, and remaining work. Read on startup (Step 1c) to resume mid-task after context reset. Cleared on task completion.
- `config.md` now includes `Context Pressure` section with configurable threshold.
- Annotated step markers: every Ralph Loop step prints a `[squidsquad]` prefixed status line (e.g. `[squidsquad] Pulling latest...`, `[squidsquad] Triaging bugs...`). Key sub-actions get their own markers too. Makes SquidSquad activity easy to scan in terminal scrollback.
- Iteration log retention: agents keep the last 20 iteration files and delete older ones. Git history preserves them.
- Quiet cycle detection: agents skip iteration log and commit when no work was done. Iteration counter only increments on productive cycles.
- **PR-based approval flow** (optional): dev agents create PRs via `gh` CLI instead of pushing to main. Human reviews and merges on GitHub. PM monitors PR state and syncs comments/decisions back to tracker Discussion. Opt-in at setup or via `config.md` `PR Flow: yes`.
- **GitHub Issues ingestion** (optional): PM auto-ingests open GitHub Issues into agent trackers each cycle via `gh issue list`. Issues are classified as bugs/features, routed to the right agent, and tracked with `GitHub Issue #N` references. Shipped items auto-close the original issue. Opt-in at setup or via `config.md` `GitHub Issues Ingestion: yes`.
- `/squidsquad-status` command: type in any Claude session to get a dashboard — agent health, open bugs/features per agent, recently shipped items.
- README.md fully rewritten to reflect current feature set, generic `[role]` examples, and all v0.5.2 features.
- **Deep 5-phase Feature Lifecycle**: replaces shallow intake process. Research → Discussion → Planning → Execution → QA. PM spawns research agents, asks targeted questions with WHY, creates test plans. Dev reads planning artifacts. PM executes test cases before shipping. Light mode for trivial features. `Rejected` status for features research shows are bad ideas.
- Agents now use `/loop [INTERVAL]m` for reliable cycling instead of self-managed sleep loops.
- **Auto versioning**: PM tracks shipped items and auto-bumps minor version every N items (configurable, default 10) when zero open bugs exist. Creates git tag, updates config.md + SKILL.md + CHANGELOG.md. Bypasses PR flow.
- **Status bar chaining**: SquidSquad no longer replaces the user's entire status bar. Setup saves existing `statusLine` command to `.squidsquad/.user-statusline`, and `statusline.sh` chains it — user's output appears first, SquidSquad line appends as the last line. Silent 1-second timeout fallback.

### Fixed

- Status line now parses JSON stdin for context window usage (color-coded: dim < 70%, yellow 70-90%, red > 90%).
- PowerShell boot scripts render Unicode correctly via `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`.
- Boot scripts no longer use `-p` and `--continue` flags — replaced with positional arg for interactive sessions.
- PM/QA Step 2 (Check In With Human) is now non-blocking — prints a note and continues immediately.
- Setup Step 7 no longer silently overwrites existing `statusLine` or `permissions.allow` — prompts user to replace or skip.
- Phase 2 (Discussion) now presents questions one at a time with (a)(b)(c)(d) choice format instead of dumping all questions at once.
- Feature approval now gates through `Planning` status — `Pending` → `Planning` → `Approved`. PM must complete the full intake process (Research → Discussion → Planning) before a feature reaches `Approved` and becomes available to dev agents.
- Step markers now use `[🦑]` squid emoji prefix instead of plain `[squidsquad]` text — visually distinct in terminal scrollback. (ANSI escape codes removed — Claude Code renders them as raw text.)

---

## [0.5.1] — 2026-03-27

### Changed

- Setup Step 1 now uses structured prompts with labels, descriptions, defaults, and validation rules for each field. Supports quick-start mode where all details can be provided in a single sentence. Displays a confirmation summary before proceeding.
- Setup now offers to import existing bugs and features after gathering project details. Supports three sources: pasted text, local file path, or connected MCP tools (GitHub Issues, Jira, Linear, etc.). Imported items are normalized into standard tracker format, routed to the correct dev agent, and seeded with Discussion notes. Step 6 updated to handle imported items alongside manual seed items.

### Fixed

- Opening paragraph, architecture diagram, and Step 9 confirm message in SKILL.md no longer hardcode "three agents" or FE/BE roles — they now use dynamic `[Role]` and `[N]` placeholders matching the flexible team shape introduced in v0.5.0.
- Ralph Loop section collapsed from separate FE/BE loops into a single generic `[Role] Lead` template. PM/QA loop and setup Steps 4/6 updated to use `[role]/` paths instead of hardcoded `fe/`/`be/`.
- Boot scripts (`start-[role].sh/.ps1`) now own the loop via `while true` in the shell — each `claude -p` invocation handles one Ralph Loop cycle. Previously the loop was only described in CLAUDE.md but `claude -p` exits after one turn.
- Console now shows cycle number and timestamp between iterations so the agent's activity is visible.
- `.claude/settings.json` pre-grants `Edit`/`Write` permissions on `.squidsquad/**` and git commands so agents never pause mid-cycle to ask for write permission.
- `SKILL.md` Step 7 settings.json template updated to include the permissions block for all future setups.
- Opening paragraph, ASCII architecture diagram, and Step 9 confirm message no longer hardcode FE/BE three-agent setup — now use generic `[role]`/`[N]` placeholders matching the flexible team shape introduced in v0.5.0.
- Ralph Loop section consolidated from two hardcoded FE/BE loops into a single generic `[role] Lead` loop. PM/QA loop updated to reference `[role]/` paths instead of hardcoded `fe/`/`be/`.

### Added

- Structured setup prompts: Step 1 now uses labeled fields with defaults, validation, and examples instead of freeform questions.
- Single-sentence setup support: "Set up SquidSquad for kubex, BE only, 5 min interval" extracts all values and only prompts for gaps.
- Confirm-or-override flow: all pre-filled values shown at once for the user to review before proceeding.

---

## [0.5.0] — 2026-03-27

Initial release.

### Core

- Flexible multi-agent coordination model: user-defined dev roles + PM/QA
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
