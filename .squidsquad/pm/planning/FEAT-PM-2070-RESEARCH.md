# FEAT-PM-2070 Research — Cycle Runner Script

## Summary

This task proposes splitting the Ralph Loop into two deterministic Python scripts (`cycle_pre.py` and `cycle_post.py`) that handle all mechanical shell operations, with the agent doing only creative work in between. Today, every agent role (PM, skill, QA, DM) executes 10-20+ bash tool calls per cycle for boilerplate operations: git pull, git push, status bar writes, context pressure reads, tracker queries, commit operations, branch switching, iteration logging, and health checks. These consume significant context window tokens and introduce non-deterministic failure modes when the LLM constructs shell commands from prose instructions.

The proposed architecture is: `cycle_pre.py` runs before the agent thinks (handles git pull, branch setup, context pressure check, working state read, tracker queries, triage) and writes a `cycle-input.json` file. The agent reads this JSON, performs its creative work (reasoning, code analysis, code writing, verification, human interaction), and writes a `cycle-output.json` file describing what it did. Then `cycle_post.py` runs after the agent finishes (handles commits, pushes, status transitions, iteration logging, status bar writes, self-restart sentinel).

The change is architecturally significant but well-bounded. The existing `references/scripts/` infrastructure already centralizes most operations (`git_ops.py`, `cycle.py`, `tracker.py`, `config.py`, `health_check.py`, `triage.py`). The cycle runner scripts would compose these existing scripts rather than reimplementing them. The main risk is that PM and QA have interactive/multi-step creative work that interleaves with mechanical operations (PM's human discussion flow, QA's branch-checkout-verify-switch-back pattern), requiring careful boundary design.

## Per-Role Analysis

### PM Agent

#### Current Steps (Mechanical vs Creative)

| Step | Description | Classification | Notes |
|------|-------------|---------------|-------|
| Step 1 — Pull Latest | `python references/scripts/git_ops.py pull` | MECHANICAL | Direct script call |
| Step 1b — Context Pressure Check | Read context-pressure file, compare to threshold | MECHANICAL | File read + comparison |
| Step 1c — Resume Working State | Read working-state.md, check for planning phase suppression | MECHANICAL (read) + CREATIVE (decision to suppress) | Suppression logic is deterministic, can be scripted |
| Step 1d — (not present for PM) | — | — | PM uses /loop, no interval sync |
| Step 2 — Check In With Human | Print non-blocking message, process human input | CREATIVE | Core PM function — discussion, investigation, filing |
| Step 3 — Run E2E Tests | Run test command (if QA absent) | MECHANICAL | Direct command execution |
| Step 4 — Investigate Test Failures | Analyze failures, investigate root cause, present to human | CREATIVE | Requires reasoning and code reading |
| Step 5 — Verify Fixed Issues | Query tracker, run tests, verify fixes | MIXED — query is MECHANICAL, verification is CREATIVE | Tracker query can be pre-fetched; verification requires reading code |
| Step 6 — Verify Pending Test Tasks | Query tracker, test against acceptance criteria | MIXED | Same as Step 5 |
| Step 6b — Monitor PRs | List PRs, check state, update tracker | MECHANICAL | Deterministic PR state checks |
| Step 6c — Increment Ship Counter | Update config.md counter | MECHANICAL | Simple counter increment |
| Step 6d — PM Delivery Fallback | Update docs, prepare CHANGELOG, mark shipped | CREATIVE (doc writing) + MECHANICAL (transitions) | Doc updates need agent creativity |
| Step 6e — Post-Merge Recompose | Detect merged branches, run compose.py | MECHANICAL | All deterministic |
| Step 7 — Agent Health Check | Run health_check.py, log results | MECHANICAL | Direct script call |
| Step 7b — Triage External Issues | List unlabeled issues, classify, route, label | MIXED — listing is MECHANICAL, classification is CREATIVE | Agent needs to read issue content to classify |
| Step 4b — Vault Remember | Reflect on cycle, decide vault writes | CREATIVE | Requires evaluating cycle work |
| Vault Optimize | Run vault_optimize.py | MECHANICAL | Direct script call |
| Step 8 — Log Iteration | Write iter-N.md, cleanup old logs | MECHANICAL | Deterministic format |
| Step 9 — Commit and Push | git_ops.py commit-push | MECHANICAL | Direct script call |
| Self-Restart | Check triggers, write sentinel | MECHANICAL | Deterministic checks |
| Step 10 — Done | Print marker | MECHANICAL | Trivial |
| Status bar writes | ~10 echo commands per cycle | MECHANICAL | Every step writes current-state |
| Timestamp fetches | ~10 cycle.py timestamp calls | MECHANICAL | Every step fetches time |
| Task Intake (Phases 1-3) | Research, discussion, planning | CREATIVE | Entirely agent reasoning + human interaction |

