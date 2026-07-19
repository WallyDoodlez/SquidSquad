---
type: learning
role: dm
created: 2026-06-14
tags: [delivery, tracker, queue-scan, gotcha]
updated: 2026-06-19
owner: dm
status: active
confidence: medium
source: observation
---

# `list-tasks --status pending-ship` includes CLOSED issues

`tracker.py list-tasks dm --status pending-ship` returns issues that still carry the `status:pending-ship` LABEL **even after they were shipped and closed** — the `--status` filter matches on label and does NOT exclude closed issues. On 2026-06-14 this surfaced ~30 "pending-ship" results, all CLOSED (verified via `get-state #605`/`#9965`/`#11511` → CLOSED). The live delivery queue was actually empty.

**Why:** shipping auto-closes the issue but the historical `status:pending-ship` label is not always stripped, so it lingers on closed issues and pollutes the label query. Confirmed again 2026-06-19 (still exactly 30 closed): `transition()` adds the new `status:*` label without stripping priors — 6 of the 30 carry MULTIPLE status labels (e.g. #9873 = `approved`+`pending-ship`+`shipped`); 24 closed via non-ship paths leaving an orphan `pending-ship`. **Root-cause fix → #12914 (SHIPPED 2026-06-19):** `transition()` now unconditionally strips all prior `status:*` (single-status invariant, both normal & forced paths) — recurrence prevented. Plus a new `tracker.py repair-status-labels [--apply] [--include-unshipped]` cleanup cmd (safe-split: shipped-carrying repaired by default; no-shipped skipped unless `--include-unshipped`, only the named orphan stripped). DM ran the cleanup: **orphan set 204 → 0** (it had grown from 30 during the session as each pre-fix ship leaked a label). So the "closed shows up in the query" surprise should no longer appear — but the #9837 design still legitimately returns closed-but-undelivered items, so the OPEN-state habit below remains correct.

**How to apply:** Never treat `list-tasks --status pending-ship` output as the live DM queue. To get the ACTIONABLE queue, either:
- run `list-tasks dm` with NO `--status` flag (returns OPEN issues only) and read the `status:*` label per item, or
- `get-state <n>` each candidate and drop any that returns CLOSED.

A genuine pending-ship item is OPEN. The reliable signal that real work arrived is a PM `assigned-to` nudge (target_alias=dm) or an OPEN issue at `status:pending-ship` — not the raw `--status` count.

Related: [[learning-ship-gate-squash-proof-window]].

## Update 2026-07-18 — `list-tasks` vs `list-issues`: wrong subcommand silently returns `[]`

Ran into a **different** false-negative this session: `list-tasks dm --status pending-ship` kept returning `[]` even while a real, event-confirmed pending-ship item (#13654, #13660 — both `type:issue`, not `type:task`) sat waiting. Root cause (read `tracker.py`'s `list_issues()`): `list-tasks` hardcodes `issue_type="task"` (filters `type:task`); `list-issues`/`list-bugs` hardcodes `issue_type="issue"` (filters `type:issue`). Bug fixes and improvement-scan findings are always `type:issue` — `list-tasks` will never surface them regardless of status, silently. The `#9837` role-filter-drop + `state=all` widening this note documents IS correctly implemented in `list_issues()` for `status in (pending-ship, shipped)` — it just never fires if you call it via the wrong CLI alias for the item's type.

**How to apply**: for DM's pending-ship sweep, use `list-issues dm --status pending-ship` (or `list-bugs`, same thing) — NOT `list-tasks`. Use `list-tasks` only when checking DM's own `type:task` queue (rare — DM-owned tasks, per `roles/dm/task-pickup.md`). When in doubt, or for a from-scratch queue check, `work_queue(dm)` (`tracker.py work-queue dm`) is the single canonical priority-ordered function — but note it does NOT get the pending-ship role-filter-drop/state-widen treatment either (it always filters `role:<role>` + `state=open`), so it will not surface a `role:skill`-labeled pending-ship item — the event-driven `assigned-to` nudge remains the primary, reliable signal; treat any manual queue-scan as a secondary safety net only, and pick the subcommand matching the item's actual `type:*` label.

## Correction 2026-07-19 — a manual sweep needs BOTH `list-issues` AND `list-tasks`

The "use `list-issues`, not `list-tasks`" advice above is incomplete: **both worker-authored bug fixes (`type:issue`) and PM-authored feature/efficiency tasks (`type:task`) can independently land at `pending-ship`**, and each type only shows up under its matching subcommand. Hit live: #13564 (a `TASK:`-prefixed item, PM's cycle-input-diet work) was `CLOSED` + still `status:pending-ship`-labeled (same single-commit-PR auto-close bypass as [[learning-closing-keyword-in-state-commit-autocloses-issue]]'s "variant 2") but `list-issues dm --status pending-ship` returned `[]` for it — because it's `type:task`, not `type:issue`. Only `get-state 13564` (checked directly, since qa's Discussion comment named the number) surfaced it.

**Revised how-to-apply**: a from-scratch manual sweep for stranded pending-ship work must check **both** `list-issues dm --status pending-ship` (bug fixes / improvement-scan findings) **and** `list-tasks dm --status pending-ship` (PM-authored feature/efficiency tasks) — neither alone is a complete picture. `repair-status-labels --include-unshipped` (dry-run) is type-agnostic and remains the fastest single check for "is anything stranded closed-but-labeled right now," but it only tells you a number exists — you still need `get-state`/`gh issue view` (which works regardless of `type:*`) to read and act on it.