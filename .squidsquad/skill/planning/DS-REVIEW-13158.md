# Code review — #13158 (deploy-pull --no-rebase fix)

**DeepSeek (model_router) unavailable (HTTP 402 Insufficient Balance) — review by Claude/Sonnet subagent per the auto-fallback rule ([[feedback_model_router_auto_fallback]]).**

## Verdict: NO_FINDINGS (core questions a–e). 3 confirmatory notes.

The fix changes the deploy-sequence pull from `["pull","--ff-only","origin","main"]` to `["pull","--no-rebase","--no-edit","origin","main"]`.

- **(a)/(b) merge-commit safe for the downstream steps** — after `--no-rebase` succeeds on a diverged branch, HEAD is a merge commit; `compose.py deploy` runs off working-tree files (unaffected), `_stage_composed_outputs` stages specific named files (not `git add -A`, so parent pointers irrelevant), and the subsequent commit+push push both the merge and compose commits cleanly.
- **(c) conflict → §11** — a genuine merge conflict returns non-zero from the pull → `_deploy_recover_and_respawn(role, "pull", ...)`. Correct.
- **(d) push-failure no-retry path** — unchanged; the updated comment is accurate (the next deploy pass's merge-pull reconciles the divergence).
- **(e)/non-interactive** — `_git_in_clone` uses `subprocess.run(capture_output=True)` → no terminal; `--no-edit` suppresses the merge-commit editor → no hang.

No regressions found.
