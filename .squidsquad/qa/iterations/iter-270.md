# Iteration 270 — 2026-06-17 (POLLING)

**Pull**: #12509 re-fix landed (branch 728142808) → genuinely **pending-test** now. New branch task/12419 (installer cluster started). **PT scan → #12509.**

**QA WORK — #12509 RE-VERIFY → FAIL (2nd) → in-progress (skill).**

The cy251 fix WAS applied (snapshot+restore sys.modules['harness'] in finally, not just sys.path) — my literal suggestion. **But contamination persists**; my cy251 root-cause was necessary-but-insufficient.

- **AC1 collection** ✅ — `pytest tests/ --co` → 4709, 0 errors. Rename correct.
- **AC3 run_tests.py** ✅ exit 0. **AC5 no product regression** ✅ (feat_10681 alone 11✓, 12460 alone 24✓).
- **AC2/AC4 FAIL** — `12509→feat_10681` = 7 failed; trio = 6 failed.

**Culprit pinned**: `test_bare_harness_import_resolves_to_real_harness`. Deselect → 13 passed; include → 7 failed; reversed → 14 passed.

**Mechanism**: the fn still does a LIVE `import harness` after `sys.modules.pop("harness")` → re-executes load-bearing harness.py mid-suite → residue beyond the one restored key. Proof: feat_10681's `patch("harness.HARNESS_STATE_FILE")` stops redirecting (save_state writes elsewhere; state_file.exists() False) — patched module vs collection-time HarnessState binding diverge.

**Required fix (stronger than cy251)**: don't mutate global import state in-process. (1) `importlib.util.find_spec("harness").origin` check (no import); or (2) subprocess-isolate the live import; or (3) drop the fn — the other two static guards already cover the regression.

**Verdict: FAIL.** Routed back to skill with culprit + mechanism + 3 fix options. Zero-gap gate held (regression test that breaks siblings doesn't ship). QA-RESULTS-12509 appended (cy270 section).

**Process**: branch checkout swapped working-state/composed → artifacts written on main; stray settings.json restore attempted.

**Open (operator)**: user asked about switching me to event mode (cy269 inline). I flagged the risk (#12506 unfixed + verifier auto-route unproven) and recommended holding; no switch directive given since → staying POLLING.

**Outcome**: productive (2nd FAIL + evidence). Quiet-cycle counter → 0. Watch: #12509 (2nd re-fix), #12493, #12492, #12506.
