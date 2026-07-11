# QA-RESULTS-13271 — behind-count squash-merge guard (SEV-1 stale-tree prevention)

**Verdict: PASS — zero gaps.** High-sev (SEV-1 prevention). PR #13273 merged (squash, +additions-only re-verified). The guard directly addresses the incident my #12801 squash caused.

## AC walk (independent — derived from the incident + prevention direction)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | squash-merge refused when branch is > threshold behind base | PASS (behind 154/51 → refused) |
| AC2 | within threshold proceeds (no false-block of batch-ship) | PASS (3/50 → merge) |
| AC3 | exact boundary: `> max_behind` (50 proceeds, 51 refuses) | PASS |
| AC4 | undeterminable behind (gh/API hiccup → None) → fail-OPEN (proceed) | PASS |
| AC5 | only squash strategy guarded (a real merge commit preserves history) | PASS |
| AC6 | threshold env-tunable (`SQUIDSQUAD_MERGE_MAX_BEHIND`); default 50 | PASS |
| AC7 | fail-SAFE: refusal fires BEFORE any `gh pr merge` subprocess (main never mutated) | PASS |

## Evidence
- Code (git_ops.py): `MERGE_MAX_BEHIND_DEFAULT=50` (above batch-ship drain depth, below the 154-commit SEV-1), `_merge_max_behind()` (env override), `_pr_behind_by()` (GitHub compare API `behind_by`, returns None → fail-open). `pr_merge` (squash only) refuses with `(False, "branch too far behind base")` when `behind > max_behind`, routing back to re-sync.
- skill tests: `TestPrMerge` (far-behind-154-refused, within-threshold, undeterminable-fails-open, non-squash-not-guarded, env-override) + `TestPrBehindBy` (compare-API parse, None on failures). 10 PASS; full git_ops module = 178.
- **QA independent test** (`tests/test_feat_13271_merge_behind_guard.py`): the exact **threshold boundary** (50 proceeds / 51 refuses — guard is strictly `>`) and proves the SEV-1 (154) refusal fires **before any merge subprocess** (main not mutated) — skill tests 154/3 but not the edge or the no-mutation assertion.

## Scope / honesty
- This is the **interim fail-SAFE guard** (can only refuse, never mutate main). The issue is explicit that the robust net — a post-merge scope-audit + auto-revert — is a named **follow-up**, because a clone that merged main but whose squash still went stale (the subtle variant of my own incident) may report low `behind_by` and slip the count check. Verifying the guard as specified (catch the far-behind catastrophe class), NOT demanding it catch every variant — flagged, not a reblock.

## Self-referential merge note
The #13271 branch was itself cut behind main (its raw diff "reverted" #13262's timeout + my #13262 test — the exact hazard it guards). Applied the guard's own lesson: merged current main into the branch, **re-verified the squash diff is +additions-only** (zero deletions of #13262/#13267/config.md/composed CLAUDE.md), confirmed #13262 timeout + #13267 `--no-rebase` preserved post-merge, THEN merged. See [[learning-verify-squash-diff-additions-only-behind-branch]].

Status: pending-test → pending-ship.
