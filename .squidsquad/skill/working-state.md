# Working State

- **Task**: none in-flight. The instruction-layering cluster is on OPERATOR HOLD (below). No new actionable autonomous work in queue. Idle-armed.

## OPERATOR HOLD — instruction-layering cluster (2026-06-27)

- **#13291 (L1 universal "stay-current" norm) — REVERTED + PARKED at `pending-human-review`.** Timeline: pm posted an operator HOLD (16:55) on the whole cluster (#13291 L1 norm / #13286 dev rule / #13287 dev-domain layer) while I was mid-build; I finished the in-flight atomic unit and shipped to pending-test (17:09, PR #13292) before the hold surfaced (pm: expected). qa picked up, verified + squash-merged before reading the hold, then git-reverted both the squash (2fe73dfb3) and the QA-RESULTS commit (e9b944004) — non-destructive revert commits a4eb27c10.., pushed. **No cluster trace on main**: identity.md back to "never push without pulling first", per-role bullets restored, all 4 composed CLAUDE.md = 0 occurrences of the new norm.
- **DIRECTIVE: drop the cluster from active work; do NOT touch #13291/#13287; await operator re-approval.** Nothing from this cluster lands in main until the operator confirms direction (re-discussion pending).
- **Self-correction this session**: on resume I had an in-flight post-merge recompose (composed CLAUDE.md carrying the new L1 wording, generated against the briefly-merged source) — DISCARDED before commit. Caught the re-land vector. Process note posted on #13291: reverting an L1 *source* change does not auto-revert *deployed* composed output; recompose is a separate post-merge step (harmless here — #13292 shipped source-only, no deploy ran — but a guard for the cluster design).

## CARRY-FORWARD (other lanes — not mine)

- **#13285 (post-merge scope-audit) — VERIFIED → pending-ship (PR #13288 merged; QA-RESULTS-13285 on main).** Flag to operator: flip `SQUIDSQUAD_MERGE_AUTO_REVERT=1` once detection is trusted in prod.
- **#13286 (dev forge-workflow) — VERIFIED + MERGED → CLOSED (PR #13290).** Landed BEFORE the hold; the operator may revisit it in cluster re-discussion (their call, not mine to revert).
- **#13275/#13276, #12450, #12492/#12271** all landed/closed earlier this run.

## NOT CLEANLY AUTONOMOUS (operator-gated)

- **#12527** — greenfield FOREIGN-repo installer smoke: LIVE run human-supervised; static audit done.
- **#10690** — wiki-link rework, gated on E6+E7.
- **#10686** — PRD-E E7 manual on-repo migration smoke.
- **#13278, #13279** (open, mine, improvement-scan): model_router degenerate / git_ops._log_diagnostic no timeout. NOT self-fixable without triage.

## STANDING REMINDERS

- Feature work on `squidsquad/task/<n>`; working-state + planning commit DIRECT to main (#11511 strips them from feature branches). `git switch -c` BEFORE code edits — esp. on idle->pickup (no task-begin fires).
- Push: `git -c credential.helper='!gh auth git-credential' push`.
- Pending-test gate = `python tests/run_tests.py static` (~5168 gated, fail-closed). Known-failures test_agent_boundaries + test_compose_author_comments_11142 (both #10360-blocked) -> gate still exits 0.
- model_router/DeepSeek degenerate this session (#13278) -> go straight to a Sonnet review subagent.
- **L1/L4 source revert ≠ composed revert**: after any revert of a DEPLOYED instruction-layer change, recompose every affected role (`compose.py deploy <alias>`) or composed output silently keeps the reverted wording.

## Improvement Scan
Status: armed. Prior idle stretch filed #13278 + #13279 (await triage).

## Quiet Cycle Counter: 0
