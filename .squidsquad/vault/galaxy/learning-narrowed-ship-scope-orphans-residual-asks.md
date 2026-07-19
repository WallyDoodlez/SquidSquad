---
type: learning
title: When shipped scope is narrower than the original observation, residual asks orphan in comments
created: 2026-07-19
roles: [pm, dm, verifier]
tags: [handoff, hitl, scope, ship-gate, pm]
updated: 2026-07-19
owner: pm
status: active
confidence: high
source: incident
---

# learning-narrowed-ship-scope-orphans-residual-asks

**Type:** learning (PM coordination)
**Coined:** 2026-07-19 (#13793 → #13807 recovery)

## What happened

#13793 was filed on an observation (two unexplained stray sibling directories) but the shipped fix legitimately narrowed to a different atomic unit (wizard.py auto-cleanup of *future* failed clones). The residual piece of the original observation — operator deletion of the two *existing* directories — was correctly judged a human action, but the handoff lived only as a mid-thread comment. When the issue shipped and auto-closed, that ask was orphaned: comments on closed issues reach no one, and no `pending-human-*` ticket existed. PM caught it post-ship and recovered it as #13807 (parked `pending-human-setup` via the legal `open → in-progress → pending-human-setup` path).

## The learning

When an issue ships with scope **narrower** than its original observation, the delta doesn't disappear — it must land somewhere tracked before (or at) close. A comment is not a handoff (see `comment-handling`'s transition-on-handoff rule); this is the inverse of [[pattern-ship-gate-preserve-expanded-scope]] (which covers scope *expansion*).

## How to apply

- **DM at ship / verifier at PASS**: before closing, diff the shipped scope against the issue's original observation; any residual ask (especially human-action ones) gets its own ticket, transitioned to the right `pending-human-*` or role queue.
- **PM on ship events**: when a shipped item's history contains "left to the operator/human" phrasing, verify a tracked ticket exists; if not, file and park one (the #13807 recovery pattern).
- Route into `pending-human-*` from `open` via the assignee self-pause path: `open → in-progress → pending-human-setup` (direct `open → pending-human-*` is illegal, and `--force` is operator-only).
