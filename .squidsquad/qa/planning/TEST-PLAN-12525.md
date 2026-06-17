# TEST-PLAN #12525 — minimal bare-harness launcher (start-harness.bat + start-harness.sh)

**Derived from the issue's explicit ACs 1-5** (operator request). Scripts/installer change → not
LLM-consumed → no comprehension gate.

## ACs (verbatim from issue, with my independent test method)
- **AC1**: `start-harness.bat` double-clicked on Windows → visible, persistent window; harness reaches /status 200.
- **AC2**: `start-harness.sh` starts the harness in the foreground on macOS/Linux.
- **AC3**: neither performs git operations or pip installs.
- **AC4**: both added to installer-files.txt; documented as the bare launcher vs start.* (full setup).
- **AC5**: no change to existing start.bat/.ps1/.sh behavior.

## Test Cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | inspect start-harness.bat (cd, python invocation, pause); 16-test `test_window_stays_open`+`test_runs_harness`; TestClient GET /status on the served app | bat invokes `python references\scripts\harness.py %*`, window persists; /status → 200 |
| TC2 | AC2 | inspect start-harness.sh (`exec python3 ... "$@"`); `test_runs_harness_in_foreground` | foreground exec (replaces shell), arg passthrough |
| TC3 | AC3 | grep both scripts for git/pip; `test_no_git_or_pip` (both) | no git, no pip |
| TC4 | AC4 | count manifest entries vs header; membership; header docs | 202 == 202, both listed, bare-vs-full documented |
| TC5 | AC5 | `git diff --name-only` (start.* absent); `test_start_sh_still_full`+`test_start_ps1_still_full` | start.bat/.ps1/.sh untouched, retain sync+dep |

## OS-GUI residue (non-blocking)
AC1 "double-click opens a visible window" and AC2 "foreground on a real macOS/Linux shell" are OS-GUI
behaviors deterministic from the (correct, tested) script content — verified structurally + functionally
(/status 200), flagged operator-confirmable-on-use. No human ENV setup required → not a
`blocked:human-action` gate.

## AC4-vs-Scope note
Issue Scope mentions "+ a one-liner in INSTALLER-ARCH / README." AC4 itself only requires "documented
as the bare launcher vs start.* (full setup)," which the file headers satisfy. INSTALLER-ARCH/README are
PM doc-lane (role boundary) — skill correctly routed that one-liner to PM. Not a worker gap.
