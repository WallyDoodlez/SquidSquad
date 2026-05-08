# FEAT-PM-6126 Context — Harness Owns PR Merge + Compose

## Scope

Move PR merge execution and post-merge compose from agents to the harness. Agents request merges via REST endpoint, harness executes merge + conditional compose, emits events back.

## Locked Decisions (human decided)

- **Dedicated POST /merge endpoint**: Clean REST semantics, not event interception. Harness still emits request-merge event for audit trail
- **Async — 202 Accepted**: Return immediately. Emit pr-merged and compose-completed events when done. Agent sees them next cycle
- **Full payload on pr-merged**: PR number, branch, issue number, files_changed. Maximum context for agents
- **Auto-compose always-on**: If merged files touch references/, compose runs. No config flag. No way to forget or disable
- **Harness merges from primary repo**: Not from agent clones. GitHub handles merge server-side via `gh pr merge`. Agents get changes on next git pull

## Dev Discretion (dev agent can choose)

- Internal structure of POST /merge endpoint handler
- Background thread vs asyncio task for merge+compose execution
- How to detect references/ changes (git diff on merged commit vs gh pr files)
- Error response format for 202 Accepted + event notification pattern
- Whether to keep git_ops.py pr_merge() as admin utility or deprecate

## Side Effect Mitigations (required)

- Remove _emit("pr-merge") from git_ops.py pr_merge() — harness emits pr-merged instead, avoids duplicate events
- Update cycle_pre.py mechanical reactions: pr-merge → pr-merged
- Update _ROLE_EVENT_TYPES to include pr-merged and compose-completed
- Merge failure (conflict) must be surfaced clearly in pr-merged event so QA can resolve
- Compose failure must NOT block pr-merged event — merge succeeded, compose is separate
- QA's conflict resolution logic stays in QA template — harness surfaces failure, QA judges resolution
- During upgrade transition: old agents calling git_ops.py pr-merge directly still works (graceful degradation)

## Upgrade Path (required)

- Stop agents → pull new code → compose.py deploy-all → start harness → start agents
- Old agents with direct pr-merge calls: still functional but harness unaware (no events, no auto-compose)
- No double-merge risk: git_ops.pr_merge() handles "already merged" gracefully
- git_ops.py pr-merge CLI remains for manual/admin use

## Out of Scope

- Other git operations (branch delete, rebase) — future extension of same pattern
- Merge conflict auto-resolution by harness — agents handle conflicts
- Configurable auto-compose flag — always-on
