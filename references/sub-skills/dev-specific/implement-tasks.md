### Step 3 — Implement Tasks

Print: `[🦑 HH:MM:SS] Checking tasks...`

**Issue gate**: Before picking up any task work, check for open issues assigned to your role:

```bash
python references/scripts/tracker.py list-issues [ROLE] --status open
```

If any open issues exist (non-empty result), **skip all task work this cycle** — issues always take priority. Print: `[🦑 HH:MM:SS] Open issues exist — skipping task pickup.` and proceed to Step 4.

**First, check for QA-rejected items** (higher priority than new work — fix existing before starting new):

```bash
python references/scripts/triage.py qa-rejected [ROLE] --json
```

This script deterministically detects in-progress items (both issues and tasks) with unaddressed QA/PM feedback. It returns a JSON array of items needing rework, each with `number`, `title`, `feedback_from`, `feedback_at`, and `feedback_summary`.

If the result is non-empty, pick up the first item:
1. Read the full QA feedback: `gh issue view [NUMBER] --json title,body,comments`
2. Write working state with `Task: #[NUMBER]`, status `in-progress`.
3. Fix each gap identified in the feedback.
4. Re-run tests and smoke tests.
5. Transition back to Pending Test:
   ```bash
   python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Fixed [N] QA gaps: [list]. Status → Pending Test."
   ```
6. Clear working state.

**Then, check for new approved tasks**:

```bash
python references/scripts/tracker.py list-tasks [ROLE] --status approved
```

Pick the highest-priority task (check `priority:high` first, then `priority:medium`, then `priority:low`). Read it: `gh issue view [NUMBER] --json title,body,labels,comments`

**Design label check**: If the issue has a `design:needed` or `design:in-progress` label, **skip it** — the designer agent has not completed the design yet. Move to the next task. Issues with `design:complete` or no design label are picked up normally.

When picking up a task, print: `[🦑 HH:MM:SS] Implementing #[NUMBER]...`

1. Comment and transition status:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Picking up. Status → In Progress."
   python references/scripts/tracker.py transition [NUMBER] approved in-progress --role [ROLE]-lead
   ```
2. **Read planning artifacts** (if they exist in `.squidsquad/[ROLE]/planning/`):
   - Look for files matching the issue number or title
   - RESEARCH.md, CONTEXT.md, TEST-PLAN.md — respect locked decisions, note dev discretion areas
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
