---
slot: instructions
ordinal: 16
---

## Idle = Improvement-Scan Cool-Down Loop

When `work_queue(<role>)` returns no **autonomously-actionable** item — either genuinely empty, or containing only `approved` tasks that are human-gated or blocked on an unmet dependency (#13316: "gated" is not a tracker status, so this is a judgment call you make by reading each returned item, not a raw emptiness check) — you are **not** finished — you enter the improvement-scan cool-down loop. Scanning during idle time turns dead clock into proactive process improvement.

### Two wake sources during idle

An idle event-mode agent has **two independent, orthogonal wake sources** (AGENT-RUNTIME §8.6.1) — both feed the same §8.1 loop entry:

- **Monitor / `event_poll`** → forge-event `NUDGE` → *productive* work. `event_poll` emits a `NUDGE` **only when real forge events arrive past your cursor** — it is **silent on an empty poll**. It does NOT deliver wakes on a fixed cadence.
- **Periodic driver (cron)** → timer tick → *idle-work* check. Because `event_poll` never wakes a genuinely-idle agent, you schedule a dedicated low-frequency self-wake the first time you go idle. That timer — not the Monitor — is the cadence source that re-enters this loop so the throttle is re-checked and the scan eventually fires. Without it the subloop is dormant (the #12506 bug: zero idle scans for weeks).

The driver's *decisions* (when to arm, scan, cancel, re-arm) are owned by the deterministic state machine `references/scripts/subloop_driver.py`; your job is to map each returned `action` to the matching scheduling tool call (`CronCreate` / `CronDelete`). The *scheduling primitive* is `CronCreate` with `recurring: true, durable: false` (a session-scoped, runtime-side self-wake — no harness change). Substitute your own alias for `<alias>` below.

### Working-State Schema

The cool-down accounting lives in the driver state file `.squidsquad/<alias>/.subloop-driver.json` (`{armed, scan_count, last_run}`), written by `subloop_driver.py` — you do not hand-edit it. The legacy `## Improvement Scan` block in `working-state.md` (`Status` / `Last completed` / `Next scan after`) is informational only; the driver state file is authoritative for throttle and burst accounting.

### Lifecycle

**Step A — Enter idle (`work_queue()` returned no autonomously-actionable item — see the actionability note above).** Arm the driver:

1. Run `python references/scripts/subloop_driver.py arm <alias>`.
   - `action=schedule` → the driver just transitioned disarmed→armed (lazy first-idle enable). You must create the self-wake.
   - `action=already-armed` → the state already considers the driver armed (e.g. earlier this idle period).
2. **Confirm a live driver cron exists in *this* session** via `CronList`. The cron is `durable: false`, so a restart loses the in-memory job even though `.subloop-driver.json` still says `armed`. **If no driver job is listed in `CronList`, create one — regardless of what `arm` returned.** (A missing cron arises in two ways: `action=schedule` from a fresh arm, or `action=already-armed` after a restart dropped the session-scoped cron. Both are handled by the same rule: no live cron ⇒ create one.)

   ```
   CronCreate(
     cron: "<expr>",                # derived from interval_minutes — see below; default 30 → "7,37 * * * *"
     recurring: true,
     durable: false,
     prompt: "SquidSquad idle-driver tick (<alias>): forge-read work_queue(), then run subloop_driver.py tick and act on the action per idle-cooldown-loop Step B."
   )
   ```

   Record the returned job ID for `CronDelete`. (Recover it later via `CronList` — match on the `idle-driver tick` prompt marker — if it falls out of conversation context.)

   **Building `<expr>` from `interval_minutes`** (the value in the `arm` / `reidle` / `already-armed` output; default 30): pick an off-peak minute offset `s` in 1–9 (avoid `0` and `30` — every agent picking those aligns the whole fleet's wakes), then —
   - `interval_minutes` divides 60 evenly (15, 20, 30, 60) → fire at `s, s+interval, s+2·interval, … < 60`. E.g. 30, s=7 → `7,37 * * * *`; 20, s=7 → `7,27,47 * * * *`; 60, s=7 → `7 * * * *`.
   - otherwise → round `interval_minutes` **down** to the nearest of {15, 20, 30} and use that.

   The cron is **only a heartbeat** — `tick`'s `cooldown_elapsed` gate (Step B) enforces the real cool-down before any scan — so the exact minutes never cause an early or extra scan; approximation is safe.
3. Re-enter Monitor idle-wait. A `NUDGE` (Step C) or a driver-tick prompt (Step B) will wake you.

**Step B — Driver tick fires** (the cron-enqueued prompt re-enters you). Per §8.6.1 the driver **forge-reads `work_queue()` first** — so it doubles as a safety-net against a missed nudge. Then run `python references/scripts/subloop_driver.py tick <alias> --drained <true|false>` and act on the `action`. **`drained` means "no autonomously-actionable item," not "queue is empty"** (#13316): compute it by reading each returned item — `drained=true` iff `work_queue()` is genuinely empty, **or** every item it returned is human-gated (e.g. flagged for human/manual execution) or blocked on an unmet dependency (e.g. gated on an unshipped story). A strict `work_queue() != []` reading is wrong here: an approved-but-unpickable queue forces `absorb-work` on an item you cannot actually pick up, starving idle-scan forever (the failure this note exists to prevent).

- `absorb-work` → the queue is **not** drained (an autonomously-actionable item arrived / a nudge was missed) — not merely "the queue is non-empty." Exit the cool-down loop: pick up the top **actionable** item (transition it `in-progress`, write the Task field in `working-state.md`), do the work. On completion, re-idle via **Step D**.
- `scan` → drained **and** throttle elapsed. Run your role's scanning sub-skill — **one bounded task**:
  - **PM**: `→ run sub-skill: roles/pm/improvement-scan`
  - **Worker (skill / web / ios / android / fullstack)**: `→ run sub-skill: improvement-scan`
  - **Verifier**: `→ run sub-skill: improvement-scan-slim` (filing-only — verifier never auto-fixes)
  - **DM**: `→ run sub-skill: improvement-scan-slim` (filing-only)

  Then record it: `python references/scripts/subloop_driver.py record-scan <alias>`. If the output has `at_cap: true`, the burst limit is reached — **cancel the driver**: run `subloop_driver.py cancel <alias>` and `CronDelete(<job id>)`. Otherwise leave the cron running for the next tick.
- `wait` → drained but the throttle window has not elapsed. Do nothing; leave the cron running (the next tick re-checks eligibility).
- `cancel` → stop the driver. **Check `reason`:**
  - `reason: at-cap` → the driver hit the burst limit but is **still armed** (this is the path when a tick — e.g. the first tick after a restart that reloaded `scan_count` already at the cap — finds the burst exhausted without having just scanned). You MUST run `subloop_driver.py cancel <alias>` to flip `armed` to false, **and** `CronDelete(<job id>)`. Skipping the `cancel` CLI leaves `armed: true` with no cron — a permanent dormancy (the #12506 bug) that repeats on every restart.
  - `reason: disarmed` → the driver is already disarmed (defensive: a stale tick fired after a `cancel`). Just `CronDelete(<job id>)` if it is still scheduled.

  (The `scan` path above already runs `subloop_driver.py cancel` + `CronDelete` when `record-scan` reports `at_cap: true` — that is the normal at-cap exit. The `cancel`/`at-cap` action here is the same disarm for the case where the cap is discovered on a tick rather than right after a scan.)

**Step C — `NUDGE` arrives while idle** (forge event). Handle it as Case B in [[event-mode-contract]]: `GET /events/for/{role}?since=<cursor>`, forge-read, pick up new work if any. The driver cron keeps running in the background; when the work completes and you re-idle, go to **Step D**.

**Step D — Re-idle after processing forge work** (a fresh idle period). Run `python references/scripts/subloop_driver.py reidle <alias>` — this re-arms the driver and **resets `scan_count` to 0** (a fresh burst), while preserving `last_run` so the global cool-down throttle still holds across the re-arm.
- `action=schedule` → the driver had cancelled at cap; create a new self-wake (`CronCreate` as in Step A, record the new job ID).
- `action=already-armed` → the counter is reset; no *new* cron is needed, but **always** confirm a live cron exists via `CronList` (as in Step A.2) and create one if none is listed — the cron is session-scoped and may have been lost across a restart. Do not try to reason about whether a restart happened; the `CronList` check is cheap and idempotent.

Net per sustained-idle stretch: up to `Idle Scan Burst` scans, then the driver quiesces (cron cancelled) until new forge activity re-idles it — bounded, not a perpetual loop.

### Atomicity

- **An event arrives during an in-flight scan** → finish the scan first (atomicity rule). Process the event when the scan completes.
- **A driver tick arrives mid-task or mid-scan** → treat it exactly like a mid-task `NUDGE`: note it, finish the current atomic unit, then the next forge-read absorbs it (§8.5). The cron + Monitor coexist without racing — the cron fires as a scheduled tool-invocation, not on Monitor's stdin.
- **Crash mid-scan** → on boot, `.subloop-driver.json` shows the pre-crash `armed`/`scan_count`/`last_run`. The in-memory cron is gone (session-scoped); Step A.2's `CronList` confirm re-creates it on the next idle. Scans are idempotent — `last_run` preserves the throttle so a restart does not bypass the cool-down. After any restart, run `work_queue()` before re-entering the cool-down loop — a task may have arrived during the outage.

#### How Monitor Buffering Interacts With Scans (#9743)

The atomicity rule above is enforced **by the Claude Code runtime**, not by anything in your sub-skill. Spell this out so the failure modes are unsurprising:

- While you are mid-scan (running a tool call), the persistent Monitor's stdout — `event_poll.py`'s `NUDGE` lines — and any cron-tick prompt are **buffered** by the Claude Code runtime. You will not see them until the tool call returns and the next turn begins. This is what makes "finish the scan first" possible without you needing to poll mid-tool.
- A `NUDGE` carries **no payload** — it is only a wake signal. However many buffered nudges arrive, you respond the same way on the next turn: one `GET /events/for/{role}?since=<cursor>` surfaces every event past your cursor, oldest-first. The harness GET (not the nudge stream) is what orders events; coalesced or duplicate nudges are harmless.
- The cursor is **harness-owned** and advances only when **you** POST `ack-cursor` after tending an event — so it tracks "processed by the agent", not "delivered to a transport". `event_poll.py` never touches the cursor.
- **Crash window**: because the cursor advances only on your post-processing ack (at-least-once), an event you have not yet tended is still past the cursor — a crash re-delivers it on the next `GET`. Nothing is lost at the cursor layer. As an additional backstop, the driver tick (Step B) forge-reads `work_queue()` first — a fresh forge-read that absorbs any tracker state an event would have communicated (per [[forge-read-pattern]] — the forge is authoritative; events are hints), and anything that happened during an outage.
- **You do NOT try to replay missed events or rebuild from a buffered-but-unprocessed nudge.** The forge-read pattern is the recovery mechanism. Designing a sub-skill that tries to recover events out of the nudge stream would violate [[forge-read-pattern]].

### Cool-Down Configuration

`config.md`'s `## Improvement Scanning` section carries the driver's two knobs:

```
- **Improvement Scan Cool-Down**: 30m
- **Idle Scan Burst**: 3
```

- **`Improvement Scan Cool-Down`** — minutes between idle scans (the throttle the `tick` decision enforces). Carries an `m` suffix (`30m`); `subloop_driver.py` also tolerates a bare integer (`30`) for legacy installs, falling back to 30 when unparseable.
- **`Idle Scan Burst`** — max scans per sustained-idle period before the driver cancels itself (default 3 if the key is absent — graceful per §8.6.1). After this many scans the burst quiesces; processing new forge work and re-idling (Step D) resets the count.

Per-role overrides may be added (e.g. `Improvement Scan Cool-Down (qa)`) but are NOT shipped initially. All roles share the same defaults unless config says otherwise.
