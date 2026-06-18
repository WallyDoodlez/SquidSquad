# TEST-PLAN #12420 — Installer post-commit harness restart (INSTALLER-ARCH §10.3)

**Derived from the issue's ACs 1-5 + AC-CQ** (PM-stated AC-CQ, verifier-authored spec per
test-workflow-separation). WIZARD.md is LLM-consumed → comprehension gate required.

## ACs
- **AC1**: after commit, probe `GET /status`; reachable → per-alias `stop`+`start`; unreachable → `start.sh` cold-start fallback. Both paths.
- **AC2**: a live squad picks up the new CLAUDE.md after a re-run (no stale-instruction agents).
- **AC3**: endpoints match HARNESS-ARCH §4.1 lifecycle routes (`POST /agents/{role}/stop|start`, alias as path-param).
- **AC4**: WIZARD.md Step 7.6 updated to perform the restart (replaces bare "run ./start.sh" + exit); doc ↔ runbook in sync.
- **AC5**: tests for reachable restart path + unreachable start.sh fallback.
- **AC-CQ**: verifier-authored `tests/comprehension/12420_spec.json`; fresh agent on the composed WIZARD restart prose → zero misreads of the 3 branches (reachable / unreachable / partial-failure) + alias-loop.

## Test Cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1/AC3 | inspect wizard.py restart_agents + §4.1; run reachable/unreachable unit tests | probe + per-alias stop/start; unreachable → cold-start; endpoints match §4.1 |
| TC2 | AC2 | restart logic (stop+start → respawn → boot refreshed) via mocked tests | no stale agents; agents respawn on refreshed CLAUDE.md |
| TC3 | AC4 | inspect WIZARD.md Step 7.5c + 7.6 prose | branches on reachable; refreshed-msg vs cold-start; ephemeral exit |
| TC4 | AC5 | run `test_wizard_12420_post_commit_restart.py` (21) | all pass; covers reachable, unreachable, partial-failure, exit codes |
| TC5 | AC-CQ | author spec; fresh sonnet agent quiz on Step 7.5c+7.6 | 6/6 correct, zero misreads |
| TC6 | regression | wizard test suite + static gate | no NEW failures introduced by the PR |
