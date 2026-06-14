---
name: learning-ead-status-routing-and-back-transition-dedup
description: event-mode work delivery (harness EAD assigned-to events) must route by STATUS to the right role-class (pending-test→verifier, pending-ship→dm), and dedup by last-status-PER-ISSUE not per-(issue,status) — a per-(issue,status) set permanently suppresses re-entry to a status and starves QA on every reject loop
metadata:
  type: learning
type: learning
tags: [learning, harness, event-mode, work-delivery, dedup, EAD, 12342, self-hosting]
created: 2026-06-14
updated: 2026-06-14
owner: skill
status: active
confidence: high
source: observation
links: [learning-default-port-fallback-is-live-egress-trap-in-tests]
---

# Event-mode work delivery: route by status, dedup by last-status-per-issue

**Observed (#12342):** in event mode, QA/DM **starved** — they sat idle with items in pending-test/pending-ship and never got a wake event. The harness External Activity Detector (`harness.py` `_check_for_changes`) only emitted `assigned-to` events for `approved`/`open` (workers); pending-test/pending-ship never routed. Plus a broken `_is_agent_update` (`title.startswith(("ISSUE:","TASK:"))`) matched *every* SquidSquad issue, so the EAD emitted nothing at all.

**Two design rules that fell out of the fix:**

1. **Route by status to the role-CLASS, not the issue's `role:*` label.** approved/open → the issue's `role:*` worker alias; **pending-test → verifier alias; pending-ship → dm alias**. The verifier/dm aliases are NOT on the issue (the `role:*` label is the worker who built it) — resolve them from the install's alias registry (`config.parse_aliases_registry()`) by role-class, so it works whatever the verifier/dm aliases are named (this install uses the legacy `qa`).

2. **Dedup by last-status-PER-ISSUE, never by `(issue_num, status)`.** A `(issue_num, status)` set looks right but **permanently suppresses re-entry to a status** — so the common reject loop `pending-test → in-progress → pending-test` (QA rejects, worker resubmits) produces no second wake and QA starves on re-verification. Record ONE entry per issue = its last observed status, emit only on a *change*, and record the intermediate (unmapped) `in-progress` so the back-transition differs and re-emits. One entry/issue also keeps the eviction cap counting *issues*, not status-tuples.

**How to apply:**
- Any "emit a wake event per state change" mechanism on a forge that allows status *cycles* must dedup on "did the state change since I last acted", not "have I ever seen this state". Cycle-bearing state machines (reject loops, merge-conflict rollbacks) break naive per-state dedup.
- A polling detector only sees *current* state, not transitions — leverage the intermediate state (here `in-progress`) it DOES observe to reset the dedup for the next routed entry. Fast cycles within one poll interval are backstopped by the agent's own `work_queue` re-scan (events are hints; the forge is truth).
- This bug was caught by the per-change DeepSeek review (DS-REVIEW Finding 1), not by my own tests — the first dedup design passed all my forward-transition tests. Reinforces the team's DeepSeek-review-at-logical-boundaries rule: review high-blast-radius logic before shipping; forward-only tests miss cycle regressions.
