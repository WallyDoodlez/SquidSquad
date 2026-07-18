---
type: learning
tags: [verifier, tracker, transitions, boot-sequence, role-authority]
created: 2026-07-18
updated: 2026-07-18
owner: verifier
status: active
confidence: high
source: observation
links: []
---

## Content

The generic `event-mode-contract.md` boot-sequence Case-2 branch ("Idle / nothing
in progress → run `work_queue()`... pick up the top item — transition it to
`status:in-progress`") is written for the general case and is **wrong for QA
specifically** when the picked-up item is a `status:pending-test` issue.

`tracker.py`'s `ROLE_AUTHORITY` table has **no `(status:in-progress, X)` entry
for `qa`/`verifier` at all** — QA's only authorized transitions are
`(pending-test → in-progress)` and `(pending-test → pending-ship)` (plus the
PR-Flow `pending-human-review` variants). Once QA follows the generic boot
instruction and moves a picked-up item to `status:in-progress`, QA has **no
legal path forward**: `in-progress → pending-ship` is DM-only (the `#6261`
DM-skips-QA carve-out), and `in-progress → pending-test` is assignee-only
(the worker role, not QA). The ticket deadlocks at `in-progress` with QA
holding a completed PASS verdict and no button to press — the only unblock is
pinging DM via `work-assign` to run the DM-authorized `in-progress →
pending-ship` transition on QA's behalf (a workaround, not a clean path).

Confirmed live 2026-07-18 on #13556: boot picked up the item per the generic
Case-2 instruction, transitioned to `in-progress`, completed the full
re-verification (PASS), then `tracker.py transition 13556 in-progress
pending-ship --role verifier-lead` was rejected with "role 'qa' is not
authorized... (allowed: ['dm'])".

## How to apply

**QA must never transition a `status:pending-test` item to `status:in-progress`
at pickup.** Stay at `pending-test` while doing the verification work (there is
no forge-visible "I'm working this" state QA needs beyond the `working-state.md`
Task field + `current-state` marker — those are agent-private/diagnostic, not
forge state). At the END of verification, transition directly:
- **PASS** → `pending-test → pending-ship` (qa-authorized).
- **FAIL** → `pending-test → in-progress` (qa-authorized — this is the ONE
  correct use of the in-progress target, and it's a terminal move for QA: the
  assignee owns it from there, not QA).

If a fresh QA session boots and picks up a `pending-test` item, the boot
sequence's generic pickup step should be read as "pick up the item (note it
in working-state), begin verification" — **skip the transition-to-in-progress
sub-step entirely** for this specific item type. This is a correction to how
the generic `event-mode-contract.md` Case-2 instruction should be interpreted
by QA, not a change to the shared fragment itself (which is correct for
worker/PM pickup flows where `pending-test`/`approved`/`open` items really do
need an in-progress marker before work starts).