#### cycle-input.json needs

```json
{
  "role": "pm",
  "cycle_number": 459,
  "timestamp": "2026-04-21T14:30:00",
  "pull_result": "ok" | "conflict" | "stash_conflict",
  "context_pressure": {
    "used_pct": 42,
    "threshold": 70,
    "exceeded": false
  },
  "working_state": {
    "task": "#2070" | "none",
    "status": "in-progress" | "none",
    "phase": "researching #2070" | null,
    "suppressed": false,
    "raw_content": "..."
  },
  "qa_present": true,
  "dm_present": true,
  "e2e_test_result": null,
  "tracker": {
    "pending_test_issues": [{"number": 123, "title": "...", "role": "skill"}],
    "pending_test_tasks": [{"number": 456, "title": "...", "role": "skill"}],
    "pending_ship_tasks": [{"number": 789, "title": "..."}],
    "external_issues": [{"number": 101, "title": "...", "body": "..."}],
    "open_prs": [{"number": 10, "title": "...", "state": "OPEN"}]
  },
  "agent_health": {
    "skill": "healthy",
    "qa": "stalled",
    "dm": "healthy"
  },
  "config": {
    "branch_workflow": true,
    "pr_flow": false,
    "auto_merge": true,
    "improvement_scanning": true,
    "vault_remember": true,
    "vault_optimize": true,
    "ship_threshold": 10,
    "shipped_since_bump": 13
  },
  "merged_branches": [],
  "template_changed": false
}
```

#### cycle-output.json produces

```json
{
  "role": "pm",
  "cycle_number": 459,
  "cycle_type": "active" | "quiet" | "suppressed",
  "human_input_processed": "Filed #2071 from user bug report" | null,
  "issues_filed": [{"number": 2071, "role": "skill", "title": "..."}],
  "issues_verified": [{"number": 123, "result": "pass" | "fail", "comment": "..."}],
  "tasks_verified": [{"number": 456, "result": "pass" | "fail", "comment": "..."}],
  "tasks_shipped": [{"number": 789, "delivery_skip": true}],
  "status_transitions": [
    {"number": 123, "from": "pending-test", "to": "pending-ship"}
  ],
  "tracker_comments": [
    {"number": 123, "message": "Verified — zero gaps. Status → Pending Ship."}
  ],
  "external_issues_triaged": [
    {"number": 101, "type": "issue", "role": "skill", "priority": "low"}
  ],
  "health_alerts": [
    {"role": "qa", "status": "stalled", "elapsed_minutes": 75}
  ],
  "vault_writes": [
    {"action": "create", "path": "galaxy/decision-foo.md"}
  ],
  "iteration_summary": "Verified #123, filed #2071, QA stalled",
  "commit_message": "pm: cycle 459 — verified #123, filed #2071",
  "version_bump": null,
  "restart_needed": false,
  "restart_reason": null
}
```

#### Edge Cases

- **Planning phase suppression**: When `working_state.phase` is set (e.g., "researching #2070"), cycle_pre must detect this and set `suppressed: true`. The agent then only runs health check (already in cycle-input) and skips everything else. cycle_post commits and writes idle state.
- **Task Intake (Phases 1-3)**: This is a multi-cycle, interactive process. The agent spawns subagents, interacts with the human, and blocks on `AskUserQuestion`. cycle_pre/post wraps each cycle, but planning phases span cycles via working-state persistence. The phase flag in working-state drives suppression of normal cycle work.
- **PM Delivery Fallback**: When DM is absent, PM writes docs. This is creative work, but the ship counter increment and status transitions are mechanical and belong in cycle_post.
- **Human input between cycles**: Human may type messages between cycles. This input is already available in the conversation context — cycle_pre cannot capture it. The agent must still read conversation history. cycle_pre can only provide tracker state.

### Skill Agent

#### Current Steps (Mechanical vs Creative)

