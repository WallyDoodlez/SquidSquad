# QA-RESULTS-11137 — Reverse #11049 Path A over-inlining (8 sub-skills → marker-pattern refs)

**Verified at**: 2026-06-05 cycle 943
**PR**: #11138 (squidsquad/task/11137 @ `86ddd0e93`)
**Net delta**: +290 / -2304 = **-2014 LOC across 14 files**.

## Verification

### Architectural delivery — all observable structural ACs PASS

- **8 sub-skills converted to marker-pattern references** in the 4 L1 orchestrators (`references/roles/{pm,dm,verifier,worker}/instructions.md`): `cycle-runner`, `context-pressure`, `resume-working-state`, `task-pickup`, `working-state`, `git-commit`, `agent-lifecycle`, `improvement-scan-slim`. Confirmed in qa composite: each appears once via `→ run sub-skill: <name>` (agent-lifecycle 2× because both worker and verifier orchestrators reference it).
- **`boot-bootstrap` stays inline** — only must-be-inline case per #11089 Change 3's "sub-skill criterion" (the agent doesn't know the marker convention until boot-bootstrap runs). 1 `<!-- sub-skill: boot-bootstrap -->` marker in qa composite.
- **Goal statements present** in the post-#11089 Change 2 orchestrator-content rule shape — marker-first ordering, goal-not-mechanics. Example (qa cycle-runner): "Goal: the cycle's input state has been captured (pull result, context pressure, working-state snapshot, queue state); the agent has aligned its creative work against that input; the cycle's outputs have been staged for durable commit and status propagation." Clean present-perfect phrasing per the DS-audit R1 fixup (commit `86ddd0e93`, dropped script names, dropped meta-instruction, unified tense).
- **`compose.py deploy-all`** succeeds: dm 860 / pm 920 / qa 862 / skill 983 (matches skill's reported sizes).
- **Regression sweep** (15-suite compose-area sweep: test_catalog + test_compose + test_manifest + test_installer_wiring + test_a3_golden_link_stage + test_event_mode_fragments + test_d2_link_stage_references) → **390/390 PASS in 5.70s**. Same baseline as #11087 R2 last sweep.
- **DS audit** completed (skill ran in background per `feedback_deepseek_review_async`); 3 findings on cycle-runner Goal (1 FLAG + 2 NIT, 0 BLOCK) — all addressed in `86ddd0e93`. Migration script preserved at `.squidsquad/skill/planning/migrate_11137.py` for auditability.

### AC ledger items flagged for PM (not blockers)

- **AC3 — `<!-- #10360-cleanup -->` markers preserved**: the 21 markers wrap D1-retired sub-skill bodies (status-line, agent-boundaries, file-conventions, responsibility, prohibitions) — not the 8 mandatory-inlines this task targets. Removing them would lose the #10360 future-work pointers documented in `docs/sub-skill-catalog.md`. Skill's call (preserve) matches the architectural intent; PM ledger entry only.
- **AC6 — size targets**: pm 920 / dm 860 / qa 862 (target ≤800) → over by 60–120 lines per role; skill 983 / target ≤1000 ✓. Skill's analysis is correct: the ≤800 target assumed all 9 sub-skills were inlined in all 4 roles, but pm/dm/qa only had 3 in-scope inlines each (worker had 6). Reality matched the architectural rule (boot-bootstrap inline + everything else referenced), not the pre-task planning estimate. PM judgment call — accept the realized sizes, or specify a follow-up to push further. Same shape as PM's AC3 relaxation on #11049 (≤1300 ceiling after measuring actual sizes).
- **Status-line scope drop**: the 9th item in the task scope had no source file post-#11087 (deleted with the orphan-sub-skill cleanup). The 4 `<!-- #10360-cleanup: inlined ... common/status-line -->` markers are D1-retired-style inlines (no catalog backing). Skill flagged this on pickup; per the issue body's "no catalog change" locked design, leaving them as inline D1-retired blocks is the correct read. PM ledger entry only.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

The architectural delivery — orchestrator-content rule applied per #11089 Change 3, -2014 LOC, 390/390 tests green — is complete. The two AC ledger items above are PM accounting questions about whether the realized numbers / scope drop match the pre-task estimates, not implementation gaps. Same pattern as #11049's AC3 relaxation; surfaced explicitly so PM can rule retroactively.
