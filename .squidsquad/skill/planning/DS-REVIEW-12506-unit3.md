I now have all the evidence needed. Here are my findings:

---

### Finding 1

- **File**: `references/sub-skills/common-events/idle-cooldown-loop.md`
- **Line**: 55
- **Severity**: error
- **Issue**: The `cancel` action description in Step B only handles the `reason: "disarmed"` case ("the driver is already disarmed"), but `tick()` at `subloop_driver.py:235` also returns `{"action": "cancel", "reason": "at-cap", ...}` when `scan_count >= burst` but the driver is still **armed**. The prose never tells the agent to run `subloop_driver.py cancel <alias>` for the "at-cap" path — only `CronDelete`. This creates an unrecoverable dormancy state in the crash-recovery path.

- **Evidence**: Trace the crash-recovery scenario: agent crashes after `record-scan` (scan_count=3, at_cap=true) but before `cancel` CLI. State file has `armed: true, scan_count: 3`. On restart → Step A: `arm` returns `already-armed` (line 182, armed=true). CronList finds no cron → agent re-creates one. Tick fires → `tick()` returns `{"action": "cancel", "reason": "at-cap"}` (line 235). Agent follows Step B line 55: only `CronDelete`, NOT `cancel` CLI. Result: `armed` stays `true`, cron deleted, no wake source → **permanent idle** (#12506 dormancy regression). The state file stuck at `armed:true, scan_count:3` guarantees this repeats on every restart.

- **Suggested fix**: Split the `cancel` action handling in Step B by reason:
  - `cancel` with `reason: "at-cap"` (or any cancel from tick where the driver may still be armed) → run `subloop_driver.py cancel <alias>` **and** `CronDelete(<job id>)`.
  - `cancel` with `reason: "disarmed"` → `CronDelete(<job id>)` if still scheduled (current behavior).
  
  Alternatively, make `tick()` call `cancel()` internally when it returns the at-cap cancel, so the agent only ever sees `cancel` from an already-disarmed state. Either approach closes the gap.

---

### Finding 2

- **File**: `references/sub-skills/common-events/idle-cooldown-loop.md`
- **Line**: 61
- **Severity**: warning
- **Issue**: Step D's `already-armed` branch says "still confirm a live cron via `CronList` per Step A.2 **if this is the first idle since a restart**." An LLM agent cannot reliably determine whether it's "the first idle since a restart." If the agent decides it is NOT and skips the CronList check, a missing cron (lost across session boundary, or deleted by a concurrent operation) will not be re-created → dormancy.

- **Evidence**: The cron is `durable: false` (line 36), so in-memory state vanishes on any session end. The conditional "if this is the first idle since a restart" invites the agent to make a binary decision on an undecidable predicate. The CronList check is cheap and idempotent — there is no harm in always performing it. The conditional adds risk with no benefit.

- **Suggested fix**: Remove the conditional. Change line 61 to: `"no new cron needed, but always confirm a live cron exists via CronList (as in Step A.2) — the cron is session-scoped and may have been lost."`

---

### Finding 3

- **File**: `references/scripts/subloop_driver.py`
- **Line**: 182
- **Severity**: warning
- **Issue**: `arm()` returns `{"action": "already-armed", "scan_count": ...}` — without `interval_minutes`. But Step A.2 of the prose (idle-cooldown-loop.md:41) says to "Build the `cron` expression from `arm`'s `interval_minutes`" when creating a cron after CronList shows none. If the agent gets `already-armed` AND CronList shows no cron (restart scenario), it must create a cron but has no `interval_minutes` from the `arm` output to build the expression.

- **Evidence**: Compare `arm` line 182 (`return {"action": "already-armed", "scan_count": state["scan_count"]}` — no `interval_minutes`) with `arm` line 186 (`return {"action": "schedule", "interval_minutes": cooldown_minutes(), ...}`) and `reidle` line 203-204 (always includes `interval_minutes`). The `already-armed` return is the only lifecycle response that omits `interval_minutes` when the agent may still need it.

- **Suggested fix**: Add `"interval_minutes": cooldown_minutes()` to the `already-armed` return dict at line 182, consistent with `reidle`'s behavior.

---

### Finding 4

- **File**: `references/sub-skills/common-events/idle-cooldown-loop.md`
- **Line**: 41
- **Severity**: warning
- **Issue**: The instruction says "Build the `cron` expression from `arm`'s `interval_minutes` (default 30 → `7,37 * * * *`)" but provides only a single example mapping. No general algorithm is given for converting an arbitrary `interval_minutes` value (e.g., 15, 45, 60) into a valid cron expression. An LLM agent given `interval_minutes: 15` has no guidance on whether to produce `7,22,37,52 * * * *`, `*/15 * * * *`, or something else.

- **Evidence**: The `CronCreate` template on lines 32-38 hardcodes `"7,37 * * * *"`. The prose on line 41 says to build from `interval_minutes` but then only gives the 30→`7,37` example. The code supports any positive integer (via `cooldown_minutes()` at line 67-83), so this gap will manifest the moment a non-30 cooldown is configured — even though per-role overrides are "NOT shipped initially" (line 93), the code path is live.

- **Suggested fix**: Either (a) provide a simple algorithm (e.g., "pick two minute-marks `M` and `M + interval_minutes` that avoid :00/:30, e.g. `7, 7+interval_minutes`" — but this breaks for intervals > 30), or (b) switch to a `CronCreate` that fires at a fixed high frequency (e.g., every 5 minutes) and rely entirely on the `tick` throttle gate, removing the need to derive a cron expression from the cooldown value.

---

### Finding 5

- **File**: `references/sub-skills/common-events/idle-cooldown-loop.md`
- **Line**: 30
- **Severity**: warning
- **Issue**: The parenthetical "either `action=schedule`, or `already-armed` after a restart" could be misread by an LLM as a **conjunctive condition** for creating the cron: "only create if CronList is empty AND (action is schedule OR we are after a restart)." Since the agent cannot reliably detect "after a restart," it might skip CronCreate when action is `already-armed` and it doesn't think it restarted — even though the cron is genuinely missing.

- **Evidence**: The parenthetical is structured as an appositive describing the two scenarios where a missing cron occurs, but LLMs can parse appositives as restrictive clauses. The safe formulation is to state the condition first ("If no driver job is listed") and explain why separately, or to simply state "If no driver job is listed, create one — regardless of what `arm` returned."

- **Suggested fix**: Rewrite line 30 to remove the ambiguous parenthetical. For example: `"If no driver job is listed in CronList, create one. (This happens in two cases: `action=schedule` from a fresh arm, or `action=already-armed` after a restart loses the session-scoped cron.)"`

---

### Finding 6

- **File**: `references/sub-skills/common-events/idle-cooldown-loop.md`
- **Line**: 34
- **Severity**: warning
- **Issue**: The `CronCreate` template hardcodes `cron: "7,37 * * * *"` — a 30-minute-interval expression — directly below text saying to build the expression from `interval_minutes`. An LLM agent that pattern-matches the template without reading the surrounding prose may use `7,37 * * * *` for all cooldown values, producing a cron that fires at the wrong cadence.

- **Evidence**: Line 34 shows the literal `"7,37 * * * *"` inside a fenced code block that looks like a copy-paste template. Line 41's instruction to build from `interval_minutes` is separated from the template by the `CronCreate` call itself (lines 33-38) and a paragraph (lines 40-41). LLM agents frequently extract code blocks verbatim.

- **Suggested fix**: Replace the hardcoded expression in the template with a placeholder like `<cron-expression-derived-from-interval_minutes>` and move the construction rule immediately adjacent, or include the expression-building in the same code block as a comment with explicit logic.
---

## Resolution (skill, 2026-06-18)

DeepSeek review (model_router exit 0). Verdict on each:

- **Finding 1 (cancel action ignores `reason: at-cap`)** — FIXED (was the only error-severity finding). Step B's `cancel` handling now splits by `reason`: `at-cap` (driver still armed) runs `subloop_driver.py cancel <alias>` **and** `CronDelete`; `disarmed` just `CronDelete`. Closes the crash-recovery dormancy regression (restart with `armed:true, scan_count>=burst` → tick returns at-cap cancel → without the `cancel` CLI, `armed` stayed true with no cron → permanent idle).
- **Finding 2 (undecidable "first idle since a restart")** — FIXED. Step D `already-armed` now **always** CronList-confirms a live cron (no conditional); the predicate an LLM can't decide is removed.
- **Finding 3 (`arm` already-armed omits `interval_minutes`)** — FIXED (code). `arm()` already-armed return now carries `interval_minutes` (consistent with `reidle`), so a restart-lost cron can be rebuilt without a second call. Test `test_second_arm_is_noop_no_double_schedule` asserts it. 29 driver tests green.
- **Finding 4 (no general interval→cron algorithm)** — FIXED (prose), DS option (a) generalized. Added an explicit construction rule (off-peak offset `s`; divisors of 60 → `s, s+N, …`; else round down to {15,20,30}). DECLINED DS option (b) (fixed high-frequency heartbeat) as a deviation from §8.6.1's "low-frequency self-wake ≈ the cool-down"; kept cron ≈ cool-down with the `tick` throttle gate making exact cadence non-critical.
- **Finding 5 (ambiguous parenthetical, line 30)** — FIXED. Rewrote to "If no driver job is listed in CronList, create one — regardless of what `arm` returned," with the two-case explanation separated out (no restrictive-clause misread).
- **Finding 6 (hardcoded `7,37` template reads as copy-paste)** — FIXED. Template `cron` is now a `<expr>` placeholder with the construction rule immediately below.

Sub-skill (idle-cooldown-loop.md) + driver (subloop_driver.py, +test) re-edited. Driver tests 29 passed.
