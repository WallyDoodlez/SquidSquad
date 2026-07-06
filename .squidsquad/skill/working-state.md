# Working State

- **#13335 SHIPPED -> pending-test (PR #13346)** — HIGH, operator-filed. Context-threshold was unenforced in event mode (no actor: event-mode agents skip cycle_post.py; harness read pressure only reactively; event-mode-contract L119 claimed non-existent logic). Fix: harness 5s health poller `_enforce_context_pressure()` flips intent=restarting at/over threshold, reusing existing graceful-restart machinery (checkpoint + 60s force-kill net + auto-reboot -> fresh context). +20 tests, CQ 13335_spec, docs (L119 rewritten AC5-clean + context-pressure.md note). Static 5225/0/0. Sonnet review -> SHIP. Filed #13345 (pre-existing /health display-path bug, clone agents, low). Verifier verifying.

- **Task**: none in-flight. **#13318 SHIPPED ✅** (PR #13320 merged by verifier dfbcb2300→ DM delivered → status:shipped, 2026-06-28 ~20:23). Launcher consolidation done end-to-end: repo root has NO launchers; the two surviving live at `.squidsquad/start.{sh,ps1}` (confirmed on local main). AC7 rejection (FAIL on first submit — I'd wholesale-deferred ALL doc repoints; AC7 requires "repoint mechanical command refs in-task AND flag narrative via TRACKED transition") was fixed in commit 24b08336c: repointed README:86 / INSTALLER-ARCH §10.3+§Refs+Phase-9 / HARNESS-ARCH §2, filed **#13322** (role:pm, low) for the narrative sweep. Verifier passed on re-verify + merged.
- **LESSON**: AC7's "repoint OR flag" lane-split = BOTH per reference — mechanical command refs repointed in-task, narrative gets a TRACKED transition (not a bare comment). Wholesale-deferring the doc surface is exactly the QA-reject gap (echoes [[feedback_no_deferred_wiring]]).
- **Recurring no-op restart-required (declined each time, correct) → tracked as #13334**: skill has received 3 no-op `assigned-to(restart-required, reason=l4-recompose)` wakes (2026-06-28, 07-03, 07-06). Each verified harmless from facts (deployed `.squidsquad/skill/CLAUDE.md` byte-identical to HEAD; newest composed-source commit still b65f61589 / #13318, no new recompose) and DECLINED per #13303 discipline. ROOT: live harness is ~198h stale on sha `d349b30f` (session-start commit), which PREDATES #13303's suppression gate (c3046ae52) — so the watcher still emits no-op restart-requireds the merged gate would suppress. Remedy = harness restart (team-level, no outage) → **filed #13334 (role:pm, low)** to refresh when convenient (also activates other post-d349b30f fixes). Do NOT re-file on future occurrences; just decline + ack (already tracked). #13303 fix is correct, not a regression.

