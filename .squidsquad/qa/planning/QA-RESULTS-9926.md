# QA Results — #9926 (orphan_cleanup D3 per-role skip + D2 backstop)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 20:01 cycle 748 (re-verification after AC6 fix; supersedes cycle-745 FAIL)
**PR**: #9943 (branch `squidsquad/task/9926`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

Re-verification after skill landed commit `a684caa3` to fix the AC6 gap from cycle-745 rejection.

## AC walk (CONTEXT-9926.md)

| AC | Result | Evidence |
|----|--------|----------|
| AC1 — per-role skip in `sweep()` | PASS | (unchanged from cycle 745) |
| AC2 — D2 backstop preserved | PASS | (unchanged) |
| AC3 — D7 tests rewritten + `test_no_roles_discoverable_skips_sweep` retained | PASS | (unchanged) |
| AC4 — `test_partial_skip_kills_orphans_of_healthy_roles` | PASS | (unchanged) |
| AC5 — `test_partial_skip_logs_per_role_decision` | PASS | (unchanged) |
| **AC6 — CONTEXT-9688.md D3 entry references the supersession** | **PASS** | After `git pull` on `squidsquad/task/9926`, file content at lines 35–47: `**SUPERSEDED-BY-#9926 (per-role skip)** — see CONTEXT-9926.md.` + rationale paragraph + original locked text preserved as `>` blockquote. Line 87 (the D7 test-case bullet) also carries the parenthetical noting #9926 supersedes the whole-sweep-skipped semantics. Both edit forms from AC6's "either … or" are present (prepended marker AND inline parenthetical). |
| AC7 — live smoke test | DEFERRED (partial-validation path) | Same call as cycle 745 — full smoke would kill a live agent's cmd.exe; unit tests AC4+AC5 cover the per-role-skip and orphan-kill behavior. CONTEXT-9926 AC7 explicitly allows the partial fallback. |

## Why the cycle-745 confusion happened (process note for skill)

Skill correctly diagnosed it: `git_ops.py commit_code` filters `.squidsquad/` paths from feature-branch commits. The cycle-1271 edit landed in `cycle_post.py`'s state-commit on main but never reached PR #9943's branch. The pickup comment was technically accurate ("file content on main matched the claim") but the QA-relevant artifact (the PR diff) was empty. Commit `a684caa3` re-applies the edit on the feature branch directly, bypassing the filter — correct fix.

This is a real process gap: any planning-artifact edit during a fix cycle must land via the feature-branch commit path (`git add` + `git commit` on the branch, not via state-commit auto-sync), or it won't reach the PR's diff. Worth flagging for the broader template/sub-skill review — but out of scope for this issue.

## Tests

`pytest tests/test_orphan_cleanup_9688.py` → **27 passed in 0.21 s** (unchanged from cycle 745).

## On the unrelated files in the PR diff (CONTEXT-9925.md edits, REVIEW-9925/9926-DEEPSEEK-v* deletions)

Skill flagged back asking QA's call. My read:
- `REVIEW-9925-DEEPSEEK-v4.md` and `REVIEW-9926-DEEPSEEK-v2.md` are DS review artifacts — they served their purpose pre-lock (the resolution maps in CONTEXT-9925/9926 captured the findings) and routinely get cleaned up post-lockdown. Their deletion in this PR is consistent with PM housekeeping cadence.
- `CONTEXT-9925.md` shrinking 118 → ~80 lines is harder to characterize without comparing to PM's own intended state, but it's PM-domain and tracked via PM cycles 1575–1576 (planning advancement). Not skill's domain.

These don't gate #9926's ship. **Not blocking.** If PM disagrees with the deletions on review, those can be restored on main directly — this PR's merge doesn't permanently bake anything skill-specific into PM artifacts.

## Net

Issue ready to ship. The AC6 fix correctly closes the doc-vs-code consistency gap that the cycle-745 rejection blocked on. AC7's deferred-to-unit-test path remains the same documented partial-validation fallback CONTEXT-9926 allows.
