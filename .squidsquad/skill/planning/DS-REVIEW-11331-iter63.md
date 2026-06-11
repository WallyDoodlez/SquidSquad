I have thoroughly reviewed all the relevant source files. Here is my analysis:

## Verification Summary

### 1. Harness EAD emit + filter rename — internally consistent ✓

- **Emit side (`harness.py:3114-3118`)**: `ExternalActivityDetector._check_for_changes` emits `payload={"target_alias": target_alias, ...}` — correct.
- **Filter side (`harness.py:2187`)**: `GET /events/for/{role}` reads `e.get("payload", {}).get("target_alias", "")` — correct.
- Both use the canonical `target_alias` field name.

### 2. Match with `l4_file_watcher.py` — consistent ✓

- `l4_file_watcher.py:189` (`emit_results`): emits `"target_alias": r.alias`
- `l4_file_watcher.py:353` (`make_change_callback` error path): emits `"target_alias": "pm"`
- Both match the harness filter's expected field name.

### 3. Regression test `test_target_alias_is_canonical_field_name` ✓

- **`tests/test_harness.py:2397-2436`**: Correctly pins both halves:
  - (a) `assertIn("canon", ids)` — filter matches `payload.target_alias`
  - (b) `assertNotIn("legacy", ids)` — filter does NOT silently accept `payload.target_role`
- The `"legacy"` event fixture at line 2424 uses `"target_role"` (intentionally, to prove rejection).

### 4. No remaining call site emits or reads `target_role` for event payloads ✓

- All Python files searched: the only string-literal `"target_role"` outside of `target_role_class` (which is a different concept) appears in:
  - `harness.py:2158`: a docstring explaining the rename (informational, not functional)
  - `tests/test_harness.py:2424`: the regression test fixture (intentionally uses legacy name to prove it's rejected)
- `l4_audit_gate.py` and `l4_conflict_preempt.py` use `target_role_class` — this is the **role-class noun** (e.g., `"pm"`, `"skill"`), not an event routing alias. Confirmed out of scope and correctly left unchanged.
- Integration test stub `test_event_mode_e2e.py:189` also reads `target_alias` — consistent with the harness filter.
- `event_catalog.py:136` lists `target_alias` in the `assigned-to` payload fields — correct.

### 5. No fixture inconsistencies or logic gaps detected ✓

No missed call sites, no stale `target_role` references in emit or filter paths, no inconsistencies between the test stubs and the production code.

NO_FINDINGS