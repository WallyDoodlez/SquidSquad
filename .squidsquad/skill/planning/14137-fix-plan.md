# Fix plan -- #14137

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`vault-synthesis.md` Activation fired "after 5 consecutive quiet cycles",
counted in PM working state, and the PM L2 step said "every 5 quiet cycles".
Event-mode PM has no quiet cycles and keeps no such counter, so synthesis
never ran: `.squidsquad/pm/.last-synthesis` has been untouched since
2026-05-31. The P4 engine-backed rewrite was unreachable, and P5 (#13861) put
only optimize on the harness schedule.

## Intended direction

- Ride the #13861 harness maintenance window. `run_vault_maintenance_window`
  decides `synthesis_due`: no signal sent yet, or the last one at least
  `Vault Optimize > Synthesis Interval Days` old (default 7, clamped to a
  weekly floor).
- One `vault-maintenance` event goes to pm when notes are queued OR synthesis
  is due, with `synthesis_due` in the payload. `last_synthesis_signal_at`
  persists in `.vault-maintenance.json`. An analyze failure blocks only the
  optimize half.
- `POST /maintenance/vault-optimize?synthesis=true` forces the signal (AC2
  live fire), and GET reports the interval and the last signal.
- PM: `vault-synthesis.md` Activation and the L2 step now key on
  `synthesis_due: true`, with no counting. The Case E bullet routes
  `queued` > 0 to optimize and `synthesis_due` to synthesis.
- Freeze (AC3): with `vault-writes-per-cycle` = 0, synthesis makes no vault
  writes. The drafted posture goes into the pending review task; the sentinel
  and log line still run.
- Config key plus default, the catalog row, and VAULT-ARCH §7.4 are updated.

## Impact

- `harness.py` (takes effect on harness restart), `config.py`,
  `event_catalog.py`, the PM L2 instructions (recompose), the PM
  `vault-synthesis` sub-skill, `event-mode-contract.md`, and VAULT-ARCH.
- Existing installs get the default 7 days. Their config.md needs no change.

## Vault context consumed

- [[decision-harness-schedules-agent-judges]] -- exactly this split: the harness decides when synthesis is due; the PM sub-skill judges what (vault-size gate, recent writes, cross-agent convergence) and files the human-gated review task
- [[learning-tests-must-not-mutate-shared-live-state]] -- window tests use a tmp `.vault-maintenance.json`, a stubbed analyze-queue subprocess and captured emits; nothing touches the live harness state

## Applicable rules

- None matched (searched rules lane: vault, synthesis, harness, maintenance)
