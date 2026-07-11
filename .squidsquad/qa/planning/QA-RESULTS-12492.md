# QA-RESULTS-12492 — Liveness cutover: progress-liveness authoritative, PID teardown-only

**Verdict: PASS — zero gaps.** High-pri TASK (#12271 slice-4 pt2). PR #13282 merged (squash, +additions-only).

## AC walk (independent)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | reboot driven by progress-liveness, not PID-poll; PID teardown-only | PASS — `_PROGRESS_LIVENESS_AUTHORITATIVE=True`; a zombie (PID-alive + progress-dead) is killed so the reboot path respawns it next poll; PID demoted (no longer vetoes a reboot) |
| AC2 | the clean divergence window cited as evidence the flip is safe | PASS (caveated) — the #12460 shadow logged to CONSOLE only (no on-disk artifact to link); canonical evidence = the recorded operator GO (#12271, 2026-06-27) + documented cases (qa zombie #10855, dm/pm wedge #13142, booting repro). The HARD GATE was operator-satisfied. |
| AC3 | a slow-booting agent (>60s, e.g. qa #12409) NOT rebooted while progressing/booting | PASS — booting-grace (#13179, `BOOT_GRACE_SECONDS=600`/10m) + pause-aware (#12458) inside progress_liveness keep a booting agent alive; only never-completes-past-grace (the #12271 ~54m case) reads dead. **I am the live AC3 case** (qa, ~1-2m boot) — comfortably protected. |
| AC4 | full harness suite green; cutover tests added | PASS — 305 harness + 8 cutover tests |
| AC5 | #12271 closes on land | (auto on ship) |

## Evidence
- Code (harness.py +60): single **additive gated kill-step** in update_health — fires only when `progress_liveness()` says dead AND PID alive AND intent=RUNNING AND not `_NO_AUTO_REBOOT` AND not pid_changed. Death/backoff/streak machinery untouched. Escape hatch `SQUIDSQUAD_HARNESS_PROGRESS_LIVENESS_SHADOW_ONLY=1`. HARNESS-ARCH §1/§13.7 synced.
- skill tests `TestProgressLivenessCutover12492` (8): zombie-killed, healthy-not-killed, shadow-only-no-kill, _NO_AUTO_REBOOT-guard, non-RUNNING-intent-guard, dead-PID-not-cutover, pid-changed-skip, kill-failure-robust. All PASS.
- **QA independent test** (`tests/test_feat_12492_cutover_slowboot_invariant.py`): asserts the two standing AC3 invariants — cutover authoritative + `BOOT_GRACE_SECONDS >= 120` (a real slow boot is never a cutover-zombie; guards against a future lowering that would re-introduce the #12409 loop) + the escape hatch exists. Authored as the live AC3 case.
- DS-review (Sonnet): NO BLOCKERS (added the pid_changed guard test). Deterministic harness → no CQ.

## Notes
- Unblocks #12409 (qa slow-boot reboot loop) retest + the qa→event-mode move. (qa is already event-mode this session; the cutover removes the residual PID-false-positive risk.)
- AC2 evidence is operator-GO-anchored rather than a linkable artifact (shadow was console-only) — flagged as a caveat, not a gap; the operator explicitly GO'd after the observation window.

Status: pending-test → pending-ship.
