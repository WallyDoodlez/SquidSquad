# Working State

> **L4-recompose restart-required was a NO-OP (2026-06-14):** Harness emitted `restart-required` (reason l4-recompose, target_alias=dm). Acked it (loop-safe). Attempted cooperative /quit — but **/quit is a no-op in this session** (Monitor kept delivering nudges; session did not terminate). Then verified: my `.squidsquad/dm/CLAUDE.md` is byte-identical (last commit f8d867a9d 2026-06-12, working tree clean) → the recompose changed nothing to pick up. So NOT restarting was correct; /quit no-op was harmless. **Finding for PM/skill:** l4_file_watcher.py emits restart-required on compose *success* regardless of whether composed output actually changed (l4_file_watcher.py:149-156) — should diff CLAUDE.md before requesting a restart, else no-op L4 writes churn restarts. Also: this event-mode session cannot self-terminate via /quit; rely on harness/operator restart or context-pressure exit-42.

- **Task**: none
- **Status**: idle

## >>> FLAG @PM — .claude/settings.json merge friction (volatile-shared-file class) <<<
- 2026-06-16: a pull aborted because `.claude/settings.json` was locally dirty (compose regenerates its activity/pause hooks block per-clone), and a stash-pop hit a UU conflict because origin also changed it. Resolved by resetting to HEAD (committed version is generic — hooks use ${CLAUDE_PROJECT_DIR}/${SQUIDSQUAD_ROLE}, serves all clones per #12418/#12443).
- **This is [[feedback_merge_spiral_volatile_file]]**: a tracked file that compose rewrites per-clone will keep blocking pulls. Structural fix = untrack + gitignore .claude/settings.json (compose regenerates it on deploy). NOT a DM-domain decision + the file may be intentionally committed (the #12418 'one committed settings.json serves all clones' design) → flag @pm/skill, don't unilaterally untrack.
- Workaround until fixed: on a blocked pull, `git checkout -- .claude/settings.json` (or reset to HEAD) before pulling — the committed version is authoritative; local compose hooks regenerate on next deploy.

## >>> PENDING TEAM REBOOT (#12473 comms rule) <<<
- #12473 (L1 plain-language comms rule) SHIPPED + composed into all 4 CLAUDE.md (commit cf5a48666). **Reboots DEFERRED per operator (2026-06-15)** — auto-reboot off during firefight; agents run stale CLAUDE.md until next natural restart, then pick up the rule. Harness compose-after-merge auto-reboot did NOT fire (no intents flipped). When operator/PM green-light a team reboot, restart pm/dm/qa/skill via `squidsquad_cli.py restart <role>` (reboot_agent.py deprecated). Note: my own /quit doesn't work this session → my reboot = harness force-kill+respawn.
- **Quiet Cycle Counter**: 3 (doc-scan GATED — see below)

## Improvement Scan
Status: **GATED** — doc-improvement-loop issue-gate trips on open #10540 (status:open, role:dm). Per gate + [[feedback_bug_gate_interpretation]] (open/in-progress block; pending do not), skip scan until #10540 resolved/routed. #10540 is NOT DM-actionable (no open→in-progress authority) → parked on PM routing; scan stays gated meanwhile.
Last completed: R73 (cycle 1715, 2026-05-31) — 0 findings, full 7-file rotation. rotation_count=74.
Next scan after: #10540 routed/closed (then quiet-gate resumes).

## Session Context (EVENT-mode, boot @ 2026-06-14)
- **Wake mode: EVENT** — boot probe succeeded on :7373 (port file = 7373, NOT the old 59999 pin). Prior session's PM port-pin (forced LOOP via dead :59999) is GONE this session. Mode is sticky — do NOT re-probe mid-session, do NOT self-heal .harness-port.
- Booted cleanly: drained 5 boot events, queried forge, armed Monitor — i.e. NOT inert. #10855 (event-mode inert boot) either resolved or doesn't bite this manual-spawn path. Functional in event mode.
- Cursor advanced to `15399ccc39154b8f` (past all 5 boot-drain events; all terminal/no-op: #11745 already shipped, #87654 skill-lane, #11511 now shipped+closed).
- Version: **v0.44.0**; Shipped Since Last Bump: **17/10** (config.md authoritative — OVER threshold).

## SHIPPED THIS SESSION (2026-06-14)
- **#12282** (PR #12341, test-isolation leak fix; test-only tests/test_cycle_post.py; merge 3a37845). Verifier PASS + live E2E (zero /restart leaks). Transition-only ship (qa-side pre-merged). Counter 15→16.
- **#12244** (PR #12293, harness crash-loop backoff P0 restart-safe intent clock + P2 fast-death backoff; harness.py+test_harness.py; merge bb1af12). Verifier PASS ×2 after PM AC-amendment; PM cleared. Transition-only ship. Counter 16→17. Deferrals tracked: session-limit label→#12271; P3→#12294.
- **#12342** (PR #12364, EAD event-routing fix: status-routes pending-test→verifier / pending-ship→dm, (issue,status) dedup, removes broken _is_agent_update; harness.py+tracker.py+tests; merge 88ed271). Verifier PASS zero gaps + live registry check + DS back-transition regression. Transition-only ship. Counter 17→18. **Requires harness restart (operator) to take effect** — running harness still on old routing. No CLAUDE.md change → no agent reboots.
- **#12380** (PR #12391, compose .local-config alias-keying fix: keys by alias qa not role-class verifier → QA boots own clone; compose.py+wizard.py+tests; merge 1a2c0de). Verifier PASS (after cy141 regression route-back, fixed 4e39f0750, re-verified 281 passed). Transition-only ship. Counter 18→19. Effect on future composes/installs (existing .local-config may need recompose — operator concern). No reboots.
- **#12418** (PR #12441, #12271 slice-1 SessionEnd-reason hook: graceful-vs-crash signal for reboot decision; compose.py+harness.py+tests; merge fc13ec2). Verifier PASS 6 ACs. **First genuine DM-merge this session** (via harness /merge, squash) — qa held off, handed merge to DM. Citation soft-gate judged satisfied (verifier-side artifacts post-date PR; no PM CONTEXT; qa AC-walk documented). 'Fixes #12418' auto-closed issue → transitioned label to shipped. Counter 19→20. Post-merge l4-recompose no-op (CLAUDE.md unchanged). No reboot.
- All internal-reliability → CHANGELOG batched to bump (added to held list below). No merge touched config.md (counter safe). No template/sub-skill change → no reboots.
- **#12442** (PR #12444, EAD handoff re-emit fix: re-emit assigned-to every 600s for unhandled pending-test/pending-ship until status changes, bypassing updatedAt filter — closes single-emit starvation that stalled #12418 48min; harness.py+tests; merge 80c96fb). Verifier PASS 6 ACs. DM-merged via harness /merge. Counter 20→21. Post-merge recompose no-op. No reboot.
- **#12443** (PR #12457, #12271 slice-2 activity-heartbeat: async PostToolUse/PostToolUseFailure command hooks + cycle_post heartbeat → harness last_activity_at, observational only; activity_hook.py+compose.py+cycle_post.py+harness.py+tests+installer-files; merge e1ccb99). Verifier PASS 6 ACs. DM-merged. PR used 'Implements' → no auto-close (clean ship). Counter 21→22. No reboot.
- **AUTO-ROUTE likely LIVE:** #12442 + #12443 pickups were harness-emitted (role:harness), NOT PM-manual (role:pm) like the first 4. Consistent with #12342/#12442 EAD auto-route + re-emit now running (harness must have been restarted onto the fixed code). Not 100%-confirmable agent-side; flagged @pm/operator to verify via harness event log. If confirmed, pending-ship→dm delivery is autonomous (closes #12442 loop).
- **Harness /merge works in event mode** (this session): POST /merge {pr_number,branch,role:dm} → 202 accepted → pr-merged event success:true. Canonical DM merge path per delivery-packaging. Used for #12418 + #12442.

- **#12458** (PR #12459, #12271 slice-3 pause-aware liveness guard: silence=death only when no hook explains it; ceiling-bounded pauses + clock-skew guard; genuine death still reboots; compose.py+harness.py+tests; merge 4b9dc42). Verifier PASS 6 ACs (377 passed). DM-merged, 'Implements' no auto-close. Counter 22→23. No reboot. (slice d = retire PID-poll, still upcoming.)

- **#11613** (PR #12471, installer dependency auto-provisioning per INSTALLER-ARCH §4.1: gather-all→present→ONE consent→provision→re-verify, never fail-fast; wizard.py+WIZARD.md+requirements.txt+start scripts; merge 887d681). Verifier PASS (ACs+§4.1+comprehension 6/6, 398 green). DM-merged. Counter 23→24. **USER-FACING** — updated README (install section: one-step dep auto-provisioning; fixed stale `pip install fastapi uvicorn`→`-r requirements.txt`). Real user-value CHANGELOG entry prepared (in #11613 comment), batched to bump.

## >>> INSTALLER CLUSTER (operator's bump-gate dependency) <<<
- Operator HELD bump 2026-06-15 for "land better installer". Installer cluster = 3 items (PM-approved 2026-06-15):
  - **#11613** dep-provisioning ✅ SHIPPED (this session)
  - **#12419** migration-walk ✅ SHIPPED (PR #12533, merge 21bc16a, counter →28) — operator-facing, CHANGELOG prepared
  - **#12420** post-commit-restart — LAST ONE; skill building next (per #12419 note). When it ships → installer cluster COMPLETE.
- When #12420 ships → flag operator that installer cluster is complete + ask for bump green-light. Do NOT auto-bump.

- **#12473** (PR #12474, L1 plain-language user-comms rule in SOUL.md+instructions.md; merge 7bf840f). Verifier PASS 6 ACs. DM-merged. Counter 24→25. Recomposed all 4 CLAUDE.md (cf5a48666); reboots deferred per operator.

- **#12475** (PR #12486, tracker.py --force bypasses legality matrix; ship-integrity gates preserved; tracker.py+tests; merge 97b7df5). Verifier PASS 5 ACs. DM-merged. Counter 25→26. Script-only, no reboot.

- **#12460** (PR #12472, #12271 slice-4 SHADOW: progress_liveness() alongside PID, logs divergence, reboot decision UNCHANGED; harness.py+tests; merge d36fef3). Verifier PASS shadow scope. DM-merged. Counter 26→27. Script-only, no reboot. **Unblocks #12492** (actual PID→progress cutover, role:skill HIGH). #12271 NOT complete until #12492 ships.

- **#12419** (PR #12533, installer migration-walk §10: version-stamp detect → in-range ordered migration steps → 3-gate safety walk; Upgrade/Full-rebuild/Abort; wizard.py+WIZARD.md+VERSION+migrations/README+tests; merge 21bc16a). Verifier PASS 6 ACs + CQ. DM-merged. Counter 27→28. OPERATOR-FACING, CHANGELOG prepared. No reboot. references/VERSION=0.44.0 (bump still DM's job).

- **#12509** (PR #12517, test-only basename-shadow fix: `tests/integration/harness.py`→`integration_harness.py` to drop the `harness` basename collision with `references/scripts/harness.py` that broke bare `pytest tests/` collection; +3 importers + regression guard; merge 43e46b5e via harness /merge, squash). qa PASS 5 ACs cy289 (3-cycle contamination saga resolved by dropping the in-process import-resolution test fn; 2 pure-filesystem guards remain). DM-merged. Issue NOT auto-closed (no closing keyword) → manual transition to shipped. Counter 28→29. Test-only, config.md untouched, no production code → no reboot. Citation soft-gate judged satisfied (#12418 precedent: verifier-side artifacts post-date PR, no PM CONTEXT, qa AC-walk documented). CHANGELOG (dev-facing, batched to bump): "bare `pytest tests/` now collects+passes out of the box (was: collection interrupted by duplicate `harness` module basename)."

- **#12574** (PR #12643, HIGH critical freeze-fix: `POST /events` unknown-role drop returned `JSONResponse(204, content={})` — 2-byte body on a 204 → h11 LocalProtocolError → poisoned keep-alive → ~6h squad freeze 2026-06-17. Fixed to bodyless `Response(status_code=204)`; harness.py +10 lines + AST regression guard; merge d796c6d5 via harness /merge, squash). qa PASS cy290, DS 12574-c1 confirmed RCA+fix. `Resolves #12574` auto-closed issue → transitioned label to shipped. Counter 29→30. **⚠️ running harness still buggy until operator restart** (prod runtime path, like #12342); no CLAUDE.md change → no agent reboots. Non-blocking: AST guard misses positional `JSONResponse({}, 204)` form (qa optional fast-follow). CHANGELOG (batched): "fixed harness bug where an unknown-agent event drop could poison the connection and silently stop event delivery squad-wide (root cause of the ~6h 2026-06-17 freeze)."

- **#12525** (PR #12617, HIGH bare-harness launcher: start-harness.sh `exec python3 harness.py` + start-harness.bat `python harness.py %* + pause` (visible window), no clone-sync/no deps; + installer-files.txt count 197→200→202 corrected; merge 840ae9f3 via harness /merge). qa PASS 5 ACs cy290, DS 12525-c1 re-clean. `Resolves #12525` auto-closed → label→shipped. Counter 30→31. New install scripts, no template → no reboot. **README updated (DM lane)**: secondary note in Quick Start→Launch documenting the bare-harness launchers as debug/hands-on option (primary flow stays squidsquad_cli.py start). **INSTALLER-ARCH TRD one-liner left to PM** (architecture-doc lane). CHANGELOG (batched): "New: `start-harness.sh`/`.bat` to launch just the harness (visible, no clone-sync/no deps) for debugging or hands-on setup."

- **#12720** (PR #12736, HIGH gate-integrity: `pytest tests/` false-green masker — the `/shutdown` test's daemon thread fired the REAL `os._exit(0)` ~1s late, hard-killing pytest at ~58% (exit 0, no summary) and masking ~40% unrun + real failures. Fix: join the daemon inside the os._exit patch window + conftest.py session thread-leak guard; merge e92dfd65 via harness /merge). qa PASS cy305 all ACs, DS-c1 F4/F5 folded. PR-title `fix #12720` auto-closed issue → label→shipped. Counter 31→32. Code/test-only, no CQ/no reboot. Defect-B test_vault fix confirmed on main (fe8c7a31f). **Suite now reports honestly** (94 now-visible failures ALL pre-existing/tracked — 39 test_agent_boundaries on open #10360, ~53 env-gated live tests — NOT #12720-caused). **Filed #12747** (skill, low): live-test clean-skip hygiene (qa note#2). CHANGELOG (batched): "Fixed a bug where the test suite could silently stop ~58% through and still report success; test runs are now honest end-to-end."

## >>> BUMP GATE OPEN (32/10) — HOLDING FOR PM/OPERATOR GREEN-LIGHT <<<
- **Operator directive 2026-06-15 05:19 UTC: HOLD the bump — "trying to land better installer."** Bundle the installer improvements into v0.45.0; do not bump until operator green-lights post-installer. Keep shipping; counter accrues.
- Counter **32/10**, well over Ship Threshold. **DO NOT auto-fire** ([[feedback_bump_requires_pm_signal]]). Flagged operator @ prior cycles 415 & 416 — no green-light yet. Not re-flagging (avoid churn; operator is aware). Hold until explicit PM/operator signal.
- On green-light: bump minor v0.44.0→v0.45.0 (config.md + SKILL.md frontmatter + CHANGELOG.md), git tag, push, reset counter→0.
- **CHANGELOG held (operator/internal-reliability framing; bump-window items are internal harness/test reliability, NOT end-user-facing):** harness restart reliability (#11538), test-suite reliability (#11503 21/23, #11657), dep-provisioning design contract (#11537), stale-lock startup-crash fix (#11641), liveness-aware port discovery (#11723), Windows ConnectionReset fix (#11587), unregistered-clone spawn-refusal (#11640), self-closing agent terminals (#11745), real-conflict PR-flap detection (#11511), WIP-preservation across reboots (#12142), harness crash-loop backoff (#12244), test-isolation /restart-leak fix (#12282), EAD event-routing fix (#12342), compose .local-config alias-keying fix (#12380), SessionEnd-reason hook #12271-slice1 (#12418), EAD handoff re-emit fix (#12442), activity-heartbeat hooks #12271-slice2 (#12443), pause-aware liveness guard #12271-slice3 (#12458), installer dep auto-provisioning #11613 (USER-FACING), L1 plain-language comms rule #12473, tracker.py --force-bypass #12475, #12271-slice4-shadow #12460, installer migration-walk #12419 (OPERATOR-FACING), bare-`pytest tests/` collection fix #12509 (dev-facing test-suite reliability), harness h11-freeze fix #12574 (HIGH — bodyless-204 on unknown-role event drop; root cause of 2026-06-17 ~6h freeze), bare-harness launchers #12525 (HIGH — start-harness.sh/.bat, README-documented, USER/OPERATOR-FACING), pytest false-green gate-integrity fix #12720 (HIGH — daemon os._exit masker; suite now honest end-to-end).

## Queue state (boot @ 2026-06-14)
- **pending-ship: 0 open** — `list-tasks dm --status pending-ship` returns ~30 results but ALL are CLOSED issues carrying stale `status:pending-ship` labels (verified get-state on #605/#9965/#11511 = CLOSED). The `--status` filter does NOT exclude closed; the no-filter `list-tasks dm` (open-only) returns 17, all status:pending. So real DM delivery queue = EMPTY.
- 17 open DM-relevant tasks all status:pending (await PM approval — not DM-actionable).
- 1 open DM-owned issue: #10540 (local-merge fallback; awaiting PM routing).

## Watch / carried
- **qa-side merges bypassing DM gate** (observed prior session on #12142/#12244): skips DM counter-reconcile, citation gate, CHANGELOG capture. On any transition-only ship, ALWAYS `git show <mergeCommit> --stat` for config.md before trusting the counter. Raise with PM once P0 firefight settles (may be intentional mid-emergency).
- **#10540 OPEN** (DM-domain: local-merge fallback; awaiting PM routing to encode degraded-mode in delivery-packaging.md). DM cannot self-pickup (open→in-progress needs worker authority).
- **#11723 Parts 1 & 3** — flagged @pm to file follow-ups (boot_remote env-honor + test-fixture isolation; boot-bootstrap CQ).
- #11503/#11657 final-2 tests gate on OPEN #10360 (status:pending, role:pm).
- pending DM-tracker approvals #8702/#7447/#9933 (awaiting PM).
- `.squidsquad/config.md merge=ours` gap — flagged @pm prior session (config.md not in .gitattributes merge=ours → counter-regression risk on merges).

## Next-cycle notes
- Event mode: react to NUDGE → GET /events/for/dm?since=<cursor> → forge-read → act → ack-cursor per event.
- On a pending-ship NUDGE: run pr-merge-wait readiness check (CI/review/mergeable), then ship per delivery-packaging.
- Doc-scan stays gated until #10540 moves.
- Primary deferred action: ship bump v0.45.0 ON operator green-light only (counter 15/10).
