# QA-RESULTS #12419 — Installer migration-walk (INSTALLER-ARCH §10)

**Verdict: PASS** → pending-ship (merge deferred to DM).
**Cycle 271, 2026-06-17. Branch squidsquad/task/12419, PR #12533.**

## Results

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 | ✅ PASS | Own fixture: no `.squidsquad/` → `migration_walk_plan` is_fresh=True, is_noop=True, chain=0 (walk skipped). Stamped config.md at 0.43.0 → installed=0.43.0 read correctly, is_fresh=False. `installed_version` returns None=fresh / PRE_VERSION_STAMP=unstamped / stamp value (annotation-token-safe, DS-c1 F5). |
| TC2 | AC2 | ✅ PASS | Own fixture: 5 migration files placed out-of-order incl. below-installed (→0.43.0) and above-target (→0.47.0); installed 0.43.0, target 0.46.0 → chain = [0.44.0, 0.45.0, 0.46.0] ascending; out-of-range excluded; missing 0.44→0.45 step simply absent (silent, §10.4). `select_migration_chain`: `installed < to <= target`, sorted by `_version_key(to)`. |
| TC3 | AC3 | ✅ PASS | WIZARD Step 0b.1: Gate 1 DeepSeek audit (no write) → Gate 2 mini-CQ operator confirm (no write) → apply atomically → Gate 3 compose `deploy-all --check` validating written tree (git-restore revert on fail). Rejection/failure at any gate stops the walk clean; version stamp NOT advanced; idempotent re-walk on re-run (§10.4). |
| TC4 | AC4 | ✅ PASS | Own fixture: `stamp_version('0.46.0')` → exactly ONE `SquidSquad Version` line (atomic .tmp+replace, in-place, CRLF-aware F3, single-stamp F6); unrelated `- **Project**: x` line preserved. WIZARD step 4: stamp is the only out-of-gate write; "Migration files MUST NOT modify this field themselves." Preservation: later steps write only fresh-scaffold paths, never overwrite. |
| TC5 | AC5 | ✅ PASS | WIZARD Step 0b: the flat 3-way prompt is replaced by Upgrade (default) / Full rebuild (typed-confirm, deletion deferred to Step 7.1) / Abort, pointing to Step 0b.1 migration walk. Doc + runbook in sync (both in WIZARD.md). |
| TC6 | AC6 | ✅ PASS | `pytest tests/test_wizard_12419_migration_walk.py tests/test_wizard_runbook.py` → **67 passed**. Covers fresh vs existing branch, sample migration chain, preservation invariant. |
| TC7 | AC-CQ | ✅ PASS | Authored `tests/comprehension/12419_spec.json` (6 CQs). Fresh sonnet agent given ONLY Step 0b/0b.1 prose → **zero branch-semantics misreads**: CQ1 Upgrade-default ✓, CQ2 three-gate walk in order ✓, CQ4 installer-stamps-not-migrations ✓, CQ5 full-rebuild typed-confirm + deferred-to-7.1 deletion ✓, CQ6 preservation ✓. CQ3: agent correctly identified that chain *ordering/gap-handling* lives in `wizard.py migration-plan` (not the runbook prose) and that it walks the returned chain in order — a correct scoping read (the ordering itself is verified at script level in TC2), not a misread. |

## AC mapping
AC1 ✅ TC1 · AC2 ✅ TC2 · AC3 ✅ TC3 · AC4 ✅ TC4 · AC5 ✅ TC5 · AC6 ✅ TC6 · AC-CQ ✅ TC7. All pass.

## Non-blocking note (flagged, not a gap)
Step 0b.1 Gate 3 carries a transparent **sequencing note**: §10 says the dry-run validates "before
any write," but `compose.py --check` reads the on-disk tree, so the only executable order is
write→validate→revert-on-fail (atomic-per-file from the operator's view). Skill has already flagged
this to PM on the #12419 Discussion to reconcile §10's wording. This is a doc-reconciliation item
(the implemented behavior is correct and atomic), NOT a QA blocker — surfaced, not hidden.

## Disposition
PASS → transition pending-test → pending-ship. **Merge deferred to DM** (DM owns the ship ceremony;
PR #12533 has no closing keyword so no auto-close, but the deferral pattern holds). Ship counter NOT
bumped (DM owns). TEST-PLAN-12419 / QA-RESULTS-12419 / tests/comprehension/12419_spec.json committed.
Sibling #12420 (post-commit restart) is next in skill's serial installer queue.
