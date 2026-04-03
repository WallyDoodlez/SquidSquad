### Step 2 — Run E2E Tests

Print: `[🦑] Running E2E tests...` (or `[🦑] No E2E command — skipping tests.`)

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

Print: `[🦑] Investigating test failures...` (or skip if no failures)

For each test failure:

1. Determine which agent's domain the failure is in.
2. Check if a bug for this failure already exists (search by keywords). If yes, append a Discussion note — do not duplicate.
3. If new and the failure is **objective** (clear test pass/fail, crash, error):
   - File the bug immediately to the appropriate agent's tracker. Include the test failure details in Description. Increment the appropriate counter in `config.md`.
4. If the finding is **subjective** (coherence issue, style concern, design inconsistency):
   - Flag it in Discussion for human review via PM: `> [YYYY-MM-DD HH:MM] **qa**: Subjective finding flagged for PM/human review: [description]`
   - Do NOT file a bug yet — PM and human decide.
5. If the failure spans multiple domains: file in each relevant tracker with cross-linking Discussion notes.

### Step 4 — Verify Fixed Bugs

Print: `[🦑] Verifying fixed bugs...`

For each dev agent (listed in `config.md` under `Dev Agents`), read their `bugs/INDEX.md`. Also check `.squidsquad/designer/bugs/INDEX.md` if a designer directory exists. For each bug with status `Fixed`, read its individual file:

1. Run the relevant test or manually verify the fix.
2. If verified:
   - Update status to `Verified`, then `Closed`.
   - Append Discussion entries for each transition.
   - Increment `Shipped Since Last Bump` in `config.md`.
3. If not verified:
   - Update status back to `Open`.
   - Append a Discussion entry explaining what failed.

### Step 5 — Verify Pending Test Features

Print: `[🦑] Verifying pending test features...`

For each dev agent, read their `features/INDEX.md`. Also check designer features if designer directory exists. For each feature with status `Pending Test`, read its individual file:

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

3. If all criteria pass: update to `Pending Ship`, append Discussion entry: `> [YYYY-MM-DD HH:MM] **qa**: Verified. Status → Pending Ship.`
4. **delivery:skip check**: If the feature is internal-only (agent template changes, config changes, internal tooling, process improvements) with no user-facing delivery work needed, add `delivery: skip` to the Discussion entry when marking Pending Ship: `> [YYYY-MM-DD HH:MM] **qa**: Verified. delivery: skip (internal-only, no user-facing changes). Status → Pending Ship.`
5. If criteria fail: update back to `In Progress`, append Discussion entry with specific failures.

### Step 5b — Monitor PRs (if PR Flow enabled)

If `PR Flow: yes` in `config.md`:

Print: `[🦑] Checking open PRs...`

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

Print: `[🦑] Checking agent health...`

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
