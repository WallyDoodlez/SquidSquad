# FEAT-SKILL-922 Context — SQLite Scan Index

## Scope

Replace flat scan-history.md targeting with a SQLite-backed scan index that tracks file coverage, git churn, cross-role interest, and human acceptance rates to produce a composite score for smarter improvement scan targeting.

## Locked Decisions (human decided)

- **Per-clone DB, gitignored**: Each clone builds its own SQLite DB from scan-history.md. DB files are in .gitignore. Markdown stays the shared source of truth. Zero merge conflict risk.
- **Standalone scan_index.py**: New script at references/scripts/scan_index.py with subcommands: suggest-targets, record-scan, record-decision, refresh-churn, rebuild. Follows existing pattern (tracker.py, vault_check.py).
- **GitHub Issues + sparse PM prompts for decision feedback**: Scan findings filed as GitHub Issues with `improvement-scan` label. PM surfaces unresolved ones during check-in (sparsely, not every cycle). Human decides on the issue. PM records the decision to DB via record-decision.
- **Detect renames during refresh-churn**: Run git log --follow --diff-filter=R to detect file renames. Update file paths in DB so historical coverage carries forward.
- **Hardcode weights initially**: Ship with fixed composite weights (coverage_gap=0.3, churn=0.3, cross_role=0.2, acceptance=0.2). Defer config.md configurability to a follow-up task if tuning is needed.

## Dev Discretion (dev agent can choose)

- DB schema details (table names, column types) — as long as it supports the documented subcommands
- Rebuild strategy (full rebuild vs incremental)
- How to handle concurrent access within a single clone (unlikely but possible)

## Side Effect Mitigations (required)

- scan-history.md must remain the source of truth — DB is a derived cache
- Existing scan-history.md format must be parseable by the rebuild command
- If DB is missing or corrupt, agent must fall back gracefully to markdown-based targeting

## Upgrade Path (required)

- New file: references/scripts/scan_index.py
- New gitignore entry for *.sqlite3 or scan-index.db
- Sub-skill template update: improvement-scan sub-skill must call scan_index.py suggest-targets instead of reading scan-history.md directly
- PM sub-skill update: add sparse prompting for pending improvement-scan decisions during check-in
- Graceful degradation: if scan_index.py doesn't exist (non-upgraded install), fall back to current markdown scanning

## Out of Scope

- Configurable weights (follow-up task if needed)
- Cross-clone DB sharing or syncing
- RAG/embedding-based search (future FEAT-SKILL-062)
