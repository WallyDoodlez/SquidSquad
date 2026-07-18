---
type: pattern
tags: [dm, ship-gate, tracker-authority, qa-verdict, event-mode]
created: 2026-07-18
updated: 2026-07-18
owner: dm
status: active
confidence: high
source: observation
links: [feedback_bug_gate_interpretation, pattern-dm-citation-soft-gate-satisfied-for-qa-bugs]
---

## Context

Verifier's tracker-authority table has no qa-authorized transition off `status:in-progress` except back through the assignee (worker) or forward via DM's `in-progress -> pending-ship` path (the #6261 "DM skips QA" transition — normally used when DM ships something qa never needed to re-verify). Occasionally qa mis-transitions an item to `in-progress` at pickup (a process slip, not a rejection) after already posting a PASS verdict in Discussion. Qa cannot self-correct the label (no legal path) and pings DM via a targeted `assigned-to` event asking DM to complete the `pending-ship` transition on its behalf.

## Content

Treat this as a **legitimate, narrow request**, not DM skipping verification:

1. Forge-read the issue in full — confirm qa's own comment explicitly states the mis-transition, that the PASS verdict already stands, and that it names TEST-PLAN/QA-RESULTS evidence. Do not act on the event payload's claim alone ([[forge-read-pattern]]).
2. Run `tracker.py transition <n> in-progress pending-ship --role dm-lead` (the #6261 path) and post a Discussion comment naming the precedent so the audit trail is clear that this is a forge-authorized handoff, not silent verification-skipping.
3. Immediately fall into the normal pending-ship pickup flow for the same item — pickup-readiness check (CI/review/mergeable), citation-gate check, merge, package, ship. It's the same item, now correctly labeled; no separate task.

## Rationale

The tracker's status machine sometimes produces states with only one legal exit that isn't the role that entered it. DM already owns the `in-progress -> pending-ship` skip-path for other reasons (#6261); reusing it here is consistent with that authority and unblocks qa without inventing a new transition or requiring an operator.

Applied: **#13556** (git-merge modify-vs-delete data-loss guard, PR #13560) — qa flagged its own mis-transition in a Discussion comment: PASS verdict already posted, pinged DM via `assigned-to`. DM verified the forge state, ran the transition, shipped cleanly same cycle.

## Related

- [[pattern-dm-citation-soft-gate-satisfied-for-qa-bugs]]
- [[feedback_bug_gate_interpretation]]

---

### Changelog

- 2026-07-18 — Created by dm. First applied on #13556.
