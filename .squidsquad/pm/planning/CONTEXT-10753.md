# BUG: PRD-C (L4 customization) — DS audit findings

**Source**: DeepSeek code review of landed PRD-C stories (C1–C10) vs spec.
**PRD spec**: `docs/prd/compose-l4-customization.md`
**Audit doc**: `.squidsquad/pm/planning/AUDIT-PRD-C-DS-REVIEW.md`
**Verdict**: PARTIAL — 1 ERROR + 3 WARNINGS

## ERROR — C8 Gate 0 prompt template not registered in model_router

- **File**: `references/scripts/model_router.py:538-546` (`template_map`)
- **Severity**: error
- **Issue**: `l4-conflict-preempt` task type is missing from `template_map`; only `l4-audit` is wired. Routing falls back to a bare generic prompt — strips the contradiction-vocabulary, sub-skill exemption, and step-id locality rules from `l4-conflict-preempt.md.j2`. **Gate 0 effectively operates in degraded mode despite C8 prompt template being authored.** Also: C3's `l4-audit` may have the same issue if `key_map` is incomplete — verify both during fix.
- **Stories implicated**: C8 (#10657), and possibly C3 (#10652)
- **Suggested fix**: add `"l4-conflict-preempt": "l4-conflict-preempt.md.j2"` to `template_map` (and verify the `key_map` routes the task to the correct model). Audit the entire l4-* task family for similar registration gaps.

## WARNING 1 — Gate-count drift in `l4-curation.md` (3 vs 4 vs 6)

- **File**: `references/sub-skills/common/l4-curation.md:12-13` vs Steps 8/9 of same file
- **Severity**: warning
- **Issue**: Line 12 says **"four safety gates"**; PRD headline says **"three"**; Step 8 enumerates **six** stages (Gate 0–5). Agents reading the sub-skill could literally skip Gate 0 (pre-emption) or Gate 5 (recompose poll) based on the contradictory headline prose. This is exactly the kind of internal-inconsistency drift `feedback_plan_first` and the prose-drift discipline target.
- **Stories implicated**: C1 (#10650), C7 (#10656), C8 (#10657) — all three touched `l4-curation.md` and none reconciled the header.
- **Suggested fix**: pick the authoritative gate count (most likely six: Gate 0–5 per Step 8), rewrite the header bullet at lines 12-13 to match, and update PRD §X.X to match. Do a single-pass DS internal-consistency audit on `l4-curation.md` after the fix.

## WARNING 2 — `wait_for_recompose` returns "failure" on missing config

- **File**: `references/scripts/l4_recompose_recovery.py:172-180`
- **Severity**: warning
- **Issue**: The standalone `wait_for_recompose` function returns `status="failure"` when `check_recompose_fn=None`, while the orchestrator path returns `"skip"`. Semantic mismatch: direct callers (not going through the orchestrator) could trigger spurious reverts on what should be a no-op.
- **Stories implicated**: C7 (#10656)
- **Suggested fix**: standardize on `"skip"` for the missing-config case in both code paths. Update tests to lock the contract.

## WARNING 3 — C4 mini-CQ head-token allowlist gap

- **File**: `references/scripts/l4_mini_cq.py:134-136`
- **Severity**: warning
- **Issue**: Phrases like `"do it now"`, `"ship it please"`, `"y please"` get classified as ambiguous despite matching `_APPROVAL_TOKENS`. The 2-strike rule may abandon clear approvals from the human, hurting throughput for the very interaction Gate 2 is supposed to validate.
- **Stories implicated**: C4 (#10653)
- **Suggested fix**: relax the head-token check to allow approval tokens to appear anywhere in a short response (configurable threshold), not just at the head. Add unit-test cases for the three example phrases above.

## Recommended fix order

1. **ERROR (C8 Gate 0 template)** first — it gates the entire L4 customization flow's correctness; fix this before any v2 cutover that exercises Gate 0.
2. **WARNING 1 (gate-count drift)** second — affects agent comprehension of the gate count; pair with the C8 fix (both touch the same sub-skill area).
3. **WARNING 2 (`wait_for_recompose` semantics)** — quick win; standardizes the contract.
4. **WARNING 3 (C4 head-token gap)** — usability polish; lowest urgency.

## Notes

- DS evidence is in `AUDIT-PRD-C-DS-REVIEW.md`.
- The gate-count drift (WARNING 1) is the kind of finding that should have been caught by the internal-consistency audit before merge — recommend adding a DS internal-consistency pass as a hard gate in the L4 sub-skill modification workflow (could be filed as a follow-up improvement task once the audit-review hold is cleared).
