# Iteration 314 — 2026-06-17 22:14

**Mode**: POLLING.

**Outcome**: **#12420 VERIFIED → FAIL → in-progress (skill).** One concrete gap; rest shipped-quality.

## Pickup
- PT scan surfaced **#12420** (type:task, priority:high) — installer post-commit harness restart (INSTALLER-ARCH §10.3). Branch squidsquad/task/12420, PR #12596. From approved skill queue.

## Verification (6 ACs + AC-CQ)
- **AC1/AC3 PASS**: `wizard.py restart_agents` probes /status; reachable → per-alias `POST /agents/<alias>/stop`+`/start` (best-effort, non-fatal, ok=False only reachable+failure); unreachable → reports ./start.sh, never self-spawns (Q-new21). Endpoints match HARNESS-ARCH §4.1.
- **AC2 PASS**: stop+start per alias → respawn on refreshed CLAUDE.md.
- **AC4 PASS**: WIZARD.md 7.5c added + 7.6 reworked (branches; ephemeral exit).
- **AC5 PASS**: test_wizard_12420_post_commit_restart.py 21/21.
- **AC-CQ PASS**: authored `tests/comprehension/12420_spec.json` (6 CQs); fresh sonnet agent **6/6 correct, ZERO misreads** of the 3 branches + alias-loop.
- **TC6 regression FAIL**: `test_wizard_runbook.py::test_every_wizard_command_mentioned_exists` → `Runbook references unknown wizard commands: {'restart-agents'}`. #12420 added `restart-agents` to wizard.py dispatch + WIZARD.md but NOT to `_WIZARD_COMMANDS` (test_wizard_runbook.py:33-42, the runbook↔dispatch invariant; its comments document the per-PR-update pattern). Passes on main → PR introduced it.

## Disposition
- FAIL → in-progress (skill). One-line fix: add `"restart-agents"` to `_WIZARD_COMMANDS`. Re-verify TC6 + quick wizard-suite pass on re-submit.
- Comprehension spec committed to main (preserved verifier artifact — re-verify reuses it).
- **Not a #12420 gap (recorded)**: `test_feat_6581 test_tc_10b` fails (recursively runs the now-honest non-zero full suite — #11503; #10360/#12748 known/env). Fails on main too.

**Quiet Cycle Counter**: 0 (productive — verification with route-back).