## #13318 PLAN (respawn-resilient checkpoint)
**Contract**: issue body + operator location-refinement comment (AUTHORITATIVE): the 2 surviving scripts live at `.squidsquad/start.{ps1,sh}` (repo root ends with NO launchers); script resolves repo-root via parent-of-parent dir / git rev-parse, cd's there. No CONTEXT-13318.md.
**Design (PM recs, non-blocking)**: Q1 drop start.bat (doc `pwsh .squidsquad/start.ps1`). Q2 quit-TUI leaves fleet running → harness+supervisor BACKGROUND/detached, TUI FOREGROUND; re-run = singleton /status probe → attach TUI, no double-start. Q3 `--bare`/`--no-setup` = skip deps+sync, harness-only (no TUI), foreground supervised loop (#12527 smoke path).

**DELETE**: start.bat, start-harness.sh, start-harness.bat, restart-harness.sh, restart-harness.bat. **MOVE**: start.ps1→.squidsquad/start.ps1, start.sh→.squidsquad/start.sh.

**Behaviors to FOLD (from research)**:
- Deps (start.*): python(3) check (unix auto-installs via apt/brew; win prints URL+exit1); pip check; 5-pkg import probe `fastapi,uvicorn,starlette,watchdog,yaml` → `pip[3] install -r requirements.txt`. start.sh also warns if `claude` CLI missing.
- Clone sync (start.*): `git checkout main && git pull --no-rebase` on primary + each clone in `.squidsquad/.local-config` (skip `.` paths; soft-warn errors).
- Supervised loop (restart-harness.*, #12825 NON-NEGOTIABLE): while-loop; exit 0→clean stop; exit $RESTART_CODE(42)→relaunch+reset crash_count; SIGINT/SIGTERM→stop (unix trap); else crash: if run≥CRASH_WINDOW(60s) reset count first, then count++; at CRASH_THRESHOLD(3)→exit1 (ref .squidsquad/harness-errors.log); sleep 1 between. Env overrides: SQUIDSQUAD_HARNESS_RESTART_CODE/CRASH_THRESHOLD/CRASH_WINDOW/HARNESS_CMD. Win uses `python -c time.time()` for window, `timeout /t 1`.
- Bare (start-harness.*, #12525): no deps/sync, straight to harness.
- Harness launch cmd: `python[3] references/scripts/harness.py` (relative to repo root, so cd first). NO port arg. NO singleton guard today. NO TUI launch today (TUI = references/tui/app.py).
- Repo-root: ALL current scripts assume script is AT root (cd $dirname/$PSScriptRoot). New scripts in .squidsquad/ → must go UP one level (`dirname $0/..` / `Split-Path -Parent (Split-Path -Parent ...)`).

**CONSUMERS to repoint (AC7)** — BLOCKERS first:
- `references/installer-files.txt` L10-15: start.sh/ps1→.squidsquad/ paths; REMOVE the 4 deleted lines.
- `references/scripts/squidsquad_cli.py` L46-47/324/334-339: RESTART_WRAPPER_BAT/SH point at restart-harness.* → rewire to `.squidsquad/start.{ps1,sh}` as the supervised launcher (POST /restart self-heal depends on this — BLOCKER).
- Tests (retarget, BLOCKER): tests/test_12525_bare_harness_launcher.py (start-harness gone→bare flag on new script), tests/test_12526_launcher_no_rebase.py (paths→.squidsquad/), tests/test_12825_harness_restart.py (restart-harness gone→supervised loop in new script).
- `packages/cli/index.js` L359 git-add line → .squidsquad/ paths.
- `references/scripts/wizard.py` L1189/1193 cold_start_cmd `./start.sh`→`.squidsquad/start.sh`; `references/wizard/WIZARD.md` L900/925/926.
- `tests/comprehension/12420_spec.json` if cold_start_cmd changes.
- MECHANICAL doc refs I update: `references/sub-skills/common/harness-restart.md` L20/41, `references/scripts/harness.py` L74 comment.
- NARRATIVE (flag to PM/DM, not me): README.md L86, docs/HARNESS-ARCH.md, docs/INSTALLER-ARCH.md, docs/prd/compose-freshness.md prose.

**KEY DESIGN RESOLUTION (#11511 collision)**: launcher code at .squidsquad/ collided with `_is_state_file` (strips ALL .squidsquad/ from feature branches). RESOLVED in-lane/in-pattern: added `_is_launcher_script()` carve-out in git_ops.py `_is_state_file` (exempts ONLY `.squidsquad/start.sh`+`.squidsquad/start.ps1` — narrow allow-list, same spirit as `_is_plan_body` #12750). Now commit_code stages them as code, guard hook doesn't strip, auto-resolve leaves conflicts unresolved (correct for code). Verified classifier. NOT escalated — operator's location directive made workable, not overridden. (statusline.sh etc. = source at references/ + installer-copied deploy; launchers are runnable-in-place code per operator, so carve-out not source/deployed split.)

**Commit plan**: (1) ✅DONE commit 43021c8a2: new .squidsquad/start.{sh,ps1} + delete 7 root + git_ops carve-out. (2) ✅DONE commit c03c0f506: runtime consumers (squidsquad_cli RESTART_WRAPPER_PS1/SH→.squidsquad/start.* --bare + _harness_launch_tail; installer-files start.*→.squidsquad/ + dropped 4; packages/cli git-add; wizard cold_start_cmd). Both PUSHED. PR diff clean (only #13318 files). (3) TODO tests retarget: test_12526_launcher_no_rebase (path→.squidsquad/, EASY), test_12525_bare_harness_launcher (start-harness gone→assert --bare flag on new script), test_12825_harness_restart (restart-harness gone→supervised loop in new .squidsquad/start.sh via SQUIDSQUAD_HARNESS_CMD stub) + new AC3/4/5 coverage + git_ops _is_launcher_script carve-out test + FIX installer-files.txt "Total: 258"→254 comment. (4) TODO mechanical doc/sub-skill refs: harness-restart.md L20/L41 (CQ-assess), harness.py L74 comment. Then full static gate, DS/Sonnet review, PR, pending-test. Update #12527 body ref to `.squidsquad/start.sh --bare` (or note in PR).
**NOTE**: full static gate currently RED (test_12525/12526/12825 ref deleted scripts) until commit 3 lands — do NOT transition pending-test before gate green.
**Smoke-verified**: bare supervised loop exit-0 (clean stop) + exit-42→relaunch→exit-0 both correct.

## EARLIER THIS SESSION
- #13303 SHIPPED (l4-watcher no-op restart-required gate). #13316/#13317 scan findings await operator triage. Booted 2026-06-28 ~03:10 (event mode). work_queue() approved = #12527/#10690/#10686, all 3 operator-gated. Open issues: #13263 pending-human-review, #302 pending-approval — not actionable. Idle.

## THIS SESSION (2026-06-28, event mode, Verbose ON)
- **#13303 FILED + SHIPPED → pending-test (PR #13314).** Discovered live: received `assigned-to(restart-required, reason=l4-recompose)` at 04:10 while idle, but composed CLAUDE.md was byte-identical to HEAD (git diff empty) and no L4 commit had occurred → no-op recompose. Root cause: `l4_file_watcher.recompose_for_role_class` emitted restart-required on every compose-success with no before/after output comparison; a benign FS touch (freshen-pull mtime rewrite / teammate-merge propagation) drives a no-op recompose → spurious agent restart. **Declined the no-op restart** (correct — nothing to pick up). Fix: content-change gate (read_deployed pre/post compose; emit only on real change; noop result skipped by emit_results; fail-safe-to-emit on reader error; gate-off when no reader = legacy). start_watcher + recompose_path default real reader (prod gate ON, harness unchanged). +10 tests. Sonnet review: NO BLOCKERS (1 minor+1 nit fixed). Static 5193/0/0.

## THIS SESSION (2026-06-27, operator inline "go ahead")

- **#13279 SHIPPED -> pending-test (PR #13299).** Last unguarded `subprocess.run` in git_ops.py: added `timeout=_git_timeout()` to `_log_diagnostic` (fire-and-forget, except-wrapped; TimeoutExpired already swallowed -> only behavior change is bounding the wait; some callers run under #13211 `_ENSURE_MAIN_LOCK`). +3 regression tests. Static 5171/0/0. Completes #13262 timeout-hardening. Picked up under operator inline "go ahead" (team idle) as the triage green-light for this own-scan finding. Low blast radius -> no DS-review.

- **#13291 UN-HELD + POST-MERGE RECOMPOSE landed (direct-to-main).** Operator LIFTED the HOLD (pm 18:37: "every agent commits to the shared git repo, so be-current-before-integrate is L1-universal; placement correct; QA proceed"). qa re-applied the exact reviewed source diff (un-revert of a4eb27c10 -> "Reapply ...") + re-verified -> pending-ship (2004b677b). **Source was re-landed source-only**, so composed `.squidsquad/<role>/CLAUDE.md` were stale (the exact drift I flagged during the HOLD). I recomposed all 4 roles (dm/pm/qa/skill) -> diff is exactly the new L1 "stay-current" wording (8 files, 0 unexpected lines), static 5168/0/0, committed direct-to-main. The deployed agent instructions now match the re-landed L1 source.

- **#13278 SHIPPED -> pending-test (PR #13300).** ROOT CAUSE was NOT what the issue assumed (DeepSeek broken/external). Live probe proved DeepSeek code-review works: a clean review returns the template's sanctioned sentinel `NO_FINDINGS` (11 chars), which route()'s uniform MIN_OUTPUT_LENGTH=200 gate misclassified as degenerate -> exit 1 -> needless fallback on EVERY clean review. Fix: CLEAN_RESULT_SENTINELS bypasses the length gate (exit 0, sentinel written); genuine degenerate output still returns 1. Sonnet DS-review (0 blockers): +None fail-closed guard, gate-fail len() guarded, "success-sentinel" audit action, case-robust match. +6 tests. Static 5179/0/0. **DeepSeek code-review is functional again now that clean reviews aren't discarded** -- the standing "model_router degenerate -> go straight to Sonnet" reminder can be relaxed once this verifies+merges (pending-test).

## AWAITING OPERATOR TRIAGE (scan findings — fix only on green-light)
- **#13323** (qa-lead-filed scan finding, role:skill, improvement-scan, low): wizard.py L1176-1177 + L3252 docstrings still say `./start.sh` — stale prose after #13318 path migration (functional cold_start_cmd at L1189/L1193 is correctly `.squidsquad/start.sh`). Cosmetic/maintainability only, NO functional impact. Verifier explicitly classed it improvement-scan + "Not a #13318 reblock". Deferred to triage, uniform with #13316/#13317 (3 open skill scan findings now). Trivial 2-line fix when greenlit.
- **#13317** (pm-filed scan finding, role:skill, improvement-scan, low): 2 sub-skills (`roles/pm/health-check.md` L18, `common/agent-lifecycle.md` L16) still call PID the "sole liveness signal" — contradicts shipped+live #12492 progress-liveness cutover. Real, in-lane, low-risk text fix (PID=teardown-only; progress-liveness=authoritative). Acked, NOT auto-picked (scan findings need operator green-light per #13279 precedent). Also sweep boot-remote-agents/context-pressure for sibling occurrences when greenlit.
- **#13316** (my scan finding, low): idle-loop --drained contract starves scans on gated-only work_queue. Awaiting triage.

## CARRY-FORWARD (other lanes)

- **#13291** SHIPPED 2026-06-28 03:10 (DM). Composed deploy was mine; lane closed.
- **#13285** (post-merge scope-audit) VERIFIED -> pending-ship (PR #13288 merged). Flag to operator: flip `SQUIDSQUAD_MERGE_AUTO_REVERT=1` once detection trusted in prod.
- **#13286** (dev forge-workflow) VERIFIED + MERGED -> CLOSED (PR #13290).
- **#13287** (dev-domain sub-layer) — PM design queue, not mine.

## NOT CLEANLY AUTONOMOUS

- **#13278** (open, mine, scan): model_router code-review degenerate -> DS-review silently falls back to Sonnet. Root cause external (model/route); the "silently" half may be fixable (loud fallback) — assess next.
- **#12527** greenfield FOREIGN-repo installer smoke (LIVE run human-supervised; static audit done).
- **#10690** wiki-link rework, gated on E6+E7.
- **#10686** PRD-E E7 manual on-repo migration smoke.

## STANDING REMINDERS

- Feature work on `squidsquad/task/<n>`; working-state + composed CLAUDE.md commit DIRECT to main (#11511 strips them from feature branches). `git switch -c` BEFORE code edits — esp. on idle->pickup (no task-begin fires).
- Push: `git -c credential.helper='!gh auth git-credential' push`.
- Pending-test gate = `python tests/run_tests.py static` (~5168 gated, fail-closed). Known-failures test_agent_boundaries + test_compose_author_comments_11142 (#10360-blocked) -> gate still exits 0.
- model_router/DeepSeek degenerate this session (#13278) -> Sonnet review subagent.
- **L1/L4 source revert/reapply != composed revert/redeploy**: after any revert OR reapply of a DEPLOYED instruction-layer change, recompose every affected role or composed output silently lags the source. (Posted as a process note on #13291 for the cluster design.)

## Improvement Scan
Status: re-armed after #13303 (reidle → scan_count=0, fresh burst; cool-down throttle preserved). Session cron **4ac1b96f** (4,34 * * * *) created this re-idle. Prior stretch filed #13278+#13279; this session filed+shipped #13303.

## Quiet Cycle Counter: 0
