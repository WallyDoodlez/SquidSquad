# Iteration 402

- **Date**: 2026-04-27 11:36
- **Type**: active
- **Work Summary**:
  - Implemented #605 — auto-expand #NNN issue references to full URLs in tracker comments. Added _get_repo_url() and _expand_issue_refs() to tracker.py. Reads repo URL from config.md
  - expands in comment() with word-boundary-aware regex. PR #3605. 10 feature tests + full suite green.
- **Notes**: none
