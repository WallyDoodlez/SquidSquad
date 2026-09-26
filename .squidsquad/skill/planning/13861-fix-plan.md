# Fix plan -- #13861

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

PRD-VAULT-V2 P5 gap. (S5.1) Nothing schedules vault-optimize: the analyze pass only runs if a
PM quiet cycle happens to reach `step:cycle/vault-optimize` -- the v1 "hope a quiet cycle
notices" bug TRD 9.6 names. `last_optimized` (TRD 4.3) is never read or written, so there is no
14-day queue. (S5.2) The instance id is a P3 provisional per-clone mint (`wizard.py` step 5): every
clone gets its own UUID, the harness root clone (PM) has none (reads `unprovisioned`), and the
harness itself never mints, persists, or distributes an id (TRD 6.3 says it owns this).

## Intended direction

- S5.2: the harness owns the id. At boot it reads `SQUIDSQUAD_DIR/.instance-id` (gitignored) and
  mints a uuid4 there only if it is absent or empty, so the id survives restarts. Every clone's
  `.squidsquad/.instance-id` is then set to the harness id (production-only guard, the same one
  used for port and `.local-config`), so shards are `<harness-id>-<alias>.jsonl` as TRD 6.3 says.
  `/status` reports `instance_id`. The wizard's provision-time mint stays as the first mint, and
  the harness adopts whatever id that step wrote.
- S5.1: a harness `VaultMaintenanceScheduler` thread checks every 10 minutes whether a window is due
  (`Vault Optimize > Interval Hours`, default 24; the last window is stored in gitignored
  `.squidsquad/.vault-maintenance.json`). When a window is due it runs the deterministic
  `vault_optimize.py analyze-queue` (active notes whose `last_optimized` is missing or 14 or more
  days old, oldest first, capped). If that queue is non-empty, it emits a `vault-maintenance`
  event to the pm alias. This follows the `deploy-error`-to-pm precedent: a harness-originated
  operational signal. `POST /maintenance/vault-optimize` forces a window for the operator or the
  verifier.
- The judgment (contradiction detection) stays in an agent session. The default model is Claude,
  so the harness cannot run it via model_router. PM reacts to the event through the rewritten
  `vault-optimize` sub-skill: it reads the queued notes and uses sonnet subagents per cluster to
  find contradictions. Each contradiction is filed by `vault_optimize.py file-contradiction`, a
  deterministic `pending` HITL task with dedup, and is never applied. Pruning proposals from the
  impressions report are filed by `vault_optimize.py file-prune-review`, also deterministic and
  deduped. Last, `vault_optimize.py mark-optimized` stamps the queue.
- Out of scope: compaction stays per-agent. It is owner-only in the owner's own clone (TRD 6.5
  invariant 1), and the harness cannot commit in agent clones. S5.3 (HARNESS-ARCH doc) rides the
  #13854 PM umbrella; the facts are handed over by comment.

## Impact

- New config key `Vault Optimize > Interval Hours` (default 24, so no config.md edit is needed).
  Two new gitignored files: `.squidsquad/.vault-maintenance.json` and its `.tmp`.
- Upgrade: at the first harness boot after deploy, clones that carry a P3 per-clone id are
  re-pointed to the harness id. Their old `<old-id>-<alias>.jsonl` shards are still read and
  summed (TRD 6.3 sum-at-read), so no telemetry is lost. They just freeze, and compaction no
  longer touches them.
- Agent instructions change (event-mode-contract Case E bullet, vault-optimize sub-skill, PM L2
  step prose). All roles need a recompose and a reboot, which is handled by the deploy-signal.
  This needs a CQ spec, so PM is asked to add a comprehension AC.

## Vault context consumed

- [[learning-tests-must-not-mutate-shared-live-state]] -- instance-id/maintenance tests use tmp SQUIDSQUAD_DIR / patched paths, never the live `.squidsquad/.instance-id`
- [[learning-default-port-fallback-is-live-egress-trap-in-tests]] -- scheduler/filing tests stub tracker subprocess + event emit; no live egress
- [[decision-vault-subagent-model-sonnet]] -- PM's contradiction analysis subagents pinned to sonnet
- [[learning-git-ops-helpers-pin-repo-root-not-cwd]] -- vault_optimize paths are module globals; tests patch VAULT_DIR rather than chdir

## Applicable rules

- None matched (searched rules lane: harness, vault, telemetry, optimize, tracker, hitl)
