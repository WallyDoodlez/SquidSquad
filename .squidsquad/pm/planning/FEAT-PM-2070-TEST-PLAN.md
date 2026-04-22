# FEAT-PM-2070 Test Plan — Cycle Runner Script

## Test Cases

---

### Section A: cycle_pre.py — Input Generation

---

### TC-1: cycle_pre produces valid cycle-input.json for PM role
- **Precondition**: PM agent directory exists at `.squidsquad/pm/`. Config.md has valid settings. GitHub CLI authenticated. Repo on `main` branch with clean working tree.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py pm`
  2. Read `.squidsquad/pm/cycle-input.json`
- **Expected**: Valid JSON with all required PM fields: `role` = "pm", `cycle_number` (integer), `timestamp` (ISO 8601), `pull_result`, `context_pressure` object, `working_state` object, `qa_present` (boolean), `dm_present` (boolean), `tracker` object with `pending_test_issues`, `pending_test_tasks`, `pending_ship_tasks`, `external_issues`, `open_prs`, `agent_health` object, `config` object, `merged_branches` array, `template_changed` boolean.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['role']=='pm'; assert 'tracker' in d; assert 'agent_health' in d; assert 'config' in d"`

### TC-2: cycle_pre produces valid cycle-input.json for skill role
- **Precondition**: Skill agent directory exists at `.squidsquad/skill/`. Config.md has valid settings. GitHub CLI authenticated.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Read `.squidsquad/skill/cycle-input.json`
- **Expected**: Valid JSON with skill-specific fields: `role` = "skill", `cycle_number`, `timestamp`, `pull_result`, `context_pressure`, `working_state` (with `completed_steps`, `remaining_steps`, `key_decisions`), `work_queue` (with `qa_rejected` and `queue` arrays), `planning_artifacts` object, `config` (with `test_command`), `quiet_cycle_counter`, `interval_minutes`, `interval_changed`, `template_changed`.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/skill/cycle-input.json')); assert d['role']=='skill'; assert 'work_queue' in d; assert 'planning_artifacts' in d"`

### TC-3: cycle_pre produces valid cycle-input.json for QA role
- **Precondition**: QA agent directory exists at `.squidsquad/qa/`. Config.md has valid settings. GitHub CLI authenticated.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py qa`
  2. Read `.squidsquad/qa/cycle-input.json`
- **Expected**: Valid JSON with QA-specific fields: `role` = "qa", `cycle_number`, `timestamp`, `pull_result`, `context_pressure`, `working_state`, `e2e_test_result` object, `verification_queue` (with `pending_test_issues` and `pending_test_tasks` arrays, each entry containing `branch` field), `open_prs`, `agent_health`, `config`, `template_changed`.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/qa/cycle-input.json')); assert d['role']=='qa'; assert 'verification_queue' in d; assert 'e2e_test_result' in d"`

### TC-4: cycle_pre produces valid cycle-input.json for DM role
- **Precondition**: DM agent directory exists at `.squidsquad/dm/`. Config.md has valid settings. GitHub CLI authenticated.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py dm`
  2. Read `.squidsquad/dm/cycle-input.json`
- **Expected**: Valid JSON with DM-specific fields: `role` = "dm", `cycle_number`, `timestamp`, `pull_result`, `context_pressure`, `working_state`, `bugs` array, `pending_ship` array (with `delivery_skip` boolean per item), `version_bump` object (with `ship_threshold`, `shipped_since_bump`, `bump_due`, `open_issues_count`, `current_version`), `config`, `template_changed`.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/dm/cycle-input.json')); assert d['role']=='dm'; assert 'pending_ship' in d; assert 'version_bump' in d"`

### TC-5: cycle_pre performs git pull before generating input
- **Precondition**: Remote has new commits not yet pulled locally. Clean working tree.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Check git log for the remote commits
- **Expected**: `pull_result` = "ok" in cycle-input.json. Local branch is up to date with remote after cycle_pre completes.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/skill/cycle-input.json')); assert d['pull_result']=='ok'"` and `git log --oneline -1` shows the remote commit.

### TC-6: cycle_pre reads working-state.md correctly
- **Precondition**: `.squidsquad/skill/working-state.md` contains an active task `#2050` with status `in-progress`, completed steps, remaining steps, and key decisions.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Read cycle-input.json
- **Expected**: `working_state.task` = "#2050", `working_state.status` = "in-progress", `completed_steps`, `remaining_steps`, `key_decisions` arrays populated, `raw_content` contains the full file content.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/skill/cycle-input.json')); assert d['working_state']['task']=='#2050'; assert d['working_state']['status']=='in-progress'"`

### TC-7: cycle_pre detects planning phase suppression for PM
- **Precondition**: `.squidsquad/pm/working-state.md` contains `- **Phase**: researching #2070`.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py pm`
  2. Read cycle-input.json
- **Expected**: `working_state.suppressed` = true. `working_state.phase` = "researching #2070".
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['working_state']['suppressed']==True; assert 'researching' in d['working_state']['phase']"`

### TC-8: cycle_pre sets correct branch for QA verification
- **Precondition**: QA has a pending-test issue #123 on branch `squidsquad/skill/123`. QA agent on `main`.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py qa`
  2. Check current git branch
  3. Read cycle-input.json
