# QA-RESULTS-14124 / 14125 -- REJECT (merge-readiness only; back to in-progress)

| TC | Result | Evidence |
|----|--------|----------|
| TC1 | PASS | delivery-packaging.md:74 now `pending-ship in-progress --role dm-lead`; _check_authority(pending-ship->in-progress, dm-lead) True |
| TC2 | PASS | _check_authority(in-progress->approved): pm-lead True; dm-lead/verifier-lead/qa-lead False |
| TC3 | PASS | own scanner: 22 literal transition commands in references/**/*.md, 0 illegal/unauthorized |
| TC4 | PASS | 34/34 on branch; pre-fix files restored from origin/main -> 3 failed (dm route-back x2, pm stalled-task) |
| TC5 | PASS | static gate 6577/0 on branch |
| TC6 | FAIL | `git merge-tree HEAD origin/main` CONFLICT in tests/comprehension/.staleness-baseline.json. Cause: QA commit 98d872817 (#14109) refreshed the same 12818_spec/9184_spec entries plus added 14109_spec; PR #14134 refreshed 12818/9184 too. |

---
# Round 2 -- PASS (PR #14134 @ b61bb1161)
TC1-TC5 unchanged from round 1 (re-run: 44/44 incl. staleness gate). TC6 PASS: merge-tree vs origin/main clean; static gate 6577/0.
