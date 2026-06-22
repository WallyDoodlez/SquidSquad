Closes #13176.

## Problem
On a harness deploy/recompose, `_stage_composed_outputs` returned `True` whenever `git add` exited 0 — but **`git add` of an unchanged file exits 0 while staging nothing**. So when the composed output already matched HEAD (the common no-net-change deploy), it returned `True`, the caller ran `git commit`, which failed benignly with `nothing to commit, working tree clean` — written to **stdout**, exit non-zero, **empty stderr**. Two impacts (both confirmed):
1. **Undiagnosable**: the `deploy-error stage=commit` event sourced `commit.stderr` only → **empty `detail`** (PM observed `detail: ""`).
2. **Re-trigger risk**: that benign "failure" routed through §11 recovery, which by design does NOT advance the compose checksum → the deploy re-fires on the next pass (PM logged this as a recurring `stage=commit` pattern across boots).

## Root cause confirmed
`_stage_composed_outputs` keyed on `add.returncode == 0` rather than on whether an actual diff got staged. Verified by reading harness.py.

## Fix
**`references/scripts/harness.py`**
1. **Root** — `_stage_composed_outputs` returns `True` only if `git diff --cached --quiet -- <staged paths>` reports a real staged diff (exit non-zero). The no-net-change case now returns `False` → the caller's **existing clean no-op success path** (`_bump_compose_checksum` + `_respawn_after_deploy`) runs: checksum advanced, **no deploy-error, no re-trigger**.
2. **Defense-in-depth** — the commit-failure `detail` now combines `commit.stderr.strip() or commit.stdout.strip() or "<fallback>"`, so a *genuine* commit failure (now the only way to reach that branch) is never empty/undiagnosable.

**`tests/test_harness_deploy_12912.py`** — +4 regression tests: `TestStageComposedOutputs` (False on add-ok-but-no-staged-diff [the regression]; True on real diff; False + no diff-probe when no composed files exist) and `test_commit_failure_detail_combines_stdout_13176` (stdout-only commit failure → non-empty diagnosable detail).

## Review (step:cycle/ds-review)
DeepSeek 402 → **Sonnet fallback** (per `feedback_model_router_auto_fallback`). Verdict **NO_BLOCKING_FINDINGS**; 3 LOW, all dispositioned no-change (diff-probe error fallthrough is *safer* than aborting; coverage depth acceptable; the `add.returncode` add-failure-invisibility is pre-existing/out-of-scope). Artifact: `.squidsquad/skill/planning/DS-REVIEW-13176.md` (on `main`).

## Gates / scope
Full static gate **exit 0** (only baseline known-failures `test_agent_boundaries` + `test_compose_author_comments_11142`, both #10360-blocked). Deterministic harness code → **no CQ** (not LLM-consumed). **No manifest update** (no new/renamed files). Related (not duplicates): #13158 (deploy stage=pull benign-divergence, analogous prior fix), #13175 (deploy-signal boot-drain), #13036 (respawn hardening).
