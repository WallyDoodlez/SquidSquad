# TEST-PLAN-13957

9398 gh-shim integration test broken by #13863 push-doctor (MEDIUM, type:issue, auto-approved). Derived independently from the bug report.

## TCs

- **TC1 — severity confirmation**: does the OLD (pre-fix) shim test genuinely run the real `tracker.py` against the real repo root, meaning #13863's push-doctor (`persist=True` by default) really did rewrite the developer's real `.git/config` credential.helper as an unintended side effect on every run — not just a hypothetical?
- **TC2 — fix correctness, live**: does the NEW hermetic-workspace fix genuinely leave the real clone's `.git/config` byte-identical before and after running the fixed test?
- **TC3 — fix isn't a vacuum pass**: does `test_check_gh_does_not_doctor_the_hermetic_workspace` actually prove the doctor ran and took its early-return (not that check-gh crashed before reaching it)?
- **TC4 — original intent preserved**: does the fixed test still verify what it always verified (check-gh passes through the gh shim's read-fallback)?
- **TC5 — full no-arg integration suite**: run the COMPLETE `run_tests.py` (no target filter) — not just my usual `harness`/`status_flow` subset, which I discovered this round does NOT include the `gh_shim_tracker` target at all.
- **TC6 — ship gate**: static gate (registry-aware, per `run_tests.py`'s own `KNOWN_FAILURES`/`KNOWN_NON_STATIC` exclusions).
