# Iteration 307 — 2026-06-17 18:44

**Mode**: POLLING.

**Outcome**: Filed **#12748** (improvement, role:skill, severity:medium) — the #12720 follow-up.

## Pickup
- Canonical PT scan → `[]`. Pull up-to-date.

## Improvement-scan task
- Characterized + filed the live-test-hygiene follow-up from #12720 (now closed, so it needed its own tracker item). Confirmed empirically: `test_comprehension_1428` → **6 errors in 0.22s** (fails fast at setup, not a clean skip) when claude CLI absent. So post-#12720 the honest `pytest tests/` is ~53-red in any keyless env (most CI / dev machines), eroding the gate's usability.
- **#12748**: env-gated live tests (comprehension ~35, model_router_live ~13, wake_mode/wizard ~5) should SKIP cleanly (collection/setup skip-guard on missing CLI/key) instead of ERROR/FAIL; optionally a `live` marker for `-m "not live"`. Sibling to #11394/#12408.

**Quiet Cycle Counter**: 0 (productive — improvement filed).
