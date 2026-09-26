---
type: decision
tags: [harness, scheduling, vault, model-routing]
created: 2026-09-26
updated: 2026-09-26
status: active
owner: worker
last_optimized: 2026-09-26
---

# Harness schedules; an agent judges

## Context

#13861 (PRD-VAULT-V2 S5.1): the vault-optimize analyze pass had to be harness-scheduled ("not hope a quiet cycle notices"), but its core step, contradiction detection, is LLM judgment. The obvious move is to have the harness call `model_router.py`. That fails on a default install: the default model route is `claude`, and `route()` answers "claude" by exiting 1 (delegate to the Agent tool). The Agent tool exists only inside an agent session, so a harness-side call would silently skip the judgment everywhere DeepSeek is not configured.

## Decision

For harness-timed work that needs judgment, split it on the deterministic/probabilistic seam:

- The **harness owns timing**. A scheduler thread with persisted gitignored last-run state, plus a force endpoint.
- **Deterministic prep runs in a script**. Here that is `vault_optimize.py analyze-queue`.
- If there is work, the harness **emits a targeted event** to the owning agent (the `deploy-error`-to-pm precedent).
- The **agent judges**, using sonnet subagents.
- Every forge write the judgment produces goes through **deterministic, deduped filer scripts** (`file-contradiction`, `file-prune-review`). The agent never shapes tickets by hand.

## Rationale

- Keeps the trigger deterministic and the judgment on the model the install actually has.
- Filing through scripts means dedup, title shape, and the `pending` HITL gate hold no matter how the model phrases its output.
- An event rather than a forge ticket avoids giving a maintenance chore the full open → pending-test → ship lifecycle. The durable outputs (HITL tasks, stamped `last_optimized`) still land on the forge and in git.

## Related

[[harness]] -- scheduler + event emit live in `harness.py` (`run_vault_maintenance_window`). Same seam discipline as [[decision-vault-subagent-model-sonnet]].
