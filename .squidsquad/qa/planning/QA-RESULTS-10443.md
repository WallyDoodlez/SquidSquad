# QA-RESULTS-10443 — PRD-B / Story B6: assemble cache layer (SHA256 key + .assemble-cache/ store)

**Verified**: 2026-05-31 22:06
**Branch**: `squidsquad/task/10443` @ `e840131a` (force-pushed rebase, predates this cycle per skill-lead)
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

`e840131a` commit isolated content (parent-relative diff):

| File | Lines added |
|---|---|
| `references/scripts/assemble_cache.py` | 93 |
| `tests/test_assemble_cache.py` | 200 |
| `tests/run_tests.py` | 1 (registration) |

Skill-lead's "3 files" claim verified. Branch sits on top of unmerged #10516/#10523/#10530 commits which inflate the diff-vs-main but are not part of this task.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1a | `cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version) -> str` SHA256 hex | Live introspection: signature matches; `len(cache_key(...)) == 64`; deterministic across runs; per-input invalidation | PASS |
| 1b | `cache_lookup(alias, key) -> str \| None` | Signature: `(alias, key, *, slot_name=None)` — adds optional kwarg for log enrichment, base contract preserved | PASS |
| 1c | `cache_store(alias, key, assembled_body)` writes `.squidsquad/<alias>/.assemble-cache/<key>.md` | `test_cache_store_creates_directory_and_file`, `test_cache_round_trip_preserves_bytes` | PASS |
| 2 | `.assemble-cache/` git-tracked (no .gitignore exclusion) | `.gitignore` shows no entry for `.assemble-cache`; only `.backlog-cache`, `__pycache__/`, `tests/comprehension/.cache/` excluded. Also covered by `test_gitignore_does_not_exclude_assemble_cache` | PASS |
| 3 | Stderr emits `[cache hit] alias=<a> slot=<s>` on lookup hit | `test_cache_lookup_hit_returns_body_and_logs_to_stderr` + `test_cache_lookup_log_uses_question_mark_when_slot_omitted` + `test_cache_lookup_no_log_on_miss` (3-way coverage: hit logs, slot fallback, miss silent) | PASS |
| 4a | Unit tests: identical inputs → identical keys | `test_cache_key_identical_inputs_identical_keys` | PASS |
| 4b | Unit tests: any input change invalidates | `test_cache_key_each_input_invalidates` parametrized × 5 (each AC1a param) | PASS |
| 4c | Unit tests: miss returns None | `test_cache_lookup_miss_returns_none` + `test_cache_lookup_miss_when_dir_absent` | PASS |
| 4d | Unit tests: round-trip preserves bytes | `test_cache_round_trip_preserves_bytes` | PASS |
| 5 | No LLM dependency | `grep -i llm` on module: 2 matches, both in module docstring ("LLM rewrite", "No LLM dependency"). No imports of anthropic/openai/requests/httpx/urllib/socket | PASS |

## Defense-in-Depth Extras (beyond ACs)

Skill added alias path-traversal hardening not strictly required by the ACs but worth noting:
- `test_invalid_alias_rejected` × 10 (`..`, `../etc`, `a/b`, `a\\b`, empty, `.hidden`, space, NUL, None, int)
- `test_valid_alias_accepted` × 7 (pm, dm, skill, qa, agent-1, role_2, a.b)
- `test_cache_store_no_tmp_left_behind` + `test_cache_store_unlinks_tmp_on_replace_failure` — atomic-write hygiene
- `test_cache_key_separator_prevents_boundary_collision` — guards against `("ab","c") == ("a","bc")`-style hash collisions
- `test_cache_isolated_per_alias` — multi-tenant boundary

## Test Execution

`pytest tests/test_assemble_cache.py -v` (clean worktree at e840131a) → **38 passed in 0.27s**

## Outcome

All 5 ACs met. Module is pure-I/O as specified. Defense-in-depth coverage on alias validation, atomic writes, and hash boundary correctness exceeds AC bar. **Transitioning #10443: pending-test → pending-ship.**
