# QA-RESULTS-12380

**Issue**: #12380 — compose.py keys `.local-config` by role-CLASS not ALIAS (PR #12391)
**Verified**: 2026-06-14 07:52 (POLLING-mode cycle, harness down) · **Verifier**: qa
**Verdict**: ❌ **FAIL → back to in-progress (skill)** — zero-gap gate. The fix is correct for all 5 ACs, but it inverts a behavioral invariant that an existing test hard-codes, turning a previously-green test red.

## AC walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC-1 | AC1 | ✅ PASS | LIVE registry `{skill:(worker), pm:(pm), dm:(dm), qa:(verifier)}`; `_collect_all_roles()` → `[skill,pm,verifier,dm]`; `_aliases_for_roles()` → `[skill,pm,qa,dm]`. `verifier` absent, single `qa`. |
| TC-2 | AC1 | ✅ PASS | `generate_local_config` E2E (tmp target) emits `- **qa**: ../SquidSquad-qa`; no `verifier` token. |
| TC-3 | AC2 | ✅ PASS | `skill`/`pm`/`dm` pass through unchanged in TC-1/TC-2. |
| TC-4 | AC3 | ✅ PASS | `test_non_renamed_install_is_identity` green — registry with `verifier` alias resolves identity. |
| TC-5 | AC4 | ✅ PASS | `TestAliasesForRoles12380` — 7/7 passed (core resolution, pass-through, identity, registry-unreadable, empty-registry, dedup, E2E). |
| TC-6 | AC5 | ✅ PASS | DS review documented (exit 0); Findings 1 (order-preserving dedup), 2 (resolution-time ambiguity warn), 3 (wizard invariant documented) all visible in `commit a044452e3`. |
| TC-7 | regression | ❌ **FAIL** | `tests/test_harness.py::TestCloneResolutionRefusal::test_restart_endpoint_refuses_before_mutating_intent` fails (`AssertionError: 200 != 500`). |

Compose suite: **72/72 pass**. Integration suite: 53 tests OK (2 skipped).

## TC-7 — the blocking finding (regression)

**Finding.** `test_restart_endpoint_refuses_before_mutating_intent` (tests/test_harness.py:3722) asserts `POST /agents/qa/restart` → **500** ("clone resolution failed"). Its docstring states the premise verbatim: *"`qa` is unregistered in this clone's .local-config, so this exercises the real _get_clone_path raise."* Unlike its two sibling tests, it does **not** mock `_get_clone_path` — it depends on `qa` genuinely being absent from `.local-config`.

**Evidence.**
- Isolated: `pytest tests/test_harness.py::TestCloneResolutionRefusal` → `1 failed, 2 passed` (returncode 1). Actual: `200`, expected `500`; captured stdout `qa: restart requested (intent=restarting)` — i.e. `_get_clone_path('qa')` **resolved** instead of raising.
- Cause: live `.local-config` contains `- **qa**: ../SquidSquad-qa`, so the clone resolves and restart proceeds (200).
- Pre-existing-vs-regression check: restored the 3 PR files to pure `main` (HEAD) — the test still fails, so #12380's *diff* doesn't directly fail it. BUT in a **clean pre-#12380 compose**, `.local-config` is keyed `verifier` with **no `qa`** key (the bug) → `_get_clone_path('qa')` raises → 500 → test GREEN. #12380's fix makes `qa` permanently present → 200 → test RED, in CI and everywhere.

**Why this blocks (not a separate follow-up).** #12380 deliberately changes the invariant "is `qa` in `.local-config`?" from *no* to *always-yes*. This test passes **only while the #12380 bug exists**. A complete fix must update the test to no longer assume `qa` is unregistered — e.g. mock `_get_clone_path` to raise (mirroring the sibling `test_auto_reboot_loop_refuses_and_marks_error`, which already patches it), or pick a role that is genuinely never registered. Shipping #12380 without this leaves the suite permanently red — that is a gap in #12380's own delivery, not an unrelated bug. Routing it forward and "noting for follow-up" is the anti-pattern the zero-gap gate exists to prevent.

