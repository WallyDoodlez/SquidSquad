# REVIEW-13298 — arch-doc reconcile audit (adversarial, cross-checked vs code)

Task #13298. Auditor: adversarial subagent (Sonnet), 2026-06-27. Scope: the 3 doc edits (HARNESS-ARCH §4.5.1, AGENT-RUNTIME §5.1 callout, COMPOSE-ARCH dev-domain note) vs (a) each other, (b) git_ops.py code, (c) internal consistency.

## VERDICT: PASS-WITH-FIXES → fixes applied → clean

### Findings
- **F2 (real fix, applied):** §4.5.1 claimed BOTH guards are "squash-strategy only." Code: only the pre-merge behind-count check is squash-gated (`_pr_behind_by` called only when `strategy == "squash"`); `_post_merge_scope_audit` fires after ANY successful merge. → Reworded: both GitHub-only; behind-count additionally squash-only; scope-audit fires for any strategy.
- **F1 (precision, applied):** §4.5.1 fail-safe didn't note that in the SHA-unresolvable tier the audit is skipped before any incident comment is posted. → Added that clause.
- **F3 (no action):** all cross-refs, env var names, threshold, defaults verified correct.

### Code-accuracy confirmations (all PASS, vs git_ops.py)
- MERGE_MAX_BEHIND_DEFAULT = 50 ✓; env SQUIDSQUAD_MERGE_MAX_BEHIND ✓
- env SQUIDSQUAD_MERGE_AUTO_REVERT ✓; **auto-revert DEFAULT OFF** ✓
- `deleted − declared` (git show --diff-filter=D vs gh pr view --json files) ✓
- fail-safe never reverts on uncertainty ✓; never raises ✓
- GitHub-only (returns early on non-GitHub backends) ✓
- behind-count fires BEFORE gh pr merge; refuse-only; main never mutated ✓; fail-OPEN on undeterminable ✓
- #13280 ahead-drop out of scope (deletion-only net) ✓ matches code docstring

### Cross-doc consistency: PASS
HARNESS-ARCH §4.5.1 ↔ AGENT-RUNTIME §5.1 callout describe #13271/#13285/#13291/#13286/#13287 consistently. AGENT-RUNTIME→HARNESS-ARCH §4.5.1 link valid. COMPOSE-ARCH dev-domain note consistent with AGENT-RUNTIME parenthetical.
