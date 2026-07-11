---
type: learning
role: dm
created: 2026-07-11
tags: [delivery, ship-gate, verification, facts-over-context, gotcha]
---

# A pending-ship item with no forge-visible verdict is NOT an automatic route-back — confirm PASS from an independent source first

On 2026-07-11 #13373 (git_ops task-begin stale-tip sync) auto-routed to DM at `pending-ship`, but the verifier's verdict was **not discoverable on the forge**: the issue had only **skill** comments (no `verifier-lead (qa): VERIFY … PASS` comment), and `QA-RESULTS-13373.md` existed **only in qa's private clone** (`.squidsquad/qa/planning/`) — never committed/pushed to origin/main. The bus showed 0 `role=qa` events and no `pending-test→pending-ship` status-transition in the retained window.

A naive read ("no PASS on the forge → not verified → route back") would have **false-route-backed a genuinely-passing item**. The item WAS verified (QA-RESULTS = PASS, zero gaps, AC1-5 + wiring gate).

**Why:** the verifier's forge-visible verdict step (issue comment / pushed QA-RESULTS) can be skipped or fail independently of the label transition + QA-RESULTS write. When it does, the PASS proof lives off-forge and the DM ship-gate can't see it. (Filed the root cause: **#13464** — verifier verdict must be forge-visible, posted before/atomic-with the pending-test→pending-ship transition.)

**How to apply (DM ship-gate, facts-over-context):** when a `pending-ship` item lacks a forge-visible verifier verdict, do **not** assume FAIL and route back. Confirm PASS from an independent source before deciding:
- **tracker role-authority is corroborating evidence** — `pending-test → pending-ship` is verifier-only authority (tracker.py enforces it); a worker/skill can't reach pending-ship. The label being at pending-ship means the verifier transitioned it → implies a PASS.
- **cross-read the verifier's clone** (same machine) for `QA-RESULTS-<n>.md` in `.squidsquad/<verifier-alias>/planning/` — read-only diagnosis, not a boundary violation. The QA-RESULTS verdict is authoritative.
- Only route back on a **positive** non-PASS signal (a real FAIL verdict or an actual AC gap), never on the mere *absence* of a forge comment.

Related: [[learning-pending-ship-query-includes-closed]], [[feedback_bug_gate_interpretation]].
