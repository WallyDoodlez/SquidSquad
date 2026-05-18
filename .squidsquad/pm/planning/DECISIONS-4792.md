# #4792 Phase 2 — Decisions Log

Locked decisions from the 17-question discussion phase walkthrough with the
human PM. Inputs: `RESEARCH-4792-lifecycle-audit.md`. These decisions are
the source of truth for drafting `CONTEXT-4792.md` and `TEST-PLAN-4792.md`.

## Architectural Principles (load-bearing)

- **Harness is the sole gatekeeper of agent process lifecycle.** No
  parallel control paths. Per memory `feedback_harness_sole_lifecycle.md`.
- **Blast-radius minimization.** Preserve current /loop-mode behavior
  byte-identical wherever possible. Cleanup ships behind regression checks.
- **L1–L4 only.** All agent instruction changes flow through compose stack
  fragments, never ad-hoc instruction files.

## Q1–Q17 Locks

### Q1 — Operator entry-point convergence — **Option A**
`squidsquad_cli.py` becomes the canonical operator interface. `start_team.py`
becomes a thin shim (existing commands still work, route through canonical).
`boot_remote.py main()` removed (file stays as harness-internal library).

### Q2 — `boot_remote.py` survival — **Option A**
Kept as harness-internal library (no `main()`, no CLI flags). Imported only
by `harness.py`. All sentinel-file reads removed during cleanup (they were
vestigial anyway per research).

### Q3 — `reboot_agent.py` survival — **Option B**
Gut to just `_kill_process` and `_read_claude_pid` utility helpers. Keep
file in place to minimize blast radius. Follow-up cleanup task (Phase 6+):
rename to `process_ops.py` and consolidate other process utilities.

### Q4 — `health_check.py` purpose — **Option B**
Keep as offline-fallback, strictly read-only. Remove `.stop` read
(line 304) and `.health` read (line 329). PID-only liveness checker.
Follow-up cleanup task (Phase 6+): migrate /loop `cycle_pre` callers to
thin `GET /status` helper, then delete `health_check.py`.

### Q5 — Stop-the-team UX — **Keep both endpoints**
Both `POST /agents/{role}/stop` AND `POST /agents/all/stop` stay.
Web-UI vision (per `project_harness_vision`) requires both.

### Q6 — PID-based liveness vs heartbeat events — **Option A**
Stay PID-based. No change to liveness detection mechanism in #4792.
PID is OS truth; heartbeats are application-layer signal. Future task
(Phase 7+, possibly tied to #3963 Web Dashboard) can add heartbeat-based
hang detection if needed.

### Q7 — #7693 fix mechanism — **Option D + (C-fallback)**
**Primary mechanism:** Agent self-quits via `/quit` after `cycle_post.py`
exits 42. Instruction-level fix added to L1–L4 fragments.

**Safety net:** Harness force-kill timeout — if **intent ∈ {STOPPING, RESTARTING}**
AND `.claude-pid` alive AND >60s since intent set, harness force-kills the
claude PID. (Scope extended to RESTARTING per PM lock 2026-05-18 after
deepseek R1 review of CONTEXT-4792.md flagged the ambiguity. Same
stuck-agent failure mode applies to both intents; no reason to differentiate.)

Parity with event mode (both modes terminate via agent self-quit).
**This fix closes #7693.** Sole authority preserved (harness only
force-kills stuck cases).

### Q8 — Harness PID check in `cycle_pre` — **Option B**
Agents run autonomously; no required harness check at cycle start. Add
`harness_status: "reachable" | "unreachable"` informational field to
`cycle-input.json` so agents can flag disconnect in iteration summary.
Sole-authority preserved at lifecycle-control layer; work execution
doesn't need handshake.

### Q9 — `.booting` sentinel — **Option A**
Keep as harness-internal boot-slot lock. Not split-brain (single writer,
single reader, harness-internal). Same shape as `.claude-pid`. The
"no sentinels" principle applies to split-brain control paths, not
single-writer mutexes.

### Q10 — Crash recovery semantics — **Confirmed**
`.harness-state.json` is the SOLE crash-recovery mechanism for lifecycle
intent. Test plan covers 6 scenarios:
1. Harness crash after `POST /stop` set intent
2. Harness crash during force-kill timeout
3. Agent crash between intent set and `cycle_post`
4. Both simultaneous crash
5. `.harness-state.json` corrupted (operator intervention required)
6. `.harness-state.json` deleted (defaults restored, intent lost — same as
   fresh install)

