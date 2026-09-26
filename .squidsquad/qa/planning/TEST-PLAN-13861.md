# TEST-PLAN-13861 (derived from issue-body AC1-AC5)

| TC | AC | Check |
|----|----|-------|
| TC1 | AC1a | two harness instances (distinct SQUIDSQUAD_DIR) hold distinct ids |
| TC2 | AC1b | restart leaves id byte-identical |
| TC3 | AC1d/e | /status reports id; `git check-ignore .squidsquad/.instance-id` |
| TC4 | AC1c + upgrade | production clone distribution; read-summed shards untouched |
| TC5 | AC2 | window fires (scheduler on its own, forced POST), emits one vault-maintenance event to pm iff queue non-empty; queue rules |
| TC6 | AC3 | seeded contradiction -> exactly one pending task; second run files nothing new; zero vault diff; prune proposals; mark-optimized excludes |
| TC7 | AC4 | compose pm carries event-triggered prose; Case E lists vault-maintenance; catalog row updated |
| TC8 | AC5 | CQ 13861_spec.json (a-f) fresh agent |
| TC9 | gate | static gate on merged-with-main tree; merge-readiness |
