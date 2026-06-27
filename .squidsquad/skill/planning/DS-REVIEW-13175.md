# Code Review — #13175 (Case E boot-drain deploy-signal liveness)

**Reviewer**: DeepSeek 402 (Insufficient Balance) → **Sonnet fallback** (per [[feedback_model_router_auto_fallback]]).
**Scope**: `references/sub-skills/common-events/event-mode-contract.md` (Case E deploy-signal bullet — shared fragment, high blast radius) + `tests/test_harness_deploy_12912.py` (loop-mode-exemption assertion robustness).

## Verdict: NO_BLOCKING_FINDINGS

The core guidance — honor a boot-drain deploy-signal, don't `ack-cursor` past it, don't self-assess local-clone drift — is consistent with the existing Case E text and the verified harness facts (cursor advanced up front ~L4628; no-op recompose clean ~L4690; ack-stop handler sets `intent=DEPLOYING` synchronously on the boot-drift path L3252-3263).

## Findings & disposition

1. **MED — event-mode-contract.md** — "you **already** satisfy the on-`main`/clean-tree precondition" overclaims: a boot that **resumes an in-progress task** (Case A step 2, before the step-4 drain) is on a feature branch / dirty tree, so the precondition is NOT yet met; the existing finish-first rule should govern. → **FIXED**: qualified to "in the common restart-while-idle case … (If your boot instead resumed an in-progress task onto a feature branch before draining, the precondition is not yet met — apply the finish-first rule from the bullet above …)".

2. **LOW — event-mode-contract.md** — the `intent=DEPLOYING`-not-pre-set parenthetical is low-visibility (buried in the second trap sub-bullet); an LLM might conflate boot-drift with the live-deploy path. → **NOT CHANGED** (dispositioned): the note is factually correct and informational only — the *agent* takes no action on intent (the harness does); it sits correctly in the anti-loop trap where the reasoning belongs. Moving it risks awkwardness for marginal lift.

3. **LOW — test_harness_deploy_12912.py** — the `from another agent` boundary fell back to a 6000-char window if the anchor is absent (no vacuous-pass risk confirmed, but silent). → **FIXED**: added `assertNotEqual(end, -1, …)` so a stale/renamed anchor is a named failure rather than a silent fallback; removed the 6000 fallback.

4. **LOW — event-mode-contract.md** — "no `references/` drift locally does NOT prove your CLAUDE.md is current" is correct and well-motivated. → no change needed.

## Gate
Full static gate **exit 0** (4921 gated; baseline known-failures `test_agent_boundaries` + `test_compose_author_comments_11142` only, both #10360-blocked). Targeted: `test_harness_deploy_12912` + `test_event_mode_fragments` 113 passed.
