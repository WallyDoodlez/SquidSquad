Now I have a complete picture. Let me produce the final analysis.

---

### Finding 1

- **File**: `references/scripts/cycle_pre.py`
- **Line**: 506–526
- **Severity**: warning
- **Issue**: `_get_verifiable_roles()` explicitly adds `dm` and `pm` (lines 524–525) but does NOT add `qa`. After #6055, `qa` is a mandatory role alongside `pm` and `dm` (per `MANDATORY_ROLES` at `compose.py:1202`). Before this config change, `qa` was listed in `Dev Agents` (`qa, skill`), so the function picked it up from config. Now that `qa` has been removed from `Dev Agents` (config.md), this function returns `["dm", "pm", "skill"]` — missing `qa`. Both `_build_qa_input` (line 649) and `_build_pm_input` (line 826) iterate over this set when querying `tracker.py list-issues` / `list-tasks` for `pending-test` items, so PM will no longer query QA's pending-test items.

- **Evidence**: Compare with every other function that reads dev-agents and adds mandatory roles:
  - `compose.py:_collect_all_roles()` (line 1210): appends `"pm"`, `"qa"`, `"dm"` 
  - `boot_remote.py:_get_all_roles()` (line 128): `roles.update({"pm", "qa", "dm"})`
  - `add_role.py:_get_configured_agents()` (line 63): iterates `("pm", "qa", "dm")`
  - `config.py:_parse_agents_v1()` (line 407): iterates `("qa", "dm")` + explicit `"pm"` at line 381
  Only `cycle_pre.py:_get_verifiable_roles()` omits `qa` while including `dm` and `pm`.

- **Suggested fix**: Add `roles.add("qa")` alongside the existing `roles.add("dm")` / `roles.add("pm")` calls at lines 524–525. Also update the docstring example (line 509) from `'designer, qa, skill'` to `'designer, skill'` to match the post-#6055 semantics.

---

### Finding 2

- **File**: `references/scripts/cycle_pre.py`
- **Line**: 509 (docstring)
- **Severity**: warning
- **Issue**: Stale docstring example in `_get_verifiable_roles()`. The docstring reads `(e.g. 'designer, qa, skill')` — listing `qa` as a dev agent. After #6055, qa is mandatory and should not appear as an example of a dev agent.

- **Evidence**: The config.md now has `Dev Agents: skill` only. QA is listed under "always present" in the Agents section. The example is misleading for anyone reading the code in the post-#6055 era.

- **Suggested fix**: Change the docstring to remove `qa` from the example, e.g., `(e.g. 'designer, skill')`.

---

### Finding 3

- **File**: `tests/test_cycle_pre.py`
- **Line**: 832–837
- **Severity**: warning
- **Issue**: `TestGetVerifiableRoles.test_includes_config_dev_agents` mocks `dev-agents` as `"skill, qa"`. There's a corresponding test `test_always_includes_dm_and_pm` (line 839–844) that verifies `dm` and `pm` are always included **regardless of config**. No equivalent test exists for `qa`. After the config change, if qa is removed from dev-agents, there's no test asserting that qa is still included in verifiable roles.

- **Evidence**: The test at line 839 asserts `dm` and `pm` are always present. The test at line 832 only verifies qa is present *when it is in dev-agents*. The post-#6055 invariant — that mandatory roles (pm, qa, dm) are always in verifiable roles — is not fully covered.

- **Suggested fix**: Add a test (or extend `test_always_includes_dm_and_pm`) to also assert `"qa" in roles`, mirroring the dm/pm check, once `_get_verifiable_roles()` is fixed to add qa explicitly.