| Step | Description | Classification | Notes |
|------|-------------|---------------|-------|
| Step 1 — Pull Latest | `git_ops.py pull` | MECHANICAL | |
| Step 1b — Context Pressure Check | Read file, compare threshold | MECHANICAL | |
| Step 1c — Resume Working State | Read working-state.md | MECHANICAL (read) | Decision to resume is trivial |
| Step 1d — Interval Sync | Read config, compare, reschedule | MECHANICAL | |
| Step 2 — Pick Up Work | Query QA-rejected, then work-queue | MECHANICAL (queries) + CREATIVE (reading issue details) | triage.py and tracker.py handle queue |
| Step 2 — Fix Issue | Read code, locate bug, write fix | CREATIVE | Core dev function |
| Step 2b — Implement Task | Read planning artifacts, implement code, run tests | CREATIVE | Core dev function |
| Step 2b — Read Planning Artifacts | Read RESEARCH.md, CONTEXT.md, TEST-PLAN.md | CREATIVE | Agent must understand and follow |
| Step 2 — Run Tests | `python tests/run_tests.py` | MECHANICAL | Direct command execution |
| Step 2 — Verify Changes Exist | `git_ops.py has-changes` | MECHANICAL | |
| Improvement Scan | Select files, scan, file findings | CREATIVE | Requires domain expertise |
| Step 4 — Log Iteration | `cycle.py log-iteration` | MECHANICAL | |
| Step 4b — Vault Remember | Reflect, decide vault writes | CREATIVE | |
| Vault Optimize | `vault_optimize.py run` | MECHANICAL | |
| Step 5 — Commit and Push | Branch workflow: commit-code + commit-state | MECHANICAL | Complex branch logic already in git_ops.py |
| Self-Restart | Check triggers, write sentinel | MECHANICAL | |
| Step 6 — Done | Print marker | MECHANICAL | |
| Status bar writes | ~8 writes per cycle | MECHANICAL | |
| Timestamp fetches | ~8 calls per cycle | MECHANICAL | |

#### cycle-input.json needs

```json
{
  "role": "skill",
  "cycle_number": 165,
  "timestamp": "2026-04-21T14:30:00",
  "pull_result": "ok",
  "context_pressure": {
    "used_pct": 35,
    "threshold": 70,
    "exceeded": false
  },
  "working_state": {
    "task": "#2050" | "none",
    "status": "in-progress" | "none",
    "completed_steps": ["..."],
    "remaining_steps": ["..."],
    "key_decisions": ["..."],
    "raw_content": "..."
  },
  "work_queue": {
    "qa_rejected": [{"number": 2050, "title": "...", "feedback": "..."}],
    "queue": [
      {"number": 2045, "type": "issue", "priority": "high", "title": "..."},
      {"number": 2060, "type": "task", "priority": "medium", "title": "..."}
    ]
  },
  "planning_artifacts": {
    "2060": {
      "research": ".squidsquad/pm/planning/FEAT-SKILL-2060-RESEARCH.md",
      "context": ".squidsquad/pm/planning/FEAT-SKILL-2060-CONTEXT.md",
      "test_plan": ".squidsquad/pm/planning/FEAT-SKILL-2060-TEST-PLAN.md"
    }
  },
  "config": {
    "branch_workflow": true,
    "pr_flow": false,
    "improvement_scanning": true,
    "vault_remember": true,
    "vault_optimize": true,
    "test_command": "python tests/run_tests.py"
  },
  "quiet_cycle_counter": 2,
  "interval_minutes": 30,
  "interval_changed": false,
  "template_changed": false
}
```

#### cycle-output.json produces

```json
{
  "role": "skill",
  "cycle_number": 165,
  "cycle_type": "active" | "quiet",
  "work_done": {
    "task_number": 2050,
    "action": "fix" | "implement" | "resume",
    "result": "pending-test" | "in-progress" | "blocked",
    "commit_message": "Fixed null check in parser.py",
    "files_changed": ["src/parser.py", "tests/test_parser.py"],
    "test_result": "pass" | "fail"
  },
  "status_transitions": [
    {"number": 2050, "from": "approved", "to": "in-progress"},
    {"number": 2050, "from": "in-progress", "to": "pending-test"}
  ],
  "tracker_comments": [
    {"number": 2050, "message": "Fixed in commit abc123. Status → Pending Test."}
  ],
  "issues_filed": [],
  "improvement_scan": {
    "files_scanned": ["src/foo.py", "src/bar.py"],
    "findings": [{"title": "...", "role": "skill", "severity": "low"}]
  },
  "vault_writes": [],
  "iteration_summary": "Fixed #2050, tests passing",
  "code_commit": {
    "branch": "squidsquad/skill/2050",
    "message": "skill: fixed null check in parser.py",
    "pr_needed": true,
    "pr_title": "skill: #2050 — Fix null check in parser"
  },
  "state_commit_message": "skill: cycle 165 — fixed #2050",
  "working_state_update": "...",
  "restart_needed": false
}
```

