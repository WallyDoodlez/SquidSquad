**Reported By**: pm-lead
**Severity**: High

## Observed (operator-flagged 2026-06-16)
No agent is running the improvement subloop. The proactive idle→scan→file-improvement layer is silently dormant across the whole team.

**Evidence — last recorded scan per role (`.squidsquad/<role>/scan-history.md`), today is 2026-06-16:**
- pm: 2026-06-03 (~13 days ago)
- skill: 2026-06-01 (~15 days ago)
- qa: 2026-05-23 (~24 days ago)
- dm: 2026-04-05 (~2 months ago)

Agents have had idle windows in that span (e.g. between cutover increments), so this is not merely 'everyone was busy.' The layer is not firing and nothing surfaced its absence.

## Impact
- The entire proactive process-improvement layer (idle-cooldown → improvement scan → file findings) is inert. Idle time is not converted to improvement; drift/gaps that scans would catch go uncaught.
- **Silent failure**: a core designed behavior has been off for weeks with no signal. (This bug itself was found by a human noticing, not by any self-check — which is the failure mode.)

## Leads for RCA (not prescribing the fix — observed surfaces only)
1. **Event-mode idle-wake gap (primary suspect):** `event_poll.py` emits a NUDGE only when real forge events arrive past the cursor — never on idle ticks. But `idle-cooldown-loop` step 5 assumes the Monitor delivers periodic wakes so the agent can re-check `Next scan after` and fire when the cooldown elapses. If an event-mode agent is genuinely idle (no forge events), it appears to never wake to evaluate the cooldown → the scan never fires. This would explain pm/skill/dm (all event-mode).
2. **dm is explicitly GATED:** dm working-state shows its scan blocked by the doc-improvement-loop issue-gate tripping on open #10540 (parked on PM routing). Separate contributing cause — PM is routing #10540.
3. **qa (loop mode)** scan-history is also stale (since 05-23) despite loop ticks — worth confirming whether the loop-mode path (step:cycle/cleanup → improvement-scan-slim) is actually reached.

## Suggested AC direction (for planning, not locking)
- An idle event-mode agent reliably fires its improvement scan when the cooldown elapses, WITHOUT depending on an unrelated forge event to wake it.
- A self-check / signal exists so a dormant subloop is detectable without a human noticing.

Refs: idle-cooldown-loop sub-skill, event_poll.py, #10540 (dm gate), AGENT-RUNTIME §8.6 (improvement subloop cursor-at-head).

---

# IMPLEMENTATION PLAN (PM Planning output — 2026-06-16)

**Design is LOCKED in AGENT-RUNTIME §8.6.1** (PR #12518, DS-audit-converged). Do NOT re-derive design — conform to §8.6.1. Research/Discussion phases are closed (design + DS audit done). This is the buildable spec.

## Gating & sequencing
- **Gated on §8.6.1 (PR #12518) merging first** — the arch is the contract.
- **Ship the 3 artifacts ATOMICALLY** (per DS-audit Q1): scheduling code + config.md + sub-skill edits land together, or the §8.6.1 "knowingly-inconsistent" breadcrumb breaks.
- No-harness-change constraint (§8.6.1): agent-side scheduling only. **If you find a harness change is required, STOP and route back to PM** — it contradicts the audited arch.

## Scope (4 units)
1. **Driver scheduling** — at first idle/drained, schedule a low-frequency cron/`/loop` self-wake; cancel at the burst cap; re-arm on re-idle. Skill picks the exact primitive (`/loop` skill / ScheduleWakeup / CronCreate) and the schedule/cancel call sites (likely in `idle-cooldown-loop` idle-entry + the §8.6 drained branch).
2. **config.md** (`## Improvement Scanning`): add `- **Idle Scan Burst**: 3`; change `Improvement Scan Cool-Down: 30` → `30m`.
3. **idle-cooldown-loop.md** — rewrite step 5 AND the surrounding "After each empty poll interval" block to the driver-tick re-entry model (not Monitor-cadence); document `Idle Scan Burst` in "Cool-Down Configuration".
4. **Tests** (unit + comprehension).

## Acceptance Criteria (testable)
- **AC1 Lazy enable**: a continuously-busy event-mode agent never schedules a driver; an agent that reaches idle/drained schedules exactly one. Deterministic test.
- **AC2 Idle scan fires (the fix)**: an idle event-mode agent with ZERO forge events runs an improvement scan within ~1 cool-down window — the #12506 dormancy is gone. Test: simulate idle + advance time → scan fires.
- **AC3 Bounded**: after `Idle Scan Burst` (3) scans in one sustained-idle period the driver is cancelled; no further idle scans until re-activity. Test the lifecycle (arm → scan×3 → cancel).
- **AC4 Re-arm**: after cancel, processing forge work then re-idling re-arms the driver and resets scan_count. Test.
- **AC5 Monitor coexistence**: both Monitor (forge-event NUDGE) and a driver tick reach the §8.1 loop; a driver tick mid-task is absorbed by the next forge-read — no double-processing, no lost work. Test.
- **AC6 Config consumption**: agent reads `Idle Scan Burst` from config.md (default 3 if absent — graceful per audit); cadence reads `Improvement Scan Cool-Down: 30m`.
- **AC7 Sub-skill reconcile**: `idle-cooldown-loop.md` no longer claims Monitor delivers fixed-cadence wakes; names the §8.6.1 periodic driver as the cadence source; KEEPS the NUDGE-arrives branch + cool-down eligibility check; documents `Idle Scan Burst`.
- **AC8 No harness change**: `harness.py` untouched (per §8.6.1).
- **AC9 Composes**: sub-skill edits reach the deployed event-mode agents' composed CLAUDE.md via `compose.py deploy-all` — verify the driver instruction is present in composed output, not just source.
- **AC10 Comprehension test** (REQUIRED — instruction change): a fresh event-mode agent quizzed "you're idle with no forge events — how/when does your next improvement scan fire?" answers "a periodic self-wake driver scheduled at first idle re-enters the loop on a timer," NOT "the Monitor wakes me on a cadence."
- **AC11 installer-files.txt** updated iff a new file is added (likely none — in-place edits).
- **AC12 DS-review per change** — the wake loop is high-blast-radius; DS-review each change per project discipline.

## Handoff
On §8.6.1 (PR #12518) merge → reassign #12506 role:pm → role:skill → skill builds against §8.6.1 + these ACs → pending-test → verifier derives TEST-PLAN from the ACs.
