# QA-RESULTS-13861 -- REJECT round 1 (3 findings)

| TC | Result | Evidence |
|----|--------|----------|
| TC1 | PASS | two real isolated harnesses from the branch (ports 7481/7482): ids 00de5353-... vs adb8778e-... |
| TC2 | PASS | killed + relaunched harness A: /status id and file byte-identical |
| TC3 | PASS | /status.harness.instance_id present; .gitignore:3 matches .squidsquad/.instance-id (and :5 .vault-maintenance.json) |
| TC4 | PASS (test-pinned) | distribution is production-only; live fleet not restarted (running harness predates code, same as #14095) -> covered by TestInstanceIdDistribution; no engine (.mjs) files touched so P3 shard read-sum unchanged |
| TC5 | PASS | forced POST /maintenance/vault-optimize -> total_due 180, queued 20, one vault-maintenance event target_alias pm; scheduler fired by itself at T+300s on fresh harness B; state 25h old reads overdue; analyze-queue oldest/never-optimized first |
| TC6 | FAIL | live file-contradiction twice back-to-back: run 1 filed #14139, run 2 filed #14140 (duplicate). Dedup reads `tracker list-by-labels type:task,role:pm` which lags create by several seconds: with +3s and +6s gaps it still double-filed, at +25s it correctly deduped ("open task already exists"). Vault diff 0 lines (never applies). propose_prunes 178 proposals. (Live artifacts #14139-#14143 closed.) |
| TC7 | PASS | composed pm CLAUDE.md line 671 carries the vault-maintenance flow; Case E line 105; catalog row 133 |
| TC8 | FAIL (f) | fresh sonnet: (a)(b)(c)(d)(e) correct; (f) "non-PM agent receives vault-maintenance" -- the contract does not say; agent only inferred skip+ack from the care-filter text and noted Case E bullet reads as an instruction with no non-PM exception |
| TC9 | FAIL | static gate 6586 gated, 1 failure test_no_silently_stale_comprehension_specs on the merged-with-main tree (also on the branch alone): 11 stale pairs (10678<-sub-skill-catalog.md, 12451/13335/14099/14109/8694<-event-mode-contract.md, 13327/13746<-pm/instructions.md, 13860<-vault-optimize.md, 9873<-event_catalog.py+harness.py). Keyword scan: none of those specs' questions touch the changed content, so refresh is valid. Merge-tree vs main clean. Worker tests 42 passed (comment claimed 43). Receipts pass. |

---
# Round 2 -- PASS (PR #14138 @ 9b15a7932)
| TC | Result | Evidence |
|----|--------|----------|
| TC1-TC5,TC7 | PASS | unchanged from round 1 (harness/scheduler/AC4 code paths not modified by fixes) |
| TC6 | PASS | live: same pair filed 3x back-to-back -> 1 filed (#14146), 2 duplicates via ledger; reversed slug order also dedupes; ledger gitignored (.gitignore:7); vault diff 0; #14146 closed |
| TC8 | PASS | fresh agent a-f all correct; (f) now states care-filter skip + ack-cursor from the contract text |
| TC9 | PASS | static gate 6623/0; worker tests 45/45; merge-tree vs origin/main clean |
