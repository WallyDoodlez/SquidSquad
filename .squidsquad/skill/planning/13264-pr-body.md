## #13264 — tombstone the unreachable v2 manifest loader (dead code post-E6)

(verifier-filed, from my #13172 review; the tombstone-vs-remove decision I flagged but hadn't filed.)

### Finding
`compose._load_manifest_v2` / `_load_manifest_v2_from_file` have **zero production callers** post-E6 (#10685). The deploy entrypoints (`deploy_role_v2` / deploy-all / wizard) route through `v2_link_stage.emit_v2_linked` → `atomic_emit.assemble_and_emit`, not this loader. Independently grep-confirmed: the only references are the pair's own `base_role` recursion + the unit tests.

### Decision: tombstone, not remove
Added an explicit **unreachable-post-E6 docstring marker** to both functions. Retained (not deleted) because:
- it preserves the `base_role`/`additional_includes` schema reader **and the #13172 fail-closed guard** in case the manifest-loader path is ever re-wired;
- removing a recursive function pair + its tests from the fleet-critical `compose.py` would warrant heavier review than a low-priority dead-code item justifies.

Removal (with tests) is the follow-on once the path is confirmed permanently retired — the marker says so.

### Verification
- +2 guard tests (`TestManifestV2TombstoneUnreachable13264`): the symbol stays referenced **only** within `compose.py` (a new production caller fails the test → forces re-deciding the tombstone rather than silently reviving dead code), and the marker stays present.
- Doc-only + guards, **zero behavior change** → no DS-review, no CQ, no manifest.
- Full static gate: **5002 passed, 0 failures, 0 errors**.
