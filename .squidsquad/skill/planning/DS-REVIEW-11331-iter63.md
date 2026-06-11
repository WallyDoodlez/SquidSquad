After a thorough review of all the changed files (harness.py EAD emit + filter, l4_file_watcher.py, test_harness.py regression test), I find the changes are internally consistent and correct:

**Verification summary:**

1. **Harness EAD emit → filter consistency**: The EAD emit at `harness.py:3117` writes `"target_alias": target_alias` into the payload. The filter at `harness.py:2187` reads `e.get("payload", {}).get("target_alias", "")`. These match exactly. The `l4_file_watcher.py` emit paths (lines 189, 353) also use `"target_alias"`. All three emit sites produce the same wire shape.

2. **Regression test `test_target_alias_is_canonical_field_name`** (lines 2397–2436): Correctly pins both halves — asserts that an event with `target_alias` IS returned, and a legacy event with `target_role` IS NOT returned. The assertions at lines 2432–2436 have clear failure messages referencing the specific contract.

3. **No remaining `target_role` call sites**: The only `target_role` references in functional Python code are:
   - `l4_audit_gate.py` / `l4_conflict_preempt.py`: use `target_role_class` (different concept, out of scope per task)
   - `test_harness.py` line 2424: the intentional legacy payload in the regression test itself
   - `harness.py` line 2158: a docstring comment documenting the legacy name

4. **Event catalog** (`event_catalog.py:136`) uses `target_alias`, and `AGENT-RUNTIME.md` consistently uses `target_alias` throughout §8.

5. **All other tests** in `TestGetEventsForRole` use `target_alias` consistently in their fixture events, and the integration test (`test_event_mode_e2e.py:189`) also uses `target_alias`.

`NO_FINDINGS`