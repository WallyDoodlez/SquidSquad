<!-- sub-skill: cycle-runner -->
## Cycle Runner (Transport Layer)

The Ralph Loop uses a 3-phase flow: mechanical pre-cycle → creative work → mechanical post-cycle. All mechanical operations (git pull, commit, push, triage queries, iteration logging) are handled by deterministic scripts. You focus on creative work only.

### Phase 1 — Pre-Cycle (Mechanical)

```bash
python references/scripts/cycle_pre.py [ROLE]
```

This script handles all mechanical operations: git pull, context pressure check, working state read, triage/queue queries, branch enforcement (ensures correct branch before pull), and writes `.squidsquad/[ROLE]/cycle-input.json`.

Read the output:

```bash
cat .squidsquad/[ROLE]/cycle-input.json
```

The JSON contains everything you need: `role`, `cycle_number`, `timestamp`, `pull_result`, `context_pressure`, `working_state`, `recent_events`, `mechanical_reactions`, and role-specific fields (work queue, verification queue, etc.).

`recent_events` (#5622): list of event bus events since your last processed cursor. Each event has `id`, `event_type`, `role`, `timestamp`, `payload`, `received_at`. Filtered to your role's relevant event types. Empty list if harness unreachable or no new events.

`mechanical_reactions` (#5622): list of actions the mechanical layer took based on high-confidence event patterns (e.g., PR merge detected, rework needed). Informational — the reaction already executed; this tells you what happened.

### Phase 2 — Creative Work (Agent)

This is your core work. Start by **reading cycle-input.json critically**:

1. **Examine the pipeline state** — don't just scan for your own work items. Look at the full picture: what's stalled, what's been rejected, what's blocked, what claims don't add up. Apply your SOUL.md personality to the data.
2. **Investigate anomalies** — if an item has been at the same status for multiple cycles, if an agent claims something is blocked without evidence, if shipped-since-bump is over threshold — these are problems to investigate, not ignore.
3. **Do your role's core work** — reasoning, code analysis, code writing, verification, human interaction, planning, or whatever your role requires.

You still have full bash access for:
- Running tests
- Reading code
- Spawning subagents
- Running verification commands
- Any creative work that requires shell access

Do NOT use bash for mechanical operations that cycle_pre/post handles (git pull, git commit, git push, status bar writes, tracker transitions, iteration logging).

### Phase 3 — Post-Cycle (Mechanical)

Write your results to `.squidsquad/[ROLE]/cycle-output.json`:

```json
{
  "role": "[ROLE]",
  "cycle_number": N,
  "cycle_type": "active" | "quiet" | "suppressed",
  "status_transitions": [
    {"number": 123, "from": "approved", "to": "in-progress"}
  ],
  "tracker_comments": [
    {"number": 123, "message": "Picking up. Status → In Progress."}
  ],
  "iteration_summary": "Brief description of work done",
  "commit_message": "[ROLE]: cycle N — brief description",
  "working_state_update": "# Working State\n\n- **Task**: none\n..."
}
```

Then run:

```bash
python references/scripts/cycle_post.py [ROLE]
```

The script handles: status transitions, tracker comments, iteration logging, git commits, pushes, version bumps (DM), and status bar cleanup. Context pressure exit is detected mechanically — `cycle_post.py` exits with code 42 when pressure exceeds threshold, and the harness respawns the agent (#4966).

### Role-Specific Fields

**Skill** cycle-output extras:
- `code_commit`: `{branch, message, pr_needed, pr_title, pr_body}` — feature-branch commit + PR creation block (#9478)
- `state_commit_message`: separate message for main branch state commit
- `improvement_scan`: `{files_scanned, findings}` — if scan ran

**PM** cycle-output extras:
- `human_input_processed`: summary of human input handled
- `issues_filed`, `issues_verified`, `tasks_verified`, `tasks_shipped`
- `external_issues_triaged`, `health_alerts`, `vault_writes`
- `version_bump`: `{new_version, items_included}` — deprecated (DM always present)

**QA** cycle-output extras:
- `e2e_log`: `{result, tests_run, failures}`
- `issues_filed`, `issues_verified`, `tasks_verified`
- `pr_actions`: `[{pr_number, action, comment}]`

**DM** cycle-output extras:
- `bugs_fixed`, `deliveries`
- `version_bump`: `{new_version, items_included}`
<!-- /sub-skill: cycle-runner -->
