# QA-RESULTS-10681 (re-batch) — PRD-E / Story E2: post-merge reverification

**Verified**: 2026-06-02 07:40 (post-merge)
**Branch**: `squidsquad/task/10681` @ `53afde86` (merge of origin/main)
**Previously verified at**: `8f27a3dd` in cycle 554 — PASS
**Verifier**: qa-lead
**Result**: **PASS** (re-batch — feature code byte-identical, post-merge integration green)

## Why this re-verification

DM bounced #10681 from pending-ship back to in-progress in cycle 555 due to PR #10692 merge conflicts against main. Skill resolved via `git merge origin/main` per `feedback_never_rebase_merge_instead`. The merge brought in `tests/run_tests.py` (union of test entries); `references/scripts/harness.py` auto-merged cleanly because E2 (last_compose_checksum) and E3 (L4 file-watch supervisor) touch different parts of `HarnessState`.

## Feature-code parity check

E2's `last_compose_checksum` additions to `HarnessState` are unchanged at `53afde86`. The branch now ALSO has E3's L4 file-watcher supervisor (because main shipped #10682 in cycle 561) — that's expected: post-merge state should converge on main.

## Post-merge integration

`pytest tests/test_feat_10681_compose_checksum.py tests/test_v1_byte_stability_9a.py tests/test_harness.py tests/test_l4_file_watcher_e3.py -q` on `53afde86` → **231 passed**.

Coverage matrix:
- 11 E2 tests (this story)
- 5 §9a v1 byte-stability
- 187 existing harness regression tests (`test_harness.py`)
- 28 E3 L4 file-watcher tests (now in main, must coexist on branch)

E2 + E3 both touch `HarnessState` but on disjoint fields (`last_compose_checksum` vs `_l4_observer`/`_l4_debouncer`/...). Auto-merge was clean; 231 tests confirm no semantic conflict.

## v1 Coexistence

§9a v1 byte-stability gate green on `53afde86`. Both E2 + E3 are harness-side additive changes; v1 compose path untouched.

## Outcome

E2 feature code is unchanged from cycle 554's verified commit; post-merge integration with E3 is fully green. **Transitioning #10681: pending-test → pending-ship.** Original QA-RESULTS-10681.md remains the canonical verification record; this file documents the re-batch event.
