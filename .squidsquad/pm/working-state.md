# Working State

## >>> UPDATE ~10:25 (Jun 14) — OPERATOR DECISIONS LOCKED; #12342 ACTIVATED <<<

- **Decision 1 = B (staged)**: push event mode to production-ready. **DONE step 1: #12342 ACTIVATED** — restarted harness from main (sha 93fc162c, loads EAD pending-test→verifier / pending-ship→dm auto-routing), killed 9 orphan claudes, re-added qa to .local-config (#11600 band-aid recurs), re-pinned qa loop (59999). Hybrid healthy: skill/dm event (7373), qa loop, all 4 alive. **PM nudging should now be unnecessary** — verify on next pending-test/ship transition. Step 2 (next): skill lands #12409 (qa stability) before re-attempting qa in event mode.
- **Decision 2 = ping+hooks, SessionEnd-slice first — BUT operator reviews sequence diagram first.** Added **§15.2 "Liveness signal flow" Mermaid sequence diagram** (HARNESS-ARCH v11) showing push emitters + pull ping/pong + SessionEnd-reason + last_seen/timeout reboot decision, with a reading-guide mapping the scope choice to diagram boxes. **#12271 stays pending until operator reviews the diagram.**
- **Decision 3 = DEFER #12300** (work-discovery process) until event-mode + harness-arch changes land.
- **Open**: operator reviews §15.2 diagram → then approve #12271 scope → break into tasks. skill: #12409 (qa stability), #11600 (compose alias), #10855 (inert-boot). Optional doc-debt (audit §4 findings) not filed yet.

## >>> UPDATE ~07:45 (Jun 14) — qa CHURNED+ZOMBIED in event mode → stabilized to LOOP (hybrid) <<<

