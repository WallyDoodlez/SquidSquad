---
slot: instructions
ordinal: 20
roles: [pm]
---

## The Ralph Loop

> **Boot prerequisite (#9588)**: by the time you Read this fragment, the boot bootstrap (`common/boot-bootstrap.md`, inlined at the top of your composed CLAUDE.md) has already verified GitHub Issues access AND scheduled the `/loop` invocation with the correct interval from `config.md`. Do NOT re-invoke `/loop` here — re-invoking would stack cron entries. If you need to recover from an interrupted `/loop` (e.g., resuming after an inline session), follow the recovery directive in the bootstrap rather than re-deriving the invocation from this fragment.

Each invocation executes **one cycle** through the steps below. `/loop` handles re-invocation at the interval configured in `.squidsquad/config.md` (`Iteration Interval > Minutes`). Print a brief one-line status as you go (e.g. `[🦑 HH:MM:SS] Pulling latest...`, `[🦑 HH:MM:SS] Running verifier pass...`).

> **Inline mode vs `/loop` mode (#9358).** When a human drives the session interactively (direct messages instead of the `/loop` trigger), `cycle_pre`/`cycle_post` are NOT invoked — there is no scheduler firing them. You still act on the human's requests (post comments, transition tasks, ship PRs) but you do this directly. As a result: `cycle-input.json` and the iter log are not written for the inline turn, the status bar `current-state` file may stay on its previous value, and `working-state.md` only changes if you (or the human) explicitly edits it. This is **expected**, not a regression — PM's pipeline sentinel should not treat an agent operating in inline mode as broken cycling. To resume `/loop` mode after an inline session, re-run the recovery directive from the boot bootstrap.

At the start of each cycle, print:

```
[🦑] ---- cycle N started at HH:MM:SS ----
```

At the end of each cycle, print:

```
[🦑] ---- cycle N complete at HH:MM:SS ----
```

**Step markers**: At the start of each step, print a one-line `[🦑 HH:MM:SS]` timestamped status so the human can scan scrollback. Key sub-actions (filing bugs, verifying fixes) also get markers. Keep each marker to one concise line. **All timestamps** (`HH:MM:SS`, `YYYY-MM-DD HH:MM`) must come from `python references/scripts/cycle.py timestamp-short` — see Timestamps in Tracker Protocol. Never guess or fabricate times.

**Status bar state**: At each step marker, also write your current state to `.squidsquad/[PM_ALIAS]/current-state` so the status bar can display it. **Use atomic writes** (write to `.tmp` then `mv`) to avoid file locking races with the statusline script on Windows:

```bash
echo "phase|sub-skill — description" > .squidsquad/[PM_ALIAS]/current-state.tmp && mv -f .squidsquad/[PM_ALIAS]/current-state.tmp .squidsquad/[PM_ALIAS]/current-state
```

Phase is one of: `pulling`, `checkin`, `testing`, `verifying`, `planning`, `researching`, `discussing`, `health`, `idle`. The sub-skill is the short name of the active sub-skill (e.g., `pull-latest`, `verification`, `feature-intake`). The description is a short (≤60 char) human-readable label. **Include the GitHub Issue number** (e.g. `#29`, `#37`) in all item-specific phases. Put the issue number near the start of the description so it survives truncation.

> Note: `test-planning` was dropped from this enum on #9319. Under the #9184 workflow PM no longer authors test plans; Verifier writes its own `TEST-PLAN-<NUMBER>.md` at verification time and uses the `test-plan` external-model route from its own sub-skill.

Examples:

- `pulling|pull-latest — Syncing with remote...`
- `testing|verification — Running E2E tests...`
- `verifying|verification — Verifying #29...`
- `planning|feature-intake — #37 intake...`
- `researching|feature-intake — Researching #35...`
- `discussing|feature-intake — Discussion for #35...`
- `idle|`

Write `idle|` at cycle end so the status bar shows rotating hints between cycles.

## What loop mode changes vs. event mode

The cycle sequence is **the same** as event mode — you still walk the seven canonical steps (boot, resume, pickup, work, checkpoint, cleanup, exit) and your role-specific sub-steps under each. Refer to the hydrated cycle diagram and the Step 1–7 sections in your composed CLAUDE.md for the full sequence; this fragment only describes what's **different** in loop mode.

Three differences fire at every cycle start:

#### step:cycle/run — agent-driven cycle wrapper

→ run sub-skill: cycle-runner

In event mode the harness wraps each cycle with `cycle_pre.py` and `cycle_post.py` automatically. In loop mode the agent is the one driving the cycle, so the pre/post wrapper surfaces as an agent-side step. Goal: the cycle's input state has been captured (pull result, context-pressure snapshot, working-state, queue state); your creative work is aligned against it; outputs are staged for durable commit and status propagation.

#### step:cycle/context-pressure — agent-side context-pressure check

→ run sub-skill: context-pressure

In event mode this detection lives in `cycle_post.py` and surfaces via the universal cooperative-exit path (see Step 7 `self-restart` in your composed CLAUDE.md). In loop mode the agent checks context pressure itself: read the live percentage from disk, compare to the configured threshold, and (above threshold) checkpoint pending work to `working-state.md` plus push git so a respawn loses nothing. Below threshold this is a no-op.

#### step:cycle/resume — planning-phase suppression (PM-only addendum)

In ADDITION to the universal resume behavior already defined in Step 2 (`resume-working-state` — Read `working-state.md`, resume any `in-progress` task), loop-mode PM runs a planning-phase suppression check that does not apply in event mode:

If `cycle-input.json` contains `"suppressed": true` in `working_state` (set when `working-state.md` has a `**Phase**:` line with an active planning phase), this cycle is **suppressed**:

1. Print: `[🦑 HH:MM:SS] ---- cycle N (suppressed — active planning phase) ----`
2. Write a minimal `cycle-output.json` with `"cycle_type": "suppressed"` and a brief summary.
3. Run `python references/scripts/cycle_post.py pm` — it handles the commit/push and status-bar cleanup.
4. Return — `/loop` will trigger the next cycle.

If working-state has no active task and no active planning phase, proceed normally through the rest of the canonical sequence (Step 3 pickup → Step 7 exit) as documented in your composed CLAUDE.md.

#### Loop-mode-specific exit note

After Step 7 exit, `cycle_post.py` applies your output before the next cron fire and `/loop` triggers the next cycle at the configured interval. Loop mode runs **exactly one cycle per cron fire** — there is no per-event walk to continue. Inline-mode caveats (above) apply when a human is driving the session directly.
