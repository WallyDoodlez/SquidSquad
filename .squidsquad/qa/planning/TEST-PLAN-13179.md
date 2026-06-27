# TEST-PLAN-13179 — progress_liveness unbounded 'booting' escape (shadow-only, #12271 Slice A)

**Source**: GitHub issue #13179 Acceptance Criteria (AC1–AC5).
**Derived without reading the diff.**

Deterministic harness code (`AgentState.progress_liveness`). Shadow-only verdict fix.

## Test Cases

### TC-1 (AC1): wedged-boot-timeout past grace; booting within grace
- **Expected**: bootup_complete=False AND age > boot-grace → `(False, "wedged-boot-timeout")`;
  within grace → `(True, "booting")`.
- **Verification**: pytest `test_not_booted_past_boot_grace_is_wedged`, `test_not_booted_within_boot_grace_is_alive`, `test_not_booted_at_grace_boundary_is_alive` (boundary == grace stays booting), `test_not_booted_boot_time_fallback_when_no_spawn`.

### TC-2 (AC2): threshold is a documented tunable, same pattern as ACTIVITY_GRACE_SECONDS
- **Expected**: `BOOT_GRACE_SECONDS` named module constant with documented default (~600s), matching the existing `ACTIVITY_GRACE_SECONDS` pattern (named, not a bare inline magic number).
- **Verification**: `grep BOOT_GRACE_SECONDS references/scripts/harness.py`.

### TC-3 (AC3): regression test catches the unbounded escape (fails pre-fix)
- **Expected**: pre-fix `progress_liveness` returns `(True, "booting")` for a >grace not-booted agent (the qa-wedge shape); post-fix returns `(False, "wedged-boot-timeout")`.
- **Verification**: run pre-fix harness against the qa-wedge shape.

### TC-4 (AC4): shadow-verdict-only — no reboot behavior change
- **Expected**: change confined to `progress_liveness` return value + constant + tests; health poller uses it only for the shadow LIVENESS DIVERGENCE log, not the reboot decision (PID stays authoritative until #12492).
- **Verification**: read harness.py:725-740 (poller shadow comparison comment); confirm diff touches no reboot path.

### TC-5 (AC5): shadow logging surfaces the new verdict
- **Expected**: the poller's divergence log includes `prog_reason`, so `wedged-boot-timeout` is logged when PID-alive disagrees.
- **Verification**: read poller log line (harness.py ~737) — logs `({prog_reason})`.

### TC-6 (no regression): full gate green
- **Expected**: progress_liveness module green (28); full `tests/run_tests.py` green.

## Coverage matrix
- AC1 → TC-1 ; AC2 → TC-2 ; AC3 → TC-3 ; AC4 → TC-4 ; AC5 → TC-5 ; (guard) → TC-6

## Comprehension Questions
N/A — deterministic harness code, not LLM-consumed instruction. No CQ spec.
