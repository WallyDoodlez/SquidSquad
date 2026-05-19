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

### Step 3 — Investigate and Route Findings

Print: `[🦑 HH:MM:SS] Investigating test failures...` (or skip if no failures)

#### Finding Routing Process

For each finding (test failure, gap, or defect discovered during verification):

**Step 3a — Classify the finding:**

Determine the finding category using your domain-specific finding categories (defined in your L3 layer). If no domain categories are available, use this generic process:
- Identify which role's **declared responsibilities** (from config.md team composition) the finding falls under.
- If ownership is unclear, escalate to PM — PM is always present and owns coordination.

**Step 3b — Check for duplicates:**

```bash
python references/scripts/tracker.py list-by-labels "type:issue,squidsquad"
```
Search output for keywords matching this finding. If a matching issue exists, comment on it — do not duplicate.

**Step 3c — Document and file:**

Every finding must include structured evidence:

```
**Finding**: [what is wrong — specific and testable]
**Evidence**: [test output, file:line, command that reproduces it]
**Category**: [implementation defect | spec gap | design defect | test infra]
**Routed to**: [role] — [why this role is responsible]
```

- If **objective** (clear pass/fail, crash, error): File immediately with the structured format above.
  ```bash
  python references/scripts/tracker.py create-issue --title "[title]" --body "[structured finding]" --role [target-role] --severity [high|medium|low] --reporter qa
  ```
- If **subjective** (coherence issue, style concern, architectural question): Flag for PM/human review. Do NOT file an issue — PM and human decide.
  ```bash
  python references/scripts/tracker.py comment [NUMBER] --role qa --message "Subjective finding flagged for PM/human review: [structured description]"
  ```
- If **ownership unclear**: Escalate to PM. PM is always present and owns coordination.
- If the finding **spans multiple domains**: File to the primary responsible role, cross-reference others in comments.

**Step 3d — Record on PR (if PR flow enabled):**

If the finding relates to a PR, also post the structured finding as a PR comment for inline review context:
```bash
gh pr comment [PR_NUMBER] --body "## QA Finding\n\n[structured finding from 3c]"
```

### Step 4 — Verify Fixed Issues

Print: `[🦑 HH:MM:SS] Verifying fixed issues...`

Query all issues pending test:

```bash
python references/scripts/tracker.py list-issues skill --status pending-test
```

(Repeat for each dev role.)

For each issue:

