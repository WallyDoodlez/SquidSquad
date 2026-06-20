# QA-RESULTS-12909 — VERDICT: PASS → pending-ship

- **Verified**: 2026-06-19 18:35 (cy372, POLLING session)
- **Issue**: #12909 (type:issue/high, role:skill) — installer manifest missing 17 more `references/scripts/*.py` (incl. critical `event_poll.py`); needs per-script runtime-vs-dev triage + a curated-allowlist completeness test. **I flagged this for prioritization in cy371's #12907 verdict.**
- **PR**: #12911, branch `squidsquad/task/12909` (MERGEABLE/CLEAN, "Closes #12909").
- **Result**: **PASS — triage correct, completeness-gated, install integrity intact.** Append-only.

## ACs (from issue Fix direction)
1. Triage all 17 (+ re-audit the full 66): runtime-required → add; dev/CI/migration-only → explicit allowlist constant with reason.
2. Completeness test: every `references/scripts/*.py` is listed OR in the documented allowlist.
3. Bump header count.

## Evidence (independent)
- **AC1 (triage) — PASS.** All 66 `references/scripts/*.py` now accounted: **63 shipped** + **3 allowlisted**. `event_poll.py` (the headline gap — every event-mode agent's Monitor spawns it) is now **listed/shipped**, along with the other critical runtime scripts I spot-checked: statusline_data, process_utils, link_stage_validator, v2_link_stage, compose_freshness, event_catalog, event_validator, catalog_parser, source_frontmatter — all shipped.
  - **Allowlist triage independently validated.** `MANIFEST_EXCLUDED_SCRIPTS` = {migrate_labels_6274.py, verify_dual_label_6274.py, monitor_smoke_poller.py}, each with a reason. I grepped all of `references/scripts/` for runtime imports/invocations of these 3 — the ONLY references are **docstring mentions** (`cycle_pre.py:662` explains the #6274 dual-tag rationale in prose; `verify_dual_label_6274.py:21` is the verifier's own docstring). **Zero runtime callers** → the 3 are genuinely one-time-migration / dev-CI-only and correctly excluded. (Erring toward shipping the uncertain `v2_*`/`orphan_cleanup`/`catalog_drift` is the safe direction — a wrongly-shipped dev script is install bloat; a wrongly-omitted runtime script breaks installs.)
- **AC2 (completeness gate) — PASS.** `tests/test_installer_wiring.py` adds `test_every_runtime_script_listed_or_excluded` (globs `scripts/*.py`, asserts each ∈ manifest OR ∈ MANIFEST_EXCLUDED_SCRIPTS — would have caught #12907 AND this AND future omissions) + `test_excluded_scripts_are_not_also_listed` (contradiction guard: allowlisted ≠ shipped). 27/27 pass. My independent disk-vs-(manifest+allowlist) sweep: **zero unaccounted**.
- **AC3 (header count) — PASS.** `# Total: 229 files` matches actual 229 entries (counted). **Install integrity**: all 229 manifest entries resolve to real files on disk (zero dangling).
- **No CQ gate** — manifest data + test file, no LLM-consumed instruction change.

## Disposition
- **VERDICT: PASS → pending-ship (DM).** Zero gaps. This closes the manifest-completeness arc (#12907 = l4 family, #12909 = the broad 66-script audit + the general gate that prevents recurrence).
- Merge **deferred to DM** — PR carries "Closes #12909" (QA-merge would auto-close + skip DM).
- Counter NOT bumped (DM owns).
- **Tracker hygiene note → PM (non-blocking):** #12909 carried a double status label (`status:pending-test` + `status:open`) when I picked it up — the `status:open` from `create-issue` was never stripped during the open→in-progress→pending-test path. My pending-ship transition removes pending-test; a residual `status:open` may remain. Cosmetic; flagging for PM/tracker hygiene. Does NOT affect routing (DM finds it via pending-ship).
