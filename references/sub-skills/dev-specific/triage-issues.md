### Step 2 — Pick Up Work (Deterministic Triage)

Print: `[🦑 HH:MM:SS] Checking work queue...`

**First, check for QA-rejected items** (highest priority — fix existing before starting new):

```bash
python references/scripts/triage.py qa-rejected [ROLE] --json
```

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
6. Clear working state. Proceed to Step 4.

**If no QA-rejected items, use the deterministic work queue**:

```bash
python references/scripts/tracker.py work-queue [ROLE]
```

This returns a unified, priority-sorted list of ALL actionable items (issues AND tasks). Priority order is enforced by the script:
1. In-progress items (resume first)
2. Approved issues — severity:high → medium → low
3. Approved tasks — priority:high → medium → low
4. Open issues — severity:high → medium → low

**You MUST pick the first item in the queue.** No discretion to skip, reorder, or cherry-pick. The queue is deterministic — the script decides priority, not you.

If the queue is empty, print: `[🦑 HH:MM:SS] No actionable work in queue.` and proceed to Step 4.

If the queue returns an item, read it: `gh issue view [NUMBER] --json title,body,labels,comments`

**Design label check**: If the item has a `design:needed` or `design:in-progress` label, skip it and pick the next item in the queue.

**For issues** (type:issue):
1. Write working state: update `.squidsquad/[ROLE]/working-state.md` with `Task: #[NUMBER]`, status `in-progress`.
2. Transition: `python references/scripts/tracker.py transition [NUMBER] [CURRENT_STATUS] in-progress --role [ROLE]-lead`
3. Comment: `python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Picking up. Status → In Progress."`
4. Read the issue details, locate the relevant code, fix the issue.
5. Run the test command: `[ROLE_TEST_CMD]`
6. **Verify changes exist**: Run `python references/scripts/git_ops.py has-changes`. If output is `false`, do NOT transition — re-read the issue and apply the fix.
7. If tests pass and changes exist:
   - Transition: `python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead`
   - Comment: `python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Fixed in commit [hash]. [Brief explanation]. Status → Pending Test."`
   - Clear working state.
8. If the root cause belongs to another agent's domain:
   - File a new issue to the correct role.
   - Comment on the original with cross-reference.
   - Clear working state.

**For tasks** (type:task): Follow the task implementation flow below (Step 2b).
