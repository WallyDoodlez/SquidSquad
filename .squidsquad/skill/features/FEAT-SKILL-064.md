## FEAT-SKILL-064 — Vault Phase 2: vault-update, vault-search, vault-check

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Pending
- **Depends On**: FEAT-SKILL-029 (vault Phase 1)
- **Description**: Phase 2 of the PARAG memory vault. Adds operational vault skills:

  1. **vault-update**: Update existing notes — apply changes, update `updated` frontmatter, append changelog entry, resolve new wikilinks. Calls vault-check after every write.
  2. **vault-search**: Query the vault via grep + wikilink traversal. Direct lookup by name, tag search, wikilink reverse search, content search, 2-hop traversal. Abstracted interface for future SQLite hybrid RAG swap (FEAT-SKILL-062).
  3. **vault-check (Level 1)**: Validates a single note + 2-hop neighborhood on every write. Template conformance, frontmatter validation, wikilink resolution, auto-maintained links field, 500-line galaxy limit, changelog presence.

  All built as common sub-skills composed into every agent template.

- **Acceptance Criteria**:
  - [ ] vault-update modifies notes, updates frontmatter, appends changelog
  - [ ] vault-search supports tag, wikilink, content, and 2-hop traversal queries
  - [ ] vault-search interface abstracted for future SQLite swap
  - [ ] vault-check runs on every vault-create and vault-update
  - [ ] vault-check validates frontmatter, wikilinks, links field, size limits
  - [ ] Auto-maintained links field (vault-check parses content, updates frontmatter)
  - [ ] Built as common sub-skills

### Discussion

> [2026-04-03 09:00] **pm/qa**: Split from FEAT-SKILL-029 (Phase 1). Phase 2 adds operational vault skills. Depends on Phase 1 shipping first. Planning artifacts (RESEARCH.md, CONTEXT.md, TEST-PLAN.md) from 029 cover this scope — TCs 16-33.
