---
slot: instructions
ordinal: 10
---

### Task Pickup (Approved Tasks)

Before role-specific work, check for approved tasks assigned to your role:

```bash
python references/scripts/tracker.py work-queue [ROLE]
```

If the queue returns an approved task (not just role-specific items like pending-ship or pending-test):

1. Read the task: `gh issue view [NUMBER] --json title,body,labels,comments`
2. **Design label check**: If `design:needed` or `design:in-progress`, skip — wait for designer.
3. Transition to in-progress:
   ```bash
   python references/scripts/tracker.py transition [NUMBER] approved in-progress --role [ROLE]-lead
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Picking up. Status -> In Progress."
   ```
4. **Adopt the plan-seeded branch** (#12750): `python references/scripts/git_ops.py task-begin [ROLE] [NUMBER]`. PM seeded `squidsquad/task/[NUMBER]` with the plan as **commit 1** and opened a draft PR — `task-begin` checks out that **existing** local/remote branch. Do **NOT** create a fresh branch; your implementation commits ride on top of the plan commit (the plan and the code that fulfils it merge to `main` together).
5. Read the plan: the committed plan body `.squidsquad/[PM_ALIAS]/planning/[NUMBER]-body.md` (commit 1 on this branch) is the source of truth for the spec. (RESEARCH.md / CONTEXT.md were PM's planning inputs that informed this plan; they are NOT committed to the task branch and you do not need to locate them.)
6. Implement the task per acceptance criteria.
7. Run tests: `python tests/run_tests.py`
8. **Verify changes exist**: `python references/scripts/git_ops.py has-changes`
9. Transition to pending-test:
   ```bash
   python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Implementation complete. Status -> Pending Test."
   ```
10. **Flip the draft PR to ready** for review (`python references/scripts/git_ops.py pr-ready [PR_NUMBER]` — canonical; routes through the forge adapter, unlike bare `gh pr ready`), then return to working branch: `python references/scripts/git_ops.py task-end [ROLE] [NUMBER]`

If the queue is empty, proceed to role-specific work (delivery scanning, verification, etc.).
