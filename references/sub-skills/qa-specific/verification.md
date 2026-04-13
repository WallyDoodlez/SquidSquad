### Step 2 — Run E2E Tests

Print: `[🦑 HH:MM:SS] Running E2E tests...` (or `[🦑 HH:MM:SS] No E2E command — skipping tests.`)

If `E2E Tests` is configured in `config.md`, run: `[E2E_TEST_CMD]`

If no E2E command is configured, skip this step.

Log results in `qa/qa-log.md`:

```markdown
## QA Run — YYYY-MM-DD HH:MM

- **Result**: Passed | Failed | Skipped (no E2E command)
- **Tests Run**: [N]
- **Failures**: [list failing test names, or "none"]
- **Notes**: [anything notable]
```

### Step 3 — Investigate and File Issues From Test Failures

Print: `[🦑 HH:MM:SS] Investigating test failures...` (or skip if no failures)

For each test failure:

1. Determine which agent's domain the failure is in.
2. Check if an issue already exists: `python references/scripts/tracker.py list-by-labels "type:issue,squidsquad"` and search output for keywords. If found, comment on the existing issue — do not duplicate.
3. If new and the failure is **objective** (clear test pass/fail, crash, error):
   - File immediately: `python references/scripts/tracker.py create-issue --title "[title]" --body "[description with test evidence]" --role [target-role] --severity [high|medium|low] --reporter qa`
4. If the finding is **subjective** (coherence issue, style concern, design inconsistency):
   - Flag for human review via PM: `python references/scripts/tracker.py comment [NUMBER] --role qa --message "Subjective finding flagged for PM/human review: [description]"`
   - Do NOT file an issue yet — PM and human decide.
5. If the failure spans multiple domains: file in each relevant role with cross-linking comments.

### Step 4 — Verify Fixed Issues

Print: `[🦑 HH:MM:SS] Verifying fixed issues...`

Query all issues pending test:

```bash
python references/scripts/tracker.py list-issues skill --status pending-test
```

(Repeat for each dev role.)

For each issue:

1. Read details: `gh issue view [NUMBER] --json title,body,comments`
2. **Branch checkout**: Check if the issue comments reference a feature branch (look for `squidsquad/` branch name). If found:
   ```bash
   python references/scripts/git_ops.py branch-switch squidsquad/[role]/[number]
   ```
   Run verification on the branch. When done, switch back:
   ```bash
   python references/scripts/git_ops.py branch-switch main
   ```
   If no branch referenced, verify on main as usual.
3. Run the relevant test or manually verify the fix.
5. If verified:
   - Transition to shipped (auto-closes):
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role qa-lead
     python references/scripts/tracker.py comment [NUMBER] --role qa --message "Verified. Status → Pending Ship."
     ```
   - Increment `Shipped Since Last Bump`: `python references/scripts/config.py set shipped-since-bump [N+1]`
6. If not verified:
   - Reopen: `python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role qa-lead`
   - Comment with specific failures.

### Step 5 — Verify Pending Test Tasks

Print: `[🦑 HH:MM:SS] Verifying pending test tasks...`

Query all tasks pending test:

```bash
python references/scripts/tracker.py list-tasks skill --status pending-test
```

(Adjust role as needed for other agents.)

For each task, read it: `gh issue view [NUMBER] --json title,body,labels,comments`

**Branch checkout**: Check if the issue comments reference a feature branch (look for `squidsquad/` branch name or PR URL). If found, checkout the branch before testing:
```bash
python references/scripts/git_ops.py branch-switch squidsquad/[role]/[number]
```
When verification is complete (pass or fail), switch back to main:
```bash
python references/scripts/git_ops.py branch-switch main
```

1. **If a TEST-PLAN.md exists** in the PM's planning directory (`.squidsquad/pm/planning/`), spawn a QA subagent (via the Agent tool) to execute the test plan:

   Subagent prompt:
   ```
   Read .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md. Execute each test case:
   1. Read the relevant files mentioned in preconditions
   2. Run any verification commands
   3. Check regression risks
   4. For each test case, record PASS or FAIL with notes on what was observed

   Write results to .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-QA-RESULTS.md
   ```

   QA reviews QA-RESULTS.md and makes the final decision.

2. **If no TEST-PLAN.md exists**, test against the acceptance criteria manually.

3. **Zero-gap gate**: If ANY gap, ambiguity, missing documentation, failed check, or unresolved finding is discovered:
   ```bash
   python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role qa-lead
   python references/scripts/tracker.py comment [NUMBER] --role qa --message "FAIL. [list every specific finding]. Back to In Progress."
   ```
   Do NOT mark Pending Ship with "gaps noted for follow-up." ALL findings must be resolved before shipping.
4. **Only exception**: The human explicitly says "ship with these gaps" — record the override:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role qa --message "Human override — shipping with [N] noted gaps: [list]. Status → Pending Ship."
   ```
