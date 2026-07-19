---
slot: instructions
ordinal: 22
roles: [verifier]
---

## Verification — Ship Flow (cold path)

Reached from `verification.md` Step 5's 5a, immediately after the mandatory forge-visible verdict comment has been posted to the issue — the mechanics of promoting test files, merging the PR (or not), and transitioning to `pending-ship` / `pending-human-review`. Also covers Step 5b's PR-monitoring loop.

**Promote test files to tests/** (before transitioning):
If any test files exist in `.squidsquad/[VERIFIER_ALIAS]/planning/` matching `TEST-[NUMBER]-tests.py` or `QA-RESULTS-[NUMBER]*.md`:
- Copy test `.py` files to `tests/` with naming convention: `tests/test_feat_[NUMBER]_[short_name].py`
- If comprehension test spec files exist at `tests/comprehension/[NUMBER]_spec.json`, leave them in place (already canonical)
- Verify the promoted tests still pass: `python -m pytest tests/test_feat_[NUMBER]_*.py`
- These tests persist as regression tests — they are NOT deleted during planning cleanup

Check PR Flow: `python references/scripts/config.py get pr-flow`

**If PR Flow `yes`** and a PR exists for this issue:
- Post verifier results on the PR:
  ```bash
  gh pr comment [PR_NUMBER] --body "## Verifier Results\n\n**Status**: PASS\n**Test Plan**: .squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-[NUMBER].md (Verifier-owned, derived from AC list)\n**Results**: [N/N tests passed]\n\nAll acceptance criteria verified against a live instance."
  ```
- Formally approve the PR:
  ```bash
  gh pr review [PR_NUMBER] --approve --body "Verifier verified — zero gaps."
  ```
  **Note (#13552)**: in a single-GH-identity install (every agent clone — pm/skill/verifier/dm — shares one `gh` auth, common for a solo-operator setup), this MAY fail with `Can not approve your own pull request (addPullRequestReview)` — GitHub sees the PR author and the reviewer as the same account. This is **expected and non-blocking**: the PR comment posted above is the durable approval record, and `gh pr ready` + the harness `/merge` below do not require an approved review. Treat the failure as a harmless no-op in this environment shape and proceed to the Auto Merge check regardless.
- **Check Auto Merge**: `python references/scripts/config.py get auto-merge`
- **Check per-ticket override**: `python references/scripts/tracker.py get-labels [NUMBER]` — look for `review:human-required` label.

**If Auto Merge `yes` AND no `review:human-required` label** — merge via harness:
  ```bash
  gh pr ready [PR_NUMBER]
  curl -s -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": [PR_NUMBER], "branch": "[BRANCH]", "role": "verifier"}'
  ```
  The harness returns 202 immediately. The `pr-merged` event appears in your next cycle's `recent_events`.
  - **Merge succeeds** (check `pr-merged` event with `success: true`): transition to pending-ship:
    ```bash
    python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role verifier-lead
    python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "Verified — zero gaps. PR auto-merged. Status → Pending Ship."
    ```
  - **Merge conflict**: handle as described in the PR Flow `no` merge conflict section below.

**If Auto Merge `no` OR `review:human-required` label present** — route to human review:
  ```bash
  gh pr ready [PR_NUMBER]
  python references/scripts/tracker.py transition [NUMBER] pending-test pending-human-review --role verifier-lead
  python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "Verified — zero gaps. PR approved. Awaiting human review. Status → Pending Human Review."
  ```

**If PR Flow `no`** (or no PR exists):

**Merge PR** (if a PR exists for this issue):
```bash
# Find and merge the PR
gh pr list --search "squidsquad/ [NUMBER]" --state open --json number,headRefName --limit 5
```
For each PR with branch matching `squidsquad/*/[NUMBER]`:
```bash
gh pr ready [PR_NUMBER] 2>/dev/null
curl -s -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": [PR_NUMBER], "branch": "[BRANCH]", "role": "verifier"}'
```
- **Merge succeeds**: proceed to pending-ship transition
- **Merge conflict**: Verifier merges the working branch into the feature branch (code was already verified):
  ```bash
  git fetch origin
  git checkout [BRANCH_NAME]
  git merge origin/[WORKING_BRANCH]
  ```
  - **Merge succeeds (no code conflicts)**: push and retry merge
    ```bash
    git push origin [BRANCH_NAME]
    curl -s -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": [PR_NUMBER], "branch": "[BRANCH_NAME]", "role": "verifier"}'
    ```
    If merge now succeeds, proceed to pending-ship. Code was already verified — no re-verification needed.
  - **Merge has code conflicts** (not just .squidsquad/ state files): reject back to worker with specific conflicting files
    ```bash
    git merge --abort
    git checkout [WORKING_BRANCH]
    python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role verifier-lead
    python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "Merge conflict with code changes on PR #[PR_NUMBER]. Conflicting files: [list]. Worker: resolve conflicts and re-submit."
    ```
  - **Only .squidsquad/ state file conflicts**: resolve by keeping both versions, then push and merge. State files are always auto-resolvable.
- **No PR found**: proceed (direct-to-main workflow, no merge needed)

After successful merge (or no PR):
```bash
python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role verifier-lead
python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "Verified — zero gaps. PR merged. Status → Pending Ship."
```

**delivery:skip check**: If the task is internal-only, add `delivery:skip` to the comment message.

**If criteria fail** (discovered here, during ship-flow mechanics — e.g. a merge conflict or a promoted-test failure; the inline zero-gap gate in `verification.md` Step 5 sub-step 3 already handles pre-verdict failures and never reaches this file):
   **If PR Flow `yes`** and a PR exists:
   - Post failure on the PR and request changes:
     ```bash
     gh pr comment [PR_NUMBER] --body "## Verifier Results\n\n**Status**: FAIL\n\n[list findings]"
     gh pr review [PR_NUMBER] --request-changes --body "Verifier FAIL: [findings summary]"
     ```
   - Transition back to `In Progress`:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role verifier-lead
     python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "FAIL. [findings]. PR changes requested. Back to In Progress."
     ```

   **If PR Flow `no`**: transition back to `In Progress` with specific failures in the comment.

## Monitor PRs (Step 5b — if PR Flow enabled)

If `PR Flow: yes` in `config.md`:

Print: `[🦑 HH:MM:SS] Checking open PRs...`

List open SquidSquad PRs:
```bash
gh pr list --search "squidsquad/" --state all --json number,title,state,mergedAt,url --limit 20
```

For each PR:
- **If merged**: find the corresponding tracker item (parse the task/issue ID from the PR title). Update status to `Pending Ship`. Append Discussion entry: `> [YYYY-MM-DD HH:MM] **verifier**: PR [URL] merged by human. Status → Pending Ship.` Apply the same `delivery: skip` logic as above if the task is internal-only.
- **If closed without merge**: update status back to `In Progress`. Append Discussion entry with note.
- **If open with new comments**: fetch comments via `gh pr view [N] --comments`. Append any new comments to the tracker Discussion: `> [YYYY-MM-DD HH:MM] **verifier**: PR comment from [author]: [summary]`
- **If open with "changes requested" review**: update status back to `In Progress`. Append Discussion entry with the requested changes.

If `PR Flow: no`, skip this step.
