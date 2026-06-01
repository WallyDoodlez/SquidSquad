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
3. **Start scan.** Write `Status: running` to working-state (atomic). Run your role's scanning sub-skill.
4. **Complete scan.** Read the cool-down value from `config.md`. Compute `Next scan after = now + cooldown`. Write under `## Improvement Scan`:
   ```
   Status: idle
   Last completed: <YYYY-MM-DD HH:MM>
   Next scan after: <YYYY-MM-DD HH:MM>
   ```
   Note: `Next scan after` is **stored**, not derived on the fly — this is the only place the cool-down value is read.
4a. **Re-check the queue.** Run `work_queue()` immediately after writing the scan-completion fields. A task may have arrived during the scan (or during the crashed-out window if this was a crash-recovery restart). If `work_queue()` returns work, **exit the cool-down loop** — transition the top item to `in-progress`, update the Task field in `working-state.md`, and begin work directly (no need to wait for an event, since you already have the item). Only if `work_queue()` is empty proceed to step 5.
5. **Wait via the Monitor.** The persistent Monitor (see [[l1-base]] "How You Listen") delivers events at a short fixed cadence; you do not perform a long blocking sleep. After each empty poll interval:
   - If `now >= Next scan after` → run the next improvement scan (back to step 3).
   - If a task-relevant event arrives in the meantime → the Monitor wakes Case B in [[l1-base]] (forge-read, possibly pick up new work). The cool-down timer keeps running in the background; when work completes (Case C) and the queue is empty again, return here for the eligibility check.

### Atomicity

- **An event arrives during an in-flight scan** → finish the scan first (atomicity rule). Process the event when the scan completes.
- **Crash mid-scan** → on boot, working-state shows `Status: running`. Skip forge verification for the scan, restart it from scratch. Scans are idempotent. After the restarted scan completes, run `work_queue()` (step 4a above) before re-entering the cool-down loop — a task may have arrived during the outage.

#### How Monitor Buffering Interacts With Scans (#9743)

The atomicity rule above is enforced **by the Claude Code runtime**, not by anything in your sub-skill. Spell this out so the failure modes are unsurprising:

- While you are mid-scan (running a tool call), the persistent Monitor's stdout — `event_poll.py`'s JSON lines — is **buffered** by the Claude Code runtime. You will not see those lines until the tool call returns and the next turn begins. This is what makes "finish the scan first" possible without you needing to poll Monitor mid-tool.
- The buffered lines arrive **in order** on the next turn. Process them in arrival order; do not re-order based on payload timestamp. Per-event ordering is the contract event_poll.py + the Monitor pipeline guarantee.
- `event_poll.py` advances its on-disk cursor as it writes each line to stdout — the cursor is past the line **before** you have seen it. This is intentional: the cursor tracks "delivered to the agent's transport", not "processed by the agent".
- **Crash window**: if the agent crashes between event_poll.py advancing the cursor and the agent processing the buffered line, that line is lost from the event stream — the cursor has moved past it on disk. This is **acceptable** because step 4a (Re-check the queue) runs `work_queue()` after every scan completion and after every crash-recovery restart, and `work_queue()` is a fresh forge-read that absorbs any tracker state the lost event would have communicated (per [[forge-read-pattern]] — the forge is authoritative; events are hints). The same forge-read also absorbs anything that happened during the outage window.
- **You do NOT try to read the cursor back, replay missed events, or rebuild from a buffered-but-unprocessed line.** The forge-read pattern is the recovery mechanism. Designing a sub-skill that tries to recover events out of the on-disk cursor would violate [[forge-read-pattern]].

### Cool-Down Configuration

`config.md` carries the default:

```
- **Improvement Scan Cool-Down**: 30m
```

Per-role overrides may be added (e.g. `Improvement Scan Cool-Down (qa)`) but are NOT shipped initially. All roles share the same default cool-down (defined in `config.md`) unless config says otherwise.
