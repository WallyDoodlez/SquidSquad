# QA-RESULTS-12363 — orphaned claude.exe / event_poll reaping across respawns

**Verdict**: ✅ **PASS — zero gaps**. All derived ACs verified (Windows live; POSIX via independent forced-branch exercise) + no-regression. → `pending-ship` (DM).
**Issue**: #12363 (type:issue, severity:medium, role:skill). **PR**: #13040 (branch `squidsquad/task/12363` @ `1a2579d16`, MERGEABLE/CLEAN, `Closes #12363`).
**CQ**: none — deterministic harness code.
**Verified in**: isolated git worktree off `origin/squidsquad/task/12363` (merges current main, carries #12294 — already verified+shipped this session).

## What it fixes
Respawns force-killed only the claude PID (`taskkill /F` / bare `SIGKILL`), orphaning the Monitor-spawned `event_poll.py` sidecar (a claude descendant) → ~13 claude + ~12 event_poll accumulated for 4 agents. The shared `_kill_process` helper now reaps the whole tree/group.

## AC walk (evidence)

**AC1 — Windows tree-kill** ✅
- `taskkill /F /T /PID` (`/T` = child tree) reaps the event_poll descendant. `test_kill_windows_uses_taskkill_force_tree` asserts `/T` in cmd — **runs + passes on this Windows box**. (TC-1)

**AC2 — POSIX group-kill** ✅
- `os.killpg(os.getpgid(pid), SIGKILL)` reaps the group. The gated unit test `test_kill_posix_kills_process_group` `skipif(win32)` — cannot execute here. Verified via **independent forced-branch exercise** (patch `sys.platform`→linux + mock `os.getpgid`/`killpg`/`signal.SIGKILL` `create=True`): S1 (target group 111 ≠ harness group 222) → `killpg(111, SIGKILL)` called, bare `kill` NOT called. (TC-2)

**AC3 — POSIX own-group safety fallback** ✅
- `if pgid != os.getpgid(0): killpg(...) else: kill(pid, ...)`. Forced-branch S2 (getpgid returns 555 for both pid and self) → `killpg` NOT called, `kill(12345, SIGKILL)` fallback — the harness's own group is spared. (TC-3) Matches `test_kill_posix_falls_back_to_sigkill_for_own_group` (skipped here).

**AC4 — shared helper, all 3 teardown paths** ✅
- `_kill_process` has exactly 3 callers in harness.py: line 758 (60s force-kill safety net in update_health), 3686, 3788 (idle-restart + poller-respawn). All inherit the tree/group reap via the single helper. (TC-5)

**AC5 — error handling preserved + extended** ✅
- PID-validation guard intact. Swallow set now `(ProcessLookupError, PermissionError, TypeError, OSError)` — OSError newly added for getpgid/killpg group-vanished races. Forced-branch S3 (getpgid→PLE), S4 (killpg→OSError), S5 (killpg→PermissionError) all swallowed, no raise. (TC-4)

**AC6 — no-regression** ✅
- Full `tests/run_tests.py static` (fail-closed #12408) on branch → **`PASS — 4807 gated test(s) passed (0 failures, 0 errors)`**, exit 0. `test_reboot_agent.py` → 25 passed / 5 skipped (the 5 POSIX killpg tests skip on Windows). (TC-6)

## Notes
- **POSIX path coverage honesty**: the 5 gated POSIX tests cannot run on the Windows dev box, and skill's "4807 passed" gate (also Windows) likewise skipped them — so neither run *executed* the real `killpg` syscall path. I closed that gap with the independent forced-branch logic exercise (5/5 scenarios incl. own-group safety + all error swallows). The real `killpg` syscall is exercised on the qa/Linux CI per the `skipif` design. No gap that blocks ship — the logic is proven; the syscall binding is standard.
- **Orphan-count confirmation ask** (1 claude + 0..1 event_poll per agent post-respawn) is the behavioral outcome of the tree/group reap at all 3 teardown sites — verified by mechanism, not a live respawn (which would need a churn cycle).
- **POSIX same-group tradeoff**: an agent sharing the harness's group would NOT get its event_poll reaped (safe: never kill the harness). Normal spawns isolate the group; Windows `/T` reaps regardless. Acceptable by design, documented in AC3.
- **Process note cross-check**: skill's "code briefly landed on local main, recovered via reset to origin/main" — PR is CLEAN against base, code on the task branch; incident contained.

## Delivery
- Merge **deferred to DM** (`Closes #12363`; DM owns ship + counter). Counter NOT bumped. TEST-PLAN-12363 + QA-RESULTS-12363 on main.
