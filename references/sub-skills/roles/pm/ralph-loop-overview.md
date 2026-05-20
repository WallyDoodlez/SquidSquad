## On Startup

When you first receive these instructions, first verify GitHub Issues access (see Tracker Protocol above). Then read the interval from `.squidsquad/config.md` (under `Iteration Interval > Minutes`) and invoke the `/loop` command to schedule repeating cycles:

```
/loop [INTERVAL]m execute one Ralph Loop cycle
```

This externalizes the cycle timing — `/loop` handles the interval and re-invocation. Each cycle is a single pass through the steps below. Do NOT manually sleep or try to self-loop. Print a brief one-line status as you go (e.g. `[🦑 HH:MM:SS] Pulling latest...`, `[🦑 HH:MM:SS] Running QA pass...`).

---

## The Ralph Loop

Each invocation executes **one cycle** through the steps below. The `/loop` command handles re-invocation every [INTERVAL] minutes.

At the start of each cycle, print:

```
[🦑] ---- cycle N started at HH:MM:SS ----
```

At the end of each cycle, print:

```
[🦑] ---- cycle N complete at HH:MM:SS ----
```

**Step markers**: At the start of each step, print a one-line `[🦑 HH:MM:SS]` timestamped status so the human can scan scrollback. Key sub-actions (filing bugs, verifying fixes) also get markers. Keep each marker to one concise line. **All timestamps** (`HH:MM:SS`, `YYYY-MM-DD HH:MM`) must come from `python references/scripts/cycle.py timestamp-short` — see Timestamps in Tracker Protocol. Never guess or fabricate times.

**Status bar state**: At each step marker, also write your current state to `.squidsquad/pm/current-state` so the status bar can display it. **Use atomic writes** (write to `.tmp` then `mv`) to avoid file locking races with the statusline script on Windows:

```bash
echo "phase|sub-skill — description" > .squidsquad/pm/current-state.tmp && mv -f .squidsquad/pm/current-state.tmp .squidsquad/pm/current-state
```

Phase is one of: `pulling`, `checkin`, `testing`, `verifying`, `planning`, `researching`, `discussing`, `health`, `idle`. The sub-skill is the short name of the active sub-skill (e.g., `pull-latest`, `verification`, `feature-intake`). The description is a short (≤60 char) human-readable label. **Include the GitHub Issue number** (e.g. `#29`, `#37`) in all item-specific phases. Put the issue number near the start of the description so it survives truncation.

> Note: `test-planning` was dropped from this enum on #9319. Under the #9184 workflow PM no longer authors test plans; QA writes its own `TEST-PLAN-<NUMBER>.md` at verification time and uses the `test-plan` external-model route from its own sub-skill.

Examples:

- `pulling|pull-latest — Syncing with remote...`
- `testing|verification — Running E2E tests...`
- `verifying|verification — Verifying #29...`
- `planning|feature-intake — #37 intake...`
- `researching|feature-intake — Researching #35...`
- `discussing|feature-intake — Discussion for #35...`
- `idle|`

Write `idle|` at cycle end so the status bar shows rotating hints between cycles.
