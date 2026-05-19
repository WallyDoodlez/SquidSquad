## File Conventions

- Your issues and tasks: GitHub Issues with `role:[ROLE]` label (queried via `python references/scripts/tracker.py list-issues/list-tasks`)
- Your iteration logs: `.squidsquad/[ROLE]/iterations/iter-N.md`
- Your working state: `.squidsquad/[ROLE]/working-state.md`
- Your planning artifacts: `.squidsquad/[ROLE]/planning/`
- PM planning artifacts (RESEARCH.md, CONTEXT.md): `.squidsquad/pm/planning/` — under the #9184 workflow PM no longer produces TEST-PLAN.md
- QA planning artifacts (TEST-PLAN-<NUMBER>.md, QA-RESULTS-<NUMBER>.md, TEST-<NUMBER>-tests.py): `.squidsquad/qa/planning/` (#9184)
- Config (read-only except ship counter): `.squidsquad/config.md`
- Cross-filing: create GitHub Issues with `role:[OTHER_ROLE]` label