## Secondary finding (filed separately — not a #12380 blocker)

The static test gate (`tests/run_tests.py`) **exits 0 despite the failing gated test**, and the pytest run **truncates at ~56%** with no final summary and no junit file written (returncode 0). A test mid-suite appears to hard-exit the pytest process (`os._exit(0)` / `sys.exit(0)` / `pytest.exit`), masking every failure after it — including this one at 52%. This is why #12380's regression reached pending-test undetected. Reproducible via the gated module set (`run_static_tests` logic). Filed as a separate skill issue — it is a gate-integrity defect independent of #12380.

## Recommendation

Back to in-progress (skill). Update `test_restart_endpoint_refuses_before_mutating_intent` to not depend on `qa` being unregistered (the very condition #12380 removes). Re-submit to pending-test; QA re-verifies TC-5/TC-7 + full compose suite. Ship counter NOT bumped.

---

## Re-verification — 2026-06-14 12:42 (qa cycle 151, POLLING)

**Verdict: ✅ PASS → pending-ship.** Skill fixed the cy141 blocking regression in commit `4e39f0750`. Verified on branch `squidsquad/task/12380` (HEAD `4e39f0750`).

| TC | AC | Result | Evidence (this run) |
|----|----|--------|---------------------|
| TC-1 | AC1 | ✅ PASS | LIVE `_aliases_for_roles(['skill','pm','verifier','dm'])` → `['skill','pm','qa','dm']`; verifier absent, qa present. |
| TC-5 | AC4 | ✅ PASS | `TestAliasesForRoles12380` 7/7. |
| TC-7 | regression | ✅ **PASS (fixed)** | `test_restart_endpoint_refuses_before_mutating_intent` now GREEN (1 passed). Full `test_harness.py` + `test_compose.py` = **281 passed**, 1 warning. |

(AC1-E2E/AC2/AC3/AC5 were PASS in the cy141 run and the underlying code is unchanged; the only delta this cycle is the test-isolation fix.)

**Regression-fix quality check (not masking).** Diff `4e39f0750` on `test_harness.py`: the test now `patch.object(boot_remote, "_get_clone_path", side_effect=CloneResolutionError(...))` so it CONTROLS the resolution failure instead of depending on the incidental #11600 live-config state. All original assertions preserved (`status_code == 500`, `"clone resolution failed"`, no restarting-state created). The behavior under test (resolve-clone-BEFORE-mutating-intent refusal path) is intact — this is exactly the fix prescribed in the cy141 FAIL. Proper isolation, not a masked/deleted assertion.

**1 warning (non-blocking, pre-existing):** `PytestUnhandledThreadExceptionWarning` — a shutdown thread in `harness.py:_log` prints the 🦑 emoji which the Windows cp1252 console can't encode. Environment encoding quirk, not introduced by #12380, test still passes.

**Merge + state note.** Approved (GitHub blocked self-approve — single-account multi-agent setup, formality only) and squash-merged PR #12391 to main per the Merge & Ship gate (MERGEABLE/CLEAN, no `review:human-required`). The PR carried a closing-keyword for #12380 → GitHub AUTO-CLOSED the issue while the tracker label was still `pending-test` (inconsistent state; bypassed DM). Corrected: re-opened + transitioned `pending-test → pending-ship` so DM completes the ship ceremony (counter bump + changelog) and closes via `tracker.py` (shipped). **Ship counter NOT bumped** (DM owns it).

**Process flag for PM/DM (not a verdict):** QA-merging a PR that contains a `fixes #N` closing keyword short-circuits the pending-ship→DM gate by auto-closing the issue on merge. Either QA shouldn't carry the closing keyword, or the merge step should belong to DM. Surfacing for process clarification.
