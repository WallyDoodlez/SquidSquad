---
slot: instructions
ordinal: 20
roles: [pm]
---

### Step 6f — Pipeline Sentinel (always runs)

This step runs **every cycle regardless of verifier presence**. It monitors the ticket pipeline for stalls, conflicts, and unmerged work.

Print: `[🦑 HH:MM:SS] Running pipeline sentinel...`

Write status bar: `python references/scripts/cycle.py status-bar [ROLE] "verifying" "pipeline-sentinel — Checking pipeline health..."`

**1. PR Conflict Detection**

List open SquidSquad PRs and check for conflicts (#9478: branch+PR is the only mode):
```bash
gh pr list --search "squidsquad/" --state open --json number,title,headRefName,mergeable --limit 20
```

For each PR with `mergeable` = `CONFLICTING`:
- Parse the issue number from the branch name (e.g., `squidsquad/skill/475` → `#475`)
- Comment on the issue: `python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "PR #[PR] has merge conflicts. Worker agent: merge main into your branch and re-push."`
- If the task is at `pending-ship` or `pending-test`, transition back to `in-progress`:
  ```bash
  python references/scripts/tracker.py transition [NUMBER] [current-status] in-progress --role pm-lead
  ```

**2. Stall Detection**

Query all open SquidSquad items:
```bash
gh issue list --label squidsquad --state open --json number,title,labels,updatedAt --limit 50
```

For each item, check time since last update. If stalled beyond **90 minutes** (3 cycles at 30-min interval):
- `pending-ship` with unmerged PR: nudge worker agent to merge — `"Task at pending-ship for [N] min. Worker agent: merge PR and mark shipped."`
- `pending-test` with no verifier activity: nudge the verifier — `"Task at pending-test for [N] min. Verifier: please verify."`
- `in-progress` with no recent Discussion comments: nudge assigned agent — `"Task in-progress for [N] min with no recent updates."`

**Max 2 nudges per cycle** to avoid noise. Only nudge items not already nudged in the last 90 minutes (check Discussion for recent PM nudge comments).

**3. PR Status Sync**

For each open PR (from the conflict check query above):
- **If merged**: find the tracker item and transition to `pending-ship` if not already (expected state: `pending-test`). Comment: `"PR merged. Status → Pending Ship."`
  ```bash
  python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role pm-lead
  python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "PR merged. Status → Pending Ship."
  ```
  If the task is not at `pending-test` (e.g., already at `pending-ship` or `shipped`), skip the transition silently.
- **If closed without merge**: transition back to `in-progress` (expected state: `pending-test`). Comment: `"PR closed without merge. Status → In Progress."`
  ```bash
  python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role pm-lead
  python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "PR closed without merge. Status → In Progress."
  ```

**4. Stuck-State Detection (comprehensive)**

After the stall and PR sync checks, run these additional stuck-state detections. Each has a **Tier 1** (immediate unstick) and **Tier 2** (root-cause bug filing) response. **Max 2 auto-filed bugs per cycle** to avoid noise — prioritize by severity.

Before filing a Tier 2 bug, check if an open bug already exists for the same root cause:
```bash
python references/scripts/tracker.py list-issues [target-role] --status open
```
If a matching bug title exists, skip filing (already tracked).

**4a. Orphaned PR** — tracker item shipped/closed but PR still open and unmerged.

Query: cross-reference open PRs against closed/shipped tracker items.
```bash
gh pr list --search "squidsquad/" --state open --json number,title,headRefName --limit 20
```
For each open PR, parse the issue number from the branch name. Check if that issue is closed:
```bash
python references/scripts/tracker.py get-state [NUMBER]
```
If the issue is closed but the PR is open and unmerged:
- **Tier 1**: Comment on the tracker issue routing to owning agent — `python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "Orphaned PR #[PR] — item shipped but PR still open. [role]-lead or human: close or merge the PR."`
- **Tier 2**: File bug against DM — `"DM delivery did not enforce PR merge before marking shipped. Item #[NUMBER] shipped but PR #[PR] left open. Code on branch may never reach main."`

**4b. Shipped without merge** — item marked shipped but PR branch never merged (code lost).

For each recently closed item with `status:shipped` (last 20 closed items):
```bash
gh issue list --label squidsquad --label status:shipped --state closed --json number,title,labels --limit 20
```
Check if a corresponding branch exists and was never merged:
```bash
git branch -r --list "origin/squidsquad/*/[NUMBER]"
```
If the branch exists, check if it was merged to main:
```bash
git log main --oneline --grep="#[NUMBER]" -n 5
```
If no merge evidence and branch still exists:
- **Tier 1**: Comment on the issue — `"Warning: branch squidsquad/[role]/[NUMBER] exists but may not be merged to main. Code could be lost. Please verify."`
- **Tier 2**: File bug against the role that shipped it — `"Item #[NUMBER] shipped but feature branch may not be merged. Delivery process should verify PR merge before shipping."`

**4c. Approved but no pickup** — item at `status:approved` for more than 90 minutes with no agent pickup.

From the open items query (check 2), filter for `status:approved` items stalled >90 min:
- **Tier 1**: Comment nudge — `"Task approved for [N] min with no pickup. [role]-lead: please pick up or flag blockers."`
- **Tier 2**: Only file if stalled >4 hours — `"Task #[NUMBER] approved but no agent picked it up for [N] hours. Possible causes: agent down, workload saturation, or task not visible in agent's query."`

**4d. Planned but never approved** — `status:planned` for more than 4 hours.

From the open items query, filter for `status:planned` items stalled >4 hours:
- **Tier 1**: Comment — `"Task planned for [N] hours but not yet approved. Human: please review and approve or defer."`
- **Tier 2**: Not auto-filed (requires human decision — approval is a human gate).

**4e. Pending with no planning** — `status:pending` for more than 4 hours with no `status:planning` transition.

From the open items query, filter for `status:pending` items stalled >4 hours:
- **Tier 1**: Comment — `"Item pending for [N] hours with no planning started. PM: please triage and begin planning or defer."`
- **Tier 2**: Only if >8 hours — file against PM — `"Item #[NUMBER] pending for [N] hours with no planning activity. May need triage prioritization."`

**4f. In-progress on dead agent** — task `status:in-progress` but assigned agent's health is stalled/stopped.

For each `in-progress` item, extract the `role:*` label. Cross-reference with agent health:
```bash
python references/scripts/health_check.py --json
```
Parse the JSON output. If the assigned agent's health is `stalled`, `stopped`, or `unknown`:
- **Tier 0** (#9272 — try recovery first): if auto-boot in `cycle_pre.py` did not recover the agent, attempt manual stall recovery via `python references/scripts/boot_remote.py --role <name>` (see `boot-remote-agents` sub-skill). Only if the boot fails OR the agent remains unhealthy on the next health check, proceed to Tier 1. Skip this tier if the agent's intent is `stopping` or `stopped` (genuinely shut down on operator request, not a stall).
- **Tier 1**: Transition the task back to `approved` so another agent (or the same agent after restart) can pick it up:
  ```bash
  python references/scripts/tracker.py transition [NUMBER] in-progress approved --role pm-lead
  python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "Agent [role] is [health status]. Returning task to approved for re-pickup."
  ```
- **Tier 2**: File bug if agent has been unhealthy for >1 hour — `"Agent [role] health is [status] but task #[NUMBER] was in-progress. Harness may need investigation."`

<!-- #9478: branch+PR is the only mode; all checks above run unconditionally. -->

