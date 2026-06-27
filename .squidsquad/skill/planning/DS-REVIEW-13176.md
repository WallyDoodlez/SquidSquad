# Code Review — #13176 (deploy stage=commit empty-detail + benign re-trigger)

**Reviewer**: DeepSeek 402 (Insufficient Balance, confirmed this session) → **Sonnet fallback** (per [[feedback_model_router_auto_fallback]]).
**Scope**: `references/scripts/harness.py` (`_stage_composed_outputs`, `_run_deploy_sequence` commit step) + `tests/test_harness_deploy_12912.py` (4 regression tests).

## Verdict: NO_BLOCKING_FINDINGS

Re-trigger elimination confirmed complete: no-net-change deploy → `_stage_composed_outputs` False → `_bump_compose_checksum` + `_respawn_after_deploy` (checksum advances, no deploy-error). Commit-detail precedence (`stderr or stdout or fallback`) correct — hook/lock failures (stderr) preferred, benign 'nothing to commit' (stdout) caught, field never empty.

## Findings & disposition (all LOW, all dispositioned — no code change)

1. **LOW — `_stage_composed_outputs`** — `git diff --cached --quiet` exit ≥2 (corrupt index) is treated as "has diff" → proceeds to commit. → **NOT CHANGED** (dispositioned): the fallthrough is *safer* than aborting — a genuine error then surfaces diagnosably via the commit step (with this PR's detail fix) and §11 recovery leaves the checksum unadvanced (retriggerable). Aborting on ≥2 would add a new failure path that could kill a recoverable deploy. Reviewer agreed "not blocking … fallthrough already safe."

2. **LOW — tests** — no single integration test chains both fixes (no-diff → False → no commit reached); the two halves are covered separately (`TestStageComposedOutputs.test_returns_false_when_add_ok_but_no_staged_diff` + `TestRunDeploySequence.test_no_change_is_clean_success`). → **NOT CHANGED** (dispositioned): reviewer called it "acceptable coverage depth"; both halves are unit-tested and the `_run` harness mocks `_stage_composed_outputs` by design.

3. **LOW — `_stage_composed_outputs`** — a persistent `git add` failure (all adds fail) → empty `staged_paths` → False → clean respawn with no error (add-failure invisible). → **NOT CHANGED** (dispositioned): pre-existing behavior, outside this PR's scope; very unlikely (composed files just written by compose in the same sequence).

## Gate
Full static gate **exit 0** (see PR). Targeted `test_harness_deploy_12912`: 48 passed (4 new).
