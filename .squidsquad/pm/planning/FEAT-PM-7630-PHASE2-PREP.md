# FEAT-PM-7630 Discussion Prep

## Recommended Question Order

1. **Q1 — Wake mechanism** (all others depend on this)
   - The harness-to-agent signaling model constrains Q3 (which command replaces `/loop`), shapes Q2 (who writes cycle-output.json and when), affects the stop-requested event design, and determines whether terminal-close-on-stop is feasible.
2. **Q-STOP — Stop signal design** (depends on Q1; enables terminal cleanup)
   - Once the wake model is settled, the stop signal is the mirror: how does the harness tell a running agent to exit cleanly between cycles.
3. **Q3 — What replaces `/loop`** (depends on Q1)
   - The scheduling mechanism follows directly from the wake model. Stateless spawn = no `/loop` at all. Persistent session = something must replace it.
4. **Q-MONITOR — Monitor tool / version gate** (depends on Q1 and Q3)
   - The Monitor tool is only relevant if the wake model requires event-driven file watching. Resolve Q1 first; if stateless spawn is chosen, Monitor tool is irrelevant.
5. **Q2 — cycle-output.json contract** (depends on Q1 and Q3)
   - Output format and ownership follow from whether agents are stateless workers (harness extracts output) or persistent sessions (agent writes JSON, harness reads it).
6. **Q4 — PM improvement scanning** (depends on Q1, Q2, Q3)
   - The scanning trigger and delivery mechanism assume a settled wake + output contract.

---

## Questions by Category

---

### Category: Wake Mechanism

#### Q1: How does the harness wake an agent to do creative work?
**Why this matters**: This is the load-bearing decision. Claude Code sessions are conversational — the harness can spawn a session but currently has no mechanism to inject new work into a running one. Getting this wrong means rebuilding the entire activation chain after everything else is built around it.
**Depends on**: none — this is the root decision.

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A (recommended) | **Stateless spawn-per-event**: harness kills the session after each work item, respawns with a fresh "you have work" prompt when the next event arrives. Working-state.md provides continuity across spawns. | Simplest implementation — no new signaling protocol needed. Clean isolation per work item. Session context never bloats across multiple work items. Aligns with existing pattern: working-state.md already handles context-reset continuity. Crash recovery is trivial (harness just respawns). | Loses in-session working memory between work items (mitigated by working-state.md). Cold-start latency on each spawn (Claude Code boot ~5-10s). Session continuity for long multi-step tasks requires robust checkpointing. |
| B | **Persistent session + file polling**: harness writes a trigger file (e.g., `.squidsquad/<role>/wake-trigger`) when work is available; agent's statusline hook detects the file and re-invokes the work loop. | No spawn overhead — agent reacts in <1s. Preserves in-session memory for long-running tasks. | Requires Claude Code hook support for file-change detection (not confirmed available). File polling introduces a race between harness writing the trigger and agent reading it. Complex to implement reliably on Windows (file locking, watcher latency). |
| C | **Persistent session + HTTP callback**: harness exposes a POST endpoint that Claude Code calls to register itself, then harness calls back into a Claude Code API to inject a message. | Low latency, push-based. | Claude Code has no documented inbound API for message injection into a running session. This would require reverse-engineering or a Claude Code plugin mechanism that doesn't exist today. Highest implementation risk. |

**PM recommendation**: Option A. The stateless spawn model is the only option with a clear, implementable path today. Working-state.md checkpointing is already battle-tested from #2057. The cold-start latency is acceptable given 30-minute cycle intervals. Pursue B only after confirming Claude Code hook support for file-change events.

---

