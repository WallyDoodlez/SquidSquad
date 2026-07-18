# TEST-PLAN-13611

Derived independently from the issue body (this is my own filed improvement-scan finding, but the AC list is still derived fresh from the issue text, not from the worker's diff).

## ACs derived from the issue

- **AC1**: The teardown idle-wait loop in `harness._teardown_and_exit` no longer reads `SQUIDSQUAD_DIR / role / "current-state"` (harness-root path) for sibling-clone agents; it reads from the agent's own clone instead.
- **AC2**: A `None`/unresolvable/missing-file result is treated as **NOT confirmed idle** (`all_idle = False`), never silently treated as idle.
- **AC3**: A genuinely mid-task sibling-clone agent (current-state != "idle*" in its own clone) is NOT force-killed early — the wait loop keeps polling up to its ~30s grace window.
- **AC4**: A stale/misleading "idle" file sitting at the harness-root path must NOT override the agent's own clone's real (non-idle) state.
- **AC5**: Reuses the existing `_read_agent_clone_file` helper (#13558) rather than duplicating clone-resolution logic — consistent with the suggested fix.
- **AC6**: New regression tests (`test_13611_teardown_idle_wait_clone.py`) cover all three of: reads-from-clone-and-breaks-immediately-when-idle, missing-file-not-treated-as-idle, harness-root-stale-idle-file-ignored.
- **AC7**: No sibling occurrences of the same harness-root-read pattern remain in `harness.py`.
- **AC8**: Comprehension staleness clean; no regressions (full static gate).

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC5 | `git diff origin/main -- references/scripts/harness.py`; confirm it calls `_read_agent_clone_file` |
| TC2 | AC2/AC3/AC4 | Read + run `test_13611_teardown_idle_wait_clone.py`'s three cases directly (they exercise exactly these scenarios against the real `_teardown_and_exit` function, not a reimplementation) |
| TC3 | AC6 | Run the full test file, confirm 3/3 pass |
| TC4 | AC7 | Independent `grep -n "SQUIDSQUAD_DIR / role" references/scripts/harness.py` — zero hits post-fix |
| TC5 | AC8 | `comprehension_staleness.py check`; `tests/run_tests.py static` |