#### Edge Cases

- **Active coding mid-cycle**: The skill agent may be mid-implementation when context pressure hits. Working state must capture enough detail for the next session to resume. cycle_pre loads this; cycle_post saves it.
- **Branch workflow**: When branch_workflow is enabled, cycle_post must handle the complex commit-code/commit-state split. The agent never touches git — it just declares what files changed and what the commit message should be. cycle_post calls `git_ops.py commit-code` and `git_ops.py commit-state`.
- **Test failures**: If tests fail, the agent keeps working (status stays in-progress). cycle_output signals `test_result: fail` and cycle_post does NOT transition status.
- **PR creation**: When marking pending-test with branch_workflow, cycle_post creates the PR. The agent provides the PR title and body in cycle-output.
- **QA-rejected rework**: cycle_pre surfaces QA-rejected items at the top of the queue. The agent reads the feedback and fixes. This is the same flow as normal work, just with different input priority.

### QA Agent

#### Current Steps (Mechanical vs Creative)

| Step | Description | Classification | Notes |
|------|-------------|---------------|-------|
| Step 1 — Pull Latest | `git_ops.py pull` | MECHANICAL | |
| Step 1b — Context Pressure Check | Read file, compare | MECHANICAL | |
| Step 1c — Resume Working State | Read working-state.md | MECHANICAL | |
| Step 1d — Interval Sync | Config read, reschedule | MECHANICAL | |
| Step 2 — Run E2E Tests | Run test command | MECHANICAL | |
| Step 3 — Investigate Test Failures | Analyze failures, classify, file | CREATIVE | Requires understanding failure domain |
| Step 4 — Verify Fixed Issues | Query tracker, checkout branch, run tests, verify | MIXED | Branch checkout is MECHANICAL, verification is CREATIVE |
| Step 5 — Verify Pending Test Tasks | Query, checkout branch, spawn QA subagent, review results | MIXED | Branch checkout MECHANICAL, test execution CREATIVE |
| Step 5b — Monitor PRs | List PRs, check state | MECHANICAL | |
| Step 6 — Agent Health Check | Read current-state files, compare mtime | MECHANICAL | |
| Step 7 — Log Iteration | Write iter-N.md | MECHANICAL | |
| Step 8 — Commit and Push | `git_ops.py commit-push` | MECHANICAL | |
| Self-Restart | Check triggers | MECHANICAL | |
| Status bar writes | ~8 per cycle | MECHANICAL | |

#### cycle-input.json needs

```json
{
  "role": "qa",
  "cycle_number": 133,
  "timestamp": "2026-04-21T14:30:00",
  "pull_result": "ok",
  "context_pressure": {
    "used_pct": 28,
    "threshold": 70,
    "exceeded": false
  },
  "working_state": {
    "task": "none",
    "status": "none",
    "raw_content": "..."
  },
  "e2e_test_result": {
    "result": "passed" | "failed" | "skipped",
    "tests_run": 42,
    "failures": ["test_foo", "test_bar"]
  },
  "verification_queue": {
    "pending_test_issues": [
      {"number": 123, "title": "...", "role": "skill", "branch": "squidsquad/skill/123"}
    ],
    "pending_test_tasks": [
      {"number": 456, "title": "...", "role": "skill", "branch": "squidsquad/skill/456",
       "test_plan_path": ".squidsquad/pm/planning/FEAT-SKILL-456-TEST-PLAN.md"}
    ]
  },
  "open_prs": [],
  "agent_health": {
    "skill": "healthy",
    "pm": "healthy",
    "dm": "unknown"
  },
  "config": {
    "pr_flow": false,
    "branch_workflow": true,
    "iteration_interval": 30
  },
  "template_changed": false
}
```

**Critical note on branch switching**: QA's verification requires checking out feature branches. Today, the agent calls `git_ops.py branch-switch squidsquad/skill/123`, verifies, then switches back to main. With the cycle runner model, there are two options:

1. **cycle_pre handles branch checkout per item**: cycle_pre checks out the branch, sets up context, and the agent verifies one item per cycle. cycle_post switches back. Simple but limits throughput.
2. **Agent still manages branch switching**: The agent reads cycle-input to know which items need verification, but still calls git commands to switch branches during creative work. This breaks the "agent never touches git" principle but preserves multi-item-per-cycle throughput.

**Recommendation**: Option 1. One verification item per cycle is fine — QA cycles are frequent (every 30 min). cycle_pre detects the first pending-test item, checks out its branch, and provides the branch context. cycle_post switches back to main after the agent verifies.

