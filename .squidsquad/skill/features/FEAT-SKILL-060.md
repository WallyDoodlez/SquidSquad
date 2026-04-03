## FEAT-SKILL-060 — OS-level notifications for human attention when required

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Pending
- **Description**: Agents should be able to trigger OS-level notifications (toast/banner notifications on Windows, macOS, Linux) when they need human attention. Use cases:

  1. **PM Phase 2 Discussion**: PM needs the human to answer questions during feature intake
  2. **Designer interactive session**: Designer is ready for a design session with the human
  3. **QA failure**: QA found test failures that need human review
  4. **Agent stalled**: PM detects a stalled agent and needs human intervention
  5. **Feature approved/shipped**: Informational notification when milestones are reached
  6. **Approval gates**: Any point where the pipeline is blocked waiting for human input

  **Implementation considerations:**
  - Cross-platform: Windows (PowerShell toast), macOS (osascript), Linux (notify-send)
  - Notification levels: urgent (needs action now), informational (FYI)
  - Should not be spammy — only trigger when genuinely blocked on human input
  - Could use a common sub-skill so any agent can trigger notifications
  - Respect quiet hours / do-not-disturb if detectable

- **Acceptance Criteria**:
  - [ ] Agents can trigger OS-level notifications via a common mechanism
  - [ ] Works on Windows, macOS, and Linux
  - [ ] Notifications include: which agent, what's needed, which feature/bug ID
  - [ ] Urgent vs informational notification levels
  - [ ] Rate-limited — no notification spam
  - [ ] Common sub-skill so all agents can use it
  - [ ] Configurable: can be disabled in config.md

### Discussion

> [2026-04-02 11:15] **pm/qa**: Filed from human request. OS-level notifications when agents need human attention — approval gates, design sessions, QA failures, stalled agents. Cross-platform, rate-limited, configurable. Status: Pending — awaiting human approval.
