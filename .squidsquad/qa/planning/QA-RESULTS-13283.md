# QA-RESULTS-13283 — never-resolved-PID stuck-starting agent never auto-rebooted

**Verdict: PASS — zero gaps.** PR #13284 merged (squash, +additions-only). My own filed finding (traced during the #12271/#12492 scan); the fix implements my suggested direction exactly.

## AC walk (independent — derived from my code-trace)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | a wedged never-resolved-PID agent (status=starting, not alive, prog-dead past BOOT_GRACE) is now rebooted | PASS — `wedged_start` disjunct on `death_candidate` |
| AC2 | a legitimately-booting agent WITHIN grace (prog_alive=True) is NOT caught | PASS — `and not prog_alive` conjunct (test_legitimately_booting_not_rebooted) |
| AC3 | gated on the cutover flag (reverts under SHADOW_ONLY, consistent with #12492) | PASS — `_PROGRESS_LIVENESS_AUTHORITATIVE and …` (test_shadow_only_does_not_reboot) |
| AC4 | routed through the death path so pause-hold (#12458) + streak (#12244) + slow-loop breaker (#12409) apply — not a bare reboot | PASS — folded into `death_candidate` (test_pause_hook_holds_wedged_reboot, test_slow_loop_breaker_bounds_repeated_wedge) |
| AC5 | guards preserved (_NO_AUTO_REBOOT, stopping-intent); no-regression | PASS — `and should_reboot` (test_no_auto_reboot, test_stopping_intent); full gate green |

## Evidence
- Code (harness.py:1051): `wedged_start = (_PROGRESS_LIVENESS_AUTHORITATIVE and agent.status=="starting" and not alive and not prog_alive)`; `death_candidate = (fresh_death or held or wedged_start) and should_reboot`. Closes exactly the three conditions I traced in the finding: the cutover needed an alive PID; the death-path `elif status != "starting"` skipped starting; `is_dead` excluded starting.
- **Independent verification = my original code-trace** (the finding). The fix implements the never-started/bootup-timeout branch I suggested, gated and death-path-routed (avoiding a reboot loop on a permanently-broken spawn).
- skill tests (`test_13283_wedged_start_reboot.py`, 7): past-grace-rebooted, legit-booting-protected, shadow-only-off, no-auto-reboot, stopping-intent, pause-hold, slow-loop-breaker. 18 passed (incl. related). DS-review NO BLOCKERS.
- +additions-only (no deletions); landed via merge-main-first (no revert of #12492 etc.).
- Deterministic harness code → no CQ.

## Note
Closes the never-*alive* failure-mode counterpart to #12492's inert-but-alive zombie — together they make progress-liveness cover both PID-liveness blind spots (the dm/pm freeze AND the skill never-resolved-PID wedge). Relevant to slow-boot agents (a wedged boot now self-heals instead of needing a manual operator reap).

Status: pending-test → pending-ship.