#### cycle-output.json produces

```json
{
  "role": "qa",
  "cycle_number": 133,
  "cycle_type": "active" | "quiet",
  "e2e_log": {
    "result": "passed",
    "tests_run": 42,
    "failures": []
  },
  "issues_filed": [
    {"number": 2071, "role": "skill", "title": "...", "severity": "high", "objective": true}
  ],
  "issues_verified": [
    {"number": 123, "result": "pass" | "fail", "comment": "Verified — zero gaps."}
  ],
  "tasks_verified": [
    {"number": 456, "result": "pass" | "fail", "comment": "FAIL. [findings].",
     "qa_results_path": ".squidsquad/qa/planning/FEAT-SKILL-456-QA-RESULTS.md",
     "delivery_skip": false}
  ],
  "status_transitions": [
    {"number": 123, "from": "pending-test", "to": "pending-ship"},
    {"number": 456, "from": "pending-test", "to": "in-progress"}
  ],
  "tracker_comments": [
    {"number": 123, "message": "Verified — zero gaps. Status → Pending Ship."}
  ],
  "pr_actions": [
    {"pr_number": 10, "action": "approve" | "request-changes", "comment": "..."}
  ],
  "health_alerts": [
    {"role": "dm", "status": "unknown"}
  ],
  "iteration_summary": "Verified #123 (pass), tested #456 (fail)",
  "commit_message": "qa: cycle 133 — verified #123, rejected #456",
  "restart_needed": false
}
```

#### Edge Cases

- **Branch checkout for verification**: As discussed above — cycle_pre should handle checkout, cycle_post should handle switch-back. If multiple items need verification, process one per cycle.
- **Spawning QA subagent for test plan execution**: The subagent spawning is creative work, but the subagent itself runs verification commands. The agent must still have bash access to spawn agents and run verification commands. cycle_pre can't pre-run verification — it doesn't know what to verify.
- **Objective vs subjective findings**: Classification of test failures requires agent judgment. Filing objective issues is mechanical once classified; flagging subjective findings is creative.

### DM Agent

#### Current Steps (Mechanical vs Creative)

| Step | Description | Classification | Notes |
|------|-------------|---------------|-------|
| Step 1 — Pull Latest | `git_ops.py pull` | MECHANICAL | |
| Step 1b — Context Pressure Check | Read file, compare | MECHANICAL | |
| Step 1c — Resume Working State | Read working-state.md | MECHANICAL | |
| Step 1d — Interval Sync | Config read, reschedule | MECHANICAL | |
| Step 1e — Triage Bugs | Query bugs, read, fix docs | MIXED — query MECHANICAL, doc fixes CREATIVE | |
| Step 2 — Scan Pending Ship | Query tracker | MECHANICAL | |
| Step 2b — Check delivery:skip | Read Discussion for tag | MECHANICAL | |
| Step 2c — Create Delivery Package | Update README, SKILL.md, CHANGELOG | CREATIVE | Core DM function |
| Step 3 — Version Bump Check | Read counters, check open issues, bump | MECHANICAL | All deterministic |
| Step 4 — Log Iteration | Write iter-N.md | MECHANICAL | |
| Step 5 — Commit and Push | `git_ops.py commit-push` | MECHANICAL | |
| Self-Restart | Check triggers | MECHANICAL | |
| Status bar writes | ~6 per cycle | MECHANICAL | |

#### cycle-input.json needs

```json
{
  "role": "dm",
  "cycle_number": 45,
  "timestamp": "2026-04-21T14:30:00",
  "pull_result": "ok",
  "context_pressure": {
    "used_pct": 15,
    "threshold": 70,
    "exceeded": false
  },
  "working_state": {
    "task": "none",
    "status": "none",
    "raw_content": "..."
  },
  "bugs": [
    {"number": 2072, "title": "README typo", "status": "open"}
  ],
  "pending_ship": [
    {"number": 789, "title": "New parser feature", "delivery_skip": false,
     "discussion_entries": ["..."]}
  ],
  "version_bump": {
    "ship_threshold": 10,
    "shipped_since_bump": 13,
    "bump_due": true,
    "open_issues_count": 0,
    "current_version": "0.23.0"
  },
  "config": {
    "branch_workflow": true,
    "pr_flow": false
  },
  "template_changed": false
}
```

#### cycle-output.json produces

