# QA-RESULTS-13236 — harness.py main() stdout hardening (cp1252 crash-net)

**Verifier**: qa
**Date**: 2026-06-26 23:xx
**Verdict**: PASS (zero gaps) — Status pending-test → pending-ship.
**Change under test**: PR #13243, branch `squidsquad/task/13236`, commit `9e65b70b6`.
**Files**: `references/scripts/harness.py` (+13), `tests/test_cli_stdio_13198.py` (+25). Follow-up to the #13198 / #13185 cp1252 crash class — I filed this finding during #13198 re-verification.

## TEST-PLAN (derived from the issue's suggested fix + crash class)
- TC-1: harness.py `main()` invokes `harden_stdio()` before any print (banner/status). Suggested fix = in-process harden_stdio (preferred over PYTHONUTF8).
- TC-2 (behavioral): on a strict cp1252 stream, harness-style non-ASCII output no longer raises UnicodeEncodeError after harden_stdio.
- TC-3: regression test present; harness.py stays out of the #13198 print-literal ASCII-sweep guard (its art is intentional).
- TC-4: no regression (harness parses; cli_stdio suite + ship gate green).

## Results
| TC | Result | Evidence |
|----|--------|----------|
| TC-1 | PASS | diff: `from cli_stdio import harden_stdio` + `harden_stdio()` is the **first** statement in `main()` (before the event-loop policy and all prints). |
| TC-2 | **PASS (behavioral)** | Simulated strict cp1252 stdout: baseline `print("🦑 — •")` raises UnicodeEncodeError; after the exact `harden_stdio()` call main() makes, the same output prints backslash-escaped with **no crash** (exit 0). |
| TC-3 | PASS | `TestHarnessWiring13236::test_harness_main_invokes_harden_stdio` + `test_harness_not_in_ascii_sweep_guard` PASS. Box-drawing banner art deliberately NOT swept (it's art, not messages — matches the issue's "optional" sweep note). |
| TC-4 | PASS | `harness.py` parses clean; full `test_cli_stdio_13198.py` 26/26; ship gate `run_tests.py` 53/53. |

## Note on scope
The fix takes the issue's **preferred** path (in-process `harden_stdio` for fleet parity) rather than the launcher-`PYTHONUTF8` alternative — correct call. The optional decorative-char ASCII sweep of harness.py was intentionally skipped (the chars are intentional art/emoji, not messages); harden_stdio crash-proofs them, which fully closes the crash class this issue was about. Zero gaps.

## Verdict
**PASS — zero gaps.** harness.py is now in the cp1252 crash-net (behaviorally proven); regression-guarded; no regression. Status pending-test → pending-ship; PR #13243 to merge.
