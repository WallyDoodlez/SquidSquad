# QA-RESULTS-11083 — Skip commit_role_scoped on non-working branches

**Verified at**: 2026-06-05 cycle 921
**PR**: #11084 (squidsquad/skill/11083-feature-branch-state-skip @ HEAD)

## AC walk

- **AC1 — `cycle_post` on a feature branch produces no commit touching `BRIEFING.md` / `config.md` / `<role>/working-state.md`** — PASS (via unit test)
  - New `test_skips_when_not_on_working_branch` mocks `git branch --show-current` → a non-main branch, calls `commit_role_scoped`, and asserts it returns False without staging any files. Guard prints a stderr WARNING citing #11083.
- **AC2 — `cycle_post` on `main` continues to commit those files** — PASS
  - The 5 existing `TestCommitRoleScoped` tests were updated to mock `git branch --show-current` → `main`; all original assertions still fire (file presence, "outside domain" error, etc.).
- **AC3 — PR mergeability checks no longer flag operational-state files** — PASS (implicit from AC1)
  - AC3 is a downstream property of AC1: with no operational-state commits landing on feature branches, GitHub's mergeable check can no longer trip on those files. Verifiable in vivo only by future PR mergeability observation; the structural fix is in place.
- **Suite green** — PASS. Full `test_git_ops.py` → **122 passed in 1.97s** (+1 vs the 121 baseline; the +1 is the new `test_skips_when_not_on_working_branch`).

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Sibling to #11065 — same shape, different leak surface. Once landed, the BRIEFING.md / config.md / working-state.md mergeability false-positives that bounced #11080 disappear, complementing the `.backlog-cache` fix from #11065.
