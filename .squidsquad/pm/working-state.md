# Working State

## >>> HARNESS RESTART TRIGGERED 2026-06-28 (operator-directed) — RESPAWNED PM: VERIFY THIS FIRST <<<
- **Why:** running harness was sha 2cc9e058, up ~28.5h, **117 commits behind origin/main**. Today's harness.py fixes were MERGED-BUT-DORMANT: #12492 progress-liveness cutover (zombie auto-reboot), #13283 (auto-reboot never-resolved-PID agent stuck at status=starting), #13170 (/merge fail-closed), #13215 (deploy-pull dirty-clone), #13255 (self-event exclusion), #13236 (stdout hardening). Restart loads current code → activates them.
- **Action taken:** PM (coordinator) POSTed /restart per harness-restart sub-skill. Whole team respawns on current origin/main (HEAD was c8ea3da08 at trigger).
- **POST-RESTART VERIFICATION (do from FACTS, respawned PM):**
  1. `GET /status`: all 4 aliases (pm/dm/qa/skill) status=running + bootup_complete=true; harness sha should now be current (NOT 2cc9e058) + low uptime.
  2. All agents event-mode (not polling fallback).
  3. Progress-liveness now LIVE: confirm #12492 code is in the running harness (sha advanced past b01d8fbae). The earlier wedges (qa-frozen, skill-never-came-up) should now auto-recover without manual boot_remote.
  - If agents do NOT come back → harness was one-shot launcher (not supervised) → operator must relaunch (restart-harness.* / squidsquad_cli start).
- **Still-open HIGH harness gaps after restart:** #9888 (singleton not enforced / orphan accumulation), #9874 (harness internal arch review, planning). #13263 (behind-clone merge sibling) at pending-human-review — operator bump pending.



_Condensed 2026-06-26 ~22:28 local (PM EVENT-mode fresh boot on new fleet restart; Verbose Mode ON). Prior 2026-06-22 narrative in iteration logs + forge._

## >>> THIS BOOT 2026-06-26 ~22:28 local — fresh PM EVENT session <<<
- Harness :7373 reachable (EVENT mode). GH OK. **Verbose Mode = ON** (full-firehose narration).
- New fleet restart in progress (harness uptime ~22s at first probe): dm running+bootup=True; pm (me) + qa mid-boot; skill was status=starting (still spawning).
- Boot drain from cursor `5c9ef30764cd2115` = **0 events** (cursor already at head). No legacy cursor line → no migration.
- Working-state was 4 days stale → did fresh forge read for pipeline truth.
- Driver `.subloop-driver.json` = armed:true, scan_count:0, last_run 2026-06-21T23:54Z (throttle preserved). Session cron **464dc7c3** (6,36 * * * *) created this boot. bootup-complete emitted.

