---
name: learning-wire-format-specs-triplicated-across-trds
description: HTTP/wire-format contracts are duplicated across HARNESS-ARCH ↔ AGENT-RUNTIME ↔ event-mode sub-skills; a drift report against one almost always means the same drift in the siblings — fix all together.
metadata:
  type: project
---

Event-bus wire-format contracts (HTTP status codes, response field names, recovery
anchors) are stated in **three** places that must agree: `docs/HARNESS-ARCH.md` (the
harness spec), `docs/AGENT-RUNTIME.md` (the agent-runtime spec), and the runtime
event-mode sub-skills under `references/sub-skills/common-events/` (e.g.
`cursor-management.md` — the contract the agent actually follows).

A drift report filed against **one** of them is a near-certain signal the same drift
exists in the siblings. Concrete case (#12971, 2026-06-21): the cursor-eviction
recovery contract was reported drifted only in HARNESS-ARCH §5.1 (`HTTP 410 Gone` +
`cursor_evicted`/`current_head`), but the **identical** wrong-model text also sat in
AGENT-RUNTIME §5 (line 411) and its phase table. Ground truth (`harness.py`
`get_since_with_eviction` → `get_events_for_role`): normal **HTTP 200** + body marker
`{evicted, oldest_id, evicted_count_hint}`, recovery `ack-cursor(oldest_id)`; the agent
sub-skill `cursor-management.md` already documented it correctly.

**How to apply:** when fixing a wire-format/HTTP-contract drift in any one of these
docs, immediately `grep` the sibling TRD(s) **and** the relevant `common-events/`
sub-skill for the old field names / status codes before closing the issue. Treat the
already-correct agent sub-skill as the tie-breaker for ground truth (agents follow code,
so the runtime fragment is usually closest to reality). Verify convergence with a
zero-residual grep of the old identifiers across all three. This is the concrete TRD-pair
instance of the L2 [[feedback_doc_first_for_arch]] prose-drift discipline.

**Ownership note:** correcting TRD prose (`docs/*-ARCH.md`) to match shipped code is **PM
doc lane**, not skill code lane — even when the reporter tags it "skill/DS-audit domain."
Skill's lane is the compose-consumed sub-skills (`references/sub-skills/`) and any code RCA.
