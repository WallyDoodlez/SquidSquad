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