#### Q-MONITOR: The Monitor tool is the wake mechanism — but current install (v2.1.86) lacks it (requires v2.1.98+). How do we handle the version gap?
**Why this matters**: If the design depends on the Monitor tool for event-driven wake, agents on v2.1.86 cannot use it. Shipping a feature that only works on a version that isn't installed yet creates a broken-on-arrival release or forces an upgrade gate that isn't managed.
**Depends on**: Q1 (Monitor tool is only relevant if persistent-session wake is chosen; irrelevant for stateless spawn).

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A (recommended) | **Design for stateless spawn (Q1-A); treat Monitor tool as future enhancement**: v1 of #7630 uses spawn-per-event. If Claude Code v2.1.98+ is available when a future cycle designs Phase 2B, add Monitor tool as an optional fast-path. Gate it behind a config flag. | No version dependency in v1. Ships immediately on any Claude Code version. Monitor tool becomes an optimization, not a requirement. | Stateless spawn has higher latency than Monitor tool. If Monitor tool becomes available soon, we may do redundant work. |
| B | **Block #7630 Phase 2 until v2.1.98+ is installed and confirmed**: treat the Monitor tool as a hard requirement and don't proceed until the upgrade is verified. | Uses the purpose-built mechanism. Lower implementation risk once available. | Delays the entire EPIC on an external dependency. Version upgrade may introduce other regressions. No fallback if Monitor tool API changes. |
| C | **Implement both paths**: stateless spawn as the fallback, Monitor tool as the primary — detect version at runtime and pick the path. | Best of both: works today, uses Monitor tool when available. | Double the implementation surface. Two code paths to maintain and test. Complexity cost may exceed the latency benefit. |

**PM recommendation**: Option A. Build Phase 2 around stateless spawn (Q1-A). Add a config flag `wake-mechanism: spawn | monitor` so the Monitor tool path can be added later without architectural changes. File a separate task to update Claude Code and validate the Monitor tool API before committing to it.

---

### Category: Architecture

#### Q2: Does the agent still write `cycle-output.json`, or does the harness extract work results differently?
**Why this matters**: cycle-output.json is the contract between agent creative work and mechanical post-processing (status transitions, tracker comments, iteration logs, git commits). If the format or ownership changes, every role's template and every post-cycle script is affected. Getting this wrong breaks delivery for all roles.
**Depends on**: Q1 (stateless spawn → harness controls when agent exits, so it can capture structured output before teardown; persistent session → agent must write file proactively).

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A (recommended) | **Agent still writes cycle-output.json; harness reads it post-exit**: the output contract is unchanged. Agent writes the JSON file at the end of its creative work, exits (or signals completion), and harness runs cycle_post.py. | Zero template migration risk for the output format. All role-specific extras (code_commit, pr_actions, vault_writes) continue to work. Harness reads the file exactly as today. | Agent must still know to write the file — some "mechanical" residue stays in templates. File must be written before crash/exit to avoid data loss. |
| B | **Agent writes a simplified result blob; harness does all post-processing**: agent outputs a minimal JSON (`{"summary": "...", "items_worked": [...]}`) and harness infers all status transitions from event bus state and tracker queries. | Templates shrink significantly — agents describe outcomes in natural language. Harness becomes the single source of truth for state. | Harness must replicate all the business logic currently in cycle_post.py (role-specific extras, status transition rules, version bumps). High reimplementation risk. Natural language summaries are ambiguous — harness can't reliably infer `pending-test` vs `pending-ship` from prose. |
| C | **Eliminate cycle-output.json entirely; agent calls harness API directly**: agent makes REST calls to harness endpoints (`POST /agents/{role}/transition`, `POST /agents/{role}/comment`) during its work. | Real-time feedback — harness knows what's happening as it happens. No file-based coordination. | Agent templates must encode API call syntax — more mechanical residue than today, not less. Network errors during creative work cause partial state. Rollback is hard. |

**PM recommendation**: Option A. The cycle-output.json contract is one of the most stable interfaces in the system. Preserving it costs nothing and avoids a high-risk rewrite of cycle_post.py. The template change for #7630 is to *remove cycle mechanics*, not to redesign the output format — keep these concerns separate.

---

