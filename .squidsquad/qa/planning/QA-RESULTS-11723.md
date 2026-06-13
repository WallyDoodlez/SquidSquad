# QA-RESULTS-11723 — Stale/leaked .harness-port strands agents + kills Monitors

**Verifier**: verifier-lead (qa)
**Date**: 2026-06-13
**PR**: #11729 (squidsquad/task/11723 → main)
**Branch verified**: squidsquad/task/11723 @ 1e760e759
**Verdict**: **PASS (Part 2 — the scoped deliverable)** + scope flag for PM (Parts 1 & 3)

## Scope
PR implements Part 2 only (the resilience layer): port discovery is liveness-aware and
skips a dead port-file value, falling through to the default. Parts 1 (stop test harnesses
polluting real clones) and 3 (boot-bootstrap CQ) are explicitly out of scope by skill's design.

## AC Walk (Part 2)

### AC: a non-listening port-file value is skipped → fall through to default 7373
**PASS.** event_poll._discover_port (event_poll.py:119) builds candidates (repo file →
5-level parent walk → default 7373) and returns the FIRST that `_port_is_live` accepts;
a dead candidate is skipped. `_port_is_live` (event_poll.py:91) = `socket.create_connection
(127.0.0.1:port, 0.5s)`, False on OSError/ValueError/TypeError/OverflowError. Mirrored in
cycle_pre._discover_harness_port (:300) and cycle_post._discover_harness_port (:782).

### Regression tests (would have caught the original bug)
**PASS.** tests/test_11723_port_discovery_liveness.py — 7/7 pass:
  - test_port_is_live_false_for_dead_port — dead port → False
  - test_discover_skips_dead_file_port_and_falls_to_live_default — THE FIX: dead .harness-port
    skipped, discovery returns the live default (the exact 59999-strands-agent scenario)
  - test_discover_returns_default_when_nothing_listening — harness down → default (loop mode)
  - test_discover_returns_live_file_port / missing_file_uses_live_default / port_is_live True/garbage

## Test Execution
- `pytest tests/test_11723_port_discovery_liveness.py` → **7 passed**, EXIT=0.
- `pytest tests/test_event_poll.py tests/test_cycle_pre.py tests/test_cycle_post.py` → **283 passed**.
- `python tests/run_tests.py static` → EXIT=0, **2268 passed, 0 failed**; new test file in gate
  (158 files); KNOWN_FAILURES still only the 2 #10360-gated entries.
- Integration suite deliberately NOT run by QA: its harness-spawning tests are the exact
  mechanism this issue identifies as polluting sibling clones' .harness-port. skill reports the
  full suite green (4124 passed / 15 skipped); my targeted + static coverage exercises all changed code.

## Scope flag for PM (NOT an AC failure — does not block Part-2 ship)
Parts 1 & 3 are tracked ONLY in #11723's comments. Since #11723 is type:issue, shipping
auto-closes it and the follow-ups would drop off the tracker. Two points for PM:
  1. Part 2 makes agents TOLERANT of a dead port but does NOT stop the pollution — the root
     cause (Part 1) persists after this ships.
  2. The root cause is QA's own per-cycle full-suite runs: integration tests spawn a harness on
     an ephemeral port against the real .local-config, and boot_remote.py (the lone $SQUIDSQUAD_DIR
     env-var holdout) distributes that dead port into real sibling clones via _deferred_init.
Recommend PM file follow-up issue(s) for Part 1 (boot_remote env-honor + test-fixture isolation)
and Part 3 (boot-bootstrap CQ) before #11723 auto-closes, so they aren't lost.

## Verdict
**PASS → pending-ship** for the Part-2 deliverable. DM ships PR #11729. PM to preserve Parts 1 & 3.
