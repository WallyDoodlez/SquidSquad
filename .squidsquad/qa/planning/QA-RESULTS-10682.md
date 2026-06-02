# QA-RESULTS-10682 — PRD-E / Story E3: L4-write file-watch + restart-required event (Layer 2)

**Verified**: 2026-06-02 06:40
**Branch**: `skill/e3-l4-filewatch-10682` @ `bcb32b7a`
**PR**: #10746
**Verifier**: qa-lead
**Result**: **FAIL — route back**

## Scope Check

- `references/scripts/l4_file_watcher.py` (+428 new) — pure functions + `_Debouncer` + `start_watcher()`
- `tests/test_l4_file_watcher_e3.py` (+417 new) — 22 tests, all on the pure surface (no `watchdog` import required)
- `tests/run_tests.py` (+1)
- `.squidsquad/skill/planning/ds-e3-review.md` (DS review log)
- **NOT modified**: `references/scripts/harness.py` — the module is not wired into the harness lifecycle.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | File-watch mechanism — recommend `watchdog` | `start_watcher` lazy-imports `watchdog.observers.Observer`; module-level docstring cites Q-E1. | PASS (mechanism) |
| 2 | Watch path: `.squidsquad/project/` recursive | `observer.schedule(_Handler(), str(watch_path), recursive=True)` in `start_watcher`. | PASS (configured) |
| 3 | On `<role-class>.md` change: identify aliases, run `compose.py deploy <alias>` per alias, emit `assigned-to(...)` | `role_class_from_path` + `compute_affected_aliases` + `recompose_for_role_class` + `emit_results` chain. Pure-function tests cover the alias projection + per-alias event emission. | PASS (module level) |
| 4 | File-watch is primary; optional `.git/hooks/post-commit` script | Module exposes `recompose_path` for hook-style direct invocation. Hook itself out of scope ("optional"). | PASS |
| 5 | Failure modes: file-watch crashes → harness logs + restarts the watcher; compose failure → emits compose-failed | **Compose-failure path**: `recompose_for_role_class` constructs `compose-failed` events on compose stderr — PASS. **Watcher-crash-restart**: NOT implemented. Source comment line 388-391: "if the observer thread dies, the harness logs + restarts the watcher. This function only constructs and starts the observer; the survive-and-restart loop lives in the harness." → **FAIL**. | **FAIL** |
| 6 | Tests cover: write → recompose, event emitted, debounce, unrelated file → no compose | 22 pure-function tests cover the callback paths + debouncer race regression (DS-F1). Tests do NOT exercise a real file-watch round-trip (no `watchdog` invoked). Live behavior unverified because there is no harness to drive it. | PARTIAL |

## Why this is a route-back

The issue body's GOAL paragraph names the harness as the actor: **"harness file-watches `.squidsquad/project/` for L4 commits. On any write, runs `compose.py deploy` ... and emits `restart-required` event"**. Without harness wiring, none of this happens at runtime — the module sits unused in the source tree.

Skill's pending-test comment makes the deferral explicit:

> "Harness wiring (Observer lifecycle, survive-restart loop) is a separate follow-up to land independently of E3's module."

Per `feedback_no_ship_with_gaps`: "Any QA gaps = back to dev, not 'noted for follow-up'." The "separate follow-up" framing is the exact phrase the rule rejects.

Compounding evidence:

- `harness.py` does not import `l4_file_watcher` (live grep: zero hits in any file other than the module itself + its tests).
- No follow-up ticket is filed for the deferred harness wiring — the "follow-up" exists only in skill's PT comment, not in the tracker. If it's not in the tracker, it can be forgotten; if it can be forgotten, this is a real gap.
- AC5's "harness logs + restarts the watcher" is unverifiable because there is no caller to crash. The compose-failure half of AC5 is implemented, but the watcher-crash half requires harness wiring.

This is structurally identical to the #10444 B1 cycle 513 + #10447 cycle 517 deferrals — both of which surfaced **real defects** on route-back. The pattern is: defer a piece of AC scope → the deferred piece exposes a real flaw when implemented.

## Test Execution

`pytest tests/test_l4_file_watcher_e3.py tests/test_v1_byte_stability_9a.py -q` on `bcb32b7a` → **27 passed** (22 E3 + 5 §9a). Tests of the *implemented* surface are clean. But the implemented surface is not the AC-defined surface.

## v1 Coexistence

§9a v1 byte-stability gate: 5/5 passed. Module is purely additive — no v1 path touched. Once harness wiring is in place, the v1 trigger semantics from PRD §9a will need re-verification (file-watch fires v1 compose pre-E6 per the issue body's "v1 coexistence" section).

## Outcome — Route back to skill

**Transitioning #10682: pending-test → in-progress.**

Two acceptable paths forward:

1. **Wire `start_watcher()` into harness.py in THIS PR.** Add an `Observer` lifecycle owner alongside the existing background threads (`_poller_thread` and friends in `HarnessState`). Implement AC5's survive-and-restart loop: when `observer.is_alive()` flips False, log + call `start_watcher` again. Include a regression test that crashes the Observer (e.g., raise inside the handler) and asserts the harness re-spawns it.

2. **Push back via PM if E3's scope is genuinely "module only."** File a follow-up ticket explicitly tracking the harness wiring requirement so it cannot be silently forgotten, and ask PM to amend this issue body so AC5's harness-side language is removed (or moved to the new ticket). Then re-route. Right now the issue body says one thing and the PR delivers another — that mismatch must resolve before pending-ship.

Either path is fine; the current "ship the module and follow up" is not.
