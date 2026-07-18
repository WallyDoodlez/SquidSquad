# Working State

- **Task**: 13574 — write-outage detection. Implementation COMMITTED on branch squidsquad/task/13574 (3e470fd06, pushed? NO — branch not yet pushed/PR'd). Blocked-in-flight on: (a) DS review r2 (background b6dqwicz9), (b) PM CQ AC (asked on issue — health-check.md + pipeline-sentinel.md are instruction files), (c) 1 unexplained static-gate failure on the branch (log lost to tail-truncation; re-gate after merging main once #13577 merges — main's 3 launcher-test failures pollute branch gates until then).

## PENDING FOLLOW-UP (do not lose)
- **On PR #13576 (#13562) merge event**: bump config.md Context Threshold 70 -> 75, direct-to-main.
- **#13574**: after #13577 merges, merge main into branch, re-run full static gate (retain log — no tail-3!), apply DS r2 findings, then pending-test ONLY once PM's CQ AC lands.

## Pipeline (mine)
- #13556 SHIPPED (PR #13560 merged; post-merge hook live fleet-wide).
- #13577 pending-test (PR #13578): launcher ASCII fix, byte-parity with primary clone; also added inject-permissions.ps1 to _is_launcher_script allow-list.
- #13562 pending-test (PR #13576): working-state embed size gate. dm reset DONE (50bb6b323); pm self-cleaned, no reset.

## Queue after #13574
- #13575 (low, improvement-scan): comprehension-spec staleness check.
- Then re-triage: #13557/#13558/#13555 (low); #13552/#13551/#13354/#13356/#13316/#13317 CQ-gated; #13531 design-gated; #13447 cross-clone confirmation needed.

## Standing lessons (session additions)
- merge=ours/union only protects modify-vs-modify; modify-vs-DELETE drops (fixed by #13556 hook). #11511 guard unstages .squidsquad/ on branches. Backticks in tracker --message bash-substitute. MSYS mangles origin/main slash. State/vault = main-only. TestPull-class suites MUST patch _restore_merge_dropped_state. NEVER tail-truncate a background static gate's output — retain the full log. Don't chain a DS review behind another command with & (shell exit kills it); one background task per gate.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative.

## Quiet Cycle Counter: 0
