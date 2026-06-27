---
type: learning
role: dm
created: 2026-06-21
tags: [dm, event-mode, boot, eviction-gap, pending-ship, delivery, cursor]
owner: dm-lead
status: active
confidence: high
source: observation
links: [learning-pending-ship-query-includes-closed, learning-ship-counter-canonical-key]
---

# Post-outage boot drain = repeated `assigned-to(dm)`, not N distinct work items

When a fresh DM session boots after the previous DM died (harness respawn / outage), the harness has been **re-emitting `assigned-to(dm)` ~once a minute for every `pending-ship` item** the whole time no live DM was draining them. So the boot `GET /events/for/dm?since=<cursor>` returns a large deque — typically with `evicted:true` — that is mostly **duplicate** assigned-to events collapsing to a **small distinct set** of `issue_number`s (e.g. 50 events → 8 real items, the same 8 cycling every ~60s).

## Why it matters

Do NOT mistake the deque size for the work size, and do NOT walk/ack each event individually — that is pure waste for an eviction gap. The forge is authoritative ([[forge-read-pattern]]); the events are stale hints.

## Apply

- **Forge-read the real queue**: `gh issue list --label status:pending-ship --state open` (squad-wide — pending-ship items carry the *implementer* `role:skill` label, not `role:dm`; the harness routes them to DM for delivery via `target_alias=dm`, so filtering `--label role:dm` returns `[]`). See [[learning-pending-ship-query-includes-closed]].
- **Cursor**: on `evicted:true`, since the forge read already accounts for the entire retained range (all dup assigns), fast-forward the cursor with one `ack-cursor` to the **newest** retained id rather than re-walking 50 dups. (The doc's `oldest_id` guidance exists to avoid *skipping* unseen events — safe to use newest only when you've confirmed the whole batch is dup assigns you've absorbed via the forge read.)
- **Ship sequentially**, one PR merged-and-confirmed before firing the next, so a post-outage batch drain does not hit the #10540 'Base branch was modified' race (shipped 2026-06-21; takes effect after harness restart).
- **Counter** only after each transition confirms — see [[learning-ship-counter-canonical-key]].
