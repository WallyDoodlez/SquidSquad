# Iteration 399

- **Date**: 2026-04-27 10:10
- **Type**: active
- **Work Summary**:
  - Fixed #3493 — duplicate ROLE_AUTHORITY keys in tracker.py silently dropped PM authority for pending-human-review. Three fixes: removed duplicate LEGAL_TRANSITIONS key
  - merged ROLE_AUTHORITY entries to {pm
  - _assignee}
  - fixed _check_authority to support mixed auth sets. PR #3566. 1103 tests green.
- **Notes**: none
