## FEAT-SKILL-047 — Cross-clone health detection via local file reads + guided agent setup

- **Priority**: High
- **Status**: Shipped
- **Requested By**: human
- **Description**: Replace the heartbeat branch system (FEAT-SKILL-033) with direct cross-clone file reads for real-time agent health detection. Each agent's clone path is stored in a gitignored `.squidsquad/.local-config` file. Statusline and PM read other agents' `current-state` files directly via absolute path — instant, zero API calls, real-time. Setup flow is enhanced to guide the user through cloning repos and launching agents in new terminals.
- **Philosophy**: GitHub (git) is the communication bus and audit trail for all content. This is the one exception — purely operational status reads that need to be real-time. No content, no decisions, no audit trail needed.
- **How It Works**:
  - `.squidsquad/.local-config` (gitignored, machine-specific) stores absolute paths to each agent's clone:
    ```markdown
    ## Agent Paths
    - **pm**: D:\Dev\SquidSquad-PM
    - **skill**: D:\Dev\SquidSquad-Skill
    ```
  - Statusline reads other agents' `current-state` file mtime for health icons and timer
  - PM Step 7 reads other agents' `current-state` for health check
  - No background process, no git fetch, no GitHub API
- **Guided Setup Flow**:
  - When adding a new agent during setup, ask for a path (or suggest a default)
  - Clone the repo to that path (`git clone <repo-url> <path>`)
  - Write the path to `.local-config`
  - Open a new terminal at that path
  - Run the boot script in the new terminal
  - User goes from "I want a skill agent" to "skill agent is running" in one flow
- **Replaces**: heartbeat.sh, heartbeat branches, `git fetch origin heartbeat/<role>`, Heartbeat Interval Seconds config
- **Health Icons**: 🦑 healthy, 👻 stalled (no update > 2x interval), ❓ unknown/no data (replaces 🥚)
- **Acceptance Criteria**:
  - [ ] `.squidsquad/.local-config` file format defined and gitignored
  - [ ] Setup flow asks for agent clone paths and writes to `.local-config`
  - [ ] Setup clones repo to specified path for new agents
  - [ ] Setup opens new terminal and runs boot script for new agent
  - [ ] Statusline reads cross-clone `current-state` files for health and timer
  - [ ] PM Step 7 reads cross-clone `current-state` for health check (no git fetch)
  - [ ] heartbeat.sh removed, boot scripts no longer launch heartbeat process
  - [ ] Heartbeat Interval Seconds removed from config.md
  - [ ] Health icons: 🦑 healthy, 👻 stalled, ❓ unknown (replaces 🥚)
  - [ ] Stale threshold: 2x iteration interval
  - [ ] Graceful fallback if `.local-config` missing or path unreachable — show ❓
  - [ ] Works on Windows (PowerShell) and Unix (bash)
  - [ ] SKILL.md, agent-instructions.md, README updated

### Discussion

> [2026-03-31 00:00] **pm/qa**: Filed from human request. Originally proposed GitHub commit statuses, but human raised concerns about consuming API rate limits (user may use GH account for other things). Pivoted to cross-clone file reads via configured paths.
> [2026-03-31 00:20] **pm/qa**: Human proposed: during setup, ask for agent path, clone repo there, open terminal, run boot script — full guided flow. Philosophy: GitHub is the bus for all content/audit trail. Local file reads are the one exception, purely for real-time operational health.
> [2026-03-31 00:25] **pm/qa**: Human approved approach. Health icons: ❓ replaces 🥚 for unknown/no data.
> [2026-03-31 00:45] **pm/qa**: Rewrote feature with updated scope. Research from original commit-status approach still partially relevant (file impact analysis, what to remove). Status → Planning.
> [2026-03-31 01:00] **pm/qa**: CONTEXT.md and TEST-PLAN.md created (23 TCs, 15 smoke, 9 regression risks). Status → Approved.
> [2026-03-31 00:30] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-31 00:45] **skill-lead**: Implementation complete. Replaced heartbeat branch system with cross-clone file reads via `.local-config`. Changes: (1) statusline.sh reads cross-clone current-state files for health icons (🦑/👻/❓), stale threshold 2x interval. (2) PM Step 7 uses cross-clone reads instead of git fetch. (3) Deleted heartbeat.sh from references/ and .squidsquad/. (4) Removed heartbeat launch blocks from all 6 boot scripts (4 live + templates). (5) Removed Heartbeat Interval Seconds from config. (6) Updated SKILL.md setup/upgrade flows. (7) Updated README. (8) .local-config added to .gitignore. All smoke tests passing. Status → Pending Test.
> [2026-03-31 01:35] **pm/qa**: QA found 4 defects — back to In Progress:
> - DEF-1 (BLOCKING): Live pm/CLAUDE.md line 735 still references heartbeat branches and 🥚 icon — not updated to match template.
> - DEF-2 (MEDIUM): SKILL.md line 710 references 🥚 instead of ❓.
> - DEF-3 (MEDIUM): SKILL.md setup .gitignore template missing `.squidsquad/.local-config`.
> - DEF-4 (MAJOR): SKILL.md setup flow has no guided agent clone + .local-config creation step (locked decision in CONTEXT.md).
> Status → In Progress.
> [2026-03-31 01:45] **skill-lead**: All 4 defects fixed: (DEF-1) Updated pm/CLAUDE.md status line section — replaced heartbeat/🥚 with cross-clone/❓ description. (DEF-2) Fixed SKILL.md 🥚→❓ in status line spec. (DEF-3) Added `.squidsquad/.local-config` to SKILL.md .gitignore template. (DEF-4) Added Step 5d (Guided Agent Clone Setup + .local-config) to SKILL.md setup flow — asks for clone path, clones repo, writes .local-config, offers to open terminal. Status → Pending Test.
> [2026-03-31 02:15] **pm/qa**: QA re-verified — all 4 defects confirmed fixed. No 🥚 in pm/CLAUDE.md or SKILL.md, .local-config in gitignore, Step 5d guided setup present, heartbeat.sh removed, ❓ icon in statusline. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
