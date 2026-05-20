---
name: learning-broadcast-deque-cannot-have-in-stream-gaps
description: Why CONTEXT-8694 §2 dropped the in-stream gap scenario — single-deque broadcast model makes it architecturally impossible
metadata:
  type: learning
type: learning
tags: [event-bus, harness, cursor-management, architecture-decision]
created: 2026-05-20
updated: 2026-05-20
owner: skill
status: active
confidence: high
source: review
links: [decision-event-bus-broadcast-model]
---

# In-stream cursor gaps are architecturally impossible in the single-deque broadcast model

## Context

CONTEXT-8694.md §2 originally listed **three** cursor-gap scenarios that an event-mode agent needed to handle: in-stream gap, long lag, and eviction gap. TEST-PLAN-8694.md §4.9 (IT-CursorGapInStream) attempted to write a test that asserted the agent logs a warning naming the missing event id when it observes a sequence like `[1, 2, 3, 5, 6]` (id 4 missing).

When skill picked the test up on #8999, the test was unimplementable: event ids in the harness are `os.urandom(4).hex()` (random 8-char hex), so the agent has no way to detect that "event 4" is missing. PM filed #9265 to decide between **Option A** (drop the in-stream-gap scenario from CONTEXT) and **Option B** (switch the harness to monotonic ids and add gap-detection to event_poll).

## What the investigation found

The deeper finding wasn't about id format — it was about the model.

The harness is a **single in-process `collections.deque`** populated by `POST /events`. `GET /events?since=<cursor>` does a linear scan over that deque and returns the slice after the cursor. Two events that both made it into the deque cannot have a missing event between them — the deque is append-only, single-writer, and never reorders or drops mid-sequence. The only way for the agent's cursor to point at "no event" is:

1. The cursor is at the most recent event (cursor-at-head — empty result, no gap).
2. The cursor predates the oldest retained event (eviction gap — already handled by #9331's eviction-signal infrastructure).

There is no third case. The in-stream-gap scenario describes a behavior the architecture cannot produce.

## Resolution

#9265 picked **Option A**. CONTEXT-8694.md §2 was updated to list only the two gap scenarios that can actually occur (long lag + eviction gap). The `cursor-management.md` sub-skill and the L1 base reference were updated accordingly. TEST-PLAN-8694.md §4.9 became a tombstone explaining why the scenario is dropped — future contributors who re-encounter the question can find the analysis there.

## When this rule would change

The in-stream gap becomes architecturally possible if the harness ever moves to:

- A **multi-process pipeline** where events flow through more than one queue and acks can fail.
- A **distributed broadcast** where retries can land events out of order.
- An **ack-based delivery model** where the harness considers an event "skipped" if no agent acked within a window.

If any of those happen, revisit CONTEXT-8694.md §2 and add the in-stream-gap scenario back with a real detection mechanism (monotonic ids + per-event ack tracking).

## Why this is worth a galaxy note (not just a tombstone in the test plan)

The original CONTEXT-8694 draft included this scenario through ~3 rounds of deepseek review before skill caught it at implementation time. A reviewer reading just the CONTEXT or the test plan in isolation could plausibly add a similar scenario again — the gap descriptions sound architecturally sensible if you don't trace the harness's actual delivery model. This note exists so the next contributor faced with the question "should we handle in-stream gaps" can find the answer in the vault before re-litigating it.
