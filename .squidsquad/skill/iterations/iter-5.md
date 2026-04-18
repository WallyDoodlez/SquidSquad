# Iteration 5

- **Date**: 2026-04-18 15:35
- **Type**: active
- **Work Summary**:
  - Fixed #1345: watcher job relative paths → absolute via Join-Path
- **Notes**: PowerShell Start-Job runs in $HOME, not repo root. Changed 8 path defs to Join-Path $repoRoot. Deployed to all 5 roles. PR #1356.
