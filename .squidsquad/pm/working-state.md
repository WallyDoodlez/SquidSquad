# Working State

_Condensed 2026-06-14. Prior incident narrative (reboot saga, event-mode stabilization, #11505/#11511 churn diagnosis) is preserved in iteration logs iter-695..698 and on the forge — not re-copied here. Working-state = current active state only._

## Current — 2026-06-14 (PM inline session: DS audit + HARNESS-ARCH doc reconciliation)

**Mode**: HYBRID — skill/dm EVENT (7373), qa LOOP (pinned 59999), pm inline. Verified this session via OS process check: 4 `claude.exe` + 2 `event_poll` alive (pm/dm/skill/qa). **verifier clone absent** — no `pending-test` work waiting, so no boot (stall-recovery-only rule). `health_check.py` snapshot is stale this session (harness not updating it) — trust process check, not the 👻 readings.

**Reboot saga: CLOSED** — all fixes shipped (#12282 trigger/test-isolation, #12244/#12293 backoff, #12342 EAD routing, #12380 compose-alias). qa loop-pin (59999) is INTENTIONAL until #12409 (qa event-mode stability) lands.

### Active threads awaiting operator
1. **Draft PR #12417** — DS audit BLOCKER #1: HARNESS-ARCH event_poll lifecycle reconciliation (§3 / §7.2 steps+diagram / §7.5+§10 dropped `event_poll_pid` / §11 / §14 → corrected to *agent-Monitor-spawns-event_poll; harness tracks only `claude_pid`; recovery = Monitor-exit→session-end→claude-PID-death→respawn*). At work-discovery **human-review gate**. After review: step 4 DS re-audit on modified doc → step 5 cross-ref vs AGENT-RUNTIME → operator "all good" → slice worker task(s). Likely root cause of #12363 (orphaned event_poll) — cross-link after approval.
2. **#11505 close** — PM ruling posted (verified): capability-check retirement is one unit owned by **#10025** per in-tree docs (manifest.md:149, sub-skill-catalog.md:143); AC1 (`capabilities/` dir) already done → no independent deliverable. Recommend close-as-superseded; flagged to operator because #11505 is in the 06-12 bundle (#11503 + #10836 R1). Handoff scope captured on #10025.
3. **#12271** liveness scope — pending operator approval (activity-heartbeat + pause-guard; SessionEnd-slice first). **Ticket-slicing HELD until #12417 lands.**
4. **#12300** work-discovery process → L2 — DEFERRED until harness-arch changes land (applying the principle now via #12417).

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