### Q11 — Distribution/packaging audit — **Lock as test-plan checklist**
- `installer-files.txt` reflects post-cleanup file inventory
- `packages/cli/package.json` exposes only canonical entry points
- Operator muscle memory preserved (`start_team.py boot` still works via
  shim)
- No new CLI entry points exposed for `boot_remote.py main()` or
  `reboot_agent.py main()`

### Q12 — CLAUDE.md sub-skill updates — **Lock as deliverable**
Fragment edits flow through compose stack. Recompose all four roles after
fragment changes. Byte-identical /loop regression check per role. Specific
updates:
- `references/sub-skills/common/agent-lifecycle.md` references
  `squidsquad_cli.py` (canonical per Q1), not `start_team.py` directly
- Remove `.health` legacy-fallback mentions in role CLAUDE.md files
  (skill 1411, pm 1979, qa 1174, dm 1087 per research §12)

**Coordination with #8697:** if #8697 ships first, #4792 edits both
`common-loop/` and `common-events/` trees. If #4792 ships first, #8697
migrates cleaned content forward.

### Q13 — Upgrade path — **Option A**
Harness cleans up legacy sentinel files (`.stop`, `.restart`, `.health`) on
first boot post-upgrade. Self-healing, automatic, idempotent (no-op on
subsequent boots).

**Downgrade-safety AC:** `.harness-state.json` is authoritative intent
record; legacy sentinels are non-load-bearing parallel paths. Downgrade
test in test plan verifies old code honors intent via JSON. CHANGELOG
note: "Downgrade safe; legacy sentinel files no longer load-bearing."

### Q14 — #8692 (singleton enforcement) interaction — **Locked, out of scope**
`.claude-pid` rewrite semantics are OUT OF SCOPE for #4792. Specifically
unchanged:
- Writer: `thin_launcher.py` (single writer)
- Atomicity: `.tmp` + rename
- Cleanup: thin_launcher removes on clean exit

Byte-identical regression AC: `thin_launcher.py:66-83` `_check_singleton`
behavior is identical before and after #4792.

### Q15 — `diagnostics.py` status — **Locked, out of scope**
Stays as pure API client. No new file reads, no subprocess calls, no
direct sentinel touches. Byte-identical regression check.

### Q16 — Backward-compat window for stale-file parsing — **Option A**
Delete all stale-file parsers (`.health`, `.pid`, `.stop`, `.restart`)
immediately. No warn-and-ignore window. Q13-A's harness-boot cleanup is
the safety net; old code that still writes legacy files is harmless
because `.claude-pid` (the actual liveness signal) is preserved per Q14.

### Q17 — `start_team.py` primary-vs-clone path bug — **Locked**
Bug vanishes with cleanup (`_write_stop` is deleted). No design decision
needed. Test plan adds primary-vs-clone path audit:
- All sentinel-file write paths being removed → audit history was
  correctly clone-pathed
- All sentinel-file write paths being kept (`.claude-pid`, `.booting`) →
  verify clone path used
- Any new path code introduced by cleanup → must use clone path

## Side-Decisions (Phase 6+ tech debt to file)

- **Rename `reboot_agent.py` → `process_ops.py`** and consolidate other
  process utilities (Q3 follow-up)
- **Migrate /loop `cycle_pre` health-check callers** to thin `GET /status`
  helper, then delete `health_check.py` entirely (Q4 follow-up)
- **Add event-bus heartbeats for application-layer hang detection** when
  needed; likely Phase 7+ tied to #3963 Web Dashboard

## Bug Closures Triggered by #4792

- **#7693** (Context-pressure restart does not respawn agent) — closes
  when Q7's mechanism ships
- **#8689** (Harness restart endpoint does not immediately reboot idle
  agents) — adjacent; may also close depending on exact restart-endpoint
  implementation

## Hard-Prereq Relationship to Phase 5

- #4792 + #8692 together gate any per-role flip of `event-driven: yes`
- #4792 does NOT block Phase 5 bundle implementation
- Coordination with #8697 covered in Q12 (fragment updates)

## Next Steps

1. Draft `CONTEXT-4792.md` synthesizing these decisions + research
2. Deepseek review of CONTEXT-4792.md
3. Draft `TEST-PLAN-4792.md`
4. Deepseek review of TEST-PLAN-4792.md
5. Transition #4792: planning → planned
6. Resume Phase 5 walkthrough (tasks 4-6: #8694, #8700, #8704)
