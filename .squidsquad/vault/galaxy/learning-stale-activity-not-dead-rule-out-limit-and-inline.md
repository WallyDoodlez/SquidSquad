---
name: learning-stale-activity-not-dead-rule-out-limit-and-inline
description: An agent with stale harness-activity (alive pid, no last_activity updates, bootup never completes) is NOT necessarily dead/inert/wedged. Rule out (a) inline human conversation, (b) account usage-limit freeze, (c) genuine wedge — IN THAT ORDER — before concluding. Multiple agents freezing at once points to a shared cause (limit), not coincident per-agent bugs. Ask the operator: they have usage-limit ground truth PM lacks.
metadata:
  type: learning
type: learning
tags: [pm-judgment, health-check, facts-over-context, lifecycle, usage-limit, inline-mode, misdiagnosis]
created: 2026-06-18
updated: 2026-06-18
owner: pm
status: active
confidence: high
source: observation
links: [feedback_health_checks_facts_not_context, feedback_minimal_repro_over_symptom_match, learning-graceful-restart-grace-timer-on-wedged-agent, feedback_manual_agents]
---

# Stale harness-activity ≠ dead agent — rule out usage-limit and inline-conversation first

## Context

2026-06-18, fresh-reboot session. Two agents looked "dead" to me on harness `/status`: **qa** (alive pid, zero activity, bootup never completed) and **skill** (alive pid, zero activity 76 min, `current-state=running full suite`). I diagnosed them as two independent bugs — qa as the inert-boot bug (#10855/#12409), skill as a hung test-suite wedge (filed #12847 HIGH). **Both were WRONG.** The operator corrected: the real cause was a single **account usage limit** that froze the agents mid-API-call. qa additionally showed no activity because the **operator was talking to it inline** (inline mode → mechanical wrappers don't fire → no harness activity updates, by design — see my own CLAUDE.md "Human interruption" note).

I'd violated [[feedback_minimal_repro_over_symptom_match]]: `current-state=running full suite` *fit* a hung-suite hypothesis, but I never confirmed an actually-hung subprocess (no ~76-min-old pytest child was ever observed — evidence I noted then under-weighted). Symptom-fit, not proof. I also missed the Occam signal: **two agents freezing in the same window is a shared cause, not coincident bugs.**

## The lesson

When an agent shows stale harness-activity (alive pid, `last_activity_at` not advancing, `bootup_complete=False`), do NOT jump to "inert/wedged/dead." Rule out, in order:

1. **Inline human conversation** — operator talking to the agent in its terminal. Inline mode fires no cycle wrappers, so harness activity looks frozen while the agent is fully alive and responsive. (Cheapest to check: ask the operator "are you talking to it?")
2. **Account usage-limit freeze** — a limit freezes the session mid-call: alive process, no tool activity, no progress. **Account-wide → hits MULTIPLE agents at once.** If ≥2 agents froze in the same window, suspect this first. The operator has the usage/limit ground truth; PM does not — ASK.
3. **Genuine wedge / inert-boot** — only after (1) and (2) are excluded.

Corollary: a session frozen on a usage limit does **not** auto-recover when the limit clears — it needs a restart to get a fresh session.

## How to apply

- Before filing a bug or restarting an agent for "looking dead": cross-check ≥2 sources (telemetry + git/commits + clone files) AND ask the operator whether they're interacting with it or whether a limit was hit.
- If multiple agents look frozen simultaneously → default hypothesis is a shared/account cause (limit, harness), NOT N independent agent bugs.
- Do NOT pre-emptively restart an agent the operator may be mid-conversation with — confirm first. (This session I killed qa's session out from under an operator inline chat.)
- Recovery for a limit-frozen agent after the limit clears: restart (DEAD pid-None → boot_remote; FROZEN-alive → harness restart grace timer, finish with boot_remote if it leaves pid None — see [[learning-graceful-restart-grace-timer-on-wedged-agent]]).

## Changelog

- 2026-06-18 — Created by pm-lead after misdiagnosing a usage-limit freeze as skill hung-suite (#12847, retracted/closed) + qa inert-boot. Operator supplied the correcting ground truth.