#### Q-STOP: Agents currently can't detect a stop signal between cycles. How should the harness signal an intent:stop-requested event?
**Why this matters**: Without a stop signal, a running agent will start a new cycle even after the human has requested a stop. The only way to interrupt today is to kill the process, which loses in-flight state. A clean stop mechanism is required for the event-driven model to be production-safe.
**Depends on**: Q1 (the stop signal is the mirror of the wake signal — same channel, opposite direction).

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A (recommended) | **Harness writes `.squidsquad/<role>/stop-requested` sentinel file; cycle_pre.py checks for it at cycle start and exits cleanly**: agent reads the sentinel at the top of each cycle, writes a final working-state checkpoint, runs cycle_post.py with `cycle_type: suppressed`, then exits. Harness deletes the sentinel after detecting agent exit. | Consistent with existing sentinel pattern (`.stop-after-cycle`, `.stop`). cycle_pre.py already reads many such files. Clean checkpoint before exit. Works for both stateless spawn and persistent session. | One-cycle delay: agent won't stop until the current cycle completes. For a 30-min cycle, worst case is 30 minutes. Sentinel file must be cleaned up on harness restart to avoid stale stops. |
| B | **Harness emits `intent:stop-requested` on the event bus; cycle_pre.py reads recent_events and exits if the event is present**: stop signal travels through the same channel as all other events. | Unified signaling channel — no new files or protocols. | Event bus is not guaranteed delivery — if harness crashes after emitting but before agent reads, stop is lost. Events are filtered by role; stop must be delivered reliably regardless of filtering. |
| C | **Harness uses SIGTERM / process signal to interrupt the agent mid-cycle**: harness sends SIGTERM to the Claude Code process, which triggers a graceful shutdown handler in thin_launcher.py. | Immediate — no cycle delay. | Claude Code process handling of SIGTERM is not documented — may not trigger a graceful handler. Could corrupt in-flight writes. Windows signal handling is unreliable (SIGTERM not supported natively). |

**PM recommendation**: Option A. Sentinel files are already the established pattern and they work on Windows. The one-cycle delay is acceptable — the harness should also set intent=stopping so the process isn't rebooted if it exits between cycles. Pair this with the terminal-close question below.

---

#### Q-TERMINAL: Should the harness close agent terminal windows on stop?
**Why this matters**: Orphaned terminal windows after a stop are a UX problem — the human sees a window with a dead agent and no clear signal that it's intentional. On Windows, terminal windows are more persistent than on Unix. If the harness doesn't own terminal lifecycle, the human must manually close them.
**Depends on**: Q1 (stateless spawn creates and destroys windows per work item; persistent session keeps the window open between items).

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A (recommended) | **Harness closes the terminal window after detecting clean agent exit on stop intent**: when an agent exits with intent=stopping, harness issues the platform-appropriate window close (Windows: `taskkill /PID`, Unix: `kill` the terminal process). Only on stop — not on crash or context-pressure restart. | Clean UX — no orphaned windows. Consistent lifecycle ownership (harness opens, harness closes). | Requires tracking the terminal PID separately from the agent PID (thin_launcher.py spawns in a new window — harness must record the window PID at spawn time). Platform differences in terminal close must be handled. |
| B | **Leave terminal windows open after stop; human closes manually**: current behavior. | Zero implementation cost. | Poor UX for teams running multiple agents. Human must know which windows belong to which agents. Stale terminal windows can confuse health monitoring (PID reuse). |
| C | **Harness closes all terminal windows on full team stop; individual agent stops leave windows open**: only close on `start_team.py --stop --all`. | Compromise — team stop is a clear signal, individual stop is ambiguous. | Inconsistent behavior. Individual agent stops (for upgrades, reboots) are common and also deserve clean windows. |

**PM recommendation**: Option A. Harness already tracks agent PIDs — extend thin_launcher.py to return the window PID at spawn, store it in `.harness-state.json`, and issue a close on clean stop exit. Implement this as a separate sub-task of #7630 Phase 4 (operational cleanup), not Phase 2.

---

### Category: Template Migration

