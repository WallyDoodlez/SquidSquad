# TEST-PLAN-12854 — current-state staleness flag (reader-side health signal)

- **Issue**: #12854 (type:issue, severity:medium, role:skill) — `current-state` goes stale (frozen on a CLOSED issue's activity) when an agent stops mid-cycle, misleading health diagnosis (it reads authoritative but is last-known).
- **PR**: #13131, branch `squidsquad/task/12854` @ `ebacdad16`. Files: `health_check.py` (+26/-1), `tests/test_12854_current_state_stale_flag.py` (+110/-0). No closing keyword.
- **Derived**: 2026-06-21 01:20. Deterministic health-check code → **NO CQ**.
- **RCA (cross-checked)**: current-state is gitignored → mtime is a reliable freshness measure (no git-touch confound). `cycle_post` writes `idle` on a clean cycle end (covers idle/task-change), but a **mid-cycle stop** never reaches `cycle_post` → frozen content. A stopped agent can't self-write → **reader-side** flag is the fix.
- **Method**: isolated worktree; test suite; independent mtime-toggle probe; full static gate.

## Acceptance criteria (derived)

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | `check_agent_health` exposes `current_state_stale: bool` (documented), True when current-state mtime is older than the staleness window (`interval*2`). | Diff + docstring; probe. |
| AC2 | Flag toggles correctly: fresh → False, old → True. | Independent probe: fresh(0m)=False, old(90m, threshold 60)=True. |
| AC3 | `format_table` marks a stale phase with a leading `~` (never presents frozen content as live); JSON field is the authoritative signal. | Diff + `test_table_marks_stale_phase_with_tilde`. |
| AC4 | No false positive when there is no state file. | `test_no_state_file_is_not_stale`. |
| AC5 | Test coverage for fresh / alive-frozen-flagged / mtime-fallback / table-mark cases. | 6/6 in `test_12854_current_state_stale_flag.py`. |
| AC6 | No regression. | `run_tests.py static`. |
