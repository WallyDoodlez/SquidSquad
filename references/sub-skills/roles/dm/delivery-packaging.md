### Step 2 — Scan for Pending Ship Items

Print: `[🦑 HH:MM:SS] Scanning for Pending Ship items...`

Query GitHub Issues for items pending delivery:

```bash
python references/scripts/tracker.py list-by-labels "status:pending-ship"
```

Pick the highest-priority item first. When picking up an item, print: `[🦑 HH:MM:SS] Delivering #[NUMBER]...`

1. Write working state: update `.squidsquad/dm/working-state.md` with the task ID, status `in-progress`, and planned delivery steps.
2. Read the task description, acceptance criteria, and Discussion entries (especially worker's delivery notes).

### Step 2b — Check for delivery:skip

Check the task's Discussion entries for a `delivery: skip` tag (set by PM when marking Pending Ship).

If found:
- Transition the issue to Shipped (auto-closes):
  ```bash
  python references/scripts/tracker.py transition [NUMBER] pending-ship shipped --role dm-lead
  python references/scripts/tracker.py comment [NUMBER] --role dm-lead --message "No delivery work needed (delivery: skip). Status → Shipped."
  ```
- Increment shipped count: `python references/scripts/config.py set shipped-since-bump [N+1]`
- Clear working state.
- Skip to Step 3 (Version Bump Check).

### Step 2c — Create Delivery Package

For each Pending Ship task that is NOT skipped:

0. **Branch checkout** (#3296): Before inspecting code for delivery, check out the task's feature branch to see the actual changes:
   ```bash
   python references/scripts/git_ops.py task-begin [role] [number]
   ```
   After delivery work is complete, return to working branch with `python references/scripts/git_ops.py task-end [role] [number]`.

0b. **PR merge gate** (#9478: branch+PR is the only mode): check for an associated PR:
   ```bash
   gh pr list --search "squidsquad/" --state open --json number,headRefName,baseRefName,body --limit 20
   ```
   Find the PR matching this issue number. Extract its `baseRefName` from the **same** list payload (no second `gh pr view` round trip). Compare against the configured working branch (#10287 stacked-PR auto-close trap):

   ```bash
   WORKING_BRANCH=$(python references/scripts/config.py get working-branch 2>/dev/null || echo "main")
   # PR_BASE comes from the gh pr list payload above — the matching PR's baseRefName field.
   ```

   - **If `$PR_BASE` is empty** (PR not found in list, or `gh pr list` returned a degraded payload): skip the base check defensively and fall through to the citation gate. Do not infer a stacked-PR state from missing data — a false-positive route-back here would block ship for transient `gh` failures.
   - **If `$PR_BASE` is non-empty AND `$PR_BASE` != `$WORKING_BRANCH`**: the PR is stacked on another feature branch. Merging the parent would squash-delete its source and auto-close this PR (`state=CLOSED, mergeable=CONFLICTING`); the PR cannot be re-targeted in place once that happens. Do **not** request a harness merge. Route back to in-progress so the worker agent merges `$WORKING_BRANCH` into the branch **and** retargets the PR base on GitHub (the git merge alone does NOT change the GitHub PR's `baseRefName` — without retargeting via the REST API, DM will detect the same stacked state next cycle and the route-back loops). **Never rebase** (operator rule [[feedback_never_rebase_merge_instead]] — rebase rewrites history, invalidates open PR review state, and is fragile on Windows/MSYS2). **Note (#10559)**: `gh pr edit --base` is broken in this repo's installed `gh` (2.34.0) by GitHub's projects-classic GraphQL deprecation — exits 1 on every invocation. Use `gh api -X PATCH ... -f base=...` against the REST endpoint instead; it does not touch the deprecated `projectCards` field:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-ship in-progress --role dm-lead
     python references/scripts/tracker.py comment [NUMBER] --role dm-lead --message "PR #[PR_NUMBER] is stacked on \`$PR_BASE\` instead of \`$WORKING_BRANCH\`. Stacked PRs auto-close when their parent merges (squash-delete) and cannot be re-targeted in place. Worker agent: merge \`$WORKING_BRANCH\` into the branch (\`git fetch origin && git merge origin/$WORKING_BRANCH\`), then retarget the PR base via \`gh api -X PATCH repos/OWNER/REPO/pulls/[PR_NUMBER] -f base=$WORKING_BRANCH\` (\`gh pr edit --base\` is broken by upstream GraphQL deprecation — see #10559; the git merge alone does not change the PR's baseRefName on GitHub either), then re-route to pending-ship. **Do not rebase** — merge is the canonical approach (operator rule). Alternatively wait for the parent PR to merge before re-routing."
     ```
     Skip this item and move to the next.

   If the base check passes (PR_BASE matches WORKING_BRANCH, or PR_BASE was empty and skipped), apply the contract-citation soft gate (#8950 Gate #4):

   ```bash
   ARTIFACTS=$(ls .squidsquad/pm/planning/*[NUMBER]* .squidsquad/qa/planning/*[NUMBER]* 2>/dev/null)
   ```

   - **If `$ARTIFACTS` is empty** (bug fix or trivial task with no planning artifacts): the citation gate does not apply — proceed with the merge request below.
   - **If `$ARTIFACTS` is non-empty**: scan the PR description (`body` field above) for a substring reference to any planning filename returned (e.g. `CONTEXT-[NUMBER].md`, `.squidsquad/qa/planning/TEST-PLAN-[NUMBER].md`, legacy `FEAT-*-[NUMBER]-TEST-PLAN.md`) OR a `### 5.X #[NUMBER]` bundle-CONTEXT section pointer. Under the #9184 workflow the typical citation is `CONTEXT-[NUMBER].md` (PM-side) and `.squidsquad/qa/planning/TEST-PLAN-[NUMBER].md` (QA-side). If **no** such reference is present, do **not** merge — route back to the verifier:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-ship pending-test --role dm-lead
     python references/scripts/tracker.py comment [NUMBER] --role dm-lead --message "PR does not cite the planning contract; cannot verify architectural conformance. verifier: confirm AC walk completed against the planning artifacts under .squidsquad/pm/planning/ (CONTEXT) and .squidsquad/qa/planning/ (TEST-PLAN)."
     ```
     Skip this item and move to the next.

   If the citation gate passes (or did not apply), request merge via harness before shipping:
     ```bash
     curl -s -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": [PR_NUMBER], "branch": "[BRANCH]", "role": "dm"}'
     ```
     The harness returns 202 immediately. Check for `pr-merged` event in your next cycle's `recent_events`. If merge fails (`success: false` in event payload):
     ```bash
     python references/scripts/tracker.py comment [NUMBER] --role dm-lead --message "PR merge failed — main has moved since the branch was last updated. Worker agent: merge main into the branch (\`git fetch origin && git merge origin/main\`), resolve any conflicts in the merge commit, push, and re-route to pending-ship. **Do not rebase** — merge is the canonical approach (operator rule [[feedback_never_rebase_merge_instead]]). Status → In Progress."
     python references/scripts/tracker.py transition [NUMBER] pending-ship in-progress --role dm-lead
     ```
     Skip this item and move to the next.

1. **Update user-facing docs**: Update `README.md` with user-story descriptions of the new functionality. Update any relevant sections of `SKILL.md` that describe user-facing behavior. Write in terms users understand — what's new, how to use it, what changed.
2. **Write CHANGELOG entry**: Prepare a CHANGELOG entry for this task. Do NOT write it to `CHANGELOG.md` yet — it will be included in the next version bump. Instead, append a Discussion note with the CHANGELOG text:
   ```
   > [YYYY-MM-DD HH:MM] **dm**: CHANGELOG entry prepared: "#[NUMBER] — [Title]". Status → Shipped.
   ```
3. **Check for config/migration changes**: If the task introduces new config values, settings, or requires migration steps for existing installs, document them in the Discussion and ensure they are reflected in the upgrade flow.
4. **Enable feature flags**: If the task introduced a feature flag (a config field that defaults to `no` for new/upgraded installs), enable it on this project:
   - Search the task body and Discussion comments for feature flag references (look for config field names like `Cycle Runner`, `PR Flow`, etc.)
   - For each flag found, enable it: `python references/scripts/config.py set <field> yes`
   - The flag defaults to `no` for other installs via upgrade, but the project that built and verified the feature should always have it enabled
5. Transition the issue to Shipped (auto-closes):
   ```bash
   python references/scripts/tracker.py transition [NUMBER] pending-ship shipped --role dm-lead
   python references/scripts/tracker.py comment [NUMBER] --role dm-lead --message "Delivery complete. Docs updated, CHANGELOG prepared. Status → Shipped."
   ```
6. Increment shipped count: `python references/scripts/config.py set shipped-since-bump [N+1]`
7. Clear working state.
