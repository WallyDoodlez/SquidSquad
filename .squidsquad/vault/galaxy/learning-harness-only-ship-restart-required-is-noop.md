---
type: learning
role: dm
created: 2026-06-19
tags: [delivery, harness, restart, recompose, gotcha]
owner: dm-lead
status: active
confidence: high
source: observation
---

# A harness.py-only ship triggers a restart-required that is usually a NO-OP

## Context

Delivering a ship whose diff is **`harness.py` (+ tests) only** — e.g. #12837 (eviction-marker bug), #12906 (recompose ensure-main). Two restart concerns get conflated at ship time; they are different and must be reasoned separately.

## The two restarts are NOT the same

1. **Harness restart — genuinely needed.** The *running* harness predates the merged fix, so harness-code changes only take effect after a harness relaunch. This folds into the pending harness-restart window (operator/supervised-launcher), deferred per standing operator directive. Note it in the ship comment; do NOT self-trigger.
2. **`l4-recompose` restart-required (target=dm) — usually a spurious NO-OP.** The harness emits a recompose `restart-required` after a merge regardless of whether composed output changed (the `l4_file_watcher` over-emit, #12895). A harness.py-only ship changes **no** L4/template/sub-skill source, so your composed `CLAUDE.md` does not change — there is nothing to pick up.

## How to tell it's a no-op (gate before any self-restart)

- `git status --short .squidsquad/dm/CLAUDE.md` → **empty** (composed output unchanged; cross-check `git log -1` shows last touch was an earlier unrelated commit), AND
- `/status` shows your `intent: running` (NOT flipped to restarting/stopping) → the signal is **advisory**, not a forced exit-42.

If both hold: treat as no-action, stay up, defer per operator. Do **not** self-restart. Confirmed twice (2026-06-14 no-op; 2026-06-19 #12837). The 2026-06-14 run also found `/quit` is itself a no-op in a live event-mode session — another reason not to chase the restart.

## Durable fix shipped (#12912, 2026-06-20)

#12895 Phase 2 (#12912, SHIPPED) makes the **deploy-signal the sole recompose path** (pull-first per-clone) and **Closes #12397** — the harness will fire a recompose/restart signal *only on actual post-compose alias drift*, not on every merge. So the spurious no-op `restart-required` documented here stops **once the harness is restarted** to pick up the new `harness.py`. Until that restart, the running (pre-#12912) harness keeps over-emitting, so the git-clean + intent-running no-op gate below remains the live mitigation in the interim.

## Direct root-cause gate shipped (#13303, 2026-06-28)

#13303 (DM-shipped 2026-06-28, PR #13314, `l4_file_watcher.py`) adds the **content-change gate at the source**: `recompose_for_role_class` now hashes the deployed `CLAUDE.md` **pre/post compose** and emits `restart-required` **only when the composed output actually changed** (reader error fails safe to emit; `compose-failed` path untouched; gate ON in prod via `start_watcher`/`recompose_path`, legacy direct-callers preserved). This is the targeted cure for the `l4_file_watcher` over-emit described above — complementary to #12912 (which made deploy-signal the sole recompose path). **Effective only after a harness restart** (the running watcher predates the fix), so until the operator-paced restart lands, the git-clean + intent-running no-op gate above remains the live mitigation. Fittingly, this exact session received one of these spurious `restart-required(l4-recompose, target dm)` events at ~04:10 and correctly declined it — then shipped the fix at ~04:47.

## Same gate applies to a `deploy-signal` (boot-drain or mid-session) — and #13032 changes its semantics

A **spent/stale `deploy-signal`** behaves exactly like the spurious `restart-required`: a no-op you must NOT respawn on. Observed 2026-06-20 boot — 3 boot-drain `deploy-signal` events (target=dm) from a prior harness lifetime. Same gate proves them spent: `git diff <local-HEAD>..origin/main -- ".squidsquad/*/CLAUDE.md"` = **empty** (zero composed drift) AND `/status` intent = `running` (not `deploying`). Both held → acked the events, did **NOT** emit `ack-stop(deploy-halted)` / `/quit`. Emitting deploy-halt on a stale signal triggers a pure no-op respawn — the exact #13032 bug.

**Post-#13032 (SHIPPED 2026-06-20) the deploy-signal semantics split:**
- A **LIVE** deploy-signal (intent flipped to `deploying`, real composed drift to pick up) → the new Case E contract (event-mode-contract.md) mandates the agent **/quit after `ack-stop(deploy-halted)`** so its process exits and the harness respawn isn't singleton-blocked. This is the cure for the old "halt without exit = silent no-op."
- A **STALE/SPENT** deploy-signal (zero drift + intent `running`) → still a no-op; decline, ack, stay up.
- The discriminator is the **same drift + intent gate** above. #13032 Part B also makes a failed respawn surface a **LOUD `deploy-error` to pm** instead of the old silent settle-to-starting no-op.
- Picked up at each agent's **next restart pull** (event-mode-contract.md is a runtime-loaded common-events fragment, #12506-style) — until reboot, a running agent won't /quit on a live deploy-signal, but Part B's loud error replaces the silent no-op in the interim.

## Apply

Scope-gate every ship: harness.py-only / runtime-loaded-fragment / test-only diffs need **no recompose and no agent reboot** (see [[pattern-runtime-loaded-subskill-change-no-recompose]]); config.md/template/sub-skill-source diffs do. Distinguish the spurious recompose `restart-required` / spent `deploy-signal` from a real one via the git-clean(composed) + intent-running gate above. Distinct failure from [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]] (which is a behind-clone pushing a revert, not a benign no-op).
