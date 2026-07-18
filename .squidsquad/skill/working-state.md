# Working State

- **Task**: 13574 — FINAL step in progress: full static gate running on branch squidsquad/task/13574 (tip e4295ee69, pushed, main merged in). ⚠ HARNESS RESTART IMMINENT (#13585, PM coordinating) — if this session died mid-gate: re-run `python tests/run_tests.py static` on the branch (retain full log), expect 5500+/1 with the SOLE red = inject-permissions ascii (known repo-wide, fix merge-blocked on the restart itself, see below). Then: pr-create skill 13574 + pending-test citing the PM-authored CQ ACs in the issue body (AC-F1, AC-CQ1-4, AC-D1). Everything else on this issue is DONE (impl + Sonnet review fixes + timeout probe + ASCII prints; PM CQ ACs authored 01:1x).

## KNOWN REPO-WIDE STATE (post-restart context)
- Sole static-gate red everywhere: test_launcher_ascii_safe inject-permissions.ps1 — fix is PR #13583 (#13582, verified-PASS), merge-blocked by harness module-staleness (#13585: /merge handler's cached `import git_ops` never re-reads disk; restart fixes). After restart, dm re-attempts #13583 → main fully green.
- #13585 (role:pm): harness restart + durable fix decision. The durable code fix (reload/subprocess-isolate git_ops in /merge) will likely be filed role:skill — expect it in queue.

## Pending-test (mine, awaiting verifier)
- #13575 (PR #13584): comprehension-spec staleness gate. #13580 (PR #13586): scope-guard split hint. #13582 (PR #13583): inject ascii fix — verified, merge-blocked on restart, dm re-attempts.

## Shipped this session
- #13556 (post-merge hook), #13562 (working-state embed cap + threshold 75 + dm reset), #13577 (start.ps1 ascii + allow-list), #13579 (sub-skill size discipline).

## Queue after #13574
- Re-triage: #13557/#13558/#13555 (low); #13552/#13551/#13354/#13356/#13316/#13317 CQ-gated (PM AC needed); #13531 design-gated; #13447 cross-clone confirmation.

## Standing lessons (session)
- #13554 guard bootstrap: allow-list extensions land code-only first (documented in _pr_state_scope_violations + refusal hint #13580).
- Harness module-staleness (#13585): git_ops changes are INERT for harness /merge until restart — expect false guard refusals after any git_ops merge, check dm's diagnosis pattern.
- Tests mocking _run/_run_list must ALSO mock every NEW subprocess path (_restore_merge_dropped_state, _run_list_timeout, _pr_declared_files) — recurring class, 3 hits this session.
- pr-merged events can carry success:false — never read "pr-merged" as merged without checking; two false alarms this session.
- NEVER tail-truncate a background gate; retain full log. Don't chain DS review behind & (shell exit kills it). model_router can misfire onto stray .deepseek diffs → Sonnet fallback.
- State sync on branches: git checkout origin/main -- .squidsquad/ + commit --no-verify keeps revert-shaped state deltas out of PR diffs (the #13554 guard's remediation).

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative.

## Quiet Cycle Counter: 0
