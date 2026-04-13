# TASK-SKILL-442 QA Results -- Round 2

**Date:** 2026-04-11
**Verdict:** FAIL (2 items remain)

---

## PART A -- Previously Failed Items (11 checks)

| # | Item | Result | Notes |
|---|------|--------|-------|
| 1 | `statusline.sh` uses `type:task`/`type:issue` | **PASS** | Confirmed `type:issue` and `type:task` throughout; no `type:bug`/`type:feature` found. |
| 2 | DM CLAUDE.md references `issue-triage.md` | **PASS** | Sub-skill markers now read `issue-triage` (lines 307, 342). No `bug-triage` found. |
| 3 | `.github/ISSUE_TEMPLATE/` has renamed files | **FAIL** | Directory still contains `bug-report.yml` and `feature-request.yml`. Expected `issue-report.yml` and `task-request.yml`. |
| 4 | `references/agent-instructions.md` uses new labels | **PASS** | No `type:bug` or `type:feature` found. |
| 5 | `SKILL.md` has `/squidsquad-issue` | **PASS** | No `/squidsquad-bug` found. |
| 6 | `references/scripts/cycle.py` uses `--issues`/`--tasks` | **FAIL** | Lines 15 and 222 still show `--bugs` and `--features` flags. |
| 7 | `references/scripts/wizard.py` says "Issue severity" | **PASS** | No "Bug severity" found. |
| 8 | `references/scripts/diagnostics.py` says "Issue Report" | **PASS** | No "Bug Report" found. |
| 9 | Designer sub-skills free of old labels | **PASS** | No `type:bug`/`type:feature` labels. "feature" usage is generic English (design context), acceptable. |
| 10 | No bare `bug` label on GitHub | **PASS** | `gh label list --search "bug"` returned no `bug` label (only `status:open`). |
| 11 | PM/skill CLAUDE.md free of residuals | **PASS** | No `type:bug`, `type:feature`, `create-bug`, `create-feature`, `list-bugs`, or `list-features` in either file. |

**Part A score: 9/11 PASS**

---

## PART B -- Test Coverage

| # | Item | Result | Notes |
|---|------|--------|-------|
| 1 | Tests for renamed tracker commands | **PASS** | `test_tracker_authority.py` has `list_issues()` tests for `issue`, `task`, `bug` (backward-compat alias to `type:issue`), and `feature` (alias to `type:task`). `test_labels.py` validates `type:issue`/`type:task` exist. |
| 2 | Tests pass | **PASS** | Static analysis: 530/530 passed. Integration: 17/17 passed (second run; first run had 2 flaky timing failures in status-flow transitions -- GitHub API race condition, not rename-related). |
| 3 | Label rename validation tests | **PASS** | `test_labels.py` line 17 asserts `EXPECTED_TYPE_LABELS = {"type:issue", "type:task"}`. `test_tracker_authority.py` tests backward-compat aliases (bug->issue, feature->task). |

**Part B score: 3/3 PASS**

---

## PART C -- Generic English Preservation

| # | Item | Result | Notes |
|---|------|--------|-------|
| 1 | `manifest.py` keeps generic "bug" | **PASS** | Lines 36-37 still use "bug" in generic English context ("walker bug, not a manifest bug"). |
| 2 | `test_git_ops.py` keeps `feature/test` branch | **PASS** | Line 182 still has `git_ops.branch_create("feature/test")`. |

**Part C score: 2/2 PASS**

---

## Remaining Failures (2)

### FAIL #3 -- Issue templates not renamed
- **File:** `.github/ISSUE_TEMPLATE/`
- **Current:** `bug-report.yml`, `feature-request.yml`
- **Expected:** `issue-report.yml`, `task-request.yml`
- **Action:** Rename both files and update their internal `name:` fields accordingly.

### FAIL #6 -- cycle.py still uses old CLI flags
- **File:** `references/scripts/cycle.py` lines 15, 222
- **Current:** `--bugs <b> --features <f>`
- **Expected:** `--issues <i> --tasks <t>`
- **Action:** Rename the CLI flags in the docstring (line 15) and usage string (line 222), plus any argparse/flag-parsing logic that references them.

---

**Overall: FAIL -- 2 gaps remain. Fix and resubmit for R3.**