```json
{
  "role": "dm",
  "cycle_number": 45,
  "cycle_type": "active" | "quiet",
  "bugs_fixed": [
    {"number": 2072, "commit_hash": "abc123"}
  ],
  "deliveries": [
    {"number": 789, "docs_updated": ["README.md", "SKILL.md"],
     "changelog_text": "#789 — New parser feature",
     "config_changes": [], "migration_steps": []}
  ],
  "status_transitions": [
    {"number": 789, "from": "pending-ship", "to": "shipped"}
  ],
  "tracker_comments": [
    {"number": 789, "message": "Delivery complete. Docs updated, CHANGELOG prepared. Status → Shipped."}
  ],
  "version_bump": {
    "new_version": "0.24.0",
    "items_included": [789, 790, 791]
  },
  "iteration_summary": "Delivered #789, bumped to v0.24.0",
  "commit_message": "dm: cycle 45 — delivered #789",
  "restart_needed": false
}
```

#### Edge Cases

- **Version bump sequence**: The bump involves updating config.md, SKILL.md, CHANGELOG.md, committing, tagging, and pushing. This is fully deterministic and should be entirely in cycle_post. The agent just signals `version_bump: {new_version: "0.24.0"}` and cycle_post executes the full sequence.
- **DM bug fixes**: DM fixes doc bugs (README, CHANGELOG). The creative work is writing the fix. The status transition is mechanical. Same pattern as skill.
- **delivery:skip handling**: cycle_pre can pre-compute this from Discussion entries. If delivery:skip is detected, cycle_pre can flag it. The agent can then just confirm the skip and cycle_post handles the transition. No creative work needed — this could even be fully automated in cycle_pre, though that changes the "agent decides" principle.

## Impact Analysis

- **Files touched**:
  - NEW: `references/scripts/cycle_pre.py` — pre-cycle mechanical operations
  - NEW: `references/scripts/cycle_post.py` — post-cycle mechanical operations
  - MODIFIED: `.squidsquad/pm/CLAUDE.md` — Ralph Loop restructured
  - MODIFIED: `.squidsquad/skill/CLAUDE.md` — Ralph Loop restructured
  - MODIFIED: `.squidsquad/qa/CLAUDE.md` — Ralph Loop restructured
  - MODIFIED: `.squidsquad/dm/CLAUDE.md` — Ralph Loop restructured
  - MODIFIED: `references/sub-skills/` — all sub-skills that contain mechanical steps
  - MODIFIED: `references/scripts/compose.py` — if template structure changes
  - EXISTING USED: `references/scripts/git_ops.py`, `tracker.py`, `cycle.py`, `config.py`, `health_check.py`, `triage.py` — all called by cycle_pre/post

- **Behavior changes**:
  - Agents no longer call bash for git, tracker, or status bar operations
  - Agent instructions shrink dramatically (mechanical steps removed from CLAUDE.md)
  - cycle-input.json and cycle-output.json become the API contract between scripts and agent
  - Agents still need bash access for: running tests, reading code, spawning subagents, running verification commands
  - Quiet cycle detection moves to cycle_pre (no work items = quiet)

- **Dependencies**:
  - All existing `references/scripts/*.py` scripts — composed by cycle_pre/post
  - `/loop` command — still handles timing, but now invokes cycle_pre → agent → cycle_post
  - `gh` CLI — still needed by tracker.py (called from cycle_pre/post)
  - `.squidsquad/.local-config` — health check cross-clone paths

## Side Effects

- **Risk 1**: Agent loses ability to react to mid-cycle events — Severity: M — Mitigation: cycle-input provides all known state upfront; truly urgent mid-cycle events (human typing) are still in conversation context
- **Risk 2**: cycle-output.json schema drift as features evolve — Severity: M — Mitigation: version the schema, validate in cycle_post, fail loudly on unknown fields
- **Risk 3**: Branch checkout in cycle_pre for QA means only one verification per cycle — Severity: L — Mitigation: 30-min cycles are frequent; batch verification in future version
- **Risk 4**: Agent writes invalid cycle-output.json (malformed JSON, wrong field names) — Severity: H — Mitigation: cycle_post validates schema strictly, rejects invalid output with clear error, agent retries
- **Risk 5**: Loss of step-by-step status bar updates during cycle — Severity: L — Mitigation: cycle_pre writes "working" state, cycle_post writes "idle"; agent can still write status-bar via a lightweight status_update field in cycle-output

## Edge Cases

