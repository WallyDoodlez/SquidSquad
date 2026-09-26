# TEST-PLAN-14127 (derived from issue-body AC1-AC4)
| TC | AC | Check |
|----|----|-------|
| TC1 | AC1 | install_vault_engine on a pre-v2 schema adds rule type + dedupThreshold, preserves custom type + overrides; idempotent |
| TC2 | AC2 | fixture test with custom type + non-default override passes |
| TC3 | AC3 | seeded rule-* note surfaced by rules lane after upgrade (negative control before) |
| TC4 | AC4 | migration note; installer-files.txt unchanged (no new file) |
| TC5 | gate | static gate, receipts, merge-readiness |
