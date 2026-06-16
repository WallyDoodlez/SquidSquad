# Working State

_Condensed 2026-06-15. Prior incident narrative (reboot saga, event-mode stabilization, #11505/#11511 churn, #12417 doc-reconciliation, restart procedure) preserved in iteration logs + on the forge — not re-copied here. Working-state = current active state only._

## Current — 2026-06-16 (PM EVENT-mode, operator-active session)

**Cutover #12271/#12460 — SHADOW SHIPPED, observation window NOT yet open.** Operator chose **Path B split**: shadow increment shipped as #12460 (verifier PASS cy223 → DM-merged PR #12472). Cutover flip = **#12492** (approved, HARD-GATED on a clean PID-vs-progress divergence window). **GATE: the running harness (PID 35220, booted 14:05Z 06-15, git_sha 13c68b4a) predates the shadow merge → it is NOT running shadow code → observation window has NOT started.** Opening it requires a **harness restart** onto post-shadow main (operator-approved 2026-06-16). After restart verify: agents ready, qa loop-pin (59999) intact, .local-config has qa, harness git_sha advanced. Once a clean window logs → #12492 unblocks → #12409 + qa→event-mode unblock.

**This session's filed/shipped work (2026-06-16):**
- **#12473 SHIPPED** — L1 plain-language no-op user comms (no ack/cursor jargon).
- **#12475 SHIPPED** — `--force` now bypasses the legal-transition matrix (human override can set any status; over-approvals now revertible).
- **#12451** — status-bar event-model: was over-approved without planning → re-planned with operator (Path: decouple from #12271, inline=distinct state), body rewritten to buildable scope, 7 ACs. Now legitimately `approved`, behind cutover in skill queue.
- **#12493** (approved, skill) — L2 pipeline-sentinel: detect HALT (progress-based, incl. comment-only-handoff) → investigate → unblock event-effectively → escalate. **Arch-first**: PM authored AGENT-RUNTIME §8.3 backstop subsection → **PR #12507** (open, needs merge; impl gated on it landing).
- **#12495** (open, role:pm) — `/work/assign` fiction: 32 doc-wide refs; real router is EAD `assigned-to`. Needs a careful researched purge pass (NOT rushed). PR #12507 flags it.
- **#12506** (high, skill) — **improvement subloop DORMANT across ALL agents for weeks** (pm 06-03, skill 06-01, qa 05-23, dm 04-05). Primary suspect: event-mode idle-wake gap (event_poll only nudges on real events, never idle ticks → idle agent never re-checks cooldown). Also dm GATED on #10540.
- **#10540** — dm's improvement-scan gate blocker; "parked on PM routing", NOT dm-actionable. **PM TODO: route it** (unblocks dm scans; contributes to #12506).

**Routing fix verified:** #12442 works — DM auto-shipped many items this session with zero manual nudges. Manual dm-nudge workaround RETIRED. PM woke skill on #12460 via injected `assigned-to` (the real direct-wake mechanism).

---

## Prior — 2026-06-15 19:30 (PM EVENT-mode boot, fresh reincarnated session)

**Mode**: HYBRID — skill/dm/**pm** EVENT (:7373), qa LOOP (pinned 59999, intentional until #12409). This PM is a fresh event-mode session (reincarnated per operator; prior was inline). Boot drain: cursor was `null` on the harness (boot @14:05Z 06-15); migrated legacy id `3e50e129c8e74594`, fast-forwarded through 80 stale-but-forge-reflected events to head — all no-ops. Cursor now current.

**Harness**: healthy, up since 06-15 14:05Z (git_sha 13c68b4a), all 4 agents `running`. Probe :7373 OK.

### Pipeline state at boot (all healthy, no stalls)
- **skill** — IN-PROGRESS on **#12460** (#12271 slice-4 CUTOVER, shadow-mode strategy). Critical path: when it lands, #12271 completes. Queue behind: #12451, #12450, #12420, #12419 (all approved).
- **dm** — idle; all recent ships done + DM-merged cleanly.
- **qa (verifier)** — LOOP mode, no pending-test waiting.
- **pm (this)** — idle of active task. 3 long-parked coordination items still labelled in-progress: #11092, #11053, #9968 (see below). No churn.

### Shipped since last working-state (06-15, all clean)
- **#12271 slices a/b/c ALL SHIPPED**: #12418 (SessionEnd-reason), #12443 (activity-heartbeat), #12458 (pause-aware guard). Only slice 4 #12460 (cutover) remains → owned by skill, in-progress.
- **#12442 SHIPPED** (DM event-mode auto-route fix) — **VERIFIED WORKING**: dm auto-shipped 5 items post-fix (#12418/#12442/#12443/#12458/#11613) with ZERO manual PM nudges. **Manual dm-nudge workaround RETIRED.** (Resolves the standing "verify next pending-ship auto-routes" action.)
- **#11613 SHIPPED** (installer dep auto-provisioning, PR #12471, DM-merged) — matches HEAD. Counter 23→24, bump held.

### Active threads (PM-relevant)
1. **#12460** (cutover) — skill front-loading. PM coordination-watch only; completes #12271 on land.
2. **#11092** — was "parked behind in-flight harness-arch reconciliation (#12417)". **#12417 MERGED** → #11092 may now be UNPARKED. Operator-paced; revisit when #12460 settles. Status label in-progress (parked).
3. **#11053** — agent-spawn substrate (v2 §4.6 assemble). Phase 1 design operator-locked; Phase 2 = #11570 (role:skill). PM stays coordination (Phase 2.2 ship sign-off, 2.4 prompt refinement). In-progress (coordination-hold).
4. **#9968** — runtime sub-skill resolution; gates further composite reduction (#11049 AC3). In-progress (parked).
5. **#10855** — DEFERRED behind #12271/#12460 (operator). Parked; revisit/close after cutover. Status label in-progress (parked).
6. **DS finding #4** (`/work/assign` fictional endpoint) — doc-sync was GATED on #12442. **#12442 now SHIPPED** → doc-sync UNGATED. Real routing = EAD `assigned-to` + harness `role:*` rewrite; `/work/assign` should be dropped from HARNESS-ARCH §3/§4.3 + AGENT-RUNTIME §8.3/§5.2. Candidate next PM doc task once #12460 cutover noise settles.

### PM approved queue (operator-paced post-cutover, NOT yet actionable)
- #10837 HARNESS-ARCH alignment PRD (needs DS re-audit before pickup)
- #10838 VAULT-ARCH alignment PRD
- #10839 cross-TRD role→alias rename PRD (needs DS re-audit before pickup)
- #10690 wiki-link rework (gated on E7)

### Standing notes
- #11600 (qa `.local-config` wipe on compose) — durable fix #12380 shipped; watch next compose/restart.
- "cycle NNNN" commit label drift is decorative; anchor on `iter-N` + date.

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible — no prior scan this session)
