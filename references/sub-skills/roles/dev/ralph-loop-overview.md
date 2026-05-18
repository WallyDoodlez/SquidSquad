## On Startup

When you first receive these instructions, first verify GitHub Issues access (see Tracker Protocol above). Then read the interval from `.squidsquad/config.md` (under `Iteration Interval > Minutes`) and invoke the `/loop` command to schedule repeating cycles:

```
/loop [INTERVAL]m execute one Ralph Loop cycle
```

This externalizes the cycle timing — `/loop` handles the interval and re-invocation. Each cycle is a single pass through Steps 1-5, then returns. Do NOT manually sleep or try to self-loop.

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

**Step markers**: At the start of each step, print a one-line `[🦑 HH:MM:SS]` timestamped status so the human can scan scrollback. Key sub-actions (filing bugs, committing) also get markers. Keep each marker to one concise line. **All timestamps** (`HH:MM:SS`, `YYYY-MM-DD HH:MM`) must come from `python references/scripts/cycle.py timestamp-short` — see Timestamps in Tracker Protocol. Never guess or fabricate times.

**Status bar state**: At each step marker, also write your current state to `.squidsquad/[ROLE]/current-state` so the status bar can display it. **Use atomic writes** (write to `.tmp` then `mv`) to avoid file locking races with the statusline script on Windows:

```bash
python references/scripts/cycle.py status-bar [ROLE] "phase" "sub-skill — description"
```

Phase is one of: `pulling`, `triaging`, `implementing`, `committing`, `idle`. The sub-skill is the short name of the active sub-skill (e.g., `pull-latest`, `tracker-protocol`, `dev-agent`, `git-commit`). The description is a short (≤60 char) human-readable label. **Include the GitHub Issue number** (e.g. `#29`, `#37`) in all item-specific phases. Put the issue number near the start of the description so it survives truncation. Examples:

- `pulling|pull-latest — Syncing with remote...`
- `triaging|tracker-protocol — Fixing #29...`
- `implementing|dev-agent — 🔨 #37...`
- `committing|git-commit — Committing #37...`
- `idle|`

Write `idle|` at cycle end so the status bar shows rotating hints between cycles.
