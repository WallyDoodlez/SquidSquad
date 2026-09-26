# Working State

- **Task**: #14162 (instruction-changing bugs skip intake / no CQ ACs). Then #14136.
- #14137: pending-test, PR #14163.
- #14147: pending-test, PR #14161.
- #14151: pending-test, PR #14159. #14150: pending-test, PR #14160.
- #14114: pending-test, PR #14158 (gate PASS 6628, DS r1+r2 fixed; 14099/14109 specs superseded_by 14114; verifier authors 14114_spec).
- #14127: SHIPPED (PR #14156).
- #14131 + #14132: SHIPPED (PR #14152). Live proof needs a harness restart.
- #14144: PR #14149 merged; diagnostic.lock untracked on main. The AC6 live proof follows the next harness restart.
- #13862: pending-human-review (M3 operator gate). The manifest is on main at .squidsquad/skill/planning/13862-m2/ (186 entries incl. the post-M0 note). Tooling PR #14145 is on HOLD. Vault writes are FROZEN (Writes Per Cycle 0) until M4. On approval: rebuild from current main, run M1 + apply, reconcile (185 M0 + 1 post-M0), then pending-test.
- SHIPPED this session: #14109, #14124, #14125, #13861, #14144.

## Queue after
- #14136, #14133, #14130, #14128. Approved but human-gated: #10690, #10686.

## Notes
- DeepSeek is live again (#14148 closed). Review inputs MUST be inside the repo (e.g. .squidsquad/tmp/review-N/). Paths outside it are silently skipped and come back NO_FINDINGS, which is the #14150 bug.
- Push with the `gh auth token --user WallyDoodlez` credential helper to `HEAD:refs/heads/<branch>`. git_ops push fails when the upstream is origin/main.
- Run the static gate and staleness refresh only on the COMMITTED tree (memory: feedback_static_gate_on_committed_tree).
- Heredocs mangle backslashes: use Write/Edit for any content with \n.

## Improvement Scan
Status: idle. Last scan 2026-07-19 05:52.

## Quiet Cycle Counter: 0
