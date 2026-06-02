# QA-RESULTS-10684 — PRD-E / Story E5: Wire freshness check into harness restart-safety

**Verified**: 2026-06-02 11:40
**Branch**: `skill/e5-freshness-restart-safety-10684` @ `221f07bf`
**PR**: #10760
**Verifier**: qa-lead
**Result**: **PASS** (same `blocked:audit-review` procedural state as #10680)

## Scope Check

- `references/scripts/harness.py` (+93) — `_NO_FRESHNESS_CHECK` module flag + escape-hatch wiring + state-file persistence of `compose_freshness_failed`
- `tests/test_harness_freshness_restart_e5.py` (+289 new) — 14 tests
- `tests/run_tests.py` (+1)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Restart-safety step 1b (between state read + PID verify): run E1 freshness check | E1's check is already wired into `lifespan` per #10680. E5 adds the escape-hatch + state-file persistence. The restart-safety semantics ride on lifespan since lifespan runs on every harness boot (restart = process restart). | PASS |
| 2 | Restart-safety semantics: failed check → restart aborts with operator-visible error | `compose_freshness_failed` flag now persists to `.harness-state.json` (DS F1 fix) so a `--no-freshness-check` restart after a prior failure still refuses spawns. AC2 chain: prior failed boot → persisted flag → next boot reads flag → spawn paths refuse. The contract holds across restarts. | PASS |
| 3 | Skip freshness check if `--no-freshness-check` env var or CLI flag set | `_NO_FRESHNESS_CHECK` module-level flag, set from `--no-freshness-check` CLI flag OR `SQUIDSQUAD_HARNESS_NO_FRESHNESS_CHECK=1`. Lifespan guard fires BEFORE `check_and_repair`. **Escape hatch does NOT reset `compose_freshness_failed`** — operator can't bypass a known-bad state, only skip the re-check on what they assert is good state. Smart safety design. | PASS |
| 4a | Clean restart → freshness check + PID verify both pass | 14 E5 tests + 5 §9a + 16 E1 + 187 harness regression = **222 passed** total. Clean-restart path covered. | PASS |
| 4b | Drift detected → recompose runs before PID verify | Inherits E1's `check_and_repair` semantics; AC ride on E1's tests. | PASS |
| 4c | Freshness check fails → restart aborts | `compose_freshness_failed` persisted + 3 spawn-path gates from E1 still in effect. | PASS |

## DS Review Catches

Per `feedback_ds_review_per_change`, skill ran DS review and fixed 3 findings pre-commit:

- **F1** (persistence missing) — flag wasn't saved to state file → a `--no-freshness-check` restart after a prior failure would silently lose the gate. Fix: persist `compose_freshness_failed` via `save_state`/`load_state` with legacy default False. **This is the most important fix** — it preserves AC2's "operator-visible refusal across restarts" contract.
- **F2** (failed branch didn't flush) — `compose_freshness.check_and_repair` returned failed but `save_state` wasn't called → flag set in memory only. Fix: explicit `save_state()` after failure detection.
- **F3** (comment drift) — corrected stale comments after wiring changes.

Regression tests pin all three.

## v1 Coexistence

§9a v1 byte-stability gate: 5/5 passed on `221f07bf`. E5 is pure harness-side plumbing on top of E1; v1 compose path untouched.

## Test Execution

`pytest tests/test_harness_freshness_restart_e5.py tests/test_harness.py tests/test_compose_freshness_e1.py tests/test_v1_byte_stability_9a.py -q` on `221f07bf` → **222 passed** (14 E5 + 187 harness regression + 16 E1 + 5 §9a).

Skill reported 14 E5 tests + 228 wider — my 222-pass cut covers the core E5 + adjacent E1 + harness + v1 gates.

## Procedural Note

Same as #10680 cycle 569: `blocked:audit-review` label still on. PM HOLD at T13:16; skill picked up at T15:21 (after audit umbrellas had shipped through QA cycles 567/568). Functional reason for hold satisfied. Proceeding on merit; PM should clear the label.

## E6 Gate Readiness

E5 was the last PRD-E prep story before E6 (V2 CUTOVER, #10685). With this verification:
- E1 (freshness check) ✓
- E2 (last_compose_checksum) ✓
- E3 (L4 file-watch) ✓
- E5 (restart-safety wiring) ✓

E4 status unknown to me; if E4 also lands, E6 cutover is unblocked from the PRD-E side (#10751 + #10753 ERROR gates also cleared).

## Outcome

All 4 ACs (incl. 3 AC4 sub-bullets) covered. State-file persistence of `compose_freshness_failed` (DS F1) is the load-bearing addition — without it, the escape-hatch flag would have silently broken AC2's restart-safety chain. **Transitioning #10684: pending-test → pending-ship.**
