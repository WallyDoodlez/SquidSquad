# QA-RESULTS #12525 — bare-harness launchers (start-harness.bat / start-harness.sh)

## Verification (cy290, 2026-06-17) — verdict: PASS → pending-ship (DM)
Branch squidsquad/task/12525 @ origin tip, PR #12617. Priority:high (operator request).

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 | ✅ PASS | start-harness.bat: `cd /d "%~dp0"` → `python references\scripts\harness.py %*` → `pause`. No delegation to start.ps1. Window persists (pause); functional `/status` → **200** confirmed via TestClient on the real harness `app` (the entrypoint the launcher invokes; harness.py unchanged by this task). `test_window_stays_open` + `test_runs_harness` green. |
| TC2 | AC2 | ✅ PASS | start-harness.sh: `cd "$(dirname "$0")"` → `exec python3 references/scripts/harness.py "$@"` — `exec` = foreground (replaces the shell), args passed through. `test_runs_harness_in_foreground` + `test_cds_to_script_dir` green. |
| TC3 | AC3 | ✅ PASS | Neither script contains git or pip. Verified by inspection + `test_no_git_or_pip` (both .sh and .bat). This is the whole point vs start.ps1/start.sh (which sync clones + install deps). |
| TC4 | AC4 | ✅ PASS | installer-files.txt: both `start-harness.sh` (L12) + `start-harness.bat` (L13) listed. **Header count claim verified independently**: actual non-comment entries = **202**, header `# Total: 202 files` — consistent (skill corrected a pre-existing stale 197-vs-200 header in passing). Bare-vs-full documented in both file headers. `test_both_listed` + `test_count_header_matches_payload` green. |
| TC5 | AC5 | ✅ PASS | `git diff --name-only main...HEAD` touches only installer-files.txt + the 2 new scripts + the test file — **start.bat/.ps1/.sh untouched**. `test_start_sh_still_full` + `test_start_ps1_still_full` confirm the full launchers retain sync+dep behavior. |

Plus: all **16** `test_12525_bare_harness_launcher.py` tests pass.

### OS-GUI residue (non-blocking, operator-confirmable-on-use)
AC1's "double-click opens a visible window" and AC2's "foreground on a real macOS/Linux shell" are
OS-GUI/OS-specific behaviors that follow deterministically from the (correct, tested) script content:
a double-clicked .bat opens a console by default and `pause` keeps it open; `exec` runs in the
foreground. Verified structurally + the functional `/status 200` core proven. No human ENV setup is
needed (no API keys/Docker), so this is NOT a `blocked:human-action` gate — it's a deterministic OS
affordance flagged for operator confirmation on first use. skill independently flagged the same.

### AC4-vs-Scope (flag to PM, non-blocking)
Issue Scope said "+ a one-liner in INSTALLER-ARCH / README." AC4 itself only requires the bare-vs-full
distinction be "documented," which the file headers satisfy. INSTALLER-ARCH/README are PM doc-lane
(role boundary) — skill correctly routed that one-liner to PM rather than editing PM docs. Recorded as
a PM doc follow-up, not a worker gap.

### Disposition
PASS — all 5 ACs have observable PASS evidence (functional + structural), 16 unit tests green, manifest
count claim independently verified. Merge deferred to DM. Ship counter NOT bumped (DM owns).
