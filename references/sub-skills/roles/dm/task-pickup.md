---
slot: instructions
ordinal: 20
roles: [dm]
---

### Task Pickup (Approved Tasks) — DM Override

Before role-specific work, check for approved tasks assigned to your role:

```bash
python references/scripts/tracker.py work-queue dm
```

If the queue returns an approved task:

1. Read the task: `gh issue view [NUMBER] --json title,body,labels,comments`
2. Transition to in-progress:
   ```bash
   python references/scripts/tracker.py transition [NUMBER] approved in-progress --role dm-lead
   python references/scripts/tracker.py comment [NUMBER] --role dm-lead --message "Picking up. Status -> In Progress."
   ```
3. **Branch checkout**: `python references/scripts/git_ops.py task-begin dm [NUMBER]`
4. Read planning artifacts if available (`.squidsquad/[PM_ALIAS]/planning/`).
5. Implement the task per acceptance criteria.
6. Run tests: `python tests/run_tests.py`
7. **Verify changes exist**: `python references/scripts/git_ops.py has-changes`
8. Transition to pending-ship (DM skips verifier — #6261):
   ```bash
   python references/scripts/tracker.py transition [NUMBER] in-progress pending-ship --role dm-lead
   python references/scripts/tracker.py comment [NUMBER] --role dm-lead --message "Implementation complete. Status -> Pending Ship."
   ```
9. Return to working branch: `python references/scripts/git_ops.py task-end dm [NUMBER]`

If the queue is empty, proceed to role-specific work (delivery scanning, etc.).
