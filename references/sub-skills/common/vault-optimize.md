---
slot: instructions
ordinal: 10
---

### Step — Vault Optimize

Two jobs, two triggers:

- **Maintenance window** (pm only) — runs when the harness emits a `vault-maintenance` event (the scheduled window: notes whose `last_optimized` is missing or 14+ days old). Nothing else starts it; never run it on a quiet cycle on your own initiative.
- **Telemetry compaction** — on quiet cycles, compact your own shard.

Maintenance is **propose-only**: nothing is archived, deleted, merged, or rewritten automatically — every finding becomes a `pending` task, which is the human approval gate. Do NOT run `vault_optimize.py run`, `prune-scan`, or `decay-apply` — they are the retired v1 time-decay path.

#### Maintenance window (pm, on a `vault-maintenance` event)

1. **Queue**: `python references/scripts/vault_optimize.py analyze-queue` → JSON `queue` of `{slug, path}`. Empty queue → nothing to do.
2. **Contradiction analysis**: group the queued notes into clusters by shared tags or hub links. Per cluster, spawn a subagent (`model: "sonnet"`) that Reads the cluster's notes plus the active notes they wikilink to and returns every pair of **active** notes making claims that cannot both be true or both be followed, as JSON `[{slug_a, slug_b, topic, statement_a, statement_b}]` (or `[]`). A note that merely refines or narrows another is not a contradiction.
3. **File each contradiction** — never resolve one yourself:
   ```bash
   python references/scripts/vault_optimize.py file-contradiction --slug-a <a> --slug-b <b> \
     --topic "<topic>" --statement-a "<quote from a>" --statement-b "<quote from b>" --reporter [ROLE]
   ```
   It files a `pending` pm task and skips a pair that already has an open one, so file each note pair **once**: when two notes conflict on several points, name them all in `--topic` and the statements. Strip backticks from the quoted statements (Bash would execute them).
4. **Pruning review**: `python references/scripts/vault_optimize.py file-prune-review --reporter [ROLE]` — files one `pending` review task from the impressions report's buckets. `filed: false` with a reason (engine unavailable, no proposals, review already open) is fine — note the reason.
5. **Stamp**: `python references/scripts/vault_optimize.py mark-optimized --slugs <queued slugs, comma-separated>`, then commit the stamped notes on main with your normal vault writes. Stamp only notes whose analysis completed — an unstamped note is simply re-queued by the next window.

On approval of a filed task, retire a note by setting `status: archived` or `status: superseded` in place (per vault-protocol's update rules) — never by moving or deleting the file.

#### Telemetry compaction (quiet cycle)

```bash
python references/scripts/vault_optimize.py compact-telemetry --alias [ROLE]
```

A `skipped` result (engine unavailable, or instance id unprovisioned) is fine — note the reason and move on.
