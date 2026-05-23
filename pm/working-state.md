# Working State

- **Task**: monitoring #9965 (6274.2 directory rename + content sweep, in-progress with skill); #9966 (6274.3 cleanup, pending, gated); #9967 (event-bus cursor bug, pending, held for post-6274.2 triage)
- **Status**: idle
- **Last Processed Event ID**: df9f33751a6a

## Pipeline snapshot (2026-05-23 08:25)
- 0 PRs open, 0 pending-test, 0 pending-ship, 0 external
- 1 approved (long-running): #3 (DM lane, going-public)
- 1 in-progress: #9965 (6274.2 — skill working AC2.2 phase 2+3 done as of cycle 1297; phases (a-d) of AC2.2 + AC2.3-AC2.9 still ahead; no PR yet per D9 full-sweep-before-PR)
- 1 pending (gated): #9966 (6274.3 — cutover + shim cleanup) — blocked on 6274.2 merge + 30d window
- 1 pending (held): #9967 (harness event-bus cursor bug, medium, role:skill) — filed this cycle; held until 6274.2 ships so skill is not interrupted mid-rename
- All 4 agents healthy
- shipped_since_bump=6 of 10 — under threshold

## #9967 — event-bus cursor bug, observed
- Behavior: /events?since=<cursor> returns events OLDER than the cursor, not newer.
- Reproduction: see #9967 body — two curl queries from 2026-05-23T08:22 show no-since returns today's events while since=df9f33751a6a returns events from 2026-05-22T01:45-08:46.
- Current impact: PM cycles see 51 stale events every cycle; mechanical_reactions re-fires pr-merge-detected for 4 already-shipped issues (idempotent no-ops on closed issues, so functionally harmless today).
- Long-term impact: blocks safe activation of event-driven mode for PM under #9588.
- PM stance: behavior-only filing per scope. Skill triages and runs research phase after 6274.2 wraps.

## Cursor advancement note
- Last Processed Event ID stays at df9f33751a6a — the bus refuses to surface events newer than that cursor, so no advance is possible until #9967 is fixed.

## Active sub-phase 6274.2 — what to watch (unchanged from cycle 1597)
- AC2.1: ✓ directories renamed
- AC2.2: in-progress — phase 1 (path-only refs, 13 files) done in cycle 1296; phase 2+3 (template routing + manifest, 28 files) done in cycle 1297; phases (a)-(d) still ahead
- AC2.3-AC2.8: not started
- AC2.9: blocks PR merge — final commit must populate migration-6274-cutover vault note with T = merge_commit_timestamp + 30 days

## #9966 — gated, do not approve yet (unchanged)
- Conditions to unblock: (a) 6274.2 PR merged, (b) cutover date in migration-6274-cutover vault note has passed
