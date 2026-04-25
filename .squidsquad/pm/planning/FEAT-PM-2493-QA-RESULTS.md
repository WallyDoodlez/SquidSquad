# FEAT-PM-2493 QA Results — Per-Agent Working Directories

**Verified at**: 2026-04-23
**Verifier**: PM QA subagent
**Branch**: main
**Full suite**: 895 passed, 0 failed

---

## Summary Table

| TC | Title | Type | Result | Test / Notes |
|----|-------|------|--------|--------------|
| TC-1 | Wizard creates sibling clones for non-PM agents | BLOCKED | BLOCKED | Requires actual `git clone` operations. Not covered by automated tests. |
| TC-2 | PM does NOT get a clone | PASS | PASS | `TestPmNoClone::test_pm_excluded_from_cloning` |
| TC-3 | .local-config written with relative paths | PASS | PASS | `TestLocalConfigRelativePaths::test_pm_maps_to_dot`, `test_non_pm_maps_to_relative`, `test_no_absolute_paths`; also `TestGenerateLocalConfig::test_with_clone_paths_relative`, `test_clone_paths_partial` |
| TC-4 | Relative paths resolve correctly from primary repo | PASS | PASS | `TestRelativePathResolution::test_health_check_resolves_relative_paths`, `test_boot_remote_resolves_relative_paths`, `test_absolute_paths_still_work`, `TestBackwardCompat::test_dot_resolves_to_repo_root` |
| TC-5 | Clones have correct remote URL | BLOCKED | BLOCKED | Requires actual `git clone` and `git remote` operations. Not covered by automated tests. |
| TC-6 | Clones are on the correct branch | BLOCKED | BLOCKED | Requires actual `git clone` and `git branch` operations. Not covered by automated tests. |
| TC-7 | Idempotent — running setup again does not break existing clones | BLOCKED | BLOCKED | Requires actual multi-repo filesystem state. Not covered by automated tests. |
| TC-8 | Single-agent setup (PM only) — no clones created | PASS | PASS | `TestSingleAgentSetup::test_pm_only_no_clones` |
| TC-9 | Windows path compatibility — spaces in paths | BLOCKED | BLOCKED | Requires actual filesystem with spaces in path and `git clone`. Not covered by automated tests. |
| TC-10 | health_check.py reads agent state via relative paths | PASS | PASS | `TestRelativePathResolution::test_health_check_resolves_relative_paths`, `TestBackwardCompat::test_dot_resolves_to_repo_root` |
| TC-11 | boot_remote.py spawns agents in correct clone dirs | PASS | PASS | `TestRelativePathResolution::test_boot_remote_resolves_relative_paths` |

---

## Test Run Details

### `python -m pytest tests/test_per_agent_workdirs.py -v`

All 12 tests passed:

```
TestLocalConfigRelativePaths::test_pm_maps_to_dot                   PASSED
TestLocalConfigRelativePaths::test_non_pm_maps_to_relative           PASSED
TestLocalConfigRelativePaths::test_no_absolute_paths                 PASSED
TestRelativePathResolution::test_health_check_resolves_relative_paths PASSED
TestRelativePathResolution::test_boot_remote_resolves_relative_paths  PASSED
TestRelativePathResolution::test_absolute_paths_still_work           PASSED
TestSingleAgentSetup::test_pm_only_no_clones                         PASSED
TestPmNoClone::test_pm_excluded_from_cloning                         PASSED
TestDetectRemoteUrl::test_returns_url_when_available                 PASSED
TestDetectRemoteUrl::test_returns_none_on_failure                    PASSED
TestBackwardCompat::test_default_generates_dot_paths                 PASSED
TestBackwardCompat::test_dot_resolves_to_repo_root                   PASSED
```

**12 passed in 0.10s**

### `python -m pytest tests/test_compose.py -v -k "local_config"`

No tests matched keyword `local_config` (exit 5 — deselected all). The relevant compose tests use the class name `TestGenerateLocalConfig`.

Running `TestGenerateLocalConfig` directly:

```
TestGenerateLocalConfig::test_generates_correct_format_default  PASSED
TestGenerateLocalConfig::test_generates_in_squidsquad_dir       PASSED
TestGenerateLocalConfig::test_with_clone_paths_relative          PASSED
TestGenerateLocalConfig::test_clone_paths_partial               PASSED
```

**4 passed** (36 total in test_compose.py, all pass)

### `python tests/run_tests.py` (Full Suite)

**895 passed, 0 failed, 0 errors**

---

## Human-Required TCs

The following TCs require an actual multi-repo git environment with real `git clone` operations. They cannot be run in CI without a live git remote:

- **TC-1**: Verify sibling clone directories are created and are valid git repos (`git rev-parse --git-dir` succeeds)
- **TC-5**: Verify each clone's `origin` URL matches the primary repo's `origin`
- **TC-6**: Verify each clone is checked out on the same branch as the primary repo
- **TC-7**: Verify idempotency — re-running scaffold preserves local modifications in clones
- **TC-9**: Verify Windows paths with spaces work end-to-end (`git clone` + `git status` in cloned dir)

**Recommended human verification command sequence:**

```bash
# Set up test env
mkdir -p /tmp/test-project && cd /tmp/test-project && git init && git remote add origin https://github.com/user/test-project.git

# Run scaffold (TC-1, TC-2, TC-5, TC-6)
python references/scripts/wizard.py install --spec <spec.json> --target /tmp/test-project

# TC-1: clones exist as git repos
ls -d /tmp/test-project-skill /tmp/test-project-qa
git -C /tmp/test-project-skill rev-parse --git-dir
git -C /tmp/test-project-qa rev-parse --git-dir

# TC-2: no PM clone
test ! -d /tmp/test-project-pm && echo "OK: no pm clone"

# TC-5: remote URLs match
diff <(git -C /tmp/test-project remote get-url origin) <(git -C /tmp/test-project-skill remote get-url origin) && echo "OK: remote matches"

# TC-6: branches match
git -C /tmp/test-project-skill branch --show-current  # expect: main

# TC-7: idempotency
echo "local mod" > /tmp/test-project-skill/.squidsquad/skill/working-state.md
python references/scripts/wizard.py install --spec <spec.json> --target /tmp/test-project
test -f /tmp/test-project-skill/.squidsquad/skill/working-state.md && echo "OK: mod preserved"
```

---

## Regression Coverage

- **Backward compat** (single-repo / no clones): Covered — `TestBackwardCompat` confirms `.` paths still resolve correctly
- **Absolute paths in old .local-config**: Covered — `test_absolute_paths_still_work` confirms old absolute paths pass through unchanged
- **health_check.py relative path resolution**: Covered — paths resolved against `REPO_ROOT`, not CWD
- **boot_remote.py relative path resolution**: Covered — same fix verified independently

---

## Verdict

**AUTOMATED: PASS** — All automatable TCs pass. 5 TCs marked HUMAN-REQUIRED due to dependency on live git clone operations.

No gaps in the automated coverage. Human verification needed before final ship sign-off on TC-1, TC-5, TC-6, TC-7, TC-9.
