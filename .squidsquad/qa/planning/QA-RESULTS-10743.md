# QA-RESULTS-10743 — Catalog parser rejects intentional name-collision

**Verified**: 2026-06-02 09:40
**Branch**: `skill/issue-10743-catalog-duplicates` @ `21f08b5f`
**PR**: #10749
**Verifier**: qa-lead
**Result**: **PASS** (with follow-up #10755 filed)

## Scope Check

- `docs/sub-skill-catalog.md` (24 lines changed) — 5 duplicate-name row patterns renamed to slash-bearing form
- `tests/test_catalog_parser_d1.py` (56 lines changed) — xfail-strict pin removed; clean-parse path enabled
- (Unrelated state-file diff: worker/skill CLAUDE.md output files removed/edited — housekeeping, not part of the fix)

## Fix Approach

Skill chose **option 3** from the issue body (slash-bearing rename) — mirrors existing precedent (`roles/dm/events/pr-merge-wait`) without parser changes since `includes.yml` already used the slash-bearing form. Cleanest of the three proposed options.

Patterns renamed (5):
- `improvement-scan` → `roles/pm/improvement-scan` (the duplicate that originally triggered #10743)
- `issue-filing` → `roles/{pm,qa,dm}/issue-filing` (3 variants)
- `task-pickup` → `roles/dm/task-pickup`
- `discussion-protocol` → `roles/{pm,qa,dm}/discussion-protocol`
- `ralph-loop-overview` → `roles/{pm,qa,dm,dev}/ralph-loop-overview`

## Verification

**Parser-clean**: `cp.parse_catalog('docs/sub-skill-catalog.md')` no longer raises. The xfail-strict marker for the duplicate-detection regression test has been removed — the test now passes cleanly.

**D4 drift-check goes live**: `python references/scripts/compose.py drift-check` on the branch returns exit 1 with a structured orphan report — the first time D4 has been able to run against the live catalog. This is **expected behavior**: D4's job is to surface drift, and there is drift to surface. **9 orphan catalog rows** (catalog entries whose source file doesn't exist on disk).

**Follow-up filed**: skill's PT comment said "pre-existing orphans ... will be filed as a separate follow-up" but the ticket had not been filed at verification time. I filed **#10755** to track the orphan-cleanup. This routes to pm-lead since PM owns the catalog rows.

## Test Execution

`pytest tests/test_catalog_parser_d1.py tests/test_v1_byte_stability_9a.py tests/test_catalog_drift_d4.py tests/test_v2_catalog_gate_d3.py tests/test_manifest_v2_d5.py -q` on `21f08b5f` → **100 passed** (no xfailed — the regression-pin flip is properly resolved).

Coverage matrix:
- 27 D1 catalog parser (including the now-real `test_real_catalog_parses_cleanly`)
- 5 §9a v1 byte stability
- 18 D4 catalog drift
- 15 D3 catalog gate
- 36 D5 unified manifest

## Scope Discipline

Per `feedback_no_ship_with_gaps`, "noted for follow-up" is the phrase to reject. The key distinction here vs #10682's route-back:

- **#10682**: deferred a piece of the story's STATED scope (AC5 harness wiring) without filing a follow-up → route-back
- **#10743**: stated scope (duplicate-name conflict) is fully resolved; the orphan-cleanup is a NEW finding D4 surfaces — different scope. Skill's "will file follow-up" intent was correct but unexecuted; I filed it (#10755) as part of QA's "file issues directly" responsibility (L3).

The fix for the issue's stated scope is clean and complete.

## v1 Coexistence

§9a v1 byte-stability gate: **5/5 passed** on `21f08b5f`. v1 compose doesn't read the catalog; the rename is invisible to v1.

## Outcome

Stated issue scope cleanly resolved. xfail-strict regression-pin properly flipped (xpass → removed). D4 now operates against the live catalog and surfaces orphans (filed as #10755). 100 tests green; §9a clean. **Transitioning #10743: pending-test → pending-ship.**
