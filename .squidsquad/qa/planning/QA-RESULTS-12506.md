# QA-RESULTS #12506 — Event-mode periodic driver

**Verdict: FAIL (11/12 ACs PASS; AC11 FAIL) → back to in-progress (role:skill).**
**Verified**: 2026-06-18 13:41 by verifier (qa). PR #12812, branch `squidsquad/task/12506` (HEAD bd7c93a72), 8 commits behind origin/main but no collision in changed files.
**Method**: TEST-PLAN-12506 derived independently from the 12 ACs + LOCKED §8.6.1; executed live against the driver CLI, the full project suite, compose output, and a fresh-agent comprehension gate.

## AC walk

| AC | Verdict | Evidence |
|----|---------|----------|
| AC1 lazy enable | PASS | live: `arm`→`{"action":"schedule"}`; 2nd `arm`→`already-armed` (idempotent). Busy agent never arms (sub-skill Step A only at idle). |
| AC2 idle scan fires | PASS | live: armed + `tick --drained true`, `last_run=null` → `{"action":"scan"}`. Driver-timer path fires independent of any forge event. |
| AC3 bounded | PASS | live: `record-scan`×3 → 3rd `at_cap:true`; later `tick` → `{"action":"cancel","reason":"at-cap"}`. Burst capped at 3. |
| AC4 re-arm + reset | PASS | live: `cancel`→`reidle`→`{"action":"schedule","rearmed":true,"scan_count":0}`; `reidle` preserves `last_run` (tick within cooldown → `wait`, not scan → throttle not bypassed). |
| AC5 Monitor coexist | PASS | live: `tick --drained false`→`absorb-work` (missed-nudge safety net). Sub-skill Atomicity §: cron tick = scheduled tool-invocation, not Monitor stdin; absorbed by next forge-read; no double-processing. |
| AC6 config consume | PASS | live `status`→`burst:3, cooldown_minutes:30`; unit tests: `30m` suffix→30, legacy bare `30`→30, absent→default. |
| AC7 sub-skill reconcile | PASS | idle-cooldown-loop.md:14 removes false fixed-cadence Monitor claim (event_poll silent on empty poll); names §8.6.1 driver as cadence source; KEEPS NUDGE branch (Step C) + cooldown eligibility (Step B); documents `Idle Scan Burst` (Cool-Down Configuration §). |
| AC8 no harness change | PASS | `git diff origin/main...HEAD` — harness.py absent. |
| AC9 composes | PASS | `→ run sub-skill: idle-cooldown-loop` present in all 4 composed CLAUDE.md (dm/pm/qa/skill). Runtime-loaded fragment; body not inlined by design (matches §8.6.1 mechanism). |
| AC10 comprehension | PASS | fresh sonnet agent given ONLY idle-cooldown-loop.md answered all 5 CQs from the file alone; identified the periodic cron driver (NOT Monitor) as cadence source. Spec: tests/comprehension/12506_spec.json. |
| **AC11 installer-files** | **FAIL** | new runtime script `references/scripts/subloop_driver.py` is NOT in `references/installer-files.txt`. |
| AC12 DS-review | PASS | DS-REVIEW-12506-unit1.md (branch+main) + unit3.md (main). High-blast-radius wake-loop reviewed; 6 findings incl. error-severity cancel-action fix corroborated in subloop_driver.py:229-233 (disarmed-tick defense). |
| TC-REG | PASS | `python tests/run_tests.py` → 53 tests OK; `pytest test_subloop_driver_12506.py test_config_functions.py` → 119 passed. |

## AC11 FAIL — detail (ship-blocking)

**Finding:** `references/scripts/subloop_driver.py` (NEW file in PR #12812) is absent from `references/installer-files.txt`.

**Evidence:**
- `installer-files.txt` header: "Every file the wizard needs, fetched by npx squidsquad before launching Claude. ... Maintained alongside the wizard — when you add a ... sub-skill, add its files here too."
- 39 `references/scripts/*.py` files ARE listed (config.py, cycle.py, git_ops.py, harness.py, tracker.py, …); the manifest is the ship gate for runtime scripts. `grep -in subloop references/installer-files.txt` → no match.
- The rewritten `idle-cooldown-loop.md` — which DOES ship (sub-skill, reaches agents at boot) — instructs every event-mode agent (Steps A/B/D) to run `python references/scripts/subloop_driver.py`.

**Impact:** On a fresh install (`npx squidsquad`), `subloop_driver.py` is never fetched. The shipped sub-skill then invokes a missing script → the driver can never arm → **the exact #12506 dormancy reproduces for all new installs.** The fix it ships does not reach the installs that need it.

**Root of the miss:** PM's AC11 wording ("updated iff a new file is added (likely none — in-place edits)") guessed wrong — the impl added a new runtime script. Existing repos already have the file from this commit; only fresh installs are affected, which is exactly what the manifest governs.

**Required fix (surgical, one cycle):**
1. Add `references/scripts/subloop_driver.py` to `references/installer-files.txt` (alphabetical neighborhood near `subloop`/`tracker`).
2. Bump the header comment count (`# Total: 202 files` → 203).
- `tests/test_subloop_driver_12506.py` correctly does NOT need listing — tests are not shipped (0 `^tests/` entries in the manifest).

All other 11 ACs pass with observable evidence; resubmit with the manifest line added for a clean ship.

---

## RE-VERIFY — 2026-06-18 18:35 → PASS (12/12) → pending-ship (DM)

Skill resubmitted (branch HEAD 35eba8381, PR #12812 MERGEABLE, `Closes #12506`). Re-verification focused on the rejected gap + a scope-creep/regression guard.

**AC11 (the rejected gap) — now PASS:**
- `references/installer-files.txt:49` now lists `references/scripts/subloop_driver.py`, correctly alphabetized between `state_bus.py` (48) and `tc_coverage.py` (50).
- Header `# Total: 203 files` == actual 203 non-comment/non-blank lines (count accurate, not just bumped).

**No scope creep / 11 ACs still valid:** `git diff bd7c93a72..HEAD` (my-reject..resubmit) on the impl files shows the core (`subloop_driver.py`, `idle-cooldown-loop.md`, `config.py`, `wizard.py`, `test_subloop_driver_12506.py`) **byte-identical** to what I verified PASS — the only intentional change is the one `installer-files.txt` line. Everything else in the range (config.md 30m/burst, comprehension specs, run_tests.py/#12408) arrived via a clean `origin/main` merge (35eba8381), not re-implementation.

**Regression (the merge is new):**
- `pytest test_subloop_driver_12506.py test_config_functions.py` → 119 passed.
- Full static gate on the merged branch: `[static-gate] PASS — 4577 gated test(s) passed (0 failures, 0 errors)`, EXIT 0 (branch now carries #12798's untrack-fix + #12408's hardened gate; previously-red `test_volatile_files_not_tracked` resolved, gate runs to session-finish).

**Out-of-scope, correctly handled:** skill flagged a systemic gap — no test asserts `installer-files.txt` lists every shipped runtime script (why AC11 slipped the gate), and `event_poll.py` itself looks similarly unlisted. `event_poll.py` is NOT introduced by #12506 (pre-existing, outside this diff), so it is correctly NOT a #12506 re-block; skill is filing a separate improvement rather than scope-creeping this PR. Agreed.

**Verdict: PASS — all 12 ACs satisfied.** Merge deferred to DM (`Closes #12506` → QA-merge would auto-close + skip DM). Counter NOT bumped. #12506's 3 atomic artifacts: config.md keys already on main; sub-skill + driver + manifest land together when DM merges PR #12812.
