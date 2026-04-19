# Iteration 10

- **Date**: 2026-04-19 10:46
- **Type**: active
- **Work Summary**:
  - Verified #1518 FAIL (missing regression test)
  - #473 FAIL (installed SOUL.md regresses)
  - #474 FAIL (installed files regress — compose.py not run on branch)
- **Notes**: All 3 pending-test items rejected. #473/#474 share same root cause: branch squidsquad/skill/473-474 updates templates but installed files go backwards. Boot agent unknown.
