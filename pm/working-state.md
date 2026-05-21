# Working State

- **Task**: HOLD on fleet flip; awaiting human direction on #9873 split + cursor cutover
- **Status**: idle — handover ready
- **Last Processed Event ID**: 2461e3f1

## v0.41.0 SHIPPED
- Version bump fired this cycle (Shipped Since Last Bump 11→0)
- All Tier 1 audit findings + #9772, #9813, #9837 + #9725 shipped
- Ship pipeline visibility bug (#9837) cleared the queue

## Awaiting human direction
- #9873 split into 3 sub-tickets vs umbrella (lean: split)
- Cursor cutover style (lean: clean cutover, no local-file fallback)
- Then PM writes CONTEXT-9873-A, -B, -C

## Architectural locks (vault: decision-event-bus-architecture-redesign)
- Harness = transport bus, not orchestrator
- Forge = work-state source of truth
- Ack = event-type on bus emitted by event_poll.py (receipt only, not completion)
- Cursor moves to harness; new `GET /events/cursor/{role}` endpoint
- Monitor contract unchanged
- No `POST /events/{id}/complete` — rejected

## Tier 1 redesign tickets (status:planning)
- **#9873** — restore ack + cursor migration. RESEARCH done. CONTEXTs pending split decision.
- **#9874** — harness arch wedge hazards (8 found, H3 = subprocess.run on event loop). RESEARCH done. DEPRIORITIZED.
- **#9875** — L2 vault writeback + research-consults-vault. RESEARCH done. DEPRIORITIZED.

## Other open
- **#9845** noop event — status:planned, awaiting approval. Will be retrofitted to ride on #9873-A.
- **#9478** branch_workflow=off removal — at pending-test, awaiting QA

## Quiet cycle
- No pending-test, pending-ship, open PRs, or external triage
- Skill picking up older Tier 2 bugs (#9687, #9724)
- DM in doc-scan mode

## Vault notes in current session (3)
- learning-strip-vs-wire-audit-findings (cycle 1541)
- decision-phase-4-event-ack-lifecycle-deferred (1541, partially superseded)
- decision-event-bus-architecture-redesign (1542) — authoritative
