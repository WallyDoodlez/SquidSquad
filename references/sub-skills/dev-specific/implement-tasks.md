### Step 2b — Implement Task (continued from Step 2)

_This step is reached when Step 2 (deterministic triage) picks a task from the work queue._

Print: `[🦑 HH:MM:SS] Implementing #[NUMBER]...`

1. Comment and transition status:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Picking up. Status → In Progress."
   python references/scripts/tracker.py transition [NUMBER] approved in-progress --role [ROLE]-lead
   ```
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
10. If tests and smoke tests pass and changes exist:
   - Transition status:
     ```bash
     python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
     python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Implementation complete. All tests passing. Status → Pending Test."
     ```
   - Clear working state.
11. If tests fail: fix the failure before changing status.
