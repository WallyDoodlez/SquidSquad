---
name: learning-strip-vs-wire-audit-findings
description: When an audit finding traces to dormant infrastructure with a near-finished consumer, wiring it can be as cheap as stripping it — check both against the architectural intent before defaulting to strip
metadata:
  type: learning
type: learning
tags: [pm-judgment, audit-response, event-bus, architectural-debt, harness]
created: 2026-05-21
updated: 2026-05-21
owner: pm
status: active
confidence: high
source: review
links: [decision-phase-4-event-ack-lifecycle-deferred, learning-broadcast-deque-cannot-have-in-stream-gaps]
---

# When audit-finding plumbing looks dead, check if it's nearly-wired before stripping

## Context

Cycle 1538 audit response to #9741: DeepSeek AUDIT-A flagged that `harness.py:1674-1678` called `event_lifecycle.dispatch()` to mark events as in-flight, but no agent ever sent an ack. Result: `.event-state.json` accumulated in-flight entries forever + timeout-scanner log spam.

The audit body surfaced three options:
1. Document as dormant, accept the noise
2. Add cursor-advance-as-implicit-ack (wire it through)
3. Strip the dispatch() call until ack is wired

PM (me) chose option 3 in CONTEXT-9741 ("simplest"; "dead Phase 4 plumbing with no consumer"). Cycle 1539, skill shipped option 3 + #9813 deleted the symmetric `event_bus.ack()` stub.

## The lesson

The infrastructure to deliver the original architectural intent was nearly complete:
- `dispatch()` worked — marked events in-flight
- `event_bus.ack()` stub existed
- `timeout_scan()` was wired and running
- `POST /events/{id}/complete` was implemented

What was missing was a **single connecting line**: the agent emitting an ack after processing each event (via cursor-advance POST or an explicit complete call). Option 2 was likely smaller than option 3 in terms of net change, AND it would have activated retry-on-no-ack — the original at-least-once delivery semantic.

By choosing option 3, the project lost:
- At-least-once delivery (now best-effort)
- Retry on agent crash mid-processing (now silent loss)
- Harness visibility into "did the agent actually receive this?" (now unknowable from server side)

These now require a future "Phase 4 lifecycle work" — a much larger undertaking than the option 2 wiring would have been, because the working stub got deleted in the strip.

## When this pattern applies

Any audit finding of the form "X is configured/wired but nothing actually drives it; consider stripping X." Before defaulting to strip:

1. **Find the original design intent.** What was X supposed to do? Search planning artifacts, original feature issue body, related vault decisions.
2. **Estimate the wire-it cost.** Often a single missing callsite. Compare honestly against the strip cost (deletion + test inversion + follow-up bug).
3. **Identify what architectural property is preserved vs lost** by each path. If stripping deletes a delivered guarantee (delivery, retry, observability) and wiring restores it, wiring is the conservative choice.
4. **Only strip when** (a) the architectural goal itself has been abandoned, or (b) the wire-it cost exceeds the strip+future-rework cost by a meaningful margin.

## How to apply

PM/skill when triaging audit findings: when the body uses words like "dormant", "unused", "Phase X deferred", or "no consumer", treat that as a flag to investigate the original intent, not as authorization to strip. The audit is reporting a symptom; the right fix may be completing the architecture, not amputating it.

## Changelog

- 2026-05-21 — Created by pm-lead. Lesson from cycle 1538 #9741 / cycle 1539 reflection prompted by human asking "what made the decision to strip it?"
