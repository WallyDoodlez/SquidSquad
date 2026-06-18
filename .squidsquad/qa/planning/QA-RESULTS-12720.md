# QA-RESULTS #12720 — `pytest tests/` false-green / hard-exit (my cy291 filing)

## Verification (cy305, 2026-06-17) — verdict: PASS → pending-ship (DM)
Branch squidsquad/task/12720 @ origin tip, PR #12736. Severity:high. This is my own cy291 filing; I
verified the fix against the live suite with attention to whether it makes the gate *honest*, not just
quiet.

**RCA confirmed (matches my cy291 evidence exactly):** `test_post_shutdown_returns_202` POSTed
`/shutdown`; the handler spawns a `shutdown` DAEMON thread that sleeps then calls `os._exit(0)`. The
old test's `patch("harness.os._exit")` reverted the instant the POST returned 202, so ~1s later the
REAL `os._exit(0)` fired from the daemon thread and hard-killed pytest (exit 0, no summary). At full
scale this fired ~58% in (wall-clock after test_harness ran) — exactly my time-based, non-os._exit
(captured-reference) signature. Fix is **test-side** (the /shutdown production behavior is correct).

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 defect A fixed | ✅ PASS | Full `pytest tests/` now **reaches sessionfinish**: `77 failed, 4665 passed, 17 skipped, 17 errors in 656.42s` (ran all 4788). `--junitxml` **written** (758,953 bytes; parses tests=4788 failures=77 errors=17). **EXIT=1** (honest). Was: hard-exit ~58%, exit 0, no summary, junitxml never written. |
| TC2 | AC2 root cause | ✅ PASS | `test_post_shutdown_returns_202` → 1 passed. Fix joins the `shutdown` daemon thread INSIDE the `os._exit`+`time.sleep` patch window (mock fires, not the real exit), redirects `HARNESS_PORT_FILE` to a tmp path so the thread's unlink can't touch live discovery, and asserts `mock_exit.assert_called_once_with(0)`. |
| TC3 | AC3 regression guard | ✅ PASS | `test_12720_thread_leak_guard.py` → 6 passed. Locks classification: non-daemon flagged; benign daemon tolerated; **dangerous `shutdown` daemon flagged even as daemon** (the exact #12720 case); allowlist tolerated; preexisting/dead not flagged. **0 guard-induced failures across all 4788 tests** (grep of the full junitxml for "12720"/"thread-leak" → none) — proves no other test leaks the shutdown thread AND the guard doesn't false-positive. This is the preventive guard I recommended in the filing. |
| TC4 | AC4 no new failures | ✅ PASS | The 94 now-visible problems are ALL pre-existing (unmasked, not caused by #12720): **39** `test_agent_boundaries` (known, blocked on **#10360** — verified open: "Implement Responsibility compose slot"), **1** `test_compose_author_comments_11142`, **1** `test_vault` (skill's fix lands on main data, not this PR — expected to still fail on the bare branch), and **~53 environment-dependent live tests** (`test_comprehension_*` 35, `test_model_router_live` 13, `test_feat_9745_wake_mode_qa_live` 4, `test_feat_6581_wizard_reframing` 1) — confirmed env-dependent via `pytest.skip("claude CLI not available")` / `test_q1_blocked_not_defer_for_missing_api_key` (need live LLM/CLI absent in my verification env). |

### Disposition
PASS — defect A (the false-green masker) is definitively fixed: the suite now runs to completion,
prints a summary, writes junitxml, and exits with an honest code. The root cause is fixed test-side
(the /shutdown daemon-thread os._exit race), and the conftest thread-leak guard — the exact mechanism I
recommended — locks the regression with 6 self-tests and zero false-positives on the real suite. The
fix introduces no new failures; the failures it *unmasks* are pre-existing and out of #12720's scope.

### Non-blocking follow-ups (flagged, do NOT block ship)
1. **Defect B is triaged, not closed**: confirm test_vault's vault-frontmatter fix is actually on main
   before/at merge (verified only that it's absent from this PR's code diff). DM/skill to ensure main
   carries it so post-merge `test_vault` is green.
2. **~53 "live" tests ERROR/FAIL rather than cleanly SKIP when the claude CLI / API keys are absent**
   (some do `pytest.skip("claude CLI not available")`, others ERROR). In a keyless CI/local env this
   adds noise to the now-honest signal. Worth a separate test-hygiene issue: make live tests skip
   cleanly when their environment prerequisite is missing. NOT a #12720 gap.

Merge deferred to DM. Ship counter NOT bumped (DM owns).
