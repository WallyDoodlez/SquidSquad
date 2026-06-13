# Iteration 463 — implemented #11723 (durable fix for the #11586 root cause)

**Mode**: loop (sticky). Manual ops.

## What happened
- Confirmed the #11586 root cause is an ACTIVE corruption: my clone's .harness-port, corrected to 7373 at 10:14, was re-stomped to 59999 by 10:17 — the verifier's per-cycle full-suite run starts a harness whose `_deferred_init` distributes its ephemeral port (find_free_port(59999)) into the REAL clones via the real .local-config. (Main commit caf10fe21 shows the team band-aiding this with a 'pin-keeper' watchdog: 'durable fix still pending operator.')
- Filed **#11723** (high) with the full 3-part fix analysis, then implemented **Part 2 (resilience)**:
  - Hardened the 3 discovery copies (event_poll._discover_port, cycle_pre/cycle_post._discover_harness_port): build a candidate list [file-port, parent-walk, default 7373] and return the FIRST that is actually LISTENING (TCP connect via _port_is_live), skipping a dead port-file value. A stale/leaked file now behaves like a missing one. Default 7373 when nothing listens. #11601 always-returns-int contract preserved.
  - Tests: 8 new (test_11723) + 5 updated existing (test_event_poll ×2, test_cycle_pre ×2, test_cycle_post ×1) to the liveness-aware contract.
  - Full suite: only the pre-existing #11657 event_poll red (gated on #11683). Zero new failures. (Pre-existing test_cycle_pre TestGetVerifiableRoles failures are quarantined #6274 debt — not mine, confirmed via stash.)
- Committed, pushed task/11723, opened **PR #11729**, spawned DS review (bv4nh01ft), posted status on #11723. Held in-progress (gated on #11683).

## Net: FOUR skill PRs in flight (#11709/#11715/#11722/#11729), all gated on #11683 ship.

## Next cycle
- Read #11723 DS output; address findings.
- #11683 → if shipped, land all 4 PRs.
- #11723 follow-up (1): isolate test .local-config so test harnesses stop polluting real clones (the ROOT fix); (3) boot-instruction fall-through.
