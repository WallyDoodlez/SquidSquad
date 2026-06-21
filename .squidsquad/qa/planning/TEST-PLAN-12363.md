# TEST-PLAN-12363 — orphaned claude.exe / event_poll reaping across respawns

**Issue**: #12363 (type:issue, severity:medium, role:skill) — orphans accumulate (~13 claude + ~12 event_poll for 4 agents) because respawns don't reap the prior session's claude + Monitor-spawned `event_poll.py` sidecar.
**PR**: #13040 (branch `squidsquad/task/12363`, `Closes #12363`).
**Derived by**: verifier (qa), independently from issue body (Why-it-matters / Asks) + skill RCA — NOT from the PR diff.
**CQ**: none — deterministic harness code.
**WINDOWS-BOX CAVEAT**: the POSIX `killpg` tests `skipif(win32)` and `os.killpg`/`getpgid`/`signal.SIGKILL` aren't attributes on Windows → they cannot execute here. POSIX path verified by code review + an independent forced-branch exercise (patch `sys.platform`→posix + mock the os/signal fns with `create=True`).

## Derived ACs
- **AC1 (Windows tree-kill)** — `_kill_process` uses `taskkill /F /T /PID` so the event_poll.py descendant tree dies with claude.exe (was `/F` only → orphan).
- **AC2 (POSIX group-kill)** — `os.killpg(os.getpgid(pid), SIGKILL)` reaps the process group (the POSIX analogue) so the event_poll descendant dies with claude.
- **AC3 (POSIX safety fallback)** — if the target shares the harness's OWN group (`getpgid(pid) == getpgid(0)`), fall back to bare `os.kill(pid, SIGKILL)` — killpg there would take the harness down. No regression vs pre-#12363.
- **AC4 (shared helper, all 3 teardown paths)** — `_kill_process` is the single helper used by poller-respawn, idle-restart, and the 60s force-kill safety net; all three inherit the tree/group reap.
- **AC5 (error handling preserved)** — PID-validation guard intact; `ProcessLookupError`/`PermissionError`/`TypeError`/`OSError` swallowed best-effort (OSError newly added for getpgid/killpg group-vanished races).
- **AC6 (no-regression)** — full fail-closed static gate green.

## Test cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC1 | `test_kill_windows_uses_taskkill_force_tree` (runs on this Windows box) + diff | `/T` in `taskkill /F /T /PID` cmd |
| TC-2 | AC2 | **Independent forced-branch exercise** S1 (different group) | `killpg(target_group, SIGKILL)` called, bare `kill` NOT called |
| TC-3 | AC3 | **Independent forced-branch exercise** S2 (own group) | `killpg` NOT called, fallback `kill(pid, SIGKILL)` — harness group spared |
| TC-4 | AC5 | forced-branch exercise S3/S4/S5 (getpgid→PLE, killpg→OSError, killpg→PermissionError) | all swallowed, no raise |
| TC-5 | AC4 | grep `_kill_process` callers in harness.py | 3 call sites (758 force-kill net / 3686 / 3788) all via shared helper |
| TC-6 | AC6 | full `run_tests.py static` on branch (Windows — POSIX cases skip) | exit 0, all pass; reboot_agent suite 25 passed / 5 skipped |

## Notes
- Branch merges current main (carries #12294 `write_claude_pid` etc. — appears in reboot_agent.py diff, already verified+shipped this session, out of #12363 scope).
- **Orphan-count confirmation ask** ("count returns to 1 claude + 0..1 event_poll per agent after a clean respawn") is the behavioral OUTCOME of the tree/group kill; not directly reproducible without a live respawn cycle, but the mechanism (reap the whole tree/group via the shared helper) is verified at all 3 teardown sites + both platforms.
- **Process note cross-check**: skill's "code briefly landed on local main by mistake, recovered by reset to origin/main" — PR #13040 is MERGEABLE/CLEAN against base main and the code lives on `squidsquad/task/12363`; incident contained, nothing wrong on origin/main.
- POSIX same-group fallback (AC3) means an agent sharing the harness's group would NOT have its event_poll reaped (safe tradeoff: never kill the harness). Normal spawns put agents in their own group (thin_launcher) so killpg reaps; Windows `/T` reaps regardless. Acceptable by design.
