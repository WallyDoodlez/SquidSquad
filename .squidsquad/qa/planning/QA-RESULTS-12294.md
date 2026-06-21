# QA-RESULTS-12294 — Keep .claude-pid authoritative across harness restart

**Verdict**: ✅ **PASS — zero gaps**. All 4 ACs verified with live evidence. → `pending-ship` (DM).
**Issue**: #12294 (type:issue, severity:medium, role:skill). **PR**: #13033 (branch `squidsquad/task/12294` @ `93473c563`, MERGEABLE/CLEAN, `Closes #12294`).
**CQ**: none — deterministic harness code, no LLM-consumed instruction change.
**Verified in**: isolated git worktree off `origin/squidsquad/task/12294` (no working-state-revert hazard).

## Implementation (design C + A, dependency-free)
- **A (read-side image verification)** — `process_utils.is_claude_process_alive(pid)` = alive AND image is claude. `update_health` swaps bare `_is_process_alive` for it on both the in-memory PID and the `.claude-pid` fallback; whole resolution block wrapped in try/except that degrades only THIS agent to "dead this poll" on any fault (DS-c3 Finding 1 — never abort the fleet poll). `thin_launcher._check_singleton` likewise image-verifies (closes recycled-PID singleton hole). `thin_launcher._win32_list_descendants` refactored to share `_win32_all_procs()`.
- **C (write-side self-heal)** — `reboot_agent.write_claude_pid` (atomic `.tmp`+replace, rejects non-positive/bool pid, swallows OSError). `update_health` writes `.claude-pid` back from in-memory truth when missing/divergent, gated on `intent=RUNNING` (DS-c3 Finding 5 — never race thin_launcher's spawn-time write during restart/deploy).

## AC walk (live evidence)

**AC1 — reconcile from real process, not stale `.claude-pid`** ✅
- `update_health` (harness.py:589-633) image-verifies the in-memory PID, then the file PID, adopting the file PID only when it image-verifies live.
- Live probe: `is_claude_process_alive` on 4 real teammates (dm/pm/qa/skill) → all True, image='claude.exe'.
- `test_file_pid_adopted_when_image_verified` (TC-9): in-mem dead + file PID live claude → adopt, keep running.

**AC2 — live agent never mis-detected dead/unknown post-restart** ✅
- Undetermined image (`image_name_for_pid`→None: snapshot fail / non-/proc platform) falls back to plain liveness. Live probe: forced image=None on a live PID → `is_claude_process_alive`=True (never mis-reclaim an uninspectable live agent).
- Mechanism confirmed load-bearing: `save_state` persists `claude_pid` (harness.py:447), `load_state` restores it (harness.py:1423) — so a restart restores the in-memory PID and image-verify confirms it even with a stale/missing file; write-back self-heals `.claude-pid` for the next restart.
- Fleet-poll try/except degrades a single faulting agent, never the whole poll.
- Regression `test_ac4_i` / `test_ac4_iii`: stale-dead and missing `.claude-pid` + live recorded PID → running, `boot_agent` NOT called (not respawned).

**AC3 — stale/recycled holder reclaimed, not trusted** ✅
- Live probe (the heart of the fix): `is_process_alive(python.exe PID)`=True (bare liveness would TRUST a recycled PID) but image='python.exe' → `is_claude_process_alive`=False → reclaimed. Dead PID (999999): both False.
- `test_ac3_recycled_nonclaude_pid_is_reclaimed` (TC-8): live non-claude PID at `.claude-pid` → reclaimed (treated dead) → respawned, not masked; write-back skipped.

**AC4 — regression test (restart w/ stale/missing `.claude-pid` + live claude.exe → detected running, not respawned)** ✅
- `test_ac4_i_stale_file_live_recorded_in_state_stays_running` + `test_ac4_iii_missing_file_live_recorded_in_state_stays_running` assert `boot_agent.assert_not_called()` (the original bug's failure mode = respawning a live agent) + `.claude-pid` self-healed. Drives the real `update_health` path. Would have caught the original bug.

## Test execution
- `test_12294_claude_pid_authoritative.py` + `test_process_utils.py` + `test_thin_launcher.py` → **94 passed**.
- `test_harness.py` + `test_12460_progress_liveness.py` → **314 passed**.
- Independent live probes (TC-1..TC-5) on the running Windows fleet → all expected.
- **No-regression**: full `tests/run_tests.py static` (fail-closed #12408, junit-backed) → **`PASS — 4787 gated test(s) passed, 0 failures, 0 errors`**, exit 0.

## Scope (verifier judgment — legitimate, not a gap)
- **Never-recorded-orphan** (live claude.exe with PID recorded nowhere — `.claude-pid` AND harness state both empty) split to **#13034**. This is a distinct root from the stated ACs (which concern reconciling the FILE against the real process when the PID is recoverable from state — delivered). Recovering a never-recorded orphan needs psutil cwd/cmdline discovery (a human-gated new dependency); terminal_pid descendant re-resolution can't substitute on Windows because `cmd /c start` exits and detaches claude.exe. Properly disclosed + tracked → not a gap.

## Delivery
- Merge **deferred to DM** (`Closes #12294`; DM owns ship + counter — QA-merge would auto-close and skip DM). Counter NOT bumped (DM owns).
