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

### Step 3 — Investigate and File Bugs From Test Failures

Print: `[🦑 HH:MM:SS] Investigating test failures...` (or skip if no failures)

For each test failure:

1. Determine which agent's domain the failure is in.
2. Check if a bug already exists: `gh issue list --label "type:bug,squidsquad" --search "[keywords]" --json number,title --limit 10`. If found, comment on the existing issue — do not duplicate.
3. If new and the failure is **objective** (clear test pass/fail, crash, error):
   - File immediately: `gh issue create --title "BUG: [title]" --body "[description with test evidence]" --label "type:bug,severity:[level],role:[target-role],squidsquad"`
4. If the finding is **subjective** (coherence issue, style concern, design inconsistency):
   - Flag for human review via PM — comment on a relevant issue or create a discussion: `> [YYYY-MM-DD HH:MM] **qa**: Subjective finding flagged for PM/human review: [description]`
   - Do NOT file a bug yet — PM and human decide.
5. If the failure spans multiple domains: file in each relevant role with cross-linking comments.

### Step 4 — Verify Fixed Bugs

Print: `[🦑 HH:MM:SS] Verifying fixed bugs...`

Query all bugs pending test:

```bash
gh issue list --label "type:bug,status:pending-test,squidsquad" --json number,title,labels,body --limit 50
```

For each bug:

1. Read details: `gh issue view [NUMBER] --json title,body,comments`
2. Run the relevant test or manually verify the fix.
3. If verified:
   - Transition to shipped and close:
     ```bash
     gh issue edit [NUMBER] --remove-label "status:pending-test" --add-label "status:shipped"
     gh issue close [NUMBER]
     gh issue comment [NUMBER] --body "> [YYYY-MM-DD HH:MM] **qa**: Verified. Status → Shipped."
     ```
   - Increment `Shipped Since Last Bump` in `config.md`.
4. If not verified:
   - Reopen: `gh issue edit [NUMBER] --remove-label "status:pending-test" --add-label "status:in-progress"`
   - Comment with specific failures.

### Step 5 — Verify Pending Test Features

Print: `[🦑 HH:MM:SS] Verifying pending test features...`

Query all features pending test:

```bash
gh issue list --label "type:feature,status:pending-test,squidsquad" --json number,title,labels,body --limit 50
```

For each feature, read it: `gh issue view [NUMBER] --json title,body,labels,comments`

1. **If a TEST-PLAN.md exists** in the agent's planning directory, spawn a QA subagent (via the Agent tool) to execute the test plan:

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
   gh issue edit [NUMBER] --remove-label "status:pending-test" --add-label "status:in-progress"
   gh issue comment [NUMBER] --body "> [YYYY-MM-DD HH:MM] **qa**: FAIL. [list every specific finding]. Back to In Progress."
   ```
   Do NOT mark Pending Ship with "gaps noted for follow-up." ALL findings must be resolved before shipping.
4. **Only exception**: The human explicitly says "ship with these gaps" — record the override: `gh issue comment [NUMBER] --body "> [YYYY-MM-DD HH:MM] **qa**: Human override — shipping with [N] noted gaps: [list]. Status → Pending Ship."`
5. If all criteria pass with zero gaps:
   ```bash
   gh issue edit [NUMBER] --remove-label "status:pending-test" --add-label "status:pending-ship"
   gh issue comment [NUMBER] --body "> [YYYY-MM-DD HH:MM] **qa**: Verified — zero gaps. Status → Pending Ship."
   ```
6. **delivery:skip check**: If the feature is internal-only, add `delivery:skip` to the comment: `"> [YYYY-MM-DD HH:MM] **qa**: Verified — zero gaps. delivery: skip (internal-only). Status → Pending Ship."`
7. If criteria fail: transition back to `In Progress` with specific failures in the comment.

### Step 5b — Monitor PRs (if PR Flow enabled)

If `PR Flow: yes` in `config.md`:

Print: `[🦑 HH:MM:SS] Checking open PRs...`

List open SquidSquad PRs:
```bash
gh pr list --search "squidsquad/" --state all --json number,title,state,mergedAt,url --limit 20
```

For each PR:
- **If merged**: find the corresponding tracker item (parse the feature/bug ID from the PR title). Update status to `Pending Ship`. Append Discussion entry: `> [YYYY-MM-DD HH:MM] **qa**: PR [URL] merged by human. Status → Pending Ship.` Apply the same `delivery: skip` logic as Step 5 item 4 if the feature is internal-only.
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
