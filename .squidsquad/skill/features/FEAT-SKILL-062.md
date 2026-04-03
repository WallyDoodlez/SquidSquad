## FEAT-SKILL-062 — Semantic search for vault memory layer (OpenSearch)

- **Priority**: Medium
- **Depends On**: FEAT-SKILL-029 (Obsidian memory layer)
- **Owner**: TBD
- **Status**: Pending
- **Description**: Extend the vault memory layer (FEAT-SKILL-029) with hybrid RAG search and a **deep dreaming** memory optimization process. This is not just "faster search" — it's the prerequisite for memory self-maintenance.

  **Two capabilities:**

  1. **Hybrid RAG Search**: SQLite-based (sqlite-vec + FTS5), FastEmbed ONNX embeddings, 0.7 vector + 0.3 keyword hybrid scoring. Lighter than OpenSearch, no server needed. Incremental indexing (only modified files). Replaces grep for conceptual queries while keeping grep for exact lookups.

  2. **Deep Dreaming** (memory optimization): Periodic process that uses semantic understanding to maintain vault quality:
     - **Prune**: Find duplicate/near-duplicate notes via embedding similarity, merge or remove
     - **Purge**: Find contradictions between notes, resolve using confidence field (high > medium > low), flag unresolvable conflicts for human review
     - **Consolidate**: Cluster related galaxy notes into area-level summaries
     - **Promote/Demote**: Move high-value inbox items to galaxy, archive stale notes
     - **Confidence calibration**: Re-evaluate confidence levels based on subsequent evidence

  **Why deep dreaming needs hybrid RAG**: Grep finds keywords, not meaning. Finding that "toast notifications for errors" and "inline error messages for validation" are contradictory requires semantic understanding, not string matching. At scale (hundreds of notes), grep-based optimization is too slow and token-intensive.

  **Phasing**: vault-search gets hybrid RAG first (replaces grep). Deep dreaming comes after, using the same embedding infrastructure.

- **Acceptance Criteria**:
  - [ ] SQLite hybrid RAG indexes all vault notes with embeddings (sqlite-vec + FTS5)
  - [ ] `/vault-search` uses hybrid scoring (0.7 vector + 0.3 keyword) when available
  - [ ] Falls back to grep when SQLite index is not built
  - [ ] Incremental indexing — only modified files re-indexed on vault-create/update
  - [ ] Deep dreaming process: finds duplicates, resolves contradictions, consolidates
  - [ ] Confidence field consumed during deep dreaming (high wins over low)
  - [ ] Unresolvable contradictions flagged for human review
  - [ ] Optional — vault works with grep-only if hybrid RAG not initialized

### Discussion

> [2026-04-02 12:00] **pm/qa**: Filed as expansion of FEAT-SKILL-029. Separated to keep core vault infrastructure-free.
> [2026-04-02 13:00] **pm/qa**: Major scope expansion. Human insight: confidence field implies garbage in memory. Deep dreaming (prune, purge, consolidate) is needed but only makes sense with semantic understanding — grep can't find duplicates or contradictions at meaning level. Hybrid RAG is the prerequisite for memory self-maintenance, not just faster search. Updated scope to include deep dreaming process. Changed from OpenSearch to SQLite hybrid RAG (lighter, embedded, no server).
