# iter-699 — 2026-06-18 16:23 (PM EVENT-mode, fresh boot after self-restart)

**Boot:** GH check-gh OK. Harness :7373 reachable (uptime 15h, git_sha 00757fe4, v0.44.0) → EVENT mode. Event-mode contract loaded (6 fragments). Cursor `3050d070742dc2e9`, boot drain EMPTY. bootup-complete emitted (ok). 0 untriaged external.

**Pipeline (forge-verified):** 0 open pending-test, 0 open pending-ship.

## Main outcome — recovered a wedged skill on the critical path (#12506)

Booting on the new #12585 "Facts Over Context" Soul, cross-checked my stale working-state against ground truth and found two corrections:

1. **qa is ALIVE (telemetry said inert).** Harness `/status`: qa bootup=False, last_activity ~894m → looks dead. Git log (independent source): qa committing iter-322→328 in POLLING mode, latest 22m ago. → qa recovered into polling; non-blocking (0 PT). Stale-telemetry for a polling agent is expected, not a bug.

2. **skill WEDGED on #12506 (critical-path self-wake driver).** Trace:
   - skill built 4 units → PR #12812 → pending-test → **qa FAIL AC11** (`subloop_driver.py` absent from `installer-files.txt`) → routed back in-progress/skill ~3h ago.
   - skill then alive-but-wedged: pid 51776 (NOT respawned by the 17m-ago "team reboot" despite prior working-state claim), last_activity 192m, **50 events backlogged undrained**, **0 skill-targeted**. The qa route-back emitted **no skill-targeted `assigned-to` wake** → even healthy skill wouldn't auto-resume. The exact idle-stall bug #12506 fixes, biting its own fix.
   - **Action:** `POST /agents/skill/restart`. Graceful stop stuck on the wedge (intent=restarting, bootup→False, same pid) for ~2m until the harness force-kill grace fired → **skill respawned pid 23616, intent=running**. On boot, work_queue() resumes #12506 (boot backstop, independent of the missing wake event). AC11 fix = compose-consumed code = skill domain (PM can't touch, #11334).
   - Route-back-no-wake is already covered by in-flight #12506 (periodic self-wake driver) + #12493 (L2 HALT detect incl. route-back) → no duplicate filed.

**Sub-observation (not filed):** harness graceful-restart of a *wedged idle* event-mode agent doesn't force-kill promptly — waits ~grace-timer for a cooperative exit that never comes. Relates to #12271 liveness redesign. Watch for recurrence.

**Handoffs confirmed on forge:** #12585 shipped; #12506 in-progress/skill; #10540 open/skill; #12799 open/skill (high); #12800 approved/skill. Queue correctly loaded — wedge was the blocker, not routing.

**PM queue:** approved umbrella PRDs (#10839/#10838/#10837/#10690) operator-paced, not autonomously actionable. Coordination-holds unchanged: #11092, #11053, #9968.

**Next:** verify skill reaches bootup-complete + picks up #12506; if fresh skill re-wedges, escalate to operator (possible environmental idle-wake bug beyond #12506's own fix).
