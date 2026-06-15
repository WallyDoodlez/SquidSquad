---
name: learning-stall-vs-deepwork-before-nudging
description: A long silent in-progress is a STALL only if progress signals are flat — verify liveness+progress (CPU growth, live child procs, commits) before firing a 90-min sentinel nudge; nudging an actively-working agent is counterproductive noise
metadata:
  type: learning
type: learning
tags: [pm-judgment, pipeline-sentinel, liveness, event-mode]
created: 2026-06-15
updated: 2026-06-15
owner: pm
status: active
confidence: high
source: review
links: [feedback_manual_agents, feedback_trust_script_output, learning-audit-scope-and-source-of-truth]
---

# Distinguish deep-work from a stall before nudging

## Context

2026-06-15. skill picked up #10855 (a deep, historically-hard "verifier inert boot" bug, post-verifier-FAIL) and went ~1.5h `in-progress` with **no interim comment or transition**. By the literal 90-min pipeline-sentinel rule, that looks like a stall warranting a nudge — and silence on a known-hard bug raised the churn suspicion (cf. the #11511 multi-hour churn earlier the same session).

Before nudging I checked the actual process: `claude.exe` CPU had climbed +122s since the prior check, and 2 live child processes were running in the clone. → genuine deep work, **not** a stall. I did not nudge. (Nudging an actively-working event-mode agent is just noise it processes after its current action — pure distraction.)

## The lesson

"Silent `in-progress` past 90 min" is necessary but **not sufficient** for a stall nudge. A stall is *no progress*, not *no chatter*. Deep work on a hard task is legitimately silent. Verify progress signals first:

- **CPU growth** of the agent's `claude.exe` between checks (`UserModeTime`) — climbing = working.
- **Live child processes** in the agent's clone (tool subprocesses: pwsh/python/node) — present = mid-tool-call right now.
- **New commits** on its branch, or a fresh transcript.

Only if ALL are flat (no CPU growth, no children, no commits) over the window is it a real stall → then nudge / investigate / consider restart. This mirrors the project's own move *away* from PID-existence liveness toward progress-based liveness (#12271): "process exists" ≠ "agent is working," and inversely "no comment" ≠ "no progress."

## How to apply

PM pipeline-sentinel, before any stall nudge on a long-`in-progress` item:

1. Check the agent's `claude.exe` CPU delta + live child procs (+ branch commits) — cheap, deterministic.
2. **Progressing → do nothing** (don't nudge; note the watch). Re-check next cycle.
3. **Flat across the window → real stall** → nudge (route comment), then escalate (re-nudge / restart) if still flat.
4. Separate "is it progressing?" (liveness) from "is it the right priority?" (a long grind on a self-selected hard bug while operator-prioritized work waits is a *priority* conversation, not a stall — handle it as routing/priority, not a stall nudge).

## Changelog

- 2026-06-15 — Created by pm-lead. From the #10855 deep-work-vs-stall judgment during the #12271 liveness build-out.
