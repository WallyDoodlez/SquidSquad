# FEAT-67 Test Plan — Integration Test Framework

**Feature**: Build the skill self-test framework (pytest-based static analysis)
**Scope**: Meta-tests — verifying the test framework itself works correctly
**Phase**: 1 (static analysis only, no GH/git integration tests)

---

## A. Static Analysis Tests Exist and Run

### TC-01: Full static test suite runs without errors
- **Command**: `python -m pytest tests/ --ignore=tests/integration/ -q`
- **Expected**: Exit code 0, all tests collected and pass
- **Failure means**: Framework is broken at a fundamental level

### TC-02: test_labels.py loads and has at least 1 test
- **Command**: `python -m pytest tests/test_labels.py --collect-only -q`
- **Expected**: At least 1 test collected, no import errors
- **Failure means**: test_labels.py has syntax errors or no test functions

### TC-03: test_references.py loads and has at least 1 test
- **Command**: `python -m pytest tests/test_references.py --collect-only -q`
- **Expected**: At least 1 test collected, no import errors
- **Failure means**: test_references.py has syntax errors or no test functions

### TC-04: test_manifest.py loads and has at least 1 test
- **Command**: `python -m pytest tests/test_manifest.py --collect-only -q`
- **Expected**: At least 1 test collected, no import errors
- **Failure means**: test_manifest.py has syntax errors or no test functions

### TC-05: test_composition.py loads and has at least 1 test
- **Command**: `python -m pytest tests/test_composition.py --collect-only -q`
- **Expected**: At least 1 test collected, no import errors
- **Failure means**: test_composition.py has syntax errors or no test functions

### TC-06: test_config.py loads and has at least 1 test
- **Command**: `python -m pytest tests/test_config.py --collect-only -q`
- **Expected**: At least 1 test collected, no import errors
- **Failure means**: test_config.py has syntax errors or no test functions

### TC-07: test_roles.py loads and has at least 1 test
- **Command**: `python -m pytest tests/test_roles.py --collect-only -q`
- **Expected**: At least 1 test collected, no import errors
- **Failure means**: test_roles.py has syntax errors or no test functions

### TC-08: test_vault.py loads and has at least 1 test
- **Command**: `python -m pytest tests/test_vault.py --collect-only -q`
- **Expected**: At least 1 test collected, no import errors
- **Failure means**: test_vault.py has syntax errors or no test functions

### TC-09: conftest.py provides repo_root fixture
- **Command**: `python -m pytest tests/test_config.py -q` (any test that uses repo_root)
- **Expected**: Tests run without "fixture 'repo_root' not found" error
- **Verification**: `grep -c "repo_root" tests/conftest.py` returns >= 1
- **Failure means**: conftest.py missing or repo_root fixture not defined

---

## B. Static Tests Catch Known Bugs

Each test case below introduces a deliberate defect, verifies the relevant test catches it, then reverts the defect. The revert step is mandatory — never leave the repo in a broken state.

### TC-10: test_labels.py catches bare `bug` label
- **Setup**: In a sub-skill file (e.g., `references/sub-skills/common/bug-filing.md`), temporarily replace one `type:bug` with bare `bug` in a `--label` argument
- **Run**: `python -m pytest tests/test_labels.py -q`
- **Expected**: At least 1 FAILED test mentioning the bare label
- **Teardown**: `git checkout -- references/sub-skills/common/bug-filing.md`
- **Failure means**: Label validation regex is too loose or not scanning the right files

### TC-11: test_references.py catches features/INDEX.md reference
- **Setup**: In a sub-skill file (NOT `features/INDEX.md` itself), temporarily add the string `features/INDEX.md` (e.g., append a comment line to `references/sub-skills/roles/dev-agent.md`)
- **Run**: `python -m pytest tests/test_references.py -q`
- **Expected**: At least 1 FAILED test mentioning stale INDEX.md reference
- **Teardown**: `git checkout -- references/sub-skills/roles/dev-agent.md`
- **Failure means**: Stale reference patterns are incomplete or exception list is wrong

### TC-12: test_references.py catches PM/QA reference in non-PM template
- **Setup**: In a non-PM sub-skill file (e.g., `references/sub-skills/roles/dev-agent.md`), temporarily add `PM/QA` string
- **Run**: `python -m pytest tests/test_references.py -q`
- **Expected**: At least 1 FAILED test mentioning stale PM/QA reference
- **Teardown**: `git checkout -- references/sub-skills/roles/dev-agent.md`
- **Failure means**: PM/QA pattern not checked, or exception list incorrectly exempts this file

### TC-13: test_manifest.py catches missing sub-skill file
- **Setup**: Temporarily rename one sub-skill file listed in manifest.md (e.g., `mv references/sub-skills/common/bug-filing.md references/sub-skills/common/bug-filing.md.bak`)
- **Run**: `python -m pytest tests/test_manifest.py -q`
- **Expected**: At least 1 FAILED test reporting the missing file
- **Teardown**: `mv references/sub-skills/common/bug-filing.md.bak references/sub-skills/common/bug-filing.md`
- **Failure means**: Manifest parsing or file existence check is broken

