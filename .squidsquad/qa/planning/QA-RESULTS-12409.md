# QA-RESULTS-12409 — frequency-based slow reboot-loop breaker

**Verdict**: ✅ **PASS — zero gaps**. All derived ACs (ask 1) verified with code + tests + independent probe + no-regression. → `pending-ship` (DM).
**Issue**: #12409 (type:issue, severity:HIGH, role:skill). **PR**: #13039 (branch `squidsquad/task/12409` @ `9c6a79490`, MERGEABLE/CLEAN, `Closes #12409`).
**CQ**: none — deterministic harness code.
**Verified in**: isolated git worktree off `origin/squidsquad/task/12409` (merges current main, carries #12294 + #13032 — both already verified+shipped this session).

## What it fixes
qa churned 4 auto-reboots in ~18min, each session living >60s. #12244's breaker keys on FAST deaths (<60s lifetime × ≥3), so each long-lived death reset `consecutive_fast_deaths` → #12244 never engaged → free churn. This adds a lifetime-agnostic frequency breaker.

## AC walk (evidence)

**AC1 — frequency breaker trips where #12244 can't** ✅
- New `elif agent.recent_reboot_count(now) >= SLOW_LOOP_THRESHOLD` branch (harness.py:1057) backs off via capped-exponential + `status=crash-looping` + `reboot_blocked_until`.
- `test_slow_loop_trips_breaker_not_reboot`: 3 reboots/900s + slow lifetime (FAST_DEATH_WINDOW+120) → status=crash-looping, reboot_blocked_until set, **`consecutive_fast_deaths==0`** (proves #12244 missed it), `boot_mock.assert_not_called()`.
- Independent probe: 2-in-window → no trip; 3-in-window → trips (exact boundary).

**AC2 — composes with #12244** ✅
- Breaker is an `elif` AFTER the fast-death check → fast-death takes precedence. `test_below_threshold_reboots_normally`: 2/window → normal reboot (boot called, status=starting).

**AC3 — sliding window, pruned, persisted** ✅
- `SLOW_LOOP_WINDOW_SECONDS=900` (15m), `SLOW_LOOP_THRESHOLD=3`. `record_reboot`/`recent_reboot_count` prune via `_prune_reboot_history`. Persisted in to_dict (h.py:496) + save_state (h.py:1398) + restored in load_state (h.py:1534, defensive list-of-numbers coercion).
- `test_save_load_round_trip`, `test_load_drops_corrupt_history_entries`, `test_stale_reboots_outside_window_do_not_trip` + probe (901s entry pruned → count drops, no trip).

**AC4 — never wedges permanently** ✅
- Backoff `min(CRASH_BACKOFF_BASE·2^over, CRASH_BACKOFF_CAP)` = 30s→60s→120s…→1800s(30m) cap. Probe-confirmed (recent=3→30s, 8→960s, 20→1800s capped). `status=crash-looping` reuses the existing resume branch (h.py:1104 `time.time() >= reboot_blocked_until`) → retries after backoff elapses.

**AC5 — DS-12409 F1 (skip ≠ reboot)** ✅
- Auto-reboot dispatch gated `if result.get("success") and result.get("action") == "spawn"` (h.py:1144) — matches the other 3 spawn paths. `record_reboot`/`last_spawn_at` only on real spawn. `test_skip_result_does_not_record_reboot`: action=skip → reboot_history unchanged (count stays 1).

**AC6 — no-regression** ✅
- Full `tests/run_tests.py static` (fail-closed #12408, junit-backed) on branch → **`PASS — 4806 gated test(s) passed (0 failures, 0 errors)`**, exit 0. `test_12409_slow_loop_breaker.py` 11/11.

## Scope (legitimate, not gaps)
- PR delivers ONLY ask 1 (the actionable breaker). Ask 2 (SessionEnd-reason capture) → #12271; ask 3 (orphan claude/event_poll accumulation) → #12363; the "inert/zombie bootup_complete=false" framing → #12820 (shipped). The three asks are independent; 2/3 are genuinely other lanes' work, properly routed at triage. Verifier judgment: correct narrowing, not a dropped requirement.
- My prior **health-data-point** comment on this issue (cy378 "PID alive + listener dead" blind spot on a #12837 Monitor death) concerns a DIFFERENT gap (listener-death detection) than this breaker — remains a valid open observation for the qa-stability lane, not in this PR's scope.

## Delivery
- Merge **deferred to DM** (`Closes #12409`; DM owns ship + counter). Counter NOT bumped. TEST-PLAN-12409 + QA-RESULTS-12409 on main.