- **Network down during cycle_pre**: cycle_pre fails to pull or query tracker. Write a degraded cycle-input.json with `pull_result: "error"` and empty tracker queues. Agent sees the error, logs it, skips tracker-dependent work. cycle_post still commits local state.
- **cycle_post push rejected**: Another agent pushed first. cycle_post should `git pull --rebase` and retry push (up to 3 times). If still failing, stash state and log error. This is already handled by git_ops.py.
- **Agent crashes mid-cycle**: cycle-output.json never written. cycle_post never runs. On next boot, cycle_pre detects no cycle-output.json from last cycle (stale timestamp or missing file), loads working-state.md, and resumes.
- **Empty work queue**: cycle_pre writes empty queues. Agent detects quiet cycle. cycle_post logs quiet iteration and writes idle state.
- **Planning phase active (PM)**: cycle_pre detects planning phase flag in working-state.md, sets `suppressed: true`. Agent skips normal work, cycle_post writes suppressed iteration log.
- **Version bump during cycle_post**: DM's cycle_post executes the full bump sequence (config update, CHANGELOG, tag, push). If any step fails mid-sequence, working-state captures progress for recovery.
- **Multiple agents pushing simultaneously**: git_ops.py already handles pull-before-push. cycle_post inherits this. State files under `.squidsquad/` are per-role, so merge conflicts are rare. Shared files (config.md counters) need atomic read-modify-write — already a risk today.

## Integration Risks

- **compose.py interaction**: Agent templates are generated by compose.py from sub-skills. The cycle runner changes will modify many sub-skills (pull-latest, context-pressure, git-commit, iteration-log, etc.). compose.py itself doesn't change, but the sub-skill content changes substantially.
- **boot_remote.py interaction**: Boot script spawns agent sessions. Currently the agent self-starts the Ralph Loop via `/loop`. With cycle runner, the boot script may need to invoke cycle_pre before the agent starts, or the `/loop` command changes to invoke the pre/post wrapper.
- **statusline interaction**: Statusline reads `current-state` files. cycle_pre/post writes these instead of the agent. Timing changes: updates happen at cycle boundaries instead of per-step.
- **Vault protocol interaction**: vault-remember (Step 4b) is creative work that happens after the main work but before commit. It stays in the agent's creative phase. vault_optimize is mechanical and can move to cycle_post.
- **Subagent spawning**: PM and QA spawn subagents (research, discussion prep, QA execution). These happen during creative work and require bash access. The cycle runner doesn't eliminate bash access — it eliminates boilerplate bash.

## Upgrade & Migration

- **New config values**:
  - `Cycle Runner: yes|no` — feature flag for gradual rollout (default: no for existing installs)

- **New files**:
  - `references/scripts/cycle_pre.py`
  - `references/scripts/cycle_post.py`
  - `references/schemas/cycle-input.schema.json` (optional, for validation)
  - `references/schemas/cycle-output.schema.json` (optional, for validation)
  - `.squidsquad/[role]/cycle-input.json` (runtime, gitignored)
  - `.squidsquad/[role]/cycle-output.json` (runtime, gitignored)

- **Template changes**:
  - All 4 role CLAUDE.md files restructured: mechanical steps replaced with "read cycle-input.json" and "write cycle-output.json" instructions
  - Sub-skills like `pull-latest`, `git-commit`, `context-pressure`, `iteration-log` become no-ops or are removed from agent templates
  - New sub-skills: `cycle-input-reader`, `cycle-output-writer` — schema documentation for agents
  - Agent "On Startup" changes: instead of `/loop 30m execute one Ralph Loop cycle`, it becomes `/loop 30m run cycle_pre, execute creative work, run cycle_post`

- **Upgrade steps**:
  - `/squidsquad-upgrade` must: (1) deploy new scripts, (2) regenerate all agent templates via compose.py, (3) add new config values with defaults
  - Feature flag allows testing on one role before rolling out to all

- **Graceful degradation**:
  - If `Cycle Runner: no` (default), agents use existing Ralph Loop — no behavior change
  - If cycle_pre.py or cycle_post.py is missing (partial upgrade), agent falls back to manual bash calls
  - cycle-input.json and cycle-output.json are gitignored — no repo pollution

## Capability Gaps

- `capability_check.py` exists but is role-manifest-based. The cycle runner doesn't require new capabilities per se — it restructures how existing capabilities are invoked. No capability gaps expected.

## Open Questions

- **Q1**: Should cycle_pre run E2E tests, or should the agent still run them during creative work? — **Why**: E2E tests are mechanical (just run a command), but interpreting failures is creative. If cycle_pre runs tests, the agent gets results in cycle-input. If the agent runs them, it burns context on the bash call but can react immediately to output.

