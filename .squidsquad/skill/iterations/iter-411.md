# Iteration 411

- **Date**: 2026-04-27 18:29
- **Type**: active
- **Work Summary**:
  - Fixed #3643 (sandbox path check bypass). Replaced str.startswith() with Path.is_relative_to() in model_router.py. Added 2 regression tests. PR #3694.
- **Notes**: none
