# #12914 repair-status-labels — evidence (23:06:15)

Safe-by-default split (DS-12914 F1/F3):
- SAFE (carries status:shipped = delivered): repaired by default.
- AMBIGUOUS (no status:shipped, possible #9837 closed-but-undelivered): SKIPPED unless --include-unshipped.

## APPLIED this session: the 6 safe (shipped-carrying) issues
Removed leftover status:pending-ship (and status:approved on #9873) from:
  #9898, #9890, #9882, #9873, #3027, #2724 -> each now single-status (status:shipped).
Verified live: #9873 was approved+pending-ship+shipped -> now [status:shipped].

## DEFERRED to DM: 198 ambiguous (no status:shipped)
Routed to DM (queue owner) — run 'repair-status-labels' (dry-run) to review,
then '--apply --include-unshipped' once confirmed none are awaiting delivery (#9837).

## Post-apply dry-run (safe set drained, ambiguous held):
```
#12914 status-label repair (DRY-RUN): 0 closed issue(s) to repair, 198 ambiguous (no status:shipped) SKIPPED.
  SKIPPED 198 closed pending-ship issue(s) with NO status:shipped � each MAY be a legitimate closed-but-undelivered issue (#9837: PR auto-close before DM ships). Verify none are awaiting delivery, then re-run with --include-unshipped to strip them: #10133, #10101, #10072, #10007, #9965, #9481, #9474, #9358, #9357, #9331, #9319, #9318, #9272, #9265, #9242, #9184, #8950, #8949, #8918, #8917 (+178 more)
```
