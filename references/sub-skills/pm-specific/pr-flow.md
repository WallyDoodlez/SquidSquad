### Step 6b — Monitor PRs (if PR Flow enabled)

If `PR Flow: yes` in `config.md`:

Print: `[🦑 HH:MM:SS] Checking open PRs...`

List open SquidSquad PRs:
```bash
gh pr list --search "squidsquad/" --state all --json number,title,state,mergedAt,url --limit 20
```

For each PR:
- **If merged**: find the corresponding tracker item (parse the feature/bug ID from the PR title). Update status to `Pending Ship`. Append Discussion entry: `> [YYYY-MM-DD HH:MM] **pm**: PR [URL] merged by human. Status → Pending Ship.` Apply the same `delivery: skip` logic as Step 6 item 3 if the feature is internal-only.
- **If closed without merge**: update status back to `In Progress`. Append Discussion entry with note.
- **If open with new comments**: fetch comments via `gh pr view [N] --comments`. Append any new comments to the tracker Discussion: `> [YYYY-MM-DD HH:MM] **pm**: PR comment from [author]: [summary]`
- **If open with "changes requested" review**: update status back to `In Progress`. Append Discussion entry with the requested changes.

If `PR Flow: no`, skip this step.

**Auto-merge for pending-ship tasks** (runs regardless of PR Flow setting):

When a task transitions to `Pending Ship` and DM **is** present (`.squidsquad/dm/` exists), PM auto-merges the PR before DM handles delivery:

Check auto-merge eligibility (same rules as delivery-fallback Step 0):
- `Auto Merge: yes` AND `Branch Workflow: yes`
- Item is `type:task` (not `type:issue`)
- Item does NOT have `merge:manual` label

If eligible, find and merge the PR:
```bash
gh pr list --search "squidsquad/[role]/[NUMBER]" --state open --json number,headRefName --limit 1
python references/scripts/git_ops.py pr-merge [PR_NUMBER]
```

Handle results same as delivery-fallback: success → proceed, conflict → route back to dev, failure → fall back to manual.

This ensures PRs are merged before DM picks up delivery, regardless of whether DM or PM handles the shipping transition.
