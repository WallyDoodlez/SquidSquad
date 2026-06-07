# QA-RESULTS-11328 — Doc-codify eager event-loop + per-event ack-cursor (PM-owned)

**Verified at**: 2026-06-07 cycle 1032
**PR**: #11332 against `squidsquad/skill/compose-polish-session` (not main — bundles with #11144 polish session)
**Branch HEAD**: `dfd64d3e3` (AC1.4 commit)
**Files**: `docs/AGENT-RUNTIME.md` (+98/-80) + 11 DS-audit artifacts under `.squidsquad/pm/planning/`

## AC walk

- **AC1.1 — D1: cursor = canonical work-completed indicator** — PASS
  - §4.1 principle 1 refined: "the harness DOES own the per-alias **event-tending cursor** in `.event-state.json` — the cursor is the work-completed indicator at event-delivery granularity, not forge-level workflow tracking" (line 254).
  - §4.1 principle 4 refined: "`ack-cursor` fires after the agent has finished processing an event (cared or skipped) — i.e., it carries *event-completion* semantics; the cursor advance IS the completion signal" (line 257).
- **AC1.2 — D2: eager per-event loop rewrites §7.1** — PASS
  - §7.1 pseudocode (lines 791-805) is the eager `loop forever:` form: per-event `ack-cursor` inside the loop, drain-to-empty outer loop, improvement subloop as a branch. Replaces the pre-D2 for-then-batched-ack pattern.
  - "Three things to notice compared to the pre-D2 batched walk" block (lines 809-813) calls out the three differences explicitly.
- **AC1.3 — D3: §7.5 mid-cycle nudge simplifies to no-action** — PASS
  - §7.5 (line 1044): "If a nudge arrives while the agent is mid-cycle: **note it in conversation context only. No file write, no queue, no flag. Take no other action.**"
  - Old "Emit ack-cursor for current event" instruction removed. Crash-safety table (lines 1054-1058) grounded in per-event ack mechanics.
- **AC1.4 — D4: ack-cursor vs ack-stop catalog clarification** — PASS
  - §4.2 signal catalog (lines 265-274): `ack-cursor` row "Agent has finished processing this event (cared or skipped); cursor advances" + `ack-stop` row "Agent has accepted a stop intent and is checkpointing".
  - Closing note (line 275): "`ack-cursor` and `ack-stop` are **operationally separate state machines** — delivery vs lifecycle — that share the `ack-` naming."
- **§10.4 rev 16 entry** — PASS (line 1280-1288): full D1-D4 capture + operator quote "the future is now" + cross-references to #11329 (runtime) and #11330 (sub-skills).

## DS audit trail

11 artifacts present (matching PM's claimed `3+4+3+1` distribution):
- AC1.1: `DS-AUDIT-11328-ac1.1.md`, `-r2.md`, `-r3.md` (3 rounds)
- AC1.2: `DS-AUDIT-11328-ac1.2.md`, `-r2.md`, `-r3.md`, `-r4.md` (4 rounds)
- AC1.3: `DS-AUDIT-11328-ac1.3.md`, `-r2.md`, `-r3.md` (3 rounds)
- AC1.4: `DS-AUDIT-11328-ac1.4.md` (1 round)

Doc-only task; no test sweep required.

## Scope discipline observed

Out-of-scope items correctly delineated and tracked elsewhere per the locked rescopes:
- Runtime code migration (event_poll.py per-event ack-cursor swap, working-state.md schema cleanup, regression tests) → **#11329**.
- Sub-skill alignment (cursor-management.md, event-mode-contract.md, event-driven-workflow.md) → **#11330**.

All three tasks ride the #11144 polish-session bundle into main.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Architectural sharpening of the cursor and nudge contracts is observably consistent across §2.2/§4.1/§4.3/§7.1/§7.5/§7.6 and §10.4. The eager-loop reframing is internally coherent (per-event ack → drain-to-empty → improvement-subloop branch → idle) and the catalog distinction between `ack-cursor` and `ack-stop` is now explicit.

PR base is `squidsquad/skill/compose-polish-session` (the polish bundle), not `main`. DM merges this through the polish-session bundle along with #11144.