#### Q3: What replaces the `/loop` command?
**Why this matters**: `/loop [INTERVAL]m` is the current agent self-scheduling mechanism. Removing it without a replacement means agents have no activation model — they run once and stop. The replacement must work with the chosen wake mechanism (Q1) and must not require agents to know about their own scheduling.
**Depends on**: Q1 (stateless spawn = `/loop` is simply removed, harness respawns; persistent session = something must replace the re-invocation trigger).

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A (recommended) | **Remove `/loop` entirely; harness respawns the agent when events arrive (stateless spawn model)**: thin_launcher.py boot prompt changes from "Boot. Begin your first Ralph Loop cycle now." to "You have been woken to process a work item. Read `.squidsquad/<role>/work-context.json` and do your creative work." Agent exits after completing work. Harness respawns on next event. | Simplest template change — one line removed from every instructions.md. No scheduling logic in agent templates at all. Interval becomes a harness config value only. | Requires harness to reliably detect agent exit and match it to work completion (not crash). Boot prompt becomes the primary agent orientation text — must be complete and accurate. |
| B | **Replace `/loop` with a file-based loop signal**: agent writes `.squidsquad/<role>/request-wake` at cycle end; harness detects the file, waits the interval, then sends the wake signal. Agent template changes from `/loop 30m` to "write request-wake and exit." | Preserves the concept of agent-controlled scheduling without the Claude Code-specific `/loop` command. Harness can override the interval from config. | Still requires agents to know about scheduling mechanics. Two-file protocol (request-wake + work-context) adds complexity. Harness must clean up stale request-wake files on crash recovery. |
| C | **Keep `/loop` but change the interval to 0**: agent loops as fast as possible, cycle_pre.py returns `suppressed: true` when no events are pending, agent skips work and immediately re-loops. | Minimal template change — interval parameter only. | Wastes Claude Code API calls on suppressed cycles. Context window grows with each suppressed cycle loop. Not truly event-driven — still polling. |

**PM recommendation**: Option A. Removing `/loop` entirely is the correct outcome for an event-driven architecture. It forces the harness to own activation fully. The template change is straightforward: strip the `/loop` call from thin_launcher.py's boot prompt and all instructions.md files. This is Phase 3 work (template migration) — straightforward once Phase 2 (wake mechanism) is built.

---

### Category: Operational

#### Q4: How does PM's improvement scanning work in event-driven mode?
**Why this matters**: PM's improvement scan is the canonical example of LLM-unreliable cyclic discipline — PM dropped it for 15+ cycles, which is the core motivation for #7630. If the event-driven model doesn't deterministically trigger scanning, the whole motivation for the EPIC is undermined for PM's most important background task.
**Depends on**: Q1, Q2, Q3 (scanning is a work item delivered to PM by the harness; its trigger and output format follow from the settled wake + output contract).

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A (recommended) | **Harness emits a `scan-due` event after N consecutive quiet cycles (no work events for PM)**: PM's `wake-on-events` config includes `scan-due`. Harness tracks consecutive quiet cycles in its state and emits `scan-due` when threshold is reached. PM is woken, reads the `scan-due` payload (which includes scan targets), runs the scan, writes results to cycle-output.json, exits. | Deterministic trigger — harness enforces it regardless of PM's prose instructions. Scan target selection is a harness config value, not LLM discretion. Eliminates the 15-cycle drop problem. | Harness must track quiet cycle count per role — new state to persist in `.harness-state.json`. Quiet cycle definition must be precise (no active work items, no pending events, no in-progress tasks). |
| B | **Harness emits a `scan-due` event on a fixed cron schedule** (e.g., every 4 hours): scan trigger is time-based, not cycle-count-based. PM's wake-on-events includes `scan-due`. | Simpler harness logic — no need to count quiet cycles. Predictable cadence. | Time-based schedule may fire during active work periods, displacing real work. Doesn't align with the "quiet cycle" semantics already established in the codebase (cycle_type: quiet). |
| C | **Keep improvement scanning in PM's prose template but add a harness-side counter that logs a warning when the scan has been skipped >3 consecutive quiet cycles**: harness doesn't trigger scanning, but it detects the skip and alerts. | Minimal harness change. PM retains autonomy. | Doesn't solve the problem — PM can still ignore the warning. Evidence shows PM does ignore it. This is the current state, renamed. |

**PM recommendation**: Option A. The harness must own the scan trigger — that's the point of #7630. Quiet-cycle counting is modest harness state (a single integer per role in `.harness-state.json`). The `scan-due` event payload should include: suggested scan targets (from scan_index.py output pre-computed by harness), quiet cycle count, and last scan timestamp. PM creative work becomes: read scan-due payload, run scan on suggested targets, write findings to cycle-output.json. No prose-driven remembering required.
