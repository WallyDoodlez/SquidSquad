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
4. **Branch checkout**: `python references/scripts/git_ops.py task-begin [ROLE] [NUMBER]`
5. Read planning artifacts if available (`.squidsquad/pm/planning/`).
6. Implement the task per acceptance criteria.
7. Run tests: `python tests/run_tests.py`
8. **Verify changes exist**: `python references/scripts/git_ops.py has-changes`
9. Transition to pending-test:
   ```bash
   python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Implementation complete. Status -> Pending Test."
   ```
10. Return to working branch: `python references/scripts/git_ops.py task-end [ROLE] [NUMBER]`

If the queue is empty, proceed to role-specific work (delivery scanning, verification, etc.).
