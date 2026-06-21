I've now thoroughly reviewed the two new tests, the module-level imports, the regex, the transitive-closure algorithm, and the integration with `catalog_parser`. Here is my analysis across each review dimension:

**Transitive-closure walk (termination, seen-set)**: Correct. The `seen` set (line 425) prevents re-processing names; `queue.pop()` gives DFS order but finds the same reachable set as BFS. The set of sub-skill names is bounded by the catalog, so termination is guaranteed. Lines 421-437.

**False-positive risk**: Low. Descriptive prose like `→ run sub-skill: <name>` (line 9 of each CLAUDE.md) does not match because `<` is not in `[a-z]`. Prose that mentions real markers (e.g., `→ run sub-skill: improvement-scan-slim is the marker`) resolves to real sub-skills that *should* be in the manifest — no false assertion. The illustrative `security-smoke` marker in `l4-curation.md` (line 243) is skipped because `catalog.get("security-smoke")` returns `None` — exactly as the docstring at lines 400-404 explains.

**False-negative risk**: The regex (line 44) handles both forms found in the codebase: bare names (`→ run sub-skill: task-pickup`) and backtick-wrapped names (`` → run sub-skill: `pr-protocol` ``), as well as slash-bearing names (`→ run sub-skill: roles/dm/events/pr-merge-wait`). The one explicit gap — `boot-bootstrap`'s runtime-read of `common-events/` fragments — is correctly scoped to the catalog-completeness gate, as the docstring states. The `includes.yml` test (lines 448-473) covers the compose-time include path, creating complementary coverage.

**Skipping catalog-unresolved names**: The right call. Names absent from the catalog (typos, illustrative examples like `security-smoke`, retired entries) cannot be mapped to a source path, so their manifest presence cannot be verified. The catalog-completeness gate (`test_v2_catalog_gate_d3`) owns catching those.

**CI robustness (committed composed files)**: The test depends on `.squidsquad/*/CLAUDE.md` being regenerated and committed when source files change. The `assert composed` guard (line 411) ensures at least some files exist. This is an accepted dependency of the self-hosted test pattern and is consistent with how other tests in this file operate.

NO_FINDINGS