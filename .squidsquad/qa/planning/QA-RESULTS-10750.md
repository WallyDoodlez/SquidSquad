# QA-RESULTS-10750 — Catalog ↔ source-tree orphans (partial fix)

**Verified at**: 2026-06-05 cycle 922
**PR**: #11085 (squidsquad/skill/10750-catalog-drift-fix @ HEAD)
**Scope**: PM's path-drift-only framing — 3 orphan catalog rows resolved. Out of scope (per PM + catalog notes): 40+ orphan source files (intermediate state per #10360) and 18 dead-code candidates (runtime-Read fragments + reactive sub-skills + chat-roadmap deferred).

## Verification

- **3 catalog row edits applied as specified**:
  - `skill/finding-categories` → `roles/verifier/skill/finding-categories` (slash-bearing per #10743; resolves to the actual file location).
  - `discussion` strikethrough'd (file rename lands as part of #10360).
  - `compose-output-review` strikethrough'd (source file pending COMPOSE-ARCHITECTURE.md §9).
- **`drift-check` output**: no "Orphan catalog rows" section emitted → `orphan_catalog_rows: 3 → 0` ✓.
- **`compose.py deploy-all`**: succeeds, sizes unchanged from #11049's measurement (dm 1006 / pm 1066 / qa 1008 / skill 1268).
- **Catalog-area tests**: `pytest tests/test_catalog*.py tests/test_compose_check_a45_10395.py` → **61 passed in 1.57s**.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Partial fix is honest about its scope per the issue body's "cleanup is independent per-category and can be split into smaller PRs". The remaining orphan source files and dead-code candidates are tracked as deferred work, not gaps.
