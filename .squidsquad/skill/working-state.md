# Working State

- **Task**: idle — #12750 plan-in-PR SHIPPED to pending-test (PR #12751 ready, DS-c1 5/5 folded). THIS session also: #12420 → pending-test (PR #12596).
- **Status**: #12420 → pending-test (PR #12596, merged main, run_tests green, both PM items cleared). #12750 built on its own plan-seeded branch (dogfood). #12509/#12574/#12525/#12720 SHIPPED earlier. #12493 still held on PM §8.3 backstop; #10855 operator-DEFERRED (superseded #12271/#12460). Approved queue: #12749 (DM-ARCH, branch squidsquad/dm-arch ready), #12585 (L1 Soul), #12527/#12450 (premature/blocked until #12420 merges).

## >>> #12750 — plan-in-PR (PR #12751) — BUILT, awaiting DS-c1 <<<
**Adopted** existing plan-seeded branch squidsquad/task/12750 (PM's plan = commit 1, draft PR #12751). Dogfood: PR now carries plan + code together.
**SCOPE FINDING (folded in):** #11511 state-guard (`guard_staged_state`) strips ALL `.squidsquad/` from feature branches → defeats plan-in-PR. Verified empirically. FIX: `git_ops._is_plan_body()` narrow allowlist exempting `.squidsquad/<role>/planning/<n>-body.md` (only plan bodies; working-state/iterations/vault still stripped → no #11511 merge-spiral regression). commit_code/commit_state/_auto_resolve untouched (guard-only change).
**Delivery:** PR (code) = git_ops.py guard + task-intake.md Phase3B (plan-in-PR) + task-pickup.md (adopt branch) + test_12750 (19 tests). MAIN (state) = worker.md L4 Branch+PR bullet + recompose. ACs: 1✓(task-intake runtime sub-skill) 2✓(task-pickup+worker.md L4) 3✓pending-merge(plan+code co-located in PR#12751) 4✓grep-clean 5✓not-in-installer-files 6✓deploy-all green 7=verifier CQ spec.
**Code commit:** 08d8192d8 on branch. **NOTE for verifier:** plan-in-PR behavior lives in RUNTIME-loaded sub-skills (task-intake/task-pickup markers) — quiz must let the agent follow `→ run sub-skill` markers.
**LESSON:** `git reset --hard HEAD~1` to clean a probe commit ALSO discarded uncommitted git_ops.py edits (tracked). Re-applied. Never reset --hard with uncommitted work; commit real work first or use --mixed.
- **RESTART-REQUIRED DEFERRED (10:21)**: l4-recompose fired restart-required, but composed skill CLAUDE.md mtime is 09:46 (≠ event time) → 10:21 recompose was a no-op → matches #12397 spurious-emit. Per operator's standing 'reboots deferred', NOT self-restarting. Composed CLAUDE.md DID change at 09:46 (uncommitted local recompose) so a reboot would sync instructions — operator's call. Surfaced to operator.
- **Updated**: 2026-06-17 09:40 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## >>> #12720 — `pytest tests/` FALSE GREEN — ROOT-CAUSED + FIXED (this session) <<<
**RCA (proven deterministically, not hypothesis):** masker = `tests/test_harness.py::TestEndpointsViaTestClient::test_post_shutdown_returns_202`. It POSTs `/shutdown` to the in-process `TestClient(app)`. The handler (`harness.py:3305 shutdown()`) spawns a **daemon thread named `shutdown`** (line 3396) that does `time.sleep(1)` then `os._exit(0)` (line 3394). The test's `patch("harness.os._exit")` reverts the instant the POST returns 202 — but the daemon thread calls the REAL `os._exit(0)` ~1s LATER → hard-kills the whole pytest process at **exit 0, no summary, pytest.main() never returns**. The 1s delay floats the death into whatever test runs ~1s on (≈58%, where test_harness.py sits) — explains "stays ~58% even ignoring test_l4_file_watcher_e3" (different file; death is timing-based). QA's "non-daemon thread" hypothesis was CLOSE but it's a DAEMON thread calling os._exit. This is ALSO the engine of #12408 (run_tests.py false-green) and the full-suite false-green.
**Proven:** temp repro (shutdown test + 2s sleeper) → process died at exit 0 mid-sleeper, no summary. After fix → sleeper completes, clean pass.
**FIX (2 files, code-only, NO CQ):**
1. `tests/test_harness.py` test_post_shutdown_returns_202: patch os._exit + time.sleep + HARNESS_PORT_FILE(→tmp nonexistent); JOIN the `shutdown` thread INSIDE the patch ctx so the mock fires; assert mock_exit.called_once_with(0) + thread not alive. Stops the masker + strengthens the assertion.
2. `tests/conftest.py` thread-leak guard (the "session guard" QA asked for): wrapper=True hooks (pytest_runtest_protocol baseline + pytest_runtest_teardown check). Fails LOUDLY if a test leaves alive a thread that's non-daemon (live server/observer) OR name in DANGEROUS={"shutdown"} (daemon os._exit caller). Allowlist={"test-event-stream-http"} (per-class e2e server). VALIDATED: catches both the daemon `shutdown` leak AND a plain non-daemon leak as ERRORs (loud), fixed test passes, no false-pos in broad run so far.
- harness.py:4162 os._exit(1) = Ctrl+C signal handler, NOT in-process test-reachable. /shutdown is the SOLE masker.
**DONE:** PR #12736 (commits 82a934ef8 fix + e8d9b3177 DS-fold), pending-test. run_tests.py static green 4462/15skip (reaches sessionfinish; was false-green ~58% trunc). DS-c1 caught F4 (assert-inside-patch → revert → real os._exit kills pytest) + F5 (teardown-raise skips leak check) — both folded. Vault frontmatter fix (test_vault) on MAIN. Defect B 39 test_agent_boundaries + test_compose_author_comments = KNOWN_FAILURES blocked #10360 (out of scope). **This also un-falses #12408** (same masker drove run_tests.py static false-green) — QA may want to re-verify/close #12408 on the back of this.

## >>> #12574 → pending-test (PR #12643) — HIGH harness freeze-fix <<<
RCA: POST /events unknown-role drop returned JSONResponse(204, content={}) — a 204 carrying a {} body → h11 LocalProtocolError 'Too much data for declared Content-Length' → poisons keep-alive conn → event-delivery GETs stall → ~6h squad freeze. Issue's multi-byte hypothesis WRONG (JSONResponse byte-sizes UTF-8 correctly; test pins it). Fix: bodyless Response(status_code=204). 3 tests (AST source guard authoritative — TestClient/httpx can't repro the h11 wire error; functional bodyless-204; UTF-8 byte-correct). DS 12574-c1 clean (1 dead-import→fixed). Code bug, no CQ.

## >>> IN-PROGRESS (claimed, RCA foothold laid — needs FRESH CONTEXT for the fix): #12720 — `pytest tests/` false green <<<
HIGH test-integrity bug (QA cy291, while verifying my units). Two defects:
- **A (masker, primary):** bare `pytest tests/` on main hard-terminates at ~58% — exit 0, NO summary, junitxml never written, `pytest.main()` never returns. NOT os._exit/sys.exit (QA's shim never fired → native/C-level exit or pre-patch ref or thread/server shutdown). Position/time-based (stays ~58% even with --ignore=test_l4_file_watcher_e3.py). Signature: a "live" test leaves a non-daemon thread / threading.Timer / uvicorn server / watchdog Observer alive that hard-exits the interpreter. **Candidate live-tests I narrowed:** test_11587_uvicorn_selector_loop, test_11723_port_discovery_liveness, test_12460_progress_liveness, tests/integration/test_event_mode_* , test_feat_9725_spawn_loop_registration_live, test_l4_file_watcher_e3 (_Debouncer Timer).
- **B (masked real failures):** test_agent_boundaries::test_ac4 L1 awareness assertion is STALE (string "Know each other's responsibilities" no longer in composed pm; grep -rl empty under references/) → update to current wording (this is already a run_tests.py KNOWN_FAILURE blocked on #10360 — reconcile). Plus a ~19% E/F cluster (module fixture cascade) + 3 F at ~45%. Full set blocked by A.
**Fix plan:** (1) RCA A — bisect to the live test, tear its thread/server down in teardown; add a session guard that FAILS if a non-daemon thread/live server survives a test (fix + regression, sibling to #11394 AC3 / #12408). (2) Triage B once summary prints. (3) CI invariant: `pytest tests/` MUST reach sessionfinish + exit reflects real outcomes.
**Why I personally witnessed it:** my own full `pytest tests/` runs this session showed exactly the 57%/exit-0/no-summary pattern; I misattributed it to a capture artifact — it's defect A.
**My shipped units stand** (QA confirmed): #12509/#12574/#12525 verdicts rest on collection + targeted + run_tests.py, NOT full-suite-green.

## Queued behind #12720: #12585 (L1 Soul 'Health & Diagnostics') — approved, role:skill
L1 SOUL change = high-blast-radius (all agents on reboot) + LLM-consumed → CQ-gated. Author on fresh main: L1 source edit + compose.py deploy-all + DS review + flag PM for CQ AC.

## >>> #12525 → pending-test (PR #12617) — bare-harness launchers <<<
start-harness.sh (exec python3 harness.py, foreground) + start-harness.bat (python harness.py + pause, visible window; runs python directly not via start.ps1). No clone-sync/dep-install. Added to installer-files.txt (count 197→202; header was stale 197 vs 200 actual). 16 tests; run_tests.py green; DS 12525-c1 1 warn (start.ps1 AC5 gap)→fixed→clean. Not LLM-consumed (no CQ). PM non-blocking: INSTALLER-ARCH/README one-liner is PM doc surface (file-headers satisfy AC4). AC1/AC2 visible-window = OS-level, flagged for live verify.

## >>> #12420 → BUILT + DS-clean (PR #12596) — HELD at in-progress on PM CQ AC <<<
INSTALLER-ARCH §10.3 post-commit harness restart. Done: `wizard.py restart-agents` (probe GET /status .harness-port default 7373 5s; reachable→POST /agents/<alias>/stop+start per config `## Aliases`, §4.1 routes, best-effort; unreachable→user-driven ./start.sh; HTTP in `_http_request` monkeypatch seam). WIZARD.md Step 7.5c added + 7.6 reworked + Step 0b.1 forward-ref synced (AC4). 21 tests (AC5 both paths + per-alias failure + edges); run_tests.py green; **DS 12420-c1 NO_FINDINGS**. ACs 1-5 satisfied as written.
- **HELD (not pending-test):** PM item 2 — WIZARD.md LLM-consumed → needs comprehension AC (cf #12419 AC-CQ) before pending-test; verifier authors CQ spec from it. @pm asked to add it; transition to pending-test the moment it lands.
- **PM item 1 (non-blocking doc-sync):** unreachable path built user-driven (honors Q-new21; matches AC1 'falls through to start.sh') vs §10.3's 'installer invokes start.sh' wording — PM to reconcile §10.3 + flip its 'not yet implemented' banner at ship. Chose stop+start over /restart (/restart leans on PID-death #12271 retires).
- Resume trigger: PM adds CQ AC → transition pending-test. Mirrors #12493 built-then-held.

## >>> #12509 → RE-SUBMITTED pending-test (PR #12517) — QA cy273 (3rd FAIL) fixed by DROPPING the fn <<<
Bug: tests/integration/harness.py shadowed references/scripts/harness.py → pytest tests/ collection abort. Fixed by rename (git mv → integration_harness.py) + 3 importers. Regression test went through 3 QA rejections, all on the 3rd fn `test_bare_harness_import_resolves_to_real_harness`:
- cy251: test popped+restored sys.modules['harness'] but still did live `import harness` (re-execute).
- cy270: assert via `importlib.util.find_spec` — helped (7→5 fail) but contamination persisted via collection-order interaction.
- cy273 (FINAL, commit bcf2e0ddd): per QA recommendation, DROPPED the fn entirely. The 2 structural guards (renamed-helper-present + no-test-dir-basename-shadow) lock the regression with zero import machinery. Repros pass (12509→feat_10681 13✓; trio 37✓); collect 4751/0 err; full pytest tests/ exit 0 (3 runs); run_tests.py OK. NOTE block left in test file recording why + subprocess escape hatch.

## Other in-flight (held on gates / others' lanes)
- **#12492** (cutover flip) — held on the #12460 shadow divergence window (now live on harness; PM/operator declares clean → wakes me).
- **#12493** (pipeline-sentinel) — built + DS-SHIP (PR #12494), held on PM's AGENT-RUNTIME §8.3 arch.
- **#12506** (improvement-subloop driver) — RCA done, routed to PM; §8.6 arch authored (PR #12518), my-lane impl scope front-loaded (config.md keys + idle-cooldown-loop step5 + boot driver), comes back on §8.6 merge.

## Installer cluster + new HIGH (queued, fresh context):
- #12450 (unit-test detection L3) — blocked behind #12420 (both touch WIZARD.md; no stacking → wait for #12420 merge).
- #12527 (HIGH — greenfield installer smoke on FOREIGN throwaway repo) — premature until installer cluster (#12420/#12450) merges; would capture a half-built installer.
- #12526 (bug — start.ps1/.sh clone-sync uses git pull --rebase → should be merge). **CROSS-DEP: when fixed, UPDATE test_12525 AC5 assertions** (test_start_sh_still_full / test_start_ps1_still_full assert `git pull --rebase` present — change to match new merge flag; [[feedback_update_stale_test_on_behavior_reversal]]).
- #12511 (test-isolation: force-transition tests emit #999 to live bus — careful event_bus.emit stub) | #12519 (tracked .claude/settings.json merge friction — option B .gitattributes merge=ours rec).
- #12511 (test-isolation: force-transition tests emit #999 to live bus — careful event_bus.emit stub) | #12519 (tracked .claude/settings.json merge friction — option B .gitattributes merge=ours rec).

## SHIPPED this session (all CLOSED)
#11613 (dep-provisioning), #12473 (L1 comms), #12475 (--force legality override), #12460-shadow (liveness divergence logging), #12419 (installer migration-walk §10), #12509 (harness.py basename-shadow / pytest collection fix, 4th submit), #12574 (HIGH harness h11 bodyless-204 freeze-fix), #12525 (bare-harness launchers start-harness.sh/.bat).

## Process / standing directives
- Operator: WIP-safe (commit incrementally + checkpoint), DS-review-per-change.
- Verifier rejection = highest priority (fix before new work). 2 QA rounds on #12509 both legit.
- Feature-branch pre-commit guard strips .squidsquad/ → working-state/vault land on MAIN.
- Always merge main into branch, never rebase. Verify branch before commits. No stacking (base follow-ups on main).
- Full `pytest tests/` collection needs #12509 merged (the harness.py rename); pre-merge, run file-scoped.

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
