## FEAT-SKILL-041 — Setup flow improvements: project context gathering + guided agent selection

- **Priority**: Medium
- **Status**: Pending
- **Owner**: skill-lead
- **Requested By**: human
- **Description**: Two improvements to the setup flow:

  **Part A — Project context gathering**: During setup, help the user create a comprehensive `CLAUDE.md` project context file so all agents (and normal Claude sessions) understand the codebase and the user's goals from day one. Detect whether a project-level `CLAUDE.md` already exists — if it does, skip (context already provided). If not, guide the user through context gathering: (1) **Auto-explore**: use agents to scan repo structure, key files, tech stack, patterns, and summarize findings, (2) **User interview**: ask about project goals, what they're trying to accomplish, current priorities, architecture decisions, team conventions, and any context that would help Claude work effectively. Combine both into a well-structured `CLAUDE.md` — not just a tech summary, but a full picture of what the user is building, why, and how they want to work.

  **Part B — Guided agent selection**: Replace the current freeform "list your dev agents" prompt (Step 1) with a guided walkthrough of all supported role types. For each role type SquidSquad supports, ask the user if they want one. Currently supported: dev agents (named, e.g. BE/FE/skill). Future roles (DM, Designer) should be wired in as they ship. Example flow: "Add a dev agent? → Name? → Add another? → Add a DM agent? → Add a designer agent?" Each role type uses its own template from `references/agent-instructions.md`.

- **Acceptance Criteria**:
  - [ ] Setup detects existing `CLAUDE.md` — if present, skips context gathering with a note
  - [ ] If no `CLAUDE.md`, runs auto-explore (subagent scans repo: file structure, manifest files, key directories, README) and presents findings
  - [ ] Asks user about project goals, current priorities, architecture decisions, coding conventions, and any other context
  - [ ] Combines auto-explored tech context with user-provided project context into a structured `CLAUDE.md`
  - [ ] `CLAUDE.md` includes sections: Project Overview, Goals & Priorities, Tech Stack, Architecture, Conventions, Key Files/Directories
  - [ ] User can skip context gathering entirely if they prefer to write CLAUDE.md themselves
  - [ ] Step 1 agent selection walks through each supported role type (dev, DM, designer) instead of freeform input
  - [ ] Each dev agent gets a name prompt (e.g. BE, FE, skill)
  - [ ] Non-dev roles (DM, designer) are yes/no — they use predefined templates
  - [ ] Setup only offers role types that have templates available (future-proof for new roles)
  - [ ] SKILL.md setup flow updated with both changes
  - [ ] Works for any project type (not just JS/TS)

### Discussion

> [2026-03-29 21:20] **skill-lead**: Filed per human request. Key design question: should auto-explore be a subagent or inline? Subagent is better for context isolation. Status: Pending — awaiting human approval.
> [2026-03-29 21:25] **skill-lead**: Updated per human feedback. Expanded scope: not just codebase scanning but also interviewing the user about their goals, priorities, and how they want to work. CLAUDE.md becomes a full project context doc, not just a tech summary. Added skip option.
> [2026-03-29 21:30] **skill-lead**: Updated again per human feedback. Added Part B — guided agent selection. Current Step 1 asks for dev agents as freeform list; should instead walk through each role type SquidSquad supports (dev, DM, designer) one at a time. Dev agents are named (BE/FE/etc.), other roles are yes/no. Human redirecting to PM for further discussion and approval.
> [2026-03-29 21:45] **pm/qa**: Human feedback on Part B role descriptions. Each role step should briefly describe the role so the user understands what they're adding:
> - **Dev agent**: All-around developer. Just give it a name (e.g. FE, BE, DevOps, skill). Can add multiple.
> - **Delivery Manager (DM)**: Owns the "last mile" of shipping — README updates, CHANGELOG entries, user-facing documentation. Takes over after PM verifies a feature, packages it for users.
> - **Designer**: (description TBD when FEAT-SKILL-027 is designed)
>
> **Dependency note**: DM role (FEAT-SKILL-035) and Designer role (FEAT-SKILL-027) are both Pending. Part B of this feature can only fully offer those roles once their templates exist. Options: (1) ship Part B with dev-only now, add DM/designer prompts as those features ship, or (2) wait until at least FEAT-035 ships. Recommend option 1 — ship dev-only guided selection now, wire in new roles as they land.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
