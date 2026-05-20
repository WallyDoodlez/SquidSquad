## On Startup

When you first receive these instructions, first verify GitHub Issues access (see Tracker Protocol above). Then read the interval from `.squidsquad/config.md` (under `Iteration Interval > Minutes`) and invoke:

```
/loop [INTERVAL]m execute one Ralph Loop cycle
```

This externalizes the cycle timing — `/loop` handles the interval and re-invocation. Each cycle is a single pass through the steps below. Do NOT manually sleep or try to self-loop.

> **Inline mode vs `/loop` mode (#9358).** When a human drives the session interactively (direct messages instead of the `/loop` trigger), `cycle_pre`/`cycle_post` are NOT invoked — there is no scheduler firing them. You still act on the human's requests (post comments, transition tasks, ship PRs) but you do this directly. As a result: `cycle-input.json` and the iter log are not written for the inline turn, the status bar `current-state` file may stay on its previous value, and `working-state.md` only changes if you (or the human) explicitly edits it. This is **expected**, not a regression — PM's pipeline sentinel should not treat an agent operating in inline mode as broken cycling. To resume `/loop` mode after an inline session, re-invoke `/loop [INTERVAL]m execute one Ralph Loop cycle`.

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

**Step markers**: At the start of each step, print a one-line `[🦑 HH:MM:SS]` timestamped status so the human can scan scrollback. Key sub-actions also get markers. Keep each marker to one concise line. **All timestamps** (`HH:MM:SS`, `YYYY-MM-DD HH:MM`) must come from `python references/scripts/cycle.py timestamp-short` — see Timestamps in Tracker Protocol. Never guess or fabricate times.

**Status bar state**: At each step marker, also write your current state to `.squidsquad/dm/current-state` so the status bar can display it. **Use atomic writes** (write to `.tmp` then `mv`) to avoid file locking races with the statusline script on Windows:

```bash
echo "phase|sub-skill — description" > .squidsquad/dm/current-state.tmp && mv -f .squidsquad/dm/current-state.tmp .squidsquad/dm/current-state
```

Phase is one of: `pulling`, `delivering`, `shipping`, `committing`, `idle`. The sub-skill is the short name of the active sub-skill (e.g., `pull-latest`, `delivery-packaging`, `version-bumps`, `git-commit`). The description is a short (≤60 char) human-readable label. **Include the specific item ID** in all item-specific phases. Put the item ID near the start of the description so it survives truncation. Examples:

- `pulling|pull-latest — Syncing with remote...`
- `delivering|delivery-packaging — 📦 #35 delivery...`
- `shipping|version-bumps — 🚀 Version bump v0.7.0...`
- `committing|git-commit — Committing delivery for #35...`
- `idle|`

Write `idle|` at cycle end so the status bar shows rotating hints between cycles.
