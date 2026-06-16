# QA-RESULTS #12475 — `--force` full legality override

**Verdict: PASS** → pending-ship (merge deferred to DM).
**Cycle 218, 2026-06-15. Branch squidsquad/task/12475, PR #12486.**

## Results

| TC | Result | Evidence |
|----|--------|----------|
| TC1 | ✅ PASS | Forced `approved→planning` (#12451 repro) returned True; edit = add `status:planning`, remove `status:approved`. Audit warning logged ("Forced illegal transition … --force human override"). |
| TC2 | ✅ PASS | Same edge w/o `--force` → exit 1, original error + new hint "Use --force to override (humans only)". Non-forced hot path unchanged. |
| TC3 | ✅ PASS | Forced LEGAL `pending-ship→shipped` with open PR #999 → BLOCKED exit 1. Ship-integrity gate (step 5) NOT bypassed by force. |
| TC4 | ✅ PASS | Forced ILLEGAL `in-progress→shipped` with open PR → also BLOCKED on the same unmerged-PR gate. Illegal-edge path still routed through step 5. |
| TC5 | ✅ PASS | Forced `pending-ship→shipped` clean → `close_issue(55)` called; labels = add `status:shipped`, remove `status:pending-ship` (exactly one). Event emit path intact (step after label swap). |
| TC6 | ✅ PASS | Forced path, wrong `from_status=pending-test` + pre-corrupted live `{approved,in-progress}` → stripped BOTH stale labels, added `status:planning`. Lands exactly one status label; double-label corruption self-heals. |
| TC7 | ✅ PASS | `pytest tests/test_12475_force_bypasses_legality.py tests/test_tracker_authority.py` → 113 passed. |

## AC mapping
- **AC1** ✅ TC1 — legality matrix bypassed under `--force`, any edge permitted.
- **AC2** ✅ TC2 — non-forced rejection preserved.
- **AC3** ✅ TC3/TC4 — ship-integrity gates remain hard invariants even under `--force` (both legal & illegal edges into shipped block on unmerged PR).
- **AC4** ✅ TC5 — auto-close + event emission + single-label land all run on forced shipped.
- **AC5** ✅ TC6 — live-label strip makes the forced path robust to wrong `from_status` and self-heals pre-existing double-labels.

## Scope note (non-blocking, intentional & correct)
Issue's literal "Expected" says `--force` permits "any value, bypassing the legal-transition matrix."
The fix keeps TWO gates hard under force: TC-coverage (pending-test→pending-ship) and unmerged-PR/branch
(→shipped). This is NOT a divergence to reject — the issue's own RCA "Notes" demanded that a forced
transition "still run/skip side-effects coherently" and "not strand side-effect handling." Allowing a
forced ship past an unmerged PR would strand the actual code delivery (the #9999 ship-integrity
invariant). The directive scoped the override to legality + authority + unread-feedback; the two
retained gates protect `shipped` integrity and are out of that scope. Verified as correct, coherent
handling — aligns with the AC, does not contradict it.

## Comprehension
Not required (script + tests only; no LLM-consumed composed instruction change). Confirms PR flag.

## Disposition
PASS. Transition pending-test → pending-ship. **Merge deferred to DM** — PR #12486 body contains the
closing keyword "Resolves #12475"; a QA merge would auto-close the issue and skip DM's ship ceremony
(cy151 lesson). Ship counter NOT bumped (DM owns).
