Now I have a complete picture. Let me compile my analysis.

---

**Summary of review**: I examined all six changed files for correctness, regressions, contradictions in the QA path, and issues with the deferred-fixture decision. Here are my findings:

**Change 1 (PM ralph-loop-overview.md source)**: ✅ Phase enum has `test-planning` removed (line 37). The 'Test plan for #35' example is absent from the examples list (lines 43-49). The explanatory note on line 39 correctly references #9319 and explains QA now owns test plans. The composed PM CLAUDE.md (line 242) matches the source.

**Change 2 (QA verification.md source)**: ✅ The model_router.py route section (lines 157-168) correctly invokes `route --task-type test-plan` with the right arguments. The router script (`references/scripts/model_router.py`) supports this: `test-plan` is a valid task type (line 16), maps to `test-plan-model` config key (line 140), uses `test-plan.md.j2` template (line 541), and the `route()` function handles it (line 634). The composed QA CLAUDE.md (lines 550-561) matches the source. The instruction makes clear this is optional.

**Change 3 (PM fixture snapshots)**: ✅ The `pm_polling_CLAUDE.md` fixture has the phase enum updated on line 233 — no `test-planning`. The `pm_events_CLAUDE.md` fixture has no ralph-loop-overview section (event-driven), so no phase enum to update.

**Deferred-fixture decision**: The task explicitly excludes the pre-#9184 task-intake `test-planning` references in the fixtures (pm_polling line 1384, pm_events line 1533) as "separate hygiene issue." This is a reasonable scoping choice — those lines belong to the entire task-intake section that was rewritten by #9184 but the fixtures weren't refreshed. Changing them would require a full fixture refresh (not just the phase enum), which is correctly deferred. No contradiction found.

NO_FINDINGS