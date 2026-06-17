# Working State

- **Task**: idle — 4 units to gates this session. #12585 (L1 Soul, approved) is NEXT but deferred for FRESH CONTEXT (high-blast-radius L1 + LLM-consumed/CQ-gated; this session is very deep — 4 units + 3 DS reviews).
- **Status**: #12509 + #12574 SHIPPED+CLOSED; #12420 held-on-PM-CQ-AC (PR #12596); #12525 pending-test (PR #12617); #12585 approved/queued; #12492/#12493/#12506 held on gates. NOTE: full `pytest tests/` now works on main (#12509 harness.py rename merged).
- **RESTART-REQUIRED DEFERRED (10:21)**: l4-recompose fired restart-required, but composed skill CLAUDE.md mtime is 09:46 (≠ event time) → 10:21 recompose was a no-op → matches #12397 spurious-emit. Per operator's standing 'reboots deferred', NOT self-restarting. Composed CLAUDE.md DID change at 09:46 (uncommitted local recompose) so a reboot would sync instructions — operator's call. Surfaced to operator.
- **Updated**: 2026-06-17 09:40 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## >>> #12574 → pending-test (PR #12643) — HIGH harness freeze-fix <<<
RCA: POST /events unknown-role drop returned JSONResponse(204, content={}) — a 204 carrying a {} body → h11 LocalProtocolError 'Too much data for declared Content-Length' → poisons keep-alive conn → event-delivery GETs stall → ~6h squad freeze. Issue's multi-byte hypothesis WRONG (JSONResponse byte-sizes UTF-8 correctly; test pins it). Fix: bodyless Response(status_code=204). 3 tests (AST source guard authoritative — TestClient/httpx can't repro the h11 wire error; functional bodyless-204; UTF-8 byte-correct). DS 12574-c1 clean (1 dead-import→fixed). Code bug, no CQ.

## >>> NEXT PICKUP: #12585 (L1 Soul 'Health & Diagnostics — Facts Over Context') — approved, role:skill <<<
Deferred this session for fresh context: it's an L1 SOUL change = high-blast-radius (all agents on reboot) + LLM-consumed → CQ-gated (needs comprehension AC; PM authors, verifier authors spec). Author carefully on fresh main. Build pattern: L1 source edit + compose.py deploy-all + DS review + flag PM for CQ AC.

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
#11613 (dep-provisioning), #12473 (L1 comms), #12475 (--force legality override), #12460-shadow (liveness divergence logging), #12419 (installer migration-walk §10), #12509 (harness.py basename-shadow / pytest collection fix, 4th submit), #12574 (HIGH harness h11 bodyless-204 freeze-fix).

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
