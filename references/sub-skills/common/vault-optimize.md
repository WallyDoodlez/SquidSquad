---
slot: instructions
ordinal: 10
---

### Step — Vault Optimize (Quiet Cycle)

During quiet cycles, run vault maintenance. This step runs AFTER the improvement scan check — if the scan ran this cycle, skip optimization.

**Activation**: always-on, no toggle. Run only when the vault has 20+ notes AND this is a quiet cycle with no other work (#13043).

Maintenance is **propose-only**: pruning is decided by usage telemetry, not age, and nothing is archived, deleted, merged, or rewritten automatically. Do NOT run `vault_optimize.py run`, `prune-scan`, or `decay-apply` — they are the retired v1 time-decay path.

1. **Pruning proposals** from the engine's impressions report:
   ```bash
   python references/scripts/vault_optimize.py propose-prunes
   ```
   - `engineUnavailable: true` → skip this step this cycle; state the `reason` in your iteration log.
   - Otherwise each proposal carries a bucket: `stale` (was used, not recently → `archive`), `surfaced-never-used` or `cold` (→ `review`).
   - If there are proposals, file **one** task for the human to review — never act on them yourself. → run sub-skill: `tracker-protocol` — **Feature task** shape, title `"Vault pruning review: <N> notes"`, body listing each proposal's slug, bucket, and evidence, `--role pm`, `--priority low` — it files as `pending`, which is the human approval gate. Skip filing if an open vault-pruning review task already exists.
   - On approval, retire a note by setting `status: archived` (per vault-protocol's update rules) — never by moving or deleting the file.

2. **Contradictions**: while reading notes for step 1, if two active notes contradict each other, file a separate task for the human (same shape, title `"Vault contradiction: <topic>"`, both `[[slugs]]` and the conflicting statements in the body, filed as `pending`). Never resolve a contradiction yourself.

3. **Telemetry compaction** of your own shard:
   ```bash
   python references/scripts/vault_optimize.py compact-telemetry --alias [ROLE]
   ```
   A `skipped` result (engine unavailable, or instance id unprovisioned) is fine — note the reason and move on.

If the vault has fewer than 20 notes, skip the whole step silently.
