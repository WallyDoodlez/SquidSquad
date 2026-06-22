Closes #13179. Parent: #12271 (progress-based liveness) — **Slice A**, PM-greenlit.

## Problem
`AgentState.progress_liveness(now)` (harness.py:457) returned `(True, "booting")` whenever `bootup_complete` is False, with **no time bound**. A wedged agent that never completes bootup read as alive-forever in the shadow verdict — the opposite of #12271's requirement "bootup never completed must trigger reboot." Real instance: qa sat `bootup_complete:false` for ~54 min (wedged at `intent=deploying`, blocked on an AskUserQuestion modal) and would have read alive the entire time.

## Fix (shadow-only — zero reboot blast radius)
- Add `BOOT_GRACE_SECONDS = 600` named module constant (same pattern as `ACTIVITY_GRACE_SECONDS` — AC2), with a generous-default comment + tunable-from-shadow-data note.
- Bound the booting escape: age a not-yet-booted agent from `last_spawn_at` (fall back to `boot_time`); past the grace → verdict `wedged-boot-timeout` (alive=False); within it → `booting` (alive). **No spawn reference** (both None) → stay `booting` (never false-positive a death we cannot time).
- **Verdict-only**: changes what the shadow `progress_liveness` reports; does NOT drive reboot. The existing poller divergence log (harness.py:731) already surfaces the new verdict (PID-alive vs progress-dead → "candidate-zombie"), so the #12492 cutover decision sees sharper data (AC5). PID-liveness remains authoritative until #12492 (AC4).

## ACs
- **AC1** ✓ `wedged-boot-timeout` (non-alive) past grace; `booting` within grace. **AC2** ✓ config-tunable named constant, ~600s default. **AC3** ✓ regression test of the qa-wedge shape (>grace not-yet-booted → non-alive). **AC4** ✓ no reboot-behavior change (shadow verdict-only). **AC5** ✓ surfaced via existing divergence logging.

## Tests / gates
+5 boundary regression tests in `test_12460_progress_liveness.py` (within-grace / over-grace [qa shape] / exactly-at-boundary / boot_time-fallback / no-spawn-reference). File: 28 passed. Full static gate: see below.

## Scope discipline
DS-review skipped per PM's #12271 structuring comment (Slice A is "shadow-only, zero reboot blast radius"; DS-review reserved for Slice B). Deterministic harness code → no CQ. No new/renamed files → no manifest update. **Slice B** (intent=deploying force-kill backstop) is a separate, higher-blast-radius slice (DS-review + PM doc-pairing) — filed/built next, not folded here.
