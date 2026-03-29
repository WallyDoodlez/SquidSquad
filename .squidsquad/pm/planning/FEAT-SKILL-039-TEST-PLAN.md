# FEAT-SKILL-039 Test Plan — Change Loop Interval On The Fly

## Happy Path Tests

### T1: Change interval with valid input
- **Preconditions**: SquidSquad is running with default 5m interval. config.md shows `Minutes: 5`.
- **Steps**:
  1. Run `/squidsquad-interval 10m` in any agent conversation.
  2. Wait for command to complete.
- **Expected**: Command confirms interval changed to 10 minutes. No errors.
- **Verify**: Read config.md — `Iteration Interval > Minutes` should be `10`.

### T2: Current agent cron is recreated
- **Preconditions**: Agent running with a cron at 5m interval. T1 completed.
- **Steps**:
  1. Run `/squidsquad-interval 15m`.
  2. Check cron state immediately after.
- **Expected**: Old 5m cron is deleted (CronDelete). New 15m cron is created (CronCreate).
- **Verify**: The agent's next cycle fires ~15 minutes after the change, not ~5 minutes.

### T3: Other agents detect the change within one cycle
- **Preconditions**: Two agents running (pm + skill), both at 5m interval.
- **Steps**:
  1. Run `/squidsquad-interval 8m` from the pm agent.
  2. Wait for the skill agent to start its next cycle.
- **Expected**: Skill agent reads config.md at cycle start, detects interval changed from 5 to 8, and re-schedules its own cron to 8m.
- **Verify**: After the skill agent's next cycle completes, its subsequent cycle fires at ~8m interval. Check agent output for re-schedule log line.

### T4: Change persists across agent restart
- **Preconditions**: Interval changed to 12m via the slash command.
- **Steps**:
  1. Stop and restart an agent (new conversation with auto-boot).
  2. Agent reads config.md on startup.
- **Expected**: Agent picks up 12m interval from config.md and creates cron at 12m.
- **Verify**: Read config.md — still shows `12`. Agent's first `/loop` call uses 12m.

## Edge Case Tests

### T5: Reject interval below minimum (under 5 minutes)
- **Preconditions**: SquidSquad running at any valid interval.
- **Steps**:
  1. Run `/squidsquad-interval 3m`.
- **Expected**: Command rejects with a clear error message stating minimum is 5 minutes. No changes made.
- **Verify**: Read config.md — interval unchanged. Cron not recreated.

### T6: Reject interval of 0 or negative
- **Preconditions**: SquidSquad running at any valid interval.
- **Steps**:
  1. Run `/squidsquad-interval 0m`.
  2. Run `/squidsquad-interval -5m`.
- **Expected**: Both rejected with error. No changes made.
- **Verify**: config.md unchanged after each attempt.

### T7: Reject non-numeric input
- **Preconditions**: SquidSquad running at any valid interval.
- **Steps**:
  1. Run `/squidsquad-interval abc`.
  2. Run `/squidsquad-interval m`.
  3. Run `/squidsquad-interval` (no argument).
- **Expected**: Each rejected with a clear usage/help message. No changes made.
- **Verify**: config.md unchanged.

### T8: Exact minimum boundary (5 minutes)
- **Preconditions**: SquidSquad running at 10m interval.
- **Steps**:
  1. Run `/squidsquad-interval 5m`.
- **Expected**: Accepted. Interval set to 5 minutes.
- **Verify**: config.md shows `Minutes: 5`. Cron recreated at 5m.

### T9: Just below minimum boundary (4 minutes)
- **Preconditions**: SquidSquad running at 10m interval.
- **Steps**:
  1. Run `/squidsquad-interval 4m`.
- **Expected**: Rejected. Error message mentions 5-minute minimum.
- **Verify**: config.md still shows `10`.

### T10: Very large interval
- **Preconditions**: SquidSquad running at 5m interval.
- **Steps**:
  1. Run `/squidsquad-interval 1440m` (24 hours).
- **Expected**: Accepted (no explicit maximum per D2). Interval set to 1440.
- **Verify**: config.md shows `Minutes: 1440`. Cron created at 1440m.

### T11: Setting interval to same value as current
- **Preconditions**: SquidSquad running at 5m interval.
- **Steps**:
  1. Run `/squidsquad-interval 5m`.
- **Expected**: Either accepts gracefully (recreates cron) or reports "already set to 5m" — either is fine. No errors or corruption.
- **Verify**: config.md still shows `5`. Agent continues cycling normally.

### T12: Input with extra whitespace or missing suffix
- **Preconditions**: SquidSquad running at any interval.
- **Steps**:
  1. Run `/squidsquad-interval  10m` (extra space).
  2. Run `/squidsquad-interval 10` (no "m" suffix, if dev chose to require it).
- **Expected**: Either parsed correctly or rejected with clear usage message. No crash, no partial config update.
- **Verify**: If accepted, config.md reflects the value. If rejected, config.md unchanged.

## Regression Tests

### T13: Config.md format not corrupted
- **Preconditions**: Clean config.md with all existing fields.
- **Steps**:
  1. Run `/squidsquad-interval 7m`.
  2. Read entire config.md.
- **Expected**: Only the `Minutes` value changed. All other fields (version, counters, agents, heartbeat, thresholds) intact and correctly formatted.
- **Verify**: Diff config.md before and after — only the interval line changed.

### T14: Ralph Loop continues normally after interval change
- **Preconditions**: Agent mid-cycle or between cycles.
- **Steps**:
  1. Run `/squidsquad-interval 10m`.
  2. Wait for next full cycle to complete.
- **Expected**: All Ralph Loop steps (pull, QA, verify bugs, verify features, commit) execute normally. No step skipped or broken.
- **Verify**: Iteration log for the next cycle shows all steps completed.

### T15: Git operations unaffected
- **Preconditions**: Agent running normally with pending changes.
- **Steps**:
  1. Run `/squidsquad-interval 8m`.
  2. Let the next cycle run through to commit/push.
- **Expected**: Git pull, commit, and push work normally. The config.md change is included in the commit.
- **Verify**: `git log` shows the config change committed. `git diff` clean after push.

### T16: Heartbeat interval unaffected
- **Preconditions**: Heartbeat configured at 10 seconds in config.md.
- **Steps**:
  1. Run `/squidsquad-interval 15m`.
  2. Check heartbeat behavior.
- **Expected**: Heartbeat interval remains 10 seconds — only loop interval changed.
- **Verify**: config.md `Heartbeat Interval Seconds` still shows `10`.

### T17: Multiple rapid interval changes
- **Preconditions**: Agent running at 5m.
- **Steps**:
  1. Run `/squidsquad-interval 10m`.
  2. Immediately run `/squidsquad-interval 7m`.
  3. Immediately run `/squidsquad-interval 20m`.
- **Expected**: Each change cleanly replaces the previous. Final state is 20m. No orphaned crons, no stale interval values.
- **Verify**: config.md shows `20`. Only one active cron exists at 20m interval.
