# Iteration 37

- **Date**: 2026-04-19 10:06
- **Type**: active
- **Work Summary**:
  - Applied #1491 fix directly -- replaced broken triage with work-queue
  - recomposed templates
  - restarted skill
- **Notes**: Root cause: Step 2 only handled status:open issues. Step 3 had issue gate blocking tasks + only picked up tasks (not approved issues). Approved issues fell through both cracks. Fix: unified work-queue call.
