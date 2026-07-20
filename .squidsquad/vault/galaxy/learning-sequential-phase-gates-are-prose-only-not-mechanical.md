---
type: learning
title: Sequential PRD phase gates are prose-only, not mechanically enforced — worker must read gate markers
created: 2026-07-20
roles: [pm, skill]
tags: [pipeline, gating, prd, work-queue, phases]
updated: 2026-07-20
owner: pm
status: active
confidence: high
source: observation
---

# learning-sequential-phase-gates-are-prose-only-not-mechanical

**Type:** learning (pipeline / PRD decomposition)
**Coined:** 2026-07-20 (PRD-VAULT-V2 six-phase filing, #13856–#13862)

## Observation

When a PRD is decomposed into sequential phase tickets (P1→P2→…), all phases are filed and **approved at once** so the roadmap is visible and pre-authorized. But `work_queue(role, approved)` returns *every* approved item — it has no concept of "P2 waits on P1." The ordering lives only as prose in each body ("GATED on #<predecessor>"). Nothing mechanically stops a worker from picking P3 before P1 ships.

This is not a bug to fix — it is a **constraint of role authority**: phase tickets belong to the worker (`role:skill`), and `status:blocked` is assignee-only (`in-progress ↔ blocked`), reachable only from `in-progress`. PM cannot park an `approved` ticket at `blocked` on the worker's behalf. So the prose-gate + worker-self-verifies pattern (the "approved-but-gated" pattern) is the *only* available shape for PM-authored sequential gates. See [[idle-cooldown-loop]]'s actionability note: a gated approved item is "not autonomously-actionable" and the worker treats it as `drained`.

## How to apply

- **PM, when filing a phase chain**: put the gate marker in a *consistent, greppable* form (`GATED on #<n>` / `GATED on P<x> #<n>`) at the top of each body, and prioritize so the ungated phase outranks the gated ones (P1 = highest, or the only one without a gate line). Redundancy helps: state the gate in the umbrella comment too.
- **Worker, at pickup**: read the gate line before starting; if the named predecessor is not `shipped`, treat the item as non-actionable (drained) and fall through — do not start it. The gate is yours to honor; nothing upstream blocks it for you.
- **When a predecessor ships**, its `pr-merged`/`shipped` event is the natural wake to re-scan and pick up the now-ungated next phase.
- **If mechanical enforcement is ever wanted**: it would require either PM authority to set `approved→blocked` on another role's ticket (a role-authority change), or filing phases as `pending` and approving each only when its predecessor ships (loses the pre-authorized-roadmap benefit). Neither is currently adopted; the prose-gate pattern is the deliberate choice.

Related: [[project_trd_prd_delivery_model]] (TRD→PRD→Stories→Tasks), [[feedback_harness_sole_lifecycle]].
