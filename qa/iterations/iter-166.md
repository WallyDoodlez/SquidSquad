# Iteration 166

- **Date**: 2026-05-08 21:06
- **Type**: active
- **Work Summary**:
  - Verified #6222 (auto-merge closes issues before DM delivery) — PASS. Root cause: list_by_labels hardcoded --state open. Fix: state parameter + DM/PM queries use --state all. 3 regression tests. PR merged. Skipped #6126 (blocked:human-action). All agents healthy.
- **Notes**: none
