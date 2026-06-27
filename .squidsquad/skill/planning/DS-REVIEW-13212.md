I've thoroughly reviewed the diff against the acceptance criteria. Let me trace through all the critical paths.

**Code change** (`references/scripts/git_ops.py` line 883): Adds `"qa": ["tests/comprehension/"]` to the `role_specific` dict inside `_role_owned_patterns`. Since `"tests/comprehension/"` ends with `/`, `_path_matches` (line 888-896) treats it as a prefix match — any path starting with `tests/comprehension/` is owned by qa. This is additive: the only new key in `role_specific` is `"qa"`, and the `return common + role_specific.get(role, [])` line (885) is unchanged.

**Foreign-file skip**: Unchanged. The `for line in lines` loop (943-950) still classifies non-matching paths as foreign, and the warning (952-961) still fires. The new test explicitly asserts the spec does NOT appear in stderr (line 1099).

**Branch guard**: Unchanged. Lines 922-932 are untouched by this diff. The new test mocks both working and current branch as `"main"` — the guard passes, and the test doesn't regress it.

**Push-role propagation**: Unchanged. Line 972 (`return push(role=role)`) is untouched.

**No other role gains `tests/comprehension/`**: Verified by `test_comprehension_specs_are_qa_only` iterating over `("pm", "dm", "skill")`.

**Test adequacy**: 
- `test_qa_extras` — positive inclusion + negative boundary checks
- `test_comprehension_specs_are_qa_only` — isolation from other roles
- `test_qa_stages_untracked_comprehension_spec_13212` — end-to-end: the exact `??` (untracked) porcelain status that was the bug, staged and not foreign-warned

All mock parameter ordering matches decorator application order (verified against existing test patterns). The `_run_side` correctly handles both `git branch --show-current` and `git status --porcelain` calls without interfering with the separately-patched `_run_list`.

NO_FINDINGS