# TEST-PLAN-14131 / 14132 (derived from issue-body ACs)
| TC | AC | Check |
|----|----|-------|
| TC1 | 14131 AC1 | live agent at intent=deploying past window: idle -> recovered via deploy sequence (once); active -> surfaced (one deploy-error), ceiling -> recovered; no-auto-reboot / freshness-failed degrade to surface |
| TC2 | 14131 AC2 | alive-PID-past-window case tested alongside dead-PID case |
| TC3 | 14131 AC3 | normal ack-stop(deploy-halted) path unchanged, in-flight guard |
| TC4 | 14132 AC1 | idle /restart with waiting_since set respawns next poll; pause-guard not applied to own kill |
| TC5 | 14132 AC2 | test covers restart of agent with waiting_since |
| TC6 | 14132 AC3 | unexplained death while waiting keeps #12458 hold |
| TC7 | gate | static gate, harness integration suite, merge-readiness, receipts |
