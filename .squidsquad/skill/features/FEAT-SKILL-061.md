## FEAT-SKILL-061 — Named sessions for easier identification in Claude Code remote

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Pending
- **Description**: When multiple SquidSquad agents run as Claude Code remote sessions, they are hard to distinguish in the session list. Each agent session should have a recognizable name that includes the role and project, making it easy to identify which session is which.

  **Examples:**
  - `SquidSquad PM — SquidSquad`
  - `SquidSquad Skill-Lead — SquidSquad`
  - `SquidSquad DM — SquidSquad`
  - `SquidSquad Designer — SquidSquad`
  - `SquidSquad QA — SquidSquad`

  **Implementation considerations:**
  - Claude Code may support session naming via CLI flags or configuration
  - Boot scripts could set the session name when launching the agent
  - Should include: role name + project name (from config.md)
  - If Claude Code doesn't support native session naming, explore terminal title setting as fallback (relates to FEAT-SKILL-036 which is On Hold)

- **Acceptance Criteria**:
  - [ ] Each agent session has a distinct, human-readable name
  - [ ] Name includes role and project name
  - [ ] Set automatically by boot scripts during agent launch
  - [ ] Works with Claude Code remote session list
  - [ ] Fallback to terminal title if native naming not supported

### Discussion

> [2026-04-02 11:20] **pm/qa**: Filed from human request. Named sessions for Claude Code remote — each agent session identifiable by role + project. Status: Pending — awaiting human approval. Note: may overlap with FEAT-SKILL-036 (boot script terminal title, On Hold).
