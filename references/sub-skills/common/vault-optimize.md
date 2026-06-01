---
slot: instructions
ordinal: 10
---

### Step — Vault Optimize (Quiet Cycle)

During quiet cycles, check if vault optimization is needed. This step runs AFTER the improvement scan check — if the scan ran this cycle, skip optimization.

**Config gate**: Check `Vault Optimize > Enabled` in `config.md`. If `no`, skip entirely.

**Activation**: Only run when the vault has 20+ notes AND this is a quiet cycle with no other work.

Run the optimizer:

```bash
python references/scripts/vault_optimize.py run
```

The script handles:
1. **Prune**: Auto-archives galaxy notes that are both stale (60+ days since update) AND orphaned (no inbound wikilinks). Never prunes notes created today.
2. **Confidence decay**: Downgrades confidence (high→medium after 60 days, medium→low after 120 days) for stale notes.
3. **Reindex**: Rebuilds `links` frontmatter from body wikilinks across all notes.
4. **Relevance scoring**: Computes scores based on link count + recency + confidence. Stored in `.squidsquad/vault/.relevance-index.json`.

**Pending questions**: If optimization surfaces questions that need human input (e.g., "Should these two similar notes be merged?"), add them to the queue:

```bash
python references/scripts/vault_optimize.py add-question --agent [ROLE] --note [path] --question "[plain language question]"
```

Questions use plain language — never expose vault internals (galaxy, frontmatter, wikilinks, PARAG). Describe notes by topic. All questions are skippable.

**Status bar**: The pending question count is shown in the status bar. PM mentions it in check-in. Human responds when ready.

If the vault is too small (<20 notes) or optimize is disabled, the script exits cleanly with no output.
