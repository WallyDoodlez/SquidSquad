# QA-RESULTS-11657 — Stale integration test asserts pre-#11601 fail-closed contract

**Verifier**: verifier-lead (qa)
**Date**: 2026-06-13
**PR**: #11683 (squidsquad/skill/post-cutover-cleanup → main) — MERGEABLE/CLEAN
**Branch verified**: squidsquad/skill/post-cutover-cleanup @ 592d55649
**Verdict**: **PASS**

## Deviation acknowledged
AC said "rebind the test"; skill REMOVED it instead. Justified: post-#11601 a missing
.harness-port resolves to default 7373, so single-shot event_poll has no stable exit code
to assert (polls live default-port harness → exit 1, or retries refused port forever) — a
rebind would be flaky or duplicative. The deterministic #11601 contract is already covered
in tests/test_event_poll.py. Verifier accepts the remove-with-NOTE over a flaky rebind:
the AC intent (no stale fail-closed assertion; #11601 behavior covered) is fully met.

## AC Walk (intent-mapped)

### AC-1: stale "harness port not found / exit 2" assertion gone
**PASS.** test_event_poll_exits_cleanly_when_harness_unreachable removed from
tests/integration/test_event_mode_agent_subprocess.py (source). Only a stale .pyc cache
still matched on grep; the .py source no longer defines it. Replaced by a thorough
#11657 NOTE (lines 523-541) documenting the supersession, the #11601 commit (d0986cb7e),
and where coverage now lives.

### AC-2: #11601 default-7373 fallback covered
**PASS.** tests/test_event_poll.py::TestDiscoverPort covers it deterministically:
  - test_defaults_to_7373_when_file_absent
  - test_garbage_content_defaults_to_7373
  - test_poll_returns_none_when_discover_port_returns_none (defensive None bail)
All green in the suite run (integration: 53 passed, 2 skipped, EXIT=0).

### AC-3: run_tests.py fully green (0 failures)
**PASS.** Full suite EXIT=0; the formerly-red un-quarantined integration test no longer fails.

## Bonus fix verified
Old test deleted the live .harness-port and only restored it in finally — a killed run left
it gone. Removal eliminates that footgun. Confirmed in NOTE + absence of the destructive method.

## Verdict
**PASS → pending-ship.** Rides PR #11683 with #11503. DM ships the bundle.
