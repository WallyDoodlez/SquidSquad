---
slot: instructions
ordinal: 16
---

## Idle = Improvement-Scan Cool-Down Loop

When `work_queue(<role>)` returns empty, you are **not** finished — you enter the improvement-scan cool-down loop. Scanning during idle time turns dead clock into proactive process improvement.

### Working-State Schema

The cool-down state lives under a `## Improvement Scan` section in `.squidsquad/<role>/working-state.md`:

```
## Improvement Scan
Status: idle | running
Last completed: YYYY-MM-DD HH:MM
Next scan after: YYYY-MM-DD HH:MM
```

Three fields, three values:

- **`Status`** — `running` while a scan is in flight; `idle` between scans.
- **`Last completed`** — wall-clock timestamp of the last successful scan completion.
- **`Next scan after`** — when the next scan is eligible to run. Computed at completion as `Last completed + <cool-down>`.

### Lifecycle

1. **Entering idle.** `work_queue()` returned empty. If `Status: running` was already set (from a previous boot interrupted mid-scan), restart the scan — improvement scans are idempotent, a fresh scan subsumes a partial one.
2. **Eligibility check.** If `Next scan after` is missing (no prior scan) or in the past, the agent is eligible — proceed to step 3. If `Next scan after` is in the future, you are NOT eligible yet — proceed to step 5 (wait).
3. **Start scan.** Write `Status: running` to working-state (atomic). Then run your role's scanning sub-skill:
   - **PM**: `→ run sub-skill: roles/pm/improvement-scan`
   - **Worker (skill / web / ios / android / fullstack)**: `→ run sub-skill: improvement-scan`
   - **Verifier**: `→ run sub-skill: improvement-scan-slim` (filing-only — verifier never auto-fixes)
   - **DM**: `→ run sub-skill: improvement-scan-slim` (filing-only)
4. **Complete scan.** Read the cool-down value from `config.md`. Compute `Next scan after = now + cooldown`. Write under `## Improvement Scan`:
   ```
   Status: idle
   Last completed: <YYYY-MM-DD HH:MM>
   Next scan after: <YYYY-MM-DD HH:MM>
   ```
   Note: `Next scan after` is **stored**, not derived on the fly — this is the only place the cool-down value is read.
4a. **Re-check the queue.** Run `work_queue()` immediately after writing the scan-completion fields. A task may have arrived during the scan (or during the crashed-out window if this was a crash-recovery restart). If `work_queue()` returns work, **exit the cool-down loop** — transition the top item to `in-progress`, update the Task field in `working-state.md`, and begin work directly (no need to wait for an event, since you already have the item). Only if `work_queue()` is empty proceed to step 5.
5. **Wait via the Monitor.** The persistent Monitor (see [[event-mode-contract]] "How You Listen") delivers `NUDGE` wake signals at a short fixed cadence; you do not perform a long blocking sleep. After each empty poll interval:
   - If `now >= Next scan after` → run the next improvement scan (back to step 3).
   - If a `NUDGE` arrives in the meantime → the Monitor wakes Case B in [[event-mode-contract]] (you `GET /events/for`, forge-read, possibly pick up new work). The cool-down timer keeps running in the background; when work completes (Case C) and the queue is empty again, return here for the eligibility check.

### Atomicity

- **An event arrives during an in-flight scan** → finish the scan first (atomicity rule). Process the event when the scan completes.
- **Crash mid-scan** → on boot, working-state shows `Status: running`. Skip forge verification for the scan, restart it from scratch. Scans are idempotent. After the restarted scan completes, run `work_queue()` (step 4a above) before re-entering the cool-down loop — a task may have arrived during the outage.

#### How Monitor Buffering Interacts With Scans (#9743)

The atomicity rule above is enforced **by the Claude Code runtime**, not by anything in your sub-skill. Spell this out so the failure modes are unsurprising:

- While you are mid-scan (running a tool call), the persistent Monitor's stdout — `event_poll.py`'s `NUDGE` lines — is **buffered** by the Claude Code runtime. You will not see those nudges until the tool call returns and the next turn begins. This is what makes "finish the scan first" possible without you needing to poll Monitor mid-tool.
- A `NUDGE` carries **no payload** — it is only a wake signal. However many buffered nudges arrive, you respond the same way on the next turn: one `GET /events/for/{role}?since=<cursor>` surfaces every event past your cursor, oldest-first. The harness GET (not the nudge stream) is what orders events; coalesced or duplicate nudges are harmless.
- The cursor is **harness-owned** and advances only when **you** POST `ack-cursor` after tending an event — so it tracks "processed by the agent", not "delivered to a transport". `event_poll.py` never touches the cursor.
- **Crash window**: because the cursor advances only on your post-processing ack (at-least-once), an event you have not yet tended is still past the cursor — a crash re-delivers it on the next `GET`. Nothing is lost at the cursor layer. As an additional backstop, step 4a (Re-check the queue) runs `work_queue()` after every scan completion and after every crash-recovery restart — a fresh forge-read that absorbs any tracker state an event would have communicated (per [[forge-read-pattern]] — the forge is authoritative; events are hints), and anything that happened during an outage.
- **You do NOT try to replay missed events or rebuild from a buffered-but-unprocessed nudge.** The forge-read pattern is the recovery mechanism. Designing a sub-skill that tries to recover events out of the nudge stream would violate [[forge-read-pattern]].

### Cool-Down Configuration

`config.md` carries the default:

```
- **Improvement Scan Cool-Down**: 30m
```

Per-role overrides may be added (e.g. `Improvement Scan Cool-Down (qa)`) but are NOT shipped initially. All roles share the same default cool-down (defined in `config.md`) unless config says otherwise.
