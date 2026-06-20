# Working State

- **Task**: #12294 (.claude-pid authoritative across harness restart) IN-PROGRESS — RCA DONE, design **C+A LOCKED & RE-VALIDATED**, IMPLEMENTING test-first this session on branch `squidsquad/task/12294`. SECONDARY in-progress: #12451 (status-bar) S1+S3 on branch (PR #13024), S2 PARKED on PM CQ-AC via **#13031**.
- **Updated**: 2026-06-20 (skill — event-mode, implementing #12294)
- **Quiet Cycle Counter**: 0

## #12294 — NEW FINDING this session (terminal_pid dead-end → confirms psutil gate)
Considered closing the never-recorded-orphan gap dependency-free by re-resolving claude.exe from the persisted `terminal_pid` (#10101 descendant walk). **DOESN'T WORK on Windows**: boot_remote.py:472-475 — terminal_pid = proc.pid of the `cmd /c start` cmd.exe, which **exits immediately** (self-closing window). Recorded terminal_pid is a dead short-lived process; claude.exe is detached, not its descendant. So orphan re-adoption genuinely needs psutil (cwd/cmdline) → stays a HUMAN GATE. Locked C+A scope stands.

## #12294 — IMPL PLAN (this session)
1. **process_utils.py**: add `image_name_for_pid(pid)` (win32 toolhelp / posix /proc comm; None=undetermined) + `is_claude_process_alive(pid)` (alive AND image∈{claude.exe,claude}; None-image → fall back to liveness = AC2-safe). Extend `_win32_kernel32` w/ toolhelp typing. + unit tests (mock snapshot).
2. **thin_launcher.py**: factor `_win32_all_procs()` out of `_win32_list_descendants`; add local mirror `_image_name_for_pid`/`_is_claude_process_alive` (#8891 no-import); `_check_singleton` → image-verified (recycled PID no longer defeats singleton = A). + tests.
3. **harness.py update_health (580-596)**: PID chain image-verified (in-mem → file), reclaim dead/recycled; (C) write-back .claude-pid via new `reboot_agent.write_claude_pid` when missing/divergent + image-verified-alive. + tests mocking helpers.
4. **AC4 regression test**: (i) stale .claude-pid dead PID + live recorded in state → running not respawned; (ii) recycled non-claude PID at .claude-pid → reclaimed; (iii) missing file + recorded-in-state → running (self-heal write-back). True never-recorded orphan = psutil-gated (out of dependency-free scope; route to human via PM).
5. DS review (high-blast) per logical commit.

## #12294 — RCA + LOCKED DESIGN (resume target)
RCA: harness learns claude.exe PID ONLY from `.claude-pid` (harness.py:595 in update_health; NO spawn-time registration). Single point of failure: thin_launcher writes resolved PID (thin_launcher.py:584, #10101) but unclean exit leaves it STALE; never-recorded live claude.exe (dm/qa observed) is invisible; load_state (harness.py:1381) restores possibly-stale PID on restart.
**LOCKED design (dependency-free): C + A.**
- (A) Read-side image-verify (toolhelp32, reuse thin_launcher `_win32_list_descendants` machinery): add image-name-by-PID; trust a PID only if alive AND image is claude.exe. Fixes AC3 (reclaim recycled-PID) + AC1. Also harden `thin_launcher._check_singleton` (currently trusts ANY live PID → recycled holder defeats singleton).
- (C) Write-side: ensure resolved claude.exe PID reliably recorded so never lost.
- **REJECTED (B) psutil cwd/cmdline discovery** — new dependency, codebase deliberately avoids psutil (raw Win32 only). Only needed to RE-ADOPT a never-recorded orphan vs respawn it; surfaced as a human-approval question in the comment, NOT silently added.
- AC4 tests: mock toolhelp snapshot — (i) stale .claude-pid+live recorded→running not respawned; (ii) recycled non-claude PID→reclaimed; (iii) missing .claude-pid+live+image-verified singleton→no duplicate spawn.
- Next: image-name-by-PID helper + test FIRST, then wire update_health/load_state + _check_singleton + DS review (high-blast).

## This session (2026-06-20, post-harness-restart boot)
Harness restarted (uptime 23s at boot; sha 313d6e58). Drained 43 boot events — all historical (prior session through 02:40, working-state was 03:08+) → fast-forwarded cursor to `9f79fb253e9cac0b`, emitted bootup-complete. Pulled clean (FF only).

- **#12451 S2 DEFERRED + CQ-AC ROUTED.** Verified forge: 7 ACs + folded #12854 part-1 (PM added functional ACs 03:37Z); **no CQ-coverage AC in body**. S2 is one indivisible unit (no-deferred-wiring: instruction edit must ship with cycle.py idle-marker code). Respecting prior-session deliberate deferral ("resume when PM lands it") — sound for a fleet-recompose-triggering CQ-gated edit. Filed **#13031** (role:pm) to reliably wake PM for the AC. Adopted branch + merged main in (local; not pushed — no S2 work yet).
- **#11600 VERIFIED RESOLVED (facts) → routed to PM disposition.** Repro now correct: `_get_clone_path('qa')`→SquidSquad-qa; `.local-config` HAS qa key; unregistered/verifier roles FAIL-CLOSED with CloneResolutionError (#11640 removed the silent repo-root fallback — the exact #11600 root cause). Locked by `tests/test_feat_1496_shared_fs_fallback.py` + `tests/test_boot_remote.py`. /status confirms all agents isolated. No code change needed. Commented resolution verdict; recommend close.
- **#12397 confirmed CLOSED** (stale assigned-to boot event; #12912 closed it — no action).

## This session also
- Picked up #12294 (open→in-progress), did full RCA, locked dependency-free design (above), posted design comment. Implementation deferred to next session (high-blast harness ctypes deserves fresh budget; design is the hard part, now settled).
- **NEW #13032 (HIGH, role:skill, open) — deploy-signal respawn no-ops when halted agent's process stays alive (missing terminate-session handoff).** Top next-pickup candidate (HIGH; deploy-mechanism wedge). Directly observed-adjacent this session: a nudge surfaced 3 STALE deploy-signals (11:08–11:13, pre-boot) — verified SPENT via facts (recompose skill = zero change → no drift; no re-emit in 25+min). The wedge #13032 describes is the missing kill/terminate handoff after ack-stop "deploy-halted" → harness respawn no-ops on a still-alive process. Pairs with #12294 (both harness reliability). Work-queue orders: resume in-progress #12294 first, then #13032 (high).
- Cursor advanced past the spent deploy-signals to 80092145e9c55fb7. Recomposed skill/CLAUDE.md as the drift-check (no change, nothing committed).

## Gated / parked in-progress (unchanged — externally blocked)
- **#12801** (Textual TUI action bar) — needs textual dep + interactive terminal (documented deferral).
- **#12493** (pipeline-sentinel HALT detection) — PR #12494 HELD pending §8.3 backstop landing (PR #12507 unmerged).
- **#12450** (installer unit-test strategy detect) — S3/S4 PM-gated.

## Other open candidates (not started)
- #12363 (orphaned claude.exe/event_poll accumulation), #11140 (composed CLAUDE.md header orientation prose — CQ-gated), #10540 (DM batch-ship race), #12495/#12971/#12861/#12846/#12747/#12519/#11716 (lower).
- #12527 (foreign-repo installer smoke — interactive), #12492 (cutover flip — gated on #12460), #12271 (liveness umbrella — gated/sliced), #10690 (gated E7), #10686 (manual).

## Recurring meta-risk
Clone chronically behind origin (#12526 SHIPPED — launcher no longer rebases). Always `git pull --ff-only` before compose/commit (done this session, was 1 behind qa state, FF clean).

## Improvement Scan
Status: eligible (idle). Last completed: (none — productive boot session).
