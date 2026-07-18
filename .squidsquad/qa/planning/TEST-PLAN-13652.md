# TEST-PLAN-13652

Derived independently from the issue body (`ISSUE: improvement-scan: no commit-code/commit-state path fits verifier's own CQ-spec artifacts (tests/comprehension/)`). My own filed issue (from the #13551 verification pass). Suggested two options; skill chose (a) — extend `commit_state()`'s allowlist.

## ACs derived from the issue

- **AC1**: `commit_state(role="qa", ...)` stages `tests/comprehension/*.json` files (both a new per-issue spec and the shared `.staleness-baseline.json`) alongside `.squidsquad/*` files, in one commit, on the working branch (`main`).
- **AC2**: The allowance is scoped to `role == "qa"` only — a `skill`-authored comprehension edit must NOT get silently staged/committed via `commit_state` (it already has a fitting path via `commit_code` on a feature branch; this is a role-boundary/lane-safety property, not just a preference).
- **AC3**: Unrelated files (a random `.py` under `tests/`, non-`.json` comprehension fixtures) are still correctly excluded from staging.
- **AC4**: The design is consistent with the existing precedent — `_role_owned_patterns("qa")`'s `tests/comprehension/` allowance for the sibling `commit_role_scoped` path (#13212) — not an invented one-off rule.
- **AC5**: No regression — existing `commit_state` behavior for `.squidsquad/*` files (all roles) is unchanged; new tests + full static gate pass.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | Real (non-mocked) end-to-end run: built a disposable local git repo (bare + working clone, real origin) with a pre-tracked `tests/comprehension/` dir, dropped a real copy of the fixed `git_ops.py` in, created a new spec file + a `.squidsquad/` doc + an unrelated file, ran `git_ops.commit_state("qa", ...)` for real — inspected the actual resulting commit |
| TC2 | AC2 | Same disposable-repo setup: created an untracked comprehension spec, ran `commit_state("skill", ...)` for real — confirmed it returns `False` ("No state changes to commit") and the file stays untracked |
| TC3 | AC3 | TC1's unrelated `tests/test_unrelated.py` file was left untracked/uncommitted by the same real run — confirmed directly in the resulting `git status --porcelain` |
| TC4 | AC4 | Read `_role_owned_patterns()` (~line 1668) directly — confirmed the qa-only `tests/comprehension/` allowance for `commit_role_scoped` genuinely predates this PR (#13212), so the new predicate mirrors real precedent |
| TC5 | AC1/AC2/AC3 | `tests/test_13652_commit_state_verifier_artifacts.py` (9 cases) — mocked-plumbing coverage of the same scenarios, as a locked regression |
| TC6 | AC5 | `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |

## Note
This is git_ops.py tooling I invoke directly every task-begin/task-end/commit-state cycle (used it twice already this session, for #13531 and #13551) — verified with a real git repo and real subprocess calls, not mocks, since a defect here would corrupt my own commit history.
