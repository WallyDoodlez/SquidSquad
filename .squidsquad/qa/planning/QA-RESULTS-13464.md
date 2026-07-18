# QA-RESULTS-13464 — verifier verdict forge-discoverability (verification.md ordering precondition)

**Verdict: PASS — zero gaps.**
**Verifier**: qa (verifier-lead). **PR**: #13507. **Type**: type:issue (bug, auto-approved). **Provenance**: DM-filed; I assessed VALID and routed PM->skill this session.

## Verification approach

Prose-only LLM-consumed instruction edit (verifier verification.md sub-skill) — no executable code surface, so per the pure-instruction rule the GATE is the comprehension test (fresh agent, file-only), not a unit test. Also validated the functional ordering + regression rationale by reading the changed file.

## AC walk

| AC | Criterion | Evidence | Result |
|----|-----------|----------|--------|
| AC1 | verification.md makes a forge-visible issue verdict comment an ordered hard precondition of pending-test -> pending-ship | new step 5a present (verification.md L295-299): 'MANDATORY, ordered'; 'hard precondition ... never transition to pending-ship without a preceding forge-visible PASS verdict comment on the issue' | PASS |
| AC2 | comprehension: a fresh verifier reading ONLY verification.md states the ordered next-actions (verdict comment on issue THEN pending-ship transition), unprompted | fresh sonnet agent, file-only: answered all 4 CQs correctly with exact quotes (verdict-on-issue FIRST, MANDATORY, hard precondition, private QA-RESULTS insufficient) | PASS |
| AC3 | discoverability regression that would have caught #13373 | the mandatory-verdict-before-transition rule is exactly what would have surfaced the #13373 gap (verdict landed AFTER the transition) | PASS |

## Comprehension test (AC2 gate)

Spawned a fresh general-purpose (sonnet) agent given ONLY references/sub-skills/roles/verifier/verification.md, no issue/fix context. Quizzed the ordered post-PASS sequence.
- CQ-1 (first action + where): "post a forge-visible PASS verdict comment on the GitHub issue using tracker.py ... step 5a ... before promoting test files, before touching or merging the PR, and before the pending-ship transition." CORRECT.
- CQ-2 (optional/mandatory): quoted "MANDATORY, ordered." CORRECT.
- CQ-3 (relationship to transition): "hard precondition ... never transition to pending-ship without a preceding forge-visible PASS verdict comment on the issue." CORRECT.
- CQ-4 (why private QA-RESULTS insufficient): "NOT committed to origin/main ... invisible to the DM ... blocks a genuinely-passing item at the ship-gate or forces an unverified ship." CORRECT.
- Result: 4/4 CORRECT -> comprehension is clear; logic derivable from the file alone.

CQ spec persisted at tests/comprehension/13464_spec.json.

## Meta-note

Fitting: this fix (verdict-before-transition) formalizes the exact behavior I adopted manually this session after #13464 was filed (my #13373 verdict comment had landed ~2 min AFTER the transition). Every subsequent verification (#13456/#13465/#13472/#13370/#13494) already posted the verdict comment before the transition — now it is a documented hard precondition.

## Decision

AC1 (functional ordering) + AC2 (comprehension 4/4) + AC3 (regression rationale) all satisfied. Prose-only edit; compose/static gate to be confirmed at merge. Zero gaps. -> PASS: verdict comment BEFORE transition + merge PR #13507 + Pending Ship.
