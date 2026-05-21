# Working State

- **Task**: HOLD on fleet flip per human directive cycle 1541-1542
- **Status**: alignment phase — locked architecture, planning artifacts in flight
- **Last Processed Event ID**: 2461e3f1

## FLEET FLIP — ON HOLD
Reason: #9873-A + #9873-B (event-bus redesign) must ship before event-driven flip. Per human directive cycle 1541.

## Architectural locks (cycle 1541-1542)
See vault: `decision-event-bus-architecture-redesign.md` for full detail.
- Harness = transport bus, not orchestrator
- Forge = work-state source of truth
- Ack = event-type on bus, emitted by event_poll.py after stdout write (receipt confirmation, not completion)
- Cursor moves to harness; new endpoint `GET /events/cursor/{role}`
- Monitor contract unchanged — redesign happens inside event_poll.py + harness
- No `POST /events/{id}/complete` — rejected entirely

## Tier 1 redesign tickets (filed cycle 1541, all status:planning)
- **#9873** — restore event ack-on-delivery (umbrella). RESEARCH-9873.md done. Splits into:
  - **9873-A**: cursor migration to harness + `GET /events/cursor/{role}` + ack event type + harness ack-consumer task. **Pre-flip blocker.**
  - **9873-B**: timeout_scan re-delivery. **Pre-flip blocker.**
  - **9873-C**: TUI ack visualization. Post-v1.
- **#9874** — harness arch review. RESEARCH-9874.md done (8 hazards found, H3 is wedge culprit). **Deprioritized — alignment-first.**
- **#9875** — L2 vault writeback + research-consults-vault. RESEARCH-9875.md done. **Deprioritized — alignment-first.**

## Awaiting human input
- #9873 split into 3 sub-tickets vs umbrella (lean: split)
- Cursor cutover style (lean: clean cutover, no local-file fallback)
- Then proceed to write CONTEXT-9873-A, -B, -C

## Other in-flight
- **#9845** noop event stress-test — status:planned, awaiting human approval. NOTE: should be retrofitted to ride on #9873-A's ack mechanism once that lands.
- **#9478** at status:pending-test (QA pipeline)
- **#9837** shipped via #9844 — universal-shipper queries now surface closed-but-labeled pending-ship items

## Pending-ship queue (now visible to DM post-#9837)
- #9740, #9741, #9742, #9744, #9725, #9772, #9813, #9837 — 8 items
- Ship counter 11/10, awaiting DM bump

## Vault writes this session
- learning-strip-vs-wire-audit-findings (1541)
- decision-phase-4-event-ack-lifecycle-deferred (1541) — SUPERSEDED in spirit by decision-event-bus-architecture-redesign which rejects Path B entirely
- decision-event-bus-architecture-redesign (1542)

## Memory rules added this session
- feedback-proactor-loop-two-bugs
- feedback-minimal-repro-over-symptom-match
- feedback-orphan-claude-from-subagents
- feedback-tracker-comment-prefix
- feedback-orphan-claude-on-reboot
