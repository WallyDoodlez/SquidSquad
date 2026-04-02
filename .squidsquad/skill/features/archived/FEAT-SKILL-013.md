## FEAT-SKILL-013 — Auto-ingest GitHub Issues into tracker on each PM cycle

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: **Optional, configurable at setup.** The PM/QA Ralph Loop should check the repo's GitHub Issues on every cycle using `gh issue list`. New issues that haven't already been ingested get triaged and filed into the appropriate agent's bug or feature tracker. This closes the loop between external contributors/users filing issues on GitHub and the SquidSquad agents picking them up automatically. This feature is opt-in — setup Step 1 should prompt: "Auto-ingest GitHub Issues? (requires `gh` CLI) [y/N]". The choice is stored in `config.md` as `GitHub Issues Ingestion: enabled/disabled`. When disabled, PM skips the ingestion step.

  **Flow:**
  1. PM runs `gh issue list --state open --json number,title,labels,body` each cycle
  2. For each open issue, PM checks if it's already been ingested (search tracker Discussion for `GitHub Issue #N`)
  3. If new: PM reads the issue body, determines if it's a bug or feature request, routes to the correct dev agent's tracker
  4. Files it with a Discussion entry: `> [DATE] **pm/qa**: Ingested from GitHub Issue #N. [link]`
  5. Labels on the issue can hint at routing (e.g. `bug`, `enhancement`, `frontend`, `backend`)
  6. If the issue is ambiguous, PM files it as a bug to the first dev agent and notes the ambiguity
  7. When a tracked bug/feature is shipped, PM adds a comment to the original GitHub Issue and closes it via `gh issue close`

- **Acceptance Criteria**:
  - [ ] PM Ralph Loop includes a new step that runs `gh issue list` to fetch open issues
  - [ ] New issues are detected by checking tracker Discussion for prior ingestion
  - [ ] Issues are classified as bug or feature based on labels and content
  - [ ] Issues are routed to the correct dev agent's tracker based on labels or content heuristics
  - [ ] Each ingested item gets a Discussion entry referencing the GitHub Issue number and URL
  - [ ] When a tracked item is shipped, PM comments on and closes the GitHub Issue
  - [ ] PM/QA CLAUDE.md template updated with the ingestion step
  - [ ] SKILL.md documents the GitHub Issues integration
  - [ ] Works with `gh` CLI — documented as a prerequisite
  - [ ] Graceful fallback if `gh` is not available (skip the step, log a note)
  - [ ] Setup Step 1 includes a prompt: "Auto-ingest GitHub Issues? (requires `gh` CLI) [y/N]"
  - [ ] Choice stored in `config.md` as `GitHub Issues Ingestion: enabled/disabled`
  - [ ] When disabled, PM skips the ingestion step entirely
  - [ ] Can be toggled post-setup by editing `config.md`

### Discussion

> [2026-03-28 03:45] **pm/qa**: Filed from human request. Bridges GitHub Issues and SquidSquad trackers — PM auto-ingests new issues each cycle, closes them when shipped. Status: Pending — awaiting human approval.
> [2026-03-28 03:55] **pm/qa**: Human feedback: this must be opt-in, same as FEAT-SKILL-012. Setup prompts for it, config stores the choice. When disabled, PM skips the step.
> [2026-03-28 04:00] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 04:05] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 04:15] **skill-lead**: Complete. Added setup prompt (field 10), config template entry, PM Ralph Loop Step 7b with ingestion logic, close-on-ship behavior, graceful `gh` fallback. Updated SKILL.md, references/agent-instructions.md, generated pm/CLAUDE.md, config.md, CHANGELOG. Status → Pending Test.
> [2026-03-28 04:10] **pm/qa**: QA verified — all criteria pass. Opt-in, PM Step 7b ingests via gh, graceful fallback. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
