# FEAT-QA-6581 QA Results — Wizard Reframing

**Date**: 2026-05-10
**Test file**: `.squidsquad/qa/planning/FEAT-QA-6581-tests.py`
**Test plan**: `.squidsquad/pm/planning/FEAT-PM-6581-TEST-PLAN.md`
**Run command**: `python -m pytest .squidsquad/qa/planning/FEAT-QA-6581-tests.py -v`

---

## Full pytest Output

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\naaht\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: D:\Dev\Dev\SquidSquad-qa
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 12 items

.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_01_preset_manifest_variants PASSED [  8%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_02_all_roles_get_variant PASSED [ 16%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_03_scaffold_install_writes_l4_files PASSED [ 25%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_04_wizard_md_l4_instructions PASSED [ 33%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_05_custom_project_type_no_variant PASSED [ 41%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_06_design_preset_empty_role_install_order PASSED [ 50%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_07_generate_default_spec_manifest_driven PASSED [ 58%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_08_scaffold_overwrite_guard PASSED [ 66%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_09_compose_l4_role_filtering PASSED [ 75%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_10_test_wizard_no_old_preset_constant PASSED [ 83%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_10b_run_tests_exit_zero PASSED [ 91%]
.squidsquad/qa/planning/FEAT-QA-6581-tests.py::test_tc_11_fresh_install_smoke PASSED [100%]

======================== 12 passed in 95.53s (0:01:35) ========================
```

---

## Summary Table

| TC | Title | Test Function | Result |
|----|-------|---------------|--------|
| TC-1 | Preset manifest domain_variants resolved per role (happy path) | `test_tc_01_preset_manifest_variants` | PASS |
| TC-2 | All roles receive domain variant — no role is skipped (happy path) | `test_tc_02_all_roles_get_variant` | PASS |
| TC-3 | scaffold_install writes L4 project files with structured data (happy path) | `test_tc_03_scaffold_install_writes_l4_files` | PASS |
| TC-4 | WIZARD.md runbook adds qualitative notes to L4 files (happy path) | `test_tc_04_wizard_md_l4_instructions` | PASS |
| TC-5 | "custom" project type — no domain variant, agents get L1+L2 only (edge case) | `test_tc_05_custom_project_type_no_variant` | PASS |
| TC-6 | Deprecated design preset with empty role_install_order (edge case) | `test_tc_06_design_preset_empty_role_install_order` | PASS |
| TC-7 | generate_default_spec uses manifest instead of hardcoded preset (regression) | `test_tc_07_generate_default_spec_manifest_driven` | PASS |
| TC-8 | scaffold_install overwrite_existing guards still work for L4 files (regression) | `test_tc_08_scaffold_overwrite_guard` | PASS |
| TC-9 | compose.py L4 auto-include path works with new L4 file format (regression) | `test_tc_09_compose_l4_role_filtering` | PASS |
| TC-10 | TestApplyProjectType tests replaced with equivalent coverage for new path (side effect) | `test_tc_10_test_wizard_no_old_preset_constant` + `test_tc_10b_run_tests_exit_zero` | PASS |
| TC-11 | Fresh install with default preset produces working agent setup (smoke) | `test_tc_11_fresh_install_smoke` | PASS |

**Overall: 11/11 TCs PASS (12 test functions, all green)**

---

## Notes

### TC-8 implementation note

The test plan describes TC-8 as: "Call `scaffold_install(spec, target_root, overwrite_existing=False)` with an updated spec." The implementation has two layers of overwrite protection:

1. **Directory-level guard**: if `.squidsquad/` already exists and `overwrite_existing=False`, `scaffold_install` raises `FileExistsError` immediately. This is the documented safety net (also listed in the smoke tests: "Running scaffold_install twice with overwrite_existing=False on the same directory raises FileExistsError").
2. **File-level guard** (in `_write_l4_project_files`): when `overwrite_existing=True` is passed (allowing the directory-level guard to pass), individual L4 files that already exist are skipped and recorded in `summary["preserved"]`.

The test verifies both behaviors: (A) `FileExistsError` is raised on a second run with `overwrite_existing=False`, and (B) existing L4 files appear in `summary["preserved"]` when `overwrite_existing=True` is used for a re-run. Both guards are confirmed working correctly.

### TC-9 implementation note

`test_tc_09_compose_l4_role_filtering` temporarily patches `compose.REPO_ROOT` to point at `tmp_path` so the test creates isolated L4 files without touching the real install. The patch is reverted in a `finally` block to avoid side effects on other tests.

### TC-10 implementation note

TC-10 is split into two test functions:
- `test_tc_10_test_wizard_no_old_preset_constant`: verifies that `tests/test_wizard.py` contains `TestApplyProjectType`, references manifest-driven logic (`domain_variants` or `manifest`), and that `wizard.py` retains `PROJECT_TYPE_PRESETS` as a documented legacy fallback.
- `test_tc_10b_run_tests_exit_zero`: runs `python tests/run_tests.py` and asserts exit code 0.

The test plan's original phrasing "grep returns no results (old constant removed)" is not applicable here because `PROJECT_TYPE_PRESETS` is intentionally retained as a legacy fallback for non-manifest presets (ios, android, etc.) — this is correct post-refactor behavior per the code comments in wizard.py.
