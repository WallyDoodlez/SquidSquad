# Fix plan -- #14131 (+ #14132, same PR)

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

- #14131: the health poller's deploy-window fallback (`harness.py`, dead branch
  under `agent.intent == AgentState.INTENT_DEPLOYING`) only recovers an agent
  whose PID is DEAD. A live agent that never emits ack-stop (deaf session,
  #14114) is forced to `status="running"` every poll and sits at
  intent=deploying forever: never respawned, lane frozen (dm, 110 min, 47
  unprocessed events).
- #14132: `/restart`'s idle fast path (#8689) kills the PID, but an idle agent
  has `waiting_since` set, so `active_pause()` returns "waiting" and the #12458
  guard holds the reboot for up to `WAITING_MAX_SECONDS` (1800s). Only the force
  path stamped `operator_force_at`, and the pause guard never consulted it.

## Intended direction

- #14131: `AgentState.deploy_stall_action(now)` classifies a live deploying
  agent. Past `_DEPLOY_WINDOW_SECONDS` and idle (no heartbeat within the
  window), or past `_DEPLOY_ALIVE_CEILING_SECONDS` (1800s) regardless, it is
  recovered through the existing `_run_deploy_sequence` (force-kill, respawn,
  cursor advanced past the newest deploy-signal). Still active past the window,
  one `deploy-error` (stage=halt-timeout) goes to pm per deploy intent. Actions
  run after the poller's non-reentrant state lock is released. Every deploy
  thread goes through `_start_deploy_thread`'s in-flight guard, so the ack-stop
  path and the poller never double-start.
- #14132: stamp `operator_force_at` for any immediate `/restart` kill (idle or
  force), and have the pause guard skip `operator_force_death()`. A failed kill
  clears the marker.
- Not changed: the dead-PID fallback, the ack-stop deploy-halt flow, the #12458
  hold for an unexplained death, and the graceful busy restart.

## Impact

- `references/scripts/harness.py` only (plus a new test file). It takes effect
  on the next harness restart. An idle restart is now classified as non-crash
  (no #12244 streak increment), matching force.

## Vault context consumed

- [[learning-tests-must-not-mutate-shared-live-state]] -- tests drive in-process HarnessState with `save_state` mocked; no live `.harness-state.json` or event-state writes
- [[learning-default-port-fallback-is-live-egress-trap-in-tests]] -- `_emit_event` is mocked in the surface test; the deploy sequence is mocked, so there is no live harness egress
- [[decision-pid-primary-liveness]] -- recovery keys off the image-verified live PID plus the deploy clock; the activity heartbeat only picks between surface and recover

## Applicable rules

- None matched (searched rules lane: harness, deploy, liveness, testing)
