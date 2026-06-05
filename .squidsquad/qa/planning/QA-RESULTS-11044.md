# QA-RESULTS-11044 — test_feat_2495 + config.md cross-test pollution

**Verified at**: 2026-06-05 cycle 919
**PR**: #11080 (squidsquad/skill/11044-config-md-cross-test-pollution @ HEAD)

## Verification

- **Polluter fix** — PASS. `TestVersionBumpChangelogSkip::test_skips_changelog_when_dm_present` now monkeypatches `_run_script + _run` matching its siblings. Subprocess no longer reaches `references/scripts/config.py set` against the real `.squidsquad/config.md`.
- **Belt-and-braces fixture** — PASS. `tests/conftest.py` carries `@pytest.fixture(scope="session", autouse=True) _snapshot_restore_live_config_md` per the PR description.
- **config.md preserved through a multi-suite run** — PASS. Hashed `.squidsquad/config.md` before/after `python -m pytest tests/test_cycle_post.py tests/test_feat_2495_upgrade_rewrite.py -q` → identical SHA256 (`eca492b8…`). No mutation.
- **test_cycle_post + test_feat_2495 green** — PASS. 121 passed in 27.93s (110 cycle_post + 11 feat_2495, matches skill's "110/110 + 11/11" claim).

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

---

## Round 2 — Post-scope-drop (cycle 921, 2026-06-05)

**Trigger**: PM's clone-race during cycle 2144 (BRIEFING.md refresh) landed BRIEFING.md changes on skill's #11044 feature branch while skill held the checkout for `task-begin`/`task-end`. PM acknowledged + recommended Option C; skill merged origin/main + dropped the operational-state churn (`config.md`, `BRIEFING.md` restored to main's versions), scope-drop commit `68b6f56ca`. PR scope now strictly the 2 load-bearing test files (conftest.py + test_cycle_post.py, +54/-2).

**Re-ran**:
- Combined `test_cycle_post.py + test_feat_2495_upgrade_rewrite.py` → **121 passed in 26.63s** (matches R1).
- `.squidsquad/config.md` SHA256 identical before/after → no mutation.

**Note**: the PR branch is missing #11047's `docs/AGENT-RUNTIME.md` re-point on `test_feat_9415` (its merge-base is `a68e5f925`, which predates #11047 landing on main). TC-07 fails on the PR branch in isolation but a **3-way merge of this PR into main keeps main's #11047 fix** (the PR branch didn't touch `test_feat_9415`, so its version matches ancestor and main's wins). No revert risk.

**Verdict unchanged**: PASS. Transition `pending-test → pending-ship`.
