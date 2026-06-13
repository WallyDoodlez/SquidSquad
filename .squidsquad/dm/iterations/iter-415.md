# DM Iteration 415 — 2026-06-13 14:45–15:15

**Wake mode**: POLLING (harness DOWN). pending-ship had 2 items.

## Shipped 2 items (separate PRs, serialized local-merge #10540)
- **#11641** (sev, role:skill) — PR #11715. thin_launcher._reclaim_stale_scheduled_lock removes a dead-holder .claude/scheduled_tasks.lock before Popen (after singleton gate); live holder preserved. Kills the startup-crash → harness reboot-loop. Verifier PASS, DeepSeek NO_FINDINGS. Counter 8→9.
- **#11723** (role:skill) — PR #11729. Part-2 resilience: event_poll._discover_port + cycle_pre/post._discover_harness_port skip a dead port-file value (repo-file → 5-level parent walk → default 7373, live-socket gated). Regression test_11723_port_discovery_liveness. Verifier PASS. Counter 9→10.

## Ship mechanics
- Both base=main, not draft, no delivery:skip. merge-tree CLEAN for both (GitHub mergeable=UNKNOWN; used merge-tree as authoritative per [[learning-pr-conflicting-flag-can-be-cosmetic]]).
- Serialized: merge --no-ff #11641 → push → re-fetch + merge-tree-recheck #11723 → merge --no-ff → push. Both PRs auto-flipped MERGED.
- Both are harness-SCRIPT changes (thin_launcher.py, event_poll.py, cycle_pre/post.py) — NOT CLAUDE.md/sub-skill templates → no compose/reboot_agent.py. Operator harness-restart picks them up (harness currently down).

## Bump gate
- Counter **10/10 = threshold**. Gate technically open. **HELD — not auto-fired** ([[feedback_bump_requires_pm_signal]]). Surfaced to operator/PM for green-light. On approval: minor v0.44.0→v0.45.0, CHANGELOG (internal-reliability framing), tag, push, reset.

## Flagged to PM
- #11723 Parts 1 (boot_remote env-honor + test-fixture isolation) & 3 (boot-bootstrap CQ) NOT in PR — PM to file follow-ups (verifier recommendation; issue auto-closed).

## Carried
- #10540 OPEN (DM-domain, awaiting PM routing). pending DM approvals #8702/#7447/#9933 (PM). Harness still down.
