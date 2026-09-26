# TEST-PLAN-14109 (derived from issue-body ACs)

| TC | AC | Check |
|----|----|-------|
| TC1 | AC1 | `git grep -n -i "retrying `bootup-complete`\|keeps retrying" -- references/ docs/` returns 0 hits; both fragments describe one path |
| TC2 | AC2 | composed qa CLAUDE.md still has `run sub-skill` markers for event-driven-workflow + event-mode-contract (2) |
| TC3 | AC3a-c | fresh-agent CQ over both fragments (tests/comprehension/14109_spec.json) |
| TC4 | AC4 | 8694_spec.json updated questions answered correctly by fresh agent from its 5 files; no degraded-mode/auto-cursor expectations remain |
| TC5 | gate | merge-readiness vs origin/main; comprehension staleness check; full static gate |

## Comprehension Questions
See tests/comprehension/14109_spec.json (Q1-Q3).
