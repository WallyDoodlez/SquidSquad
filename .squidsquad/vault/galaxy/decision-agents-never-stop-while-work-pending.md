---
name: decision-agents-never-stop-while-work-pending
description: Operator-locked principle (2026-06-19) — agents always move ahead and NEVER voluntarily stop while work is pending. Any handoff (to another agent OR a human) is a status transition + immediate continue, never a stop. HITL → assign ticket to the human + continue; PM advertises human-assigned tickets to the operator. Generalizes #12799 (human-only no-block) to all handoffs. Tracked by #12853.
metadata:
  type: decision
type: decision
tags: [soul, l1, autonomy, async-no-pause, hitl, pm-interface, lifecycle]
created: 2026-06-19
updated: 2026-06-19
owner: pm
status: active
confidence: high
source: conversation
links: [decision-async-no-pause-never-block-human, learning-stale-activity-not-dead-rule-out-limit-and-inline]
---

# Agents never stop while work is pending — all handoffs are transition-and-continue

## Decision (operator-locked, 2026-06-19, inline)

Agents must **always move ahead and never voluntarily stop while there is pending work.** This generalizes the existing #12799 L1 rule "Never Block on a Human" (which was scoped only to humans) into a universal principle:

1. **Never stop while work is pending** — always pick up the next queue item. An agent never ends its turn/loop to "wait" for another party.
2. **Any handoff is a status transition + immediate continue** — whether the handoff is to another agent (verifier/QA, DM, any) OR to a human. Deferring to QA is `pending-test` + continue, NOT a stop.
3. **HITL** → assign the ticket to the human (`role:<human>` + `pending-human-*` via transition) and continue.
4. **PM advertises human-assigned tickets to the human operator** — the bridge half of the return path. PM proactively surfaces `pending-human-*` items so HITL gets attention.

## Why

The operator hit this live: skill stopped autonomous cycling on a "QA tangent" (deferring to verification) and needed a manual nudge. The #12799 rule only forbade blocking on *humans*, so nothing forbade stopping to defer to another *agent*. The #12506 self-wake driver doesn't recover this — it re-reads the queue from an *idle* state, but a turn that *ended waiting* is not idle. Result: silent stall needing a manual nudge. Autonomy is the whole point of the system; a voluntary stop with pending work is a defect.

## Strengthened 2026-06-19 — Relentless autonomy + inline auto-timeout

Operator strengthened the principle:

- **Default = RELENTLESS.** Agents work nonstop to *attend to* all assigned work; the ONLY thing that pauses an agent is **explicit human engagement (inline mode)**. Nothing else stops it.
- **Inline mode auto-releases after 20 minutes of human silence — HARDCODED, NON-CONFIGURABLE** (explicit operator directive: do not add a config field). Once ≥20 min elapse since the human's last inline message, the **next event the agent detects** resumes autonomous work.
- **Backstop (PM rec):** the #12506 self-wake driver tick counts as a qualifying "event" so a dead-silent 20-min window still resumes (no permanent inline limbo).
- **Outcome intent:** assigned work must be ATTENDED TO (every item looked at within available time/resources), even if not all COMPLETED. Human-decision items → assigned to human + parked; everything else pushed as far as possible. ("Assign a pile before bed → by morning all attended to, not necessarily done.")
- **Reconcile:** AGENT-RUNTIME §3 inline definition + inline status-bar indicator must clear on the 20-min resume. Tracked in **#12853** (expanded spec).

**Locked behavior hierarchy (precedence), operator-confirmed 2026-06-19:**
1. **Pending work** (assigned OR discovered) → work RELENTLESSLY, no rest.
2. **No work** → jump to **self-improvement** (improvement scan).
3. **Self-improvement capped: 3 runs then cooldown** — KEEP the existing improvement-loop design (the burst-of-3 + cooldown is the token-burn guardrail; do NOT make continuous, do NOT remove cooldown).
4. **Inline mode** = the only pause; auto-releases after 20 min human silence → resume.

The cooldown is rest from SCANNING only — never rest from actual pending WORK. 'No rest at all' = never idle-sleeping; always working, self-improving (3x), or briefly cooling down between scan-bursts.

## Boundaries / nuance

- **Idle ≠ stop.** Going idle (event-bus wait / cool-down loop, which auto-resumes on nudge/cooldown) is correct and is NOT a stop. Ending the turn to wait for another party IS a stop and is forbidden.
- **Legitimate session-ends are lifecycle-only:** context-pressure exit-42, stop-requested, Monitor death — all harness-managed, not the agent "choosing to wait."

## How to apply

- **PM (now):** proactively advertise any `pending-human-*` ticket to the operator (don't wait for the human to notice). Adopted immediately ahead of the L2 source change.
- **Implementation:** tracked by **#12853** (role:skill) — generalize L1 `SOUL.md`, add PM L2 advertise duty, recompose, comprehension test + DS-audit. L1/L2 source = compose-consumed = skill domain.
- When diagnosing a stalled agent: distinguish "idle (auto-resumes)" from "ended-turn-waiting (needs nudge — a defect under this rule)".

## Changelog

- 2026-06-19 — Locked by operator (inline). Filed #12853 (impl) + #12854 (stale current-state hygiene that masked this incident).