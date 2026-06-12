---
name: pattern-stale-ac-vs-canonical-arch
description: When a task's acceptance criteria contradict the canonical architecture doc (because the AC predates a later arch refinement), surface the specific fork to the operator with a recommendation, build to the canonical arch, and reframe the ACs via a tracker comment for the AC owner
metadata:
  type: pattern
type: pattern
tags: [pattern, planning, architecture, acceptance-criteria, role-boundary, self-hosting]
created: 2026-06-11
updated: 2026-06-11
owner: skill
status: active
confidence: high
source: observation
links: [feedback-no-deferred-wiring, pattern-parallel-axis-audit]
---

## Context

In a self-hosting system, architecture docs (TRDs) and task acceptance criteria drift apart: a task is scoped at time T against the arch-as-of-T, then the arch is refined at T+1 by a later task, but the original task's ACs are never re-written. When the original task is finally picked up at T+2, its ACs literally contradict the now-canonical arch doc.

Concrete instance (#11329, 2026-06-11): the task ACs (written 2026-06-07) said `event_poll.py` should own the cursor and POST `ack-cursor` itself (AC1 "swap the file-write for a POST"; AC4 `test_event_poll_acks_per_event_via_harness`). But the canonical model the polish session produced (post-#11328 D2: AGENT-RUNTIME §8.0/§8.1, `cursor-management.md`, the L1 per-nudge diagram) said the **opposite** — `event_poll` emits a bare `NUDGE` with no payload, and the **agent** does `GET /events/for` + per-event `ack-cursor`. Building the literal AC would have re-created the exact doc-vs-runtime drift the task existed to eliminate.

## Pattern

When a picked-up task's ACs contradict the canonical arch doc:

1. **Don't silently follow either side.** Following the AC literally ships against a superseded model; silently following the arch doc deviates from an approved spec without the AC owner knowing. Both are wrong.

2. **Find the decisive technical tie-breaker, not just "which doc is newer."** In #11329 it was the at-least-once guarantee: if `event_poll` acks at emit-time (AC-literal), the cursor advances before the agent tends the event, so a crash in between silently loses it — only the agent-acks model preserves crash-recovery. A correctness argument settles the fork more durably than doc-recency.

3. **Surface the specific fork to the operator with a recommendation** (AskUserQuestion or a Discussion comment), framed as: "AC says X; canonical arch says Y; they're incompatible because Z; I recommend Y because <correctness reason>." Don't ask "what should I do" — present the resolved analysis and let them ratify.

4. **Build to the canonical arch** once ratified.

5. **Reframe the ACs via a tracker comment addressed to the AC owner (PM).** AC ownership is a role boundary — the worker doesn't own the AC text. Post a comment that (a) names the contradiction, (b) records the operator ratification, (c) lists the specific AC reframes (e.g. "AC4's `test_event_poll_acks_per_event_via_harness` is wrong for the chosen model — replaced by `test_event_poll_emits_nudge_not_json`"). This keeps the forge record honest for the verifier, who derives the test plan from the ACs independently.

## Why this works

- **Correctness tie-breaker > recency.** Doc timestamps tell you which was written later, not which is right. A crash-safety / invariant argument is reviewable and survives further drift.
- **Operator ratification before code** converts a unilateral worker deviation into an approved decision — cheap insurance for a high-blast-radius change.
- **Reframing ACs on the forge, not silently** respects the PM/worker/verifier seam: the verifier builds the test plan from ACs, so stale ACs left unflagged produce a bogus verification.

## When NOT to use

- The "contradiction" is a surface wording mismatch, not a behavioral fork — just build the obvious intent.
- The AC and arch agree and only an implementation detail is open — that's normal engineering judgment, no operator fork needed.
- The arch doc itself is the thing being changed by this task — then the AC *is* canonical; don't defer to a doc you're rewriting.

## Changelog

- 2026-06-11 — Authored by skill agent from #11329 (the model-A→model-B `ack-cursor` migration), where the 2026-06-07 ACs contradicted the post-#11328-D2 canonical agent-acks model. Operator ratified the canonical model; ACs reframed in a #11329 Discussion comment.
