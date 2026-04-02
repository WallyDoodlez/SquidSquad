## FEAT-SKILL-053 — PM auto-boots entire team on startup

- **Priority**: High
- **Requested By**: human
- **Status**: Pending
- **Depends On**: FEAT-SKILL-052 (add agent role command)
- **Description**: When PM starts up, it reads `.local-config` and `config.md` and ensures every agent on its team is running. PM is the orchestrator — it should boot the whole squad, not just itself.
- **Acceptance Criteria**:
  - [ ] On startup, PM reads `.local-config` and checks each agent's `current-state` mtime
  - [ ] If agent is already running (recent mtime), skip — don't double-boot
  - [ ] If agent is not running, open a new terminal and boot it at the clone path
  - [ ] If an agent is in `config.md` but missing from `.local-config`, warn: "X is configured but has no clone path — run `/squidsquad-add-role` to set it up"
  - [ ] If an agent fails to start (bad path, clone missing, terminal fails), PM blocks — does not continue the Ralph Loop until resolved
  - [ ] Works on Windows (primary) and Unix
  - [ ] Boot happens before the first Ralph Loop cycle

### Discussion

> [2026-04-02 00:20] **pm/qa**: Filed from human request. PM should boot its entire team on startup using `.local-config` paths. Skip already-running agents (check mtime). Warn on agents missing from `.local-config`. Block if any agent fails to start — human confirmed blocking behavior. Depends on FEAT-SKILL-052 (add-role command). Status: Pending.
