# Label Taxonomy

Issues use labels for structured metadata. The following labels must exist on the repo (created during setup):

**Type:**
- `issue` — defect, regression, broken behavior
- `task` — new capability or enhancement

**Priority:**
- `priority:high` — urgent, blocks other work
- `priority:medium` — normal priority
- `priority:low` — nice-to-have, improvement scan items

**Status:**
- `status:open` — issue filed, awaiting triage
- `status:pending` — filed, awaiting human approval
- `status:planning` — approved by human, PM running intake
- `status:planned` — planning complete, awaiting human approval for execution
- `status:approved` — human approved, ready for dev pickup
- `status:in-progress` — agent actively working
- `status:pending-test` — implementation complete, awaiting QA
- `status:pending-human-review` — in-progress iteration awaiting HITL review (designer loop)
- `status:pending-human-setup` — worker paused, needs human to complete tool/environment setup
- `status:pending-ship` — QA verified, awaiting DM delivery
- `status:shipped` — delivered, closed

**Role (assignee domain):**
- `role:skill` (or `role:fe`, `role:be`, etc.) — dev agent
- `role:pm` — PM agent
- `role:qa` — QA agent
- `role:designer` — designer agent
- `role:dm` — DM agent

**Design (for tasks needing design):**
- `design:needed` — designer must produce specs before dev
- `design:in-progress` — designer working on specs
- `design:complete` — design approved, dev can proceed

**Severity (for issues):**
- `severity:high` — critical, blocks usage
- `severity:medium` — degraded functionality
- `severity:low` — cosmetic, minor annoyance

**Special:**
- `squidsquad` — all SquidSquad-managed items get this label
- `improvement-scan` — filed by improvement scanning (quiet cycle)
