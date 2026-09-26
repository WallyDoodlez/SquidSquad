# QA-RESULTS-14131 / 14132 -- PASS
| TC | Result | Evidence |
|----|--------|----------|
| TC1 | PASS | test_deploy_stall_restart_14131_14132.py drives the REAL HarnessState.update_health() (only process/boot seams mocked): idle-past-window -> _run_deploy_sequence called once with newest deploy-signal id across repeated polls; active-past-window -> one deploy-error stage=halt-timeout, no deploy; past ceiling -> recover; no-auto-reboot/freshness-failed -> surface; inside window untouched; recheck-before-kill (F3) |
| TC2 | PASS | same class contains dead-PID cases unchanged (dead past window fallback; dead + deploy in flight left to deploy; dead inside window settles) |
| TC3 | PASS | TestDeployInflightGuard: second start refused, cleared on raise, ack-stop deploy-halted routes through guard; tests/test_harness_deploy_12912.py updated 13 lines, passes |
| TC4 | PASS | TestIdleRestartBypassesPauseGuard: idle restart stamps operator_force_at, active_pause would still say "waiting", next poll boot_agent called once, marker one-shot consumed |
| TC5 | PASS | test_idle_restart_with_waiting_since_respawns_next_poll + force variant |
| TC6 | PASS | test_unexplained_death_while_waiting_keeps_hold + stale marker keeps hold + failed kill / already-dead clear marker |
| TC7 | PASS | 75/75 (new + 12912 suite); static gate 6586/0; harness integration suite exit 0; merge-tree clean; receipts pass |
Live limits: an isolated-harness attempt with a fake live agent could not be staged (persisted intent normalizes on load) and adopted the real agents' PIDs, so it was stopped at once; real fleet PIDs unchanged (dm 33564, pm 47068, qa 14808, skill 36696). Behavior takes effect on the next harness restart, same as #14144 AC6.
