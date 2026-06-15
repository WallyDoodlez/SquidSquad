# Working State

_Condensed 2026-06-14. Prior incident narrative (reboot saga, event-mode stabilization, #11505/#11511 churn diagnosis) is preserved in iteration logs iter-695..698 and on the forge — not re-copied here. Working-state = current active state only._

## Current — 2026-06-14 (PM inline session: DS audit + HARNESS-ARCH doc reconciliation)

**Mode**: HYBRID — skill/dm EVENT (7373), qa LOOP (pinned 59999), pm inline. Verified this session via OS process check: 4 `claude.exe` + 2 `event_poll` alive (pm/dm/skill/qa). **verifier clone absent** — no `pending-test` work waiting, so no boot (stall-recovery-only rule). `health_check.py` snapshot is stale this session (harness not updating it) — trust process check, not the 👻 readings.

**Reboot saga: CLOSED** — all fixes shipped (#12282 trigger/test-isolation, #12244/#12293 backoff, #12342 EAD routing, #12380 compose-alias). qa loop-pin (59999) is INTENTIONAL until #12409 (qa event-mode stability) lands.

### Active threads
1. **#12417 — MERGED 2026-06-15** (merge commit 29643ca8). HARNESS-ARCH (v24–v26) + AGENT-RUNTIME event_poll/`.claude-pid` reconciliation on main. Full work-discovery flow completed: research → draft → human review → DS re-audit (step 4) → cross-ref (step 5) → "all okay" → merge. PM merged under explicit operator authorization (boundary deviation noted on PR). **Descriptive-corrective → no new impl tasks spawned** (docs now match existing code). PM merged (boundary exception, operator-authorized).
2. **#12271** — **APPROVED + SLICED 2026-06-15** (operator "go ahead"). Umbrella, status:approved. Slice **(a) #12418 SessionEnd-reason hook** FILED + approved → skill. Slices (b) activity-heartbeat hooks, (c) pause-aware guard, (d) retire PID-poll — sequenced, file as predecessors land. Locked scope: liveness = activity-heartbeat + pause-guard; PID teardown-only; no new PID-reporting.
3. **#12363** — `/T` teardown fix: skill ENGAGED (RCA confirmed, fix contained: taskkill /T + os.killpg in `_kill_process`, all 3 paths via shared helper). Queued by skill as front-loaded pickup. medium sev. No PM action.
4. **#11505** — CLOSED 2026-06-15 as superseded-by-#10025 (operator-confirmed). Scope handed to #10025. Removed from 06-12 bundle.
5. **#12300** work-discovery → L2 — DEFERRED (the process just proved itself on #12417).
6. **DS finding #4** (`/work/assign` payload) — small follow-up doc task, NOT filed yet.

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
