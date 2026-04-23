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
4. **Test coverage check**: Verify that the fix includes a regression test. Check for new or modified test files corresponding to the changed code. If the fix adds or changes code but includes no tests, reject it.
5. **Run the full test suite**: `python tests/run_tests.py` — all tests must pass.
6. If verified (fix works, regression test exists, all tests pass):
   - If a PR exists for this issue, convert from draft to ready:
     ```bash
     gh pr list --search "squidsquad/" --state open --json number,headRefName | python -c "import sys,json; [print(p['number']) for p in json.load(sys.stdin) if '/[NUMBER]' in p['headRefName']]"
     # If a PR number is found:
     gh pr ready [PR_NUMBER]
     ```
   - Transition to shipped (auto-closes):
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
   - Transition to `pending-review` (not `pending-ship`):
     ```bash
     # Convert draft PR to ready for review
     gh pr ready [PR_NUMBER]
     python references/scripts/tracker.py transition [NUMBER] pending-test pending-review --role qa-lead
     python references/scripts/tracker.py comment [NUMBER] --role qa --message "Verified — zero gaps. PR approved. Awaiting human review. Status → Pending Review."
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
   python references/scripts/git_ops.py pr-merge [PR_NUMBER]
   ```
   - **Merge succeeds**: proceed to pending-ship transition
   - **Merge conflict**: back to in-progress, comment with conflict details, dev rebases
     ```bash
     python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role qa-lead
     python references/scripts/tracker.py comment [NUMBER] --role qa --message "Merge conflict on PR #[PR_NUMBER]. Dev: rebase and re-submit. Back to In Progress."
     ```
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
