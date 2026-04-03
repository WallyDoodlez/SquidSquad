## FEAT-SKILL-066 — Vault Phase 4: vault-optimize (full vault sweep)

- **Priority**: Medium
- **Owner**: skill-lead
- **Status**: Pending
- **Depends On**: FEAT-SKILL-065 (vault Phase 3)
- **Description**: Phase 4 of the PARAG memory vault. Adds on-demand vault maintenance:

  1. **vault-optimize (Level 2)**: Full vault sweep — runs vault-check Level 1 across every note plus vault-wide checks:
     - Template conformance across all notes
     - Broken wikilink detection (vault-wide)
     - Near-duplicate detection (fuzzy match within folders)
     - Orphan detection (notes never linked to)
     - Staleness audit (notes where `updated` > 30 days, non-archived status)
     - Tag normalization (collect all tags, identify duplicates, suggest canonical forms)
     - Relationship symmetry (if A links to B, does B link back?)
     - README.md refresh (stats, recent updates, health)

  2. **Archive management**: Move stale/completed notes to archives/ folder with proper archived frontmatter.

  Run on-demand by the human or during extended quiet periods. Not part of the regular Ralph Loop.

- **Acceptance Criteria**:
  - [ ] vault-optimize runs all Level 2 checks listed above
  - [ ] Findings grouped by severity (auto-fixable, needs-review, info)
  - [ ] Auto-fixable items (tag normalization, missing backlinks) fixed with user approval
  - [ ] README.md refreshed with vault stats
  - [ ] Stale notes flagged for archival
  - [ ] Built as common sub-skill (invokable by any agent)

### Discussion

> [2026-04-03 09:00] **pm/qa**: Split from FEAT-SKILL-029. Phase 4 adds vault maintenance and health. On-demand, not every cycle. Depends on Phase 3 (vault must have content to optimize). Planning artifacts from 029 cover this — TCs 43-49. Note: deep dreaming (prune/purge/consolidate using semantic understanding) is in FEAT-SKILL-062 — requires hybrid RAG.
