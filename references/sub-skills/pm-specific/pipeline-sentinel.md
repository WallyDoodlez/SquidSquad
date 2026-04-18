### Step 6f — Pipeline Sentinel (always runs)

This step runs **every cycle regardless of QA presence**. It monitors the ticket pipeline for stalls, conflicts, and unmerged work.

Print: `[🦑 HH:MM:SS] Running pipeline sentinel...`

Write status bar: `python references/scripts/cycle.py status-bar [ROLE] "verifying" "pipeline-sentinel — Checking pipeline health..."`

**1. PR Conflict Detection**

Check Branch Workflow setting:
```bash
python references/scripts/config.py get branch-workflow
```

If `yes`, list open SquidSquad PRs and check for conflicts:
```bash
gh pr list --search "squidsquad/" --state open --json number,title,headRefName,mergeable --limit 20
```

For each PR with `mergeable` = `CONFLICTING`:
- Parse the issue number from the branch name (e.g., `squidsquad/skill/475` → `#475`)
- Comment on the issue: `python references/scripts/tracker.py comment [NUMBER] --role pm-lead --message "PR #[PR] has merge conflicts. Dev agent: rebase onto main."`
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
- `pending-ship` with unmerged PR: nudge dev agent to merge — `"Task at pending-ship for [N] min. Dev agent: merge PR and mark shipped."`
- `pending-test` with no QA activity: nudge QA — `"Task at pending-test for [N] min. QA: please verify."`
- `in-progress` with no recent Discussion comments: nudge assigned agent — `"Task in-progress for [N] min with no recent updates."`

**Max 2 nudges per cycle** to avoid noise. Only nudge items not already nudged in the last 90 minutes (check Discussion for recent PM nudge comments).

**3. PR Status Sync**

For each open PR (from the conflict check query above):
- **If merged**: find the tracker item, update to `Pending Ship` if not already. Comment: `"PR merged. Status → Pending Ship."`
- **If closed without merge**: update to `In Progress`. Comment: `"PR closed without merge. Status → In Progress."`

If Branch Workflow is `no`, skip this entire step silently.
