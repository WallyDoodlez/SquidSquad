# TEST-PLAN-13860 (derived from PRD-VAULT-V2 P4 S4.1-S4.5 + PM's added S4.4 ACs on #13860/#14123)

- **TC1 -- S4.1 intake injection live**: throwaway issue; inject-context appends `## Vault context`; impressions attributed; re-run replaces (idempotent)
- **TC2 -- S4.2 lineage**: lineage-path / init-fix-plan (bug-flow fix-plan created lean); skeleton fails check-receipts
- **TC3 -- S4.2 receipts shapes**: cited, none-line, engine-unavailable, prose, empty, section missing
- **TC4 -- S4.2/S4.3 lineage in PR diff**: check-receipts --diff-base origin/main passes on the real PR; fails when file not in diff
- **TC5 -- S4.2 cite/used events**: cite writes used events per slug; unresolved slug writes none
- **TC6 -- S4.4 dedup**: dup subject->update; unrelated->create; content-tier only->create; archived/superseded->create; threshold override honored; probe writes zero telemetry
- **TC7 -- S4.3/S4.5 comprehension**: fresh-agent CQ over all changed instruction files (13860_spec.json, 10 Qs)
- **TC8 -- gate**: static gate on branch merged with main
- **TC9 -- merge readiness / consumption**: PR mergeable; sub-skill catalog + L1 vault slot consumption test

## Comprehension Questions
See tests/comprehension/13860_spec.json (Q1-Q10).
