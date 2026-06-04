Now I have a thorough understanding of all the changes. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/compose.py`
- **Line**: 2161–2203 (deploy check block), 2225–2249 (deploy-all check block)
- **Severity**: error
- **Issue**: After cutover, `deploy <role> --check` and `deploy-all --check` still compare against the v1 file `CLAUDE.md`, but the non-check deploy path now writes to the v2 file `CLAUDE.v2.md`. This makes `--check` functionally disconnected from what `deploy`/`deploy-all` actually produce.

- **Evidence**: 
  - `check_role()` (line 1413) reads `.squidsquad/<output_name>/CLAUDE.md`.
  - `deploy_alias_v2()` writes `.squidsquad/<alias>/CLAUDE.v2.md` (line 1754, `filename_suffix` defaults to `.v2.md`; line 1761-1764 returns `triple_paths[0]` which is the assembled `CLAUDE.v2.md`).
  - Pre-cutover, `deploy pm` wrote `CLAUDE.md` and `deploy pm --check` checked `CLAUDE.md` — they agreed on the file. Post-cutover, `deploy pm` writes `CLAUDE.v2.md` but `deploy pm --check` still checks `CLAUDE.md`, which will be MISSING after a fresh deploy.
  - The `deploy-all` check block (lines 2225–2249) iterates roles from `_collect_all_roles()` (v1 config) and calls `check_role()` — also checking v1 `CLAUDE.md` — while the non-check block (lines 2250–2286) iterates aliases from the registry and writes v2 files.
  - Both check blocks were left untouched by the diff, creating an asymmetry.

- **Suggested fix**: Either (a) route `--check` to a new v2-aware check that compares against the in-memory v2 composition output at `CLAUDE.v2.md`, or (b) document the `--check` flag as v1-only and emit a clear warning that it does not apply to v2 deploy output. The comment at lines 2256-2257 acknowledges event contracts have "no v2 analog" and should be "restore[d] in a follow-up" — `--check` deserves the same explicit acknowledgment rather than silently checking the wrong file.

---

### Finding 2

- **File**: `tests/test_compose_a6_v2.py`
- **Line**: 380–398
- **Severity**: error
- **Issue**: `test_main_deploy_all_v2_iterates_registry` fails to mock `_collect_all_roles()`, `_check_mandatory_roles()`, `generate_local_config()`, and `Path.write_text`. Post-cutover, the `deploy-all` non-check path no longer returns early after the alias loop — it proceeds to topology bookkeeping (lines 2277–2286), which calls unmocked functions that write to the real `.squidsquad/.local-config`.

- **Evidence**:
  - Old code (`v2_mode` path, removed in diff at old line ~183): the alias loop ended with `return`, skipping topology bookkeeping entirely.
  - New code (lines 2277–2286): after the alias loop, unconditionally calls `_collect_all_roles()`, `_check_mandatory_roles()`, and `generate_local_config(roles)`. None of these are mocked in the test.
  - `generate_local_config` (line 2070) calls `config_path.write_text(...)` which writes to the real repo's `.squidsquad/.local-config`.
  - The test only mocks `deploy_alias_v2`, `parse_aliases_registry`, and `Path.read_text`.

- **Suggested fix**: Add monkeypatch stubs for `_collect_all_roles` (return a safe list like `["pm", "verifier", "dm"]`), `generate_local_config` (return a fake Path), and `Path.write_text` (no-op). Also stub `_check_mandatory_roles` if needed for isolation.

---

### Finding 3

- **File**: `tests/test_compose_a6_v2.py`
- **Line**: 401–419 (`test_main_deploy_v2_returns_without_calling_event_contracts`)
- **Severity**: warning
- **Issue**: This test now verifies a tautology. Event-contract derivation (`derive_and_write_event_contracts`) was removed from **all** `deploy`/`deploy-all` paths in the cutover (both the old v1 branch and the v2 branch). The test asserts the function is "never called" and passes, but it no longer distinguishes between correct v2 routing and a hypothetical bug where the v1 path was taken (because the v1 path also doesn't call event contracts anymore).

- **Evidence**:
  - Diff removed `derive_and_write_event_contracts()` calls from both the `deploy` path (old line ~222 in diff: removed after `deploy_role`) and the `deploy-all` path (old line ~268 in diff: removed after the role loop and `.local-config` generation).
  - The test's comment at lines 416–418 says "v2 path leaves v1 side-effects untouched" but there is no v1 side-effect to leave untouched anymore — the distinction the test was designed to validate no longer exists.

- **Suggested fix**: Either delete the test (it validates a retired invariant) or rewrite it to assert the new post-cutover invariant (e.g., that `deploy_alias_v2` is called and `deploy_role` is not). The current form gives false confidence.

---

### Finding 4

- **File**: `tests/test_compose_a6_v2.py`
- **Line**: 307 (comment), 292 (section header)
- **Severity**: warning
- **Issue**: Stale comments misrepresent post-cutover routing. The section header at line 292 says `"CLI argv parsing: --v2 flag detected; v1 path byte-equivalent"` and the comment at line 307 says `"deploy_alias_v2 is only entered when --v2 is present."` Both are false post-cutover: `deploy_alias_v2` is the **only** path regardless of `--v2`.

- **Evidence**: The test `test_main_strips_v2_flag_and_routes_v1_without_it` (line 295) monkeypatches `deploy_role` and `derive_and_write_event_contracts` and sends `--v2` in argv. These monkeypatches are dead setup in the post-cutover world since `deploy_role` is never called from `main()` anymore. The test still passes, but the comments and dead mocks are misleading for future maintainers.

- **Suggested fix**: Update the section header and inline comment to reflect post-cutover reality. Consider removing the dead `deploy_role` / `derive_and_write_event_contracts` monkeypatches from this test to keep it focused on what it actually validates (that `--v2` still routes to `deploy_alias_v2`).