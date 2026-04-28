# FEAT-PM-3735 Context — Skip CQ tests when spec files unchanged

## Scope

Add deterministic content-hash caching to `run_comprehension_test.py` so CQ tests skip when their spec files and tested files haven't changed since the last passing run. Single-file change + new cache directory.

## Locked Decisions (human decided)

- **Hash scope**: Hash both the spec JSON file AND the listed files — changing questions triggers re-run
- **Mechanically determined**: Skip decision uses SHA256 content hashes only — no agent/LLM judgment
- **Cache on PASS only**: Failed runs don't update the cache (prevents masking broken state)

## Dev Discretion (dev agent can choose)

- Hash algorithm details (SHA256 recommended but dev can choose)
- Cache file format (JSON, plain text, whatever works)
- How to structure the `--force` / `FORCE_CQ=1` bypass
- Whether to add a helper function or integrate inline in the runner

## Side Effect Mitigations (required)

- Spec file itself must be included in the hash (locked decision above)
- Cache dir missing = graceful fallback to running the test (no crash)
- File in spec deleted = hash fails = re-run (safe fallback)

## Upgrade Path (required)

- N/A — no upgrade impact. Cache dir is new and gitignored.

## Out of Scope

- Modifying individual `test_comprehension_*.py` files (logic goes in the shared runner)
- Changing CQ test behavior when files HAVE changed
- Any non-CQ test caching
