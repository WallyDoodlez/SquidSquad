# QA-RESULTS-12451 — VERDICT: PASS (zero gaps)

- **Verified**: 2026-06-21 01:15 by verifier (qa), POLLING-mode cycle 3.
- **Task**: #12451 (type:task/medium, role:skill). **PR**: #13024 @ `376cf1426`, branch `squidsquad/task/12451`, OPEN, no `review:human-required`.
- **Env**: isolated worktree (removed). S2 touches the fleet-wide `event-mode-contract.md` → CQ HARD GATE applied.

## AC walk — live evidence

- **AC1 — wake mode displayed (PASS).** `references/statusline.sh:102`: `WAKE_MODE=$(... statusline_data.py mode "$ROLE" ...)` — the statusline already consumes the mode (the task confirmed the wiring; no change needed). `test_event_mode_reported` + `test_polling_mode_reported` green.
- **AC2 — idle event-mode not stalled (PASS).** `cmd_phase` in event mode pulls phase from the harness (`/agents/<role>`), not the on-disk file; the overdue/stale block is gated to the non-event branch. `test_event_mode_uses_harness_not_stale_file`, `test_overdue_block_is_gated_to_non_event_branch`.
- **AC3 — loop-mode staleness preserved (PASS).** `test_missed_interval_renders_overdue_badge` + `test_computes_elapsed_and_remaining_from_mtime` confirm loop-mode still flags a missed interval from `current-state` mtime — existing behavior intact.
- **AC4 — inline distinct state (PASS).** New `_is_inline_marker()` gives the agent-self-written `inline` marker **precedence in either wake mode** (the wrappers can't refresh it, so a stale harness phase must not mask it) → renders `inline|operator session`. `test_inline_beats_stale_harness_phase_event_mode`, `test_inline_surfaced_in_polling_mode`, `test_inline_substring_is_not_a_marker` (no false match).
- **AC5 — no event-mode file-age verdict (PASS).** Event mode never applies the file-age "stalled" verdict (overdue block gated to non-event). #12271 activity-heartbeat correctly OUT of scope (fast-follow).
- **AC6 — unit coverage (PASS).** 26/26 across `test_12451_idle_marker_discipline.py` (AC8 presence-locks) + `test_12451_statusline_event_model.py` (inline detect/precedence, event-mode-no-file-age, mode visible) + `test_12451_statusline_loop_mode_staleness.py` (loop regression, event-no-staleness).
- **AC7 — installer-files (PASS).** In-place edits to `statusline_data.py` + `event-mode-contract.md`; no new runtime file → installer-files correctly unchanged (not in PR).
- **AC8 — CQ HARD GATE (PASS).** Verifier-authored `tests/comprehension/12451_spec.json` on the S2 "Keep current-state honest" rule. Fresh sonnet (id a78e0d0e6a689522d) given ONLY the rule + Case C, no issue context → **4/4 correct, zero anti-patterns**: write idle marker on task-close (prevents #12854), write new task's marker ON THE TRANSITION across every pickup path, freshness = write-on-transition not file-age cadence, idle ≠ inline (distinct).

## Disagreement-is-finding
None on the ACs. The fix correctly closes the narrow gaps on top of the existing `statusline_data.py` mode-branching (did not rebuild), and the S2 write-side rule is the correct complement to #12854's reader-side flag.

## Hygiene flag (non-blocking → DM)
PR #13024 carries `.squidsquad/skill/working-state.md` (+12/-2) — an agent state-file the #11511 state-guard normally strips from feature branches. Self-healing (skill's next cycle overwrites main on its own clone), but DM should strip/reconcile it at merge so it doesn't revert skill's current main state. Not an AC failure; flagged for delivery hygiene (and worth skill confirming the state-guard didn't have a gap here).

## Verdict
**PASS — zero gaps.** AC1–AC8 confirmed (26/26 unit + statusline.sh mode-wiring + 4/4 CQ + 4850 static gate). Status → **pending-ship** (verifier-lead). Merge **deferred to DM** (no closing keyword; DM owns ship + counter + the working-state.md hygiene strip). Counter **NOT** bumped.
