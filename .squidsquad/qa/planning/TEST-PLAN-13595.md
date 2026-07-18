# TEST-PLAN-13595 — config-value placeholder substitution reads the installing clone, not target_root

**Source**: GitHub issue #13595 body (my own filed finding) + its "Suggested direction" section.
**Derived without reading the diff first — ACs re-derived from my own issue body.**

## Acceptance Criteria (self-derived, from the issue's own scope)

- **AC1**: A mechanism exists that, during a foreign `deploy_role_v2`/`deploy_alias_v2(target_root=foreign)` call, redirects `config.get_field()`/`_read_config_value()` reads to the target's own scaffolded config.md instead of the installing clone's `config.CONFIG_PATH`.
- **AC2**: Wired into BOTH `deploy_alias_v2` and `deploy_role_v2` (the two compose entry points identified in the original finding).
- **AC3**: Covers all previously-identified leaking placeholder fields (workers, `{role}-tests`, interval, alias-pm/qa/dm, e2e-tests, agent-compose, project-name) since they funnel through the same `get_field`/`_read_config_value` call.
- **AC4 (decisive)**: A live reproduction with a DIVERGENT installing-clone vs. target-root config pair confirms the leak is closed — the target's own value appears in composed output, the installing clone's value does not.
- **AC5 (non-regression)**: Self-hosted compose (target_root unset/defaults to REPO_ROOT) is functionally unaffected — `get_field()` calls outside any override still read the ambient `CONFIG_PATH`, and the override path for a self-hosted deploy resolves to the identical file as before.

## Test Cases

### TC-1 (covers AC1/AC2): Design review
- **Steps**: Read `config.py`'s new `config_path_override` context manager (contextvar-backed) and its wiring into both `deploy_alias_v2` and `deploy_role_v2` in `compose.py`.
- **Expected**: Both entry points wrap `_substitute_placeholders` in `config_path_override(target_root / ".squidsquad" / "config.md")`.
- **Result**: PASS — confirmed via diff read.

### TC-2 (covers AC3): Scope of the redirect
- **Steps**: Confirm `_read_config_value` is the single funnel point for all named placeholder fields (already established during the original #13595 investigation — 9 call sites, all via `_read_config_value` → `config.get_field`).
- **Expected**: The `config_path_override` context manager affects `config.get_field` globally for its duration, so all 9 call sites are covered by one wrap.
- **Result**: PASS — `_read_config()` (which every `get_field` call routes through) is the single point patched; no per-field special-casing needed.

### TC-3 (covers AC4, decisive): Live re-run of the ORIGINAL repro
- **Steps**: Re-ran the exact `wizard.scaffold_install(spec, target, overwrite_existing=True)` call against a fresh throwaway target that originally surfaced this bug (during #12527's verification) — own script, not the worker's fixture.
- **Expected**: No "Dev Agents:" deprecation warning (my own qa clone's real legacy field no longer leaks); written config.md still clean.
- **Result**: PASS — stderr fully empty (also confirms the "stderr noise" side-fix), no `Dev Agents` string anywhere. The warning's disappearance is diagnostic of the READ SOURCE changing (my clone's config.md has the legacy field; the target's does not) — stronger evidence than checking a coincidentally-matching output value.

### TC-4 (covers AC4): Worker's own divergent-value regression
- **Steps**: `test_deploy_alias_v2_reads_target_config_not_installing_clone` / `test_deploy_role_v2_reads_target_config_not_installing_clone` — explicit installing-clone config with a marker value (`INSTALLING-CLONE-LEAK`) vs. target config with a different value (`foreign-pm`).
- **Result**: PASS (re-run independently) — target's value present, installing clone's marker absent, in both compose entry points.

### TC-5 (covers AC5): Non-regression
- **Steps**: `test_config_get_field_unaffected_outside_override` (worker's test); code-read confirming `target_root` defaults to `REPO_ROOT` in both compose functions, making the override path identical to the default `CONFIG_PATH` for self-hosted calls.
- **Result**: PASS — both the test and the code-path trace confirm zero behavior change for the 99% self-hosted case.

### TC-6: Full regression + static gate
- **Steps**: `pytest tests/test_compose*.py tests/test_config*.py tests/test_13595_config_target_root_leak.py`, combined-state static gate.
- **Result**: 556/557 passed (the 1 "failure" is the pre-existing, gate-excluded `test_10360_cleanup_markers_preserved` known-failure, unrelated to this diff — confirmed via the static gate's own allowlist notice). Full static gate result pending at write time.

## Coverage matrix
- AC1 → TC-1
- AC2 → TC-1
- AC3 → TC-2
- AC4 → TC-3, TC-4
- AC5 → TC-5
