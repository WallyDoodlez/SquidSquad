## FEAT-SKILL-062 — Semantic search for vault memory layer (OpenSearch)

- **Priority**: Medium
- **Depends On**: FEAT-SKILL-029 (Obsidian memory layer)
- **Owner**: TBD
- **Status**: Pending
- **Description**: Extend the vault memory layer (FEAT-SKILL-029) with semantic search powered by OpenSearch, replacing or augmenting the grep-based COG retrieval approach. Enables natural language queries across the vault with vector similarity, fuzzy matching, and ranked results.

  **Why**: As the vault grows (hundreds/thousands of notes), grep-based search becomes noisy and slow for conceptual queries like "what does the human prefer for error handling?" — grep finds keywords but not meaning. Semantic search understands intent.

  **Approach (inspired by human's external research):**
  - OpenSearch as the search backend (self-hosted or managed)
  - Index vault notes with embeddings for semantic similarity
  - Agents query OpenSearch instead of (or in addition to) grep
  - Results ranked by relevance, not just keyword match
  - Hybrid: semantic search for conceptual queries, grep for exact lookups

  **Implementation considerations:**
  - This adds infrastructure (OpenSearch instance) — breaks the "zero infrastructure" COG philosophy
  - Should be optional — vault works fine with grep, OpenSearch is an enhancement
  - Indexing pipeline: on vault-create/update, index the note
  - Query interface: natural language → embedding → OpenSearch → ranked results

- **Acceptance Criteria**:
  - [ ] OpenSearch indexes all vault notes with embeddings
  - [ ] `/vault-search` can use semantic search when OpenSearch is available
  - [ ] Falls back to grep when OpenSearch is not configured
  - [ ] Natural language queries return relevance-ranked results
  - [ ] Indexing happens automatically on vault-create/update
  - [ ] Optional — zero-config installs work without OpenSearch

### Discussion

> [2026-04-02 12:00] **pm/qa**: Filed as expansion of FEAT-SKILL-029. Human's external research identified grep-based COG approach as sufficient for initial vault, but recommended semantic search (OpenSearch) for scale. Separated from 029 to keep the core vault simple and infrastructure-free. This is the "speed up search" enhancement.