### TC-14: test_config.py catches invalid version format
- **Setup**: In `.squidsquad/config.md`, temporarily change the version field to an invalid value (e.g., `vX.Y` instead of semver like `0.5.0`)
- **Run**: `python -m pytest tests/test_config.py -q`
- **Expected**: At least 1 FAILED test reporting invalid version format
- **Teardown**: `git checkout -- .squidsquad/config.md`
- **Failure means**: Version validation regex is too permissive

---

## C. Config Integration

### TC-15: config.md has Skill Tests field
- **Command**: `grep -c "Skill Tests" .squidsquad/config.md`
- **Expected**: Returns >= 1 (field exists)
- **Failure means**: Config update was missed during implementation

### TC-16: Running the skill test command from config produces output
- **Steps**:
  1. Read the `Skill Tests` value from `.squidsquad/config.md`
  2. Execute that command (expected: `python -m pytest tests/ --ignore=tests/integration/ -q`)
  3. Verify it produces pytest output (contains "passed" or test collection info)
- **Expected**: Command exits 0 and output contains pytest summary line
- **Failure means**: Config command is wrong or pytest is not installed

### TC-17: Dev agent template references skill tests for sub-skill changes
- **Steps**: Search `references/sub-skills/roles/dev-agent.md` (or the relevant dev agent template) for a reference to running skill tests when sub-skill files are modified
- **Expected**: Template contains guidance about running skill tests
- **Failure means**: Side effect mitigation from CONTEXT.md was not implemented

---

## D. Framework Structure

### TC-18: tests/ directory exists with expected files
- **Check**: All of these paths exist:
  - `tests/conftest.py`
  - `tests/test_labels.py`
  - `tests/test_references.py`
  - `tests/test_manifest.py`
  - `tests/test_composition.py`
  - `tests/test_config.py`
  - `tests/test_roles.py`
  - `tests/test_vault.py`
- **Expected**: All 8 files exist
- **Failure means**: Implementation is incomplete

### TC-19: requirements-dev.txt exists with pytest
- **Check**: `requirements-dev.txt` exists at repo root and contains `pytest`
- **Expected**: File exists, contains a line with `pytest` (e.g., `pytest>=7.0`)
- **Failure means**: Dev dependency file was not created

### TC-20: conftest.py provides repo_root fixture
- **Check**: Read `tests/conftest.py`, verify it defines a `repo_root` fixture
- **Expected**: Contains `def repo_root` and uses `@pytest.fixture`
- **Failure means**: Shared fixture infrastructure is missing

### TC-21: Tests use pathlib for cross-platform paths
- **Check**: Each test file imports `pathlib` or `Path`, and does NOT use hardcoded `/` or `\\` path separators in file path construction
- **Expected**: All path construction uses `pathlib.Path` or `os.path.join`
- **Failure means**: Tests will break on Windows or Unix depending on what was hardcoded

---

## E. False Positive Check

### TC-22: Clean repo produces zero test failures
- **Precondition**: No deliberate defects introduced, repo is in its normal committed state
- **Command**: `python -m pytest tests/ --ignore=tests/integration/ -q`
- **Expected**: ALL tests pass, zero failures, zero errors
- **Critical**: This is the most important test case. False positives erode trust in the test suite. If any test fails on a clean repo, it is a bug in the test framework, not in the skill files.
- **Failure means**: A test has an incorrect assertion, wrong regex pattern, or bad assumption about repo structure. Must be fixed before shipping.

### TC-23: Clean repo produces zero warnings from test collection
- **Command**: `python -m pytest tests/ --ignore=tests/integration/ -q 2>&1`
- **Expected**: No pytest warnings about missing fixtures, deprecated usage, or import issues
- **Failure means**: Test infrastructure has latent issues that will confuse developers

---

## Test Execution Order

Run in this order to fail fast on fundamental issues:

1. **TC-18, TC-19, TC-20** — Structure exists (no point running tests if files are missing)
2. **TC-09** — Fixture works
3. **TC-22, TC-23** — False positive check (clean repo must pass first)
4. **TC-01** — Full suite runs
5. **TC-02 through TC-08** — Individual test files load
6. **TC-10 through TC-14** — Defect injection tests (B section)
7. **TC-15, TC-16, TC-17** — Config integration
8. **TC-21** — Cross-platform check

---

## Pass Criteria

- **All 23 TCs must pass** to mark FEAT-67 as Pending Ship
- **TC-22 is a hard gate** — any false positive on clean repo blocks the entire feature
- Each TC-10 through TC-14 must revert its changes (verify with `git status` showing clean after each)
