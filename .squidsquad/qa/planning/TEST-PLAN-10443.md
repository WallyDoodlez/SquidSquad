# TEST-PLAN-10443 — PRD-B / Story B6: assemble cache layer

**Source**: issue #10443 ACs (parent PRD compose-assemble-stage §4.6).
**Derived without reading the worker's diff.**

## Acceptance criteria

- **AC-1**: `cache_key/lookup/store` exist with documented signatures; key is SHA256 hex; round-trip preserves body bytes; any input change invalidates key.
- **AC-2**: `.gitignore` does NOT exclude `.assemble-cache/`.
- **AC-3**: stderr emits `[cache hit] alias=<a> slot=<s>` on lookup hit.
- **AC-4**: unit tests cover identity / sensitivity / miss / round-trip.
- **AC-5**: no LLM dependency.

## Test Cases

### TC-1 (AC-1 identity/length): same inputs → same 64-char hex key
- Probe: `cache_key('b','s','p','m','v') == cache_key('b','s','p','m','v')` and length 64, all hex.

### TC-2 (AC-1 boundary injectivity): `('ab','c',...)` and `('a','bc',...)` produce distinct keys
- The 0x1F separator claim must hold; probe confirmed.

### TC-3 (AC-1 round-trip): store then lookup returns identical bytes
- Probe in temp SQUIDSQUAD_DIR; multiline body preserved verbatim.

### TC-4 (AC-1 miss): lookup on missing key returns None.

### TC-5 (AC-2): `grep '.assemble-cache' .gitignore` finds no exclusion line.

### TC-6 (AC-3): cache_lookup hit emits `[cache hit] alias=pm slot=workflow` to stderr.

### TC-7 (AC-4 dev unit coverage): `pytest tests/test_assemble_cache.py -v` exit 0 with ≥5 tests covering identity/sensitivity/miss/round-trip.
- Result: 38 passed (well over the AC-4 minimum: 5 parametric identity-sensitivity + round-trip + miss + 10 path-traversal guards + Windows tmp-unlink guard).

### TC-8 (AC-5 no-LLM): AST-walk imports — must NOT include `anthropic/openai/deepseek/model_router/requests/httpx`.
- Result: `{hashlib, os, pathlib, re, sys}` only.

## Coverage matrix
- AC-1 → TC-1, TC-2, TC-3, TC-4, TC-7
- AC-2 → TC-5
- AC-3 → TC-6
- AC-4 → TC-7
- AC-5 → TC-8

## Comprehension Questions
N/A — Python code only.

## Results
All TCs PASS live. `python tests/run_tests.py` 52 passed / 2 skipped / 0 fail.
