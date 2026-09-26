# Fix plan -- #14114

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

The event-mode contract (`event-mode-contract.md` Monitor-exit rule and
Harness-Loss Recovery) and the L1 `instructions.md` Monitor rule said "end your
session", relying on the harness seeing the `claude` PID die. An LLM agent
cannot end its own process (#13077). Ending the turn leaves the PID alive at
intent=running, the health poller sees a healthy agent, and the session sits
deaf. This was reproduced live twice: PM (2026-09-26 10:51) and dm (cursor
frozen, 47 events, which also caused #14131).

## Intended direction

- New deterministic helper `cycle.py end-session [role]` (role defaults to
  `SQUIDSQUAD_ROLE`). It POSTs `/agents/<role>/restart?force=true`: an immediate
  kill, stamped as a requested kill so the #14132 pause-guard bypass applies
  and the next poll respawns. On an unreachable harness or a refused restart it
  exits 1 and prints "end your turn".
- The instructions become two steps: run `end-session`, then end the turn.
  Being killed mid-command is expected; a dead harness is restarted by the
  operator.
- Force (not graceful) so the kill is immediate and always stamped. A graceful
  restart of a non-idle agent falls to the 60s force-kill net, which does not
  stamp, and the pause guard could then hold the respawn.
- AGENT-RUNTIME's two mechanism sentences are repointed to the helper.
- Not changed: expiry re-arm, harness-initiated halts (exit-42,
  deploy-signal), and loop mode.

## Impact

- `references/scripts/cycle.py`, `event-mode-contract.md` (runtime-loaded),
  `references/roles/instructions.md` (L1, composed into every role's
  CLAUDE.md, which takes effect on recompose/deploy), `docs/AGENT-RUNTIME.md`,
  and a new test file.
- Agents already running keep the old wording until they are respawned.
- Depends on #14132 (merged in #14152) for the prompt respawn of a force kill.

## Vault context consumed

- [[learning-default-port-fallback-is-live-egress-trap-in-tests]] -- every end-session test passes an explicit opener/port or mocks `_discover_port`; an unmocked call would force-restart a live agent
- [[learning-tests-must-not-mutate-shared-live-state]] -- the real-endpoint test drives the harness app in-process via TestClient with the kill, boot and save seams mocked

## Applicable rules

- None matched (searched rules lane: harness, event-mode, monitor, restart)
