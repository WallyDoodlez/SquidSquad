## FEAT-SKILL-052 — Add agent role command: clone, configure, and boot any role from PM

- **Priority**: High
- **Requested By**: human
- **Status**: Pending
- **Depends On**: FEAT-SKILL-030 (sub-skill plugin system)
- **Description**: A generic command (e.g. `/squidsquad-add-role`) that lets the human add any agent role (DM, future roles) to a running SquidSquad project. The human tells PM "add a DM at D:\path" and the system handles everything: clone (if needed), template setup, `.local-config` registration, and auto-boot in a new terminal.
- **Acceptance Criteria**:
  - [ ] Generic — works for any role (DM, or future sub-skill roles), not hardcoded to DM
  - [ ] Smart clone detection: if target path already has a git clone, skip cloning; otherwise clone the repo
  - [ ] Sets up `.squidsquad/<role>/` with the correct template files for the role
  - [ ] Registers the clone path in `.squidsquad/.local-config`
  - [ ] Opens a new terminal and boots the agent automatically
  - [ ] Updates `config.md` agent list if needed
  - [ ] Works on Windows (primary) and Unix

### Discussion

> [2026-04-02 00:15] **pm/qa**: Filed from human request. Human wants to tell PM "add a DM" + specify a path, and have the system clone, configure, and boot. Confirmed: generic (any role), smart clone detection (skip if exists), auto-start in new terminal. Blocked on FEAT-SKILL-030 (sub-skill plugin system). Status: Pending.
