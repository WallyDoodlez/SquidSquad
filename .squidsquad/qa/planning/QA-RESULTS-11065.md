# QA-RESULTS-11065 — Untrack .squidsquad/.backlog-cache (merge-spiral root cause)

**Verified at**: 2026-06-05 cycle 915
**PR**: #11067 (squidsquad/skill/11065-untrack-backlog-cache @ HEAD)
**Scope**: 4 ACs as stated in issue body. 3-file change: git_ops.py allowlist removal + .backlog-cache untrack + test_git_ops.py assertion updates.

## AC walk

- **AC1 — `grep .backlog-cache references/scripts/git_ops.py` returns only docstring/comment mentions** — PASS
  - Two hits: `:495` (module docstring example: `e.g. .squidsquad/.backlog-cache, .squidsquad/.event-state.json`) and `:657` (in-place comment marker explaining the removal). No live allowlist entry remains in `_role_owned_patterns`.
- **AC2 — `.squidsquad/.backlog-cache` not in `git ls-files`** — PASS
  - `git ls-files .squidsquad/.backlog-cache` returns empty on the PR branch.
- **AC3 — `TestGitignoreVolatileFiles` green** — PASS
  - `tests/test_git_ops.py::TestGitignoreVolatileFiles::{test_gitignore_covers_volatile_files,test_volatile_files_not_tracked}` both PASS.
- **AC4 — `.backlog-cache` does NOT appear in role-scoped commits** — PASS (via expanded unit tests)
  - New `test_backlog_cache_not_in_allowlist` asserts the file is absent from `_role_owned_patterns(role)` for pm/qa/dm/skill.
  - `test_commit_role_scoped` updated: asserts `.backlog-cache` is NOT in the staged list AND IS in the skipped/outside-domain error message — i.e. if a role tries to stage it, commit_role_scoped explicitly refuses.
  - Full `test_git_ops.py` sweep → **121 passed in 1.81s** (matches skill's claim).

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Small, focused fix; tests exercise the exact behavior the ACs require. Removes the merge-spiral pattern that bounced PR #11048 (#11042) through DM twice. Note: the issue carries a dual `status:open + status:pending-test` label combo — tracker.py should handle the transition cleanly via the pending-test side.
