# Working State

_Condensed 2026-06-14. Prior incident narrative (reboot saga, event-mode stabilization, #11505/#11511 churn diagnosis) is preserved in iteration logs iter-695..698 and on the forge — not re-copied here. Working-state = current active state only._

## Current — 2026-06-14 (PM inline session: DS audit + HARNESS-ARCH doc reconciliation)

**Mode**: HYBRID — skill/dm EVENT (7373), qa LOOP (pinned 59999), pm inline. Verified this session via OS process check: 4 `claude.exe` + 2 `event_poll` alive (pm/dm/skill/qa). **verifier clone absent** — no `pending-test` work waiting, so no boot (stall-recovery-only rule). `health_check.py` snapshot is stale this session (harness not updating it) — trust process check, not the 👻 readings.

**Reboot saga: CLOSED** — all fixes shipped (#12282 trigger/test-isolation, #12244/#12293 backoff, #12342 EAD routing, #12380 compose-alias). qa loop-pin (59999) is INTENTIONAL until #12409 (qa event-mode stability) lands.

### >>> DONE: harness restart (operator 2026-06-15 12:56) — executed ~14:0x in the quiet window after #12443 shipped <<<
- **Restart SUCCESS**: killed old harness (nohup 31668 + python 35768), relaunched `nohup python harness.py`. New harness on :7373, latest main (git_sha 13c68b4a) → **#12442 routing fix ACTIVE** (retire manual dm-nudge — verify next pending-ship auto-routes). All 4 agents SURVIVED with same PIDs (reconnected through ~8s blip, no respawn/WIP-loss). No compose ran (launched harness.py directly) → .local-config qa intact. qa stays loop. **event_poll orphans (9) NOT cleared** (seamless restart; cosmetic, #12363). 
- **#12271 slice (c) DUE**: slice (b) #12443 (activity-heartbeat) SHIPPED → file slice (c) pause-aware guard next.
- (Original pending-restart procedure/side-effects notes below superseded by the above.)
- **Quiet condition**: skill idle (no active child procs, #10855 at a transition point, CPU flat) AND no other agent mid-work.
- **Current harness**: nohup-wrapped (nohup PID 31668 → python harness.py 35768), :7373, up since 06-14 10:20 (#12342-loaded). Survived the operator's accidental terminal-close via nohup.
- **Why restart**: (1) clears the 9 `event_poll` orphans (#12363 cruft); (2) **activates #12442** (DM event-mode auto-route fix, SHIPPED to main 2026-06-15 — running harness predates it) → retires the manual dm-nudge workaround; fresh harness.
- **Side-effects to handle on restart**: (1) compose runs → verify `.local-config` still has `qa` (#11600; #12380 should've fixed — re-add if dropped); (2) port redistribution may un-pin qa's loop (59999→7373) → re-pin qa to 59999 (loop intentional until #12409); (3) confirm all 4 agents respawn + reach ready; (4) orphans cleared.
- **Procedure**: stop harness (kill nohup+python, or POST /shutdown) → relaunch via start.sh (or nohup python harness.py) → verify agents + qa config + qa pin.

### >>> DECISIONS RESOLVED 2026-06-15 ~22:35 (operator) <<<
- **#12460** (#12271 slice 4 CUTOVER) — APPROVED (shadow-mode strategy). skill front-loading it.
- **#12450** (installer unit-test detection) — APPROVED; L3/L4 split locked in-task (L3=behavior, L4-seed=specifics).
- **#12451** (status-bar event-model) — APPROVED.
- **#10855** — DEFERRED behind #12460 (operator "fine to defer"); likely superseded by the cutover (inert agent → no heartbeat → rebooted). Stays parked, do NOT resume; PM revisits/closes after #12460 lands. Status label still in-progress (parked) — clean up on revisit.
- **#12271 status**: slices 1-3 SHIPPED; slice 4 (#12460) approved + front-loading → completes #12271 when it lands.
- **skill approved queue**: #12460 (cutover, front-loading) · #11613 (installer, in-progress) · #12419/#12420 (installer) · #12450 · #12451 · #12363 (open).

### Active threads
1. **#12417 — MERGED 2026-06-15** (merge commit 29643ca8). HARNESS-ARCH (v24–v26) + AGENT-RUNTIME event_poll/`.claude-pid` reconciliation on main. Full work-discovery flow completed: research → draft → human review → DS re-audit (step 4) → cross-ref (step 5) → "all okay" → merge. PM merged under explicit operator authorization (boundary deviation noted on PR). **Descriptive-corrective → no new impl tasks spawned** (docs now match existing code). PM merged (boundary exception, operator-authorized).
2. **#12271** — **APPROVED + SLICED 2026-06-15** (operator "go ahead"). Umbrella, status:approved. Slice **(a) #12418 SessionEnd-reason hook** FILED + approved → skill. Slices (b) activity-heartbeat hooks, (c) pause-aware guard, (d) retire PID-poll — sequenced, file as predecessors land. Locked scope: liveness = activity-heartbeat + pause-guard; PID teardown-only; no new PID-reporting.
3. **#12363** — `/T` teardown fix: skill ENGAGED (RCA confirmed, fix contained: taskkill /T + os.killpg in `_kill_process`, all 3 paths via shared helper). Queued by skill as front-loaded pickup. medium sev. No PM action.
4. **#11505** — CLOSED 2026-06-15 as superseded-by-#10025 (operator-confirmed). Scope handed to #10025. Removed from 06-12 bundle.
5. **INSTALLER-ARCH thread (2026-06-15 re-audit + doc-honesty pass)** — operator recalled this thread. Doc re-audited (DS): architecture settled + cross-doc consistent; fixed event_poll straggler (§6/§10.3), reframed §4.8/§4.9 (scaffold composes inline via `deploy_role_v2`, no separate Phase 6), labeled §4.3/§10 migration-walk + §10.3 restart as **target — not yet in runbook**. **Installer impl backlog — APPROVED for build 2026-06-15 (operator "approve all"), all role:skill:** #11613 (dep auto-provisioning), #12419 (migration-walk in WIZARD/wizard.py), #12420 (post-commit harness restart). No PM planning phase (design in INSTALLER-ARCH §4.1/§10/§10.3 + research artifact; ACs testable). Coordination note on #11613: build serially (all touch WIZARD.md/wizard.py), suggested order #11613→#12419→#12420, DS-review-per-change, keep INSTALLER-ARCH↔WIZARD.md in sync. Now in skill's lane.
6. **#12300** work-discovery → L2 — DEFERRED (the process just proved itself on #12417).
7. **DS finding #4** (`/work/assign`) — INVESTIGATED: the endpoint is **fictional** (no route in harness.py/tracker.py; real routing = EAD `assigned-to` events + harness `role:*` rewrite). Bigger than "missing payload field" — affects HARNESS-ARCH §3/§4.3 + AGENT-RUNTIME §8.3/§5.2. **Doc-sync GATED on #12442** (routing fix determines whether `/work/assign` becomes real or the docs drop it). Linked on #12442; PM doc-syncs once routing settles.

### DS audit (HARNESS-ARCH §14/§15/§16) — 6 findings
- #1 event_poll spawn (BLOCKER) → draft PR #12417.
- #2 §7.3 `.claude-pid` health-poll fallback (HIGH) → FIXED v23.
- #3 AGENT-RUNTIME §4.2 stale `wt.exe` note (MED) → FIXED v23.
- #4 `/work/assign` body `payload` (MED) → needs doc task (routing investigation; outside §14/§15/§16). NOT filed yet.
- #5 §15-vs-§7.4 context-pressure (LOW) → by-design; rides #12271.
- #6 §4.1 aspirational API shapes (LOW) → no-op.

### Standing notes
- #11600 (qa `.local-config` wipe on compose) — durable fix #12380 shipped; re-add band-aid should no longer be needed if #12380 holds. Watch on next compose/harness-restart.
- "cycle NNNN" commit label has drifted historically (commit lineage ~2324 vs iter-log lineage ~2344); decorative only — anchor on `iter-N` + date.

- **Last Processed Event ID**: 3e50e129c8e74594
- **Quiet Cycle Counter**: 0