- **Expected**: Git is checked out to `squidsquad/skill/123`. `verification_queue.pending_test_issues[0].branch` = "squidsquad/skill/123". Agent is on the correct branch to verify the work.
- **Verification**: `git branch --show-current` returns `squidsquad/skill/123`. cycle-input.json contains the branch info.

### TC-9: cycle_pre queries tracker for work queue (skill)
- **Precondition**: Tracker has 1 QA-rejected issue (#2050) and 2 queued items (#2045 high priority issue, #2060 medium priority task) assigned to skill role.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Read cycle-input.json
- **Expected**: `work_queue.qa_rejected` contains #2050 with feedback. `work_queue.queue` contains #2045 and #2060 with titles, types, and priorities. QA-rejected items appear first. Queue is sorted by priority.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/skill/cycle-input.json')); assert len(d['work_queue']['qa_rejected'])>=1; assert d['work_queue']['queue'][0]['priority']=='high'"`

### TC-10: cycle_pre populates planning_artifacts paths (skill)
- **Precondition**: Task #2060 has planning artifacts at `.squidsquad/pm/planning/FEAT-SKILL-2060-RESEARCH.md`, `FEAT-SKILL-2060-CONTEXT.md`, and `FEAT-SKILL-2060-TEST-PLAN.md`.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Read cycle-input.json
- **Expected**: `planning_artifacts["2060"]` contains paths to all three artifacts. Paths are relative to repo root.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/skill/cycle-input.json')); assert '2060' in d['planning_artifacts']; assert 'research' in d['planning_artifacts']['2060']"`

### TC-11: cycle_pre computes context pressure correctly
- **Precondition**: Context window used percentage is 42%. Config threshold is 70%.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py pm`
  2. Read cycle-input.json
- **Expected**: `context_pressure.used_pct` = 42, `context_pressure.threshold` = 70, `context_pressure.exceeded` = false.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['context_pressure']['exceeded']==False"`

### TC-12: cycle_pre increments cycle number from previous iteration
- **Precondition**: Last PM iteration log is `iter-458.md`.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py pm`
  2. Read cycle-input.json
- **Expected**: `cycle_number` = 459.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['cycle_number']==459"`

---

### Section B: cycle_post.py — Output Processing

---

### TC-13: cycle_post commits and pushes state for PM quiet cycle
- **Precondition**: Agent wrote cycle-output.json with `cycle_type: "quiet"`, empty arrays for all work fields, and `commit_message: "pm: cycle 459 — quiet, queue empty"`. Repo has uncommitted state changes.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
  2. Check git log
  3. Check remote
- **Expected**: New commit with message "pm: cycle 459 — quiet, queue empty". Changes pushed to remote. Iteration log NOT created (quiet cycle). Status bar set to `idle|`.
- **Verification**: `git log --oneline -1` matches expected commit message. `git diff origin/main` is empty.

### TC-14: cycle_post performs status transitions via tracker.py
- **Precondition**: Agent wrote cycle-output.json with `status_transitions: [{"number": 123, "from": "pending-test", "to": "pending-ship"}]`.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
  2. Query issue #123 labels
- **Expected**: Issue #123 has label `status:pending-ship`. Previous `status:pending-test` label removed. Transition was performed via `tracker.py transition` (not raw `gh issue edit`).
- **Verification**: `python references/scripts/tracker.py get-labels 123` shows `status:pending-ship`.

### TC-15: cycle_post posts tracker comments
- **Precondition**: Agent wrote cycle-output.json with `tracker_comments: [{"number": 123, "message": "Verified — zero gaps. Status -> Pending Ship."}]`.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
  2. Read issue #123 comments
- **Expected**: New comment on #123 with the specified message, attributed to pm-lead.
- **Verification**: `gh issue view 123 --json comments --jq '.comments[-1].body'` contains "Verified".

### TC-16: cycle_post creates iteration log for active cycle
- **Precondition**: Agent wrote cycle-output.json with `cycle_type: "active"`, `cycle_number: 459`, `iteration_summary: "Verified #123, filed #2071"`.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
  2. Check iteration log
- **Expected**: File `.squidsquad/pm/iterations/iter-459.md` created with correct format. Old logs cleaned up if >20 exist.
- **Verification**: File exists and contains "Verified #123" in content.

### TC-17: cycle_post handles skill branch workflow (commit-code + commit-state)
- **Precondition**: Skill agent on branch `squidsquad/skill/2050`. Agent wrote cycle-output.json with `code_commit: {branch: "squidsquad/skill/2050", message: "skill: fixed null check", pr_needed: true, pr_title: "skill: #2050 — Fix null check"}` and `state_commit_message: "skill: cycle 165 — fixed #2050"`. Config has `branch_workflow: true`.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py skill`
  2. Check git log on feature branch
  3. Check git log on main
  4. Check PRs
- **Expected**: Code commit on `squidsquad/skill/2050` with message "skill: fixed null check". State commit on `main` with message "skill: cycle 165 — fixed #2050". PR created with title "skill: #2050 — Fix null check" if pr_needed is true.
- **Verification**: `git log squidsquad/skill/2050 --oneline -1` and `git log main --oneline -1` show correct commits. `gh pr list` shows new PR.

### TC-18: cycle_post handles QA branch switch-back after verification
- **Precondition**: QA agent was checked out to `squidsquad/skill/123` by cycle_pre. Agent wrote cycle-output.json with verification results.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py qa`
  2. Check current branch
- **Expected**: Git is back on `main` branch. State committed to main.
- **Verification**: `git branch --show-current` returns `main`.

### TC-19: cycle_post performs DM version bump sequence
- **Precondition**: DM agent wrote cycle-output.json with `version_bump: {new_version: "0.24.0", items_included: [789, 790, 791]}`. Current version is "0.23.0".
- **Steps**:
  1. Run `python references/scripts/cycle_post.py dm`
  2. Check config.md version
  3. Check SKILL.md version
  4. Check CHANGELOG.md
  5. Check git tags
- **Expected**: config.md updated to "0.24.0". SKILL.md frontmatter version updated. CHANGELOG.md has new section for 0.24.0 listing items 789, 790, 791. Git tag `v0.24.0` created. `Shipped Since Last Bump` reset to 0 in config.md. All pushed.
- **Verification**: `git tag -l "v0.24.0"` returns the tag. `python references/scripts/config.py get version` returns "0.24.0".

### TC-20: cycle_post validates cycle-output.json schema
- **Precondition**: Agent wrote malformed cycle-output.json (e.g., missing `role` field, or invalid `cycle_type` value "banana").
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
- **Expected**: Script exits with non-zero status. Clear error message printed indicating which fields are invalid or missing. No partial execution of transitions, commits, or comments.
- **Verification**: Exit code != 0. No new commits created. No tracker modifications.

### TC-21: cycle_post validates status transition from/to states
- **Precondition**: Agent wrote cycle-output.json with `status_transitions: [{"number": 123, "from": "approved", "to": "shipped"}]` (illegal transition — skips multiple states).
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
- **Expected**: Transition rejected by tracker.py. Error logged. Other cycle_post operations (commit, iteration log) still execute. The invalid transition is skipped, not the entire post-processing.
- **Verification**: Issue #123 retains its original status label. Error output mentions illegal transition.

### TC-22: cycle_post writes correct status bar state
- **Precondition**: Agent completed cycle. cycle-output.json has `cycle_type: "active"`.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
  2. Read `.squidsquad/pm/current-state`
- **Expected**: File contains `idle|` after cycle_post completes. Written via atomic write (tmp + mv).
- **Verification**: `cat .squidsquad/pm/current-state` returns `idle|`.

### TC-23: cycle_post handles self-restart sentinel
- **Precondition**: Agent wrote cycle-output.json with `restart_needed: true`, `restart_reason: "context pressure at 85%"`.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
  2. Check for sentinel file
- **Expected**: File `.squidsquad/pm/.restart` exists with content "context pressure at 85%". Working state saved. All changes committed and pushed before sentinel was written.
- **Verification**: `cat .squidsquad/pm/.restart` returns the reason. `git status` shows clean working tree (all committed).

---

### Section C: Branch Switching

---

### TC-24: cycle_pre ensures skill agent is on correct feature branch
- **Precondition**: Skill working-state.md has active task #2050. Branch `squidsquad/skill/2050` exists. Agent is currently on `main`.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Check current branch
- **Expected**: Git is checked out to `squidsquad/skill/2050`. cycle-input.json reflects the active task with branch context.
- **Verification**: `git branch --show-current` returns `squidsquad/skill/2050`.

### TC-25: cycle_pre keeps skill agent on main when no active task
- **Precondition**: Skill working-state.md has no active task (`task: none`). Agent is on `main`.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Check current branch
- **Expected**: Git remains on `main`. cycle-input.json shows `working_state.task: "none"`.
- **Verification**: `git branch --show-current` returns `main`.

### TC-26: cycle_post switches QA from feature branch back to main
- **Precondition**: QA agent is on branch `squidsquad/skill/123` (set by cycle_pre). Agent wrote verification results in cycle-output.json.
- **Steps**:
  1. Confirm current branch is `squidsquad/skill/123`
  2. Run `python references/scripts/cycle_post.py qa`
  3. Check current branch
- **Expected**: Git switched back to `main`. State committed on `main`. No code committed on feature branch by QA.
- **Verification**: `git branch --show-current` returns `main`.

### TC-27: cycle_post commits code to feature branch, state to main (skill)
- **Precondition**: Skill agent on `squidsquad/skill/2050`. Agent modified `src/parser.py`. cycle-output.json declares `code_commit.branch: "squidsquad/skill/2050"` and `state_commit_message` for main.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py skill`
  2. Check commits on feature branch
  3. Check commits on main
- **Expected**: `src/parser.py` committed on `squidsquad/skill/2050`. State files (iteration log, working-state.md, current-state) committed on `main`. No code files on main. No state files on feature branch.
- **Verification**: `git log squidsquad/skill/2050 --oneline -1` shows code commit. `git log main --oneline -1` shows state commit. `git diff squidsquad/skill/2050 main -- src/parser.py` shows the diff.

### TC-28: cycle_pre handles missing feature branch gracefully
- **Precondition**: Skill working-state.md references task #2050 but branch `squidsquad/skill/2050` does not exist (e.g., was deleted or never created).
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Read cycle-input.json
- **Expected**: cycle_pre creates the branch from main (or stays on main and flags the situation). cycle-input.json provides enough context for the agent to decide how to proceed. No crash.
- **Verification**: Script exits 0. cycle-input.json is valid JSON.

---

### Section D: Graceful Degradation

---

### TC-29: cycle_pre handles network down (git pull fails)
- **Precondition**: Network is unreachable. `git pull` will fail. `gh` CLI will fail.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py pm` (with network disconnected or mocked failure)
- **Expected**: cycle-input.json is still written. `pull_result` = "error". Tracker fields (`pending_test_issues`, etc.) are empty arrays. `agent_health` may show "unknown" for all agents. Script exits 0 (degraded, not failed).
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['pull_result']=='error'; assert d['tracker']['pending_test_issues']==[]"`

### TC-30: cycle_pre handles git pull conflict
- **Precondition**: Local changes conflict with remote changes. `git pull --rebase` results in a conflict.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Read cycle-input.json
- **Expected**: `pull_result` = "conflict" or "stash_conflict". cycle-input.json is still valid and contains all other fields. Agent can see the conflict status and decide how to handle it.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['pull_result'] in ['conflict','stash_conflict']"`

### TC-31: cycle_pre handles missing working-state.md
- **Precondition**: `.squidsquad/skill/working-state.md` does not exist (fresh agent, first cycle).
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Read cycle-input.json
- **Expected**: `working_state.task` = "none", `working_state.status` = "none", `working_state.raw_content` = "" or null. No crash.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/skill/cycle-input.json')); assert d['working_state']['task']=='none'"`

### TC-32: cycle_pre handles missing config.md gracefully
- **Precondition**: `config.md` is deleted or corrupt.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py pm`
- **Expected**: Script uses sensible defaults (threshold 70%, branch_workflow false, etc.) or exits with a clear error. Does not crash with an unhandled exception.
- **Verification**: Script exit code is 0 (with defaults) or non-zero (with clear error message).

### TC-33: cycle_post handles missing cycle-output.json (agent crash)
- **Precondition**: Agent crashed mid-cycle. No cycle-output.json exists in `.squidsquad/pm/`.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py pm`
- **Expected**: Script detects missing output file. Logs a warning. Does NOT commit, transition, or modify any state. Exits cleanly (exit code 0 or specific "no output" code). Next cycle's cycle_pre will recover from working-state.md.
- **Verification**: Exit code is 0. No new commits. No tracker changes. Warning message printed.

### TC-34: cycle_post handles push rejection (concurrent push from another agent)
- **Precondition**: Another agent pushed to remote between this agent's pull and push. Push will be rejected.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py skill` (with simulated push rejection)
- **Expected**: cycle_post runs `git pull --rebase` and retries push (up to 3 times). If successful after retry, exits 0. If still failing after 3 retries, stashes state and logs error.
- **Verification**: `git log --oneline -1` shows the commit was pushed (check remote). Or error log shows retry exhaustion.

### TC-35: cycle_post handles invalid JSON in cycle-output.json
- **Precondition**: Agent wrote syntactically invalid JSON to cycle-output.json (truncated, encoding error).
- **Steps**:
  1. Write `{"role": "pm", "cycle_number": 459, ` (truncated) to `.squidsquad/pm/cycle-output.json`
  2. Run `python references/scripts/cycle_post.py pm`
- **Expected**: Clear error message about JSON parse failure. No partial execution. Exit code non-zero.
- **Verification**: Exit code != 0. Error output mentions JSON. No new commits.

---

### Section E: Feature Flag

---

### TC-36: Feature flag "Cycle Runner: no" — agent uses existing Ralph Loop
- **Precondition**: config.md has `Cycle Runner: no`. Agent template contains both old Ralph Loop steps and new cycle_pre/post instructions.
- **Steps**:
  1. Boot an agent (any role)
  2. Observe cycle execution
- **Expected**: Agent follows existing Ralph Loop (15+ bash calls for git, tracker, status bar). Does NOT call cycle_pre.py or cycle_post.py. Behavior is identical to pre-feature state.
- **Verification**: Agent conversation log shows individual bash calls for git pull, tracker queries, status bar writes. No mention of cycle-input.json or cycle-output.json.

### TC-37: Feature flag "Cycle Runner: yes" — agent uses cycle runner
- **Precondition**: config.md has `Cycle Runner: yes`. Agent template has been recomposed with cycle runner instructions.
- **Steps**:
  1. Boot an agent (any role)
  2. Observe cycle execution
- **Expected**: Agent calls `cycle_pre.py` at cycle start, reads cycle-input.json, performs creative work, writes cycle-output.json, calls `cycle_post.py` at cycle end. Only 2 mechanical bash calls per cycle (pre and post).
- **Verification**: Agent conversation log shows exactly 2 script calls (cycle_pre, cycle_post). No individual git pull, tracker query, or status bar write bash calls.

### TC-38: Feature flag missing from config.md — defaults to "no"
- **Precondition**: config.md does not contain a `Cycle Runner` field at all (pre-upgrade install).
- **Steps**:
  1. Boot an agent
  2. Observe cycle execution
- **Expected**: Agent uses existing Ralph Loop. No cycle runner behavior. No error about missing config.
- **Verification**: Same as TC-36.

### TC-39: Feature flag per-role granularity
- **Precondition**: config.md has `Cycle Runner: yes`. Skill template recomposed with cycle runner. PM template NOT yet recomposed (incremental rollout).
- **Steps**:
  1. Boot skill agent — should use cycle runner
  2. Boot PM agent — should use existing Ralph Loop
- **Expected**: Each agent follows its own template. Skill uses cycle runner. PM uses old Ralph Loop. No cross-contamination.
- **Verification**: Skill log shows cycle_pre/post calls. PM log shows individual bash calls.

---

### Section F: Quiet Cycle Detection

---

### TC-40: cycle_pre sets likely_quiet when all queues are empty
- **Precondition**: No pending-test issues, no pending-test tasks, no external issues, no pending-ship tasks, no QA-rejected items, no work queue items.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Read cycle-input.json
- **Expected**: A `likely_quiet: true` field (or equivalent) is set in cycle-input.json. Work queue arrays are all empty.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/skill/cycle-input.json')); assert d.get('likely_quiet', False)==True or (len(d['work_queue']['qa_rejected'])==0 and len(d['work_queue']['queue'])==0)"`

### TC-41: Agent overrides likely_quiet when human input arrives
- **Precondition**: cycle-input.json has `likely_quiet: true`. Human typed a message in the conversation between cycles.
- **Steps**:
  1. Agent reads cycle-input.json, sees `likely_quiet: true`
  2. Agent checks conversation context, finds human input
  3. Agent writes cycle-output.json with `cycle_type: "active"`
- **Expected**: cycle-output.json has `cycle_type: "active"` despite `likely_quiet: true` in input. Agent processed the human's input. ~100 tokens overhead for the override check.
- **Verification**: cycle-output.json `cycle_type` = "active". Human input was processed (filed, discussed, etc.).

### TC-42: Quiet cycle produces minimal output
- **Precondition**: cycle-input.json has `likely_quiet: true`. No human input in conversation. Agent confirms quiet.
- **Steps**:
  1. Agent reads cycle-input.json
  2. Agent writes cycle-output.json with `cycle_type: "quiet"`
  3. Run `python references/scripts/cycle_post.py skill`
- **Expected**: No iteration log created. Commit message is "skill: cycle 165 — quiet, queue empty". Status bar set to `idle|`. Minimal git diff (only current-state and working-state if updated).
- **Verification**: No `iter-165.md` file created. Git commit message matches quiet pattern.

---

### Section G: Status Transitions

---

### TC-43: Valid transition — pending-test to pending-ship (PM/QA)
- **Precondition**: Issue #123 has label `status:pending-test`. Agent is PM or QA.
- **Steps**:
  1. Agent writes cycle-output.json with `status_transitions: [{"number": 123, "from": "pending-test", "to": "pending-ship"}]`
  2. Run `python references/scripts/cycle_post.py pm`
- **Expected**: Transition succeeds. Issue #123 now has `status:pending-ship`.
- **Verification**: `python references/scripts/tracker.py get-labels 123` shows `status:pending-ship`.

### TC-44: Valid transition — approved to in-progress (skill)
- **Precondition**: Issue #2060 has label `status:approved` and `role:skill`.
- **Steps**:
  1. Agent writes cycle-output.json with `status_transitions: [{"number": 2060, "from": "approved", "to": "in-progress"}]`
  2. Run `python references/scripts/cycle_post.py skill`
- **Expected**: Transition succeeds.
- **Verification**: `python references/scripts/tracker.py get-labels 2060` shows `status:in-progress`.

### TC-45: Valid transition — pending-ship to shipped (DM)
- **Precondition**: Issue #789 has label `status:pending-ship`.
- **Steps**:
  1. Agent writes cycle-output.json with `status_transitions: [{"number": 789, "from": "pending-ship", "to": "shipped"}]`
  2. Run `python references/scripts/cycle_post.py dm`
- **Expected**: Transition succeeds. Issue auto-closed by tracker.py.
- **Verification**: `python references/scripts/tracker.py get-state 789` shows `shipped`. `gh issue view 789 --json state` shows `CLOSED`.

### TC-46: Invalid transition — wrong from state
- **Precondition**: Issue #123 currently has `status:approved` but agent declares `from: "pending-test"`.
- **Steps**:
  1. Agent writes cycle-output.json with `status_transitions: [{"number": 123, "from": "pending-test", "to": "pending-ship"}]`
  2. Run `python references/scripts/cycle_post.py pm`
- **Expected**: Transition rejected. Error logged. Issue retains `status:approved`. Other cycle_post operations proceed.
- **Verification**: `python references/scripts/tracker.py get-labels 123` still shows `status:approved`.

### TC-47: Unauthorized transition — skill tries pending-ship to shipped
- **Precondition**: Issue #789 has `status:pending-ship`. Skill agent tries to ship it.
- **Steps**:
  1. Agent writes cycle-output.json with `status_transitions: [{"number": 789, "from": "pending-ship", "to": "shipped"}]`
  2. Run `python references/scripts/cycle_post.py skill`
- **Expected**: Transition rejected (only DM can ship). Error logged. Issue retains `status:pending-ship`.
- **Verification**: `python references/scripts/tracker.py get-labels 789` still shows `status:pending-ship`.

### TC-48: Multiple transitions in single cycle
- **Precondition**: Skill agent picked up #2060 (approved -> in-progress) and completed #2050 (in-progress -> pending-test) in same cycle.
- **Steps**:
  1. Agent writes cycle-output.json with two transitions
  2. Run `python references/scripts/cycle_post.py skill`
- **Expected**: Both transitions succeed independently. If one fails, the other still executes.
- **Verification**: #2060 shows `status:in-progress`. #2050 shows `status:pending-test`.

---

### Section H: PM Hybrid Model

---

### TC-49: PM reads conversation context for human input (not from cycle-input)
- **Precondition**: Human typed "there's a bug in parser.py" between cycles. cycle-input.json has no field for this input (by design — conversation context is not transport).
- **Steps**:
  1. Run cycle_pre.py pm
  2. Agent reads cycle-input.json (gets tracker state, git state, etc.)
  3. Agent reads conversation context (gets human message)
  4. Agent processes both
- **Expected**: Agent uses cycle-input for mechanical context AND conversation history for human input. Files issue after investigation and discussion. cycle-output.json reflects the filed issue.
- **Verification**: cycle-output.json contains `issues_filed` or `human_input_processed` field populated.

### TC-50: PM cycle-input provides tracker state even during human interaction
- **Precondition**: PM is in the middle of a multi-cycle planning discussion with human. cycle_pre runs normally.
- **Steps**:
  1. Run cycle_pre.py pm
  2. Read cycle-input.json
- **Expected**: Tracker state (pending-test issues, health checks, etc.) is fully populated even though the PM is primarily doing interactive work. PM can still check agent health and verify issues alongside discussion.
- **Verification**: cycle-input.json has populated `tracker` and `agent_health` objects.

---

### Section I: Existing Test Suite

---

### TC-51: Existing test suite passes after cycle runner scripts added
- **Precondition**: All tests in `tests/` pass before cycle runner changes. New files `references/scripts/cycle_pre.py` and `references/scripts/cycle_post.py` added.
- **Steps**:
  1. Run `python tests/run_tests.py`
- **Expected**: All existing tests pass. No regressions. New scripts do not break imports, file paths, or shared infrastructure.
- **Verification**: `python tests/run_tests.py` exits 0 with all tests passing.

### TC-52: git_ops.py still works independently of cycle runner
- **Precondition**: `Cycle Runner: no` in config. Agent calls `git_ops.py pull` directly.
- **Steps**:
  1. Run `python references/scripts/git_ops.py pull`
  2. Run `python references/scripts/git_ops.py commit-push pm "manual test"`
- **Expected**: Both commands work exactly as before. No dependency on cycle_pre/post.
- **Verification**: Commands exit 0. Git log shows the commit.

### TC-53: tracker.py still works independently of cycle runner
- **Precondition**: `Cycle Runner: no`. Agent calls tracker.py directly.
- **Steps**:
  1. Run `python references/scripts/tracker.py list-issues skill --status open`
  2. Run `python references/scripts/tracker.py transition 123 pending-test pending-ship --role pm-lead`
- **Expected**: Both commands work exactly as before. No dependency on cycle runner.
- **Verification**: Commands exit 0 with expected output.

### TC-54: health_check.py still works independently of cycle runner
- **Precondition**: `Cycle Runner: no`. Agent calls health_check.py directly.
- **Steps**:
  1. Run `python references/scripts/health_check.py`
- **Expected**: Output is identical to pre-cycle-runner behavior.
- **Verification**: Script exits 0. Output shows per-agent health status.

### TC-55: compose.py regenerates templates correctly with cycle runner content
- **Precondition**: Sub-skills modified for cycle runner (pull-latest simplified, git-commit simplified, etc.). compose.py has not changed.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`
  2. Diff generated CLAUDE.md files against expected output
- **Expected**: All 4 role CLAUDE.md files regenerated. For roles with `Cycle Runner: yes`, mechanical steps replaced with cycle_pre/post calls. Sub-skills properly composed.
- **Verification**: Each generated CLAUDE.md contains "cycle_pre.py" and "cycle_post.py" references (or still contains old steps if flag is "no").

---

### Section J: Transport vs Behavior Separation

---

### TC-56: cycle_pre does not encode workflow decisions
- **Precondition**: cycle_pre.py source code available.
- **Steps**:
  1. Review cycle_pre.py source code
  2. Check for any conditional logic that decides what work to do (as opposed to what state to report)
- **Expected**: cycle_pre only reads state and reports it. It does NOT: decide which issue to work on, determine if a verification passed, classify external issues, decide whether to run tests, choose between fix approaches. All such decisions are left to the agent.
- **Verification**: Code review — no `if` branches that encode PM/QA/skill workflow decisions. Only infrastructure logic (git operations, file reads, tracker queries, error handling).

### TC-57: cycle_post does not encode workflow decisions
- **Precondition**: cycle_post.py source code available.
- **Steps**:
  1. Review cycle_post.py source code
  2. Check for any conditional logic that decides what the agent should have done
- **Expected**: cycle_post only executes the declared operations from cycle-output.json. It does NOT: second-guess transitions, auto-file issues, skip transitions based on its own judgment, add comments the agent didn't request. It validates schema and executes.
- **Verification**: Code review — cycle_post only reads cycle-output.json and executes declared operations. Validation is schema-level (field types, legal transitions), not behavior-level.

### TC-58: Agent retains bash access for creative work
- **Precondition**: `Cycle Runner: yes`. Agent template recomposed.
- **Steps**:
  1. Boot skill agent
  2. Agent picks up a task
  3. Agent runs `python tests/run_tests.py` (test execution)
  4. Agent reads source code via file reads
  5. Agent spawns subagent (if QA)
- **Expected**: All bash operations for creative work succeed. Agent is not blocked from running tests, reading files, or spawning subagents. Only boilerplate bash (git pull, status bar, tracker queries) is handled by cycle_pre/post.
- **Verification**: Agent successfully runs tests and reads files during creative phase.

---

### Section K: Upgrade Verification

---

### TC-59: Fresh install with Cycle Runner: no (default)
- **Precondition**: New SquidSquad install. No prior config.
- **Steps**:
  1. Run setup flow
  2. Check config.md
- **Expected**: `Cycle Runner: no` present in config.md (or field absent, defaulting to no). Agent behavior unchanged from pre-feature state.
- **Verification**: Config.md does not have `Cycle Runner: yes`. Agent uses Ralph Loop.

### TC-60: Existing install upgraded — scripts deployed, flag stays "no"
- **Precondition**: Existing install with active agents. Pre-upgrade state committed.
- **Steps**:
  1. Run `/squidsquad-upgrade`
  2. Check new files exist
  3. Check config.md
  4. Boot agents
- **Expected**: `references/scripts/cycle_pre.py` and `cycle_post.py` exist. Config.md has `Cycle Runner: no` (default for existing installs). All agents continue using existing Ralph Loop. No behavior change.
- **Verification**: New script files exist. Agents use old Ralph Loop. No errors during upgrade.

### TC-61: Existing install opts in — flag changed to "yes", templates recomposed
- **Precondition**: Existing install with `Cycle Runner: no`. Scripts already deployed.
- **Steps**:
  1. Change config.md to `Cycle Runner: yes`
  2. Run `python references/scripts/compose.py deploy-all`
  3. Boot agents
- **Expected**: Agent templates regenerated with cycle_pre/post instructions. Agents use cycle runner on next boot. Working-state.md from previous sessions is correctly read by cycle_pre.
- **Verification**: CLAUDE.md files contain cycle_pre/post instructions. Agent uses cycle runner.

### TC-62: Upgrade does not break running agents
- **Precondition**: Agents are actively running. Upgrade introduces new scripts and config values.
- **Steps**:
  1. Run upgrade while agents are mid-cycle
  2. Observe agent behavior
- **Expected**: Running agents complete their current cycle with old behavior (they read their template at boot, not mid-cycle). On next restart (or context reset), agents pick up new templates. No crash, no lost state.
- **Verification**: No agent crashes during upgrade. Next cycle after restart uses updated template.

### TC-63: Downgrade — flag changed back to "no"
- **Precondition**: Install was using `Cycle Runner: yes`. Admin changes to `Cycle Runner: no`.
- **Steps**:
  1. Change config.md to `Cycle Runner: no`
  2. Run `python references/scripts/compose.py deploy-all`
  3. Boot agents
- **Expected**: Agent templates regenerated with old Ralph Loop steps. cycle_pre/post scripts still exist but are not called. Agents resume old behavior. No stale cycle-input.json or cycle-output.json interfere.
- **Verification**: Agents use old Ralph Loop. No errors from leftover JSON files.

### TC-64: Partial upgrade — scripts exist but template not recomposed
- **Precondition**: cycle_pre.py and cycle_post.py deployed. Templates NOT recomposed (forgot to run compose.py). `Cycle Runner: yes` in config.
- **Steps**:
  1. Boot agent
- **Expected**: Agent template still has old Ralph Loop instructions (since compose.py wasn't run). Agent uses old behavior. The mismatch between config flag and template is tolerable — agents follow their template, not the config flag directly.
- **Verification**: Agent uses old Ralph Loop despite config saying "yes". No crash.

---

### Section L: Agent Crash Recovery

---

### TC-65: Agent crash — no cycle-output.json, next cycle recovers
- **Precondition**: Agent crashed after cycle_pre ran but before writing cycle-output.json. working-state.md has an active task.
- **Steps**:
  1. Simulate: run cycle_pre.py, then delete any cycle-output.json
  2. Run cycle_pre.py again (next cycle)
- **Expected**: cycle_pre detects missing or stale cycle-output.json. Loads working-state.md. Generates cycle-input.json with active task context from working state. Agent can resume work.
- **Verification**: cycle-input.json `working_state.task` matches the task from working-state.md. No data loss.

### TC-66: Agent crash — partial cycle-output.json written
- **Precondition**: Agent wrote partial cycle-output.json (valid JSON but missing required fields like `cycle_type`).
- **Steps**:
  1. Write partial JSON to cycle-output.json
  2. Run `python references/scripts/cycle_post.py pm`
- **Expected**: cycle_post detects incomplete output. Logs error. Does not execute partial operations. Next cycle's cycle_pre recovers from working-state.md.
- **Verification**: Exit code non-zero. No partial commits or transitions.

### TC-67: cycle-output.json from previous cycle does not contaminate next cycle
- **Precondition**: Previous cycle's cycle-output.json still exists when cycle_pre runs for the new cycle.
- **Steps**:
  1. Leave old cycle-output.json in place
  2. Run cycle_pre.py
  3. Agent writes new cycle-output.json (overwrites old)
  4. Run cycle_post.py
- **Expected**: cycle_pre ignores or cleans up old cycle-output.json. cycle_post processes only the new output. No duplicate transitions or commits from the previous cycle.
- **Verification**: Only one set of transitions executed. Commit messages match current cycle number.

---

### Section M: E2E Test Result Handling

---

### TC-68: cycle_pre runs E2E tests for QA role and includes results
- **Precondition**: E2E test command configured in config.md. QA role.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py qa`
  2. Read cycle-input.json
- **Expected**: `e2e_test_result` object populated with `result` ("passed"/"failed"), `tests_run` count, and `failures` array. Tests were actually executed by cycle_pre.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/qa/cycle-input.json')); assert d['e2e_test_result']['result'] in ['passed','failed','skipped']"`

### TC-69: E2E tests not configured — result shows skipped
- **Precondition**: No E2E test command in config.md. QA role.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py qa`
  2. Read cycle-input.json
- **Expected**: `e2e_test_result.result` = "skipped". No error.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/qa/cycle-input.json')); assert d['e2e_test_result']['result']=='skipped'"`

---

### Section N: Template Change Detection

---

### TC-70: cycle_pre detects template change
- **Precondition**: `.squidsquad/pm/CLAUDE.md` was modified after the current session started (e.g., compose.py regenerated it).
- **Steps**:
  1. Touch `.squidsquad/pm/CLAUDE.md` to update mtime
  2. Run `python references/scripts/cycle_pre.py pm`
  3. Read cycle-input.json
- **Expected**: `template_changed` = true. Agent knows to trigger self-restart at cycle end.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['template_changed']==True"`

### TC-71: cycle_pre reports no template change when template is unchanged
- **Precondition**: `.squidsquad/pm/CLAUDE.md` not modified since session start.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py pm`
  2. Read cycle-input.json
- **Expected**: `template_changed` = false.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['template_changed']==False"`

---

## Smoke Tests

- [ ] `python references/scripts/cycle_pre.py pm` exits 0 and produces valid JSON at `.squidsquad/pm/cycle-input.json`
- [ ] `python references/scripts/cycle_pre.py skill` exits 0 and produces valid JSON at `.squidsquad/skill/cycle-input.json`
- [ ] `python references/scripts/cycle_pre.py qa` exits 0 and produces valid JSON at `.squidsquad/qa/cycle-input.json`
- [ ] `python references/scripts/cycle_pre.py dm` exits 0 and produces valid JSON at `.squidsquad/dm/cycle-input.json`
- [ ] cycle-input.json `role` field matches the argument passed to cycle_pre
- [ ] cycle-input.json `cycle_number` is a positive integer
- [ ] cycle-input.json `timestamp` is a valid ISO 8601 string
- [ ] `python references/scripts/cycle_post.py pm` with a minimal valid cycle-output.json exits 0
- [ ] cycle_post creates no commits when cycle-output.json is missing (agent crash case)
- [ ] `python tests/run_tests.py` passes with new scripts in place
- [ ] `Cycle Runner: no` config results in no cycle_pre/post calls from agent template
- [ ] cycle-input.json and cycle-output.json are listed in `.gitignore`
- [ ] cycle_pre writes `working` status to current-state at start
- [ ] cycle_post writes `idle|` to current-state at end
- [ ] `python references/scripts/git_ops.py pull` still works independently

## Regression Risks

- **git_ops.py internal changes**: cycle_pre/post compose git_ops.py functions. If git_ops.py internals change (function signatures, return values), cycle runner scripts may break silently. Watch for: git_ops.py refactors that don't update cycle_pre/post.
- **tracker.py API changes**: cycle_pre queries tracker.py for work queues; cycle_post calls transitions and comments. If tracker.py label format or CLI args change, cycle runner fails. Watch for: tracker.py label taxonomy updates.
- **config.py field additions**: New config fields may not be propagated to cycle-input.json. Watch for: new config values that agents need but cycle_pre doesn't include.
- **compose.py sub-skill changes**: Sub-skills that encode mechanical steps (pull-latest, git-commit, iteration-log) are simplified or removed. If compose.py template rendering changes, generated CLAUDE.md files may have stale or missing instructions. Watch for: compose.py changes that don't account for cycle runner mode.
- **Status bar format changes**: cycle_pre/post write to current-state. If statusline.py changes the expected format, status display breaks. Watch for: statusline format changes.
- **Working-state.md format drift**: cycle_pre parses working-state.md for task, status, phase. If agents change the format (new fields, different markdown structure), parsing breaks. Watch for: working-state format changes in role templates.
- **Multiple agents sharing config.md**: cycle_post may read-modify-write config.md (ship counter, version). If two agents do this simultaneously, race condition on counter values. Watch for: concurrent config.md writes from DM bump + PM ship counter.
- **Branch existence assumptions**: cycle_pre assumes feature branches exist when working-state references a task. If branches are deleted externally (manual cleanup, GitHub auto-delete), checkout fails. Watch for: stale branch references in working-state.md.
- **cycle-output.json schema evolution**: As new features are added, cycle-output.json gains new fields. If cycle_post validation is too strict (rejects unknown fields), forward-compatible agent outputs break. If too lenient, typos in field names cause silent data loss. Watch for: schema version mismatches between agent template and cycle_post.py.
- **Vault remember timing**: vault_remember runs during creative phase but vault_optimize moves to cycle_post. If the boundary is wrong, vault writes may be double-counted or skipped. Watch for: vault write budget tracking across the pre/creative/post boundary.
- **PM hybrid model conversation leakage**: PM reads conversation context during creative phase. If cycle_pre accidentally clears conversation state or if cycle_post commits state that suggests human input was processed when it wasn't, PM may miss or double-process human messages. Watch for: human input handling across cycle boundaries.
- **QA single-item-per-cycle throughput**: Moving from multi-item verification to one-item-per-cycle may cause verification backlog if many items land simultaneously. Watch for: growing pending-test queue with QA unable to keep up.
