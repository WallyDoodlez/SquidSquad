# Working State

- **Task**: cycle 2344 — overnight stabilization (operator asleep, expects: reboot issue resolved + team in event mode)
- **Status (02:25)**: ALL 4 AGENTS RUNNING & STABLE — pids constant over 40s, NOTHING crash-looping. QA now in OWN clone. Lock-watchdog active.

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
