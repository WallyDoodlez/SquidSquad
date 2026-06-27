# QA-RESULTS-12801 — Harness TUI bottom action bar with reboot (per-agent/all, busy-aware, force)

**Verdict: PASS — zero gaps.** High-priority TASK; 8 ACs. PR #13269 merged (squash).

## AC walk (independent — derived from the 8 ACs in the issue body)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | TUI shows a bottom action bar listing reboot | PASS — live headless render: Footer mounted, BINDINGS `r=Reboot, R=Reboot all, f=Force reboot, q=Quit` |
| AC2 | reboot a specific agent AND all agents | PASS — `restart_agent` (cursor) + `restart_all`; harness `/agents/{role}/restart` + `/agents/all/restart` |
| AC3 | indicate whether the target is busy (in-flight/mid-cycle) | PASS — busy from `in_flight_until`/`current_cycle`/`intent`; `test_selected_agent_reports_busy` |
| AC4 | graceful = intent stopping→checkpoint→restart; force = immediate, overriding busy | PASS — graceful via intent=restarting (next-boundary exit); force = immediate PID kill (`?force=true`) |
| AC5 | force is a distinct, confirmed action | PASS — `ConfirmReboot` modal; `test_force_requires_confirm_then_dispatches_force` + `test_force_cancel_does_not_dispatch` |
| AC6 | reboot via lifecycle (not raw kill); force does NOT count toward crash-streak | PASS — `operator_force_at` stamp; classifier treats force-death as non-crash, authoritative only when `>= last_spawn_at` (a prior-session force can't excuse a later natural crash); consumed once; `test_operator_force_death_not_counted_toward_streak` |
| AC7 | tests for action dispatch + busy-detection + graceful-vs-force | PASS — 71 TUI/feature tests + 56 harness tests |
| AC8 | HARNESS-ARCH updated for the contract change | PASS — docs/HARNESS-ARCH.md +5 (new `/agents/all/restart`, `?force=true`) |

## Evidence
- Code: `references/tui/app.py` (HarnessTUI + ConfirmReboot modal + action bindings), `references/tui/harness_client.py` (restart_agent/restart_all, `?force=true` suffix), `references/scripts/harness.py` (force endpoint + all/restart + operator_force death-classification, +163), HARNESS-ARCH +5, installer-files.txt +8.
- skill tests: `test_feat_12801_reboot_action_bar.py` (force endpoint, crash-streak exclusion, marker-transient, client POST, action-bar dispatch, confirm/cancel, busy) + `test_tui_app_12801.py` + `test_tui_harness_client_12801.py` + `test_tui_render_12801.py` (Pilot headless) + `test_tui_requirements.py` + harness endpoint tests. **71 TUI/feature + 56 harness additions, all PASS** (full test_harness.py = 326).
- **QA independent headless render** (`tests/test_feat_12801_render_contract_qa.py`): drives the real HarnessTUI via Textual `App.run_test()`/Pilot, asserts the Footer is mounted and the BINDINGS advertise reboot (AC1) / reboot-all (AC2) / a distinct force action (AC5). Confirmed live: bindings `r/R/f/q`.
- Render-verification approach: Textual `App.run_test()` + Pilot — zero new dependency (textual 8.2.7 already fleet-wide). [[decision-tui-headless-render-verification]].

## Notes
- No CQ: TUI/harness code is deterministic, not LLM-consumed. HARNESS-ARCH is human-facing doc.
- Branch was behind main + GitHub showed a STALE "CONFLICTING"; a real test-merge into current main produced **0 conflicts**. Landed by bringing main into the branch (state files auto-merge; #13169's run_comprehension_test.py preserved from main) then squash-merge.

Status: pending-test → pending-ship.
