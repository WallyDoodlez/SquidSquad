# FEAT-PM-1278 Context — Vault Entity Extraction + Connection Mining

## Scope

Replace vault-remember's subjective "is this significant?" gate with a three-layer knowledge absorption system: extract entities from cycle context, compare against existing vault, and mine connections between notes. Makes the vault continuously absorbing rather than passively waiting for "significant" events.

## Locked Decisions (human decided)

- **Trigger**: Every non-quiet cycle, extract from running context (not limited to human messages — includes all context the agent processed during the cycle)
- **Architecture**: New `vault_entity.py` script for pattern-matching entity extraction. Agent calls it, reviews results, then creates/updates vault notes. Testable and deterministic for the pattern-matching layer, LLM handles judgment calls.
- **Connection mining**: Extend vault-check Level 1 with connection suggestions. After each vault-create/update, vault-check scans related notes and suggests wikilinks for implicit relationships. Centralized, runs automatically.
- **Scope**: PM-only for v1. PM is the primary human interface. Expand to other agents later if data shows value.

## Dev Discretion (dev agent can choose)

- Entity type categories and detection patterns in vault_entity.py
- How "running context" is passed to the extraction script (iteration log, working state, or explicit context dump)
- Threshold for fuzzy matching against existing vault notes
- Format of connection suggestions from vault-check
- Whether to add a `--suggest-links` flag to vault-check or make it automatic

## Side Effect Mitigations (required)

- Write budget (max 2 notes per cycle) still applies — extraction may find many entities but only top 2 are written
- vault-optimize still handles pruning/confidence decay — growth is controlled
- Existing vault-remember gates (dedup, reusability) remain for quality control
- Connection mining must not create circular or redundant wikilinks
- Token cost should stay under ~3000 additional tokens per active cycle

## Upgrade Path (required)

- New script: `references/scripts/vault_entity.py`
- Template changes: vault-remember sub-skill updated to call extraction
- vault-check extended with connection suggestion logic
- compose.py deploy-all regenerates templates
- No new config values needed
- Graceful degradation: old templates skip extraction, vault still works

## Out of Scope

- Extraction by non-PM agents (v2)
- Semantic/embedding-based search (TASK#19)
- Automated entity classification (LLM handles this inline)
- Changes to vault-optimize or vault structure