- **Q2**: How does the `/loop` command integrate with cycle_pre/post? Does `/loop` invoke a wrapper script that runs pre → agent → post? Or does the agent template instruct the agent to call cycle_pre at cycle start and cycle_post at cycle end? — **Why**: The former is cleaner (agent never sees mechanical work) but requires changes to the loop infrastructure. The latter is simpler to implement but the agent still makes 2 bash calls per cycle.

- **Q3**: Should the agent be fully blocked from bash during creative work, or just discouraged? — **Why**: Agents need bash for tests, code reading, subagent spawning, and verification commands. Full blocking breaks these. The goal is to eliminate boilerplate bash, not all bash.

- **Q4**: How granular should cycle-output.json status transitions be? Should the agent specify `from` and `to` states, or just the target state? — **Why**: tracker.py already validates transitions. If the agent specifies only the target, cycle_post must look up the current state. If it specifies both, cycle_post can validate without an API call.

- **Q5**: Should cycle_pre pre-fetch full issue details (body, comments) for queued items, or just list numbers and titles? — **Why**: Pre-fetching saves context (agent doesn't need to call `gh issue view`), but adds latency to cycle_pre and may fetch details for items the agent won't work on this cycle.

- **Q6**: How does the human interaction flow (PM Step 2) work with cycle-input? Human input arrives via conversation context, not via tracker queries. — **Why**: cycle_pre can't capture human chat messages. The PM agent must still read conversation history directly. This means PM's creative phase is inherently different from other roles.

- **Q7**: Should quiet cycle detection happen in cycle_pre or remain agent-side? — **Why**: cycle_pre can detect empty queues and set `quiet: true` in cycle-input. But the skill agent's quiet cycle counter is working-state-based and needs creative judgment (was real work done?). DM and QA have simpler quiet detection.

## Performance Analysis

### Current Context Cost Per Cycle (Estimated)

Each mechanical bash call costs roughly 200-500 tokens (command + output + agent processing). Per cycle:

| Operation | Calls/Cycle | Tokens/Call | Total |
|-----------|-------------|-------------|-------|
| Timestamps | 8-12 | 150 | 1,200-1,800 |
| Status bar writes | 8-12 | 200 | 1,600-2,400 |
| Git pull | 1 | 300 | 300 |
| Tracker queries | 2-5 | 400 | 800-2,000 |
| Config reads | 2-4 | 200 | 400-800 |
| Health check | 1 | 500 | 500 |
| Git commit/push | 1-3 | 400 | 400-1,200 |
| Context pressure read | 1 | 150 | 150 |
| Working state read | 1 | 300 | 300 |
| **Total per quiet cycle** | | | **~4,000-6,000** |
| **Total per active cycle** | | | **~6,000-10,000** |

### With Cycle Runner

| Operation | Calls/Cycle | Tokens/Call | Total |
|-----------|-------------|-------------|-------|
| Read cycle-input.json | 1 | 500-1,000 | 500-1,000 |
| Write cycle-output.json | 1 | 500-1,000 | 500-1,000 |
| **Total mechanical overhead** | | | **~1,000-2,000** |

**Savings: 4,000-8,000 tokens per cycle**, or roughly 60-80% reduction in mechanical overhead. Over a long-running session (20+ cycles before context pressure), this extends useful context lifetime significantly.

## Recommendation

**Feasible with caveats.**

The core architecture is sound and well-supported by the existing script infrastructure. The main caveats:

1. **QA branch switching** needs the "one item per cycle" simplification or a mid-cycle branch-switch mechanism. The one-per-cycle approach is cleaner and adequate given 30-minute cycle intervals.

2. **PM human interaction** cannot be captured by cycle_pre. The PM agent will always have a hybrid model where cycle_pre handles tracker/git mechanics but human conversation remains in the creative phase.

3. **Agent bash access must remain** for tests, code reading, verification commands, and subagent spawning. The cycle runner eliminates boilerplate bash, not all bash.

4. **Schema versioning** is essential from day one. The cycle-input/output JSON contracts will evolve as features are added. cycle_post must validate and fail clearly on schema mismatches.

5. **Incremental rollout** via feature flag (`Cycle Runner: yes|no`) is strongly recommended. Start with the skill agent (simplest cycle), then QA, then DM, then PM (most complex).

6. **The `/loop` integration** (Q2) is the biggest open architectural decision. Recommend the wrapper approach: `/loop` invokes a wrapper that runs `cycle_pre.py → agent creative phase → cycle_post.py`. This keeps the agent template clean and ensures pre/post always run even if the agent crashes.
