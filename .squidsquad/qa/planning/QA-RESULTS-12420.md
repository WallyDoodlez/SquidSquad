# QA-RESULTS #12420 — Installer post-commit harness restart (§10.3)

## Re-verification (cy316, 2026-06-17) — verdict: PASS → pending-ship (DM)
Branch squidsquad/task/12420 @ 4c3590fb6, PR #12596. The cy314 gap (TC6) is fixed at root.
- **TC6 now PASS**: `restart-agents` registered in `_WIZARD_COMMANDS` (tests/test_wizard_runbook.py:43, with `# #12420 §10.3` comment — the #11613/#12419 pattern). `test_every_wizard_command_mentioned_exists` → PASS.
- Full `test_wizard_runbook.py` + `test_wizard_12420_post_commit_restart.py` → **45 passed**.
- Test-only one-liner; wizard.py / WIZARD.md / the AC-CQ comprehension spec (cy314 6/6) all unchanged → AC1-5 + AC-CQ remain PASS from cy314. `test_tc_10b` left as-is (pre-existing #11503/#12748, fails on main too).
- **Verdict: PASS, all ACs green.** Merge deferred to DM (`Resolves #12420`). Counter NOT bumped.

---

## Verification (cy314, 2026-06-17) — verdict: FAIL → in-progress (skill)
Branch squidsquad/task/12420 @ origin tip, PR #12596. One concrete gap (test-registry drift the PR's
own change introduced); everything else is PASS-quality.

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1/AC3 | ✅ PASS | `wizard.py restart_agents`: reads `.harness-port` (default 7373), probes `GET /status` (2xx within 5s) → reachable: per-alias `POST /agents/<alias>/stop` then `/start` (best-effort, per-alias failure non-fatal, `ok=False` only on reachable+failure); unreachable: reports `./start.sh`, NEVER self-spawns (Q-new21). Endpoints match HARNESS-ARCH §4.1 (`POST /agents/{role}/stop|start`, alias as path-param; per-alias not `/agents/all`). |
| TC2 | AC2 | ✅ PASS | stop+start per alias → agents respawn in own trees + boot refreshed CLAUDE.md (no stale-instruction agents). Covered by `test_restarts_each_alias_stop_then_start`. |
| TC3 | AC4 | ✅ PASS | WIZARD.md Step 7.5c added + Step 7.6 reworked: branches on `reachable`/`ok` (refreshed-team message vs cold-start `./start.sh`/`.\start.ps1`), "Never auto-spawn the harness yourself", ephemeral exit. Replaces the bare "run ./start.sh" + exit. |
| TC4 | AC5 | ✅ PASS | `test_wizard_12420_post_commit_restart.py` → **21/21 pass**: port read (default/file/whitespace/invalid), alias parse, probe (transport-err/non-2xx → cold-start), reachable stop+start each alias, partial-failure recorded, exit codes (unreachable 0, clean 0, reachable+failure 1). |
| TC5 | AC-CQ | ✅ PASS | Authored `tests/comprehension/12420_spec.json` (6 CQs). Fresh **sonnet** agent given ONLY the Step 7.5c+7.6 prose → **6/6 correct, ZERO misreads**: per-alias stop+start (not global/start.sh), unreachable→no-self-spawn/cold-start, partial-failure→non-fatal/no-rollback/list-failures, refreshed-vs-cold-start message, helper-already-called, ephemeral exit. |
| TC6 | regression | ❌ **FAIL** | `tests/test_wizard_runbook.py::TestHelperCommandReferences::test_every_wizard_command_mentioned_exists` → **FAILED**: `Runbook references unknown wizard commands: {'restart-agents'}`. |

## The gap (TC6 — root cause, specific)
#12420 added the `restart-agents` command to **both** `references/scripts/wizard.py` (dispatch line
3666, `cmd_restart_agents`) and `references/wizard/WIZARD.md` (Step 7.5c: `wizard.py restart-agents`),
but did **not** register it in the test's command set `_WIZARD_COMMANDS`
(`tests/test_wizard_runbook.py:33-42`). That set is the runbook↔dispatch consistency invariant; its
own comments document the pattern that each command-adding PR updates it (`#11613 → gather-deps,
provision-deps`; `#12419 → migration-plan, stamp-version`). #12420 left `test_wizard_runbook.py`
untouched, so `test_every_wizard_command_mentioned_exists` now fails on the branch. (Passes on main —
no `restart-agents` mention there — so the PR introduced it.)

## Required fix (skill, one-line)
Add `"restart-agents"` to `_WIZARD_COMMANDS` in `tests/test_wizard_runbook.py` (with a
`# #12420 §10.3 post-commit restart` comment, matching the established pattern). Re-run
`tests/test_wizard_runbook.py` → green.

## Not a #12420 gap (for the record)
`tests/test_feat_6581_wizard_reframing.py::test_tc_10b_run_tests_exit_zero` also fails, but it is
**pre-existing / tracked (#11503)**: it recursively invokes the FULL suite and asserts exit-zero —
which is now honestly non-zero post-#12720 (the suite completes and surfaces the known/env failures:
#10360, #12748). Fails on main too; not introduced by #12420.

## Disposition
FAIL → in-progress (skill). The fix half (wizard.py + WIZARD.md + 21 tests + comprehension) is
shipped-quality; only the stale test-command registry blocks. Comprehension spec authored + committed
(preserved). Zero-gap gate: one failing test = back to the worker.
