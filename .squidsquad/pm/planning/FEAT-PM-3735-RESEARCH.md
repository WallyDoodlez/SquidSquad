# FEAT-PM-3735 Research — Skip CQ tests when spec files unchanged

## Summary

CQ tests spawn 2 Claude CLI agents per spec (test + eval), costing significant tokens/time. There are 5 specs, all following an identical test pattern. Each spec declares its `files` list. A deterministic SHA256 content-hash check before spawning can skip unchanged specs safely.

Two implementation approaches: (A) modify each `test_comprehension_*.py` fixture, or (B) add the cache logic to `run_comprehension_test.py` itself. Option B is cleaner — single change point, all test files benefit automatically, and future CQ tests inherit the behavior.

## Vault Context

- **BRIEFING.md priorities**: not directly relevant
- **Related decisions**: none
- **Related patterns**: none
- **Human preferences**: "mechanically determined" — no agent judgment in the skip decision
- **Related learnings**: none

## Impact Analysis

- **Files touched**: `references/scripts/run_comprehension_test.py` (main change), `tests/comprehension/.cache/` (new, gitignored)
- **Behavior changes**: CQ tests skip when spec files unchanged; run normally when changed
- **Dependencies**: hashlib (stdlib), no new deps

## Side Effects

- **Risk 1**: Cache corruption could cause false skips — Severity: L — Mitigation: cache only on PASS, `--force` flag to bypass
- **Risk 2**: File paths in spec could be relative or absolute — Severity: L — Mitigation: resolve relative to repo root (already done in runner)

## Edge Cases

- **Spec file itself changes but listed files don't**: should re-run (new questions). Hash the spec file too.
- **Cache dir doesn't exist**: create on first PASS, skip check gracefully if missing.
- **File in spec deleted**: hash computation fails, triggers re-run (safe fallback).
- **Multiple pytest workers**: unlikely for CQ tests, but hash files are atomic write (write-then-rename).

## Integration Risks

- None — this is isolated to the CQ test pipeline, no interaction with other tasks.

## Upgrade & Migration

- **New config values**: none
- **New files**: `tests/comprehension/.cache/` directory (gitignored)
- **Template changes**: none
- **Upgrade steps**: N/A — no upgrade impact
- **Graceful degradation**: N/A

## Capability Gaps

- None — standard Python stdlib (hashlib, pathlib, json)

## Open Questions

- **Q1**: Should the spec JSON file itself be included in the hash? — **Why**: If someone edits questions but not the tested files, the CQ should re-run.

## Recommendation

Straightforward. Single-file change to `run_comprehension_test.py` with a cache directory.
