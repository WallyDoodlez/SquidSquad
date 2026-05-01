### Step 2b — Implement Task (continued from Step 2)

_This step is reached when Step 2 (deterministic triage) picks a task from the work queue._

Print: `[🦑 HH:MM:SS] Implementing #[NUMBER]...`

1. Comment and transition status:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Picking up. Status → In Progress."
   python references/scripts/tracker.py transition [NUMBER] approved in-progress --role [ROLE]-lead
   ```
1b. **Branch checkout** (#3296): `python references/scripts/git_ops.py task-begin [ROLE] [NUMBER]` — checks out the task's feature branch if branch-workflow is enabled.
2. **Read planning artifacts** — PM creates these during task intake. Check both locations:
   - `.squidsquad/pm/planning/` (PM's planning directory — primary location)
   - `.squidsquad/[ROLE]/planning/` (your own planning directory — fallback)
   - Look for files matching the issue number (e.g. `FEAT-SKILL-195-CONTEXT.md`)
   - RESEARCH.md, CONTEXT.md, TEST-PLAN.md — respect locked decisions, note dev discretion areas
   - If PM comments reference planning artifacts but you cannot find them, **push back** (see Prohibitions)
3. Write working state: update `.squidsquad/[ROLE]/working-state.md` with `Task: #[NUMBER]`, status `in-progress`, planned approach, and acceptance criteria checklist.
4. Implement the task according to the acceptance criteria. Respect locked decisions from CONTEXT.md. Implement required side effect mitigations. Update working state as you complete sub-steps.
5. Run the test command: `[ROLE_TEST_CMD]`
6. **Run smoke tests** from TEST-PLAN.md (if it exists) before marking as Pending Test.
7. **Update docs**: Update only technical documentation (API docs, code comments, architecture notes). User-facing docs are handled by DM. If the change affects user-facing behavior, comment delivery notes on the Issue.
8. **Copy changed references to live**: If any files in `references/` were modified (e.g. `statusline.sh`, `hints-*.txt`, `agent-instructions.md`), copy them to the live `.squidsquad/` location so changes take effect immediately.
9. **Verify changes exist**: Run `python references/scripts/git_ops.py has-changes`. If output is `false`, do NOT transition — re-read the acceptance criteria and apply the implementation.
9b. **Self-verification reflection** — before marking pending-test, stop and critically review your own work:
   - **Regression**: Does this change break existing behavior? Read the code paths you touched — what else depends on them?
   - **Integration**: Does this work correctly with the current system setup? Is it compatible with config, compose, and the deployed state?
   - **Philosophy**: Does this violate any project philosophy, vault decisions, or established patterns?
   - **Personas**: Will this break workflows for any agent role (PM, QA, DM, human)? Think through each consumer of your change.
   If ANY of these checks reveal a concern — fix it before transitioning. Do not ship known concerns for QA to catch.
10. If tests and smoke tests pass and changes exist:
   - Transition status:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
     python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Implementation complete. All tests passing. Status → Pending Test."
     ```
   - `python references/scripts/git_ops.py task-end [ROLE] [NUMBER]` — return to working branch.
   - Clear working state.
11. If tests fail: fix the failure before changing status.
