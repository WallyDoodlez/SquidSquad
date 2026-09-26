# TEST-PLAN-14124 / 14125 (derived from issue bodies' Observation + Suggested fix; no formal ACs)

| TC | Source | Check |
|----|--------|-------|
| TC1 | #14124 | delivery-packaging.md citation-gate route-back command is executable (legal edge + DM authority) |
| TC2 | #14125 | pipeline-sentinel Tier 1 `in-progress -> approved --role pm-lead` executes (PM authorized; other non-assignee roles still rejected) |
| TC3 | both (class) | independent scan of every literal `tracker.py transition ... --role X-lead` in references/**/*.md vs LEGAL_TRANSITIONS + ROLE_AUTHORITY |
| TC4 | gate | new tests/test_doc_transitions_14124.py passes on branch and FAILS on pre-fix tracker.py + delivery-packaging.md (negative control) |
| TC5 | gate | full static gate |
| TC6 | gate | merge-readiness vs origin/main |
