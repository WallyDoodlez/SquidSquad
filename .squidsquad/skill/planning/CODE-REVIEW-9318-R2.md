### Finding 1

- **File**: tests/test_cycle_pre.py
- **Line**: 820–823 (assertion block of `test_qa_queries_all_roles`)
- **Severity**: warning
- **Issue**: `test_qa_queries_all_roles` does not assert that `"qa"` is in `queried_roles`, even though #9318 added `qa` to `_get_verifiable_roles()`. The test name promises "all roles" but only validates `dm` and `pm`. If `roles.add("qa")` were later removed, `test_always_includes_mandatory_roles` would catch the unit-level regression, but this integration test would silently pass despite QA no longer querying itself for pending-test items.
- **Evidence**: The mock `_config_get` sets `"dev-agents": "skill"` (line 792). Post-#9318, `_get_verifiable_roles()` returns `["dm", "pm", "qa", "skill"]`. The `fake_run_script` records every queried role in `queried_roles` (lines 804, 809), so `"qa"` is present in that list at runtime — but the test only asserts `"dm" in queried_roles` and `"pm" in queried_roles` (lines 821–822), never `"qa"`.
- **Suggested fix**: Add `assert "qa" in queried_roles, "QA input must query qa role for pending-test items"` alongside the existing dm/pm assertions.

### Finding 2

- **File**: tests/test_cycle_pre.py
- **Line**: 868–870 (assertion block of `test_pm_queries_all_roles`)
- **Severity**: warning
- **Issue**: Same gap in `TestPMInputMultiRole.test_pm_queries_all_roles` — the test records all queried roles but only asserts `"dm" in queried_roles`, never `"qa"`. Post-#9318, PM should also query `qa` for pending-test items.
- **Evidence**: The mock `_config_get` sets `"dev-agents": "skill"` (line 851). `fake_run_script` appends every role argument to `queried_roles` (lines 842, 845). Only `"dm"` is asserted (line 869); `"qa"` is not checked.
- **Suggested fix**: Add `assert "qa" in queried_roles, "PM input must query qa role for pending-test items"` alongside the existing dm assertion.