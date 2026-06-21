# TEST-PLAN-12409 — frequency-based slow reboot-loop breaker

**Issue**: #12409 (type:issue, severity:HIGH, role:skill) — qa slow event-mode reboot loop; #12244 backoff misses slow loops (>60s lifetime).
**PR**: #13039 (branch `squidsquad/task/12409`, `Closes #12409`).
**Derived by**: verifier (qa), independently from issue body + skill triage/scoping comments — NOT from the PR diff.
**CQ**: none — deterministic harness code, no LLM-consumed instruction change.
**Scope**: ONLY ask 1 (frequency breaker). Ask 2 (SessionEnd-reason) → #12271; ask 3 (orphans) → #12363; "inert/zombie" framing → #12820 (shipped). Verifier judgment: legitimate scope narrowing — the three asks are independent and 2/3 are genuinely other issues' lanes; this fix delivers the one actionable breaker. Verify only ask 1; the others are correctly routed, not gaps.

## Derived ACs (ask 1)
- **AC1** — frequency-based breaker: ≥`SLOW_LOOP_THRESHOLD` auto-reboots within `SLOW_LOOP_WINDOW_SECONDS` (lifetime-agnostic) → back off instead of rebooting, EVEN when `consecutive_fast_deaths==0` (the slow loop #12244 cannot see).
- **AC2** — composes with #12244: fast-death breaker takes precedence (elif ordering); below threshold → normal reboot.
- **AC3** — `reboot_history` sliding window, pruned on record/read, persisted across harness restart (to_dict / save_state / load_state, defensive coercion on load).
- **AC4** — never wedges permanently: capped-exponential backoff (30s base, 1800s/30m cap), `status=crash-looping` reuses the existing resume machinery (retry when `reboot_blocked_until` elapsed).
- **AC5 (DS-12409 F1)** — auto-reboot dispatch gated on `action=="spawn"` (not `success` alone): a `skip` (agent alive in a race) must NOT record a phantom reboot or stamp `last_spawn_at`.
- **AC6** — no-regression: full fail-closed static gate green.

## Test cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC1 | `test_slow_loop_trips_breaker_not_reboot` + independent probe | 3 reboots/window + slow lifetime → status=crash-looping, reboot_blocked_until set, `consecutive_fast_deaths==0` (proves #12244 missed it), boot NOT called |
| TC-2 | AC2 | `test_below_threshold_reboots_normally` + probe (boundary) | 2/window → normal reboot (boot called, status=starting); breaker `elif` after fast-death check |
| TC-3 | AC3 | `test_*_prunes*`, `test_save_load_round_trip`, `test_load_drops_corrupt_history_entries`, `test_stale_reboots_outside_window_do_not_trip` + probe (901s pruned) | window pruning correct; persisted+restored; corrupt entries dropped |
| TC-4 | AC4 | code review (backoff `min(30·2^over,1800)`) + probe + resume branch (harness.py:1104 `time.time()>=reboot_blocked_until`) | backoff caps at 30m; crash-looping resumes/retries after elapse |
| TC-5 | AC5 | `test_skip_result_does_not_record_reboot` + diff (harness.py:1144 `success and action=="spawn"`) | skip → reboot_history unchanged, last_spawn_at not stamped |
| TC-6 | AC6 | full `run_tests.py static` on branch | exit 0, all pass |

## Notes
- Branch merges current main (carries #12294 + #13032 image-verify/deploy changes — both already verified+shipped this session; they appear in the harness.py diff but are out of #12409 scope).
- Verifier has a prior **health-data-point** comment on this issue (the cy378 "PID alive + listener dead" blind spot from a #12837 Monitor death) — that observation is about a DIFFERENT gap (listener-death detection) than the slow-reboot-loop breaker; not in this PR's scope, remains a valid open observation for this lane.
