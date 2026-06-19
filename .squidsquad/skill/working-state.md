# Working State

- **Task**: 12906 (in-progress, code path located) — Phase 1 of #12895 (operator-approved): harness recompose ensure-main+pull-first. Implementation deferred to fresh context (high-blast-radius L4 watcher + extreme context depth; pending harness restart provides it).
- **Updated**: 2026-06-19 11:33 (skill — event-mode; #12906 claimed+investigated; #12903 shipped)
- **Quiet Cycle Counter**: 0

## #12906 (HIGH, operator-approved Phase 1 of #12895) — TOP next-pickup, plan captured
The operator DECIDED on #12895: Phase 1 = harness recompose/deploy must ensure-main + pull-first (kills stale-source revert at root). Phase 2 (non-interruption layer) stays on #12895 (PM arch spec pending) — do NOT build here.
- **Code path located:** \`references/scripts/l4_file_watcher.py\` deploy helper (~L135, L196-203) shells out to \`compose.py deploy <alias>\`. Guard goes BEFORE it, ONCE per recompose batch.
- **Guard:** git_ops has current_branch()/branch_switch('main')/pull() — ensure-on-main + pull() before deploy. 
- **Impl TODO (fresh ctx):** (a) check restart/boot recompose path also needs the guard; (b) tolerate uncommitted state in harness clone; (c) AC1 test = behind-clone recompose pulls first (composed reflects origin, not stale local); AC2 no-regression vs deploy-all; AC3 installer-files. Full plan on the #12906 comment.

## THIS CYCLE (after the long #12800/#12801 session)
- **#12903** (LOW, qa improvement-scan): run_tests.py integration_only guard drift → fixed (shared _INTEGRATION_MODULES registry; dispatch+guard one source; data-driven importlib loop) + 6 regression tests. **SHIPPED pending-test, PR #12904.**
- **CLONE WAS 21 COMMITS BEHIND origin** (chronic boot-pull lag) — #12895 bit me: 8 composed CLAUDE.md files dirty-reverted by stale-source recompose. Stashed+DISCARDED them, git-pull-synced (composed back to correct), then worked on synced base. Posted as 3rd-occurrence live evidence on #12895.
- **Vault gate blocker fixed**: DM's galaxy note pattern-ship-gate-preserve-expanded-scope.md (from #12853 ship) lacked YAML frontmatter → broke fleet-wide test_vault static gate. Added frontmatter (body untouched, my lane = code-consumed data), committed to main. Recurring issue (also happened #12853) — candidate for a process guard (vault-remember frontmatter enforcement / pre-commit) — improvement-scan finding.
- Full static gate after fixes: 4635 passed, 0 fail.
- **Filed #12905** (medium, mine): the recurring vault-frontmatter gate-breaker → suggested write-time guard (pre-commit hook rejecting galaxy/*.md without frontmatter + test). **Fix is HIGH-blast-radius (pre-commit gates every commit) → fresh context.**

## NEXT actionable (fresh/equipped context — both want clean budget)
1. **#12905** (medium bug): add pre-commit galaxy-frontmatter guard + test. High-blast-radius (pre-commit hook) → fresh context; verify hook fires without blocking legit commits.
2. **#12801** S1.3+ (Textual TUI): needs \`textual\` installed + interactive terminal for smoke-test. Plan: .squidsquad/skill/planning/TUI-12801-DECOMPOSITION.md. Fix installer-files header count (206→).
3. **#12895** awaiting operator deploy-model decision (then implement chosen approach, folds #12519).
- Recurring meta-risk: this clone chronically boots behind origin (#12526) → #12895 stale-recompose. Verify \`git pull\` synced BEFORE any compose/commit each session.

## SESSION OUTCOME (2026-06-19 ~09:40–11:02) — actionable queue drained
- **#12800** (human as non-agent role, 8 ACs, HIGH-blast-radius) → **SHIPPED pending-test, PR #12902.** All gates green (static 4621, integration 53, targeted 101), DS NO_FINDINGS. Composed deployed to main.
- **#12895** (HIGH bug — stale-source recompose reverts shipped composed CLAUDE.md fleet-wide) → RCA done + fix options (A untrack composed [recommended, root, folds #12519] / B pull-before-deploy guard / C interim: cycle_post excludes composed from auto-commit). Routed **pending-human-review** (operator decides deploy-model approach — A reverses eager-deploy/tracked-composed model + touches installer = operator-owned). Then implement chosen approach.
- **#12519** (LOW) → folded into #12895 (same family); will close with that fix.
- **#12801** (Harness TUI) → claimed, decomposed (4 Stories, artifact). S1.1 (harness /status `lag` backend) + S1.2 (references/tui/harness_client.py data layer) committed + green. **S1.3+ (Textual app, panels, action bar, wake) NEEDS `textual` installed + interactive terminal for the mandatory skill-domain smoke-test — fresh/equipped context.** NIT: installer-files.txt header "Total: 206" → 208 (fix on next branch commit).
- **#10855** blocked on #12820 (pending-test); **#12493** blocked on PM §8.3 arch backstop; **#12450** S3/S4 PM-gated; **#12820/#12853** shipped pending-test/merged earlier.

## NEXT (fresh context)
1. #12895: implement operator-chosen deploy-model fix (likely A: untrack composed + .claude/settings.json, regenerate on boot/deploy, installer generates; or C interim first). Folds #12519. DS-review (high-blast-radius). Then back in-progress→pending-test.
2. #12801: continue S1.3 (Textual app skeleton) once textual provisioned — per .squidsquad/skill/planning/TUI-12801-DECOMPOSITION.md. Fix installer-files header count.

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
