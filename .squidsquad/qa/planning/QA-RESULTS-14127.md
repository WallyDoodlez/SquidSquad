# QA-RESULTS-14127 -- PASS
| TC | Result | Evidence |
|----|--------|----------|
| TC1 | PASS | scratch install, pre-v2 schema (traversalBudget 5, project weight 0.1, tieBreak used 9.0, custom runbook type): wizard.install_vault_engine merged dedupThreshold 0.5, tieBreakWeights.walked/recency, types area/resource/decision/pattern/learning/rule/system/archive; user values byte-preserved (budget 5, weight 0.1, used 9.0, runbook identical); run 2 -> schema_merged [], file sha unchanged |
| TC2 | PASS | tests/test_vault_schema_merge_14127.py 12/12 (custom type + override fixture, atomic write, broken file reported, fresh install seeds) |
| TC3 | PASS | real engine vault-query.mjs --types rule --tags deploy: after merge -> [rule-qa-14127-probe]; negative control with the pre-v2 schema restored -> [] (the reported silent-empty rules lane) |
| TC4 | PASS | v0.45.0-to-v0.46.0.md gains a "Vault schema additions (#14127)" section; no new file so installer-files.txt correctly unchanged |
| TC5 | PASS | static gate 6598/0; receipts pass; merge-tree clean |