0. **Blocked check**: If the item has a `blocked:human-action` label, skip it. Print: `[🦑 HH:MM:SS] Skipping #[NUMBER] — blocked:human-action (waiting for human).` Do not change its status. Move to the next item.
1. Read details: `gh issue view [NUMBER] --json title,body,comments`
1b. **Consult the vault** (#5572) — search for relevant context before verifying:
   ```bash
   grep -rl "[keyword from issue]" .squidsquad/vault/ --include="*.md" | head -5
   ```
   Check for: decisions that affect expected behavior, patterns the fix should follow, learnings from similar past issues, and human quality preferences (`[[human-profile]]`). This prevents false passes on code that violates vault-documented constraints.
2. **Branch checkout** (#3296): Check out the task's feature branch before verification:
   ```bash
   python references/scripts/git_ops.py task-begin [role] [number]
   ```
   This is a no-op when branch-workflow is disabled. If the branch doesn't exist, task-begin exits non-zero — push back to the submitting agent.
   Run verification on the branch. When done, return to working branch:
   ```bash
   python references/scripts/git_ops.py task-end [role] [number]
   ```
3. Run the relevant test or manually verify the fix.
4. **Test coverage check**: Verify that the fix includes a regression test. Check for new or modified test files corresponding to the changed code. If the fix adds or changes code but includes no tests, reject it.
5. **Run the full test suite**: `python tests/run_tests.py` — all tests must pass.
6. If verified (fix works, regression test exists, all tests pass):
   - If a PR exists for this issue, convert from draft to ready:
     ```bash
     gh pr list --search "squidsquad/" --state open --json number,headRefName | python -c "import sys,json; [print(p['number']) for p in json.load(sys.stdin) if '/[NUMBER]' in p['headRefName']]"
     # If a PR number is found:
     gh pr ready [PR_NUMBER]
     ```
   - Transition to pending-ship:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role qa-lead
     python references/scripts/tracker.py comment [NUMBER] --role qa --message "Verified. Status → Pending Ship."
     ```
   - Increment `Shipped Since Last Bump`: `python references/scripts/config.py set shipped-since-bump [N+1]`
7. If not verified (fix doesn't work, no regression test, or tests fail):
   - Reopen: `python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role qa-lead`
   - Comment with specific failures — be specific about missing tests.

### Step 5 — Verify Pending Test Tasks

Print: `[🦑 HH:MM:SS] Verifying pending test tasks...`

Query all tasks pending test:

```bash
python references/scripts/tracker.py list-tasks skill --status pending-test
```

(Adjust role as needed for other agents.)

For each task:

0. **Blocked check**: If the item has a `blocked:human-action` label, skip it. Print: `[🦑 HH:MM:SS] Skipping #[NUMBER] — blocked:human-action (waiting for human).` Do not change its status. Move to the next item.

Read it: `gh issue view [NUMBER] --json title,body,labels,comments`

**Branch checkout** (#3296): Check out the task's feature branch before testing:
```bash
python references/scripts/git_ops.py task-begin [role] [number]
```
When verification is complete (pass or fail), return to working branch:
```bash
python references/scripts/git_ops.py task-end [role] [number]
```

1. **If a TEST-PLAN.md exists** in the PM's planning directory (`.squidsquad/pm/planning/`), spawn a QA subagent (via the Agent tool) to execute the test plan:

   Subagent prompt:
   ```
   Read .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md. For each test case:

   1. Write an executable pytest test in .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-tests.py
      - Each TC becomes a test function: test_tc_01_[name], test_tc_02_[name], etc.
      - Tests must use concrete assertions (file exists, string matches, JSON parses, exit code checks)
      - Use subprocess.run for script verification, pathlib for file checks, json/yaml for structure
   2. Run the tests: python -m pytest .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-tests.py -v
   3. Record pytest output verbatim in QA-RESULTS.md

   TC result rules:
   - PASS: test function passes
   - FAIL: test function fails — include assertion error
   - HUMAN-REQUIRED: TC cannot run because the environment is not set up (missing API key,
     Docker not running, etc.). This is NOT a code bug — a human must fix the environment.
     Tag with `blocked:human-action` label and note what the human needs to do.
   - "Deferred" and "Skipped" are NOT valid results. Every TC must be PASS, FAIL, or HUMAN-REQUIRED.

   If any TC is marked `[human-required]` in TEST-PLAN.md, skip it — PM will route to human.

   Write results to .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-QA-RESULTS.md
   Include the full pytest output and a summary table.
   ```

   **HUMAN-REQUIRED gate**: If any TC is HUMAN-REQUIRED, do NOT transition to pending-ship. Add the `blocked:human-action` label and comment: `"HUMAN-REQUIRED: [N] TCs need human environment setup: [list what's needed]. Cannot ship until resolved."`

   QA reviews QA-RESULTS.md and makes the final decision.

1b. **Comprehension testing** (if TEST-PLAN.md has a `## Comprehension Questions` section):

   This applies when the task touches LLM-consumed instructions (CLAUDE.md, sub-skills, SOUL.md). If TEST-PLAN.md has no `## Comprehension Questions` section, skip this step.

   Spawn a comprehension agent (via the Agent tool) with a neutral, file-scoped prompt: "Read the following files and answer ONLY from what you find in them. Files: [list modified files]. Answer each question below, quoting file content."

   **Adaptive spawning**: If 4+ sub-skills affected, spawn one agent per sub-skill group. Otherwise, single spawn.

   Record results in QA-RESULTS.md under `## Comprehension Tests` with per-CQ PASS/FAIL entries. A comprehension failure is a legitimate finding.

2. **If no TEST-PLAN.md exists**, test against the acceptance criteria manually.

2b. **Test coverage check** (always runs, with or without TEST-PLAN.md): Verify that new code has corresponding unit tests. Check for new or modified test files. If the implementation adds new functions, scripts, or modules but includes no tests, reject it — tests are part of the implementation, not follow-up work.

2c. **Run the full test suite**: `python tests/run_tests.py` — all tests must pass.

2d. **AC walk against the planning contract** (#8950 Gate #3) — before marking any task `pending-test → pending-ship`, locate the TEST-PLAN by task-number match (covers both legacy `FEAT-PM-<NUMBER>-TEST-PLAN.md` and new `TEST-PLAN-<NUMBER>.md` conventions):

   ```bash
   TEST_PLAN=$(ls .squidsquad/pm/planning/*[NUMBER]* 2>/dev/null | grep -i 'test-plan' | head -1)
   ```

   - **If `$TEST_PLAN` is empty** (bug fix or trivial task with no planning artifact): skip this AC walk, proceed with the existing verification flow.
   - **If `$TEST_PLAN` is non-empty**: read it and walk its AC list. For each AC, confirm it is **observably satisfied** by the implementation — run the verification command stated in the AC, check the file the AC names, or observe the output the AC describes. **Tests passing is necessary but not sufficient — do not infer AC satisfaction from test names.** If any AC is not observably satisfied, transition `pending-test → in-progress` and comment which AC failed:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role qa-lead
     python references/scripts/tracker.py comment [NUMBER] --role qa-lead --message "AC walk failed: AC-[N] in $TEST_PLAN is not observably satisfied — [what was checked and what failed]. Status → In Progress."
     ```

3. **Zero-gap gate**: If ANY gap, ambiguity, missing documentation, failed check, missing test coverage, or unresolved finding is discovered:
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

   **Promote test files to tests/** (before transitioning):
   If any test files exist in `.squidsquad/[ROLE]/planning/` matching `*-tests.py` or `*-QA-RESULTS*.md`:
   - Copy test `.py` files to `tests/` with naming convention: `tests/test_feat_[NUMBER]_[short_name].py`
   - If comprehension test files exist, also copy to `tests/`
   - Verify the promoted tests still pass: `python -m pytest tests/test_feat_[NUMBER]_*.py`
   - These tests persist as regression tests — they are NOT deleted during planning cleanup

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
   - **Check Auto Merge**: `python references/scripts/config.py get auto-merge`
   - **Check per-ticket override**: `python references/scripts/tracker.py get-labels [NUMBER]` — look for `review:human-required` label.

   **If Auto Merge `yes` AND no `review:human-required` label** — merge via harness:
     ```bash
     gh pr ready [PR_NUMBER]
     curl -s -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": [PR_NUMBER], "branch": "[BRANCH]", "role": "qa"}'
     ```
     The harness returns 202 immediately. The `pr-merged` event appears in your next cycle's `recent_events`.
     - **Merge succeeds** (check `pr-merged` event with `success: true`): transition to pending-ship:
       ```bash
       python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role qa-lead
       python references/scripts/tracker.py comment [NUMBER] --role qa --message "Verified — zero gaps. PR auto-merged. Status → Pending Ship."
       ```
     - **Merge conflict**: handle as described in the PR Flow `no` merge conflict section below.

   **If Auto Merge `no` OR `review:human-required` label present** — route to human review:
     ```bash
     gh pr ready [PR_NUMBER]
     python references/scripts/tracker.py transition [NUMBER] pending-test pending-human-review --role qa-lead
     python references/scripts/tracker.py comment [NUMBER] --role qa --message "Verified — zero gaps. PR approved. Awaiting human review. Status → Pending Human Review."
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
   curl -s -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": [PR_NUMBER], "branch": "[BRANCH]", "role": "qa"}'
   ```
   - **Merge succeeds**: proceed to pending-ship transition
   - **Merge conflict**: QA merges the working branch into the feature branch (code was already verified):
     ```bash
     git fetch origin
     git checkout [BRANCH_NAME]
     git merge origin/[WORKING_BRANCH]
     ```
     - **Merge succeeds (no code conflicts)**: push and retry merge
       ```bash
       git push origin [BRANCH_NAME]
       curl -s -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": [PR_NUMBER], "branch": "[BRANCH_NAME]", "role": "qa"}'
       ```
       If merge now succeeds, proceed to pending-ship. Code was already verified — no re-verification needed.
     - **Merge has code conflicts** (not just .squidsquad/ state files): reject back to dev with specific conflicting files
       ```bash
       git merge --abort
       git checkout [WORKING_BRANCH]
       python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role qa-lead
       python references/scripts/tracker.py comment [NUMBER] --role qa --message "Merge conflict with code changes on PR #[PR_NUMBER]. Conflicting files: [list]. Dev: resolve conflicts and re-submit."
       ```
     - **Only .squidsquad/ state file conflicts**: resolve by keeping both versions, then push and merge. State files are always auto-resolvable.
   - **No PR found**: proceed (direct-to-main workflow, no merge needed)

   After successful merge (or no PR):
   ```bash
   python references/scripts/tracker.py transition [NUMBER] pending-test pending-ship --role qa-lead
   python references/scripts/tracker.py comment [NUMBER] --role qa --message "Verified — zero gaps. PR merged. Status → Pending Ship."
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
