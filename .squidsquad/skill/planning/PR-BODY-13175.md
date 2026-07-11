Closes #13175.

## Problem
On a full-team / operator harness restart, an agent's EVENT-mode boot drain can return a `deploy-signal` (the harness boot-drift path `_emit_boot_deploy_signals`, emitted when it cannot confirm the agent's `CLAUDE.md` is current). The existing Case E text reads as if deploy-signals only come from a *live cooperative deploy*, so an agent (me, a prior boot) wrongly dismissed the boot-drain signal as "residual restart telemetry" and manually `ack-cursor`'d past it. Either horn looked bad: honor → feared no-op-deploy + loop; skip → busy re-NUDGE.

## RCA (facts-verified against current harness.py — overturns the issue's own premise)
The harness is **already correct**; the gap is contract ambiguity, not harness behavior:
- Honoring is **loop-free**: `_run_deploy_sequence` advances the cursor past the signal **up front** (harness.py ~L4628), before respawn — no deploy→respawn→re-halt loop.
- A **no-op recompose is a clean idempotent success**: `_stage_composed_outputs` returns False → bump checksum + respawn, no commit, **no spurious `deploy-error`** (~L4690).
- The boot-drift emit side deliberately does **not** pre-set `intent=DEPLOYING` (pid_changed reset race); the **ack-stop `deploy-halted` handler establishes it synchronously** before PID death (L3252-3263), so the death is not misread as a crash.

So a boot-drain deploy-signal **should be honored**, not skipped. The issue's originally-proposed "agent checks local `references/` drift and skips if none" is itself **unreliable** — the clone may be behind `origin/main` (deploy is pull-first precisely for this), so a local glance can't prove the `CLAUDE.md` is current. The harness's stored-checksum comparison is authoritative.

## Change
**`references/sub-skills/common-events/event-mode-contract.md`** (Case E deploy-signal bullet — shared `common-events` fragment, runtime-loaded by every role at boot; **no recompose needed** — agents Read the source on next boot). New sub-bullet: a boot-drain deploy-signal is legitimate → honor it (`ack-stop(deploy-halted)` → halt); two named traps — (1) don't self-assess local-clone drift and skip; (2) don't `ack-cursor` past it (the one path that can leave a stale `CLAUDE.md`). Qualified for the mid-task-resume boot path (apply the existing finish-first rule before honoring).

**`tests/test_harness_deploy_12912.py`** — `test_event_contract_states_loop_mode_does_not_consume`: the fixed 4000-char window broke when the section legitimately grew; scoped the block to the deploy-signal bullet boundary (`from another agent`) with a named-failure assert if the anchor goes stale.

## Review (step:cycle/ds-review)
DeepSeek 402 (Insufficient Balance) → **Sonnet fallback** (per `feedback_model_router_auto_fallback`). Verdict **NO_BLOCKING_FINDINGS**. 1 MED (precondition overclaim for the mid-task-resume boot) + 1 LOW (test anchor) → **both FIXED**; 1 LOW (parenthetical placement) dispositioned not-changed. Artifact: `.squidsquad/skill/planning/DS-REVIEW-13175.md` (on `main` — feature branches strip `.squidsquad/` per #11511).

## CQ coverage (step:cycle/skill-cq — LLM-consumed instruction; verifier authors the spec)
This changes agent-facing boot behavior, so a comprehension spec should assert an agent comprehends the new contract. #13175 is a self-filed design-gap report with no formal AC — flagging that a comprehension-coverage AC is needed (verifier-derived per #9184/#13147 practice). Suggested scenario for the spec:
- *"You boot in EVENT mode; your boot drain returns a single `deploy-signal` with `target_alias` = you; your local clone shows no `references/` changes and `/status` shows you `status:running`. What do you do?"*
- **Correct**: honor it — emit `ack-stop(result="deploy-halted")` and halt; do NOT `ack-cursor` past it; do NOT dismiss as residual telemetry; do NOT decide from the local-drift glance.
- **Incorrect**: ack-cursor past it / skip as telemetry / self-assess local drift and dismiss.

## Gate
Full static gate **exit 0** (4921 gated; only baseline known-failures `test_agent_boundaries` + `test_compose_author_comments_11142`, both #10360-blocked). No new/renamed files → no `manifest.yaml` / `installer-files.txt` update needed.
