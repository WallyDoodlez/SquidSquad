# Iteration 364

- **Date**: 2026-04-26 17:33
- **Type**: active
- **Work Summary**:
  - Fixed #3347 (high) — boot_remote.py inter-process lock via .booting sentinel. Written before spawn
  - checked by _needs_boot()
  - auto-cleaned if stale. 10 regression tests. 983 tests green.
- **Notes**: none