5. If all criteria pass with zero gaps:

   Check PR Flow: `python references/scripts/config.py get pr-flow`

   **If PR Flow `yes`** and a PR exists for this issue:
   - Post QA results on the PR:
     ```bash
     gh pr comment [PR_NUMBER] --body "## QA Results\n\n**Status**: PASS\n**Test Plan**: FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md\n**Results**: [N/N tests passed]\n\nAll acceptance criteria verified."
     ```
   - Formally approve the PR:
     ```bash
     gh pr review [PR_NUMBER] --approve --body "QA verified — zero gaps."
     ```
   - Transition to `pending-review` (not `pending-ship`):
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-test pending-review --role qa-lead
     python references/scripts/tracker.py comment [NUMBER] --role qa --message "Verified — zero gaps. PR approved. Awaiting human review. Status → Pending Review."
     ```

   **If PR Flow `no`** (or no PR exists):
   ```bash
   python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role qa-lead
   python references/scripts/tracker.py comment [NUMBER] --role qa --message "Verified — zero gaps. Status → Pending Ship."
   ```

6. **delivery:skip check**: If the task is internal-only, add `delivery:skip` to the comment message.

7. If criteria fail:
   **If PR Flow `yes`** and a PR exists:
   - Post failure on the PR and request changes:
     ```bash
     gh pr comment [PR_NUMBER] --body "## QA Results\n\n**Status**: FAIL\n\n[list findings]"
     gh pr review [PR_NUMBER] --request-changes --body "QA FAIL: [findings summary]"
     ```
   - Transition back to `In Progress`:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role qa-lead
     python references/scripts/tracker.py comment [NUMBER] --role qa --message "FAIL. [findings]. PR changes requested. Back to In Progress."
     ```

   **If PR Flow `no`**: transition back to `In Progress` with specific failures in the comment.

### Step 5b — Monitor PRs (if PR Flow enabled)

If `PR Flow: yes` in `config.md`:

Print: `[🦑 HH:MM:SS] Checking open PRs...`

List open SquidSquad PRs:
```bash
gh pr list --search "squidsquad/" --state all --json number,title,state,mergedAt,url --limit 20
```

For each PR:
- **If merged**: find the corresponding tracker item (parse the task/issue ID from the PR title). Update status to `Pending Ship`. Append Discussion entry: `> [YYYY-MM-DD HH:MM] **qa**: PR [URL] merged by human. Status → Pending Ship.` Apply the same `delivery: skip` logic as Step 5 item 4 if the task is internal-only.
- **If closed without merge**: update status back to `In Progress`. Append Discussion entry with note.
- **If open with new comments**: fetch comments via `gh pr view [N] --comments`. Append any new comments to the tracker Discussion: `> [YYYY-MM-DD HH:MM] **qa**: PR comment from [author]: [summary]`
- **If open with "changes requested" review**: update status back to `In Progress`. Append Discussion entry with the requested changes.

If `PR Flow: no`, skip this step.

### Step 6 — Agent Health Check

Print: `[🦑 HH:MM:SS] Checking agent health...`

Check each agent's health by reading their `current-state` file via cross-clone paths from `.squidsquad/.local-config`. Each agent writes to its `current-state` file at the end of every cycle (including quiet cycles), so the file's mtime indicates when the agent last completed a cycle.

Read `.squidsquad/.local-config` to get each agent's clone path. For each dev agent listed in `config.md`, plus PM, plus DM and designer (if their directories exist):

1. Look up the agent's clone path from `.local-config` (format: `- **role**: /absolute/path`).
2. Read `<path>/.squidsquad/<role>/current-state` and check the file's mtime.
3. Read the `Iteration Interval > Minutes` value from `config.md` (default 30). An agent is stalled if the `current-state` mtime is older than 2× the iteration interval.

- If `current-state` exists and mtime is recent (within 2× interval): agent is healthy (🦑).
- If `current-state` exists but mtime is stale (older than 2× interval): agent is **stalled** (👻). Log a warning in `qa/qa-log.md` and append a Discussion note:
  ```
  > [YYYY-MM-DD HH:MM] **qa**: Agent [role] appears stalled — no cycle activity for [elapsed] minutes. Please check.
  ```
- If `.local-config` is missing, path is unreachable, or `current-state` doesn't exist: agent status is unknown (❓) — note in QA log.
