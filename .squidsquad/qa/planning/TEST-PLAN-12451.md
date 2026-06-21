# TEST-PLAN-12451 — Status bar: support the event model (event vs loop mode)

- **Task**: #12451 (type:task, priority:medium, role:skill). Mode-aware status bar; idle-event-mode not stalled; inline distinct state; S2 write-side "Keep current-state honest" (folds #12854 part-1).
- **PR**: #13024, branch `squidsquad/task/12451` @ `376cf1426`. Files: `statusline_data.py` (+29/-4), `event-mode-contract.md` (+3/-2), 3 test files (+295), `.squidsquad/skill/working-state.md` (+12/-2 — agent state-file, flagged). No closing keyword.
- **Derived**: 2026-06-21 01:15. S2 edits the fleet-wide `event-mode-contract.md` (every event-mode agent Reads at boot) → **CQ HARD GATE (AC8)**, verifier-authored.
- **Method**: isolated worktree; 3 test suites; statusline.sh mode-wiring check; fresh-agent CQ; full static gate.

## Acceptance criteria

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC1 | Statusline shows wake mode (event vs loop). | `statusline.sh:102` consumes `statusline_data.py mode`; `test_event_mode_reported` / `test_polling_mode_reported`. |
| AC2 | Legitimately-idle EVENT-mode agent shown healthy/idle, not stalled. | `test_event_mode_uses_harness_not_stale_file`, `test_overdue_block_is_gated_to_non_event_branch`. |
| AC3 | LOOP-mode agent still flagged stale on missed interval (regression). | `test_missed_interval_renders_overdue_badge`, `test_computes_elapsed_and_remaining_from_mtime`. |
| AC4 | Inline / no-wrapper agent renders as distinct labelled state. | `_is_inline_marker` precedence (either mode); `test_inline_beats_stale_harness_phase_event_mode`, `test_inline_surfaced_in_polling_mode`. |
| AC5 | Event-mode applies no file-age staleness verdict (#12271 OUT of scope). | `test_event_mode_uses_harness_not_stale_file`, overdue gated to non-event. |
| AC6 | Unit tests cover mode-aware freshness, inline, loop regression. | 26/26 across 3 test files. |
| AC7 | installer-files updated only if a new file is added (in-place edits → none). | No new runtime file; installer-files not in PR. |
| AC8 | CQ on the `event-mode-contract.md` "Keep current-state honest" rule (S2). | `tests/comprehension/12451_spec.json` + fresh sonnet. |

## Hygiene flag (non-blocking → DM)
PR carries `.squidsquad/skill/working-state.md` (+12/-2) — an agent state-file the #11511 state-guard normally strips from feature branches. Self-healing (skill's next cycle overwrites main), but DM should strip/reconcile at merge rather than revert skill's current state. Not an AC failure.
