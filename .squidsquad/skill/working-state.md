# Working State

- **Task**: 12801 (in-progress) — Harness TUI. Branch squidsquad/task/12801. S1.1+S1.2 done; S1.3 next.
- **Updated**: 2026-06-19 10:55 (skill — event-mode; #12800 shipped pending-test PR#12902; #12801 S1.1+S1.2 done)
- **Quiet Cycle Counter**: 0

## #12801 Harness TUI (in-progress) — decomposed, S1.1+S1.2 landed
Plan: `.squidsquad/skill/planning/TUI-12801-DECOMPOSITION.md` (4 Stories). Contract: `.squidsquad/pm/planning/TUI-INTERFACE-DESIGN.md` (operator-approved). Textual, separate process consuming harness HTTP. Wake LAST (gated #12495).
- **S1.1 DONE** (branch squidsquad/task/12801): harness.py `EventLifecycleManager.lag_for(role)` (events-behind-head; 0=caught up, N=behind, no-cursor/evicted=full depth) + GET /status injects per-agent `lag`. Tests TestCursorLag12801 (6); full test_harness.py 293 passed.
- **S1.2 DONE** (branch): references/tui/harness_client.py (+__init__.py) — derive_work_state (working/idle/down + colors), lag_to_bar (→ arrow, left-third alert), agent_rows, fetch_status/fetch_human_queue (graceful None on unreachable). Tests test_tui_harness_client_12801 (17). Added both tui files to installer-files.txt. **NIT to fix on next branch commit: installer-files.txt header still says "Total: 206 files" → should be 208 (cosmetic, untested).**
- **S1.3 NEXT**: Textual app skeleton (references/tui/app.py + entry script) — title bar 🦑 SquidSquad · <project>, refresh loop polling harness_client, panel placeholders. Needs textual dep installed to run (S1.4). **Substantial UI work — fresh context ideal.**
- **S1.4**: textual dep → requirements + installer-files.txt + start scripts (NEW references/tui/ files MUST be in installer-files.txt — AC).
- **S2**: panels (Agents+lag bar+GREEN/YELLOW/RED, Needs You, Pipeline, Activity) + branding.
- **S3** (AC core): action bar Reboot/Reboot All/Force (busy-aware via lifecycle intent SM, force≠crash per #12244) + Options(Change background) + Bring-PM-Forward. May need small reboot_agent/harness flag for force-not-a-crash.
- **S4**: Wake GATED on #12495.
- AC8: HARNESS-ARCH update for /status `lag` + force-not-a-crash. DS-review per Story. PR when substantially built.

## #12800 SHIPPED → pending-test (PR #12902) (8 ACs, high-blast-radius)
All gates green: targeted 101 passed, static gate 4621 passed (0 fail), integration 53 OK, DS review NO_FINDINGS, deploy-all rc=0, AC2 e2e verified.
- **AC1** (alias registers): config.py role-class split — AGENT_ROLE_CLASSES{pm,worker,verifier,dm} + NON_AGENT_ROLE_CLASSES{human}; ALIASES_ROLE_CLASSES=union. tracker.py already accepts role:human (free-form labels; FEEDBACK_ROLES has human). Tests: human accepted table+bullet, multi-human, canonicalize human.
- **AC2** (compose skips human): compose.deploy_alias_v2 + check_alias_staged_l4 skip NON_AGENT (return None / role_class); deploy + deploy-all treat None as clean no-op. Tests + e2e deploy-all-skips-2-humans.
- **AC3** (routing flip): harness EAD _STATUS_ROUTING += pending-human-review|setup -> ('role_class','human'). is_handoff excludes non-agent role-classes (human not on bus → emit once, no #12442 re-emit pileup). Tests: routes-to-human ×2 + no-reemit-timer.
- **AC4** (inline status bar): cycle.py status-bar-self 'inline'/clear. Instruction sources (instructions.md + 4 ralph-loop) updated. Test: inline write+clear.
- **AC5** (return path): async via work_queue — ticket keeps role:<originator> (EAD routes pending-human by role_class not label), returns at in-progress, surfaces in originator work_queue. Test added.
- **AC6/AC8** (docs reconcile): AGENT-RUNTIME Terminology/§3/§8.3 already rev-16; added L124 #9358-superseded + rev-17 changelog. Stale #9358 inline text replaced in 5 sources.
- **AC7**: no new source files → installer-files.txt unchanged (CONFIRMED).
- **AC8** (DS-audit): DS review NO_FINDINGS (.squidsquad/skill/planning/DS-REVIEW-12800.md); 8 paths audited incl human-never-an-agent invariant. DS thoroughness note: _get_entry_file_for_role('human') falls back to worker but only reachable via wizard which validates references/roles/human/ exists first (doesn't) → ValueError before composition. No realistic path.

## Shipped earlier this session
- #12820 (PR #12883 MERGED, shipped), #12853 (PR #12894 MERGED, shipped).

## Next pickup (verify via work-queue, don't trust this)
Per boot work-queue: in-progress items #10855 (medium, prior misdiagnosis-resolved non-bug — check if stale), #12493, #12450 (S3/S4 PM-gated); #12801 (approved, TUI bottom action bar, handed to me). HIGH open bugs #12837/#12409/#12397/#11600.

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
