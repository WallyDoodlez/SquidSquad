# QA-RESULTS-14109 — REJECT (back to in-progress)

- TC1/AC1 PASS: git grep for "retrying `bootup-complete`"/"keeps retrying" over references/ docs/ = 0 hits (branch and merged-with-main tree). Both fragments describe one path.
- TC2/AC2 PASS: composed qa CLAUDE.md carries 2 run-sub-skill markers (event-driven-workflow, event-mode-contract).
- TC3/AC3 PASS: fresh sonnet agent, both fragments only, 14109_spec.json Q1-Q3 (a,b,c) all correct.
- TC4/AC4 PASS (content): fresh agent on 8694 updated Q1,2,3,7,8,10,11,12: all consistent with expected/must_not. Note Q8 expected cites boot-bootstrap polling detail not present in the 5 spec files; agent answer still compatible.
- TC5 FAIL: PR #14111 branch is not merge-ready. `git merge origin/main` conflicts in tests/comprehension/.staleness-baseline.json (both sides changed the event-mode-contract.md hash; main's #14099 also edited that fragment). Conflict is in tests/, not .squidsquad/ state, so not verifier-resolvable. After merge the baseline hash for event-mode-contract.md (12451, 13335, 8694, 9742, 14099 entries) must be regenerated on the merged fragment, plus 14109_spec.json entry.
- Finding 2 (minor): event-mode-contract.md Case A header still says "boot sequence MUST work even when the harness is unreachable. Forge access is the only hard prerequisite" while step 3 says reachability is guaranteed and the new recovery section says end the session; a fresh agent flagged the tension.

---
# Round 2 -- PASS (PR #14111 @ a83f52252)

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 | PASS | `git grep -n -i "retrying \`bootup-complete\`\|keeps retrying" -- references/ docs/` exit 1 (0 hits); both fragments state one path; Case A header reconciled (round-1 finding 2 fixed) |
| TC2 | AC2 | PASS | composed qa CLAUDE.md carries 2 run-sub-skill markers (event-driven-workflow, event-mode-contract) |
| TC3 | AC3 a/b/c | PASS | fresh sonnet agent, both fragments only: Q1 ceiling->Monitor ends->session ends, no retry/pivot; Q2 boot-phase loss ends session, never skip bootup-complete; Q3 health poller / operator / polling on next boot |
| TC4 | AC4 | PASS | fresh agent on 8694 (Q1,2,3,7,8,10,11,12) answers match updated contract; no degraded-mode/auto-cursor expectations remain |
| TC5 | gate | PASS | `git merge-tree HEAD origin/main` clean, PR MERGEABLE/CLEAN; static gate 6351/0 on rerun (first run 1 failure in test_13373 TestFastForwardStashGuardRealGit13819, passed alone and on full rerun -- transient, real-git test raced my concurrent git commands) |