## >>> OPERATOR INLINE REQUEST — handled this boot <<<
- Operator (inline ~22:28): "kill agent for me when you are loaded" → clarified via AskUserQuestion: target=**skill**, semantics=**kill + respawn**.
- Action: `POST /agents/skill/restart` → success:true, immediate:false (skill was mid-spawn → graceful path). Intent flipped to **restarting** — BUT respawn never fired (force-kill net had no claude_pid; auto-reboot is_dead never tripped).
- **ROOT CAUSE:** skill had been wedged in `status=starting` since fleet boot — its original spawn never resolved a claude PID. Both terminal_pid (17304) AND claude_pid (None) were dead; harness state stale. PID-liveness blind to a never-came-up spawn (the #12271 progress-liveness gap).
- **RECOVERY (PM stall-recovery, sanctioned):** `boot_remote.py --dry-run --role skill` → safe ("no PID file found") → `boot_remote.py --role skill` → spawned. **VERIFIED skill now healthy: status=running, claude_pid=24532, bootup=True.** Kill+respawn complete end-to-end.
- **POSSIBLE FOLLOW-UP (offered to operator, not yet filed):** bug vs role:skill — "spawn dies before claude-PID resolution → harness auto-reboot never fires" variant of #12271. Awaiting operator go.

## >>> QA WEDGE RECOVERED ~01:10 local 2026-06-27 <<<
- QA (verifier) **wedged-alive ~48min**: claude.exe (45192) + event_poll sidecar (27492) BOTH alive, bootup=True, but frozen — `last_dispatch_at` (38m) > `last_activity_at` (48m) = dispatched work, zero tool-call response; 3 items piled in pending-test, none picked up. PID-liveness blind (the #12271 class — exactly what operator just GO'd).
- Diagnosed from 3 facts (process-alive + sidecar-alive + dispatch>activity). A fresh nudge wouldn't help (session frozen, not transport). Recovery: `POST /agents/qa/restart` → immediate path, killed 45192. **VERIFIED recovered: fresh pid 50876, bootup=True, active (tool-calls flowing).** 3rd wedge-class incident this session-history (qa-zombie / skill-never-came-up / now qa-frozen) — reinforces the #12271 GO.
- **WATCH**: confirm QA drains pending-test (#13255/#13215/#13172/#13170) → pending-ship on next wake; if it re-wedges, escalate.

## >>> SEV-1 (#13271) ROOT-CAUSE CLUSTER — session 2026-06-27 <<<
- **#13271** SHIPPED (behind-count merge guard, git_ops.pr_merge >50). **#13285** SHIPPED (post-merge scope-audit + auto-revert, mechanism-agnostic). **#13286** SHIPPED (dev sync-before-start/before-merge mechanics).
- **#13291** (L1 universal sync norm: be-current-before-integrate / merge-never-overwrite) — operator-confirmed L1-universal placement; un-held → **pending-test** (QA verifying). Was held then resumed.
- **#13287** (developer-domain sub-layer: 'a worker isn't always a dev') — **PARKED** (pending, role:pm). Separate arch question; revisit on own merits.
- **#13277** (TUI README) — un-held → approved (dm).
- **#13298 (role:pm) — DONE + CLOSED 2026-06-27.** #13291 shipped → gate cleared → picked up + completed in one DS-audited pass. Landed commit **ac2b5af78** (PM doc lane): HARNESS-ARCH §4.5.1 (git_ops guards #13271/#13285) + v30; AGENT-RUNTIME §5.1 L1-norm callout (#13291); COMPOSE-ARCH #13287 open-question. DS-audit REVIEW-13298-DEEPSEEK.md (PASS-WITH-FIXES, both applied; code-cross-checked). Task=none now.

## Pipeline (forge-verified ~22:30 local)
- **pending-test: 0 · pending-ship: 0 · pending-human-review: 0 · untriaged externals: not yet swept (team mid-boot).**
- **work_queue (role:pm approved): #10690 ONLY — GATED** on E7 (#10686 not shipped). Not pickable. No autonomously-actionable PM work this boot.
- **in-progress (pm, intentional parked coord-holds — NOT stalls):** #11092, #10839 (DS-re-audit gated), #9968.

## >>> OPERATOR DECISIONS — this session <<<
- **#12271 liveness cutover: OPERATOR GO (2026-06-27, inline).** Decision LOCKED + recorded on #12271. Transitioned pending-human-review → in-progress (gate cleared, wakes skill). **#12492 (cutover) unblocked.** Asked skill to confirm sequencing: heartbeat hooks (#13213) land first ✓; **Slice B (intent=deploying force-kill backstop) must exist before the PID-off flip** — flagged to skill to file/confirm B's disposition. Cutover stays behind verification ACs. NO LONGER an advertise item.
- TUI task = **#12801** (Harness TUI bottom action bar w/ reboot, busy-aware) — in-progress (skill); operator asked its location this session.

## Improvement Scan
Status: idle this boot. Driver armed + live cron 464dc7c3. Throttle last_run 2026-06-21T23:54Z preserved.
(This boot: 0 cared events; handled operator inline skill-kill; pipeline clean; no actionable PM work; armed driver + live cron; refreshed stale working-state. Idle/listening.)
