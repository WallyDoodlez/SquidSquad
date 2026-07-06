# TEST-PLAN-13303 — L4 watcher restart-required gated on actual composed-output change

**Issue**: #13303 (type:issue, severity:medium, role:skill) — L4 file-watcher emits `restart-required` on no-op recompose (composed output unchanged) → spurious agent restarts.
**PR**: #13314 (base main, head squidsquad/task/13303) — +327/-9, files: `references/scripts/l4_file_watcher.py`, `tests/test_l4_file_watcher_e3.py`.
**Verifier**: qa. Derived independently from the issue body's "Tests (regression)" contract + Remediation direction — NOT from the worker's diff.
**Context note**: verifier personally received this exact no-op `restart-required` over-emit at 04:09 this session and handled it as a NO-OP from facts (composed CLAUDE.md clean, intent advisory). This task fixes that symptom at the source.

## Acceptance criteria (independent interpretation)

- **AC1** — A no-op recompose (compose produces composed `CLAUDE.md` byte-identical to what is already deployed) emits **no** `restart-required` event.
- **AC2** — A real L4 change (compose produces different composed output) **still** emits `restart-required` (no regression to existing behavior).
- **AC3** — The `compose-failed` path is unaffected by the new gate (failure still emits `compose-failed`).

## Edge / robustness criteria (beyond the 3 ACs — verifier-added)

- **E1** — First deploy (no prior deployed file → reader returns `None`) counts as a change → emits `restart-required`.
- **E2** — Gate disabled (`read_deployed=None`) preserves pre-#13303 always-emit behavior (direct callers/tests unaffected).
- **E3** — Fail-safe: if the before-read OR after-read raises, the gate cannot prove "no change" → emits (a needless restart beats silently dropping a real update).
- **E4** — Production entries (`recompose_path` post-commit hook, `start_watcher` file-watch) default to the real `_default_read_deployed` → gate ON in production.

## Test method

1. Run the PR's full module `tests/test_l4_file_watcher_e3.py` on the PR head branch (executes the gate + all pre-existing watcher tests → no module regression).
2. **Independent reproduction** (verifier-authored, not the worker's stubs): drive `recompose_for_role_class` with the REAL `_default_read_deployed` bound to a temp `.squidsquad/<alias>/CLAUDE.md`, simulating the issue's exact scenarios:
   - no-op `run_compose` (rewrites byte-identical content) → assert `noop=True`, zero events (AC1)
   - changing `run_compose` (rewrites different content) → assert `restart-required` emitted (AC2)
   - failing `run_compose` → assert `compose-failed` emitted, gate not interfering (AC3)
   - real reader on a missing alias file → assert `None` (E1 substrate)

## Pass condition

All 3 ACs PASS via both the PR module (green) AND the independent real-filesystem reproduction. Regression test that would have caught the original bug present. Landing safety confirmed (+additions-only, branch not behind main).
