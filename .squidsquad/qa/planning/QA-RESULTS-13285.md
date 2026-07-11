# QA-RESULTS-13285 — Post-merge scope-audit + auto-revert safety net

**Verdict: PASS — zero gaps.** PR #13288 merged (squash, +additions-only). The robust complement to #13271 — it automates the exact manual recovery DM did for the #13269 SEV-1 I caused.

## AC walk (independent)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | detects a merge deleting files outside the PR's declared changed-set; clean merges pass untouched | PASS — `_scope_audit_violations = deleted − declared`; **proven against the actual #13269 incident** (flags config.md + composed CLAUDE.md + vault); no false positive on clean/in-scope merges |
| AC2 | auto-revert non-destructive (revert commit, never force-push) + idempotent | PASS — `git revert --no-edit` + push; push-failure undoes the local revert; `test_auto_revert_is_non_destructive_revert_then_push` |
| AC3 | fail-SAFE on uncertainty (FLAG, don't guess); FILE-deletions only (not line-level — #13271 was 194 FILE deletions) | PASS — `None` on gh/git uncertainty → never auto-revert; `git show --diff-filter=D` (file-level); rename old-path not a violation |
| AC4 | emits a loud incident comment so a human/DM can confirm | PASS — `test_audit_violation_emits_incident_no_revert_when_off` |
| (rollout) | auto-revert DEFAULT OFF — ships defused (detect+alert) until trusted | PASS — `SQUIDSQUAD_MERGE_AUTO_REVERT=1` opts in; `test_auto_revert_flag_default_off` |

## Evidence
- Code (git_ops.py +366): `_pr_declared_files`, `_merge_deleted_files` (`git show --diff-filter=D`), `_scope_audit_violations` (deleted − declared, None→fail-safe), `_post_merge_scope_audit` (detect + incident comment + opt-in revert, never raises), `_merge_auto_revert_enabled` (default OFF).
- skill tests (test_git_ops.py): 28 — violations-are-deleted-minus-declared, clean-no-violations, fail-safe-when-unknown, default-off, flag-on, emits-incident, auto-reverts-when-on, fail-safe-inconclusive, never-raises, **non-destructive-revert-then-push**, rename-not-violation, checkout/push/revert failure handling, config.md case. All PASS.
- **QA independent test** (`tests/test_feat_13285_scope_audit_catches_sev1.py`): replays the ACTUAL #13269 incident shape (declared TUI files vs 194 out-of-scope deletions) → flags exactly the out-of-scope files; clean +additions and in-scope-deletion → no false positive; undeterminable declared → None (fail-safe). **Proves the net would have caught the SEV-1 I caused.**
- +additions-only; deterministic harness/git code → no CQ.

## Note
Together with #13271 (pre-merge >50-behind refusal) this gives two-layer protection against the behind-clone stale-tree mass-revert: the threshold heuristic blocks the obvious case; this post-merge audit catches what the threshold misses (a <50-behind merge that still reverts out-of-scope files) by checking what the merge ACTUALLY did. Ships defused (detect+alert) for a safe production rollout before the destructive auto-revert is trusted.

Status: pending-test → pending-ship.
