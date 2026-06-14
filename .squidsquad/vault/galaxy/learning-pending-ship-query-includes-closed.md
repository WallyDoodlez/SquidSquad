---
type: learning
role: dm
created: 2026-06-14
tags: [delivery, tracker, queue-scan, gotcha]
---

# `list-tasks --status pending-ship` includes CLOSED issues

`tracker.py list-tasks dm --status pending-ship` returns issues that still carry the `status:pending-ship` LABEL **even after they were shipped and closed** — the `--status` filter matches on label and does NOT exclude closed issues. On 2026-06-14 this surfaced ~30 "pending-ship" results, all CLOSED (verified via `get-state #605`/`#9965`/`#11511` → CLOSED). The live delivery queue was actually empty.

**Why:** shipping auto-closes the issue but the historical `status:pending-ship` label is not always stripped, so it lingers on closed issues and pollutes the label query.

**How to apply:** Never treat `list-tasks --status pending-ship` output as the live DM queue. To get the ACTIONABLE queue, either:
- run `list-tasks dm` with NO `--status` flag (returns OPEN issues only) and read the `status:*` label per item, or
- `get-state <n>` each candidate and drop any that returns CLOSED.

A genuine pending-ship item is OPEN. The reliable signal that real work arrived is a PM `assigned-to` nudge (target_alias=dm) or an OPEN issue at `status:pending-ship` — not the raw `--status` count.

Related: [[learning-ship-gate-squash-proof-window]].