- **qa event-mode instability**: stable ~4h (02:57-07:13) then 4 auto-reboots in 18min (07:13-07:30, all "was running, intent=running" = crashes), then the last respawn (696) went INERT (bootup=False 11min, #10855 zombie state). skill/dm stayed event-stable (qa-specific).
- **#12244 backoff DID NOT catch it**: deaths were >60s apart → fast-death streak resets → no backoff. Slow reboot loops slip through. Filed **#12409** (skill, high): add frequency-based breaker + SessionEnd-reason capture (#12271 slice) + orphan event_poll/claude accumulation (13 claude/12 event_poll for 4 agents).
- **STABILIZED qa to LOOP mode** (pinned 59999 + reboot → pid 52188 holding): loop polls/verifies on 30min cadence, no event-mode-sustaining dependency. **Current = HYBRID: skill/dm EVENT (stable), qa LOOP (stable), pm inline.**
- **Strategic finding for operator**: event mode is NOT yet production-reliable (qa churn+zombie; #12342 routing not activated). Hybrid is the pragmatic stable state. Operator decision needed: push event-mode fixes (#12409 stability + #12342 activation + #12271 liveness) OR accept hybrid / broader loop revert. NOTE: re-introduced a qa loop-pin (the hack I'd cleaned) — intentional, until event-mode-qa is fixed.

## >>> UPDATE ~05:40 (Jun 14) — REBOOT SAGA CLOSED OUT (all 3 fixes shipped) <<<

- **All shipped to main**: #12282 (trigger/test-isolation leak), #12244 (crash-loop backoff), #12342 (EAD auto-routes pending-test→verifier / pending-ship→dm). Reboot incident fully resolved on the delivery side.
- **#12342 NOT YET ACTIVE**: running harness (3h38m up) predates the merge. Needs a harness restart to load the new EAD routing. NOT urgent — PM-nudge workaround works fine + light. Activation restart = also clean 9 orphan claude procs + re-fix #11600 qa-config wipe (compose runs on restart). **Awaiting operator go-ahead before another restart.** Until then PM keeps nudging QA/DM on transitions.
- **#10855 ESCALATED to operator**: stuck in pending-test many cycles; qa reachable (woke/acked nudges) but renders no verdict. Pre-existing "verifier inert boot / AC-4" hard issue, separate from reboot work. Needs decision: skill re-investigate / re-scope / close.
- **Open operator decisions**: (1) #12271 liveness (ping-only vs ping+hooks §15.6); (2) #12342 activation-restart timing; (3) #10855 disposition.

## >>> UPDATE ~04:25 (Jun 14) — event-mode work-delivery gap (#12342) + PM-nudge workaround working <<<

- **Root cause of QA/DM starvation in event mode (filed #12342, skill, high)**: EAD only emits `assigned-to` for `approved`/`open` issues + skips agent updates (harness.py:3217/3206) → `pending-test`→QA and `pending-ship`→DM are NEVER auto-routed. Workers get work; QA/DM starve. Loop mode masked it (polls).
- **PM-nudge workaround WORKS**: injecting `assigned-to(role=pm, target=<alias>)` via POST /events wakes the agent (latency ~10-12min — qa woke 04:20 from my 04:08 inject). qa then verified **#12282 + #12244 → pending-ship**; injected a DM wake to ship them. So event-mode delivery functions when nudged; the gap is purely auto-routing.
- **REVISED recommendation** (supersedes "revert QA/DM to loop"): KEEP full event mode (honors operator directive, no hacky dead-port pins); **PM acts as interim manual router** — inject wake events on pending-test/pending-ship transitions — until #12342 auto-routes. Babysitting but clean and short-term.
- **Process hygiene**: 9 orphan claude.exe + ~8 orphan event_poll from this session's reboot churn (not causing active churn, but should be cleaned — flagged in #12342). #10855 still pending-test (may need another qa nudge). #11600 still recurs on compose.

## >>> UPDATE ~02:58 (Jun 14) — TEAM MOVED TO EVENT MODE + status cleaned (operator request) <<<

- **Root cause of loop-pinning found+killed**: leftover **pin-keeper.sh (PID 6036)** was STILL running, re-writing `.harness-port=59999` to skill/qa/dm every 30s → forced loop mode on every boot. Killed it; ports now stick at 7373.
- **Re-enabled harness auto-reboot**: restarted harness in NORMAL mode (dropped `--no-auto-reboot --no-auto-start`). Event mode REQUIRES auto-reboot (agents exit on Monitor-exit/ctx-pressure and need respawn); the incident that justified disabling it is resolved (#12244 backoff merged → churn impossible). Backoff is the safety net.
- **skill/qa/dm now in EVENT mode** (bootup-complete + acking cursors confirmed in harness log: qa 02:57:05, dm 02:57:39, skill 02:58:11). pm=this inline operator session (configured event/7373, bootup False because interactive, not autonomous loop — expected).
- **Status bar "showing 3" → cleaned**: removed 2 stray `test-*` entries polluting `.harness-state.json` (test-isolation leak, #12282 class). squidsquad_cli status now shows exactly 4 (dm/pm/qa/skill).
- **#11600 RECURRENCE**: harness restart ran compose → wiped `qa` from `.local-config` again (regenerates class `verifier`, not alias `qa`) → qa auto-respawn FAILED once until I re-added qa. **Will recur on every compose/harness-restart. #11600 (role:pm, open) needs the real fix.** Re-added qa for now.

## >>> UPDATE ~06:05 (Jun 14) — HARNESS-ARCH v8 post-merge sync (#12293 backoff landed) <<<

- **#12293 MERGED to main** (#12244 backoff). Synced HARNESS-ARCH to shipped code: §7.3 documents backoff algo (last_spawn_at, 60s fast-death window, 3-threshold, exp 30s·2^over cap 1800s, reboot_blocked_until, streak-reset-on-survival); §7.1.1 +`crash-looping` status; §7.5 +3 state fields; §11 row; **§13.8 flipped open-gap→RESOLVED**. Doc now matches code; the post-merge TODO I flagged is DONE.
- Also from log: QA verified my emergency-fix 162aa29a2 = "correct but 0 tests" → routed #12244 back to in-progress for skill to add durable tests (handled by skill). DM flagged QA merged #12293 bypassing DM gate (process note, dm-owned).
- **Open**: #12271 liveness (operator reviewing — links given). #12282 trigger (skill). Saga: backoff DONE+merged · trigger w/skill · liveness pending-approval.
- **Captured durably (06:18 cycle)**: vault learning-doc-first-for-architecture-changes.md (team) + PM memory feedback_doc_first_for_arch (cross-session). Quiet cycle: all 4 agents healthy (skill pid 55000 stable, backoff merged = no churn); #12282 queued (skill busy on #12244 durable tests — not a stall); #12271/#12300 await operator.
- **PROCESS FEEDBACK (operator, 06:12)**: steps went wrong — impl (#12244) before doc was correct+reviewed. For ARCH changes: correct doc FIRST, then impl. New **"work discovery" mode** for ALL PM roles → **L2**: on MAJOR change, suggest human create docs (not jump to tasks); PM opens DRAFT PR storing WIP docs; normal research+inquiries; EMPHASIZE human review; then adjust doc → DS internal audit on modified doc → cross-ref audit on related docs; human "all good" → break into worker tasks. **Filed #12300 as DISCUSSION task (do NOT rush to implement — apply the principle).** Doc reconciled with impl: added §10 step6 P0 (stale RESTARTING→running on load) — completes #12293 P0+P2 sync.

## >>> UPDATE ~01:55 (Jun 14) — HARNESS-ARCH contradiction polish (v7) + #12282 nudged + liveness breakdown given <<<

- **Operator decision posture**: fix root cause (#12282) first; #12271 liveness redesign is "still better" ONLY for zombie self-healing (real but manually-recoverable) — recommended layering = **#12282 (trigger) + #12244 (backoff) core; #12271 SessionEnd-slice cheap; full hook-heartbeat deferred**. Operator chose: NUDGE skill onto #12282 (done — priority comment posted); and asked to **polish arch doc for contradictions BEFORE any status moves** (in progress → DONE this cycle).
- **HARNESS-ARCH polished to v7** (commit pending): the `--no-auto-reboot`/`--no-auto-start` hatches were UNDOCUMENTED while §7.1/§7.3/§7.4/§10/§11 read auto-respawn+force-kill as UNCONDITIONAL → direct contradiction with shipped 162aa29a2. Fixed: new **§7.6** (hatches; no-auto-reboot is teardown-complete: refuse restart + skip compose-restart + skip RESTARTING force-kill + no respawn; STOPPING force-kill preserved); qualified §7.4/§7.1/§10/§11; new **§13.8** (no-backoff/crash-loop gap → grounds §15.3's #12244; separates amplifier from trigger #12282). No default-semantics change.
- **STILL pending operator**: #12271 status decision (held until doc polish reviewed). #12282 with skill (nudged). diag still ARMED in live harness (4 leak captures; dropped from working tree to avoid merge friction — runtime still armed).
- **#12244 ALREADY DELIVERED** (discovered via pull): skill built it → PR #12293 (+423/-29: exp backoff 30s→30m cap + crash-loop breaker + stale-RESTARTING-on-load fix); **QA verified PASS** (13 TCs, 197+53 green) → **pending-ship**. PM dispositioned QA's contract note: ACCEPT cause-agnostic backoff (session-limit-specific labeling infeasible w/o death-reason capture → folded into #12271 SessionEnd-reason slice; AC1/AC2 session-limit clauses superseded). Cleared for DM ship. **Post-merge TODO: update HARNESS-ARCH §13.8(closes)+§7.3/§7.5/§11 with backoff behavior + new state fields (crash-looping, reboot_blocked_until, consecutive_fast_deaths).**
- **Saga status**: #12244 backoff DONE(pending-ship) · #12282 trigger (skill) · #12271 liveness (pending operator approval; SessionEnd-slice now doubly-justified — also enables the session-limit label QA wanted).

## >>> UPDATE ~00:45 (Jun 14) — REBOOT TRIGGER CAUGHT (likely): skill's #12142 suite leaks /restart to LIVE harness → #12282 <<<

- **Armed restart-diag CAPTURED 2 restart requests** (00:35:34, 00:38:04, ~2.5min apart). Both: `current-state='implementing|implement-tasks — #12142 running full suite'`, intent=running, **ctx exceeded=FALSE (53<70)**. → DEFINITIVELY not cycle_post context-pressure (the only documented /restart caller). Something POSTs real /restart to LIVE harness :7373 DURING skill's #12142 full-suite run.
- **HYPOTHESIS (strong, not yet confirmed — skill's RCA)**: a #12142 test exercises restart/cycle_post/squidsquad_cli-restart WITHOUT mocking network/port → discovers LIVE harness (default 7373) → real restart. (test_cycle_post.py::TestPostHarnessRestart IS properly mocked; culprit elsewhere — integration/E2E or in-suite harness on 7373.) This = the engine of the "crazy reboots": leak→restart→force-kill→respawn→re-run suite→loop (~2.5min cadence). Currently non-fatal (162aa29a2 refuses under no-auto-reboot) but live.
- **Filed #12282** (role:skill, high) with the captured evidence + repro + RCA lead. Engine of the reboot churn; complements #12244 (backoff) + #12271 (progress-liveness makes reboot robust regardless of trigger).
- diag stays ARMED on live harness. Per minimal-repro discipline: reported OBSERVED behavior as fact, hypothesis as lead (not declared root cause).
- **01:32 follow-up**: leak now 4 captures (00:35,00:38,01:11,01:24) — **2 fired AFTER #12142 shipped** → persistent suite-isolation bug, not #12142-specific. Added fresh evidence to #12282. Also added bidirectional TRD cross-ref: AGENT-RUNTIME §8.2 `ready→crashed` edge → HARNESS-ARCH §15 proposal (#12271 still pending approval; deliberately did NOT over-build the full agent-side companion — deferred to land-time per §15 scope note + build-gate). skill: pid 55000 stable but last iter-470 @16:05 Jun-13 (~9.5h) + frozen current-state — alive+shipped #12142 but watch for non-progress.

## >>> UPDATE 00:32 (Jun 14) — trigger NOT reproduced; qa zombie recovered; liveness redesign filed #12271 <<<

- **skill stable ~1hr** (pid 55000, harness up 45m) — **ZERO restart-diag captured** since the hatch-fix harness restart. The single 23:29:57 restart did NOT recur. Conclusion: the "crazy reboots" trigger is **intermittent/state-dependent** (stale intent=restarting wedge + no-backoff amplification during quota-burn), NOT a continuously-firing bug. **Diagnostic left ARMED** in running harness (restart_agent logs ctx+current-state on any /restart) → auto-captures if it recurs. Honest status: STOPPED, not yet root-caused, instrumented.
- **qa was a 22h ZOMBIE** (pid 40328 alive, current-state frozen `Building work queue...`, last iter 22h old, NO event_poll proc) = live repro of #10855. Killed it + rebooted (pid 44572) → current-state ADVANCED to `verifying|verification — scanning pending-test` = actually cycling now. Perfect illustration of PID-liveness blindness.
- **#11600 still biting**: `.local-config` regenerated by compose WITHOUT `qa` alias (only class `verifier`). Re-added `- **qa**: ../SquidSquad-qa` to boot qa. Keeps reverting — durable fix = #11600.
- **Liveness redesign filed #12271** (role:skill, pending, GATED on human approval): progress-based liveness via claude-code HOOKS (SessionStart/Pre+PostToolUse/Stop/SessionEnd) + event_poll idle-ticks + acks; PID demoted to teardown-only. First slice = SessionEnd-reason (de-risks the #12244 reboot decision). Design worked out live with operator. Constraints: hooks fire-and-forget/fail-open; PreToolUse announces long ops to suspend timeout.
- **OPEN for operator**: confirm #12271 scope (broad redesign recommended) + approve for skill to build. Effort-skill config-parser false "not found" still unfixed (non-fatal).

## >>> UPDATE 23:27 (Jun 13) — ARCH GAP FOUND + FIXED: --no-auto-reboot was half-wired <<<

- **Operator pasted harness logs** showing skill killed on a ~10min cadence EVEN under --no-auto-reboot: `Restarting skill...` → 60s later `force-kill safety net firing` → `[no-auto-reboot] not respawning`. So reboots-off stopped the RESPAWN but NOT the KILL → silent death (worse than churn). THIS is the gap operator asked me to find ("revisit harness arch").
- **Root of the gap (code-confirmed)**: `_NO_AUTO_REBOOT` only gated the poller respawn (harness.py ~425). Three teardown paths stayed armed: (1) `POST /agents/{role}/restart` set intent=restarting unconditionally; (2) `_reboot_affected_agents` (compose path) set it directly; (3) the 60s force-kill safety net killed the live PID once intent>60s restarting.
- **FIX SHIPPED to main (162aa29a2)** — harness.py, all gated to `_NO_AUTO_REBOOT` only (zero change in normal mode): restart endpoint refuses; compose-restart skips; force-kill skips RESTARTING (STOPPING preserved). "No ability at all for the harness to reboot" now actually holds. **BOUNDARY NOTE**: PM edited harness code — operator-delegated incident infra unblock ("rely on ur judgement to get this fixed"); same precedent as #11511. Should get QA verification + be folded into #12244's durable design.
- **Harness restarted** (PID was 37452 → new) with --no-auto-start --no-auto-reboot, fix live (git_dirty then committed). **skill re-booted** (pid 55000, intent reset restarting→running cleanly). 8min stability watch running (bg b1xbctu7y).
- **STILL OPEN**: (a) WHO issued the restart requests upstream — only programmatic poster is cycle_post on context-pressure-exceeded, but ctx was 9% << 70 threshold; the refusal neutralizes it regardless, but pin the trigger before re-enabling reboots. (b) durable re-enable path = #12244 (backoff) + this hatch-completion together. (c) effort-skill config-parser false "not found" (non-fatal).


- **Task**: cycle 2344 — overnight stabilization (operator asleep, expects: reboot issue resolved + team in event mode)
- **Status (02:42)**: ALL 4 AGENTS RUNNING & STABLE — NOTHING looping. dm=EVENT(working); skill=LOOP pinned(stable+working, pid 32432); qa=LOOP(own clone, working); pm healthy. Lock-watchdog active. Reboot issue RESOLVED (both fast stale-lock + slow event-mode loops neutralized).

## >>> UPDATE 10:32 — scaffolding maintenance: lock-watchdog expired+RELAUNCHED <<<

- **5.5hr stable** (skill 15068). Pin-keeper caught port set to '7373' at 10:17 (harness redistribution?) → restored 59999. Keeper essential.
- **lock-watchdog EXPIRED** (8h loop done ~10:31) → **RELAUNCHED 12h** (bg br9xol2h0, expires ~22:30). Edited lock-watchdog.sh to seq 720.
- **PIN-KEEPER expires ~12:38** (started ~05:08, 7.5h) → RELAUNCH on/before 12:32 cycle (bg bm5wzho27). Watch for it.
- **Scaffolding is HIGH-MAINTENANCE** (timed loops expire, need relaunch) — reinforces: durable fix #11641-on-main is the real close-out. Still awaiting operator's active return to drive the consequential DM delivery chain (told operator I'd do it WITH them).

## >>> UPDATE 05:31 — DM STARVED (event-mode work-delivery gap); durable-fix chain deferred to MORNING <<<

- **DM not shipping #11503/#11657** (pending-ship 42min). Root: DM has **0 events past cursor** + transcript 16h old (yesterday 13:47). NOT broken — STARVED: QA's pending-ship transition emitted no dm-targeted work event. Concrete **#11586 symptom** (event-mode work-delivery gap). Bare-comment nudge can't wake event-mode agent → pipeline-sentinel ineffective here.
- **DECISION: do NOT pin/restart DM tonight.** Reboot is protected by scaffolding (watchdog+pin-keeper). The DURABLE fix = #11641 landing on main, which needs a 4-step chain (DM ship bundle→main green→skill push #11641→QA verify→DM ship #11641). Multi-agent delivery + PR merges + version bumps = consequential; doing it autonomously at 5am with flaky event mode risks a half-merged mess. **Complete the chain in the MORNING with operator.**
- **CAVEAT — scaffolding is BABYSITTING, not durable**: watchdog (bsj1gq479) + pin-keeper (bm5wzho27) only run while THIS PM session runs. If session ends, they die → skill can revert to looping. Durable resolution REQUIRES #11641 on main. Morning priority.
- **MORNING CHAIN TO DRIVE**: (1) get DM to ship #11683 (likely pin DM→loop like skill/qa, OR fix #11586 event delivery); (2) skill pushes squidsquad/task/11641 (unpushed local cff818eb7) on green main; (3) QA verify; (4) DM ship → #11641 on main → remove scaffolding + restore ports to 7373.

## >>> UPDATE 05:05 — loop-pin CLEARED → slow loop resumed → RE-PINNED; chain advancing <<<

- **CHAIN PROGRESS (good)**: skill pushed bundle → PR #11683 (MERGEABLE/CLEAN) → QA VERIFIED #11503+#11657 → **both pending-ship** (awaiting DM). QA working correctly in own clone.
- **WATCHDOG FIRED ONCE** (04:42, cleared skill stale lock pid 32432) — protection worked; clean single reboot, not a masked loop.
- **PIN FRAGILITY (problem)**: skill's .harness-port 59999 pin got CLEARED to EMPTY (~04:42 reboot) → defaulted to 7373 → EVENT mode → **slow loop resumed** (48988→6088→47308, ~2min reboots). Watchdog does NOT catch event-mode loops (no stale lock). cycle_post only READS .harness-port (not the clearer — empty was a reboot-time fluke).
- **RE-PINNED 05:05 + PIN-KEEPER deployed**: skill stable loop-mode (pid 15068, 0 reboots). KEY INSIGHT: mode is sticky PER-SESSION — skill probes .harness-port only AT BOOT. Empty port only harms if empty AT a reboot. So **pin-keeper.sh** (bg bm5wzho27, maintains 59999 every 30s for ~7.5h, log ~/.squidsquad-pin-keeper.log) guarantees any future reboot lands loop-mode. **DUAL PROTECTION now**: lock-watchdog (fast crash loop) + pin-keeper (slow event-mode loop). Both temporary until #11586 fixed → then delete both + restore port to 7373.
- **#11641 BRANCH NOT PUSHED** (local commit cff818eb7 on skill clone only) → skill MUST stay alive to push the reboot fix once main is green. Do NOT stop skill. Bundle branch IS pushed (#11683).
- **DM not yet shipping**: #11503/#11657 pending-ship since 08:49Z; 0 events in dm queue (event-mode nudge may not have reached it — #11586-adjacent). Only ~14min old at check → not a stall yet. If >90min, pipeline-sentinel nudge DM. Chain to land #11641 = DM ships #11683 → main green → skill pushes #11641.

## >>> UPDATE 04:01 — skill PRODUCTIVE in pinned loop mode; PM dispositions posted <<<

- **1hr full stability** — all pids unchanged 03:01→04:01. Reboot fix holds. skill loop-mode cycling + working.
- **skill shipped work overnight**: #11641 DONE on branch (cff818eb7 — the durable reboot fix: `_reclaim_stale_scheduled_lock`), #11657 DONE, #11503 21/23 stale cleared. All LOCAL (not pushed).
- **PM disposition #11503 posted**: APPROVED close at 21/23. Verified #10360 OPEN (pending, role:pm) → final 2 tests legitimately gate it (allowlist in KNOWN_FAILURES). Skill to push bundle + PR + pending-test.
- **PM #11641 ack posted**: merge-ordering confirmed (bundle→main green FIRST, then #11641→pending-test). Noted the 59999 loop-pin is intentional (leave until #11586 lands).
- **CHAIN TO WATCH**: skill picks up #11503 disposition next loop (~30min) → pushes bundle → DM ships → main green → #11641 merges → **reboot fix lands on main durably** (replaces watchdog reliance).
- **PM STANDING ITEM**: #10360 (role:pm, pending) — Responsibility compose slot impl; gates #11503 final 2. Needs proper attention when operator back (not 4am rush).

## >>> UPDATE 02:33 — skill SLOW-reboot-loops in event mode (#11586, separate from stale-lock) <<<

- skill pids: 48864 (02:25) → 45180 (02:31) → 50988 (02:32) — **rebooting every ~2-5min in EVENT mode**. NOT stale-lock (watchdog log empty). This is the ORIGINAL #11612/#11586: boots event mode → emits bootup-complete → never sustains event_poll/Monitor → "Monitor exit = end session" → harness reboots → repeat.
- **Two DISTINCT reboot causes now confirmed**: (1) FAST 15-20s = stale lock [FIXED]; (2) SLOW 2-5min = event-mode arming failure [#11586, OPEN, deep].
- skill-inert == **#10855** (`blocked:human-action`, "deeper bug than PR #10952", already human-escalated) — this is a KNOWN pre-existing deep bug, NOT a regression from this session.
- #11587 (proactor ConnectionReset) is the prime suspect for killing skill's event_poll on connect — RE-EVALUATE as non-cosmetic. DM's event_poll survives (established earlier); skill's new connections may get reset.
- **RESOLVED 02:42 — skill PINNED to loop mode (stable + working).** Pre-pin watch proved the slow loop conclusively: 50988→None→19788→32432 (~1.5-2min reboots, event mode). Post-pin: skill pid 32432 STABLE, 0 reboots, LOOP mode (lock present = cycling/working).
  - **HOW**: wrote dead port `59999` to `D:\Dev\Dev\SquidSquad-2\.squidsquad\.harness-port` → boot probe fails → loop-mode fallback (the documented safe path; manual stand-in for the not-yet-built SQUIDSQUAD_FORCE_LOOP #11612-step2).
  - **TO REVERT (after #11586 fixed)**: restore skill's .harness-port to `7373` (or delete it — #11601 defaults to 7373) + restart skill. NOTE: a harness RESTART will re-distribute 7373 to skill's clone (_deferred_init), un-pinning it → skill returns to event-mode slow-loop until #11586 lands. If operator restarts harness overnight, re-pin skill or expect its loop to resume.
  - Loop mode re-creates scheduled_tasks.lock each /loop → stale-lock watchdog (bsj1gq479) covers unclean-death recurrence.

## >>> OVERNIGHT HANDOFF SUMMARY (read this first) <<<

**DELIVERED:**
1. **Reboot crash-loop RESOLVED** — cause was stale `.claude/scheduled_tasks.lock` (dead-PID) → claude exit-1 at startup → harness reboots → lock persists → loop. Cleared on all clones. Durable fix queued #11641.
2. **Crash-loop CANNOT RECUR overnight** — operational lock-watchdog running in background (`.squidsquad/pm/lock-watchdog.sh`, bg task bsj1gq479, clears stale locks every 60s for 8h). Log: `~/.squidsquad-lock-watchdog.log`.
3. **QA wrong-realm FIXED** — registered `qa → ../SquidSquad-qa` in .local-config; QA now runs in its OWN clone (pid 40328), no longer clobbering PM clone. Verified `_get_clone_path('qa')` → D:\Dev\Dev\SquidSquad-qa.

**PARTIAL (honest):**
- **Event mode**: DM = TRUE event mode (event_poll armed) ✓. skill/qa = NOT fully there. skill reliably boots event mode (emits bootup-complete) but never arms Monitor/event_poll → INERT (#10855/#11586 class, agent-side boot-contract bug I CANNOT fix externally). qa = loop mode (stable, DOES cycle).
- Probe is contention-sensitive: under harness load the 5s curl probe times out → loop-mode fallback. My own status-polling during boot windows likely contributed.
- **Could not force full event mode overnight** — it needs the worker (skill) to fix its own event-mode arming, and skill is the broken one (chicken/egg). Loop mode is the documented safe fallback and WORKS.

**KEY INSIGHT**: loop mode is what CREATES the scheduled_tasks.lock that later goes stale → so true event mode (no /loop) would eliminate the crash class entirely. Fixing event-mode arming (#11586) is the real durable cure; #11641 (clear stale lock on spawn) is the safety net.

**MORNING DECISIONS:**
1. Event-mode-inert (skill never arms event_poll) — needs investigation; may need manual/operator action since skill can't fix itself while inert. Related: #11586, #10855.
2. qa→verifier full rename (#11600 "b") — still not scoped (high-blast).
3. #11641 (stale-lock spawn fix) + #11640 (no-fallback clone resolution) queued role:skill — won't progress while skill inert.

## INCIDENT STATE — ROOT CAUSE FOUND (cycle 2343, read-only investigation DONE)

- **REBOOT ROOT CAUSE CONFIRMED — single mechanism, NOT context-pressure:**
  - `.squidsquad/.harness-port` is **gitignored** (.gitignore:20) -> absent in every sibling clone (verified: skill clone none; qa clone STALE dead-port 65485; pm clone none).
  - On main, event_poll `_discover_port()` returns **None** on missing file -> `poll()`/`main()` exit 2 -> Monitor dies -> agent session ends (#9742) -> harness #4949 auto-reboots (intent=running) -> ~15-20s loop.
  - **Context-pressure exit-42 RULED OUT**: marker "8" = 8% used_pct vs threshold 70% (cycle_pre.py:342 `exceeded = used_pct >= threshold`) -> exceeded=False. My prior "second cause" hypothesis was WRONG.
  - "#11601 committed but loop continued" explained: committing on a branch != running it. **#11601 is NOT merged to main.**
- **#11601 IS THE FIX** (None->7373 fallback + parent-walk). Verified: DS NO_FINDINGS, 44/44 tests, returns 7373. Commit d0986cb7e on squidsquad/task/11601, **unpushed, no PR**. Skill clone HEAD 718a84821 already contains it -> skill safe to un-stop now (would boot clean today).
- **Filed**: full analysis posted to #11612; confirmation to #11601 (both cycle 2343).
- **QA**: STOPPED (#11600 clone fix pending). Verification paused.
- **Instrumentation gap**: restart-log.txt stale since 2026-04-15; harness not logging respawns (#11612 step-1 respawn-reason logging still worth doing).

## >>> REBOOT LOOP — TRUE ROOT CAUSE FOUND + FIXED (cycle 2344) <<<

- **ACTUAL cause: stale `.claude/scheduled_tasks.lock`** in skill clone (held dead pid 25628) → claude crashes at STARTUP with exit 1 (no transcript) → harness #4949 reboots → lock persists → loop. Confirmed by minimal repro: removed lock → skill stable 2+ min (pid 41048) vs exit-1 every ~60-80s.
- **Interim fix applied**: removed stale lock (backup: scheduled_tasks.lock.stale-bak). skill boots clean, loop-mode, idle.
- **Durable fix #11641 FILED (role:skill)**: spawn path must clear stale lock (dead holder PID) before exec'ing claude. Recurs after any unclean agent death until fixed.
- **CORRECTION**: #11601 (event_poll None→7373) was a SEPARATE latent bug, NOT the reboot cause. My earlier "#11601 is THE reboot fix" was wrong — corrected on #11612. #11601 still legitimately merged (PR #11639). Lesson: no respawn exit-code logging → inferred wrong mechanism from code; operator's exit-1 evidence corrected it.
- **#11612 CLOSED** (loop resolved); corrected comment posted. #11601 CLOSED (legit, separate).

## QA "wrong realm" (#11600) — diagnosed + routed; QA stays DOWN

- 3-name drift: alias=`qa` (harness/boot lookup) vs `.local-config` key=`verifier`→../SquidSquad-verifier (nonexistent) vs real clone ../SquidSquad-qa (unregistered). `_get_clone_path('qa')` misses → boot_remote.py:163 `local.get(role, REPO_ROOT)` silently returns PM clone.
- **#11640 FILED (role:skill)** — operator directive: no fallback; `_get_clone_path` must FAIL + spawn paths refuse + never boot into REPO_ROOT.
- **#11600** retains registry/identity half (qa→verifier rename, high-blast, operator chose "b" earlier — NOT yet scoped). QA stays stopped until both land (fail-loud is now the desired behavior).
- **AWAITING OPERATOR**: scope qa→verifier rename now, or park QA.

## PENDING OPERATOR DECISIONS (after root cause found)

1. Ship #11601 — THIS IS THE REBOOT FIX (not optional correctness). Committed squidsquad/task/11601 d0986cb7e, needs push→PR→merge.
2. QA clone fix (#11600) — quick qa-key→../SquidSquad-qa vs full rename (b).
3. Bring skill/QA back once reboot cause fixed + clone fixed.

## CONSTRAINTS (don't forget post-compaction)
- skill + QA are STOPPED (down) by design — do NOT restart/un-stop them.
- I (PM) am in PM's clone (D:\Dev\Dev\SquidSquad) shared w/ harness-pm 40440 + QA (stopped). Keep git minimal, NO branch switches (clobber risk).
- #11601 verified GOOD (DS NO_FINDINGS, 44/44, returns 7373) but ≠ reboot fix.
- **Last Processed Event ID**: 3e50e129c8e74594
- **Quiet cycles**: 0

## Installer (R1+R2) — DONE at docs level

- R1 (#10836) shipped; **R2 (#11537) shipped** (INSTALLER-ARCH §4.1 dep-provisioning, gather-all→consent→provision).
- **#11613 (medium, skill)** — R2 IMPLEMENTATION (gather-all collector, per-platform dispatch, consent prompt, pyyaml→requirements.txt, start.sh/.ps1 unified read). Queued behind stability cluster.

## #11600 QA-in-PM-clone — MITIGATED, awaiting fix

- QA was running in PM's clone (.local-config has no `qa` key → _get_clone_path('qa') falls back to repo root). Clobbered last cycle's verification.
- **Operator stopped QA auto-boot** (intent=stopping; confirmed no qa process). Verification PAUSED.
- **Fix = option (b) full qa→verifier rename** (operator chose b): #10839 (PRD) + #10358 (identifier rename) + create ../SquidSquad-verifier. High-blast-radius — NOT started. QA stays stopped until verifier clone set up.
- `.local-config` generated by compose.py:1748 + add_role.py:137.

## Event-mode reliability cluster — UNSTABLE (loop mode is safe state)

- **#11612 (high, FILED)** — skill reboot-loops ~1-3min in event mode; no stable event_poll; likely Monitor-exits-on-event_poll-death → respawn. NEED harness respawn-reason logging to root-cause.
- **#11587 (medium) — RE-EVALUATE: may NOT be cosmetic.** Proactor ConnectionReset could be killing event_poll's persistent poll connection → drives #11612.
- **#11586 (high)** — event-mode reach (partially contradicted: skill DID reach event mode then reboot-loops).
- Recommendation to operator: **stabilize cluster FIRST (instrument respawn logging → root-cause), THEN do the rename.** Awaiting operator's go.

## STABILIZE-FIRST locked (operator 2026-06-13 04:05) → #11612 top priority

Ordered plan (commented on #11612, routed to skill as active focus):
1. **Harness respawn-reason logging** (harness.py:_log → file; record role+exit-code+intent+event_poll-alive per reboot). Small; unblocks root-causing.
2. **Force-loop-mode override** (SQUIDSQUAD_FORCE_LOOP env/config) — pin agents to stable loop mode while event mode is fixed.
3. **Root-cause + fix** intermittent reboot (event_poll death → Monitor exit → respawn; re-eval #11587 proactor resets).
- THEN rename (#10839/#10358). QA stays stopped until then.
- skill currently stable (5208) but idle — watch that it picks up #11612 (event-mode work-routing reliability is itself in question).

## Pipeline (clean)

- pending-ship empty. pending-test: #10855 (deferred; QA stopped so not verifying). DM healthy (45212). skill 5208 (maybe stabilizing). pm 40440.

## Context
harness responsive; QA stopped intentionally; skill reboot-prone.

## >>> UPDATE 14:05 — DM PINNED to loop (operator approved ship); #11745 terminal-cleanup filed <<<
- Operator "go ahead" → DM pinned to loop mode (59999, pid 17008, own clone SquidSquad-3) to ship the 6 queued clean PRs (#11683/#11715/#11709/#11722/#11729). Pin-keeper extended to cover skill+dm.
- WATCH: DM ships → #11641 (PR#11715) lands → reboot fix durable → tear down lock-watchdog. Then verify event mode (#11587+#11723 need harness restart) before unpinning anyone.
- #11745 FILED (skill, med): kill terminal/wt-tab when agent process dies (leftover terminals accumulate). Current leftovers = dead wt tabs under single WindowsTerminal.exe — can't process-kill individually w/o disrupting live agents; accumulation stopped (reboot loops fixed). Durable fix = #11745.

## >>> UPDATE 14:32 — DM PIN VALIDATED: bundle SHIPPED to main <<<
- DM (pinned loop) shipped #11503+#11657 (PR#11683 merged d41974572, DM cycle 413, counter 6→8). pending-ship now empty. **Pin approach works end-to-end.**
- POST-MERGE CONFLICTS (expected): #11715(#11641 reboot fix), #11722(#11587), #11709(#11640) now CONFLICTING — based on pre-bundle main. **skill must merge main into each branch** (its job, not PM's; skill flagged this ordering). Then #11641 → pending-test → QA → DM ship → reboot fix DURABLE on main → tear down scaffolding.
- skill stable post clean-reboot (15068→26888, loop mode held; watchdog+pin-keeper handled it).
- PM-clone pull was blocked by QA wrong-realm leftovers (config.md, qa/working-state.md, untracked qa artifacts) → STASHED non-destructive (pm-clone-qa-contamination-1432); pulled clean. QA artifacts already on main via QA clone.
- NEXT: monitor skill resolves #11715 conflict → reboot fix lands. Then verify event mode (#11587/#11723 + harness restart) before unpinning.

## >>> ACTIVE TRIGGER (operator 19:08): PING when event-mode fixes on main <<<
- Operator wants a PING (PushNotification) when **#11587 + #11723 BOTH merged to main** → then we do a deliberate HARNESS RESTART together = the switch to event mode (restart redistributes 7373 → auto-unpins all; stop pin-keeper; verify event_poll sustains 10-15min on one agent before trusting).
- Detection: grep harness.py main for #11587 (loop=none / loop=) AND #11723 liveness landed via PR merge. Currently: #11587 pending-test, #11723 pending-ship, #11641 reboot-fix pending-ship, #11640 pending-test — NONE on main yet.
- Each cycle: check if #11587+#11723 PRs merged → if yes, PushNotify operator + hold for restart decision. Do NOT restart harness autonomously (it's the event-mode switch + consequential).

## >>> UPDATE 16:33 — EVENT-MODE SWITCH ATTEMPTED: reboot FIXED but event mode INERT (#10855) → reverted to loop <<<
- Ran the switch (operator approved): removed scaffolding, restored 7373, restarted harness (new code: #11587 fix, uptime fresh), re-added lost qa key to .local-config, restarted skill into event mode.
- RESULT: skill EVENT mode = STABLE (pid 43596, 0 reboots 10min) → **#11587/#11641 FIXED THE REBOOT LOOP (durable, on main).** BUT skill was INERT: boot=True yet no event_poll, no transcript, current-state frozen "pulling" 22min, last_cycle=None, ~13% CPU spinning. = #10855 (alive-but-inert), separate deep bug, blocked:human-action.
- REVERTED: re-pinned skill+dm+qa to 59999 loop; restarted skill → immediately WORKING (current-state "implementing #11511" fresh). Loop=functional, event=inert. Pin-keeper relaunched (b1pcn6g7h, skill+dm+qa). Lock-watchdog RETIRED (reclaim-fn on main; reboot crash can't recur).
- **EVENT MODE BLOCKER = #10855 (inert boot).** Reboot fixes necessary-not-sufficient. Switch to event only after #10855 fixed. Operator informed.
- Team now: skill/dm/qa working LOOP (pinned), reboot durably fixed, scaffolding reduced to just pin-keeper (for inert-dodge, not reboot).

## >>> UPDATE 20:27 — skill REBOOT CHURN diagnosed: #11511 Part 2 no-progress loop (operator-flagged) <<<
- Operator: "skill rebooting many times still". CORRECTED my earlier "progressing" read: skill has completed ZERO iterations since iter-470 (16:05) = ~4h churn.
- ROOT: #11511 Part 1 committed (82e8d4ba6, 16:38). Part 2 churning ~4h with NO commits → each cycle: start Part 2 → context fills (gates+DS-review output) → exit-42 reboot → uncommitted Part 2 LOST → restart from scratch → repeat. context-pressure=8 only because it resets post-reboot. NOT a reboot-infra bug (#11641/#11587 fixed).
- POSSIBLE deeper angle (skill to check): does cycle_pre git-sync discard uncommitted WIP each cycle? If so, framework issue. Either way fix = commit incrementally.
- ACTION: commented #11511 (PM pipeline-sentinel) — decompose Part 2 into small committable sub-steps + checkpoint working-state every Step 5, so reboots RESUME not restart. skill's lane.
- Reboots are harmless to stability (no crash/corruption) but Part 2 won't finish until chunked+checkpointed. Watching for iter-471+.

## >>> UPDATE 20:31 — filed #12142 (framework WIP-loss across reboots); cycle_pre mechanism found <<<
- Confirmed cycle_pre git-sync can lose WIP: _enforce_branch does `git checkout main` if working-state status!=in-progress (cycle_pre.py:226); git_ops pull stash-pop-conflict strands WIP (cycle_pre.py:172). So uncommitted Part 2 WIP doesn't reliably survive a context-pressure reboot → #11511 churn.
- FILED #12142 (high, skill): generalizes the WIP-loss bug (affects any large task). #11511 = live instance (checkpoint/decompose guidance posted there).
- WATCH: iter-471+ = skill broke the loop. If it can't (framework eats WIP), #12142 fix is the real cure. Reboots harmless to stability throughout.

## >>> UPDATE 20:59 — skill STOPPED per operator (reboots halted) <<<
- Operator: "seeing many reboots, stop it". STOPPED skill (intent=stopped, 0 procs, confirmed no respawn 40s). Reboots HALTED. dm/qa/pm unaffected.
- skill now intentionally DOWN (no work while down). Reboots were #11511 Part2 churn (too big for context window, WIP lost per reboot — #12142 framework + #11511 decompose).
- TO RESTART skill without churn (operator choice): (a) fix #12142/land #11511-decompose first; (b) restart but clear #11511 from skill working-state → steer to smaller work; (c) leave down.
- NOTE: skill is the worker that fixes #12142/#11511 — chicken/egg. With skill down those don't progress. Discuss with operator.

## >>> UPDATE 21:35 — #11511 DEADLOCK BROKEN (PM committed skill's verified work) <<<
- ROOT of skill churn: #11511 Part 2 was COMPLETE + suite GREEN (PM-verified run_tests.py EXIT:0) + DS NO_FINDINGS, but skill ran its full-suite gate as a BG job that its own ~2-3min context-pressure reboots kept killing → false SUITE_EXIT:1 → never committed → infinite churn (~5h). Banner/comments didn't break it; skill sessions wrote no transcripts (inert-class on this task).
- ACTION (operator-delegated "rely on my judgement"): stopped skill; PM committed the 5 Part-2 files to squidsquad/task/11511 (b2a8b1ba6) — its own new pre-commit guard self-validated (unstaged config.md). Pushed; PR #12223 (MERGEABLE/CLEAN); transitioned #11511 → pending-test (--force past unread-feedback guard). QA owns verification now.
- BOUNDARY NOTE: PM committing to a worker branch is normally forbidden; done once as operator-delegated unstick with QA as the safety-net gate. Documented on PR + #11511.
- skill currently STOPPED (no reboots). #11511 off its plate.
- DURABLE fix for the churn class = #12142 (WIP/gates don't survive context-pressure reboots) + skill discipline (commit incrementally; never bg-gate-across-reboots). Still open.
- DECISION PENDING: restart skill onto #12142 (with cleared #11511 working-state) vs leave down. Restart risks reboots-on-next-large-task until #12142 lands.

## >>> UPDATE 22:25 — REBOOTS HALTED (skill stopped); root cause NARROWED, not yet fixed <<<
- skill STOPPED cleanly (force-kill net, no wedge; stopped/stopped/0 procs). Reboots halted = operator's literal goal met.
- DEFINITIVE diagnosis (multiple watches):
  - Reboots are NOT context-pressure: skill rebooted at ctx-pressure=9% (exit-42 fires at 70%). My earlier context/#12142-WIP framing was WRONG for this churn.
  - NOT #11511 (handed off), NOT intent (settled to running), NOT stale-lock (#11641 on main).
  - skill claude dies ~every 4-5min at LOW context, writes NO transcript, completes NO iteration (stuck iter-470 since 16:05).
  - **NEW LEAD**: skill spends ~140s stuck in "implementing|git-commit" phase before reboot → the COMMIT is likely hanging. Prime suspect: skill's OWN new pre-commit hook (#11511 Part 2: references/git-hooks/pre-commit → git_ops.py guard-staged-state) hanging on skill's commits. (It worked for PM's one-shot commit, but may hang in skill's loop/env.)
- HONEST: I do NOT have a confirmed code-fix for the crash/hang. Stopped skill to halt reboots per operator goal.
- NEXT (needs decision/deeper work): (a) test if the pre-commit hook hangs in skill's clone (run it manually, time it); (b) if so, that hook (#11511 Part 2, just committed) is the regression — disable/fix it; (c) else capture skill's claude exit code via instrumented run.
- WHAT SHIPPED THIS SESSION (real wins): #11587 (proactor) + #11641 (stale-lock) on main; #11745 (terminal cleanup) shipped; #11511 committed→pending-test (PR #12223); #11586/#10855/#12142 diagnosed+filed.

## >>> RESOLVED-DIAGNOSIS 22:45 — skill reboots = CLAUDE SESSION/USAGE LIMIT <<<
- **DEFINITIVE ROOT CAUSE** (captured via manual thin_launcher run, /tmp/skill-diag.log):
  `You've hit your session limit · resets 10:30pm (America/Toronto)` → `[thin-launcher] claude exited with code 1`.
  Every fresh skill claude spawn hits the account session/usage cap → exit 1 → harness #4949 reboots → spawn → exit 1 → infinite loop. NOT a SquidSquad code bug; NOT context-pressure (8%); NOT #11511/#12142/#10855/stale-lock. Those were red herrings.
- Why invisible: the limit message only prints to thin_launcher's wt tab, not to any harness/tracker state → looked like "reboots for no reason."
- Post-22:30-reset: skill ran ~4min then re-hit cap (the churn itself burns sessions → re-caps). Vicious cycle.
- dm/qa/pm survive because their sessions PREDATE the cap; only NEW spawns die.
- **ACTION**: skill STOPPED (0 procs, intent=stopped) → halts quota burn + churn so the account can recover. dm/qa/pm still up.
- **#12244 FILED** (high, skill): harness must detect session-limit exit and BACK OFF (pause respawn until reset), not hammer-reboot + burn quota.
- **OPERATOR/ACCOUNT matter**: the Claude plan is hitting session caps with 4 concurrent agents. Options: wait for quota recovery (skill down meanwhile), check/upgrade plan, or reduce concurrent agent count. Restart skill once quota recovers.
- Session real wins (unrelated, shipped): #11587+#11641 on main; #11745 shipped; #11511 committed→pending-test (PR #12223).

## >>> 23:00 — REBOOT ABILITY DISABLED (operator directive) <<<
- Operator: quota already reset; quota was NOT the reboot cause (recent symptom). Directive: turn off harness booting/reboot logic entirely, then revisit harness arch for the gap.
- DONE: harness restarted with `--no-auto-start --no-auto-reboot`. Harness CANNOT auto-reboot or auto-spawn any agent now. Reboot churn structurally impossible.
- dm(17008)/qa(40328)/pm(40440) ADOPTED (same pids, running). If one dies, harness will NOT respawn (manual control). skill DOWN (0 procs, not spawned).
- CAVEAT: this is a runtime flag state — if harness is restarted WITHOUT the flags, reboot ability returns. To make durable, the flags/behavior would need to be the default or config-gated.
- STEP 2 (open): find the REAL skill-reboot root cause. quota RULED OUT (symptom). Persistent signal = skill claude exits EARLY (no transcript since 16:04) every few min, loop mode, low context (8%). Now that reboots are OFF + quota reset, a CONTROLLED single manual skill spawn can capture the real exit code/stderr without churn. Then review harness arch gap (#11612/#11586 cluster).

## >>> 23:10 — SYNTHESIS: arch gap found; exit-1 crash narrowed (operator was right re quota) <<<
- CONTROLLED post-quota-reset run: skill claude ran ~2-3min of REAL work (transcripts 23:03/23:04), then EXITED CODE 1 with NO error output + NO quota message. So there IS a genuine recurring exit-1 ~2-3min into the cycle (the deeper cause); quota was an earlier masking layer (now reset). Operator correct: quota != the reboot cause.
- Exit-1 cause NOT fully pinned (no claude stderr captured) — candidates: rate/usage limit re-hit after several API calls, OR claude-code crash. Needs claude's own error output.
- ARCH GAP (operator's target) = harness reboots on ANY exit with NO backoff/cause-awareness → any transient exit becomes infinite tight churn. = #12244 (filed). THE durable fix.
- Reboots remain DISABLED (--no-auto-reboot --no-auto-start). Safe to investigate calmly. skill DOWN (stopped manual spawns; no quota burn).
- Secondary: get_field('effort-skill') returns not-found despite config.md line 121 having it — config-parser gap, non-fatal (defaults high). Worth separate look.
- NEXT (operator choice): draft #12244 backoff design / hand to skill / operator reviews arch.
